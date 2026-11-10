"""Live agent text and the subagent panel from the local conversation view."""

import os
import sys
import threading

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def test_live_text_and_subagent_panel(tmp_path, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    binary = tmp_path / "grok"
    binary.write_text(
        f"#!{sys.executable}\n"
        + """
import json, os, time
from pathlib import Path
def emit(value):
    print(json.dumps(value), flush=True)
def delta(kind, **fields):
    emit({'type':'stream_event','event':{'type':'content_block_delta',
          'delta':{'type':kind, **fields}}})
delta('thinking_delta', thinking='private test reasoning')
delta('text_delta', text='Checking the ')
delta('text_delta', text='two runs.')
gate = Path(os.environ['SIMJECTURE_TEST_GATE'])
while not gate.exists():
    time.sleep(.05)
if Path('CONTEXT.json').exists():
    Path('result.txt').write_text('done')
    Path('HELPER_RESULT.json').write_text(json.dumps({
        'status':'completed', 'summary':'Completed the assigned local data check.',
        'artifacts':['result.txt'], 'checks':['result saved'], 'unresolved':[]}))
emit({'type':'result','subtype':'success','result':'Both checks finished.'})
"""
    )
    binary.chmod(0o755)
    gate = tmp_path / "release"
    monkeypatch.setenv("SIMJECTURE_TEST_GATE", str(gate))
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    app = SimjectureWebApplication(runs_root=tmp_path / "data", scan_roots=(tmp_path / "data",))
    ws = app.workspace
    project = ws.create(
        {"name": "Convergence check", "agent": {"backend": "grok", "model": "grok-test"}}
    )
    project_id = project["id"]
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(
                f"http://127.0.0.1:{server.server_port}/workspace#project={project_id}&view=interactive"
            )
            playwright.expect(page.locator("#project-title")).to_have_text(project["name"])
            page.locator("#chat-input").focus()
            panel = page.locator("#subagent-panel")
            playwright.expect(panel).to_be_hidden()
            ws.send(project_id, {"message": "Check convergence at two grid resolutions."})
            playwright.expect(page.locator(".live-answer")).to_have_text(
                "Checking the two runs.", timeout=15000
            )
            assert "private test reasoning" not in page.locator("#messages").inner_text()
            tasks = [
                dict(
                    name=name,
                    task="Inspect the measurements.",
                    completion_criteria="Write the result.",
                    outputs=["result.txt"],
                    input_files=[],
                )
                for name in ("Grid convergence", "Mass balance")
            ]
            ws.start_subagents(project_id, {"tasks": tasks, "wait": False})
            playwright.expect(panel.locator("a")).to_have_count(2)
            playwright.expect(panel.locator("a").first).to_be_visible()
            playwright.expect(page.locator("#chat-input")).to_be_focused()
            playwright.expect(page.locator("#subagent-count")).to_have_text("2 active")
            page.keyboard.press("Escape")
            playwright.expect(panel.locator("a").first).to_be_hidden()
            page.locator("#subagent-toggle").click()
            page.set_viewport_size({"width": 390, "height": 844})
            box = page.locator("#subagent-list").bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= 390
            page.set_viewport_size({"width": 1440, "height": 900})
            page.locator("#subagent-list").get_by_role(
                "link", name="Mass balance", exact=False
            ).click()
            playwright.expect(page.locator("#simulation-detail h3")).to_have_text("Mass balance")
            gate.touch()
            playwright.expect(page.locator(".message.assistant .message-content")).to_have_text(
                "Both checks finished.", timeout=15000
            )
            playwright.expect(page.locator("#subagent-count")).to_have_text("2")
            playwright.expect(page.locator(".live-answer")).to_have_count(0)
            assert errors == []
            browser.close()
    finally:
        gate.touch()
        server.shutdown()
        server.server_close()
        thread.join()
