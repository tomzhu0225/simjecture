import json
import re
import socket
import threading
import time

import pytest


@pytest.mark.parametrize("general_execution", [True, False])
def test_hosted_cylinder_card_credit_custom_study_and_benchmark(tmp_path, general_execution):
    uvicorn = pytest.importorskip("uvicorn")
    playwright = pytest.importorskip("playwright.sync_api")
    from tests.test_public_workspace import app as factory

    app = factory.__wrapped__(tmp_path)
    registry = tmp_path / "tools.json"
    registry.write_text(
        json.dumps(
            {
                "tools": [
                    {
                        "id": "lbm-cylinder",
                        "family": "lbm",
                        "name": "Cylinder wake · Re=100",
                        "scope": "2D isothermal MRT-LBM",
                        "qualification": "Runtime fixture",
                        "qualified": True,
                        "parameters": {},
                    }
                ]
            }
        )
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    (tmp_path / "settings.json").write_text(
        json.dumps(
            {
                "public_origin": origin,
                "tools_registry": str(registry),
                "executor_qualified": general_execution,
            }
        )
    )
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/#tools")
            card = page.locator('[data-tool="warp-lbm"]')
            playwright.expect(card).to_be_visible()
            playwright.expect(page.locator("#tool-collection-note")).to_contain_text(
                "Your administrator chooses and maintains"
            )
            playwright.expect(page.locator("#available-tool-section")).to_be_hidden()
            playwright.expect(page.locator("#tool-availability-filters")).to_be_hidden()
            playwright.expect(page.locator("#connect-research-tool")).to_be_hidden()
            playwright.expect(page.locator("#tools-machines-help")).to_be_hidden()
            search = page.get_by_role("searchbox", name="Search research tools")
            search.fill("Re=100")
            playwright.expect(page.locator(".research-tool-card:visible")).to_have_count(1)
            if general_execution:
                playwright.expect(card).to_contain_text("Zifei Meng")
            card.click()
            dialog = page.locator("#tool-details-dialog")
            playwright.expect(page.locator("#tool-detail-action")).to_be_hidden()
            assert dialog.get_by_role("button", name="Check installed").count() == 0
            choice = dialog.get_by_role("combobox")
            assert choice.input_value() == ("custom-study" if general_execution else "lbm-cylinder")
            assert choice.locator("option[value='custom-study']").count() == int(general_execution)
            choice.select_option("lbm-cylinder")
            playwright.expect(dialog.get_by_role("button", name="Run preset")).to_be_visible()
            playwright.expect(
                page.get_by_role("link", name="Contributed by Zifei Meng")
            ).to_have_attribute("href", "https://github.com/ZifeiMengSPH")
            page.evaluate("refreshTools()")
            assert choice.input_value() == "lbm-cylinder"
            dialog.get_by_role("button", name="Prepare benchmark").click()
            playwright.expect(dialog).not_to_be_visible()
            playwright.expect(page.locator("#chat-input")).to_have_value(
                re.compile(r"Prepare an autonomous.*Hold downstream distance at 40D")
            )
            with app.state.store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0

            if general_execution:
                page.get_by_role("button", name="Research tools", exact=True).click()
                card.click()
                dialog.get_by_role("combobox").select_option("custom-study")
                dialog.get_by_role("button", name="Prepare in chat").click()
                playwright.expect(dialog).not_to_be_visible()
                playwright.expect(page.locator("#chat-input")).to_have_value(
                    re.compile("Help me prepare a custom study with Cylinder flow")
                )

            # A permitted preset still queues through the hosted endpoint.
            page.get_by_role("button", name="Research tools", exact=True).click()
            card.click()
            dialog.get_by_role("combobox").select_option("lbm-cylinder")
            dialog.get_by_role("button", name="Run preset").click()
            playwright.expect(dialog).not_to_be_visible()
            playwright.expect(page.locator("#project-title")).to_have_text("Cylinder wake · Re=100")
            with app.state.store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
