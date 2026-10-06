"""Tool details stay accessible without growing cards or rerunning setup."""

import threading

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def test_tool_panel_isolates_expansion_preserves_logs_and_scopes_missing_runtime(
    tmp_path, monkeypatch
):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    missing = "capability runtime is unavailable: /fixture/.runtime/warpx-cpu"
    warp = dict(
        id="warpx-cpu",
        name="WarpX · CPU",
        description="Particle-in-cell solver",
        installed=True,
        registered=False,
        state="installed",
        readiness="failed",
        action="install",
        variants=[
            dict(label=f"Build {i}", runtime=f"/fixture/build-{i}", description="Local build")
            for i in range(24)
        ],
        report={
            "ready": False,
            "checks": [
                {
                    "status": "fail",
                    "required": True,
                    "detail": missing,
                    "remedy": "Run simjecture install warpx-cpu.",
                }
            ],
        },
        log="initial setup log",
    )
    flash = dict(
        id="flash",
        name="FLASH",
        description="MHD solver",
        installed=True,
        registered=True,
        state="installed",
        readiness="unchecked",
        action="source",
        variants=[],
        report={},
        log="",
    )
    eos = dict(
        id="atomec",
        name="atoMEC",
        description="Atomic physics",
        installed=False,
        state="available",
        readiness="unchecked",
        action="install",
        variants=[],
        report={},
        log="",
    )
    monkeypatch.setattr(app.workspace, "catalogue", lambda: [warp, flash, eos])
    installations = []
    registrations = []
    monkeypatch.setattr(
        app.workspace, "start_install", lambda payload: installations.append(payload)
    )
    monkeypatch.setattr(
        app.workspace,
        "register_tool",
        lambda payload: registrations.append(payload) or {"registered": True},
    )
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#tools")
            card = page.locator('[data-tool="warpx-cpu"]')
            neighbor = page.locator('[data-tool="flash"]')
            playwright.expect(card).to_contain_text("Detected")
            assert missing not in card.inner_text() and card.locator("details").count() == 0
            height = neighbor.bounding_box()["height"]
            grid = page.locator("#installed-tool-grid").bounding_box()["height"]
            page.evaluate("window.originalToolCard=document.querySelector('[data-tool=\"flash\"]')")
            card.get_by_role("button", name="View installations", exact=True).click()
            playwright.expect(page.locator("#tool-details-dialog")).to_be_visible()
            # Browser coordinates can differ by tiny subpixel rounding after
            # opening a dialog; a real card expansion is still rejected.
            assert neighbor.bounding_box()["height"] == pytest.approx(height, abs=0.05)
            assert page.locator("#installed-tool-grid").bounding_box()["height"] == pytest.approx(
                grid, abs=0.05
            )
            assert page.locator('[data-key="variants-warpx-cpu"]').get_attribute("open") is not None
            page.locator("#tool-details-body").evaluate("e=>e.scrollTop=300")
            warp["log"] = "updated setup log"
            page.evaluate("refreshTools()")
            assert page.evaluate(
                "originalToolCard===document.querySelector('[data-tool=\"flash\"]')"
            )
            assert page.locator("#tool-details-body").evaluate("e=>e.scrollTop") == 300
            assert page.locator('[data-key="variants-warpx-cpu"]').get_attribute("open") is not None
            page.locator('[data-key="variants-warpx-cpu"] summary').click()
            page.locator('[data-key="diagnostics-warpx-cpu"] summary').click()
            assert missing in page.locator(".tool-failure").inner_text()
            assert (
                "does not test these detected builds"
                in page.locator("#tool-details-body").inner_text()
            )
            assert installations == []
            page.get_by_role("button", name="Close tool details").click()
            page.get_by_role("button", name="Connect existing tool", exact=False).click()
            playwright.expect(page.locator("#custom-tool-dialog")).to_be_visible()
            page.locator("#tool-name").fill("Existing instrument")
            page.locator("#tool-path").fill("/fixture/capabilities")
            page.get_by_role("button", name="Register tool", exact=True).click()
            playwright.expect(page.locator("#custom-tool-dialog")).not_to_be_visible()
            assert registrations == [
                {"name": "Existing instrument", "path": "/fixture/capabilities"}
            ]
            assert installations == [] and not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
