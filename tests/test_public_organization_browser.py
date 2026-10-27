"""Hosted member navigation, project creation and cited conversation retrieval."""

import json
import socket
import threading
import time
from pathlib import Path

import pytest

from conjecture_solver.public.server import COOKIE, create_app


@pytest.mark.parametrize("width", [1440, 390])
def test_member_workspaces_projects_and_knowledge_in_browser(tmp_path, width):
    playwright = pytest.importorskip("playwright.sync_api")
    uvicorn = pytest.importorskip("uvicorn")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    (tmp_path / "settings.json").write_text(json.dumps({"public_origin": origin}))
    (tmp_path / "provider.json").write_text(
        json.dumps(
            {
                "public_enabled": True,
                "api_key": "fixture",
                "model": "fixture-model",
                "base_url": "https://fixture.invalid",
            }
        )
    )
    app = create_app(tmp_path, dispatch=False, secure_cookies=False)
    store = app.state.store
    _, visitor = store.create_visitor("member-browser")
    token, owner = store.authorize_identity(visitor["id"], 123, "researcher", "Researcher")
    conversation = store.create_project(owner["id"], "Earlier diffusion discussion")
    job = store.enqueue(
        owner["id"],
        "interactive",
        "What baseline should we use?",
        project=conversation["id"],
    )
    store.claim()
    store.update(job["id"], status="completed", finished=time.time())
    store.finish_project_job(job, "Amber resonance is the saved baseline from this discussion.")
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    errors = []
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": width, "height": 1000 if width > 400 else 844},
            )
            context.add_cookies([{"name": COOKIE, "value": token, "url": origin}])
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/workspace?tour")
            playwright.expect(page.locator("#account-button")).to_be_enabled()
            tour = page.get_by_role("dialog", name="Ask your agent anything")
            playwright.expect(tour).to_be_visible()
            playwright.expect(tour).to_contain_text("provided for this workspace")
            page.keyboard.press("ArrowRight")
            playwright.expect(page.locator("#tour-title")).to_have_text(
                "Reuse earlier conversations"
            )
            playwright.expect(page.locator("#tour-body")).to_contain_text(
                "Search completed replies"
            )
            while page.locator(".tour-next").inner_text() != "Done":
                page.keyboard.press("ArrowRight")
            if width > 400:
                playwright.expect(page.locator("#tour-title")).to_have_text(
                    "Explore the available research tools"
                )
                playwright.expect(page.locator("#tour-body")).to_contain_text(
                    "Your administrator manages installation"
                )
            page.locator(".tour-next").click()
            playwright.expect(page.locator(".tour-card")).to_have_count(0)
            if not page.locator("#workspace-switcher").is_visible():
                page.locator("#left-sidebar-toggle").click()
            page.locator("#knowledge-nav").click()
            playwright.expect(page.locator("#view-knowledge")).to_be_visible()
            playwright.expect(page.locator("#knowledge-connect")).to_be_hidden()
            playwright.expect(page.locator('[data-knowledge-tab="access"]')).to_be_hidden()
            page.locator("#knowledge-query").fill("Amber")
            page.locator("#knowledge-search-form").evaluate("(form) => form.requestSubmit()")
            page.locator(".knowledge-result").first.click()
            playwright.expect(page.locator(".knowledge-preview-body")).to_contain_text(
                "Amber resonance"
            )
            screenshots = Path("artifacts/release-0.6.3")
            screenshots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshots / f"hosted-knowledge-{width}.png"), full_page=True)
            # Attach the exact indexed passage to a fresh conversation without running a model.
            page.locator("#knowledge-preview").get_by_role(
                "button", name="Discuss this"
            ).click()
            playwright.expect(page.locator("#home-knowledge-refs")).to_contain_text(
                "Earlier diffusion"
            )
            assert store.jobs(owner["id"])[0]["status"] != "queued"
            if not page.locator("#workspace-switcher").is_visible():
                page.locator("#left-sidebar-toggle").click()
            page.locator("#workspace-switcher").click()
            page.locator("#new-space-name").fill("Plasma lab")
            page.locator("#create-space-form").evaluate("(form) => form.requestSubmit()")
            page.wait_for_url("**/workspace?workspace=space-*")
            playwright.expect(page.locator("#account-button")).to_be_enabled()
            if not page.locator("#new-collection").is_visible():
                page.locator("#left-sidebar-toggle").click()
            page.locator("#new-collection").click()
            page.locator("#collection-name").fill("Diffusion project")
            page.locator("#collection-summary").fill("Related discussions and recorded studies")
            page.locator("#collection-guidance").fill("Account for boundary flux.")
            page.locator("#collection-form").evaluate("(form) => form.requestSubmit()")
            playwright.expect(page.locator("#collection-title")).to_have_text("Diffusion project")
            playwright.expect(page.locator("#collection-instructions")).to_have_text(
                "Account for boundary flux."
            )
            page.screenshot(path=str(screenshots / f"hosted-project-{width}.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
