"""Backend, DAG staging, board messaging, worker control, and HTTP tests for v0.8 swarms."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import httpx
import pytest

from conjecture_solver.web.activity import describe_tool
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from conjecture_solver.web.swarm import _validate_swarm_spec
from conjecture_solver.web.workspace import Workspace
from tests.test_workspace import wait_for


def _write_swarm_codex_stub(binary: Path) -> None:
    """Fake CLI worker that reads upstream artifacts, board/steering, and writes outputs."""
    binary.write_text(
        f"#!{sys.executable}\n"
        + """
import json, os, sys, time
from pathlib import Path

context = json.loads(Path("CONTEXT.json").read_text(encoding="utf-8"))
name = context["name"]
outputs = context["outputs"]
Path("worker_started").touch()

# Optional gate for testing live steering / stop controls
gate = os.environ.get("SIMJECTURE_SWARM_GATE")
if gate and name == os.environ.get("SIMJECTURE_SWARM_HOLD_MEMBER", ""):
    deadline = time.time() + 15
    while time.time() < deadline and not Path(gate).exists():
        time.sleep(0.05)

# Optional failure injection for retry testing
fail_flag = os.environ.get("SIMJECTURE_SWARM_FAIL_ONCE")
fail_member = os.environ.get("SIMJECTURE_SWARM_FAIL_MEMBER", "")
if fail_flag and Path(fail_flag).exists() and name == fail_member:
    Path(fail_flag).unlink(missing_ok=True)
    err_ev = {"type": "item.completed", "item": {"type": "agent_message", "text": "Fail once"}}
    print(json.dumps(err_ev), flush=True)
    sys.exit(1)

upstream_dir = Path("inputs/upstream")
upstream_files = {}
if upstream_dir.is_dir():
    for path in sorted(upstream_dir.rglob("*")):
        if path.is_file():
            rel_key = path.relative_to(upstream_dir).as_posix()
            upstream_files[rel_key] = path.read_text(encoding="utf-8")

payload = {
    "member": name,
    "upstream": upstream_files,
    "prompt_has_steering": "LIVE USER STEERING" in sys.argv[-1] or "SWARM" in sys.argv[-1],
}
for rel in outputs:
    target = Path(rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\\n", encoding="utf-8")

Path("HELPER_RESULT.json").write_text(
    json.dumps(
        {
            "status": "completed",
            "summary": f"{name} completed with {len(upstream_files)} upstream files.",
            "artifacts": outputs,
            "checks": ["outputs written"],
            "unresolved": [],
        }
    ),
    encoding="utf-8",
)
done_ev = {"type": "item.completed", "item": {"type": "agent_message", "text": f"{name} done."}}
print(json.dumps(done_ev), flush=True)
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 2}}), flush=True)
""",
        encoding="utf-8",
    )
    binary.chmod(0o755)


def test_swarm_dag_validation_and_stage_assignment():
    spec, stages = _validate_swarm_spec(
        {
            "title": "Euler DAG",
            "strategy": "adversarial_verify",
            "members": [
                {
                    "name": "Solver",
                    "role": "solver",
                    "task": "Compute the primal numerical solution.",
                    "completion_criteria": "Write solution.json.",
                    "outputs": ["solution.json"],
                },
                {
                    "name": "Falsifier",
                    "role": "falsifier",
                    "task": "Probe for boundary counterexamples.",
                    "completion_criteria": "Write falsify.json.",
                    "outputs": ["falsify.json"],
                },
                {
                    "name": "Verifier",
                    "role": "verifier",
                    "task": "Verify Solver and Falsifier outputs.",
                    "completion_criteria": "Write verdict.json.",
                    "outputs": ["verdict.json"],
                    "depends_on": ["Solver", "Falsifier"],
                },
            ],
        }
    )
    assert spec.title == "Euler DAG"
    assert stages == {"Solver": 0, "Falsifier": 0, "Verifier": 1}

    # Cycle detection
    with pytest.raises(ValueError, match="cycle"):
        _validate_swarm_spec(
            {
                "title": "Cyclic",
                "members": [
                    {
                        "name": "Alpha",
                        "task": "Step A depends on B.",
                        "completion_criteria": "Write a.txt.",
                        "outputs": ["a.txt"],
                        "depends_on": ["Beta"],
                    },
                    {
                        "name": "Beta",
                        "task": "Step B depends on A.",
                        "completion_criteria": "Write b.txt.",
                        "outputs": ["b.txt"],
                        "depends_on": ["Alpha"],
                    },
                ],
            }
        )

    # Unknown dependency & duplicate name
    with pytest.raises(ValueError, match="unknown member"):
        _validate_swarm_spec(
            {
                "title": "Missing dep",
                "members": [
                    {
                        "name": "Solo",
                        "task": "Depends on ghost.",
                        "completion_criteria": "Write s.txt.",
                        "outputs": ["s.txt"],
                        "depends_on": ["Ghost"],
                    }
                ],
            }
        )


def test_swarm_activity_labels():
    assert describe_tool("launch_swarm", {"title": "Scan"})["label"] == "Launching swarm"
    assert describe_tool("swarm_status", {"swarm_id": "swarm-1"})["label"] == "Checking swarm"
    assert describe_tool("swarm_message", {"recipient": "all"})["label"] == "Messaging swarm"
    assert describe_tool("swarm_import", {})["label"] == "Importing swarm artifact"
    assert describe_tool("swarm_control", {})["label"] == "Controlling swarm"
    assert describe_tool("swarm_board_read", {})["label"] == "Reading swarm board"
    assert describe_tool("swarm_board_post", {})["label"] == "Posting to swarm board"


def test_composer_swarm_mode_persists_and_injects_coordinator_directive(tmp_path: Path):
    ws = Workspace(tmp_path / ".workspace")
    ws.save_api({"base_url": "http://127.0.0.1:9999/v1"})
    proj = ws.create(
        {
            "name": "Auto Swarm",
            "agent": {"backend": "builtin", "model": "test-model"},
            "swarm_mode": "auto",
        }
    )
    pid = proj["id"]
    assert ws.project(pid)["swarm_mode"] == "auto"
    assert set(ws.project(pid)["agent"]) == {"backend", "model", "reasoning_effort"}

    ws.select_agent(
        pid,
        {
            "backend": "builtin",
            "model": "test-model",
            "reasoning_effort": "high",
            "swarm_mode": "adversarial_verify",
        },
    )
    assert ws.project(pid)["swarm_mode"] == "adversarial_verify"
    assert ws.project(pid)["agent"] == {
        "backend": "builtin",
        "model": "test-model",
        "reasoning_effort": "high",
    }

    from conjecture_solver.web.workspace import swarm_coordination_prompt

    directive = swarm_coordination_prompt("adversarial_verify")
    assert "SWARM COORDINATION MODE IS ENABLED (adversarial_verify)" in directive
    assert "launch_swarm" in directive


def test_swarm_dag_execution_upstream_staging_board_and_import(tmp_path: Path, monkeypatch):
    binary = tmp_path / "codex"
    _write_swarm_codex_stub(binary)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])

    ws = Workspace(tmp_path / ".workspace")
    project = ws.create({"name": "DAG Swarm", "agent": {"backend": "codex", "model": "test"}})
    pid = project["id"]
    pdir = ws.directory(pid)
    (pdir / "files/seed.txt").write_text("seed=42\n", encoding="utf-8")

    created = ws.launch_swarm(
        pid,
        {
            "title": "Two-stage exploration",
            "objective": "Compare branch A and branch B, then synthesize.",
            "strategy": "parallel_explore",
            "wait": False,
            "members": [
                {
                    "name": "Explorer A",
                    "role": "explorer",
                    "task": "Explore numerical scheme A.",
                    "completion_criteria": "Produce branch_a.json.",
                    "outputs": ["branch_a.json"],
                    "timeout_seconds": 30,
                },
                {
                    "name": "Explorer B",
                    "role": "explorer",
                    "task": "Explore numerical scheme B.",
                    "completion_criteria": "Produce branch_b.json.",
                    "outputs": ["branch_b.json"],
                    "timeout_seconds": 30,
                },
                {
                    "name": "Synthesizer",
                    "role": "synthesizer",
                    "task": "Combine upstream branch A and branch B.",
                    "completion_criteria": "Produce synthesis.json.",
                    "outputs": ["synthesis.json"],
                    "depends_on": ["Explorer A", "Explorer B"],
                    "timeout_seconds": 30,
                },
            ],
        },
    )
    swarm_id = created["id"]
    assert created["scientific_status"] == "exploration"
    wait_for(lambda: ws.swarm_detail(pid, swarm_id)["status"] == "completed", seconds=25)

    detail = ws.swarm_detail(pid, swarm_id)
    assert detail["counts"]["succeeded"] == 3
    synth = next(m for m in detail["members"] if m["name"] == "Synthesizer")
    assert synth["stage"] == 1
    assert synth["job_id"]
    synth_file = pdir / "simulations" / synth["job_id"] / "workspace" / "synthesis.json"
    synth_payload = json.loads(synth_file.read_text(encoding="utf-8"))
    # Verify upstream deliverables were automatically staged into inputs/upstream/<slug>/
    assert "explorer-a/branch_a.json" in synth_payload["upstream"]
    assert "explorer-b/branch_b.json" in synth_payload["upstream"]

    # Post a board message and verify it persists
    msg = ws.swarm_message(
        pid, {"swarm": swarm_id, "message": "Synthesizer findings verified", "recipient": "all"}
    )
    assert msg["message"]["content"] == "Synthesizer findings verified"
    board = ws.swarm_detail(pid, swarm_id)["board"]
    assert any(b["content"] == "Synthesizer findings verified" for b in board)

    # Import verified deliverable into project files/
    imported = ws.swarm_import(
        pid, {"swarm": swarm_id, "worker": synth["job_id"], "files": ["synthesis.json"]}
    )
    assert len(imported["imported"]) == 1
    assert (pdir / "files/synthesis.json").is_file()


def test_swarm_retry_worker_add_worker_and_http_routes(tmp_path: Path, monkeypatch):
    binary = tmp_path / "codex"
    _write_swarm_codex_stub(binary)
    fail_flag = tmp_path / "fail_once"
    fail_flag.touch()
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("SIMJECTURE_SWARM_FAIL_ONCE", str(fail_flag))
    monkeypatch.setenv("SIMJECTURE_SWARM_FAIL_MEMBER", "Flaky")

    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    project = app.workspace.create(
        {"name": "Swarm HTTP Control", "agent": {"backend": "codex", "model": "test"}}
    )
    pid = project["id"]
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False) as c:
            token = c.get("/api/workspace/bootstrap").json()["control_token"]
            headers = {"X-Simjecture-Token": token}

            # Unauthenticated launch must be rejected
            unauth = c.post(
                "/api/workspace/swarm-launch",
                json={
                    "project": pid,
                    "title": "Blocked",
                    "members": [
                        {
                            "name": "Flaky",
                            "role": "worker",
                            "task": "Attempt a transient task.",
                            "completion_criteria": "Write flaky.json.",
                            "outputs": ["flaky.json"],
                        }
                    ],
                },
            )
            assert unauth.status_code == 403

            launched = c.post(
                "/api/workspace/swarm-launch",
                headers=headers,
                json={
                    "project": pid,
                    "title": "Retryable swarm",
                    "strategy": "custom",
                    "wait": False,
                    "members": [
                        {
                            "name": "Flaky",
                            "role": "solver",
                            "task": "Fail once then succeed on retry.",
                            "completion_criteria": "Write flaky.json.",
                            "outputs": ["flaky.json"],
                            "timeout_seconds": 30,
                        }
                    ],
                },
            )
            assert launched.status_code == 200
            swarm_id = launched.json()["id"]

            wait_for(
                lambda: c.get("/api/workspace/swarm", params={"id": pid, "swarm": swarm_id})
                .json()["members"][0]["status"]
                == "failed",
                seconds=15,
            )

            # Retry the failed worker through HTTP control endpoint
            retried = c.post(
                "/api/workspace/swarm-control",
                headers=headers,
                json={
                    "project": pid,
                    "swarm": swarm_id,
                    "action": "retry_worker",
                    "worker_id": "Flaky",
                },
            )
            assert retried.status_code == 200
            wait_for(
                lambda: c.get("/api/workspace/swarm", params={"id": pid, "swarm": swarm_id})
                .json()["members"][0]["status"]
                == "succeeded",
                seconds=15,
            )

            # Dynamically add a second worker and wait for completion
            added = c.post(
                "/api/workspace/swarm-control",
                headers=headers,
                json={
                    "project": pid,
                    "swarm": swarm_id,
                    "action": "add_worker",
                    "member": {
                        "name": "Auditor",
                        "role": "verifier",
                        "task": "Audit Flaky's deliverable.",
                        "completion_criteria": "Write audit.json.",
                        "outputs": ["audit.json"],
                        "depends_on": ["Flaky"],
                        "timeout_seconds": 30,
                    },
                },
            )
            assert added.status_code == 200
            wait_for(
                lambda: c.get("/api/workspace/swarm", params={"id": pid, "swarm": swarm_id})
                .json()["counts"]["succeeded"]
                == 2,
                seconds=20,
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
