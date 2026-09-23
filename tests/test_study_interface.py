import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conjecture_solver.mvp_launch import materialize_operator_input, prepare_resume
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.study_launch import NativeStudyRequest
from conjecture_solver.study_status import TerminalProgress, minimal_snapshot
from conjecture_solver.web.application import SimjectureWebApplication, WebApplicationError


def test_native_launch_persists_mode_backend_and_fixed_deadline(tmp_path):
    request = NativeStudyRequest(
        hypothesis="A finite claim.",
        campaign_id="study",
        output_directory=str(tmp_path / "study"),
        max_wall_seconds=60,
        agent_executable=sys.executable,
    )
    plan = materialize_operator_input(request)
    root = Path(plan.output_directory)
    before = ResearchService(root).manifest["deadline"]
    put(root / "supervisor/state.json", {}) if (root / "supervisor").exists() else None
    resumed = prepare_resume(root)
    assert "--mode" in resumed.argv and "minimal" in resumed.argv
    assert ResearchService(root).manifest["deadline"] == before
    assert minimal_snapshot(root).identity.config["mode"] == "minimal"


def test_browser_defaults_and_explicit_unsupported_routes(tmp_path):
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    assert app.bootstrap()["default_mode"] == "minimal"
    for backend in ["dsh", "api"]:
        with pytest.raises(WebApplicationError, match="explicit legacy"):
            app.create_campaign(dict(hypothesis="A finite claim.", backend=backend))


def test_minimal_browser_graph_and_terminal_progress(tmp_path):
    s = ResearchService.create(tmp_path / "study", "A finite claim.")
    (s.root / "supervisor").mkdir()
    put(
        s.root / "supervisor/state.json",
        dict(
            status="running",
            backend="codex-glm",
            model="glm-5.3",
            round=1,
            started_at=time.time(),
            deadline=time.time() + 60,
            activity="Running a command",
        ),
    )
    app = SimjectureWebApplication(
        initial_run=s.root, scan_roots=(tmp_path,), allow_mutations=False
    )
    snapshot = app.campaign_snapshot(app.initial_campaign)
    assert snapshot["engine"]["mode"] == "minimal"
    assert snapshot["engine"]["name"] == "codex-glm"
    assert snapshot["claim_graph"]["nodes"][0]["statement"] == "A finite claim."
    assert not snapshot["controls"]["can_cancel"]
    output = io.StringIO()
    with TerminalProgress(s.root, stream=output):
        time.sleep(0.05)
    assert "Running a command" in output.getvalue()
    assert "codex-glm/glm-5.3" in output.getvalue()
    assert "left" in output.getvalue()


def wait_state(root, predicate, timeout=15):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            state = json.loads((root / "supervisor/state.json").read_text())
        except (OSError, ValueError):
            state = {}
        if predicate(state):
            return state
        time.sleep(0.1)
    pytest.fail(f"Timed out waiting for state: {state}")


def start_fixture(tmp_path, root, code, wall=30):
    agent = tmp_path / "fixture-agent"
    agent.write_text(f"#!{sys.executable}\n" + code)
    agent.chmod(0o755)
    h = tmp_path / "hypothesis.txt"
    h.write_text("A lifecycle fixture, not scientific evidence.")
    i = tmp_path / "instructions.txt"
    i.write_text("Exercise process lifecycle only.")
    command = [
        sys.executable,
        "-m",
        "conjecture_solver.study",
        "--campaign",
        str(root),
        "--hypothesis-file",
        str(h),
        "--instructions-file",
        str(i),
        "--backend",
        "codex-glm",
        "--executable",
        str(agent),
        "--wall-seconds",
        str(wall),
        "--turn-seconds",
        "10",
        "--quiet",
    ]
    log = (tmp_path / "fixture.log").open("a")
    process = subprocess.Popen(
        command,
        stdout=log,
        stderr=log,
        start_new_session=True,
        env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src")),
    )
    log.close()
    return process


def test_real_process_pause_resume_and_deadline(tmp_path):
    root = tmp_path / "study"
    code = (
        "import time,json\n"
        'print(json.dumps({"type":"thread.started","thread_id":"fixture"}),flush=True)\n'
        "time.sleep(60)\n"
    )
    process = start_fixture(tmp_path, root, code, wall=16)
    try:
        state = wait_state(root, lambda s: bool(s.get("child_pid")))
        deadline = state["deadline"]
        put(root / "supervisor/control.json", dict(command="pause"))
        assert process.wait(timeout=10) == 0
        assert wait_state(root, lambda s: s.get("status") == "paused")["deadline"] == deadline
        process = start_fixture(tmp_path, root, code, wall=16)
        state = wait_state(root, lambda s: s.get("status") == "running" and s.get("child_pid"))
        assert state["deadline"] == deadline
        assert process.wait(timeout=25) == 124
        assert (
            json.loads((root / "research_report.json").read_text())["status"] == "budget_exhausted"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


@pytest.mark.parametrize("message", ["quota exhausted", "401 unauthorized"])
def test_provider_failure_pauses_without_scientific_completion(tmp_path, message):
    root = tmp_path / "study"
    process = start_fixture(
        tmp_path, root, f"import sys\nprint({message!r},file=sys.stderr)\nsys.exit(1)\n"
    )
    try:
        assert process.wait(timeout=20) == 1
        state = wait_state(root, lambda s: s.get("status") == "paused_external_error")
        assert state["round"] == 1
        assert not ResearchService(root).status()["completed"]
        assert prepare_resume(root).argv
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def test_cancel_terminates_real_experiment_process_group(tmp_path):
    from conjecture_solver.mvp_launch import ProcessIdentity, process_identity_matches

    s = ResearchService.create(
        tmp_path / "study", "Lifecycle cancellation fixture.", wall_seconds=60
    )
    (s.work / "slow.py").write_text("import time\ntime.sleep(60)\n")
    receipt = s.run("slow.py", outputs=["result.json"])
    identity = ProcessIdentity.model_validate(receipt["worker_identity"])
    assert process_identity_matches(identity)
    s.cancel_active()
    end = time.monotonic() + 5
    while process_identity_matches(identity) and time.monotonic() < end:
        time.sleep(0.05)
    assert not process_identity_matches(identity)
    assert s.status()["experiments"][0]["status"] == "cancelled"
    assert not s.status()["completed"]


def test_backend_contract_and_study_lock_are_enforced(tmp_path):
    import argparse
    import fcntl
    import hashlib

    from conjecture_solver.study import configure_parser, run

    root = tmp_path / "study"
    root.mkdir()
    put(root / "study-launch.json", dict(backend="grok", model="saved-model"))
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    args = parser.parse_args(
        ["--campaign", str(root), "--instructions-file", "unused", "--backend", "codex-glm"]
    )
    with pytest.raises(ValueError, match="launch contract"):
        run(args)
    digest = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:20]
    with (tmp_path / f".simjecture-{digest}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ValueError, match="already owns"):
            run(args)


@pytest.mark.parametrize(
    "entry",
    [
        ["python", "-m", "conjecture_solver.study"],
        ["python", "-m", "conjecture_solver.research_supervisor"],
        ["python", "-m", "conjecture_solver.agent_supervisor"],
        ["python", "-m", "conjecture_solver", "study"],
        ["python", "/venv/bin/simjecture", "study"],
        ["python", "/venv/bin/simjecture-supervise"],
        ["python", "/venv/bin/simjecture-research"],
    ],
)
def test_verified_identity_recognizes_native_entrypoints(tmp_path, entry):
    from conjecture_solver.mvp_launch import _argv_targets_run

    assert _argv_targets_run(tuple(entry + ["--campaign", str(tmp_path)]), tmp_path)
    assert not _argv_targets_run(tuple(entry + ["--campaign", str(tmp_path / "other")]), tmp_path)
    assert not _argv_targets_run(("python", "unrelated.py", "--campaign", str(tmp_path)), tmp_path)


@pytest.mark.parametrize("mode", ["structured", "frontier"])
def test_native_modes_project_live_backend_and_jobs(tmp_path, mode):
    from conjecture_solver.mvp_monitor import MVPRunMonitor

    request = NativeStudyRequest(
        hypothesis="A finite test.",
        campaign_id="study",
        output_directory=str(tmp_path / "study"),
        mode=mode,
        agent_executable=sys.executable,
    )
    plan = materialize_operator_input(request)
    root = Path(plan.output_directory)
    (root / "supervisor").mkdir(exist_ok=True)
    put(
        root / "supervisor/state.json",
        dict(
            status="running",
            workflow=mode,
            round=3,
            started_at=time.time(),
            deadline=time.time() + 60,
            activity="Reviewing evidence",
            usage_by_thread={"example": dict(input_tokens=123, output_tokens=45)},
        ),
    )
    job = root / "jobs/jobs/job_example"
    job.mkdir(parents=True, exist_ok=True)
    put(job / "state.json", dict(job_id="job_example", status="running"))
    put(job / "request.json", dict(metadata={"action": "run_python", "argv": ["calc.py"]}))
    snapshot = MVPRunMonitor(root).snapshot()
    assert snapshot.identity.config["mode"] == mode
    assert snapshot.current_action.description == "Reviewing evidence"
    assert snapshot.token_usage.total_tokens == 168
    assert snapshot.executions[0].status == "running"


def test_browser_revision_tracks_custom_supervisor_directory(tmp_path):
    root = tmp_path / "study"
    ResearchService.create(root, "A custom-state monitoring fixture.")
    directory = tmp_path / "separate-supervisor"
    directory.mkdir()
    put(
        root / "study-launch.json",
        dict(state_dir=str(directory), backend="codex-glm", model="fixture"),
    )
    put(directory / "state.json", dict(status="running", round=1, activity="Agent working"))
    app = SimjectureWebApplication(initial_run=root, scan_roots=(tmp_path,), allow_mutations=False)
    first = app.campaign_snapshot(app.initial_campaign)
    put(directory / "state.json", dict(status="running", round=1, activity="Reviewing evidence"))
    second = app.campaign_snapshot(app.initial_campaign)
    assert first["revision"] != second["revision"]
    assert second["snapshot"]["current_action"]["description"] == "Reviewing evidence"


def test_network_failure_retries_until_absolute_deadline(tmp_path):
    root = tmp_path / "study"
    process = start_fixture(
        tmp_path,
        root,
        "import sys\nprint('network interrupted',file=sys.stderr)\nsys.exit(1)\n",
        wall=10,
    )
    try:
        assert process.wait(timeout=20) == 124
        state = wait_state(root, lambda s: s.get("status") == "budget_exhausted")
        assert state["provider_retry_count"] >= 2
        assert state["provider_wait_seconds"] > 0
        assert not ResearchService(root).status()["completed"]
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
