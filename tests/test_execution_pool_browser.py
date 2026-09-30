"""Visible machine preparation and study pool selection, without a model call."""

import threading
from pathlib import Path

import httpx
import pytest

from conjecture_solver.execution import probe_execution_backend
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def test_machine_page_prepares_worker_and_preserves_study_selection(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    if not probe_execution_backend("bubblewrap")["available"]:
        pytest.skip("Numerical launcher needs Bubblewrap namespaces")
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#machines")
            page.locator("#register-local-worker").click()
            page.locator('#machine-form button[type="submit"]').click()
            card = page.locator('[data-machine="local"]')
            playwright.expect(card).to_contain_text("Not prepared")
            card.get_by_role("button", name="Prepare worker", exact=True).click()
            playwright.expect(card).to_contain_text("Execution ready", timeout=30000)
            project = app.workspace.create({"name": "Pool proposal"})
            app.workspace.save_brief(
                project["id"],
                {
                    "question": "A finite pool fixture",
                    "success_criteria": "Verified numerical data",
                    "constraints": "Local worker only",
                    "machine_ids": ["local"],
                },
            )
            page.goto(
                f"http://127.0.0.1:{server.server_port}/workspace#project={project['id']}&view=autonomous"
            )
            playwright.expect(page.locator("#prepared-details")).to_contain_text("local")
            playwright.expect(page.locator("#study-machines")).to_have_values(["local"])
            from conjecture_solver.research_service import ResearchService

            parent = ResearchService.create(
                tmp_path / "parent",
                "Worker-pool continuation",
                execution_pool=app.workspace.machine_registry.freeze(["local"]),
            )
            continuation = app.workspace.prepare_continuation(
                {
                    "campaign": app.registry.register(parent.root),
                    "guidance": "Test a new regime",
                    "hours": 1,
                    "files": [],
                },
                app,
            )
            followup = app.workspace.project(continuation["project"])
            assert followup["brief"]["machine_ids"] == ["local"]
            # Agent-prepared drafts inherit the same pool unless explicitly changed.
            app.workspace.save_brief(
                continuation["project"],
                {
                    "question": "A refined question",
                    "success_criteria": "Verified controls",
                    "constraints": "Original pool",
                    "hours": 1,
                },
            )
            assert app.workspace.project(continuation["project"])["brief"]["machine_ids"] == [
                "local"
            ]
            shots = Path("artifacts/ssh-feature")
            shots.mkdir(parents=True, exist_ok=True)
            page.locator('[data-view="machines"]').click()
            playwright.expect(page.locator("#machine-grid")).to_contain_text("Execution ready")
            page.screenshot(path=str(shots / "machines-page.png"), full_page=True)
            assert not list(app.workspace.projects_root.glob("*/turns/*"))
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


def test_readonly_machine_api_has_no_provisioning_side_effects(tmp_path):
    app = SimjectureWebApplication(
        scan_roots=(tmp_path,), runs_root=tmp_path / "runs", allow_mutations=False
    )
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        boot = httpx.get(url + "/api/workspace/bootstrap").json()
        assert httpx.get(url + "/api/workspace/machines").json()["machines"] == []
        response = httpx.post(
            url + "/api/workspace/save-machine",
            json={"id": "test", "host": "example.invalid", "root": "/tmp/test"},
            headers={"X-Simjecture-Token": boot["control_token"]},
        )
        assert response.status_code == 403
        assert not app.workspace.machine_registry.root.exists()
    finally:
        server.shutdown()
        server.server_close()
