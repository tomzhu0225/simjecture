"""Real provider protocol, file persistence and research handoff integration tests."""

import base64
import contextlib
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from conjecture_solver.web.workspace import Workspace, load, private_json


@pytest.fixture
def provider():
    """Deterministic API peer, exercising the real smolagents/OpenAI transport."""
    pytest.importorskip("smolagents")
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):  # noqa: N802
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            tools = {t["function"]["name"] for t in request.get("tools", [])}
            messages = request["messages"]
            context = json.dumps(messages)
            calls = [
                m
                for m in messages
                if m.get("role") == "assistant" and "Calling tools:" in json.dumps(m)
            ]
            if "connection_check" in tools:
                name, args = "connection_check", {"value": "connected"}
            elif "draft_study" in tools:
                step = len(calls)
                if step == 0:
                    name, args = (
                        "write_file",
                        {"path": "observations.txt", "content": "Saved research input.\n"},
                    )
                elif step == 1:
                    name, args = (
                        "terminal",
                        {"command": "printf 'calculation finished\\n' > calculation.txt"},
                    )
                elif step == 2:
                    name, args = (
                        "draft_study",
                        dict(
                            question="Euler preserves positivity for every positive time step.",
                            success_criteria="A recorded step with h=2 gives y1=-1 from y0=1.",
                            constraints="Ordinary Python. A negative result is valid.",
                            hours=0.05,
                            completion_policy="answer",
                        ),
                    )
                else:
                    name, args = (
                        "final_answer",
                        {"answer": "The calculation and editable study brief are ready."},
                    )
            elif "terminal" in tools:
                if len(calls) == 0:
                    command = (
                        "python - <<'PY'\nfrom pathlib import Path\nfrom lab import lab\n"
                        "import json, time\n"
                        "Path('euler.py').write_text(\"import json\\nfrom pathlib import Path\\n"
                        "Path('result.json').write_text(json.dumps({'h':2,'y0':1,'y1':-1}))\\n\")\n"
                        "experiment = lab.run('euler.py', outputs=['result.json'], key='h2')\n"
                        "for _ in range(60):\n"
                        "    status=lab.status()\n"
                        "    if status['experiments'][0]['status']=='succeeded': break\n"
                        "    time.sleep(.2)\n"
                        "print(lab.review([experiment['id']], "
                        "'At h=2 Euler gives y1=-1 from y0=1, a counterexample.', "
                        "disposition='falsified'))\nPY"
                    )
                    name, args = "terminal", {"command": command, "timeout_seconds": 30}
                else:
                    name, args = (
                        "final_answer",
                        {"answer": "Evidence recorded. Ready for independent review."},
                    )
            else:
                if "independent scientific reviewer" in context:
                    content = json.dumps(
                        dict(
                            claim_id="root",
                            decision="approved",
                            disposition="falsified",
                            rationale=(
                                "The recorded calculation at h=2 has a negative next step "
                                "and falsifies the universal claim."
                            ),
                            evidence_gaps=[],
                            next_test=None,
                        )
                    )
                else:
                    content = "A concise summary of the recorded work."
                body = dict(
                    id="review",
                    object="chat.completion",
                    model="fixture-model",
                    choices=[
                        dict(
                            index=0,
                            finish_reason="stop",
                            message=dict(role="assistant", content=content),
                        )
                    ],
                    usage=dict(prompt_tokens=10, completion_tokens=10, total_tokens=20),
                )
                self.respond(body)
                return
            body = dict(
                id="tool",
                object="chat.completion",
                model="fixture-model",
                choices=[
                    dict(
                        index=0,
                        finish_reason="tool_calls",
                        message=dict(
                            role="assistant",
                            content=None,
                            tool_calls=[
                                dict(
                                    id=f"call-{len(calls)}",
                                    type="function",
                                    function=dict(name=name, arguments=json.dumps(args)),
                                )
                            ],
                        ),
                    )
                ],
                usage=dict(prompt_tokens=10, completion_tokens=10, total_tokens=20),
            )
            self.respond(body)

        def respond(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1", requests
    server.shutdown()
    server.server_close()


def connect(workspace, url):
    workspace.save_settings(
        dict(backend="builtin", base_url=url, model="fixture-model", api_key="test-secret")
    )
    workspace.test_connection()


def wait_for(fn, seconds=30):
    deadline = time.time() + seconds
    while time.time() < deadline:
        result = fn()
        if result:
            return result
        time.sleep(0.15)
    raise AssertionError("Operation did not finish within its test deadline")


def test_real_agent_chat_persists_files_brief_and_secret_boundary(tmp_path, provider):
    url, requests = provider
    workspace = Workspace(tmp_path / ".workspace")
    connect(workspace, url)
    assert "test-secret" not in json.dumps(workspace.settings())
    assert workspace.settings_path.stat().st_mode & 0o777 == 0o600
    project = workspace.create({"name": "Euler positivity"})
    assert "euler-positivity" in project["id"]
    workspace.send(project["id"], {"message": "Calculate and prepare a counterexample study."})
    try:
        result = wait_for(
            lambda: (
                (p if not p["running"] else None)
                if (p := workspace.project(project["id"]))
                else None
            )
        )
        assert result["messages"][-1]["status"] == "complete", result["messages"]
        assert result["brief"]["completion_policy"] == "answer"
        files = Path(result["files_directory"])
        assert (files / "observations.txt").read_text() == "Saved research input.\n"
        assert (files / "calculation.txt").read_text() == "calculation finished\n"
        assert Workspace(workspace.root).project(project["id"])["messages"] == result["messages"]
        assert any("Saved observations.txt" in json.dumps(r) for r in requests)
    finally:
        workspace.stop(project["id"])


def test_autonomous_api_reuses_supervisor_and_accepts_negative_result(tmp_path, provider):
    from conjecture_solver.execution import probe_execution_backend

    if not probe_execution_backend("bubblewrap")["available"]:
        pytest.skip("Linux namespaces unavailable")
    url, requests = provider
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    workspace = app.workspace
    connect(workspace, url)
    p = workspace.create({"name": "Euler positivity"})
    workspace.upload(
        p["id"], dict(name="input.txt", data=base64.b64encode(b"original input").decode())
    )
    workspace.save_brief(
        p["id"],
        dict(
            question="Euler preserves positivity for every positive step.",
            success_criteria="At h=2 the numerical next step is negative.",
            constraints="Ordinary Python",
            hours=0.05,
            completion_policy="answer",
        ),
    )
    launched = workspace.launch(p["id"], {"request_key": "one"}, app)
    root = Path(launched["path"])
    assert root.parent.parent == workspace.directory(p["id"])
    assert root.name.startswith("001-euler-")
    assert "api_key" not in (root / "study-launch.json").read_text()
    assert (root / "research/project_inputs/input.txt").read_text() == "original input"
    assert workspace.launch(p["id"], {"request_key": "one"}, app) == launched
    try:
        result = wait_for(
            lambda: (
                (r if r.get("status") in {"completed", "paused_external_error"} else None)
                if (r := load(root / "supervisor/state.json"))
                else None
            ),
            seconds=65,
        )
        assert result["status"] == "completed", (result, (root / "controller.log").read_text())
        report = load(root / "research_report.json")
        assert report["completed"] and report["reviews"][0]["verdict"]["disposition"] == "falsified"
        assert list((root / "experiments").glob("*/workspace/result.json"))
        assert "Scientific results" in (workspace.directory(p["id"]) / "README.md").read_text()
        app2 = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
        assert app2.registry.resolve(launched["campaign"]) == root
        judges = [
            r for r in requests if "independent scientific reviewer" in json.dumps(r["messages"])
        ]
        assert judges and all(not r.get("tools") for r in judges)
    finally:
        with contextlib.suppress(Exception):
            app.control(launched["campaign"], "cancel")


def test_completion_policy_is_immutable_and_legacy_remains_repair(tmp_path):
    root = tmp_path / "research"
    service = ResearchService.create(root, "A bounded question", completion_policy="answer")
    put(
        root / "reviews/accepted.json",
        dict(
            id="accepted",
            claim="root",
            experiments=[],
            status="accepted",
            verdict=dict(decision="approved", disposition="falsified"),
        ),
    )
    assert service.status()["completed"]
    with pytest.raises(ValueError, match="immutable"):
        ResearchService.create(root, "A bounded question", completion_policy="repair")
    manifest = load(root / "research.json")
    manifest.pop("completion_policy")
    put(root / "research.json", manifest)
    assert not ResearchService(root).status()["completed"]


def test_workspace_http_blocks_mutations_readonly_and_path_escape(tmp_path):
    app = SimjectureWebApplication(
        runs_root=tmp_path, scan_roots=(tmp_path,), allow_mutations=False
    )
    project = app.workspace.create({"name": "Permanent files"})
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
            assert "What would you like" in client.get("/").text
            boot = client.get("/api/workspace/bootstrap").json()
            assert client.post("/api/workspace/projects", json={"name": "bad"}).status_code == 403
            response = client.post(
                "/api/workspace/projects",
                headers={"X-Simjecture-Token": boot["control_token"]},
                json={"name": "bad"},
            )
            assert response.status_code == 403
            response = client.get(
                "/api/workspace/file", params={"id": project["id"], "path": "../../outside.txt"}
            )
            assert response.status_code == 400
    finally:
        server.shutdown()
        server.server_close()


def test_upload_never_overwrites_existing_inputs(tmp_path):
    workspace = Workspace(tmp_path / ".workspace")
    p = workspace.create({"name": "Input provenance"})
    payload = dict(name="input.txt", data=base64.b64encode(b"original").decode())
    workspace.upload(p["id"], payload)
    with pytest.raises(FileExistsError):
        workspace.upload(p["id"], payload)
    with pytest.raises(ValueError):
        workspace.upload(p["id"], payload | {"name": "../escape"})


def test_connection_rotation_does_not_reuse_key_for_new_endpoint(tmp_path):
    workspace = Workspace(tmp_path / ".workspace")
    private_json(workspace.settings_path, dict(base_url="https://a.example/v1", api_key="secret"))
    workspace.save_settings(dict(model="test", base_url="https://b.example/v1"))
    assert not workspace.settings()["has_key"]


def test_detected_cli_uses_existing_transport_and_persists_brief(tmp_path, monkeypatch):
    binary = tmp_path / "bin"
    binary.mkdir()
    cli = binary / "codex"
    brief = dict(
        question="A clear testable claim",
        success_criteria="A recorded counterexample",
        constraints="Ordinary Python",
        hours=1,
        completion_policy="answer",
    )
    cli.write_text(
        f"#!{sys.executable}\nimport json,sys\nfrom pathlib import Path\n"
        "if '--version' in sys.argv:\n    print('fixture-cli 1.0');raise SystemExit(0)\n"
        "Path('cli-result.txt').write_text('Permanent CLI output')\n"
        f"Path('STUDY_BRIEF.json').write_text({json.dumps(brief)!r})\n"
        "print(json.dumps({'type':'item.completed','item':{'type':'agent_message',"
        "'text':'CLI preparation completed.'}}))\n"
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'output_tokens':3}}))\n"
    )
    cli.chmod(0o700)
    monkeypatch.setenv("PATH", str(binary) + os.pathsep + os.environ["PATH"])
    workspace = Workspace(tmp_path / "runs/.workspace")
    assert next(c for c in workspace.settings()["clis"] if c["id"] == "codex")["path"] == str(cli)
    workspace.save_settings(dict(backend="codex", model="fixture-cli"))
    workspace.test_connection()
    project = workspace.create({"name": "CLI project"})
    workspace.send(project["id"], {"message": "Prepare my experiment"})
    try:
        result = wait_for(
            lambda: (
                (p if not p["running"] else None)
                if (p := workspace.project(project["id"]))
                else None
            )
        )
        assert result["messages"][-1]["content"] == "CLI preparation completed."
        assert result["brief"] == brief
        assert (Path(result["files_directory"]) / "cli-result.txt").is_file()
        assert (
            "CLI preparation completed."
            in (workspace.directory(project["id"]) / "CONVERSATION.md").read_text()
        )
    finally:
        workspace.stop(project["id"])


def test_terminal_timeout_stops_descendant_commands(tmp_path):
    pytest.importorskip("smolagents")
    from conjecture_solver.workspace_agent import agent_tools

    terminal = next(t for t in agent_tools(tmp_path, time.time() + 10) if t.name == "terminal")
    result = terminal.forward("sleep 60 & echo $! > child.pid; wait", timeout_seconds=1)
    assert "timed out" in result
    child_pid = int((tmp_path / "child.pid").read_text())
    stat = Path(f"/proc/{child_pid}/stat")
    assert not stat.exists() or stat.read_text().split(") ")[1].split()[0] in {"Z", "X"}
