"""Home shows both ways to work, with examples that run on this installation."""

import threading

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


@pytest.mark.parametrize("flash_ready", [False, True])
def test_mode_cards_offer_examples_that_match_installed_tools(tmp_path, monkeypatch, flash_ready):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    flash = dict(
        id="flash", name="FLASH", description="MHD solver", action="source",
        installed=flash_ready, registered=True, state="installed" if flash_ready else "available",
        readiness="passed" if flash_ready else "unchecked", report={}, log="",
    )
    monkeypatch.setattr(app.workspace, "catalogue", lambda: [flash])
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 768})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace")
            cards = page.locator(".mode-card")
            playwright.expect(cards).to_have_count(2)
            playwright.expect(cards.nth(0)).to_contain_text("Interactive")
            playwright.expect(cards.nth(1)).to_contain_text("Autonomous study")
            # Both modes and every example are visible without scrolling on a laptop.
            for card in (cards.nth(0), cards.nth(1)):
                box = card.bounding_box()
                assert box["y"] + box["height"] <= 768
            assert page.locator(".lead, .eyebrow").filter(visible=True).count() == 0
            slot = page.locator("#home-example-solver")
            expected = "flash" if flash_ready else "python"
            playwright.expect(slot).to_have_attribute("data-solver", expected)
            playwright.expect(slot).to_contain_text(
                "magnetic islands" if flash_ready else "Watch chaos appear"
            )
            slot.click()
            request = page.locator("#first-request")
            value = request.input_value()
            assert ("FLASH" in value) is flash_ready and ("Lorenz" in value) is not flash_ready
            playwright.expect(request).to_be_focused()
            page.get_by_role("button", name="Does a pendulum keep the same period?").click()
            assert "10-minute autonomous research study" in request.input_value()
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
