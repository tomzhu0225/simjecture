"""Shared UI language behavior on the real localhost workspace and monitor."""

import json
import re
import threading
from pathlib import Path
from urllib.parse import urlencode

import httpx
import pytest

from conjecture_solver.research_service import ResearchService
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


@pytest.fixture
def language_site(tmp_path, monkeypatch):
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    monkeypatch.setattr(
        app.workspace, "default_agent", lambda: {"backend": "builtin", "model": "fixture"}
    )
    project = app.workspace.create({"name": "Untranslated research conversation"})
    study = ResearchService.create(tmp_path / "study", "Untranslated scientific hypothesis")
    campaign = app.registry.register(study.root)
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", project["id"], campaign
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def language_browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        executable = Path(runtime.chromium.executable_path)
        if not executable.is_file():
            pytest.skip(f"Playwright Chromium executable is not installed: {executable}")
        browser = runtime.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def language_page(language_browser):
    # A Chinese browser must still start in English without an explicit choice.
    context = language_browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 1050})
    errors = []
    context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
    page = context.new_page()
    try:
        yield page, pytest.importorskip("playwright.sync_api").expect
        assert not errors
    finally:
        context.close()


def choose_language(page, language):
    picker = page.get_by_label("Interface language", exact=True)
    if "/workspace" in page.url:
        box = picker.bounding_box()
        if box is None or box["x"] < 0:
            page.locator("#rail-toggle").click()
    picker.select_option(language)


def test_translation_catalog_and_static_routes(language_site):
    base, _, _ = language_site
    with httpx.Client(base_url=base, trust_env=False) as client:
        for asset in ["i18n-messages.js", "i18n.js"]:
            response = client.get(f"/assets/{asset}")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/javascript; charset=utf-8"
        source = client.get("/assets/i18n-messages.js").text
        messages = json.loads(source.split("window.SimjectureMessages = ", 1)[1].rstrip(";\n"))
        for route in ["/workspace", "/monitor"]:
            html = client.get(route).text
            assert html.index("/assets/i18n-messages.js") < html.index("/assets/i18n.js")
            keys = re.findall(r'data-i18n(?:-placeholder|-title)?="([^"]+)"', html)
            assert keys
            for key in keys:
                assert messages[key]["en"]
                assert messages[key]["zh-CN"]


@pytest.mark.parametrize("width", [1440, 390])
def test_language_round_trip_reload_and_navigation(language_site, language_page, tmp_path, width):
    base, _, campaign = language_site
    page, expect = language_page
    page.set_viewport_size({"width": width, "height": 1050 if width > 400 else 844})
    page.goto(base + "/workspace")
    expect(page.locator("#account-button")).to_be_enabled()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    assert page.evaluate("localStorage.getItem('simjecture-language')") is None
    page.locator("#first-request").fill("Keep this research draft unchanged")
    draft = page.locator("#first-request").element_handle()
    choose_language(page, "zh-CN")
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    expect(page.locator('[data-i18n="workspace.homeIntro"]')).to_have_text("我们要研究什么？")
    expect(page.locator("#new-project")).to_have_text("＋ New conversation")
    expect(page.locator("#first-request")).to_have_value("Keep this research draft unchanged")
    assert draft.evaluate("node => node === document.getElementById('first-request')")
    assert page.evaluate("""() => [...document.querySelectorAll('[data-i18n]')].every(
        node => node.childElementCount === 0
          && node.textContent === SimjectureI18n.t(node.dataset.i18n))""")
    assert page.evaluate("localStorage.getItem('simjecture-language')") == "zh-CN"
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(tmp_path / f"workspace-zh-CN-{width}.png"), full_page=True)

    page.reload()
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    expect(page.get_by_label("Interface language", exact=True)).to_have_value("zh-CN")
    page.goto(base + f"/monitor?campaign={campaign}")
    expect(page.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    expect(page.locator('[data-i18n="monitor.evidenceHelp"]')).to_contain_text("独立评估")
    expect(page.locator("#new-run-button")).to_have_text("New hypothesis")
    page.evaluate("renderExecutions()")
    expect(page.locator("#execution-list")).to_contain_text("尚未记录数值计算运行")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(tmp_path / f"monitor-zh-CN-{width}.png"), full_page=True)
    choose_language(page, "en")
    expect(page.locator('[data-i18n="monitor.evidenceHelp"]')).to_contain_text(
        "Recorded experiments"
    )
    expect(page.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")
    page.go_back()
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator('[data-i18n="workspace.homeIntro"]')).to_have_text(
        "What are we investigating?"
    )
    page.reload()
    expect(page.get_by_label("Interface language", exact=True)).to_have_value("en")
    page.close()
    reopened = page.context.new_page()
    reopened.goto(base + "/workspace")
    expect(reopened.locator("html")).to_have_attribute("lang", "en")
    assert reopened.evaluate("localStorage.getItem('simjecture-language')") == "en"


def test_dynamic_help_preserves_draft_nodes_and_expanded_details(language_site, language_page):
    base, project, _ = language_site
    page, expect = language_page
    page.goto(base + "/workspace#" + urlencode({"project": project, "view": "interactive"}))
    expect(page.locator("#project-title")).to_have_text("Untranslated research conversation")
    page.locator("#chat-input").fill("Do not translate or replace this draft")
    draft = page.locator("#chat-input").element_handle()
    folder = page.locator("#project-files + details")
    folder.evaluate("node => node.open = true")
    choose_language(page, "zh-CN")
    expect(page.locator("#project-files")).to_contain_text("智能体创建的文件")
    expect(page.locator("#brief-summary")).to_have_text(
        "尚未规划研究。问题明确后，可打开 Autonomous study。"
    )
    # Exercise the same renderer used by polling, after the language has changed.
    page.evaluate("renderProject()")
    expect(page.locator("#project-files")).to_contain_text("智能体创建的文件")
    expect(page.locator("#solver-development-help")).to_contain_text("求解器副本")
    # Research data stays English even when it happens to match a UI catalog entry.
    page.evaluate("""() => {
        state.project.brief = {question: 'What are we investigating?'};
        renderProject();
    }""")
    expect(page.locator("#brief-summary")).to_have_text("What are we investigating?")
    choose_language(page, "en")
    expect(page.locator("#project-files")).to_have_text(
        "Files you upload and files your agent creates appear here."
    )
    expect(page.locator("#chat-input")).to_have_value("Do not translate or replace this draft")
    assert draft.evaluate("node => node === document.getElementById('chat-input')")
    assert folder.evaluate("node => node.open")
    expect(page.locator("#project-title")).to_have_text("Untranslated research conversation")


def test_open_tabs_share_language_and_storage_removal(language_site, language_page):
    base, _, campaign = language_site
    page, expect = language_page
    page.goto(base + "/workspace")
    monitor = page.context.new_page()
    monitor.goto(base + f"/monitor?campaign={campaign}")
    expect(monitor.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")
    choose_language(page, "zh-CN")
    expect(monitor.locator("html")).to_have_attribute("lang", "zh-CN")
    expect(monitor.get_by_label("Interface language", exact=True)).to_have_value("zh-CN")
    choose_language(monitor, "en")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    choose_language(page, "zh-CN")
    expect(monitor.locator("html")).to_have_attribute("lang", "zh-CN")
    monitor.evaluate("localStorage.removeItem('simjecture-language')")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    # Returning to a cached page re-reads preferences without writing a default.
    monitor.evaluate("dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))")
    expect(monitor.locator("html")).to_have_attribute("lang", "en")
    assert monitor.evaluate("localStorage.getItem('simjecture-language')") is None


def test_missing_chinese_copy_falls_back_to_english(language_site, language_page):
    base, _, _ = language_site
    page, expect = language_page
    page.goto(base + "/workspace")
    # Simulate an incomplete catalog without shipping a deliberately missing translation.
    page.evaluate("delete SimjectureMessages['workspace.homeIntro']['zh-CN']")
    choose_language(page, "zh-CN")
    expect(page.locator('[data-i18n="workspace.homeIntro"]')).to_have_text(
        "What are we investigating?"
    )
    expect(page.locator('[data-i18n="workspace.interactiveSummary"]')).to_contain_text("运行代码与仿真")
    assert page.evaluate("SimjectureI18n.t('unknown.message')") == "unknown.message"


@pytest.mark.parametrize("saved", ["fr", "zh", ""])
def test_unsupported_preferences_use_english(language_site, language_page, saved):
    base, _, _ = language_site
    page, expect = language_page
    page.add_init_script(f"localStorage.setItem('simjecture-language', {json.dumps(saved)})")
    page.goto(base + "/workspace")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.get_by_label("Interface language", exact=True)).to_have_value("en")
    assert page.evaluate("localStorage.getItem('simjecture-language')") == saved


def test_language_switch_works_when_storage_is_blocked(language_site, language_page):
    base, _, _ = language_site
    page, expect = language_page
    page.add_init_script("""
        Object.defineProperty(window, 'localStorage', {
          get() { throw new DOMException('Storage blocked', 'SecurityError'); }
        });
    """)
    page.goto(base + "/monitor")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    choose_language(page, "zh-CN")
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    choose_language(page, "en")
    expect(page.locator("html")).to_have_attribute("lang", "en")
