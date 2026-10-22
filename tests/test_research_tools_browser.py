"""Tool details stay accessible without growing cards or rerunning setup."""

import threading
from pathlib import Path

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from conjecture_solver.web.workspace import CATALOGUE


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
            card.click()
            playwright.expect(page.locator("#tool-details-dialog")).to_be_visible()
            # Browser coordinates can differ by tiny subpixel rounding after
            # opening a dialog; a real card expansion is still rejected.
            assert neighbor.bounding_box()["height"] == pytest.approx(height, abs=0.05)
            assert page.locator("#installed-tool-grid").bounding_box()["height"] == pytest.approx(
                grid, abs=0.05
            )
            page.get_by_role("button", name="View installations", exact=True).click()
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


@pytest.mark.parametrize("read_only", [False, True])
def test_catalog_search_filters_keyboard_and_setup_permissions(tmp_path, monkeypatch, read_only):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(
        runs_root=tmp_path / "runs", scan_roots=(tmp_path,), allow_mutations=not read_only
    )
    catalog = [
        dict(
            id=identifier, name=name, description=description, action=action,
            installed=identifier in {"flash", "warpx-cpu"}, registered=True,
        )
        for identifier, name, description, action in CATALOGUE
    ]
    catalog.append(dict(
        id="custom-spectrometer", name="Connected spectrometer", installed=True,
        description="Lab instrument", action="custom",
        variants=[dict(label="Laser calibration", description="Spectral response")],
    ))
    monkeypatch.setattr(app.workspace, "catalogue", lambda: catalog)
    installs = []

    def install(payload):
        installs.append(payload)
        next(t for t in catalog if t["id"] == payload["name"])["state"] = "working"
        return {"started": True}

    monkeypatch.setattr(app.workspace, "start_install", install)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    screenshots = Path(__file__).resolve().parents[1] / "artifacts/tool-catalog-preview"
    screenshots.mkdir(parents=True, exist_ok=True)
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#tools")
            visible = page.locator(".research-tool-card:visible")
            playwright.expect(visible).to_have_count(len(catalog) + 1)
            search = page.get_by_role("searchbox", name="Search research tools")
            category = page.get_by_role("combobox", name="Filter tools by category")
            search.fill(" WARPX ")
            playwright.expect(visible).to_have_count(2)
            search.fill("gpu particle")
            playwright.expect(visible).to_have_count(1)
            playwright.expect(visible).to_have_attribute("data-tool", "warpx-cuda")
            search.fill("laser calibration")
            playwright.expect(visible).to_have_attribute("data-tool", "custom-spectrometer")
            search.fill("magnetic")
            category.select_option("Electromagnetics")
            playwright.expect(visible).to_have_count(1)
            playwright.expect(visible).to_have_attribute("data-tool", "magnetic-smoke")
            visible.click()
            playwright.expect(page.locator("#tool-details-dialog")).to_contain_text(
                "no circuit or eddy-current solve"
            )
            page.keyboard.press("Escape")
            search.fill("")
            category.select_option("Materials & radiation")
            playwright.expect(visible).to_have_count(6)
            search.fill("feos")
            playwright.expect(visible).to_have_count(1)
            playwright.expect(visible).to_have_attribute("data-tool", "feos")
            visible.click()
            playwright.expect(page.locator("#tool-details-dialog")).to_contain_text("no opacity")
            page.keyboard.press("Escape")
            search.fill("material eos builder")
            playwright.expect(visible).to_have_count(1)
            playwright.expect(visible).to_have_attribute("data-tool", "material-eos")
            visible.click()
            playwright.expect(page.locator("#tool-details-dialog")).to_contain_text("no opacity")
            page.keyboard.press("Escape")
            search.fill("")
            page.get_by_role("button", name="Installed", exact=True).click()
            playwright.expect(page.locator("#tool-search-empty")).to_be_visible()
            playwright.expect(page.locator("#tool-results-count")).to_have_text(
                f"0 of {len(catalog) + 1} tools"
            )
            page.get_by_role("button", name="Clear filters").click()
            playwright.expect(search).to_be_focused()
            playwright.expect(visible).to_have_count(len(catalog) + 1)

            # Included tools have details too, with no installer offered.
            search.fill("numpy")
            opener = page.get_by_role("button", name="View Python research stack details")
            opener.focus()
            opener.press("Enter")
            dialog = page.locator("#tool-details-dialog")
            playwright.expect(dialog).to_contain_text("NumPy, SciPy, pandas")
            playwright.expect(page.locator("#tool-detail-action")).to_be_hidden()
            page.keyboard.press("Escape")
            playwright.expect(opener).to_be_focused()
            search.fill("nothing-matches-<script>")
            playwright.expect(page.locator("#tool-search-empty")).to_be_visible()
            page.get_by_role("button", name="Clear filters").click()

            # Background polling preserves filters; installation updates move a card
            # out of the filtered shelf without closing its progress dialog.
            page.get_by_role("button", name="Available to add", exact=True).click()
            category.select_option("Materials & radiation")
            search.fill("atomec")
            page.evaluate("refreshTools()")
            playwright.expect(search).to_have_value("atomec")
            playwright.expect(category).to_have_value("Materials & radiation")
            playwright.expect(visible).to_have_count(1)
            visible.click(position={"x": 15, "y": 15})
            playwright.expect(dialog).to_be_visible()
            install_button = dialog.get_by_role("button", name="Install", exact=True)
            if read_only:
                playwright.expect(page.locator("#tool-collection-note")).to_contain_text(
                    "Read-only workspace"
                )
                playwright.expect(install_button).to_be_disabled()
                playwright.expect(
                    dialog.get_by_role("button", name="Check installed")
                ).to_be_disabled()
                assert installs == []
            else:
                install_button.click()
                playwright.expect(install_button).to_be_disabled()
                assert installs == [{"name": "atomec", "action": "install"}]
                tool = next(t for t in catalog if t["id"] == "atomec")
                tool.update(installed=True, state="installed", readiness="passed")
                page.evaluate("refreshTools()")
                playwright.expect(dialog).to_be_visible()
                playwright.expect(
                    dialog.get_by_role("button", name="Check readiness")
                ).to_be_enabled()
                playwright.expect(visible).to_have_count(0)
            page.keyboard.press("Escape")
            search.fill("")
            category.select_option("all")
            page.get_by_role("button", name="All tools", exact=True).click()

            if not read_only:
                page.screenshot(path=str(screenshots / "catalog-desktop.png"), full_page=True)
                page.evaluate("WorkspaceTheme.set('dark')")
                page.screenshot(path=str(screenshots / "catalog-dark.png"), full_page=True)
                page.evaluate("WorkspaceTheme.set('light')")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            if not read_only:
                page.screenshot(path=str(screenshots / "catalog-mobile.png"), full_page=True)
            page.locator('[data-tool="flash"]').click()
            playwright.expect(dialog).to_be_visible()
            box = dialog.bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= 390
            assert box["y"] >= 0 and box["y"] + box["height"] <= 844
            if not read_only:
                page.screenshot(path=str(screenshots / "details-mobile.png"))
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
