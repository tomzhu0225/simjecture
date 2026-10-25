import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from simjecture_monitor.events import put


def modules(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    result = []
    for name in ["generalization_fixture", "generalization_trials"]:
        spec = importlib.util.spec_from_file_location(name, scripts / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result.append(module)
    return result


def test_diagnostic_reprocessing_keeps_original_submission_unchanged(tmp_path, monkeypatch):
    fixture, _ = modules(monkeypatch)
    script = tmp_path / "submit_bundle.py"
    script.write_text(fixture.SUBMIT)
    subprocess.run([sys.executable, str(script)], cwd=tmp_path, check=True, capture_output=True)
    original = (tmp_path / "SUBMISSION.json").read_bytes()
    duplicate = subprocess.run([sys.executable, str(script)], cwd=tmp_path, capture_output=True)
    assert duplicate.returncode != 0
    subprocess.run(
        [sys.executable, str(script), "--reprocess"], cwd=tmp_path, check=True, capture_output=True
    )
    assert (tmp_path / "SUBMISSION.json").read_bytes() == original
    assert json.loads((tmp_path / "REPROCESS.json").read_text())["id"]
    compile(fixture.PIPELINE, "pipeline.py", "exec")
    compile(fixture.EXPERIMENT, "experiment.py", "exec")


def test_raw_observer_excludes_host_labels_and_clears_failures_on_recovery(tmp_path, monkeypatch):
    _, loaded = modules(monkeypatch)
    # initialize needs the repair argument container before constructing a source subject.
    sup = loaded.RawSupervisor.__new__(loaded.RawSupervisor)
    work = tmp_path / "research"
    work.mkdir()
    (work / "harness").mkdir()
    sup.root = tmp_path
    sup.args = SimpleNamespace()
    sup.service = SimpleNamespace(work=work, pending_help=lambda: [], _all=lambda _: [])
    sup.monitor_dir = tmp_path / "monitor"
    sup.monitor_dir.mkdir()
    sup.initialize("model")
    sup.monitor_streams = {}
    sup.authority_future = None
    sup.state = {"deadline": 1000}
    sup.worker_parked = True
    put(
        tmp_path / "HOST_CASE.json", {"family": "secret_family", "expected_action": "wake_director"}
    )
    put(
        work / "progress.json",
        dict(sequence=1, phase="read_attempt", exit_code=1, stderr="temporary read"),
    )
    first = sup.snapshot(tmp_path / "turn", 100)
    assert first["state"]["host_state"]["telemetry"]["consecutive_tool_failures"] == 1
    assert "secret_family" not in json.dumps(first)
    assert "HARNESS_CONTRACT_ERROR" not in json.dumps(first)
    put(
        work / "progress.json",
        dict(sequence=2, phase="aggregation", exit_code=0, iteration=1, loss=0.4),
    )
    second = sup.snapshot(tmp_path / "turn", 105)
    assert second["state"]["host_state"]["telemetry"]["consecutive_tool_failures"] == 0
    assert len(second["state"]["host_state"]["progress_history"]) == 2


def test_completed_job_blocks_late_action_without_relabelling_model_choice(tmp_path, monkeypatch):
    _, loaded = modules(monkeypatch)
    sup = loaded.RawSupervisor.__new__(loaded.RawSupervisor)
    sup.monitor_dir = tmp_path
    sup.monitor_sequence = 0
    sup.discretionary_used = False
    sup.worker_parked = True
    sup.observation_violations = []
    sup.job = SimpleNamespace(poll=lambda: 0)
    sup.monitor_latest = {"state": {"host_state": {}}}
    packet = {
        "packet_sha256": "same",
        "state": {"subject": "worker", "events": [], "host_state": {}},
    }
    decision = {"choice": "request_repair_judge", "packet_sha256": "same"}
    sup._record_decision(packet, decision, received_at=10)
    recorded = json.loads((tmp_path / "decision-00001.json").read_text())
    assert recorded["decision"]["choice"] == "request_repair_judge"
    assert recorded["effective_action"] == "defer"
    assert not sup.discretionary_used
