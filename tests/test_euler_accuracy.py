"""Check the matched-accuracy contract, independent audits, and proof provenance."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demos/lean_euler/accuracy"


def load_study(tmp_path, monkeypatch):
    for source in [
        DEMO / "study.py",
        DEMO.parent / "euler.py",
        DEMO.parent / "optimization/experiment.py",
    ]:
        shutil.copy2(source, tmp_path / source.name)
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("euler_accuracy", tmp_path / "study.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_same_solution_full_pipeline_and_final_time_admission(tmp_path, monkeypatch):
    study = load_study(tmp_path, monkeypatch)
    outputs = {
        m: study.solve(8, m, 0.05, 0.3) for m in ["reference", "cached", "fused", "muscl_rk2"]
    }
    assert np.array_equal(outputs["reference"][0], outputs["cached"][0])
    assert np.array_equal(outputs["reference"][0], outputs["fused"][0])
    for u, row in outputs.values():
        study.assess(u, row, 0.05)
    assert outputs["muscl_rk2"][1]["density_l1"] < outputs["reference"][1]["density_l1"]
    assert outputs["reference"][1]["density_l1"] > 0.02
    assert (
        outputs["fused"][1]["eos_cell_evaluations"] < outputs["cached"][1]["eos_cell_evaluations"]
    )
    with pytest.raises(ValueError, match="physical time"):
        study.assess(study.exact_state(8, 0), dict(n=8, final_time=0.0), 0.05)
    assert (
        study.select([outputs["reference"][1]], [1e-8], ["reference"])[0]["status"] == "unattained"
    )


def test_reference_quadrature_and_eos_instrumentation(tmp_path, monkeypatch):
    load_study(tmp_path, monkeypatch)
    shutil.copy2(DEMO / "validate.py", tmp_path / "validate.py")
    spec = importlib.util.spec_from_file_location("accuracy_validation", tmp_path / "validate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    report = json.loads((tmp_path / "validation.json").read_text())
    assert report["quadrature_max_error"] < 1e-13
    assert report["point_sample_vs_cell_average_max"] > 1e-4
    assert all(r["observed_eos_cells"] == r["reported_eos_cells"] for r in report["counts"])


def test_accuracy_record_matches_executed_sources_and_preserves_rejected_representation():
    r = json.loads((DEMO / "record/accuracy.json").read_text())
    for name, expected in r["sources"].items():
        assert hashlib.sha256((DEMO / "record/sources" / name).read_bytes()).hexdigest() == expected
        current = {
            "euler.py": DEMO.parent / name,
            "experiment.py": DEMO.parent / "optimization" / name,
        }.get(name, DEMO / name)
        assert hashlib.sha256(current.read_bytes()).hexdigest() == expected
    assert len(r["rows"]) == 72
    for row in r["rows"]:
        assert abs(row["final_time"] - r["contract"]["final_time"]) < 1e-12
        assert row["min_density"] > 0 and row["min_pressure"] > 0
    for choice in r["choices"]:
        candidates = [
            x
            for x in r["summary"]
            if x["method"] == choice["method"] and x["density_l1"] <= choice["epsilon"]
        ]
        assert choice["minimum_sampled_work"]["cell_stage_updates"] == min(
            x["cell_stage_updates"] for x in candidates
        )
        assert choice["fastest_sampled_wall"]["median_solver_seconds"] == min(
            x["median_solver_seconds"] for x in candidates
        )
    audit = json.loads((DEMO / "record/representation.json").read_text())
    rejected = next(c for c in audit["cases"] if c["method"] == "muscl_rk2" and c["n"] == 8)
    assert rejected["cell_average_l1"] < 0.01 < rejected["reconstruction_l1_order5"]
    assert not rejected["numerically_meets_reconstructed_target"]
    assert audit["one_cell_projection_negative_control"]["reconstructed_l1"] > 0.04


def test_conditional_proof_artifacts_match_sources():
    proof = json.loads((DEMO / "record/formal-results.json").read_text())
    assert sum(len(r["theorems"]) for r in proof.values()) == 12
    for name, r in proof.items():
        assert r["checked"]
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == r["source_sha256"]
        for file in ["Audit.lean", "compile.log", "audit.log"]:
            assert (
                hashlib.sha256((DEMO / "record" / Path(name).stem / file).read_bytes()).hexdigest()
                == r["artifact_sha256"][file]
            )
    ledger = json.loads((DEMO / "record/ledger.json").read_text())
    assert ledger["claims"]["hypotheses_discharged_for_nonlinear_solvers"] == "open"


@pytest.mark.skipif(
    not (ROOT / ".runtime/lean-4.24.0/share/build-record.json").is_file()
    or not shutil.which("bwrap"),
    reason="installed Lean and sandbox required",
)
def test_accuracy_lemmas_in_actual_capability(tmp_path):
    from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig
    from conjecture_solver.mvp_skills import MVPCapabilityRegistry

    for name in [
        "ContactReference.lean",
        "WaveDerivative.lean",
        "ErrorWork.lean",
        "check_formal.py",
    ]:
        shutil.copy2(DEMO / name, tmp_path / name)
    registry = MVPCapabilityRegistry.discover(ROOT / "capabilities", names=("lean-4.24.0",))
    sandbox = BubblewrapSandbox(
        tmp_path,
        MVPAgentConfig(max_iterations=1, max_memory_bytes=4 * 1024**3, max_command_seconds=180),
        registry,
    )
    result = sandbox.run_capability("lean-4.24.0", ("check_formal.py",), timeout_seconds=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert all(
        r["checked"] for r in json.loads((tmp_path / "formal-results.json").read_text()).values()
    )
