"""Rendered shared-navigation acceptance checks; require Playwright and Chromium.

All studies and conversations are local fixtures. No provider calls or real launches
are needed. These checks complement, rather than replace, deterministic client tests.
"""

import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from conjecture_solver.web.workspace import load


@pytest.fixture
def navigation_case(tmp_path, monkeypatch):
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    monkeypatch.setattr(
        app.workspace, "default_agent", lambda: {"backend": "builtin", "model": "fixture"}
    )
    project = app.workspace.create({"name": "Navigation fixture conversation"})
    directory = app.workspace.directory(project["id"])
    studies = []
    for name, question in [
        ("001-original", "Original study: account for the boundary energy"),
        ("002-follow-up", "Follow-up study: resolve the axial modes"),
    ]:
        study = ResearchService.create(directory / "studies" / name, question)
        (study.work / "calculation.py").write_text("print(1)\n")
        studies.append(
            dict(
                campaign=app.registry.register(study.root),
                campaign_id=name,
                question=question,
                path=str(study.root),
            )
        )
    put(directory / "project.json", load(directory / "project.json") | {"studies": studies})
    standalone = ResearchService.create(tmp_path / "cli-study", "Standalone CLI fixture")
    standalone_campaign = app.registry.register(standalone.root)
    return app, project["id"], studies, standalone_campaign


@pytest.fixture
def rendered_page():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        executable = Path(runtime.chromium.executable_path)
        if not executable.is_file():
            pytest.skip(f"Playwright Chromium executable is not installed: {executable}")
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            yield page, playwright.expect
            assert not errors
        finally:
            browser.close()


@contextmanager
def serve(app):
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def workspace_route(project, campaign, view="autonomous"):
    return "/workspace#" + urlencode(dict(project=project, study=campaign, view=view))


def assert_workspace_route(page, project, campaign, view):
    params = parse_qs(urlsplit(page.url).fragment)
    assert params["project"] == [project]
    assert params["study"] == [campaign]
    assert params["view"] == [view]


def screenshot(page, name):
    directory = Path("artifacts/workspace-preview")
    directory.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(directory / f"navigation-{name}.png"), full_page=True)


@pytest.mark.parametrize("width", [1440, 390])
def test_owned_conversation_study_evidence_round_trip_and_reload(
    navigation_case, rendered_page, width
):
    app, project, studies, _ = navigation_case
    page, expect = rendered_page
    original = studies[0]["campaign"]
    page.set_viewport_size({"width": width, "height": 1050 if width > 400 else 844})
    with serve(app) as base:
        page.goto(base + workspace_route(project, original, "interactive"))
        nav = page.get_by_role("navigation", name="Research navigation", exact=True)
        expect(nav.locator('[aria-current="page"]')).to_have_text("Conversation")
        nav.get_by_role("link", name="Study", exact=True).click()
        expect(nav.locator('[aria-current="page"]')).to_have_text("Study")
        expect(page.locator(f"#study-{original}")).to_have_class("study-card selected-study")
        assert_workspace_route(page, project, original, "autonomous")
        nav.get_by_role("link", name="Evidence & review", exact=True).click()
        expect(page.locator("#root-hypothesis")).to_have_text(studies[0]["question"])
        expect(nav.locator('[aria-current="page"]')).to_have_text("Evidence & review")
        assert parse_qs(urlsplit(page.url).query)["campaign"] == [original]
        screenshot(page, f"owned-evidence-{width}")
        nav.get_by_role("link", name="Conversation", exact=True).click()
        expect(page.locator("#interactive-panel")).to_be_visible()
        assert_workspace_route(page, project, original, "interactive")
        page.get_by_role("button", name="Autonomous research", exact=True).click()
        expect(page.locator(f"#study-{original}")).to_have_class("study-card selected-study")
        page.reload()
        expect(page.locator(f"#study-{original}")).to_have_class("study-card selected-study")
        assert_workspace_route(page, project, original, "autonomous")
        assert len(app.workspace.projects()) == 1
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        screenshot(page, f"owned-study-{width}")


def test_campaign_picker_back_forward_restores_context(navigation_case, rendered_page):
    app, project, studies, _ = navigation_case
    page, expect = rendered_page
    original, newer = [study["campaign"] for study in studies]
    with serve(app) as base:
        page.goto(base + f"/monitor?campaign={original}")
        expect(page.locator("#root-hypothesis")).to_have_text(studies[0]["question"])
        page.get_by_label("Select campaign").select_option(newer)
        expect(page.locator("#root-hypothesis")).to_have_text(studies[1]["question"])
        assert parse_qs(urlsplit(page.url).query)["campaign"] == [newer]
        page.go_back()
        expect(page.locator("#root-hypothesis")).to_have_text(studies[0]["question"])
        expect(page.get_by_label("Select campaign")).to_have_value(original)
        page.go_forward()
        expect(page.locator("#root-hypothesis")).to_have_text(studies[1]["question"])
        expect(page.get_by_label("Select campaign")).to_have_value(newer)
        page.locator("#conversation-return").click()
        expect(page.locator("#interactive-panel")).to_be_visible()
        assert_workspace_route(page, project, newer, "interactive")


@pytest.mark.parametrize("readonly", [False, True])
def test_direct_cli_evidence_is_standalone_and_readonly_safe(
    navigation_case, rendered_page, readonly
):
    app, _, _, standalone = navigation_case
    app.allow_mutations = not readonly
    page, expect = rendered_page
    with serve(app) as base:
        page.goto(base + f"/monitor?campaign={standalone}")
        nav = page.get_by_role("navigation", name="Research navigation", exact=True)
        expect(nav.get_by_text("Standalone study", exact=True)).to_be_visible()
        expect(nav.get_by_role("link", name="Conversation", exact=True)).to_have_count(0)
        expect(nav.get_by_role("link", name="Study", exact=True)).to_have_count(0)
        expect(page.locator("#conversation-return")).to_have_text("Workspace")
        expect(page.locator("#conversation-return")).to_have_attribute("href", "/workspace")
        assert len(app.workspace.projects()) == 1
        if readonly:
            expect(page.locator("#continue-study-link")).to_be_hidden()
            expect(page.locator("#steer-study-link")).to_be_hidden()
            for control in ["pause-button", "resume-button", "cancel-button"]:
                expect(page.locator(f"#{control}")).to_be_disabled()
        screenshot(page, f"standalone-{'readonly' if readonly else 'editable'}")


def test_owned_continuation_cancel_escape_and_repeated_submit_reuse_conversation(
    navigation_case, rendered_page
):
    app, project, studies, _ = navigation_case
    page, expect = rendered_page
    original = studies[0]["campaign"]
    prepares = []
    page.on(
        "request",
        lambda request: prepares.append(request.post_data_json)
        if request.url.endswith("/api/workspace/prepare-continuation")
        else None,
    )
    with serve(app) as base:
        for dismiss in ["cancel", "escape"]:
            page.goto(base + f"/monitor?campaign={original}")
            page.get_by_role("link", name="Continue investigation", exact=True).click()
            dialog = page.get_by_role("dialog", name="Continue investigation", exact=True)
            expect(dialog).to_be_visible()
            assert_workspace_route(page, project, original, "autonomous")
            if dismiss == "cancel":
                dialog.get_by_role("button", name="Cancel", exact=True).click()
            else:
                page.keyboard.press("Escape")
            expect(dialog).to_have_count(0)
            assert prepares == []
            assert len(app.workspace.projects()) == 1
            assert not app.workspace.project(project).get("continuation_draft")

        page.locator(f"#study-{original}").get_by_role(
            "button", name="Continue investigation", exact=True
        ).click()
        dialog = page.get_by_role("dialog", name="Continue investigation", exact=True)
        dialog.get_by_label("What should the next phase investigate?").fill(
            "Compare boundary flux with independent energy accounting"
        )
        dialog.get_by_label("New wall-time budget (hours)").fill("2")
        # Two events in one JavaScript turn cover duplicate submissions before a response.
        dialog.locator("form").evaluate(
            """form => {
              const submitter = form.querySelector('button[value="direct"]');
              for (let i=0;i<2;i++) form.dispatchEvent(new SubmitEvent('submit',
                {bubbles:true,cancelable:true,submitter}));
            }"""
        )
        expect(page.locator("#prepared-heading")).to_have_text("CONTINUATION PROPOSAL")
        expect(page.locator("#prepared-brief")).to_be_visible()
        assert len(prepares) == 1
        assert prepares[0]["project"] == project
        assert prepares[0]["campaign"] == original
        assert len(app.workspace.projects()) == 1
        saved = app.workspace.project(project)
        assert saved["continuation_draft"]["campaign"] == original
        assert len(saved["studies"]) == 2
        screenshot(page, "owned-continuation")
