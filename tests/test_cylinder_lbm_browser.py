import json
import re
import socket
import threading
import time

import pytest


def test_hosted_cylinder_card_credit_custom_study_and_benchmark(tmp_path):
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
                "executor_qualified": True,
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
            playwright.expect(card).to_contain_text("Zifei Meng")
            choice = card.get_by_role("combobox")
            assert choice.input_value() == "custom-study"
            choice.select_option("lbm-cylinder")
            playwright.expect(card.get_by_role("button", name="Run preset")).to_be_visible()
            card.get_by_role("button", name="Details", exact=True).click()
            playwright.expect(
                page.get_by_role("link", name="Contributed by Zifei Meng")
            ).to_have_attribute("href", "https://github.com/ZifeiMengSPH")
            page.get_by_role("button", name="Close tool details").click()
            card.get_by_role("button", name="Prepare benchmark").click()
            playwright.expect(page.locator("#chat-input")).to_have_value(
                re.compile(r"Prepare an autonomous.*Hold downstream distance at 40D")
            )
            with app.state.store.connect() as db:
                assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
            assert errors == []
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
