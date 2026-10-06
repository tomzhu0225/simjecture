"""Execution purpose stays independent of output files and artifact provenance."""

import json

import pytest

from conjecture_solver.public.lab import HostedLab, agent_tools
from conjecture_solver.research_service import ResearchService, put, sha
from tests.test_public_workspace import app as workspace_app
from tests.test_public_workspace import project, session


@pytest.fixture
def app(tmp_path):
    return workspace_app.__wrapped__(tmp_path)


def frozen_run(service, identifier, request, result=None, status="succeeded"):
    workspace = service.root / "experiments" / identifier / "workspace"
    workspace.mkdir(parents=True)
    general = request.get("tool") is None
    put(workspace / ("lab-request.json" if general else "native-case.json"), request)
    artifacts = {}
    if result is not None:
        put(workspace / "result.json", result)
        artifacts["result.json"] = {"sha256": sha(workspace / "result.json")}
    for name in request.get("outputs", []):
        path = workspace / "generated" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("recorded output")
        artifacts["generated/" + name] = {"sha256": sha(path)}
    put(
        service.root / "experiments" / (identifier + ".json"),
        {"id": identifier, "status": status, "artifacts": artifacts},
    )


@pytest.mark.parametrize(
    "case,result,status,expected",
    [
        ({"outputs": ["plot.png"]}, {"tool": "project-command"}, "succeeded", "command"),
        ({"outputs": ["plot.png"]}, {"tool": "project-command"}, "failed", "command"),
        ({"outputs": []}, {"tool": "project-command"}, "succeeded", "command"),
        ({"outputs": ["plot.png"]}, None, "running", "command"),
        (
            {"outputs": ["fields.h5"], "kind": "simulation"},
            {"tool": "project-command"},
            "succeeded",
            "simulation",
        ),
        (
            {"outputs": [], "kind": "simulation"},
            {"tool": "project-command"},
            "failed",
            "simulation",
        ),
        (
            {"tool": "flash-2d"},
            {"tool": "flash-2d"},
            "succeeded",
            "simulation",
        ),
        ({"tool": "flash-2d"}, None, "running", "simulation"),
    ],
)
def test_hosted_categories_do_not_depend_on_declared_outputs(app, case, result, status, expected):
    client = session(app)
    p = project(client)
    job = client.post(
        "/api/workspace/message", json={"project": p["id"], "message": "Run controls"}
    ).json()
    service = ResearchService.create(
        app.state.store.root / "jobs" / job["id"] / "study", "A numerical campaign"
    )
    frozen_run(service, "exp_check", case, result, status)
    original = service.root / "experiments/exp_check/workspace/lab-request.json"
    before = original.read_bytes() if original.exists() else None
    row = client.get("/api/workspace/project?id=" + p["id"]).json()["simulations"][0]
    assert row["kind"] == expected and row["status"] == status
    assert row["file_provenance"] == "verified"
    assert all(f["role"] == "output" for f in row["files"])
    assert not before or original.read_bytes() == before  # No historical receipt rewrite.


def test_tool_schema_accepts_explicit_kind_and_rejects_invalid_values(app, monkeypatch):
    settings = app.state.store.root / "settings.json"
    settings.write_text(json.dumps({"executor_qualified": True, "executor_socket": "/no-rpc"}))
    client = session(app)
    p = project(client)
    job = client.post(
        "/api/workspace/message", json={"project": p["id"], "message": "Run controls"}
    ).json()
    service = ResearchService.create(
        app.state.store.root / "jobs" / job["id"] / "study", "A numerical campaign"
    )
    job = app.state.store.job(job["id"])
    command = next(t for t in agent_tools(app.state.store, job, service) if t.name == "run_command")
    assert command.inputs["kind"]["nullable"] is True
    calls = []
    monkeypatch.setattr(HostedLab, "run", lambda self, *args: calls.append(args) or {})
    command(command="python solve.py", outputs=["fields.h5"], kind="simulation")
    command(command="python plot.py", outputs=["plot.png"])
    assert calls[0][-1] == "simulation" and calls[1][-1] == "command"
    monkeypatch.undo()
    monkeypatch.setattr("conjecture_solver.public.worker.check_running", lambda *args: None)
    with pytest.raises(ValueError, match="command or simulation"):
        HostedLab(app.state.store, job, service).run("true", [], kind="plot")


def test_browser_custom_setup_and_isolated_command_outputs(app):
    import re
    import socket
    import threading
    import time

    import uvicorn

    playwright = pytest.importorskip("playwright.sync_api")
    store = app.state.store
    registry = store.root / "tools.json"
    put(
        registry,
        {
            "tools": [
                {
                    "id": "flash-2d",
                    "name": "FLASH 2D · starter vortex",
                    "family": "flash",
                    "scope": "Starter MHD example",
                    "qualification": "Test fixture only",
                    "qualified": True,
                }
            ]
        },
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    put(
        store.root / "settings.json",
        {"public_origin": origin, "executor_qualified": True, "tools_registry": str(registry)},
    )
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    errors = []
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin)
            page.locator(".example").nth(2).click()
            playwright.expect(page.locator("#first-request")).to_have_value(
                re.compile(r"10-minute autonomous research.*within 1%")
            )
            playwright.expect(page.locator(".home-modes")).to_contain_text("Interactive")
            playwright.expect(page.locator(".home-modes")).to_contain_text("independent review")
            assert page.locator(".setup-strip").count() == 0
            page.locator('[data-view="benchmarks"]').click()
            page.locator("#benchmark-leaderboard tbody tr").first.wait_for()
            playwright.expect(page.locator("#benchmark-ranked-charts")).to_be_visible()
            playwright.expect(
                page.locator("#benchmark-time-bars .benchmark-bar-row").first
            ).to_be_visible()
            playwright.expect(
                page.locator("#benchmark-cost-bars .benchmark-bar-row").first
            ).to_be_visible()
            playwright.expect(page.locator("#benchmark-tradeoff svg")).to_be_visible()
            playwright.expect(page.locator("#benchmark-run")).to_be_disabled()
            playwright.expect(page.locator("#benchmark-import")).to_be_disabled()
            assert page.locator('#benchmark-source option[value="local"]').evaluate(
                "o => o.disabled"
            )
            page.locator("#benchmark-task-tabs").get_by_role(
                "button", name="Radiation energy accounting"
            ).click()
            playwright.expect(page.locator("#benchmark-task-brief")).to_contain_text("CSV")
            with page.expect_download() as result:
                page.locator("#benchmark-export").click()
            assert result.value.suggested_filename.startswith("simjecture-official-results-")
            page.locator("#benchmark-your-work > summary").click()
            playwright.expect(page.locator("#benchmark-tasks button").first).to_be_disabled()
            page.get_by_role("button", name="Research tools", exact=True).click()
            assert page.locator(".research-tools-intro").count() == 0
            card = page.locator('[data-tool="flash"]')
            choice = card.get_by_label("FLASH 4.8 study setup")
            assert choice.input_value() == "custom-study"
            assert card.locator('optgroup[label="Starter presets"]').count() == 1
            assert "custom applications" in card.inner_text()
            choice.select_option("flash-2d")
            playwright.expect(
                card.get_by_role("button", name="Run preset", exact=True)
            ).to_be_visible()
            choice.select_option("custom-study")
            card.get_by_role("button", name="Prepare in chat", exact=True).click()
            playwright.expect(page.locator("#chat-input")).to_have_value(re.compile("custom study"))
            playwright.expect(page.locator('#study-navigation [aria-current="page"]')).to_have_text(
                "Conversation"
            )
            assert page.locator("#study-navigation ul").count() == 1
            assert page.locator("#study-navigation li").nth(1).evaluate(
                "e => getComputedStyle(e, '::before').content"
            ) in ("none", "normal")
            cookie = next(
                c["value"] for c in page.context.cookies() if c["name"] == "simjecture_visitor"
            )
            assert store.jobs(store.visitor(cookie)["id"]) == []  # Drafts do not spend model quota.
            project_id = page.evaluate("state.project.id")
            job = page.evaluate(
                "async id => api('message', {project: id, message: 'Run numerical controls'})",
                project_id,
            )
            service = ResearchService.create(
                store.root / "jobs" / job["id"] / "study", "A numerical campaign"
            )
            frozen_run(
                service,
                "exp_solver",
                {"tool": "flash-2d", "name": "Actual solver run"},
                {"tool": "flash-2d", "name": "Actual solver run"},
            )
            frozen_run(
                service,
                "exp_analysis",
                {"name": "Analyze fields", "outputs": ["diags.json"]},
                {"tool": "project-command", "name": "Analyze fields"},
            )
            page.evaluate("async id => openProject(id)", project_id)
            playwright.expect(page.locator("#simulation-count")).to_have_text("1")
            playwright.expect(page.locator("#command-count")).to_have_text("1")
            playwright.expect(page.locator("#sidebar-run-list")).not_to_contain_text(
                "Analyze fields"
            )
            page.locator('wa-tab[panel="commands"]').click()
            page.locator("#command-list a").click()
            playwright.expect(page.locator("#command-detail h4")).to_have_text("Command outputs")
            playwright.expect(page.locator("#command-detail")).to_contain_text("isolated workspace")
            assert page.locator("#command-detail .run-shared-files").count() == 0
            with page.expect_download() as info:
                page.locator("#command-detail a").filter(has_text="generated/diags.json").click()
            assert info.value.suggested_filename == "diags.json"
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(10)
        listener.close()
