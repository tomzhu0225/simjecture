"""First-visit guided tour and the one-time Autonomous study explainer."""

import threading
import time

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from tests.test_workspace_startup_browser import startup_workspace as startup_workspace


@pytest.mark.parametrize("delayed_path", ["/assets/workspace-tour.js", "/api/workspace/bootstrap"])
def test_first_visit_tour_waits_for_delayed_loading(startup_workspace, delayed_path):
    playwright = pytest.importorskip("playwright.sync_api")
    origin, _ = startup_workspace
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        # Exercise automatic first-visit behavior, without the ?tour override.
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")
        pending, errors = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**" + delayed_path, lambda route: pending.append(route))
        page.goto(origin + "/workspace", wait_until="commit")
        playwright.expect(page.locator("#quick-start")).to_be_visible()
        deadline = time.monotonic() + 5
        while not pending and time.monotonic() < deadline:
            page.wait_for_timeout(20)
        assert len(pending) == 1
        # Let other startup requests finish while this response is held back.
        page.wait_for_timeout(1000)
        playwright.expect(page.locator(".tour-card")).to_have_count(0)
        pending.pop().continue_()
        page.unroute("**" + delayed_path)
        playwright.expect(
            page.get_by_role("dialog", name="Ask your agent anything")
        ).to_be_visible()
        page.locator(".tour-skip").click()
        page.reload()
        playwright.expect(page.locator("#account-button")).to_be_enabled()
        playwright.expect(page.locator(".tour-card")).to_have_count(0)
        assert not errors
        browser.close()


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
            playwright.expect(card).to_contain_text("Choose which agent and model")
            resources = page.locator(".workspace-resources")
            assert resources.evaluate("e => e.open") is False  # 768 px starts collapsed
            titles = []
            while True:
                titles.append(page.locator("#tour-title").inner_text())
                if titles[-1] == "Bring your own references":
                    playwright.expect(page.locator(".tour-card")).to_contain_text("Connect folders")
                box = page.locator(".tour-card").bounding_box()
                assert box["x"] >= 0 and box["y"] >= 0
                assert box["x"] + box["width"] <= 1366 and box["y"] + box["height"] <= 768
                if page.locator(".tour-next").inner_text() == "Done":
                    playwright.expect(page.locator(".tour-card")).to_contain_text("Install solvers")
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

            # Replay from the workspace menu; Escape also works outside the card.
            page.goto(base + "/workspace")
            page.locator("#account-button").click()
            page.get_by_role("button", name="Take the tour", exact=True).click()
            playwright.expect(page.locator(".tour-card")).to_be_visible()
            page.locator("#first-request").focus()
            page.keyboard.press("ArrowRight")
            playwright.expect(page.locator("#tour-title")).to_have_text("Ask your agent anything")
            page.keyboard.press("Escape")
            playwright.expect(page.locator(".tour-card")).to_have_count(0)
            playwright.expect(page.locator("#first-request")).to_be_focused()

            # Navigating through the highlighted tools link ends the tour and
            # restores Resources instead of leaving a card over the next page.
            page.locator("#account-button").click()
            page.get_by_role("button", name="Take the tour", exact=True).click()
            while page.locator(".tour-next").inner_text() != "Done":
                page.keyboard.press("ArrowRight")
            page.get_by_role("button", name="Research tools", exact=True).click()
            playwright.expect(page.locator("#view-tools")).to_be_visible()
            playwright.expect(page.locator(".tour-card")).to_have_count(0)
            playwright.expect(page.locator(".tour-ring")).to_have_count(0)
            assert resources.evaluate("e => e.open") is False

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
