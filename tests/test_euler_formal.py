"""Audit the new formal record, executable mapping, and a broken-cache mutation."""

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EULER = ROOT / "demos/lean_euler"
FORMAL = EULER / "optimization/formal"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_formal_cache_record_matches_checked_sources_and_audits():
    results = json.loads((FORMAL / "record/formal-results.json").read_text())
    for name, result in results.items():
        assert result["checked"] and result["status"] == "proved"
        assert digest(FORMAL / name) == result["source_sha256"]
        for log in ["Audit.lean", "compile.log", "audit.log"]:
            assert (
                digest(FORMAL / "record" / Path(name).stem / log) == result["artifact_sha256"][log]
            )
        assert all(
            set(axioms) <= {"propext", "Classical.choice", "Quot.sound"}
            for axioms in result["axioms"].values()
        )
    assert "CacheSchedule.weighted_cache_optimal" in results["CacheSchedule.lean"]["axioms"]
    assert "EulerCache.step_equivalence" in results["EulerCache.lean"]["axioms"]
    instrumentation = json.loads((FORMAL / "record/instrumentation.json").read_text())
    for name, expected in instrumentation["source_sha256"].items():
        source = {
            "euler.py": EULER / name,
            "experiment.py": EULER / "optimization" / name,
            "instrument.py": FORMAL / name,
        }[name]
        assert digest(source) == expected
    assert instrumentation["stale_pressure_negative_control_max_difference"] > 0
    assert not instrumentation["schedules"]["missing_eval_negative_control"]["legal"]


def test_executable_call_counts_and_stale_cache_negative_control(tmp_path, monkeypatch):
    for source in [
        EULER / "euler.py",
        EULER / "optimization/experiment.py",
        FORMAL / "instrument.py",
    ]:
        shutil.copy2(source, tmp_path / source.name)
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("euler_instrument", tmp_path / "instrument.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    result = json.loads((tmp_path / "instrumentation.json").read_text())
    for row in result["actual_call_counts"]:
        assert row["reference"]["pressure_cells"] == 3 * row["cells"]
        assert row["cached"]["pressure_cells"] == row["cells"]
    assert result["scalar_model_transcription_max_difference"] < 1e-13
    assert result["stale_pressure_negative_control_max_difference"] > 1e-6


@pytest.mark.skipif(
    not (ROOT / ".runtime/lean-4.24.0/share/build-record.json").is_file()
    or not shutil.which("bwrap"),
    reason="installed Lean and sandbox required",
)
def test_real_formal_suite_and_broken_flux_are_distinguished(tmp_path):
    from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig
    from conjecture_solver.mvp_skills import MVPCapabilityRegistry

    for name in ["EulerCache.lean", "CacheSchedule.lean", "check_formal.py"]:
        shutil.copy2(FORMAL / name, tmp_path / name)
    registry = MVPCapabilityRegistry.discover(ROOT / "capabilities", names=("lean-4.24.0",))
    sandbox = BubblewrapSandbox(
        tmp_path,
        MVPAgentConfig(
            max_iterations=1,
            max_memory_bytes=4 * 1024**3,
            max_command_seconds=120,
        ),
        registry,
    )
    result = sandbox.run_capability("lean-4.24.0", ("check_formal.py",), timeout_seconds=120)
    assert result.returncode == 0, result.stdout + result.stderr
    reports = json.loads((tmp_path / "formal-results.json").read_text())
    assert all(r["checked"] for r in reports.values())
    # Break only the cached energy flux, leaving the reference and proof statements intact.
    source = (tmp_path / "EulerCache.lean").read_text()
    changed = source.replace("t.p * velocity u a", "(t.p+1) * velocity u a")
    assert changed != source
    (tmp_path / "Broken.lean").write_text(changed)
    (tmp_path / "check_broken.py").write_text(
        "from lean_check import check\n"
        "r=check('Broken.lean',['EulerCache.step_equivalence'],output='broken')\n"
        "assert not r['checked'] and r['status']=='undecided'\n"
    )
    result = sandbox.run_capability("lean-4.24.0", ("check_broken.py",), timeout_seconds=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / "broken/result.json").read_text())["compile_returncode"] != 0
