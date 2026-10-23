import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from simjecture_monitor.events import put
from simjecture_monitor.native_guard import stop_session


def module(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("parked_test", scripts / "parked_trials.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_async_submit_retains_real_owned_job_after_submitter_exits(tmp_path, monkeypatch):
    loaded = module(monkeypatch)
    (tmp_path / "submit.py").write_text(loaded.SUBMIT)
    (tmp_path / "experiment.py").write_text(
        "import time\nfrom pathlib import Path\ntime.sleep(.2)\n"
        "Path('finished').write_text('real child completed')\n"
    )
    result = subprocess.run(
        [sys.executable, "submit.py", "--name", "control", "--cells", "64", "--steps", "40"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    job = json.loads((tmp_path / "jobs/control.json").read_text())
    assert json.loads(result.stdout)["status"] == "submitted"
    until = time.time() + 3
    try:
        while not (tmp_path / "finished").exists() and time.time() < until:
            time.sleep(0.02)
        assert (tmp_path / "finished").read_text() == "real child completed"
        assert job["identity"]["session"] == job["identity"]["pid"]
    finally:
        stop_session(job["identity"])


def test_actual_receipt_and_adapter_observation_remain_separate(tmp_path, monkeypatch):
    loaded = module(monkeypatch)
    (tmp_path / "harness").mkdir()
    bridge = tmp_path / "harness/bridge.py"
    bridge.write_text(loaded.live.BRIDGE_GOOD)
    put(tmp_path / "jobs/control.json", dict(name="control", identity={"pid": 1, "starttime": "0"}))
    put(tmp_path / "runs/control/receipt.json", dict(status="succeeded", returncode=0))
    monkeypatch.setattr(loaded, "owned_alive", lambda _: False)
    assert loaded.statuses(tmp_path)[0]["reported_status"] == "completed"
    bridge.write_text(loaded.live.BRIDGE_BAD)
    observed = loaded.statuses(tmp_path)[0]
    assert (
        observed["process_receipt_status"] == "succeeded"
        and observed["reported_status"] == "running"
    )


def test_completion_stream_is_installed_before_jobs_exist(tmp_path, monkeypatch):
    loaded = module(monkeypatch)
    monkeypatch.setattr(loaded, "statuses", lambda _: [])
    monkeypatch.setattr(loaded.PairedSupervisor, "monitor_tick", lambda *a: None)
    sup = loaded.ParkedSupervisor.__new__(loaded.ParkedSupervisor)
    sup.monitor_streams = {}
    sup.service = SimpleNamespace(work=tmp_path)
    sup.monitor_tick(tmp_path / "turn")
    stream = next(iter(sup.monitor_streams.values()))
    assert isinstance(stream, loaded.CompletionStream)
    assert stream.packet("Observe")["state"]["host_state"]["async_completion"] == []
