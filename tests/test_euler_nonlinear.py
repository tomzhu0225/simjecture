"""Nonlinear-family commissioning and retained proof/source provenance."""

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos/lean_euler/nonlinear"


def test_pressure_coupled_dynamics_and_all_three_spatial_directions():
    spec = importlib.util.spec_from_file_location("nonlinear_probe", DEMO / "probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    state = probe.initial(16, 0.75, 0.05)
    pressure = probe.euler.pressure(state)
    assert np.all(state[..., 3] == 0)
    assert state[..., 0].min() >= 0.95
    assert pressure.min() >= 0.625
    assert all(np.max(np.abs(np.diff(pressure, axis=d))) > 0.01 for d in range(3))
    result = probe.run(16, 0.75, 0.05, final_time=0.05)
    assert result["max_abs_vertical_velocity"] > 1e-4
    assert result["max_abs_pressure_change"] > 1e-4
    assert result["mean_conserved_drift"] < 1e-11


def test_retained_commissioning_and_initial_diagnostic_proof():
    record = DEMO / "record"
    numerical = json.loads((record / "results.json").read_text())
    for name, checksum in numerical["sources"].items():
        assert hashlib.sha256((DEMO.parent / name).read_bytes()).hexdigest() == checksum
    assert len(numerical["rows"]) == 6
    assert all(r["max_abs_vertical_velocity"] > 1e-4 for r in numerical["rows"])
    proof = json.loads((record / "proof/result.json").read_text())
    assert proof["checked"]
    checksum = hashlib.sha256((DEMO / "InitialDynamics.lean").read_bytes()).hexdigest()
    assert checksum == proof["source_sha256"]
    for axioms in proof["axioms"].values():
        assert set(axioms) <= {"propext", "Classical.choice", "Quot.sound"}


def test_solver_foundations_and_independent_validation_provenance(tmp_path):
    record = DEMO / "record/solver"
    proof = json.loads((record / "solver-formal.json").read_text())
    assert proof["result"]["checked"]
    spec = importlib.util.spec_from_file_location("nonlinear_assembly", DEMO / "assemble_solver.py")
    assembly = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(assembly)
    assert set(proof["component_sha256"]) == set(assembly.COMPONENTS)
    assembled = tmp_path / "Solver.lean"
    assembly.assemble(assembled)
    for name, checksum in proof["component_sha256"].items():
        assert hashlib.sha256((DEMO / "formal" / name).read_bytes()).hexdigest() == checksum
    source = (record / "proof/Candidate.lean").read_bytes()
    assert assembled.read_bytes() == source
    assert hashlib.sha256(source).hexdigest() == proof["result"]["source_sha256"]
    assert {
        "EulerAdmissible.computed_nonlinear_step_admissible",
        "EulerDiscreteEnergy.frozen_linearized_energy_contraction",
        "EulerGridSobolev.three_dimensional_embedding",
        "EulerVariableStability.variable_principal_energy_growth",
        "EulerVariableStability.varying_metric_energy_increase",
        "EulerEntropyConvexity.entropy_convex",
        "EulerEntropyDynamics.canonical_entropy_potential",
        "EulerEntropyDynamics.smooth_entropy_balance",
        "EulerFaceEntropy.rusanov_face_entropy_bound",
        "EulerFiniteVolumeEntropy.entropy_step_dissipation",
        "EulerEntropyRegion.nonlinear_step_entropy_from_region",
        "EulerInitialRegion.initial_family_in_region",
        "EulerPhysicalFluxBounds.concrete_region_bounds",
        "EulerPhysicalFluxBounds.current_speeds_fail_any_region_constants",
        "EulerEntropyConservativeFlux.canonical_entropy_conservation",
        "EulerEntropyConservativeFlux.face_entropy_stable",
        "EulerEntropyCandidateStep.backtracked_step",
        "EulerEntropyCandidateStep.earlier_trials_rejected",
        "EulerPressurePolynomial.path_curvature_bound",
        "EulerEntropyStepBounds.quantitative_retry_bound",
        "EulerEntropyStepBounds.accepted_ratio_lower_bound",
    } <= set(proof["result"]["theorems"])
    for dependencies in proof["result"]["axioms"].values():
        assert set(dependencies) <= {"propext", "Classical.choice", "Quot.sound"}
    numerical = json.loads((record / "validation.json").read_text())
    for name, checksum in numerical["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == checksum
    assert numerical["cell_average_quadrature_max_error"] < 2e-12
    assert numerical["random_state_split_min_pressure"] > 0
    assert numerical["random_state_update_conservation_error"] < 1e-11
    assert numerical["unsafe_flux_splitting_pressure"] == -49
    entropy_record = json.loads((record / "entropy-validation.json").read_text())
    for name, checksum in entropy_record["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == checksum
    assert len(entropy_record["rows"]) == 9
    assert {row["n"] for row in entropy_record["rows"]} == {16, 32, 64}
    for row in entropy_record["rows"]:
        assert row["final_time"] == 0.25
        assert row["entropy_loss"] > 0
        assert row["relative_entropy_final"] > 0
        assert row["conservation_error"] < 1e-11

        if row["n"] == 16:
            assert row["direct_solver_replay_max_error"] == 0
    assert len(entropy_record["random_states"]) == 24
    alternative = json.loads((record / "ec-validation.json").read_text())
    for name, checksum in alternative["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == checksum
    assert alternative["logmean_high_precision_max_relative_error"] < 2e-14
    assert alternative["entropy_gradient_complex_step_max_scaled_error"] < 1e-10
    assert alternative["tadmor_identity_max_scaled_error"] < 1e-10
    assert alternative["excessive_proposal_control"]["rejected"] > 0
    assert alternative["constant_state_control"]["state_max_error"] == 0
    assert alternative["constant_state_control"]["rejected"] == 0
    assert len(alternative["rows"]) == 9
    assert {row["n"] for row in alternative["rows"]} == {16, 32, 64}
    for row in alternative["rows"]:
        assert row["final_time"] == 0.25
        assert row["min_density"] > 0 and row["min_pressure"] > 0
        assert row["minimum_entropy_margin"] >= 0
        assert row["conservation_error"] < 1e-11


def test_quantitative_retry_record_and_independent_derivative_checks():
    record = json.loads((DEMO / "record/solver/step-bound-validation.json").read_text())
    for name, checksum in record["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == checksum
    assert record["random_states"] == 2048
    assert record["hessian_complex_step_max_scaled_error"] < 1e-10
    assert record["minimum_scaled_curvature_margin"] >= 0
    assert record["minimum_density_ratio"] >= 0.5
    assert record["minimum_quadratic_ratio"] >= 0.5
    control = record["excessive_proposal_control"]
    assert 0 < control["actual_halvings"] <= control["predicted_halvings"]
    assert record["zero_dissipation_predicted_halvings"] == 0
    assert len(record["rows"]) == 9
    for row in record["rows"]:
        assert row["final_time"] == 0.25
        assert 0 <= row["max_actual_halvings"] <= row["max_predicted_halvings"]
        assert 0 < row["max_proposal_over_cap"] < 1
        assert row["min_entropy_budget_slack"] > 0
