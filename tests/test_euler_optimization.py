"""A cache must preserve the original nonlinear update and its retained inputs."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos/lean_euler"


def test_cached_euler_matches_on_rectangular_nonlinear_grid(tmp_path, monkeypatch):
    shutil.copy2(DEMO / "euler.py", tmp_path / "euler.py")
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location(
        "cache_experiment", DEMO / "optimization/experiment.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rng = np.random.default_rng(28)
    u = np.empty((3, 4, 5, 5))
    rho = rng.uniform(0.5, 2, (3, 4, 5))
    velocity = rng.uniform(-0.5, 0.5, (3, 4, 5, 3))
    u[..., 0] = rho
    u[..., 1:4] = rho[..., None] * velocity
    u[..., 4] = rng.uniform(0.5, 2, (3, 4, 5)) + 0.5 * rho * np.sum(velocity**2, axis=-1)
    original = u.copy()
    expected = module.reference.step(u, 0.001, 0.2)
    actual = module.cached_step(u, 0.001, 0.2)
    assert np.array_equal(actual, expected)
    assert np.array_equal(u, original)
    assert np.max(abs(actual.sum(axis=(0, 1, 2)) - u.sum(axis=(0, 1, 2)))) < 1e-12
    assert np.array_equal(module.cached_step(u, 0, 0.2), u)


def test_3d_record_matches_sources_and_retains_all_timing_samples():
    result = json.loads((DEMO / "optimization/record/optimization.json").read_text())
    for name, expected in result["source_sha256"].items():
        source = DEMO / name if name == "euler.py" else DEMO / "optimization" / name
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    assert all(case["bitwise_equal"] for case in result["equivalence_checks"])
    for row in result["timings"]:
        assert all(len(samples) == 11 for samples in row["trials_seconds"].values())
    assert result["claim_status"]["solver_optimality_at_fixed_error"] == "open"
