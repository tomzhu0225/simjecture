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
            card = page.locator('[data-machine="local"]')
            playwright.expect(card).to_contain_text("Online", timeout=30000)
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
            playwright.expect(page.locator("#machine-grid")).to_contain_text("Online")
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


def test_two_field_dialog_and_advanced_settings_persist_without_model_calls(tmp_path, monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")
    from conjecture_solver.execution_pool import MachineRegistry
    from conjecture_solver.worker_protocol import load, private_put

    prepared = []

    def prepare(registry, identifier):
        prepared.append(identifier)
        private_put(
            registry.root / "preparation" / identifier / "state.json", {"status": "working"}
        )
        return {"message": "Fixture preparation started"}

    monkeypatch.setattr(MachineRegistry, "start_prepare", prepare)
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    # Only this fixture's SSH endpoint is synthetic.
    app.workspace.poll_machine_availability = lambda: None
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"http://127.0.0.1:{server.server_port}/workspace#machines")
            page.get_by_role("button", name="Add machine", exact=True).click()
            assert page.locator("#machine-form input:visible").count() == 2
            page.locator("#machine-address").fill("ssh -p 23 root@fixture.example")
            page.locator("#machine-password").fill("fixture-only-secret")
            page.locator("#save-machine").click()
            playwright.expect(page.locator("#machine-dialog")).not_to_be_visible()
            card = page.locator("[data-machine]").first
            playwright.expect(card).to_contain_text("Preparing")
            records = app.workspace.machine_registry.catalogue()
            assert len(records) == 1
            record = records[0]
            identifier = record["machine"]["id"]
            assert record["machine"]["automatic_setup"]["execution_backend"] == "auto"
            assert record["has_password"] and "fixture-only-secret" not in __import__("json").dumps(
                records
            )
            assert prepared == [identifier]
            card.get_by_role("button", name="Settings", exact=True).click()
            assert page.locator("#machine-form input:visible").count() == 2
            page.locator("#machine-advanced > summary").click()
            page.locator("#machine-label-input").fill("My P40")
            page.locator("#machine-memory").fill("6144")
            page.locator("#machine-gpus").fill("none")
            page.locator("#save-machine").click()
            playwright.expect(card).to_contain_text("My P40")
            saved = app.workspace.machine_registry.machine(identifier)
            assert saved.automatic_setup.memory_mb == 6144 and saved.automatic_setup.gpu_ids == []
            private_put(
                app.workspace.machine_registry.root / "preparation" / identifier / "state.json",
                {"status": "ready"},
            )
            profile = load(app.workspace.machine_registry.path(identifier))
            profile["availability"] = {
                "online": True,
                "status": "ready",
                "checked_at": __import__("time").time(),
            }
            private_put(app.workspace.machine_registry.path(identifier), profile)
            playwright.expect(card).to_contain_text("Online")
            card.get_by_role("button", name="Prepare with agent", exact=True).click()
            playwright.expect(page.locator("#chat-input")).to_have_value(
                __import__("re").compile(".*execution_machines.*", __import__("re").DOTALL)
            )
            assert not list(app.workspace.projects_root.glob("*/turns/*"))
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
