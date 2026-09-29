"""Real browser acceptance: fresh install, numerical preflight, visible demo.

Run with the workspace and browser dependencies installed. Downloads optional
runtimes into a new artifacts/iter-pack/oneclick-* deployment; makes no LLM calls.
"""

import json
import os
import shutil
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server

repo = Path(__file__).resolve().parents[1]
output = repo / "artifacts/iter-pack"
root = output / ("oneclick-" + str(int(time.time())))
root.mkdir()
for folder in ("skills", "capabilities", "environments", "scripts"):
    shutil.copytree(repo / folder, root / folder)
for name in ("pyproject.toml", "uv.lock"):
    shutil.copyfile(repo / name, root / name)
os.chdir(root)
app = SimjectureWebApplication(runs_root=root / "runs", scan_roots=(root / "runs",))
server = create_server(app, port=0)
threading.Thread(target=server.serve_forever, daemon=True).start()
errors = []
started = time.time()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{server.server_port}/")
        page.get_by_role("button", name="Research tools", exact=False).click()
        card = page.locator('[data-tool="iter-pack"]')
        card.get_by_role("button", name="Install", exact=True).click()
        print("Clicked Install on fresh deployment:", root, flush=True)
        deadline = time.time() + 900
        last = 0
        while time.time() < deadline:
            rows = app.workspace.catalogue()
            tool = next(t for t in rows if t["id"] == "iter-pack")
            if tool["state"] == "tested":
                break
            if tool["state"] == "failed":
                raise RuntimeError(json.dumps(tool["report"]))
            if time.time() - last > 30:
                print(tool["state"], tool.get("log", "")[-400:], flush=True)
                last = time.time()
            page.wait_for_timeout(1000)
        else:
            raise TimeoutError("Install exceeded 15 minutes")
        page.screenshot(path=str(output / "oneclick-installed.png"), full_page=True)
        card.get_by_role("button", name="Run demo", exact=True).click()
        print("Clicked Run demo", flush=True)
        deadline = time.time() + 120
        while time.time() < deadline:
            projects = app.workspace.projects()
            if projects:
                project = app.workspace.project(projects[0]["id"])
                jobs = project["simulations"]
                if jobs and jobs[-1]["status"] in {"failed", "timed_out", "succeeded"}:
                    break
            page.wait_for_timeout(500)
        assert jobs[-1]["status"] == "succeeded", jobs[-1]
        directory = (
            app.workspace.directory(project["id"]) / "simulations" / jobs[-1]["id"] / "workspace"
        )
        demo = json.loads((directory / "iter_pack_demo.json").read_text())
        assert all(demo["checks"].values()), demo
        page.wait_for_timeout(2000)
        page.screenshot(path=str(output / "oneclick-demo.png"), full_page=True)
        assert not errors, errors
        result = {
            "root": str(root),
            "install_and_demo_seconds": time.time() - started,
            "checks": demo["checks"],
            "browser_errors": errors,
            "project": project["id"],
            "outputs": str(directory),
        }
        (output / "oneclick-result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2), flush=True)
        browser.close()
finally:
    server.shutdown()
    server.server_close()
