"""First-paint layout must not depend on JavaScript or session network latency."""

import socket
import threading
import time

import pytest


@pytest.fixture(params=["local", "hosted"])
def startup_workspace(request, tmp_path):
    if request.param == "local":
        from conjecture_solver.web.application import SimjectureWebApplication
        from conjecture_solver.web.server import create_server

        app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
        server = create_server(app, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}", False
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    else:
        uvicorn = pytest.importorskip("uvicorn")
        from tests.test_public_workspace import app as public_app

        app = public_app.__wrapped__(tmp_path)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
        (tmp_path / "settings.json").write_text('{"public_origin":"' + origin + '"}')
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started
            yield origin, True
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listener.close()


@pytest.mark.parametrize("width", [1440, 390])
def test_first_paint_and_slow_bootstrap_keep_the_same_layout(startup_workspace, width):
    playwright = pytest.importorskip("playwright.sync_api")
    origin, hosted = startup_workspace
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": 1000}, reduced_motion="reduce")
        errors, scripts, bootstraps = [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Hold the application script, then its bootstrap. These are distinct
        # first-paint states: neither may show the former local-only interface.
        page.route("**/assets/workspace.js", lambda route: scripts.append(route))
        page.route("**/api/workspace/bootstrap", lambda route: bootstraps.append(route))
        page.goto(origin + "/workspace", wait_until="commit")
        # Visibility probes can inspect the parsed DOM while render-blocking
        # CSS is still in flight. Test the first renderable layout, with the
        # unrelated entrance animation disabled for geometry comparisons.
        page.wait_for_function(
            """() => ['account-rail.css', 'workspace-composer.css', 'interface.css'].every(
                name => [...document.styleSheets].some(sheet => sheet.href?.endsWith('/' + name))
            )"""
        )
        rail = page.locator(".account-rail")
        composer = page.locator("#quick-start")
        playwright.expect(rail).to_be_visible()
        playwright.expect(page.locator("#first-request")).to_be_visible()
        playwright.expect(page.locator("#home-agent-picker")).to_be_visible()
        playwright.expect(page.locator("#account-button")).to_be_disabled()
        assert composer.evaluate("e => getComputedStyle(e).display") == "grid"
        assert composer.bounding_box()["height"] < 70
        assert page.locator("#first-request").bounding_box()["height"] < 30
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if hosted:
            playwright.expect(page.locator("#connection-button")).to_be_hidden()
            playwright.expect(page.locator('[data-view="machines"]')).to_be_hidden()
        else:
            playwright.expect(page.locator("#connection-button")).to_be_visible()
        initial = composer.bounding_box()
        assert len(scripts) == 1
        scripts.pop().continue_()
        # This attribute is set when the deferred composer script mounts.
        playwright.expect(page.locator("#home-agent-picker")).to_have_attribute(
            "aria-controls", "home-agent-popup"
        )
        deadline = time.monotonic() + 5
        while not bootstraps and time.monotonic() < deadline:
            page.wait_for_timeout(20)
        assert len(bootstraps) == 1
        assert composer.bounding_box() == pytest.approx(initial, abs=0.1)
        playwright.expect(page.locator("#account-button")).to_be_disabled()
        bootstraps.pop().continue_()
        # New guests create a session and repeat bootstrap after the first 401.
        page.unroute("**/api/workspace/bootstrap")
        playwright.expect(page.locator("#account-button")).to_be_enabled()
        playwright.expect(rail).to_have_count(1)
        playwright.expect(page.locator("#home-agent-picker")).to_have_count(1)
        assert composer.bounding_box() == pytest.approx(initial, abs=0.1)
        page.locator("#account-button").click()
        playwright.expect(page.locator("#hosting-account")).to_be_visible()
        page.keyboard.press("Escape")
        playwright.expect(page.locator("#hosting-account")).to_be_hidden()
        assert errors == []
        browser.close()
