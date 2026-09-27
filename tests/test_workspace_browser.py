"""Browser acceptance checks. Install Playwright + Chromium to run locally."""

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
            page.get_by_role("button", name="API connections").click()
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
            page.get_by_role("button", name="Draft from this conversation").click()
            page.locator("#interactive-panel").wait_for(state="visible")
            playwright.expect(page.locator("#send-message")).to_be_enabled(timeout=40000)
            page.get_by_role("button", name="Autonomous research", exact=True).click()
            page.locator("#prepared-question").wait_for()
            page.screenshot(path=str(screenshots / "study-brief.png"), full_page=True)
            from conjecture_solver.execution import probe_execution_backend

            if probe_execution_backend("bubblewrap")["available"]:
                page.get_by_role("button", name="Start research ↗", exact=True).click()
                page.get_by_text("COMPLETED", exact=True).wait_for(timeout=90000)
                page.get_by_text("Accepted: falsified.", exact=False).wait_for()
                page.get_by_text("Results, reports, and simulation files", exact=True).click()
                page.get_by_role("link", name="result.json", exact=False).first.wait_for()
                page.screenshot(path=str(screenshots / "accepted-result.png"), full_page=True)
            page.get_by_role("button", name="Interactive research", exact=True).click()
            page.locator("#conversation-model").select_option("fixture-alternate")
            playwright.expect(page.locator("#agent-switch-warning")).to_be_visible()
            playwright.expect(page.locator("#agent-switch-warning")).to_contain_text("cache reuse")
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
            page.wait_for_function("customElements.get('wa-tab-group') !== undefined")
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
            page.wait_for_function("document.querySelector('#rich-test img').naturalWidth > 0")
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
            page.locator("#sidebar-run-list a").first.click()
            assert "simulation=" in page.url
            page.reload()
            page.locator("#simulation-detail h3").filter(has_text="Wave evolution").wait_for()
            assert "simulation=" + job["id"] in page.url
            assert page.locator("#interactive-panel").is_visible()
            page.screenshot(
                path="artifacts/workspace-preview/simulation-monitor.png", full_page=True
            )
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
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
            page.locator('[data-key="variants-flash"] summary').click()
            page.locator('[data-key="installation-flash"] summary').click()
            page.evaluate("window.scrollTo(0, 450)")
            tool["log"] = "updated log"
            page.evaluate("refreshTools()")
            assert page.locator('[data-key="variants-flash"]').get_attribute("open") is not None
            assert page.locator('[data-key="installation-flash"]').get_attribute("open") is not None
            assert page.evaluate("window.scrollY") == 450
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
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
