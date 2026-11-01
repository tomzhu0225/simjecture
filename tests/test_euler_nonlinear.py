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
