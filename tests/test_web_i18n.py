"""Shared UI language behavior on the real localhost workspace and monitor."""

import importlib.util
import json
import re
import sys
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
    picker = page.locator("[data-language-select]")
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
            keys = re.findall(
                r'data-i18n(?:-(?:placeholder|title|aria-label|aria-valuetext|alt|label))?="([^"]+)"',
                html,
            )
            assert keys
            for key in keys:
                assert messages[key]["en"]
                assert messages[key]["zh-CN"]
        for key, entry in messages.items():
            assert entry.get("en"), key
            assert entry.get("zh-CN"), key
            assert set(re.findall(r"\{(\w+)\}", entry["en"])) == set(
                re.findall(r"\{(\w+)\}", entry["zh-CN"])
            ), key


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
    expect(page.locator("#new-project")).to_have_text("＋ 新建对话")
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
    expect(page.locator("[data-language-select]")).to_have_value("zh-CN")
    page.goto(base + f"/monitor?campaign={campaign}")
    expect(page.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    expect(page.locator('[data-i18n="monitor.evidenceHelp"]')).to_contain_text("独立评估")
    expect(page.locator("#new-run-button")).to_have_text("新建假设")
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
    expect(page.locator("[data-language-select]")).to_have_value("en")
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
        "尚未规划研究。问题明确后，可打开自主研究。"
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
    expect(monitor.locator("[data-language-select]")).to_have_value("zh-CN")
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
    expect(page.locator('[data-i18n="workspace.interactiveSummary"]')).to_contain_text(
        "运行代码与仿真"
    )
    assert page.evaluate("SimjectureI18n.t('unknown.message')") == "unknown.message"


@pytest.mark.parametrize("saved", ["fr", "zh", ""])
def test_unsupported_preferences_use_english(language_site, language_page, saved):
    base, _, _ = language_site
    page, expect = language_page
    page.add_init_script(f"localStorage.setItem('simjecture-language', {json.dumps(saved)})")
    page.goto(base + "/workspace")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    expect(page.locator("[data-language-select]")).to_have_value("en")
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


def test_bound_labels_keep_children_focus_and_raw_content(language_site, language_page):
    base, _, _ = language_site
    page, expect = language_page
    page.goto(base + "/workspace")
    page.evaluate("""() => {
        const label = document.createElement('label'); label.id = 'bound-label';
        SimjectureI18n.text(label, 'ui.reason');
        const input = document.createElement('input'); input.id = 'bound-input';
        input.value = 'running {p0} <b>unchanged</b>';
        label.append(input); document.body.append(label); input.focus();
        window.boundInput = input;
        const raw = document.createElement('p'); raw.id = 'raw-ui-word';
        raw.dataset.i18n = 'ui.reason';
        SimjectureI18n.content(raw, 'Reason'); document.body.append(raw);
        const report = document.createElement('div'); report.id = 'raw-ui-markdown';
        report.dataset.i18n = 'ui.loading-campaign';
        SimjectureI18n.render(report, 'Reason', text => report.textContent = text);
        document.body.append(report);
        SimjectureI18n.attribute(input, 'placeholder',
          () => SimjectureI18n.t('ui.reason'));
        SimjectureI18n.attribute(input, 'title',
          () => SimjectureI18n.t('ui.reason'));
        SimjectureI18n.setLanguage('zh-CN');
    }""")
    expect(page.locator("#bound-label")).to_have_text("原因")
    expect(page.locator("#bound-input")).to_have_attribute("placeholder", "原因")
    expect(page.locator("#bound-input")).to_have_attribute("title", "原因")
    expect(page.locator("#bound-input")).to_be_focused()
    expect(page.locator("#raw-ui-word")).to_have_text("Reason")
    expect(page.locator("#raw-ui-markdown")).to_have_text("Reason")
    assert page.evaluate("boundInput === document.getElementById('bound-input')")
    expect(page.locator("#bound-input")).to_have_value("running {p0} <b>unchanged</b>")
    # Parameter contents are literal text, never HTML or recursively substituted.
    assert page.evaluate("""() => {
        SimjectureMessages['test.template'] = {en:'{name}: {value}', 'zh-CN':'{name}：{value}'};
        const node = document.createElement('p'); document.body.append(node);
        SimjectureI18n.text(node, 'test.template',
          {name:'{value}', value:'<img onerror=alert(1)>'});
        return node.childElementCount === 0
          && node.textContent === '{value}：<img onerror=alert(1)>';
    }""")
    page.evaluate("""() => {
        SimjectureI18n.attribute(boundInput, 'title', () => null);
        SimjectureI18n.setLanguage('en');
    }""")
    expect(page.locator("#bound-label")).to_have_text("Reason")
    expect(page.locator("#bound-input")).to_be_focused()
    assert page.locator("#bound-input").get_attribute("title") is None


def test_budget_dialog_live_switch_and_exact_payload(language_site, language_page):
    base, _, campaign = language_site
    page, expect = language_page
    page.goto(base + "/workspace")
    expect(page.locator("#account-button")).to_be_enabled()
    page.evaluate(
        """campaign => {
        window.budgetFixture = {supported:true, deadline:1900000000, remaining_seconds:3600,
            can_extend:true, operating_limits:{worker_action_limit:7, worker_checkpoint_seconds:90,
              review_seconds:120}};
        StudyBudget.open({campaign, budget:budgetFixture,
            submit:async payload => {window.budgetPayload = payload; return {};},
            onSaved:async()=>{}});
    }""",
        campaign,
    )
    dialog = page.locator("dialog[open]")
    expect(dialog).to_have_attribute("aria-label", "Extend study time")
    amount = dialog.locator('input[type="number"]')
    amount.fill("2.5")
    dialog.locator("textarea").fill("Keep this user reason in English")
    field = amount.element_handle()
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(dialog).to_have_attribute("aria-label", "延长研究时间")
    expect(dialog.locator('button[type="submit"]')).to_have_text("增加 2.5 小时")
    expect(amount).to_have_value("2.5")
    assert field.evaluate("node => node.isConnected")
    page.evaluate("SimjectureI18n.setLanguage('en')")
    expect(dialog.locator('button[type="submit"]')).to_have_text("Add 2.5 hours")
    dialog.locator('button[type="submit"]').click()
    payload = page.evaluate("budgetPayload")
    assert payload.pop("request_key")
    assert payload == dict(
        campaign=campaign,
        hours=2.5,
        reason="Keep this user reason in English",
        expected_deadline=1900000000,
    )
    page.evaluate(
        """campaign => {
        const root = document.createElement('section'); root.id = 'budget-settings';
        document.body.append(root);
        StudyBudget.render(root, {campaign, budget:budgetFixture, readonly:false,
            submitLimits:async payload => {window.limitPayload = payload;},
            onLimitsSaved:async()=>{}});
    }""",
        campaign,
    )
    page.locator("#budget-settings").get_by_role("button", name="Run settings").click()
    dialog = page.locator("dialog[open]")
    fields = dialog.locator('input[type="number"]')
    fields.nth(0).fill("9")
    dialog.locator("textarea").fill("English operator rationale")
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(dialog).to_have_attribute("aria-label", "研究运行设置")
    expect(fields.nth(0)).to_have_value("9")
    expect(dialog.locator("label").first).to_contain_text("执行智能体每轮操作数")
    dialog.locator('button[type="submit"]').click()
    assert page.evaluate("limitPayload") == dict(
        campaign=campaign,
        limits=dict(worker_action_limit=9, worker_checkpoint_seconds=90, review_seconds=120),
        reason="English operator rationale",
    )


def test_monitor_dialog_accessibility_and_state_unchanged(language_site, language_page):
    base, _, campaign = language_site
    page, expect = language_page
    page.goto(base + f"/monitor?campaign={campaign}")
    expect(page.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")
    before = page.evaluate("JSON.stringify(state.snapshot)")
    page.locator("#new-run-button").click()
    dialog = page.locator("#new-run-dialog")
    draft = dialog.locator('textarea[name="hypothesis"]')
    draft.fill("running: this scientific hypothesis stays English")
    model = page.locator("#launch-model")
    model.fill("fixture-model")
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    # Read synchronously: polling must not mask a placeholder overwriting research.
    assert page.evaluate("document.getElementById('root-hypothesis').textContent") == (
        "Untranslated scientific hypothesis"
    )
    expect(dialog.locator("h2")).to_have_text("向 Simjecture 提出一个假设")
    expect(draft).to_have_value("running: this scientific hypothesis stays English")
    expect(model).to_have_value("fixture-model")
    expect(page.locator("#theme-button")).to_have_attribute("aria-label", re.compile("主题"))
    assert page.evaluate("JSON.stringify(state.snapshot)") == before
    assert page.evaluate("""() => {
        const n=document.createElement('span');setBadge(n,'budget_exhausted','budget_exhausted');
        document.body.append(n);window.rawStatusBadge=n;
        return n.dataset.status==='budget_exhausted' && n.textContent==='预算已耗尽';
    }""")
    page.evaluate("SimjectureI18n.setLanguage('en')")
    assert page.evaluate("rawStatusBadge.textContent") == "budget exhausted"
    assert page.evaluate("rawStatusBadge.dataset.status") == "budget_exhausted"
    expect(draft).to_have_value("running: this scientific hypothesis stays English")


def test_workspace_api_payload_does_not_depend_on_language(language_site, language_page):
    base, project, _ = language_site
    page, expect = language_page
    page.goto(base + "/workspace#" + urlencode({"project": project, "view": "interactive"}))
    expect(page.locator("#project-title")).to_have_text("Untranslated research conversation")
    payloads = []

    def capture(route):
        payloads.append(route.request.post_data_json)
        route.fulfill(json={"ok": True})

    page.route("**/api/workspace/i18n-fixture", capture)
    payload = dict(
        project=project,
        status="running",
        reasoning_effort="high",
        machine_ids=["local"],
        message="Keep user and research content in English",
    )
    before = page.evaluate("JSON.stringify(state.project)")
    page.evaluate("payload => api('i18n-fixture', payload)", payload)
    choose_language(page, "zh-CN")
    assert page.evaluate("JSON.stringify(state.project)") == before
    page.evaluate("payload => api('i18n-fixture', payload)", payload)
    choose_language(page, "en")
    assert payloads == [payload, payload]
    assert page.evaluate("JSON.stringify(state.project)") == before


def test_machine_form_keeps_persisted_default_name_in_both_languages(language_site, language_page):
    base, _, _ = language_site
    page, expect = language_page
    payloads = []

    def capture(route):
        payloads.append(route.request.post_data_json)
        route.fulfill(status=400, json={"error": "Fixture: no machine was saved"})

    page.route("**/api/workspace/save-machine", capture)
    page.goto(base + "/workspace#machines")
    expect(page.locator("#account-button")).to_be_enabled()
    for language in ["en", "zh-CN"]:
        page.evaluate("language => SimjectureI18n.setLanguage(language)", language)
        page.evaluate("fillMachine()")
        page.locator("#machine-advanced").evaluate("node => node.open = true")
        page.locator("#machine-kind").select_option("local")
        page.locator("#save-machine").click()
        expect(page.locator("#machine-form-error")).to_have_text("Fixture: no machine was saved")
        page.locator("#cancel-machine-editor").click()
    expected = dict(
        id="local", kind="local", label="This computer", python="python3",
        config=dict(execution_backend="bubblewrap", capabilities=[]),
    )
    assert payloads == [expected, expected]


def test_tour_and_model_summary_update_without_replacing_controls(language_site, language_page):
    base, _, _ = language_site
    page, expect = language_page
    page.goto(base + "/workspace")
    expect(page.locator("#home-backend")).to_be_attached()
    page.evaluate("WorkspaceTour.start()")
    expect(page.locator("#tour-title")).to_have_text("Ask your agent anything")
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(page.locator("#tour-title")).to_have_text("向智能体提问")
    expect(page.locator(".tour-skip")).to_have_text("跳过引导")
    expect(page.locator("#tour-body")).to_contain_text("描述一个问题")
    page.locator(".tour-next").click()
    page.evaluate("SimjectureI18n.setLanguage('en')")
    expect(page.locator(".tour-skip")).to_have_text("Skip tour")
    page.evaluate("WorkspaceTour.stop()")
    expect(page.locator("#home-agent-picker")).to_be_enabled()
    expect(page.locator('#home-model option[value="__custom__"]')).to_be_attached()
    page.evaluate("""() => {
        document.getElementById('home-model').value='__custom__';
        document.getElementById('home-custom-model').value='my-exact-model';
        WorkspaceComposer.refresh('home');
    }""")
    expect(page.locator("#home-agent-picker .agent-picker-summary")).to_have_text("my-exact-model")
    choose_language(page, "zh-CN")
    expect(page.locator("#home-agent-picker .agent-picker-summary")).to_have_text("my-exact-model")
    expect(page.locator("#home-custom-model")).to_have_value("my-exact-model")


def test_source_audit_distinguishes_copy_from_data(tmp_path, monkeypatch, capsys):
    script = Path(__file__).resolve().parents[1] / "scripts/check_web_i18n.py"
    spec = importlib.util.spec_from_file_location("check_web_i18n", script)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    monkeypatch.setattr(audit, "STATIC", tmp_path)
    (tmp_path / "fixture.html").write_text("""
        <span data-i18n="ui.reason">Reason</span>
        <button>run</button><input placeholder="Describe the task">
        <code>research/RESULTS.md</code>
    """)
    (tmp_path / "fixture.js").write_text("""
        // Ignore this English comment and /a regular expression/.
        const matcher = /[{}"']/;
        const route = "/api/fixture", status = "running";
        const request = {prompt: "Keep these scientific instructions in English"};
        node.textContent = "loading";
        node.setAttribute("aria-label", "dismiss");
        node.append(el("button", "start"));
        const copy = enabled ? "Open report" : "Close report";
        const nested = `Progress ${enabled ? `Batch ${count} checked` : "Still waiting"}`;
        const html = "<p>Generated interface help</p>";
        const localized = SimjectureI18n.message("ui.reason");
    """)
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor/third-party.js").write_text('node.textContent = "Vendor label"')
    records = audit.audit()
    pending = {row["text"] for row in records if row["category"] == "unresolved"}
    assert pending >= {
        "run",
        "Describe the task",
        "loading",
        "dismiss",
        "start",
        "Open report",
        "Close report",
        "Batch {value} checked",
        "Still waiting",
        "Generated interface help",
    }
    assert not any(row["text"] == "Vendor label" for row in records)
    assert any(row["text"] == "ui.reason" and row["category"] == "localized" for row in records)
    technical = {row["text"] for row in records if row["category"] == "technical"}
    assert {"/api/fixture", "running", "research/RESULTS.md"} <= technical
    assert "Keep these scientific instructions in English" in technical
    monkeypatch.setattr(sys, "argv", [str(script), "--check", "--json"])
    assert audit.main() == 1
    assert json.loads(capsys.readouterr().out)["counts"]["unresolved"] >= 10


def test_builtin_descriptions_and_status_labels_remain_live(language_site, language_page):
    base, _, campaign = language_site
    page, expect = language_page
    page.goto(base + "/workspace#tools")
    description = page.locator('[data-tool="freecad"] .research-tool-description')
    expect(description).to_have_text("Parametric CAD and STEP geometry")
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(description).to_have_text("参数化 CAD 与 STEP 几何建模")
    expect(description).to_have_attribute("title", "参数化 CAD 与 STEP 几何建模")
    # A user-defined tool or new server wording passes through the explicit boundary.
    assert page.evaluate("""() => {
        const raw = 'This custom tool description must remain English';
        return SimjectureI18n.known('ui.tool-description.freecad', raw) === raw;
    }""")
    page.evaluate("SimjectureI18n.setLanguage('en')")
    expect(description).to_have_text("Parametric CAD and STEP geometry")
    page.goto(base + f"/monitor?campaign={campaign}")
    expect(page.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(page.locator("#metric-claims-detail")).to_contain_text("科学")
    expect(page.locator("#research-trace")).to_contain_text("不会根据 token 总数推算")
    expect(page.locator("#research-trace")).to_contain_text("此记录尚无已完成轮次")
    expect(page.locator("#claim-graph .node-id")).to_have_text("科学")
    expect(page.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")


@pytest.mark.parametrize("language", ["en", "zh-CN"])
def test_monitor_launch_form_keeps_raw_contract(language_site, language_page, language):
    base, _, campaign = language_site
    page, expect = language_page
    payloads = []

    def capture(route):
        if route.request.method == "POST":
            payloads.append(route.request.post_data_json)
            route.fulfill(status=400, json={"error": "Fixture: no study was launched"})
        else:
            route.continue_()

    page.route("**/api/campaigns", capture)
    page.goto(base + f"/monitor?campaign={campaign}")
    expect(page.locator("#new-run-button")).to_be_enabled()
    page.locator("#new-run-button").click()
    page.evaluate("language => SimjectureI18n.setLanguage(language)", language)
    form = page.locator("#new-run-form")
    form.locator('[name="backend"]').select_option("codex")
    form.locator('[name="model"]').fill("fixture-model")
    form.locator("#launch-solver-development").select_option("readonly")
    form.locator('[name="hypothesis"]').fill("Keep this hypothesis in English")
    form.locator('[name="instruction"]').fill("Keep exact scientific instructions")
    expected = page.evaluate("""() => {
        const data = Object.fromEntries(new FormData(document.getElementById('new-run-form')));
        return {mode:'minimal', backend:'codex', model:'fixture-model',
          execution_backend:data.execution_backend, capability_directory:null,
          hypothesis:'Keep this hypothesis in English',
          instruction:'Keep exact scientific instructions',
          campaign_id:null, max_wall_seconds:Number(data.max_wall_seconds),
          max_command_seconds:Number(data.max_command_seconds), allow_solver_development:false};
    }""")
    page.locator("#launch-button").click()
    expect(page.locator("#new-run-error")).to_have_text("Fixture: no study was launched")
    assert payloads == [expected]
    expect(form.locator('[name="hypothesis"]')).to_have_value("Keep this hypothesis in English")


def test_benchmark_switch_updates_labels_and_keeps_raw_effort_filter(language_site, language_page):
    base, _, _ = language_site
    page, expect = language_page
    page.goto(base + "/workspace#benchmarks")
    expect(page.locator("#benchmark-tasks article")).to_have_count(2)
    expect(page.locator("#benchmark-leaderboard tbody tr").first).to_be_visible()
    expect(page.locator("#toast")).to_be_hidden()
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(page.locator("#benchmark-price-note")).to_contain_text("按公开的标准短上下文")
    expect(page.locator("#benchmark-tasks")).to_contain_text("CSV 诊断数据")
    expect(page.locator("#benchmark-tasks")).to_contain_text("CSV 能量核算")
    expect(page.locator("#benchmark-task-tabs")).to_contain_text("RZ 等离子体诊断")
    expect(page.locator("#benchmark-task-brief")).to_contain_text("可复现分析")
    effort = page.locator("#benchmark-effort-filter")
    effort.select_option("high")
    expect(effort).to_have_value("high")
    label = page.evaluate("SimjectureI18n.label('high')")
    rows = page.locator("#benchmark-leaderboard tbody tr")
    expect(rows.first.locator(":scope > td").nth(2)).to_have_text(label)
    existing = rows.count()
    page.evaluate("SimjectureI18n.setLanguage('en')")
    expect(effort).to_have_value("high")
    expect(rows).to_have_count(existing)
    expect(rows.first.locator(":scope > td").nth(2)).to_have_text("high")
    expect(page.locator("#benchmark-task-brief")).to_contain_text("Write a reproducible analysis")
    expect(page.locator("#toast")).to_be_hidden()


def test_research_markdown_stays_raw_while_generated_controls_update(language_site, language_page):
    base, _, _ = language_site
    page, expect = language_page
    page.goto(base + "/workspace")
    markdown = (
        "Reason\n\n```python\nprint('running')\n```\n\n"
        "![](https://example.invalid/empty.png)\n\n"
        "![Figure](https://example.invalid/caption.png)"
    )
    page.evaluate(
        """markdown => {
        const target = document.createElement('div'); target.id = 'rich-fixture';
        document.body.append(target);
        WorkspaceRich.render(target, markdown, null);
    }""",
        markdown,
    )
    target = page.locator("#rich-fixture")
    expect(target.locator("code")).to_have_text("print('running')\n")
    original_code = target.locator("code").text_content()
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(target.locator(".code-toolbar button")).to_have_text("复制")
    expect(target.locator(".code-toolbar button")).to_have_attribute("aria-label", "复制代码")
    expect(target.locator('a[href="https://example.invalid/empty.png"]')).to_have_text("图片")
    expect(target.locator('a[href="https://example.invalid/caption.png"]')).to_have_text("Figure")
    assert target.locator("code").text_content() == original_code
    expect(target.locator("p").first).to_have_text("Reason")
    page.evaluate("SimjectureI18n.setLanguage('en')")
    expect(target.locator(".code-toolbar button")).to_have_text("Copy")
    expect(target.locator('a[href="https://example.invalid/empty.png"]')).to_have_text("Figure")
    assert target.locator("code").text_content() == original_code


def test_legacy_stages_graph_values_and_contract_expansion_stay_stable(
    language_site, language_page
):
    base, _, campaign = language_site
    page, expect = language_page
    page.goto(base + f"/monitor?campaign={campaign}")
    expect(page.locator("#root-hypothesis")).to_have_text("Untranslated scientific hypothesis")
    page.evaluate("""() => {
        state.pollInFlight = true;
        const root = state.snapshot.claim_graph.nodes[0].id;
        state.snapshot.engine = {mode:'mvp'};
        state.snapshot.snapshot.loop_state = {stage:'commissioning', role:'researcher', cycle:1,
          status:'active', active_claim_id:root, detail:'Searching for a counterexample.'};
        state.snapshot.commissioning = {stages:[{id:'stage-fixture',node_type:'stage',
          stage:'commissioning',status:'pending',scientific_claim_id:root,
          claim_ids:[],binding_count:0}]};
        state.snapshot.claim_details[root].evidence_contracts = [
          {version:1, observable:'Keep scientific observation text in English'}];
        state.selectedClaim = root;
        renderLoopProgress(state.snapshot); renderInspector();
        window.rawGraphFixture = JSON.stringify(graphData());
    }""")
    active = page.locator(".loop-stage.active")
    expect(active).to_have_attribute("data-stage", "commissioning")
    detail = page.locator(".contract-card details")
    detail.locator("summary").click()
    expect(detail).to_have_attribute("open", "")
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    expect(active).to_have_attribute("data-stage", "commissioning")
    expect(active).to_have_text("验证工具")
    assert page.evaluate("JSON.stringify(graphData()) === rawGraphFixture")
    assert page.evaluate("""() => {
        const graph=graphData();
        return graph.edges.some(e=>e.relation==='enables evidence for')
          && graph.nodes.every(n=>typeof n.statement==='string');
    }""")
    # Polling an unchanged record must retain the same expansion identity.
    page.evaluate("renderInspector()")
    expect(detail).to_have_attribute("open", "")
    expect(detail.locator("summary")).to_have_text("观测量")
    expect(detail).to_contain_text("Keep scientific observation text in English")
    page.evaluate("""() => {
        state.snapshot.snapshot.loop_state.stage = 'repair';
        renderLoopProgress(state.snapshot);
    }""")
    expect(active).to_have_attribute("data-stage", "repair")
    page.evaluate("SimjectureI18n.setLanguage('en')")
    expect(active).to_have_attribute("data-stage", "repair")
    expect(active).to_have_text("Repair")
    page.evaluate("renderInspector()")
    expect(detail).to_have_attribute("open", "")
    expect(detail.locator("summary")).to_have_text("Observable")
