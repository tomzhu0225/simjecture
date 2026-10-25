"""First-visit guided tour and the one-time Autonomous study explainer."""

import threading

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def test_tour_replays_from_menu_and_explainer_shows_once(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    conversation = app.workspace.create({"name": "Tour conversation"})
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            # Automated browsers are not interrupted unless the tour is requested.
            page.goto(base + "/workspace")
            page.locator("#quick-start").wait_for()
            page.wait_for_timeout(300)
            assert page.locator(".tour-card").count() == 0

            page.goto(base + "/workspace?tour")
            card = page.get_by_role("dialog", name="Ask your agent anything")
            playwright.expect(card).to_be_visible()
            playwright.expect(card).to_be_focused()
            resources = page.locator(".workspace-resources")
            assert resources.evaluate("e => e.open") is False  # 768 px starts collapsed
            titles = []
            while True:
                titles.append(page.locator("#tour-title").inner_text())
                box = page.locator(".tour-card").bounding_box()
                assert box["x"] >= 0 and box["y"] >= 0
                assert box["x"] + box["width"] <= 1366 and box["y"] + box["height"] <= 768
                if page.locator(".tour-next").inner_text() == "Done":
                    playwright.expect(
                        page.get_by_role("button", name="Research tools", exact=True)
                    ).to_be_visible()
                    break
                page.keyboard.press("ArrowRight")
            assert titles[2] == "Two ways to work" and len(titles) == 5
            page.locator(".tour-next").click()
            playwright.expect(page.locator(".tour-card")).to_have_count(0)
            # The tour restores the reader's collapsed Resources group and remembers it ran.
            assert resources.evaluate("e => e.open") is False
            assert page.evaluate("localStorage.getItem('simjecture-tour-seen')") == "true"

            # Replay from the workspace menu; Escape closes it.
            page.goto(base + "/workspace")
            page.locator("#account-button").click()
            page.get_by_role("button", name="Take the tour", exact=True).click()
            playwright.expect(page.locator(".tour-card")).to_be_visible()
            page.keyboard.press("Escape")
            playwright.expect(page.locator(".tour-card")).to_have_count(0)

            # The Autonomous study explainer appears once, until dismissed.
            page.get_by_role("button", name="Tour conversation", exact=True).click()
            page.get_by_role("button", name="Autonomous study", exact=True).click()
            explainer = page.locator("#study-explainer")
            playwright.expect(explainer).to_be_visible()
            playwright.expect(explainer).to_contain_text("Review the brief")
            page.get_by_role("button", name="Got it", exact=True).click()
            playwright.expect(explainer).to_be_hidden()
            page.reload()
            page.get_by_role("button", name="Tour conversation", exact=True).click()
            page.get_by_role("button", name="Autonomous study", exact=True).click()
            playwright.expect(page.locator("#autonomous-panel")).to_be_visible()
            playwright.expect(explainer).to_be_hidden()
            assert conversation["id"]
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
