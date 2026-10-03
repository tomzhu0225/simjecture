"""The scientific progress advisory is visible in the existing run monitor."""

import json
import threading
import time
from pathlib import Path

import pytest

from conjecture_solver.research_service import ResearchService, put, sha
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("register_target", [True, False])
def test_recorded_progress_and_cost_are_visible(tmp_path, width, register_target):
    playwright = pytest.importorskip("playwright.sync_api")
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    s = ResearchService.create(
        tmp_path / "study", "A radiation contribution bound", wall_seconds=600
    )
    (s.work / "calc.py").write_text("print(1)\n")
    identifier = "exp_" + "b" * 24
    workspace = s.root / "experiments" / identifier / "workspace"
    workspace.mkdir(parents=True)
    p = workspace / "result.json"
    p.write_text(json.dumps({"actual_end_ns": 2}))
    put(
        s.root / "experiments" / (identifier + ".json"),
        dict(
            id=identifier,
            status="succeeded",
            created_at=time.time(),
            stage="exploration",
            binding=s._binding("calc.py", (), (), None),
            outputs=["result.json"],
            execution={"wall_seconds": 13500},
            artifacts={"result.json": {"sha256": sha(p), "bytes": p.stat().st_size}},
        ),
    )
    live_id = "exp_" + "c" * 24
    put(
        s.root / "experiments" / (live_id + ".json"),
        dict(
            id=live_id,
            status="running",
            created_at=time.time(),
            stage="exploration",
            binding=s._binding("calc.py", (), (), None),
            outputs=["result.json"],
            cancel_requested=True,
            stop_reason="An affordable full trajectory is needed.",
            monitor={"path": "progress.json", "target": 40.0},
            telemetry=dict(
                available=True,
                value=2,
                target=40,
                unit="ns",
                quantity="Live 3D time",
                elapsed_seconds=600,
                estimated_additional_seconds=11400,
                authority="Mutable operational telemetry; not scientific evidence",
            ),
        ),
    )
    (s.root / "director").mkdir()
    put(
        s.root / "director" / "director_test.json",
        dict(
            id="director_test",
            created_at=time.time(),
            decision="replan",
            scientific_feasibility="limited",
            budget_feasibility="infeasible",
            rationale="This early-time calculation cannot reach the radiation peak in budget.",
            next_action="Test a complete adaptive trajectory before refining diagnostics.",
            control_actions=[dict(experiment=live_id, status="running")],
        ),
    )
    if register_target:
        s.progress(
            experiment=identifier,
            output="result.json",
            path="actual_end_ns",
            quantity="3D physical time",
            unit="ns",
            target=20.5,
            estimate_rate=True,
        )
    campaign = app.registry.register(s.root)
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as runtime:
            if not Path(runtime.chromium.executable_path).is_file():
                pytest.skip("Chromium is not installed")
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": 1050})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/monitor?campaign={campaign}")
            panel = page.locator(".scientific-progress")
            playwright.expect(panel).to_contain_text("Measured execution:")
            playwright.expect(panel).to_contain_text("Live 3D time: 2 ns / target 40 ns")
            playwright.expect(panel).to_contain_text("not scientific evidence")
            director = page.locator(".research-director")
            playwright.expect(director).to_contain_text("budget infeasible")
            playwright.expect(director).to_contain_text("Awaiting worker plan or challenge")
            playwright.expect(director).to_contain_text("awaiting confirmation")
            if register_target:
                playwright.expect(panel).to_contain_text("3D physical time: 2 ns / target 20.5 ns")
                playwright.expect(panel).to_contain_text("Exceeds remaining wall budget")
                link = panel.get_by_role("link", name="View recorded metric")
                path = f"experiments%2F{identifier}%2Fworkspace%2Fresult.json"
            else:
                playwright.expect(panel).to_contain_text("calc.py")
                link = panel.get_by_role("link", name="View execution receipt")
                path = f"experiments%2F{identifier}.json"
            playwright.expect(link).to_have_attribute(
                "href",
                f"/api/artifact?campaign={campaign}&path={path}",
            )
            output = Path("artifacts/workspace-preview")
            output.mkdir(parents=True, exist_ok=True)
            panel.scroll_into_view_if_needed()
            page.screenshot(
                path=str(output / f"scientific-progress-{width}-{register_target}.png"),
                full_page=True,
            )
            assert not errors
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
