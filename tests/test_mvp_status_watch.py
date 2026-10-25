from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.mvp_launch import (
    ResumeError,
    load_launch_request,
    prepare_resume,
    validate_campaign_id,
)
from conjecture_solver.mvp_monitor import RunPhase, load_run_snapshot

from .test_mvp_monitor import _action, _append_transcript, _manifest, _report, _write


def test_public_cli_uses_simjecture_brand() -> None:
    assert build_parser().prog == "simjecture"


def test_status_json_and_human_output(tmp_path: Path, capsys) -> None:
    root = tmp_path / "run"
    root.mkdir()
    hypothesis = "Status must project durable records without claiming they are running."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 1,
            "model": "test-model",
            "content": _action(
                action="list_files",
                research_note="Inspect the workspace.",
                path=".",
            ),
        },
    )
    json_args = build_parser().parse_args(["status", str(root), "--json"])
    assert json_args.handler(json_args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["phase"] == RunPhase.INCOMPLETE.value
    assert "running" not in payload["phase_label"]
    assert payload["identity"]["hypothesis"] == hypothesis

    human_args = build_parser().parse_args(["status", str(root)])
    assert human_args.handler(human_args) == 0
    text = capsys.readouterr().out
    assert "incomplete (no terminal report)" in text
    assert "Listing ." in text
    assert hypothesis in text


def test_watch_command_exits_after_report(tmp_path: Path, capsys) -> None:
    root = tmp_path / "done"
    root.mkdir()
    hypothesis = "Watch should terminate when a cancelled report already exists."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        root / "mvp_report.json",
        _report(
            hypothesis=hypothesis,
            status="cancelled",
            final_answer="The campaign was cancelled.",
        ),
    )
    args = build_parser().parse_args(["watch", str(root), "--jsonl", "--poll-seconds", "0.05"])
    assert args.handler(args) == 0
    payload = json.loads(capsys.readouterr().out.splitlines()[0])
    assert payload["phase"] == "cancelled"


def test_validate_campaign_id_rejects_unsafe_names() -> None:
    assert validate_campaign_id("plasma-test-001") == "plasma-test-001"
    try:
        validate_campaign_id("../etc")
    except ValueError as error:
        assert "campaign id" in str(error)
    else:
        raise AssertionError("expected invalid campaign id to fail")


def test_base_cli_does_not_import_textual() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys\n"
                "import conjecture_solver.cli as cli\n"
                "assert 'textual' not in sys.modules\n"
                "parser = cli.build_parser()\n"
                "args = parser.parse_args(['status', 'missing', '--json'])\n"
                "assert args.command == 'status'\n"
                "print('ok')\n"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "ok"


def test_status_does_not_modify_run_directory(tmp_path: Path, capsys) -> None:
    root = tmp_path / "readonly"
    root.mkdir()
    _write(root / "mvp_manifest.json", _manifest("Status is a read-only projection."))
    before = {path.name: path.stat().st_mtime_ns for path in root.iterdir()}
    args = build_parser().parse_args(["status", str(root), "--json"])
    assert args.handler(args) == 0
    capsys.readouterr()
    after = {path.name: path.stat().st_mtime_ns for path in root.iterdir()}
    assert before == after
    assert load_run_snapshot(root).phase is RunPhase.INITIALIZED


def test_pause_without_live_process_does_not_signal(tmp_path: Path, capsys) -> None:
    args = build_parser().parse_args(["pause", str(tmp_path / "missing")])
    assert args.handler(args) == 1
    assert "no verified running process" in capsys.readouterr().out


def test_resume_without_launch_record_explains_the_contract(tmp_path: Path, capsys) -> None:
    root = tmp_path / "no-launch"
    root.mkdir()
    args = build_parser().parse_args(["resume", str(root)])
    assert args.handler(args) == 2
    assert "new minimal study" in capsys.readouterr().err


def test_launch_record_cannot_read_a_hypothesis_outside_the_run(tmp_path: Path) -> None:
    output = tmp_path / "crafted"
    operator = output / "operator_input"
    operator.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("must-not-be-loaded\n")
    (operator / "launch.json").write_text(
        json.dumps(
            {
                "schema_version": "0.2.0",
                "campaign_id": "campaign-crafted",
                "hypothesis_file": "../../outside.txt",
            }
        )
        + "\n"
    )
    with pytest.raises(ResumeError, match="hypothesis_file"):
        load_launch_request(output)


def test_legacy_partial_launch_record_is_not_automatically_replayed(
    tmp_path: Path,
) -> None:
    output = tmp_path / "legacy-launch"
    operator = output / "operator_input"
    operator.mkdir(parents=True)
    (operator / "hypothesis.txt").write_text("Legacy records omitted advanced options.")
    (operator / "launch.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "campaign_id": "campaign-legacy",
                "hypothesis_file": "hypothesis.txt",
            }
        )
        + "\n"
    )
    with pytest.raises(ResumeError, match="have been removed"):
        prepare_resume(output)
