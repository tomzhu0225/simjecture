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

        def do_GET(self):  # noqa: N802
            self.respond({"data": [{"id": "fixture-model"}, {"id": "fixture-alternate"}]})

        def do_POST(self):  # noqa: N802
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(request)
            deepseek = request.get("model") == "deepseek-flash"
            if deepseek and request.get("tools"):
                if request.get("tool_choice") not in (None, "auto", "none"):
                    self.respond(
                        {"error": {"message": "Thinking mode does not support this tool_choice"}},
                        status=400,
                    )
                    return
                if any(
                    m["role"] == "assistant" and not m.get("reasoning_content")
                    for m in request["messages"]
                ):
                    self.respond({"error": {"message": "Missing reasoning_content"}}, status=400)
                    return
            tools = {t["function"]["name"] for t in request.get("tools", [])}
            messages = request["messages"]
            context = json.dumps(messages)
            plain = "\n".join(
                m.get("content", "")
                if isinstance(m.get("content"), str)
                else "\n".join(c.get("text", "") for c in m.get("content") or [])
                for m in messages
            )
            task_indices = [
                i
                for i, m in enumerate(messages)
                if "CURRENT USER REQUEST:" in json.dumps(m.get("content", ""))
            ]
            current_messages = messages[task_indices[-1] :] if task_indices else messages
            calls = [
                m
                for m in current_messages
                if m.get("role") == "assistant" and "Calling tools:" in json.dumps(m)
            ]
            if "connection_check" in tools:
                name, args = "connection_check", {"value": "connected"}
            elif deepseek and plain.rsplit("CURRENT USER REQUEST:\n", 1)[-1].startswith("Hello"):
                name, args = "final_answer", {"answer": "Hello!"}
            elif "draft_study" in tools and (
                plain.rsplit("CURRENT USER REQUEST:\n", 1)[-1].startswith("Grill me to prepare")
            ):
                name, args = (
                    "final_answer",
                    {"answer": "What question should we test, and what time budget should I use?"},
                )
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
            if deepseek:
                message = body["choices"][0]["message"]
                message["reasoning_content"] = f"provider-private-reasoning-fixture-{len(requests)}"
                checkpoint = "COMPLETION CHECK:" in json.dumps(current_messages[-2:])
                if (
                    not calls
                    and plain.rsplit("CURRENT USER REQUEST:\n", 1)[-1].startswith("Progress test")
                    and not checkpoint
                ):
                    message["content"] = "Let me inspect and write the calculation now."
                    message.pop("tool_calls")
                    body["choices"][0]["finish_reason"] = "stop"
                elif name == "final_answer" and not checkpoint:
                    message["content"] = args["answer"]
                    message.pop("tool_calls")
                    body["choices"][0]["finish_reason"] = "stop"
            self.respond(body)

        def respond(self, value, status=200):
            body = json.dumps(value).encode()
            self.send_response(status)
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
        assert any("AVAILABLE SIMJECTURE RESEARCH SKILLS" in json.dumps(r) for r in requests)
        assert any("flash-mhd/SKILL.md" in json.dumps(r) for r in requests)
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
            assert "What are we investigating?" in client.get("/").text
            boot = client.get("/api/workspace/bootstrap").json()
            assert client.post("/api/workspace/projects", json={"name": "bad"}).status_code == 403
            response = client.post(
                "/api/workspace/projects",
                headers={"X-Simjecture-Token": boot["control_token"]},
                json={"name": "bad"},
            )
            assert response.status_code == 403
            assert response.headers["connection"] == "close"
            response = client.post(
                "/api/workspace/delete-project",
                headers={"X-Simjecture-Token": boot["control_token"]},
                json={"project": project["id"], "confirm": project["id"]},
            )
            assert response.status_code == 403
            assert app.workspace.directory(project["id"]).exists()
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
        "Path('cli-argv.json').write_text(json.dumps(sys.argv))\n"
        f"Path('STUDY_BRIEF.json').write_text({json.dumps(brief)!r})\n"
        "print(json.dumps({'type':'item.completed','item':{'type':'agent_message',"
        "'text':'CLI preparation completed.'}}))\n"
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':2,'output_tokens':3}}))\n"
    )
    cli.chmod(0o700)
    monkeypatch.setenv("PATH", str(binary) + os.pathsep + os.environ["PATH"])
    workspace = Workspace(tmp_path / "runs/.workspace")
    assert next(c for c in workspace.settings()["clis"] if c["id"] == "codex")["path"] == str(cli)
    project = workspace.create({"name": "CLI project"})
    workspace.select_agent(
        project["id"], dict(backend="codex", model="fixture-cli", reasoning_effort="high")
    )
    assert not workspace.settings_path.exists()
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
        assert result["brief"] == brief | {"capability_directory": ""}
        assert (Path(result["files_directory"]) / "cli-result.txt").is_file()
        argv = load(Path(result["files_directory"]) / "cli-argv.json")
        assert 'model_reasoning_effort="high"' in argv
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


def test_conversation_agents_are_independent_and_api_credentials_are_optional(
    tmp_path, monkeypatch
):
    import conjecture_solver.web.workspace as module

    monkeypatch.setattr(
        module.shutil, "which", lambda name: "/bin/true" if name == "grok" else None
    )
    workspace = Workspace(tmp_path / ".workspace")
    first = workspace.create({"name": "First conversation"})
    second = workspace.create({"name": "Second conversation"})
    assert not workspace.settings_path.exists()
    selected = workspace.select_agent(
        first["id"], dict(backend="grok", model="grok-4.7", reasoning_effort="high")
    )
    assert (
        workspace.project_connection(workspace.project(first["id"]))["reasoning_effort"] == "high"
    )
    workspace.select_agent(second["id"], dict(backend="grok", model="grok-4.6"))
    assert workspace.project(first["id"])["agent"] == selected
    assert workspace.project(second["id"])["agent"]["model"] == "grok-4.6"
    workspace.save_api(dict(base_url="https://example.org/v1", api_key="private-test-key"))
    assert workspace.project(first["id"])["agent"] == selected
    assert "private-test-key" not in json.dumps(workspace.settings())
    assert "private-test-key" not in json.dumps(workspace.project(first["id"]))
    with pytest.raises(ValueError, match="reasoning effort separately"):
        workspace.select_agent(first["id"], dict(backend="grok", model="grok-4.7 high"))


def test_api_model_discovery_uses_saved_endpoint_without_global_model(tmp_path, provider):
    url, _ = provider
    workspace = Workspace(tmp_path / ".workspace")
    workspace.save_api(dict(base_url=url, api_key="test-secret"))
    assert not workspace.settings_path.exists()
    assert {m["id"] for m in workspace.models("builtin")["models"]} == {
        "fixture-model",
        "fixture-alternate",
    }
    project = workspace.create({"name": "API project"})
    workspace.select_agent(project["id"], dict(backend="builtin", model="fixture-alternate"))
    assert (
        workspace.project_connection(workspace.project(project["id"]))["model"]
        == "fixture-alternate"
    )


def test_grill_and_draft_use_agent_preparation_not_empty_forms(tmp_path, monkeypatch):
    workspace = Workspace(tmp_path / ".workspace")
    captured = []
    monkeypatch.setattr(workspace, "send", lambda identifier, payload: captured.append(payload))
    workspace.prepare("project", {"approach": "interview"})
    assert captured[-1]["message"] == "Grill me to prepare an autonomous investigation."
    assert "three consequential questions" in captured[-1]["preparation"]
    workspace.prepare("project", {"approach": "draft"})
    assert "one-hour budget" in captured[-1]["preparation"]
    assert "rather than inventing" in captured[-1]["preparation"]
    assert "draft_study" not in captured[-1]["message"]


def test_native_reasoning_effort_is_in_frozen_launch_contract(tmp_path, monkeypatch):
    import conjecture_solver.execution as execution
    import conjecture_solver.study_launch as launch
    from conjecture_solver.study_launch import NativeStudyRequest, materialize_native

    monkeypatch.setattr(launch.shutil, "which", lambda name: "/bin/true")
    monkeypatch.setattr(execution, "require_execution_backend", lambda _: {"available": True})
    request = NativeStudyRequest(
        hypothesis="An explicit bounded claim.",
        output_directory=str(tmp_path / "study"),
        campaign_id="study-test",
        engine="native",
        backend="grok",
        model="grok-4.7",
        reasoning_effort="high",
    )
    plan = materialize_native(request)
    assert plan.argv[plan.argv.index("--reasoning-effort") + 1] == "high"
    assert load(tmp_path / "study/study-launch.json")["request"]["reasoning_effort"] == "high"
    with pytest.raises(ValueError, match="differs"):
        materialize_native(request.model_copy(update={"reasoning_effort": "low"}), resume=True)


def test_invalid_legacy_pair_is_not_a_default_or_an_agy_model(tmp_path, monkeypatch):
    from types import SimpleNamespace

    import conjecture_solver.web.workspace as module

    monkeypatch.setattr(module.shutil, "which", lambda name: "/bin/true")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(
            returncode=0,
            stdout=(
                "Fetching available models...\ngemini-test\tGemini Test\nclaude-test\tClaude Test\n"
            ),
        ),
    )
    workspace = Workspace(tmp_path / ".workspace")
    private_json(workspace.settings_path, dict(backend="agy", model="grok-4.7"))
    assert workspace.default_agent()["backend"] != "agy"
    models = workspace.models("agy")
    assert [m["id"] for m in models["models"]] == ["gemini-test", "claude-test"]
    with pytest.raises(ValueError, match="different agent"):
        workspace.select_agent(None, dict(backend="agy", model="grok-4.7"))
    selected = workspace.select_agent(None, dict(backend="grok", model="grok-4.7"))
    assert workspace.default_agent() == selected
    project = workspace.create({"name": "Preserve the conversation"})
    path = workspace.directory(project["id"]) / "project.json"
    record = load(path)
    record["agent"] = dict(backend="agy", model="grok-4.7", reasoning_effort="")
    put(path, record)
    assert workspace.project(project["id"])["agent"] == dict(
        backend="agy", model="", reasoning_effort=""
    )


def test_flash_inventory_finds_existing_application_variants(tmp_path, monkeypatch):
    import conjecture_solver.deployment as deployment
    import conjecture_solver.web.workspace as module
    from conjecture_solver.web.inventory import discover_installed

    monkeypatch.setattr(deployment, "resolve_project_root", lambda *a: tmp_path)
    (tmp_path / "capabilities").mkdir()
    configs = []
    for revision in (1, 2):
        runtime = tmp_path / ".runtime" / f"flash-driven-sheet-r{revision}"
        (runtime / "bin").mkdir(parents=True)
        binary = runtime / "bin/flash4"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o700)
        directory = tmp_path / ".private" / "existing-study" / f"capabilities-r{revision}"
        directory.mkdir(parents=True)
        path = directory / "flash-driven-sheet.json"
        config = dict(
            runtime_root=str(runtime),
            executable="bin/flash4",
            manifest=dict(
                name="flash-driven-sheet",
                version=f"4.8.local.{revision}",
                description="Driven-sheet MHD; commissioning only",
                skill="flash-mhd",
                executable_kind="application",
            ),
        )
        put(path, config)
        configs.append(path)
    installed = discover_installed(tmp_path)
    assert len(installed) == 2
    assert {v["path"] for v in installed} == {str(p) for p in configs}
    workspace = Workspace(tmp_path / "artifacts/.workspace")
    flash = next(t for t in workspace.catalogue() if t["id"] == "flash")
    assert flash["installed"] and flash["readiness"] == "unchecked"
    assert len(flash["variants"]) == 2
    assert flash["path"] == str(configs[1])
    commands = []
    monkeypatch.setattr(module, "spawn", lambda argv, *args: commands.append(argv) or {})
    workspace.start_install(dict(name="flash", action="check"))
    assert commands[0][commands[0].index("--descriptor") + 1] == str(configs[1])
    assert "--source" not in commands[0]


def test_inventory_context_is_compact_and_excludes_logs(tmp_path, monkeypatch):
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    monkeypatch.setattr(
        app.workspace,
        "catalogue",
        lambda: [
            dict(
                id="flash",
                name="FLASH",
                installed=True,
                registered=True,
                readiness="unchecked",
                log="large private installation log",
                report={"unrelated": "details"},
                variants=[dict(label="FLASH build", runtime="/runtime/flash")] * 50,
            )
        ],
    )
    context = app.workspace.inventory_context()
    card = json.loads(context)[0]
    assert card["installed"] and card["installation_count"] == 50
    assert len(card["installations"]) == 3
    assert "installation log" not in context
    assert "unrelated" not in context


def test_delete_conversation_removes_owned_folders_only(tmp_path):
    w = Workspace(tmp_path / ".workspace")
    p = w.create({"name": "Disposable conversation"})
    other = w.create({"name": "Keep conversation"})
    root = w.directory(p["id"])
    (root / "files/result.txt").write_text("saved result")
    (root / "studies/example").mkdir(parents=True)
    outside = tmp_path / "shared-tool"
    outside.mkdir()
    (outside / "keep.txt").write_text("shared")
    (root / "files/shared-link").symlink_to(outside, target_is_directory=True)
    credentials = w.root / "turn-connections" / (p["id"] + "-123.json")
    credentials.parent.mkdir()
    credentials.write_text("{}")
    with pytest.raises(ValueError, match="Confirm"):
        w.delete_project(p["id"], {})
    assert root.exists()
    w.delete_project(p["id"], {"confirm": p["id"]})
    assert not root.exists() and not credentials.exists()
    assert w.directory(other["id"]).exists() and (outside / "keep.txt").exists()
    assert len(w.projects()) == 1
    with pytest.raises(ValueError):
        w.delete_project("../shared-tool", {"confirm": "../shared-tool"})


def test_delete_refuses_live_owner_and_linked_project(tmp_path):
    import os

    from conjecture_solver.mvp_launch import read_process_identity

    w = Workspace(tmp_path / ".workspace")
    p = w.create({"name": "Active"})
    root = w.directory(p["id"])
    turn = root / "turns/123"
    turn.mkdir()
    (turn / "process.json").write_text(read_process_identity(os.getpid()).model_dump_json())
    with pytest.raises(ValueError, match="Stop active"):
        w.delete_project(p["id"], {"confirm": p["id"]})
    linked = w.projects_root / "linked"
    linked.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="linked"):
        w.delete_project("linked", {"confirm": "linked"})
    assert root.exists()


def test_delete_refuses_live_autonomous_supervisor(tmp_path):
    import subprocess

    from conjecture_solver.mvp_launch import read_process_identity, write_supervisor_record

    w = Workspace(tmp_path / ".workspace")
    p = w.create({"name": "Active study"})
    study = w.directory(p["id"]) / "studies/001-study"
    study.mkdir(parents=True)
    child = subprocess.Popen(["sleep", "30"], cwd=study)
    try:
        write_supervisor_record(study, read_process_identity(child.pid, run_directory=study))
        with pytest.raises(ValueError, match="Stop active autonomous"):
            w.delete_project(p["id"], {"confirm": p["id"]})
        assert study.exists()
    finally:
        child.terminate()
        child.wait()


def test_progress_updates_are_durable_and_visible_in_conversation(tmp_path):
    w = Workspace(tmp_path / ".workspace")
    p = w.create({"name": "Progress"})
    root = w.directory(p["id"])
    turn = root / "turns/123"
    turn.mkdir()
    put(
        turn / "request.json", dict(message="Run a pilot", agent=p["agent"], created_at=time.time())
    )
    saved = load(root / "project.json")
    saved["active_turn"] = "123"
    put(root / "project.json", saved)
    w.progress_update(p["id"], "Inputs are prepared; next I will run a short pilot.")
    result = w.project(p["id"])
    assert result["messages"][-1]["progress"].startswith("Inputs are prepared")
    assert result["messages"][-1]["last_activity_at"] > 0


def test_uninstalled_tool_keeps_failed_install_report(tmp_path):
    workspace = Workspace(tmp_path / ".workspace")
    report = {"ready": False, "error": "Package download failed"}
    (workspace.root / "tools/warpx-cpu").mkdir(parents=True)
    put(workspace.root / "tools/warpx-cpu/result.json", report)
    card = next(c for c in workspace.catalogue() if c["id"] == "warpx-cpu")
    assert card["report"] == report
    assert card["readiness"] == "failed"


def test_partial_eos_runtime_is_not_listed_as_installed(tmp_path, monkeypatch):
    monkeypatch.setattr("conjecture_solver.deployment.resolve_project_root", lambda *a: tmp_path)
    caps = tmp_path / "capabilities"
    caps.mkdir()
    runtime = tmp_path / ".runtime/eos"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "bin/python").write_text("#!/bin/sh\nexit 0\n")
    (runtime / "bin/python").chmod(0o755)
    put(
        caps / "singularity-eos-fixture.json",
        dict(
            runtime_root="../.runtime/eos",
            executable="bin/python",
            identity_files=["bin/eos-query", "share/build-record.json"],
            manifest=dict(
                name="singularity-eos-fixture",
                version="1",
                description="EOS fixture",
                skill="eos",
                executable_kind="python-test",
            ),
        ),
    )
    workspace = Workspace(tmp_path / "artifacts/.workspace")
    card = next(c for c in workspace.catalogue() if c["id"] == "singularity-eos")
    assert not card["installed"] and not card["registered"] and not card["variants"]
    (runtime / "bin/eos-query").write_text("binary")
    (runtime / "share").mkdir()
    put(runtime / "share/build-record.json", {"version": "fixture"})
    card = next(c for c in workspace.catalogue() if c["id"] == "singularity-eos")
    assert card["installed"] and card["registered"]


def test_long_build_command_is_monitored_after_tool_returns(tmp_path):
    pytest.importorskip("smolagents")
    from conjecture_solver.workspace_agent import agent_tools

    workspace = Workspace(tmp_path / ".workspace")
    project = workspace.create({"name": "Build lifecycle"})
    root = Path(project["files_directory"])
    tool = next(
        t
        for t in agent_tools(root, float("inf"), project["id"], workspace)
        if t.name == "run_command"
    )
    result = json.loads(
        tool.forward("Install fixture", "sleep 1; echo installed > installed.txt", 10)
    )
    job = wait_for(
        lambda: (
            (j if j["status"] == "succeeded" else None)
            if (j := workspace.simulation(project["id"], result["id"]))
            else None
        )
    )
    assert job["kind"] == "command"
    assert (root / "installed.txt").read_text().strip() == "installed"
    failure = json.loads(tool.forward("Failed build", "false | cat", 10))
    failed = wait_for(
        lambda: (
            (j if j["status"] == "failed" else None)
            if (j := workspace.simulation(project["id"], failure["id"]))
            else None
        )
    )
    assert failed["returncode"] != 0


def test_registered_tool_can_be_checked_from_catalogue(tmp_path, monkeypatch):
    import conjecture_solver.web.workspace as module

    workspace = Workspace(tmp_path / ".workspace")
    descriptors = tmp_path / "capabilities"
    descriptors.mkdir()
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    executable = runtime / "runner"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    template = json.loads((Path(__file__).parents[1] / "capabilities/m-aneos-1.0.json").read_text())
    template.update(runtime_root=str(runtime), executable="runner", identity_files=[])
    (descriptors / "test.json").write_text(json.dumps(template))
    record = workspace.register_tool({"name": "Custom solver", "path": str(descriptors)})
    commands = []
    monkeypatch.setattr(module, "spawn", lambda command, *args: commands.append(command) or {})
    workspace.start_install({"name": record["id"], "action": "check"})
    assert commands[0][-2:] == ["--descriptor", str(descriptors)]
    put(workspace.root / "tools" / record["id"] / "result.json", {"ready": True})
    card = next(t for t in workspace.catalogue() if t["id"] == record["id"])
    assert card["readiness"] == "passed"
    assert card["state"] == "tested"
    template["environment"]["MANEOS_QUERY"] = str(runtime / "runner")
    (descriptors / "test.json").write_text(json.dumps(template))
    with pytest.raises(ValueError, match="host runtime path"):
        workspace.register_tool({"name": "Wrong mapping", "path": str(descriptors)})
