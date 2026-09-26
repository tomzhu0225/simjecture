"""Browser acceptance checks. Install Playwright + Chromium to run locally."""

import threading
from pathlib import Path

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from tests.test_workspace import provider as protocol_provider


@pytest.fixture
def provider():
    yield from protocol_provider.__wrapped__()


def test_browser_setup_chat_files_and_autonomous_handoff(tmp_path, provider):
    playwright = pytest.importorskip("playwright.sync_api")
    url, _requests = provider
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    screenshots = Path(__file__).resolve().parents[1] / "artifacts/workspace-preview"
    screenshots.mkdir(parents=True, exist_ok=True)
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}")
            page.get_by_role("button", name="API connections").click()
            page.locator("#base-url").fill(url)
            page.locator("#api-key").fill("test-secret")
            assert page.locator("#model").count() == 0
            page.get_by_role("button", name="Save API connection").click()
            page.get_by_text(
                "API connection saved. Choose its model in a conversation.", exact=True
            ).first.wait_for()
            assert page.locator("#api-key").input_value() == ""
            page.get_by_role("button", name="New conversation").click()
            page.locator("#home-backend").select_option("builtin")
            page.locator("#home-model option[value='fixture-model']").wait_for(state="attached")
            page.locator("#home-model").select_option("fixture-model")
            page.locator("#home-effort").select_option("high")
            page.locator("#first-request").fill("Grill me to prepare an autonomous investigation.")
            page.locator("#first-request").press("Shift+Enter")
            assert page.locator("#first-request").input_value().endswith("\n")
            assert len(app.workspace.projects()) == 0
            page.screenshot(path=str(screenshots / "overview.png"), full_page=True)
            page.locator("#first-request").press("Enter")
            page.get_by_text(
                "What question should we test, and what time budget should I use?", exact=True
            ).wait_for(timeout=40000)
            playwright.expect(page.locator("#send-message")).to_be_enabled(timeout=40000)
            page.locator("#chat-input").fill("Calculate and prepare a counterexample study.")
            page.locator("#chat-input").press("Shift+Enter")
            assert page.locator("#chat-input").input_value().endswith("\n")
            page.locator("#chat-input").dispatch_event(
                "keydown", {"key": "Enter", "isComposing": True}
            )
            assert page.locator("#messages .message.user").count() == 1
            page.locator("#chat-input").press("Enter")
            page.get_by_text(
                "The calculation and editable study brief are ready.", exact=True
            ).wait_for(timeout=40000)
            page.get_by_role("link", name="observations.txt", exact=True).wait_for()
            assert "grill-me" in page.locator("#project-path").text_content()
            page.screenshot(path=str(screenshots / "interactive.png"), full_page=True)
            page.reload()
            page.get_by_text(
                "The calculation and editable study brief are ready.", exact=True
            ).wait_for()
            page.locator("#conversation-model option[value='fixture-model']").wait_for(
                state="attached"
            )
            assert page.locator("#conversation-backend").input_value() == "builtin"
            assert page.locator("#conversation-model").input_value() == "fixture-model"
            assert page.locator("#conversation-effort").input_value() == "high"
            page.get_by_role("button", name="Autonomous research", exact=True).click()
            assert "Euler" in page.locator("#brief-question").input_value()
            assert not page.locator("#brief-question").is_visible()
            page.get_by_role("button", name="Draft from this conversation").click()
            page.locator("#interactive-panel").wait_for(state="visible")
            playwright.expect(page.locator("#send-message")).to_be_enabled(timeout=40000)
            page.get_by_role("button", name="Autonomous research", exact=True).click()
            page.locator("#prepared-question").wait_for()
            page.screenshot(path=str(screenshots / "study-brief.png"), full_page=True)
            from conjecture_solver.execution import probe_execution_backend

            if probe_execution_backend("bubblewrap")["available"]:
                page.get_by_role("button", name="Start research ↗", exact=True).click()
                page.get_by_text("COMPLETED", exact=True).wait_for(timeout=90000)
                page.get_by_text("Accepted: falsified.", exact=False).wait_for()
                page.get_by_text("Results, reports, and simulation files", exact=True).click()
                page.get_by_role("link", name="result.json", exact=False).first.wait_for()
                page.screenshot(path=str(screenshots / "accepted-result.png"), full_page=True)
            page.get_by_role("button", name="Research tools", exact=True).click()
            page.get_by_role("heading", name="Python research stack").wait_for()
            assert "✓ Installed" in page.locator("#installed-tool-grid").inner_text()
            assert "Not installed" in page.locator("#available-tool-grid").inner_text()
            page.screenshot(path=str(screenshots / "tools.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#home")
            page.locator("#first-request").wait_for()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
            assert errors == []
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
