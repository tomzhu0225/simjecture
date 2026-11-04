"""Verify the floating-point demonstration and its formal evidence provenance."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos/lean_euler/optimality"


def load_solver():
    spec = importlib.util.spec_from_file_location("euler_optimality_solver", DEMO / "solver.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_output_contains_samples_and_never_requeries_input():
    solver = load_solver()
    observations = []

    def oracle(a):
        observations.append(a.reshape(-1, 3).copy())
        return solver.demonstration_density(a)

    reconstruction = solver.solve(oracle, 2.0, 0.2)
    n = reconstruction.n
    assert sum(len(a) for a in observations) == n**3 == reconstruction.query_count
    points = np.random.default_rng(42).random((2000, 3))
    points = np.concatenate([points, [[0, 0, 0], [1, 1, 1]]])
    for t in [0.0, 0.75, 1.0]:
        x = solver.flow(t, points)
        error = np.max(
            np.abs(
                reconstruction.evaluate(t, x)
                - solver.exact_state(solver.demonstration_density, t, x)
            )
        )
        assert error <= reconstruction.exact_real_error_bound + 1e-12
    assert len(observations) == 1
    with pytest.raises(ValueError, match="outside"):
        reconstruction.evaluate(0, np.array([[2.0, 0.5, 0.5]]))


def test_resolution_factor_has_a_nontrivial_accuracy_witness():
    solver = load_solver()

    def density(a):
        return 1.5 + 0.49 * np.tanh((2 / 0.49) * (a[..., 0] - 0.45))

    correct = solver.solve(density, 2.0, 0.05)
    n = 10
    c = (np.arange(n) + 0.5) / n
    bad_data = density(np.stack(np.meshgrid(c, c, c, indexing="ij"), axis=-1))
    altered = solver.Reconstruction(bad_data, 2.0, 0.05, n**3)
    witness = solver.flow(0.75, np.array([[0.5 - 1e-10, 1.0, 1.0]]))
    exact = solver.exact_state(density, 0.75, witness)
    assert np.max(np.abs(correct.evaluate(0.75, witness) - exact)) <= 0.05
    assert np.max(np.abs(altered.evaluate(0.75, witness) - exact)) > 0.14


def test_proof_and_numerical_receipts_match_current_sources():
    proof = json.loads((DEMO / "record/formal-results.json").read_text())
    assert proof["positive"]["checked"]
    assert "Machines.certified_general_optimality" in proof["positive"]["theorems"]
    assert not proof["negative"]["checked"]
    assert proof["negative"]["compile_returncode"] == 1
    allowed = {"propext", "Classical.choice", "Quot.sound"}
    for dependencies in proof["positive"]["axioms"].values():
        assert set(dependencies) <= allowed
    for name, expected in proof["component_sha256"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == expected
    assert (
        hashlib.sha256((DEMO / "record/proof/Candidate.lean").read_bytes()).hexdigest()
        == proof["positive"]["source_sha256"]
    )
    numeric = json.loads((DEMO / "record/results.json").read_text())
    for name, expected in numeric["sources"].items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == expected
    for row in numeric["rows"]:
        assert row["oracle_queries"] == row["n"] ** 3
        assert (
            max(row["sampled_full_state_max_error_by_time"])
            <= row["exact_real_uniform_bound"] + 1e-12
        )
    assert numeric["hard_pair"]["all_query_answers_equal"]
    assert numeric["resolution_negative_control"]["altered_error"] > 0.14
