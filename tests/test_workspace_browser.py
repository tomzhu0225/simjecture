"""Browser acceptance checks. Install Playwright + Chromium to run locally."""

import shlex
import threading
from pathlib import Path

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server
from tests.test_workspace import provider as protocol_provider


@pytest.fixture
def provider():
    yield from protocol_provider.__wrapped__()


def test_browser_setup_chat_files_and_autonomous_handoff(tmp_path, provider):
    playwright = pytest.importorskip("playwright.sync_api")
    url, _requests = provider
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    screenshots = Path(__file__).resolve().parents[1] / "artifacts/workspace-preview"
    screenshots.mkdir(parents=True, exist_ok=True)
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}")
            page.get_by_role("button", name="Connections").click()
            page.locator("#base-url").fill(url)
            page.locator("#api-key").fill("test-secret")
            assert page.locator("#model").count() == 0
            page.get_by_role("button", name="Save API connection").click()
            page.get_by_text(
                "API connection saved. Choose its model in a conversation.", exact=True
            ).first.wait_for()
            assert page.locator("#api-key").input_value() == ""
            page.get_by_role("button", name="New conversation").click()
            assert page.locator("#quick-start #home-backend").count() == 1
            page.locator("#home-backend").select_option("builtin")
            page.locator("#home-model option[value='fixture-model']").wait_for(state="attached")
            page.locator("#home-model").select_option("fixture-model")
            page.locator("#home-effort").select_option("high")
            page.locator("#first-request").fill("Grill me to prepare an autonomous investigation.")
            page.locator("#first-request").press("Shift+Enter")
            assert page.locator("#first-request").input_value().endswith("\n")
            assert len(app.workspace.projects()) == 0
            page.screenshot(path=str(screenshots / "overview.png"), full_page=True)
            page.locator("#first-request").press("Enter")
            page.get_by_text(
                "What question should we test, and what time budget should I use?", exact=True
            ).wait_for(timeout=40000)
            playwright.expect(page.locator("#send-message")).to_be_enabled(timeout=40000)
            assert page.locator(".composer-bottom #conversation-backend").count() == 1
            route_box = page.locator("#conversation-backend").bounding_box()
            send_box = page.locator("#send-message").bounding_box()
            assert (
                abs(
                    (route_box["y"] + route_box["height"] / 2)
                    - (send_box["y"] + send_box["height"] / 2)
                )
                < 20
            )
            page.locator("#chat-input").fill("Calculate and prepare a counterexample study.")
            page.locator("#chat-input").press("Shift+Enter")
            assert page.locator("#chat-input").input_value().endswith("\n")
            page.locator("#chat-input").dispatch_event(
                "keydown", {"key": "Enter", "isComposing": True}
            )
            assert page.locator("#messages .message.user").count() == 1
            page.locator("#chat-input").press("Enter")
            page.get_by_text(
                "The calculation and editable study brief are ready.", exact=True
            ).wait_for(timeout=40000)
            page.get_by_role("link", name="observations.txt", exact=True).wait_for()
            assert "grill-me" in page.locator("#project-path").text_content()
            page.screenshot(path=str(screenshots / "interactive.png"), full_page=True)
            page.reload()
            page.get_by_text(
                "The calculation and editable study brief are ready.", exact=True
            ).wait_for()
            page.locator("#conversation-model option[value='fixture-model']").wait_for(
                state="attached"
            )
            assert page.locator("#conversation-backend").input_value() == "builtin"
            assert page.locator("#conversation-model").input_value() == "fixture-model"
            assert page.locator("#conversation-effort").input_value() == "high"
            page.get_by_role(
                "link", name="Review autonomous research proposal", exact=False
            ).click()
            assert "view=autonomous" in page.url
            assert "Euler" in page.locator("#brief-question").input_value()
            assert not page.locator("#brief-question").is_visible()
            playwright.expect(page.locator("#study-preparation")).to_be_hidden()
            playwright.expect(page.locator("#study-stage")).to_contain_text("Proposal ready")
            assert page.locator("#breadcrumb").count() == 0
            page.locator("#prepared-question").wait_for()
            page.screenshot(path=str(screenshots / "study-brief.png"), full_page=True)
            page.locator("#brief-editor > summary").click()
            page.locator("#brief-form .advanced > summary").click()
            playwright.expect(page.locator("#research-director")).to_be_checked()
            page.locator("#research-director").uncheck()
            page.locator("#review-model").fill("fixture-model")
            page.locator("#review-effort").select_option("high")
            assert page.locator("#research-director").bounding_box()["width"] <= 20
            page.screenshot(
                path=str(screenshots / "research-director-settings.png"), full_page=True
            )
            page.locator("#brief-editor > summary").click()
            from conjecture_solver.execution import probe_execution_backend

            if probe_execution_backend("bubblewrap")["available"]:
                page.get_by_role("button", name="Start research ↗", exact=True).click()
                page.get_by_text("COMPLETED", exact=True).wait_for(timeout=90000)
                from conjecture_solver.web.workspace import load

                project = app.workspace.projects()[0]
                saved = load(app.workspace.directory(project["id"]) / "project.json")
                request = load(Path(saved["studies"][-1]["path"]) / "study-launch.json")["request"]
                assert request["director_enabled"] is False
                assert request["judge_model"] == "fixture-model"
                assert request["judge_reasoning_effort"] == "high"
                page.get_by_text("Accepted: falsified.", exact=False).wait_for()
                page.get_by_text("Results, reports, and simulation files", exact=True).click()
                page.get_by_role("link", name="result.json", exact=False).first.wait_for()
                page.screenshot(path=str(screenshots / "accepted-result.png"), full_page=True)
            page.get_by_role("button", name="Interactive research", exact=True).click()
            if probe_execution_backend("bubblewrap")["available"]:
                page.get_by_text(
                    "The completed study found a reviewed counterexample.", exact=True
                ).wait_for(timeout=30000)
                playwright.expect(page.locator("#send-message")).to_be_enabled(timeout=30000)
            page.locator("#conversation-model").select_option("fixture-alternate")
            playwright.expect(page.locator("#agent-switch-warning")).to_be_visible()
            playwright.expect(page.locator("#agent-switch-warning")).to_contain_text("cache reuse")
            page.get_by_role("button", name="Dismiss session warning").click()
            playwright.expect(page.locator("#agent-switch-warning")).to_be_hidden()
            page.evaluate("renderProject()")
            playwright.expect(page.locator("#agent-switch-warning")).to_be_hidden()
            page.locator("#conversation-model").select_option("fixture-model")
            playwright.expect(page.locator("#agent-switch-warning")).to_be_hidden()
            page.locator("#conversation-model").select_option("fixture-alternate")
            playwright.expect(page.locator("#agent-switch-warning")).to_be_visible()
            page.locator("#conversation-model").select_option("fixture-model")
            playwright.expect(page.locator("#agent-switch-warning")).to_be_hidden()
            page.get_by_role("button", name="Research tools", exact=True).click()
            page.get_by_role("heading", name="Python research stack").wait_for()
            assert "✓ Installed" in page.locator("#installed-tool-grid").inner_text()
            assert "Not installed" in page.locator("#available-tool-grid").inner_text()
            page.screenshot(path=str(screenshots / "tools.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#home")
            page.locator("#first-request").wait_for()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
            assert errors == []
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_rich_chat_and_simulation_side_monitor(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    project = app.workspace.create({"name": "Wave figures"})
    directory = app.workspace.directory(project["id"])
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="160">'
        '<path d="M0 140L80 40L160 100L300 20" stroke="purple" fill="none"/></svg>'
    )
    (directory / "files/wave.svg").write_text(svg)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.context.grant_permissions(["clipboard-read", "clipboard-write"])
            base = f"http://127.0.0.1:{server.server_port}"
            page.goto(base + "/#project=" + project["id"])
            page.locator("#chat-input").wait_for()
            page.evaluate("() => customElements.whenDefined('wa-tab-group')")
            rich = r"""Inline $E=mc^2$ and \(\alpha_0\).

\[\frac{\partial u}{\partial t}=D\nabla^2 u\]

```python
print("wave")
# ![literal](wave.svg)
```

![Wave result](wave.svg)
"""
            page.evaluate(
                """([text, project]) => {
              const target = document.createElement('div'); target.id='rich-test';
              document.querySelector('#messages').append(target);
              WorkspaceRich.render(target, text, project);
            }""",
                [rich, app.workspace.project(project["id"])],
            )
            assert page.locator("#rich-test math").count() == 3
            assert page.locator("#rich-test .hljs-string").count() > 0
            assert page.locator("#rich-test code").inner_text().endswith("# ![literal](wave.svg)\n")
            assert page.locator("#rich-test figure").count() == 1
            figure = page.locator("#rich-test img")
            figure.scroll_into_view_if_needed()
            assert figure.evaluate("""img => new Promise((resolve, reject) => {
                if (img.complete) return resolve(img.naturalWidth > 0);
                const timer = setTimeout(() => reject(Error('Figure did not load')), 10000);
                img.addEventListener('load', () => {
                    clearTimeout(timer); resolve(img.naturalWidth > 0)
                }, {once:true});
                img.addEventListener('error', () => {
                    clearTimeout(timer); resolve(false)
                }, {once:true});
            })""")
            page.get_by_role("button", name="Copy code").click()
            playwright.expect(page.get_by_role("button", name="Copy code")).to_have_text("Copied")
            job = app.workspace.start_simulation(
                project["id"],
                dict(
                    name="Wave evolution",
                    command=(
                        "echo evolving; while [ ! -f continue ]; do sleep 0.1; done; "
                        "cp wave.svg result.svg; echo complete"
                    ),
                    timeout_seconds=45,
                ),
            )
            page.locator("#simulation-detail h3").filter(has_text="Wave evolution").wait_for(
                timeout=15000
            )
            playwright.expect(page.locator("#inspector-tabs")).to_have_attribute(
                "active", "simulations"
            )
            page.get_by_role("button", name="Stop run", exact=True).wait_for()
            (Path(job["work_directory"]) / "continue").touch()
            page.locator("#simulation-detail .live-console").filter(has_text="complete").wait_for(
                timeout=20000
            )
            page.locator("#simulation-detail a").filter(has_text="result.svg").wait_for()
            playwright.expect(page.locator("#simulation-detail .run-outputs")).to_contain_text(
                "result.svg"
            )
            playwright.expect(page.locator("#simulation-detail .run-outputs")).not_to_contain_text(
                "wave.svg"
            )
            assert not page.locator("#simulation-detail .run-inputs").evaluate("e => e.open")
            assert page.locator("#simulation-detail .run-inputs figure").count() == 0
            page.locator("#sidebar-run-list a").first.click()
            assert "simulation=" in page.url
            page.reload()
            page.locator("#simulation-detail h3").filter(has_text="Wave evolution").wait_for()
            assert "simulation=" + job["id"] in page.url
            assert page.locator("#interactive-panel").is_visible()
            command = app.workspace.start_simulation(
                project["id"],
                dict(name="Inspect environment", command="echo command-ready", kind="command"),
            )
            playwright.expect(page.locator("#command-count")).to_have_text("1", timeout=15000)
            playwright.expect(page.locator("#simulation-count")).to_have_text("1")
            playwright.expect(page.locator("#sidebar-run-list a")).to_have_count(1)
            playwright.expect(page.locator("#sidebar-run-list")).not_to_contain_text(
                "Inspect environment"
            )
            playwright.expect(page.locator("#inspector-tabs")).to_have_attribute(
                "active", "simulations"
            )
            page.locator('wa-tab[panel="commands"]').click()
            page.locator("#command-list a").click()
            assert "command=" + command["id"] in page.url
            page.reload()
            page.locator("#command-detail .live-console").filter(
                has_text="command-ready"
            ).wait_for()
            playwright.expect(page.locator("#command-detail .run-shared-files h4")).to_have_text(
                "Project files (shared)"
            )
            playwright.expect(page.locator("#inspector-tabs")).to_have_attribute(
                "active", "commands"
            )
            playwright.expect(page.locator("#simulation-list a")).to_have_count(1)
            page.locator("#sidebar-run-list a").click()
            page.locator("#simulation-detail h3").filter(has_text="Wave evolution").wait_for()
            original_width = page.locator(".conversation-column").bounding_box()["width"]
            page.get_by_role("button", name="Collapse left sidebar", exact=True).click()
            page.get_by_role("button", name="Collapse right sidebar", exact=True).click()
            assert not page.locator("#workspace-sidebar").is_visible()
            assert not page.locator("#research-inspector").is_visible()
            assert page.locator(".conversation-column").bounding_box()["width"] > original_width
            page.reload()
            page.get_by_role("button", name="Expand right sidebar", exact=True).wait_for()
            assert not page.locator("#workspace-sidebar").is_visible()
            assert not page.locator("#research-inspector").is_visible()
            page.get_by_role("button", name="Expand left sidebar", exact=True).click()
            page.locator("#sidebar-run-list a").click()
            assert page.locator("#research-inspector").is_visible()
            page.locator("#simulation-detail h3").filter(has_text="Wave evolution").wait_for()
            page.screenshot(
                path="artifacts/workspace-preview/simulation-monitor.png", full_page=True
            )
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            playwright.expect(page.locator("#workspace-sidebar")).not_to_be_visible()
            page.get_by_role("button", name="Collapse right sidebar", exact=True).click()
            assert not page.locator("#research-inspector").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.get_by_role("button", name="Expand left sidebar", exact=True).click()
            page.get_by_role("button", name="Expand right sidebar", exact=True).click()
            assert page.locator("#research-inspector").is_visible()
            assert errors == []
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_selected_simulation_files_do_not_mix_run_outputs_and_project_results(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    from tests.test_workspace_simulations import await_finished

    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    project = app.workspace.create({"name": "Separate run artifacts"})
    directory = app.workspace.directory(project["id"])
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50">'
        '<text y="30">{}</text></svg>'
    )
    (directory / "files/comparison.svg").write_text(svg.format("Shared comparison"))
    (directory / "files/input.txt").write_text("before")
    runs = []
    for number in (1, 2):
        command = "printf %s " + shlex.quote(svg.format(f"Run {number}")) + " > result.svg"
        if number == 1:
            command += "; printf 'after!' > input.txt"
        run = app.workspace.start_simulation(
            project["id"], dict(name=f"Case {number}", command=command)
        )
        assert await_finished(directory, run["id"])["status"] == "succeeded"
        runs.append(run)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            base = f"http://127.0.0.1:{server.server_port}"
            page.goto(base + "/#project=" + project["id"])
            for number, run in enumerate(runs, 1):
                page.locator("#sidebar-run-list a").filter(has_text=f"Case {number}").click()
                detail = page.locator("#simulation-detail")
                playwright.expect(detail.locator("h3")).to_have_text(f"Case {number}")
                outputs = detail.locator(".run-outputs")
                link = outputs.locator("a.file-row").filter(has_text="result.svg")
                link.wait_for()
                href = link.get_attribute("href")
                assert f"simulation={run['id']}" in href
                assert f"Run {number}" in page.request.get(base + href).text()
                playwright.expect(outputs).not_to_contain_text("comparison.svg")
                copied = detail.locator(".run-inputs")
                assert not copied.evaluate("e => e.open")
                assert copied.locator("figure").count() == 0
                copied.locator("summary").click()
                copied.get_by_role("link", name="comparison.svg", exact=True).wait_for()
                if number == 1:
                    outputs.get_by_role("link", name="input.txt", exact=True).wait_for()
                    playwright.expect(outputs).to_contain_text("Changed from the copied input")
                else:
                    playwright.expect(outputs).not_to_contain_text("input.txt")
                copied.locator("summary").click()
            page.reload()
            playwright.expect(page.locator("#simulation-detail h3")).to_have_text("Case 2")
            playwright.expect(page.locator("#simulation-detail .run-outputs")).not_to_contain_text(
                "comparison.svg"
            )
            page.locator('wa-tab[panel="files"]').click()
            playwright.expect(page.locator("#project-files")).to_contain_text("comparison.svg")
            playwright.expect(page.locator('wa-tab[panel="files"]')).to_have_text("Project files")
            assert errors == []
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_theme_and_confirmed_conversation_deletion(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    project = app.workspace.create({"name": "Disposable theme preview"})
    directory = app.workspace.directory(project["id"])
    (directory / "files/result.txt").write_text("output")
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, color_scheme="light")
            page.goto(f"http://127.0.0.1:{server.server_port}/#project=" + project["id"])
            page.locator("#chat-input").wait_for()
            page.get_by_role("button", name="Switch to dark mode").click()
            playwright.expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            page.reload()
            playwright.expect(page.locator("html")).to_have_attribute("data-theme", "dark")
            page.locator("#chat-input").wait_for()
            page.screenshot(path="artifacts/workspace-preview/dark-theme.png", full_page=True)
            page.get_by_role(
                "button", name="Delete conversation: Disposable theme preview", exact=True
            ).click()
            playwright.expect(page.locator("#delete-path")).to_have_text(str(directory))
            page.get_by_role("button", name="Cancel", exact=True).click()
            assert directory.exists()
            page.get_by_role(
                "button", name="Delete conversation: Disposable theme preview", exact=True
            ).click()
            page.get_by_role("button", name="Delete conversation and files", exact=True).click()
            page.locator("#delete-dialog").wait_for(state="hidden")
            assert not directory.exists()
            playwright.expect(page.locator("#project-list")).to_contain_text(
                "Your work will appear here"
            )
            page.get_by_role("button", name="Switch to light mode").click()
            playwright.expect(page.locator("html")).to_have_attribute("data-theme", "light")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_refresh_preserves_inspector_and_tool_details_and_dark_math(tmp_path, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    tool = dict(
        id="flash",
        name="FLASH",
        installed=True,
        registered=False,
        action="source",
        state="installed",
        readiness="unchecked",
        description="Installed solver",
        variants=[
            dict(label=f"Build {i}", runtime="/runtime/flash", description="Local build")
            for i in range(20)
        ],
        report={},
        log="initial log",
    )
    monkeypatch.setattr(app.workspace, "catalogue", lambda: [tool])
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{server.server_port}")
            page.get_by_role("button", name="Research tools", exact=True).click()
            page.locator('[data-tool="flash"]').get_by_role(
                "button", name="Details", exact=True
            ).click()
            page.locator('[data-key="variants-flash"] summary').click()
            page.locator('[data-key="installation-flash"] summary').click()
            page.locator("#tool-details-body").evaluate("e => e.scrollTop = 450")
            tool["log"] = "updated log"
            page.evaluate("refreshTools()")
            assert page.locator('[data-key="variants-flash"]').get_attribute("open") is not None
            assert page.locator('[data-key="installation-flash"]').get_attribute("open") is not None
            assert page.locator("#tool-details-body").evaluate("e => e.scrollTop") == 450
            page.get_by_role("button", name="Close tool details").click()
            result = page.evaluate(r"""async () => {
              state.view='home';
              history.replaceState(null,'','#home');
              document.querySelector('#view-tools').hidden=true;
              const project = {id:'fixture', files:[],
                simulations:[{id:'001-wave',name:'Wave',status:'running',live:true}]};
              let job = {...project.simulations[0], command:'python wave.py',
                created_at:Date.now()/1000,
                output:Array.from({length:100},(_,i)=>`step ${i}`).join('\n'),
                files:Array.from({length:20},(_,i)=>({name:`output-${i}.txt`}))};
              const monitor = WorkspaceMonitor.create({api:async()=>job,project:()=>project,
                link:()=> '#',notify:()=>{},readonly:()=>false});
              document.querySelector('#view-home').hidden=true;
              document.querySelector('#view-project').hidden=false;
              monitor.render(project);
              await monitor.open('001-wave');
              await new Promise(r=>setTimeout(r,100));
              const detail = document.querySelector('#simulation-detail details');
              detail.open=true;
              const console = document.querySelector('.live-console');
              console.scrollTop=90;
              const inspector=document.querySelector('.project-context');
              inspector.scrollTop=210;
              job={...job,output:job.output+'\nnew step'};
              await monitor.update();
              const kept={sameConsole:console===document.querySelector('.live-console'),
                open:detail.open,consoleScroll:console.scrollTop,inspectorScroll:inspector.scrollTop};
              WorkspaceTheme.set('dark');
              const math=document.createElement('div');math.className='message-content';
              document.querySelector('#messages').append(math);
              WorkspaceRich.render(math,
                String.raw`\[A=-0.05\ln\cosh(x/0.05)+0.05\cos(\pi x/2)\cos(\pi y)\]`,project);
              const equation=math.querySelector('math');
              kept.math=!!equation;
              kept.background=getComputedStyle(equation).backgroundColor;
              kept.color=getComputedStyle(equation).color;
              return kept;
            }""")
            assert result["sameConsole"] and result["open"] and result["math"]
            assert result["consoleScroll"] == 90 and result["inspectorScroll"] == 210
            assert result["background"] == "rgb(36, 41, 59)"
            assert result["color"] == "rgb(240, 237, 255)"
            tool.update(
                installed=False,
                state="failed",
                report={"ready": False, "error": "Package download failed"},
            )
            page.get_by_role("button", name="Research tools", exact=True).click()
            page.evaluate("refreshTools()")
            playwright.expect(page.locator('[data-tool="flash"]')).to_contain_text(
                "Needs attention"
            )
            page.locator('[data-tool="flash"]').get_by_role(
                "button", name="Details", exact=True
            ).click()
            page.locator('[data-key="diagnostics-flash"] summary').click()
            assert page.locator(".tool-failure").inner_text() == "Package download failed"
            assert page.locator(".tool-failure").is_visible()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_live_activity_updates_preserve_completed_message_nodes(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    project = app.workspace.create({"name": "Visible progress"})
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{server.server_port}/#project=" + project["id"])
            page.locator("#chat-input").wait_for()
            result = page.evaluate("""() => {
              state.view='home'; // keep polling out of this synthetic activity test
              const original = {role:'assistant',turn:'old',content:'Completed result',
                events:[],links:[],running:false};
              const active = {role:'assistant',turn:'new',content:'',
                events:[],links:[],running:true,
                started_at:Date.now()/1000-1800,last_activity_at:Date.now()/1000-3,
                monitored_runs:0,progress:'Inputs are prepared; checking the boundary mapping.',
                activity:{label:'Reading file',detail:'flash.par',recent_actions:[
                  {label:'Reading file',detail:'flash.par',status:'completed'}]}};
              state.project.messages=[original,active];
              renderProject();
              const old=document.querySelector('[data-message-key="assistant-old"]');
              active.activity={label:'Running command',detail:'Pilot simulation',recent_actions:[
                {label:'Running command',detail:'Pilot simulation',status:'running'}]};
              active.last_activity_at=Date.now()/1000;
              renderProject();
              return {preserved:old===document.querySelector('[data-message-key="assistant-old"]'),
                text:document.querySelector('[data-message-key="assistant-new"]').textContent};
            }""")
            assert result["preserved"]
            assert "Running command" in result["text"]
            assert "Pilot simulation" in result["text"]
            assert "Inputs are prepared" in result["text"]
            assert "0 monitored simulations" in result["text"]
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_cooperative_fallback_warning_is_visible_and_persistent(tmp_path):
    from conjecture_solver.execution import COOPERATIVE_WARNING

    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    app.workspace.execution = dict(
        backend="proot-cooperative",
        available=True,
        warning=COOPERATIVE_WARNING,
        reason="Probe passed",
    )
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{server.server_port}")
            playwright.expect(page.locator("#execution-warning-message")).to_have_text(
                COOPERATIVE_WARNING
            )
            assert page.locator("#execution-warning").is_visible()
            assert page.locator("#execution-backend").input_value() == "proot-cooperative"
            page.reload()
            playwright.expect(page.locator("#execution-warning-message")).to_have_text(
                COOPERATIVE_WARNING
            )
            assert page.locator("#execution-warning").is_visible()
            assert page.locator("#workspace-sidebar #execution-warning").count() == 1
            assert page.locator(".topbar").count() == 0
            page.get_by_role("button", name="Dismiss execution warning").click()
            assert not page.locator("#execution-warning").is_visible()
            page.reload()
            page.get_by_role("button", name="Limited isolation", exact=True).wait_for()
            assert not page.locator("#execution-warning").is_visible()
            page.get_by_role("button", name="Limited isolation", exact=True).click()
            assert page.locator("#execution-warning").is_visible()
            app.workspace.execution = dict(
                backend="bubblewrap",
                available=False,
                reason="bwrap: Namespace creation denied. https://example.invalid/diagnostic",
                fallback_unavailable="Missing proot executable",
            )
            page.reload()
            playwright.expect(page.locator("#execution-status")).to_have_text(
                "Experiments unavailable"
            )
            assert page.locator("#execution-warning").is_visible()
            assert "https://" not in page.locator("#execution-warning-message").inner_text()
            assert not page.locator("#execution-warning-diagnostics").is_visible()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_source_tools_open_agent_assisted_installation_conversations(tmp_path, monkeypatch):
    import re

    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    cards = [
        dict(
            id=identifier,
            name=name,
            action="agent",
            installed=False,
            state="available",
            description="Agent-assisted setup",
            report={},
            log="",
        )
        for identifier, name in [("flash", "FLASH"), ("warpx-cuda", "WarpX · CUDA")]
    ]
    monkeypatch.setattr(app.workspace, "catalogue", lambda: cards)
    installs = []
    monkeypatch.setattr(app.workspace, "start_install", lambda payload: installs.append(payload))
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{server.server_port}")
            for identifier, name, guide in [
                ("flash", "FLASH", "references/local-deployment.md"),
                ("warpx-cuda", "WarpX · CUDA", "references/local-cuda-deployment.md"),
            ]:
                page.get_by_role("button", name="Research tools", exact=True).click()
                page.locator(f'[data-tool="{identifier}"]').get_by_role(
                    "button", name="Install with agent", exact=True
                ).click()
                playwright.expect(page.locator("#project-title")).to_have_text(f"Install {name}")
                playwright.expect(page.locator("#chat-input")).to_have_value(
                    re.compile(re.escape(guide))
                )
                draft = page.locator("#chat-input").input_value()
                assert guide in draft and "read_skill" in draft
                assert "persistent named folders" in draft
                assert page.locator("#interactive-panel").is_visible()
                assert page.locator("#source-dialog").count() == 0
            assert not installs
            assert len(app.workspace.projects()) == 2
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_sidebar_edges_drag_closed_and_reopen(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    project = app.workspace.create({"name": "Panel gestures"})
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(f"http://127.0.0.1:{server.server_port}/#project={project['id']}")
            page.locator("#chat-input").wait_for()
            page.evaluate("() => customElements.whenDefined('wa-split-panel')")

            def drag(selector, end_x, y_offset=20):
                box = page.locator(selector).bounding_box()
                x, y = box["x"] + box["width"] / 2, box["y"] + min(y_offset, box["height"] / 2)
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(end_x, y, steps=16)
                page.mouse.up()

            drag("#left-sidebar-resizer", 2)
            playwright.expect(page.locator("#workspace-sidebar")).not_to_be_visible()
            drag("#left-sidebar-toggle", 280)
            playwright.expect(page.locator("#workspace-sidebar")).to_be_visible()
            assert abs(page.locator("#workspace-sidebar").bounding_box()["width"] - 280) < 2
            split = page.locator("#research-layout").bounding_box()
            drag('#research-layout [part="divider"]', split["x"] + split["width"] - 2)
            playwright.expect(page.locator("#research-inspector")).not_to_be_visible()
            drag("#right-sidebar-toggle", split["x"] + split["width"] - 340)
            playwright.expect(page.locator("#research-inspector")).to_be_visible()
            assert page.locator("#research-inspector").bounding_box()["width"] > 250
            page.get_by_role("button", name="Collapse left sidebar").click()
            page.get_by_role("button", name="Collapse right sidebar").click()
            page.reload()
            page.get_by_role("button", name="Expand right sidebar").wait_for()
            assert not page.locator("#workspace-sidebar").is_visible()
            assert not page.locator("#research-inspector").is_visible()
            page.screenshot(
                path="artifacts/workspace-preview/collapsed-edge-tabs.png", full_page=True
            )
            page.get_by_role("button", name="Expand left sidebar").click()
            page.get_by_role("button", name="Expand right sidebar").click()
            assert abs(page.locator("#workspace-sidebar").bounding_box()["width"] - 280) < 2
            page.screenshot(
                path="artifacts/workspace-preview/expanded-edge-tabs.png", full_page=True
            )
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_study_lifecycle_and_followup_keep_history(tmp_path):
    import json

    from conjecture_solver.web.workspace import load, put

    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path, scan_roots=(tmp_path,))
    w = app.workspace
    p = w.create({"name": "Repeated investigations"})
    directory = w.directory(p["id"])
    brief = dict(
        question="Euler positivity",
        success_criteria="Independent review",
        constraints="Python",
        hours=1,
        completion_policy="answer",
    )
    w.save_brief(p["id"], brief)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with playwright.sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            status = {"value": "running"}
            page.route(
                "**/api/workspace/study?*",
                lambda route: route.fulfill(
                    content_type="application/json",
                    body=json.dumps(
                        dict(
                            snapshot={"snapshot": {}, "controls": {}, "artifacts": []},
                            live={
                                "status": status["value"],
                                "activity": "Testing Euler",
                                "remaining": 25,
                            },
                            report={},
                            results="The step h=2 gives y1=-1.",
                        )
                    ),
                ),
            )
            page.goto(f"http://127.0.0.1:{server.server_port}/#project={p['id']}&view=autonomous")
            playwright.expect(page.locator("#prepared-brief")).to_be_visible()
            playwright.expect(page.locator("#study-preparation")).to_be_hidden()
            assert page.locator("#breadcrumb").count() == 0
            assert not page.locator("#machine-label").is_visible()

            record = load(directory / "project.json")
            record.update(
                brief_launched="first",
                studies=[
                    dict(
                        campaign="first",
                        campaign_id="001-euler",
                        question=brief["question"],
                        path=str(directory / "studies/001-euler"),
                    )
                ],
            )
            put(directory / "project.json", record)
            page.reload()
            playwright.expect(page.locator("#study-runs")).to_contain_text("RUNNING")
            playwright.expect(page.locator("#prepared-brief")).to_be_hidden()
            playwright.expect(page.locator("#study-preparation")).to_be_hidden()
            playwright.expect(page.locator("#new-study")).to_be_visible()
            status["value"] = "completed"
            page.reload()
            playwright.expect(page.locator("#study-runs")).to_contain_text("Study finished")
            assert (
                page.get_by_role("link", name="Return to the conversation")
                .get_attribute("href")
                .startswith("#project=")
            )
            playwright.expect(
                page.get_by_role("button", name="Explain in conversation")
            ).to_be_visible()

            # Study artifact links survive sanitization; foreign campaigns cannot resolve.
            rendered = page.evaluate("""() => {
              const target = document.createElement('div');
              const project = {id: 'test', studies: [{campaign: 'first'}]};
              WorkspaceRich.render(target, '[Report](study:first/research/RESULTS.md)', project);
              return [target.querySelector('a').getAttribute('href'),
                WorkspaceRich.artifactURL('study:foreign/research/RESULTS.md', project)];
            }""")
            assert "campaign=first" in rendered[0] and "RESULTS.md" in rendered[0]
            assert rendered[1] is None
            page.get_by_role("button", name="Prepare another study").click()
            playwright.expect(page.locator("#study-preparation")).to_be_visible()
            playwright.expect(page.locator("#study-runs")).to_contain_text("Euler positivity")
            page.reload()
            playwright.expect(page.locator("#study-preparation")).to_be_visible()
            playwright.expect(page.locator("#study-runs")).to_contain_text("COMPLETED")
            assert w.project(p["id"])["brief"] is None
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
