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
        "EulerECFluxBounds.flux_consistency_bound",
        "EulerECFluxBounds.flux_consistency_bound_right",
        "EulerRegionEscape.accepted_step_leaves_region",
        "EulerGridPoincare.vector_poincare",
        "EulerEntropyDecay.computed_trace_entropy_loss",
        "EulerEntropyError.entropy_gap_error_lower_bound",
        "EulerEntropyIntegral.periodic_entropy_conservation",
        "EulerEntropyIntegral.periodic_conserved_integral",
        "EulerEntropyIntegral.cube_measure_univ",
        "EulerEntropyIntegral.physical_error_from_initial_entropy",
        "EulerHatReconstruction.reconstruction_nodes",
        "EulerHatReconstruction.reconstruction_mean",
        "EulerHatReconstruction.reconstruction_entropy",
        "EulerHatReconstruction.reconstructed_physical_error_lower_bound",
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


def test_region_consistency_record_and_compression_escape_control():
    record = json.loads((DEMO / "record/solver/region-validation.json").read_text())
    for name, checksum in record["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == checksum
    assert record["random_pairs"] == 4096
    assert record["near_pair_scales"] == [1, 1e-8]
    assert record["maximum_observed_flux_consistency_ratio"] <= record["proved_flux_bound"]
    control = record["compression_control"]
    assert control["shape"] == [3, 3, 3]
    assert control["before"]["minimum_region_margin"] == 0
    assert control["after"]["max_energy"] > 4
    assert control["after"]["min_density"] > 0
    assert control["after"]["min_pressure"] > 0
    assert control["rejected"] == 0
    assert control["entropy_margin"] >= 0
    assert control["conservation_error"] < 1e-11
    assert len(record["family_rows"]) == 31
    assert len([row for row in record["family_rows"] if row["n"] == 16]) == 25
    for row in record["family_rows"]:
        assert row["final_time"] == 0.25
        assert row["minimum_region_margin"] >= 0


def test_accumulated_entropy_loss_and_l1_comparison_record():
    record = json.loads((DEMO / "record/solver/entropy-decay-validation.json").read_text())
    for name, checksum in record["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == checksum
    assert record["pair_variance_max_scaled_error"] < 2e-14
    assert record["random_grid_max_poincare_ratio"] <= 1.5
    assert abs(record["constant_state_entropy_excess"]) < 1e-14
    errors = record["entropy_error_checks"]
    assert errors["max_independent_gradient_component"] <= 32
    assert errors["max_pointwise_entropy_over_component_l1"] <= 32
    assert errors["entropy_gap_lower_bound"] <= errors["weighted_max_component_l1"]
    assert len(record["rows"]) == 9
    for row in record["rows"]:
        assert row["final_time"] == 0.25
        assert row["min_region_margin"] >= 0
        assert row["mean_conservation_error"] < 1e-11
        assert row["max_variance_over_n2_edges"] <= 1.5
        assert row["max_excess_over_n2_edges"] <= 75_000
        assert row["min_dissipation_over_edges"] >= 1 / 100_000
        assert row["entropy_loss"] >= row["conditional_loss_lower_bound"] > 0


def test_continuous_reconstruction_provenance_and_independent_quadrature():
    record = json.loads((DEMO / "record/solver/reconstruction-validation.json").read_text())
    for name, checksum in record["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == checksum
    assert record["constant_error"] < 2e-15
    assert {row["n"] for row in record["random_rows"]} == {1, 2, 3, 5}
    for row in record["random_rows"]:
        assert row["queries"] == 4096
        assert row["dense_sparse_error"] < 3e-13
        assert row["node_error"] < 3e-13
        assert row["periodic_error"] < 3e-13
        assert row["seam_error"] == 0
        assert row["min_weight"] >= 0
        assert row["weight_sum_error"] < 1e-14
    assert len(record["family_rows"]) == 4
    for row in record["family_rows"]:
        assert row["final_time"] == 0.25
    for row in record["random_rows"] + record["family_rows"]:
        assert row["mean_error"] < 5e-13
        assert row["axis_weight_integral_error"] < 2e-14
        assert abs(row["quadrature_total_weight"] - 1) < 2e-14
        assert row["quadrature_entropy_margin"] >= -2e-14
        assert row["reconstruction_region_margin"] >= 0
