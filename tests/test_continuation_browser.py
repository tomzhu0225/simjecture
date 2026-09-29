"""Exercise visible continuation and steering entry points with a real browser."""

import threading
import time
from pathlib import Path

import pytest

from conjecture_solver.research_continuation import steering
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from tests.test_workspace import connect
from tests.test_workspace import provider as protocol_provider


@pytest.fixture
def provider():
    yield from protocol_provider.__wrapped__()


def test_monitor_to_continuation_draft_and_steering(tmp_path, provider, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    parent = ResearchService.create(
        tmp_path / "old-study", "Does magnetic work explain the radiation?"
    )
    parent.freeze_protocol("Independent flux accounting is required.")
    (parent.work / "calculation.py").write_text("print(1)\n")
    (parent.root / "supervisor").mkdir()
    put(parent.root / "supervisor/state.json", {"status": "paused", "deadline": time.time() + 3600})
    app = SimjectureWebApplication(
        initial_run=parent.root, scan_roots=(tmp_path,), runs_root=tmp_path / "runs"
    )
    connect(app.workspace, provider[0])
    token = app.registry.register(parent.root)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    from types import SimpleNamespace

    monkeypatch.setattr(
        "conjecture_solver.mvp_launch.start_managed_campaign",
        lambda plan: SimpleNamespace(close=lambda: None),
    )
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + f"/monitor?campaign={token}")
            page.get_by_role("link", name="Send guidance", exact=True).click()
            page.get_by_label("Guidance for the agent").fill("Measure boundary flux independently.")
            page.get_by_role("button", name="Send guidance", exact=True).click()
            page.get_by_text("Guidance queued for the next agent checkpoint.").wait_for()
            assert steering(parent.root)[0]["message"] == "Measure boundary flux independently."
            # Expired parents remain continuable, without altering their deadline.
            expired = parent.manifest | {"deadline": time.time() - 2}
            put(parent.root / "research.json", expired)
            put(
                parent.root / "supervisor/state.json",
                {"status": "paused_external_error", "deadline": expired["deadline"]},
            )
            original = (parent.root / "research.json").read_bytes()
            page.goto(base + f"/monitor?campaign={token}")
            page.get_by_role("link", name="Continue investigation", exact=True).click()
            page.get_by_label("What should the next phase investigate?").fill(
                "Resolve axial modes and compare energy pathways."
            )
            page.get_by_label("New wall-time budget (hours)").fill("2")
            page.get_by_role("button", name="Prepare directly", exact=True).click()
            page.locator("#prepared-brief").wait_for(state="visible")
            assert page.locator("#brief-hours").input_value() == "2"
            assert (
                page.locator("#brief-constraints").input_value()
                == "Resolve axial modes and compare energy pathways."
            )
            page.get_by_role("link", name="Continuation phase", exact=False).wait_for()
            project = app.workspace.projects()[0]
            assert project["continuation_draft"]["files"] == ["calculation.py"]
            assert (parent.root / "research.json").read_bytes() == original
            assert len(project["studies"]) == 0  # Review first; preparing is not launching.
            shots = Path("artifacts/workspace-preview")
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots / "continuation-proposal.png"), full_page=True)
            page.locator("#start-prepared-study").click()
            page.get_by_text(
                "Autonomous research started. You can close this page and return later."
            ).wait_for()
            saved = app.workspace.project(project["id"])
            assert len(saved["studies"]) == 1
            child = ResearchService(saved["studies"][0]["path"])
            assert child.manifest["continuation"]["parent"] == str(parent.root)
            assert (child.work / "inherited/calculation.py").read_text() == "print(1)\n"
            assert child.manifest["deadline"] > time.time() + 7100
            page.get_by_role("button", name="Send guidance", exact=True).click()
            page.get_by_label("Guidance for the agent").fill(
                "Preserve the uniform baseline as a control."
            )
            page.get_by_role("button", name="Send guidance", exact=True).last.click()
            page.get_by_text("Operator guidance (1 queued)", exact=True).click()
            page.get_by_text("Preserve the uniform baseline as a control.", exact=True).wait_for()
            assert steering(child.root)[0]["delivered_at"] is None
            page.screenshot(path=str(shots / "study-guidance.png"), full_page=True)
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_prepare_with_agent_opens_chat_and_generates_linked_brief(tmp_path, provider):
    playwright = pytest.importorskip("playwright.sync_api")
    parent = ResearchService.create(tmp_path / "parent", "Q: distinguish physical energy pathways")
    (parent.work / "reader.py").write_text('print("reader")\n')
    app = SimjectureWebApplication(
        initial_run=parent.root, scan_roots=(tmp_path,), runs_root=tmp_path / "runs"
    )
    connect(app.workspace, provider[0])
    token = app.registry.register(parent.root)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_port}/monitor?campaign={token}")
            page.get_by_role("link", name="Continue investigation", exact=True).click()
            dialog = page.locator("dialog.research-action-dialog")
            dialog.wait_for(state="visible")
            assert dialog.get_by_role("button", name="Cancel", exact=True).is_visible()
            assert dialog.get_by_role("button", name="Prepare directly", exact=True).is_visible()
            page.get_by_label("New wall-time budget (hours)").fill("3")
            dialog.get_by_role("button", name="Prepare with agent", exact=True).click()
            page.locator("#interactive-panel").wait_for(state="visible")
            page.get_by_text(
                "The calculation and editable study brief are ready.", exact=True
            ).wait_for(timeout=40000)
            page.locator("#continuation-parent-link").wait_for(state="visible")
            page.get_by_role("button", name="Autonomous research", exact=True).click()
            page.locator("#prepared-brief").wait_for(state="visible")
            assert page.locator("#prepared-heading").inner_text() == "CONTINUATION PROPOSAL"
            project = app.workspace.projects()[0]
            assert project["continuation_draft"]["parent"] == str(parent.root)
            assert not project["studies"]
            assert (
                Path(project["path"]) / "files" / project["continuation_draft"]["context_file"]
            ).exists()
            page.screenshot(
                path="artifacts/workspace-preview/agent-continuation-brief.png", full_page=True
            )
            assert not errors
            browser.close()
    finally:
        for project in app.workspace.projects():
            app.workspace.stop(project["id"])
        server.shutdown()
        server.server_close()
