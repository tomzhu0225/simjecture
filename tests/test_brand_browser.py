"""Browser regressions for shared branding; install Playwright + Chromium to run."""

from __future__ import annotations

import threading
from urllib.parse import urlsplit

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


@pytest.fixture(scope="module")
def brand_browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        # Match the existing browser suite: missing browsers or launch restrictions
        # are reported as failures, never hidden behind a broad exception/skip.
        browser = runtime.chromium.launch(headless=True)
        try:
            yield browser, playwright.expect
        finally:
            browser.close()


@pytest.fixture(scope="module")
def brand_base_url(tmp_path_factory):
    root = tmp_path_factory.mktemp("brand-browser")
    app = SimjectureWebApplication(runs_root=root, scan_roots=(root,), allow_mutations=False)
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _show_workspace_brand(page, expect):
    sidebar = page.locator("#workspace-sidebar")
    if not sidebar.is_visible():
        page.get_by_role("button", name="Expand left sidebar", exact=True).click()
    expect(sidebar).to_be_visible()


def _assert_logo(page, expect, route, theme):
    if route == "/workspace":
        _show_workspace_brand(page, expect)
    name = "Simjecture research workspace" if route == "/workspace" else "Simjecture home"
    brand = page.get_by_role("link", name=name, exact=True)
    expect(brand).to_have_count(1)
    expect(brand).to_be_visible()
    expect(brand).to_have_attribute("href", "/workspace" if route == "/workspace" else "/")
    expect(brand.get_by_role("img")).to_have_count(0)
    images = brand.locator("img.brand-logo")
    expect(images).to_have_count(1 if route == "/workspace" else 2)
    page.wait_for_function(
        """() => [...document.querySelectorAll('.brand img.brand-logo')].every(
            img => img.complete && img.naturalWidth > 0 && img.naturalHeight > 0
        )"""
    )
    variant = "dark" if route == "/workspace" else theme
    visible = brand.locator("img.brand-logo:visible")
    expect(visible).to_have_count(1)
    expect(visible).to_have_attribute("src", f"/assets/brand/simjecture-lockup-{variant}.svg")
    expect(visible).to_have_attribute("alt", "")
    expect(visible).to_have_attribute("aria-hidden", "true")
    for index in range(images.count()):
        expect(images.nth(index)).to_have_attribute("alt", "")
        expect(images.nth(index)).to_have_attribute("aria-hidden", "true")
    box = visible.bounding_box()
    brand_box = brand.bounding_box()
    assert box is not None and brand_box is not None
    assert 100 <= box["width"] <= 240
    assert 22 <= box["height"] <= 54
    assert box["width"] / box["height"] == pytest.approx(288.824 / 64, abs=0.03)
    assert box["x"] >= brand_box["x"] - 1
    assert box["x"] + box["width"] <= brand_box["x"] + brand_box["width"] + 1
    assert box["y"] >= brand_box["y"] - 1
    assert box["y"] + box["height"] <= brand_box["y"] + brand_box["height"] + 1
    container = page.locator("#workspace-sidebar" if route == "/workspace" else ".topbar")
    container_box = container.bounding_box()
    assert container_box is not None
    assert box["x"] >= container_box["x"]
    assert box["x"] + box["width"] <= container_box["x"] + container_box["width"]
    assert box["x"] >= 0
    assert box["x"] + box["width"] <= page.viewport_size["width"]
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


@pytest.mark.parametrize("route", ["/workspace", "/monitor"])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(
    "viewport",
    [
        pytest.param({"width": 1440, "height": 1000}, id="desktop"),
        pytest.param({"width": 820, "height": 1180}, id="tablet"),
        pytest.param({"width": 390, "height": 844}, id="mobile"),
    ],
)
def test_brand_images_load_fit_and_follow_theme_through_reload(
    brand_browser, brand_base_url, route, theme, viewport
):
    browser, expect = brand_browser
    context = browser.new_context(viewport=viewport, color_scheme=theme)
    errors = []
    try:
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(brand_base_url + route)
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        _assert_logo(page, expect, route, theme)
        for new_theme in ["dark" if theme == "light" else "light", theme]:
            toggle = page.locator("#theme-toggle" if route == "/workspace" else "#theme-button")
            if route == "/workspace":
                page.locator("#account-button").click()
            toggle.click()
            if route == "/workspace":
                page.keyboard.press("Escape")
            expect(page.locator("html")).to_have_attribute("data-theme", new_theme)
            assert page.evaluate("localStorage.getItem('simjecture-theme')") == new_theme
            _assert_logo(page, expect, route, new_theme)
            page.reload()
            expect(page.locator("html")).to_have_attribute("data-theme", new_theme)
            _assert_logo(page, expect, route, new_theme)
        if route == "/workspace":
            page.get_by_role("button", name="Collapse left sidebar", exact=True).click()
            expect(page.locator("#workspace-sidebar")).to_be_hidden()
            page.reload()
            expect(page.locator("#workspace-sidebar")).to_be_hidden()
            _show_workspace_brand(page, expect)
            _assert_logo(page, expect, route, theme)
        assert errors == []
    finally:
        context.close()


@pytest.mark.parametrize(
    ("route", "name", "target"),
    [
        ("/workspace", "Simjecture research workspace", "/workspace"),
        ("/monitor", "Simjecture home", "/"),
    ],
)
def test_brand_links_have_accessible_names_and_work_with_keyboard(
    brand_browser, brand_base_url, route, name, target
):
    browser, expect = brand_browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    try:
        page = context.new_page()
        page.goto(brand_base_url + route + "#brand-navigation-test")
        brand = page.get_by_role("link", name=name, exact=True)
        expect(brand).to_be_visible()
        brand.focus()
        expect(brand).to_be_focused()
        brand.press("Enter")
        page.wait_for_url(brand_base_url + target)
        assert urlsplit(page.url).path == target
        assert urlsplit(page.url).fragment == ""
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_brand_fits_smallest_previously_saved_sidebar_width(brand_browser, brand_base_url, theme):
    browser, expect = brand_browser
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme=theme)
    try:
        # The current drag minimum is 176 px, but existing saved widths as small
        # as 160 px are accepted. The artwork must shrink without clipping.
        context.add_init_script("localStorage.setItem('simjecture-left-width', '160')")
        page = context.new_page()
        page.goto(brand_base_url + "/workspace")
        for attempt in range(2):
            if attempt:
                page.reload()
            _assert_logo(page, expect, "/workspace", theme)
            assert page.locator("#workspace-sidebar").bounding_box()["width"] == 160
    finally:
        context.close()
