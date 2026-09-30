"""Visible recovery and usage details from the stagnation-audit fixes."""

import threading
import time
from pathlib import Path

import pytest

from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.server import create_server


def test_monitor_shows_credit_recovery_usage_and_alternative_instruments(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    study = ResearchService.create(tmp_path / "study", "An audit UI fixture", wall_seconds=3600)
    study.freeze_requirements({"required_capability_prefixes": ["flash-", "warpx-"]})
    manifest = study.manifest | {"capability_hashes": {"flash-fixture": "abc"}}
    put(study.root / "research.json", manifest)
    (study.root / "supervisor").mkdir()
    put(
        study.root / "supervisor/state.json",
        dict(
            status="paused_external_error",
            backend="builtin",
            model="fixture",
            mode="minimal",
            updated_at=time.time(),
            deadline=manifest["deadline"],
            last_error="Provider quota failure",
            provider_error_category="quota",
            provider_attention="Provider quota exhausted. Restore credit, then resume this study.",
            provider_wait_seconds=120,
            usage_by_thread={
                "turn-00001": dict(
                    input_tokens=1000,
                    output_tokens=20,
                    cached_input_tokens=0,
                    reasoning_output_tokens=0,
                    requests=2,
                    requests_without_usage=1,
                    cache_usage_complete=False,
                    reasoning_usage_complete=False,
                )
            },
        ),
    )
    app = SimjectureWebApplication(
        initial_run=study.root, scan_roots=(tmp_path,), runs_root=tmp_path / "runs"
    )
    token = app.registry.register(study.root)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/monitor?campaign={token}")
            playwright.expect(page.locator("#research-trace")).to_contain_text("Restore credit")
            playwright.expect(page.locator("#research-trace")).to_contain_text("2 tracked requests")
            playwright.expect(page.locator("#research-trace")).to_contain_text(
                "any of flash- or warpx-"
            )
            playwright.expect(page.locator("#token-breakdown")).to_contain_text(
                "Not fully reported"
            )
            shots = Path("artifacts/release-0.5.3rc1")
            shots.mkdir(parents=True, exist_ok=True)
            page.locator("#trace-title").scroll_into_view_if_needed()
            page.screenshot(path=str(shots / "usage-and-recovery.png"))
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
