"""Backend, runtime, CLI, and HTTP tests for Codex-style v0.8 direct steering."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import httpx

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from conjecture_solver.web.steering import (
    consume_pending_steering,
    has_pending_steering,
    list_queued_steering,
    submit_steering,
)
from conjecture_solver.web.workspace import Workspace
from conjecture_solver.workspace_protocol import agent_type
from tests.test_workspace import wait_for


def _write_fake_codex(binary: Path) -> None:
    """Fake Codex CLI that supports initial turn + --resume steering with thread_id."""
    binary.write_text(
        f"#!{sys.executable}\n"
        + """
import json, os, sys, time
from pathlib import Path

args = sys.argv[1:]
prompt = args[-1]
state_file = Path("codex_runs.jsonl")
is_resume = "resume" in args

with state_file.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps({"resume": is_resume, "prompt": prompt}) + "\\n")

if not is_resume:
    print(json.dumps({"type": "thread.started", "thread_id": "thread-steer-001"}), flush=True)
    Path("first_turn_started").touch()
    # Stay active until supervisor sends steering interrupt or gate releases.
    deadline = time.time() + 15
    while time.time() < deadline:
        if Path(os.environ["SIMJECTURE_STEER_RELEASE"]).exists():
            break
        time.sleep(0.05)
    msg = {"type": "item.completed", "item": {"type": "agent_message", "text": "Original draft"}}
    print(json.dumps(msg), flush=True)
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 2}}), flush=True)
else:
    Path("steered_output.txt").write_text("Applied: " + prompt, encoding="utf-8")
    msg = {
        "type": "item.completed",
        "item": {"type": "agent_message", "text": "Pivoted per steering!"},
    }
    print(json.dumps(msg), flush=True)
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3}}), flush=True)
""",
        encoding="utf-8",
    )
    binary.chmod(0o755)


def test_builtin_protocol_agent_mid_turn_steering_and_final_answer_interception(tmp_path: Path):
    from smolagents.models import (
        ChatMessage,
        ChatMessageToolCall,
        ChatMessageToolCallFunction,
        MessageRole,
    )

    turn_dir = tmp_path / "turns/0001"
    turn_dir.mkdir(parents=True)
    seen_prompts: list[str] = []

    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        def generate(self, messages, **_kwargs):
            self.calls += 1
            rendered = json.dumps(messages, default=str)
            seen_prompts.append(rendered)
            if self.calls == 1:
                # Simulate user steering arriving mid-step while model tries to finish early.
                submit_steering(
                    tmp_path, "0001", "Wait: also verify n=64 convergence!", mode="steer"
                )
                return ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content="Done early.",
                    tool_calls=[
                        ChatMessageToolCall(
                            id="call_1",
                            type="function",
                            function=ChatMessageToolCallFunction(
                                name="final_answer",
                                arguments={"answer": "Premature draft"},
                            ),
                        )
                    ],
                    token_usage=SimpleNamespace(input_tokens=10, output_tokens=5),
                )
            return ChatMessage(
                role=MessageRole.ASSISTANT,
                content="Applying steering now.",
                tool_calls=[
                    ChatMessageToolCall(
                        id="call_2",
                        type="function",
                        function=ChatMessageToolCallFunction(
                            name="final_answer",
                            arguments={"answer": "Verified n=64 convergence!"},
                        ),
                    )
                ],
                token_usage=SimpleNamespace(input_tokens=12, output_tokens=6),
            )

    AgentClass = agent_type(steering_dir=turn_dir)
    agent = AgentClass(tools=[], model=FakeModel(), max_steps=4)
    answer = agent.run("Analyze convergence")
    assert "n=64" in str(answer)
    assert len(seen_prompts) == 2
    assert "Wait: also verify n=64 convergence!" in seen_prompts[1]
    assert not has_pending_steering(turn_dir)


def test_external_cli_instant_direct_steering_resumes_same_session(tmp_path: Path, monkeypatch):
    binary = tmp_path / "codex"
    _write_fake_codex(binary)
    release = tmp_path / "release"
    monkeypatch.setenv("SIMJECTURE_STEER_RELEASE", str(release))
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])

    ws = Workspace(tmp_path / ".workspace")
    project = ws.create({"name": "CLI Steering", "agent": {"backend": "codex", "model": "test"}})
    pid = project["id"]
    pdir = ws.directory(pid)

    ws.send(pid, {"message": "Run the initial numerical scan"})
    wait_for(lambda: (pdir / "files/first_turn_started").exists(), seconds=10)

    # Send instant mid-turn steering while the first CLI process is live!
    steered = ws.steer(
        pid, {"message": "Pivot to the adaptive Chebyshev basis instead", "mode": "steer"}
    )
    assert steered["mode"] == "steer"
    assert steered["steering"]["status"] == "pending"

    wait_for(lambda: not ws.project(pid)["running"], seconds=15)
    state = ws.project(pid)
    assistant = state["messages"][-1]
    assert assistant["status"] == "complete"
    assert "Pivoted per steering!" in assistant["content"]
    assert (pdir / "files/steered_output.txt").is_file()
    steered_text = (pdir / "files/steered_output.txt").read_text(encoding="utf-8")
    assert "adaptive Chebyshev basis" in steered_text

    # Verify both initial and resumed runs happened inside the same turn
    runs = [
        json.loads(line)
        for line in (pdir / "files/codex_runs.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(runs) == 2
    assert runs[0]["resume"] is False
    assert runs[1]["resume"] is True
    assert "adaptive Chebyshev basis" in runs[1]["prompt"]
    event_types = [ev.get("type") for ev in assistant.get("events", [])]
    assert "steer" in event_types
    assert "steer_applied" in event_types


def test_steering_queue_promote_cancel_and_http_auth(tmp_path: Path, monkeypatch):
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    monkeypatch.setattr(
        app.workspace, "default_agent", lambda: {"backend": "builtin", "model": "fixture"}
    )
    project = app.workspace.create({"name": "Queue HTTP"})
    pid = project["id"]
    pdir = app.workspace.directory(pid)
    turn_dir = pdir / "turns/0001"
    turn_dir.mkdir(parents=True)
    # Simulate an active live turn so queued items stay queued until promoted/cancelled.
    monkeypatch.setattr(app.workspace, "_active_live_turn", lambda _d: "0001")
    monkeypatch.setattr(app.workspace, "dispatch_all_queued_steering", lambda: None)

    # Queue two items, cancel the second, promote the first to direct steer
    q1 = submit_steering(pdir, "0001", "First follow-up", mode="queue")
    q2 = submit_steering(pdir, "0001", "Second follow-up", mode="queue")
    assert len(list_queued_steering(pdir)) == 2

    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False) as c:
            boot = c.get("/api/workspace/bootstrap").json()
            token = boot["control_token"]
            headers = {"X-Simjecture-Token": token}

            # Default steering mode can be tuned in settings and persists
            pref = c.post(
                "/api/workspace/steering-settings",
                headers=headers,
                json={"steering_mode": "interrupt"},
            )
            assert pref.status_code == 200
            assert pref.json()["steering_mode"] == "interrupt"
            assert app.workspace.settings()["steering_mode"] == "interrupt"

            # Unauthenticated POST must be rejected (403)
            unauth = c.post(
                "/api/workspace/steer",
                json={"project": pid, "message": "No token", "mode": "queue"},
            )
            assert unauth.status_code == 403

            # Cancel q2 via authenticated HTTP endpoint
            cancel_res = c.post(
                "/api/workspace/cancel-steer",
                headers=headers,
                json={"project": pid, "id": q2["id"]},
            )
            assert cancel_res.status_code == 200
            assert [item["id"] for item in list_queued_steering(pdir)] == [q1["id"]]

            # Promote q1 to direct mid-turn steering
            promote_res = c.post(
                "/api/workspace/promote-steer",
                headers=headers,
                json={"project": pid, "id": q1["id"], "mode": "steer"},
            )
            assert promote_res.status_code == 200
            assert list_queued_steering(pdir) == []
            claimed = consume_pending_steering(turn_dir)
            assert [item["message"] for item in claimed] == ["First follow-up"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
