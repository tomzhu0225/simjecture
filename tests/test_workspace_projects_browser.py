"""Actual browser navigation across optional projects and independent local spaces."""

import threading

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def test_projects_spaces_and_default_chat(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path)
    original = app.workspace.create({"name": "Existing ungrouped conversation"})
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace")
            page.locator("#workspace-switcher").wait_for()
            assert not page.locator("dialog[open]").count()
            assert page.locator("#quick-start").is_visible()
            page.locator("#new-collection").click()
            page.locator("#collection-name").fill("Generic device research")
            page.locator("#collection-guidance").fill("Check units and retain reference inputs.")
            page.get_by_role("button", name="Save project", exact=True).click()
            page.get_by_role("heading", name="Generic device research", exact=True).wait_for()
            group = app.workspace.collections()[0]
            page.reload()
            page.get_by_role("heading", name="Generic device research", exact=True).wait_for()
            page.locator("#collection-upload").set_input_files(
                {
                    "name": "reference.txt",
                    "mimeType": "text/plain",
                    "buffer": b"A generic reference",
                }
            )
            page.locator("#collection-files a").wait_for()
            with page.expect_download() as download:
                page.locator("#collection-files a").click()
            assert download.value.suggested_filename == "reference.txt"
            page.locator("#collection-new-chat").click()
            assert page.locator("#quick-start").is_visible()
            assert "Generic device research" in page.locator("#home-collection").text_content()
            page.reload()
            playwright.expect(page.locator("#home-collection")).to_be_visible()
            assert "Generic device research" in page.locator("#home-collection").text_content()
            page.get_by_role("button", name="Existing ungrouped conversation", exact=True).click()
            page.locator("#conversation-collection").select_option(group["id"])
            playwright.expect(page.locator("#conversation-collection")).to_have_value(group["id"])
            page.locator("#workspace-switcher").click()
            page.locator("#new-space-name").fill("Another laboratory")
            page.get_by_role("button", name="Create", exact=True).click()
            playwright.expect(page.locator("#workspace-name")).to_have_text("Another laboratory")
            assert page.locator("#project-list .project-link").count() == 0
            assert page.locator("#collection-list button").count() == 0
            # An independent tab still has the original workspace and owned records.
            other = browser.new_page()
            other.goto(f"http://127.0.0.1:{server.server_port}/workspace#project={original['id']}")
            playwright.expect(other.locator("#workspace-name")).to_have_text("Personal")
            playwright.expect(other.locator("#project-title")).to_have_text(
                "Existing ungrouped conversation"
            )
            assert other.locator("#conversation-collection").input_value() == group["id"]
            for width in (1440, 390):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
