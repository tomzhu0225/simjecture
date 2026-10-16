"""Report routing, parked inference and usage coverage in the actual monitor."""

import threading
from pathlib import Path

import pytest

from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("surface", ["monitor", "workspace"])
def test_budget_dialog_extends_the_clock_and_retains_job_limits(
    tmp_path, monkeypatch, width, surface,
):
    from conjecture_solver.research_budget import budget_status
    from conjecture_solver.web.workspace import load

    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path / "runs")
    monkeypatch.setattr(
        app.workspace, "default_agent", lambda: {"backend": "builtin", "model": "fixture"}
    )
    project = app.workspace.create({"name": "Budget control fixture"})
    directory = app.workspace.directory(project["id"])
    service = ResearchService.create(
        directory / "studies/001-budget", "A bounded budget-control fixture", wall_seconds=600,
        report_reserve_seconds=60,
    )
    original = service.manifest["deadline"]
    (service.root / "supervisor").mkdir()
    put(service.root / "supervisor/state.json", dict(status="paused", deadline=original))
    receipt = dict(id="fixed-job", status="running", timeout=20,
                   execution_deadline=original, started_at=original - 600)
    put(service.root / "experiments/fixed-job.json", receipt)
    campaign = app.registry.register(service.root)
    put(directory / "project.json", load(directory / "project.json") | {"studies": [dict(
        campaign=campaign, campaign_id="001-budget", path=str(service.root),
        question=service.manifest["hypothesis"],
    )]})
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page(viewport=dict(width=width, height=1050))
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            route = (
                f"/monitor?campaign={campaign}" if surface == "monitor" else
                f"/workspace#project={project['id']}&study={campaign}&view=autonomous"
            )
            page.goto(f"http://127.0.0.1:{server.server_port}" + route)
            page.get_by_role("button", name="Extend time", exact=True).click()
            dialog = page.get_by_role("dialog", name="Extend study time")
            dialog.get_by_role("button", name="+12 h", exact=True).click()
            assert dialog.get_by_label("Additional hours").input_value() == "12"
            dialog.get_by_label("Reason (optional)").fill("Observe the post-collision window")
            shots = Path("artifacts/workspace-preview")
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots / f"study-budget-dialog-{surface}-{width}.png"))
            dialog.get_by_role("button", name="Add 12 hours", exact=True).click()
            playwright.expect(dialog).not_to_be_visible()
            page.get_by_text("Budget history · 1 extension", exact=True).wait_for()
            assert service.manifest["deadline"] == original + 43200
            assert service.manifest["finalization_policy"]["compute_deadline"] == original + 43140
            assert service._read("experiments", "fixed-job") == receipt
            assert budget_status(service.root)["revision"] == 1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors
            shots = Path("artifacts/workspace-preview")
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots / f"study-budget-{surface}-{width}.png"), full_page=True)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("width", [1440, 390])
def test_monitor_routes_report_and_displays_wait_and_unknown_usage(tmp_path, monkeypatch, width):
    playwright = pytest.importorskip("playwright.sync_api")
    service = ResearchService.create(
        tmp_path / "study", "A bounded scientific question", wall_seconds=600
    )
    (service.work / "RESULTS.md").write_text(
        "The hypothesis remains unresolved; inspect the failed control."
    )
    service.wait("Await operator feedback on the retained result", for_operator=True)
    (service.root / "supervisor").mkdir()
    put(
        service.root / "supervisor/state.json",
        dict(
            status="running",
            deadline=service.manifest["deadline"],
            usage_by_thread={
                "worker": dict(input_tokens=1000, cached_input_tokens=900, output_tokens=20)
            },
            usage_roles_by_thread={"worker": "worker"},
            usage_unreported_threads={"missing-director": "director"},
        ),
    )
    monkeypatch.setattr("conjecture_solver.web.application._is_live", lambda root: True)
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    campaign = app.registry.register(service.root)
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as runtime:
            if not Path(runtime.chromium.executable_path).is_file():
                pytest.skip("Chromium is not installed")
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page(viewport=dict(width=width, height=1050))
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/monitor?campaign={campaign}")
            panel = page.locator("#research-trace")
            playwright.expect(panel).to_contain_text("Worker awaiting feedback")
            playwright.expect(panel).to_contain_text("Reported totals are a minimum")
            button = page.get_by_role("button", name="Assess current report")
            playwright.expect(button).to_be_enabled()
            button.click()
            playwright.expect(panel).to_contain_text("Report queued")
            assert len(service._all("report_requests")) == 1
            assert not service.status()["completed"]
            assert not errors
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            screenshot = Path("artifacts/workspace-preview") / f"harness-feedback-{width}.png"
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot), full_page=True)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_report_control_preserves_read_only_boundary_and_requires_running_study(
    tmp_path, monkeypatch
):
    service = ResearchService.create(tmp_path / "study", "A bounded report fixture")
    (service.work / "RESULTS.md").write_text("Unresolved; check a matched control next.")
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", allow_mutations=False)
    campaign = app.registry.register(service.root)
    from conjecture_solver.web.application import WebApplicationError

    with pytest.raises(WebApplicationError, match="read-only"):
        app.control(campaign, "assess-report")
    app.allow_mutations = True
    monkeypatch.setattr("conjecture_solver.web.application._is_live", lambda root: False)
    with pytest.raises(WebApplicationError, match="running minimal"):
        app.control(campaign, "assess-report")
    assert not service._all("report_requests")
