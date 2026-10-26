"""Removed routes cannot launch or resume, while archived records stay readable."""

import json
from pathlib import Path

import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.mvp_launch import (
    MVPLaunchPlan,
    MVPLaunchRequest,
    materialize_operator_input,
    prepare_resume,
    start_managed_campaign,
)
from conjecture_solver.study import selected_mode
from conjecture_solver.study_launch import NativeStudyRequest
from conjecture_solver.web.application import SimjectureWebApplication, WebApplicationError

from .legacy_records import write_legacy_launch


@pytest.mark.parametrize("command", ["mvp", "dsh-run", "dsh-profile", "tui"])
def test_removed_commands_are_not_advertised_or_accepted(command):
    parser = build_parser()
    assert command not in parser.format_help()
    with pytest.raises(SystemExit) as error:
        parser.parse_args([command])
    assert error.value.code == 2


@pytest.mark.parametrize("mode", ["structured", "frontier", "legacy"])
def test_removed_modes_rejected_by_cli_and_launch_contract(tmp_path, mode):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["study", "--campaign", str(tmp_path), "--mode", mode])
    with pytest.raises(ValueError):
        NativeStudyRequest(
            mode=mode, hypothesis="An archived claim.", campaign_id="old",
            output_directory=str(tmp_path),
        )


@pytest.mark.parametrize("payload", [
    {"mode": "legacy", "backend": "dsh"},
    {"mode": "legacy", "backend": "api"},
    {"mode": "structured"},
    {"mode": "frontier"},
    {"backend": "dsh"},
    {"engine": "dsh"},
])
def test_removed_http_routes_fail_before_materialization(tmp_path, payload, monkeypatch):
    app = SimjectureWebApplication(scan_roots=(tmp_path,), runs_root=tmp_path / "runs")
    assert app.bootstrap()["modes"] == ["minimal"]

    def forbidden(*args, **kwargs):
        pytest.fail("Removed routes must not materialize a study")

    monkeypatch.setattr("conjecture_solver.web.application.materialize_operator_input", forbidden)
    with pytest.raises(WebApplicationError, match="have been removed") as error:
        app.create_campaign({"hypothesis": "An archived claim.", **payload})
    assert error.value.status == 400


@pytest.mark.parametrize("engine", ["native", "dsh"])
def test_classical_launch_and_resume_cannot_execute_or_change_records(tmp_path, engine):
    request = MVPLaunchRequest(
        hypothesis="A historical claim.", campaign_id="old",
        output_directory=str(tmp_path / "old"), engine=engine,
    )
    with pytest.raises(ValueError, match="have been removed"):
        materialize_operator_input(request)
    assert not Path(request.output_directory).exists()
    root = write_legacy_launch(request)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="have been removed"):
        prepare_resume(root)
    plan = MVPLaunchPlan(
        request=request, output_directory=str(root),
        hypothesis_file=str(root / "operator_input/hypothesis.txt"),
        launch_record=str(root / "operator_input/launch.json"),
        controller_log=str(root / "controller.log"), argv=("must-not-run",),
    )
    with pytest.raises(ValueError, match="have been removed"):
        start_managed_campaign(plan, popen=lambda *_a, **_k: pytest.fail("Process started"))
    app = SimjectureWebApplication(initial_run=root, scan_roots=(tmp_path,))
    snapshot = app.campaign_snapshot(app.initial_campaign)
    assert not snapshot["controls"]["can_resume"]
    assert snapshot["snapshot"]["identity"]["hypothesis"] == request.hypothesis
    assert before == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("mode", ["structured", "frontier"])
def test_archived_native_resume_reports_migration_without_rewriting(tmp_path, mode):
    record = {"mode": mode, "request": {"mode": mode}}
    path = tmp_path / "study-launch.json"
    path.write_text(json.dumps(record))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="have been removed"):
        prepare_resume(tmp_path)
    with pytest.raises(ValueError, match="have been removed"):
        selected_mode(tmp_path)
    assert path.read_bytes() == before


def test_web_dsh_engine_is_removed():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["web", "--engine", "dsh"])


def test_minimal_still_accepts_builtin_api_and_native_agents(tmp_path):
    for backend in ["builtin", "codex", "codex-glm", "grok", "agy"]:
        request = NativeStudyRequest(
            backend=backend, model="test-model", hypothesis="A finite claim.",
            campaign_id="study", output_directory=str(tmp_path),
        )
        assert request.mode == "minimal"
        assert request.engine == "native"
