from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.mvp_launch import (
    LaunchConflictError,
    MVPLaunchRequest,
    MVPOutputLock,
    ResumeError,
    build_mvp_argv,
    load_launch_request,
    materialize_operator_input,
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


def test_instruction_file_is_accepted_by_mvp_parser(tmp_path: Path) -> None:
    instruction = tmp_path / "instruction.txt"
    instruction.write_text("Keep the instruction out of an ad-hoc shell string.\n")
    args = build_parser().parse_args(
        [
            "mvp",
            "--hypothesis-file",
            str(tmp_path / "hypothesis.txt"),
            "--instruction-file",
            str(instruction),
            "--output",
            str(tmp_path / "out"),
        ]
    )
    assert args.instruction_file == str(instruction)
    assert args.instruction is None


def test_build_mvp_argv_uses_hypothesis_file_not_inline_text(tmp_path: Path) -> None:
    output = tmp_path / "campaign"
    request = MVPLaunchRequest(
        hypothesis="A multiline\nhypothesis stays in a file.",
        instruction="Use the installed example capability.",
        campaign_id="campaign-demo-001",
        output_directory=str(output),
        max_wall_seconds=3600,
        max_command_seconds=120,
        max_workspace_mb=256,
        max_memory_mb=2048,
        executable=(sys.executable, "-m", "conjecture_solver"),
    )
    plan = materialize_operator_input(request)
    assert Path(plan.hypothesis_file).read_text() == "A multiline\nhypothesis stays in a file."
    assert plan.instruction_file is not None
    assert "--hypothesis" not in plan.argv
    assert "--hypothesis-file" in plan.argv
    assert plan.argv[plan.argv.index("--hypothesis-file") + 1] == plan.hypothesis_file
    assert "--instruction-file" in plan.argv
    assert "A multiline" not in " ".join(plan.argv)
    assert all("\x00" not in item for item in plan.argv)
    launch = json.loads(Path(plan.launch_record).read_text())
    assert launch["campaign_id"] == "campaign-demo-001"
    assert "DEEPSEEK_API_KEY" not in json.dumps(launch)
    rebuilt = build_mvp_argv(
        request,
        hypothesis_file=Path(plan.hypothesis_file),
        instruction_file=Path(plan.instruction_file),
    )
    assert rebuilt == plan.argv


def test_dsh_launch_uses_stable_session_and_resume_command(tmp_path: Path) -> None:
    output = tmp_path / "dsh-campaign"
    hypothesis = "A private multiline\nhypothesis never enters the DSH process argv."
    request = MVPLaunchRequest(
        hypothesis=hypothesis,
        campaign_id="campaign-dsh-001",
        output_directory=str(output),
        engine="dsh",
        executable=(sys.executable, "-m", "conjecture_solver"),
    )
    initial = materialize_operator_input(request)
    assert initial.engine == "dsh"
    assert initial.dsh_session_id is not None
    assert "dsh-run" in initial.argv
    assert "--resume" not in initial.argv
    assert hypothesis not in " ".join(initial.argv)
    assert "--hypothesis-file" not in initial.argv

    launch = json.loads(Path(initial.launch_record).read_text())
    assert launch["schema_version"] == "0.3.0"
    assert launch["engine"] == "dsh"
    assert launch["dsh_session_id"] == initial.dsh_session_id

    loaded = load_launch_request(output)
    assert loaded is not None
    assert loaded.engine == "dsh"
    assert loaded.dsh_session_id == initial.dsh_session_id
    resumed = prepare_resume(output)
    assert resumed.dsh_session_id == initial.dsh_session_id
    assert "--resume" in resumed.argv
    assert resumed.argv[resumed.argv.index("--session-id") + 1] == initial.dsh_session_id


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


def test_tui_missing_dependency_explains_extra(monkeypatch, capsys) -> None:
    from conjecture_solver import cli

    def boom() -> None:
        raise ImportError("No module named 'textual'")

    monkeypatch.setattr(cli, "_import_tui", boom)
    args = build_parser().parse_args(["tui"])
    assert args.handler(args) == 2
    err = capsys.readouterr().err
    assert "uv sync --extra tui" in err
    assert "Traceback" not in err


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
    assert "launch.json" in capsys.readouterr().err


def test_prepare_resume_rebuilds_safe_argv(tmp_path: Path) -> None:
    from conjecture_solver.mvp_launch import persist_operator_launch, prepare_resume

    output = tmp_path / "resumable"
    persist_operator_launch(
        hypothesis="A stored operator input is enough to resume the contract.",
        instruction="Keep using the installed sandbox.",
        campaign_id="campaign-resume-test",
        output_directory=output,
        max_wall_seconds=3600,
        max_command_seconds=120,
        max_workspace_mb=128,
        max_file_mb=16,
        max_memory_mb=1024,
    )
    plan = prepare_resume(output)
    assert "--hypothesis-file" in plan.argv
    assert "--hypothesis" not in plan.argv
    assert Path(plan.hypothesis_file).read_text().startswith("A stored operator")


def test_resume_replays_the_complete_self_contained_contract(tmp_path: Path) -> None:
    output = tmp_path / "complete-contract"
    skills = output / "custom-skills"
    capabilities = output / "custom-capabilities"
    skills.mkdir(parents=True)
    capabilities.mkdir()
    request = MVPLaunchRequest(
        hypothesis="Every structured launch option survives a safe automatic resume.",
        instruction="Use the escalation route for this bounded campaign.",
        campaign_id="campaign-complete-contract",
        output_directory=str(output),
        max_wall_seconds=9876,
        max_command_seconds=321,
        max_workspace_mb=333,
        max_file_mb=17,
        max_memory_mb=2222,
        max_iterations=77,
        max_tool_output_chars=12345,
        command_heartbeat_seconds=7.5,
        literature_search_timeout_seconds=11.5,
        recent_full_turns=9,
        max_model_retries=5,
        model_failover_after=4,
        ledger=str(output / "audit" / "model.sqlite3"),
        skills_directory=str(skills),
        capability_directory=str(capabilities),
        use_glm=True,
        reason="Operator selected the alternate route.",
    )
    materialize_operator_input(request)
    loaded = load_launch_request(output)
    assert loaded is not None
    assert loaded.model_dump(exclude={"executable"}) == request.model_copy(
        update={
            "output_directory": str(output.resolve()),
            "ledger": str((output / "audit" / "model.sqlite3").resolve()),
            "skills_directory": str(skills.resolve()),
            "capability_directory": str(capabilities.resolve()),
        }
    ).model_dump(exclude={"executable"})
    plan = prepare_resume(output)
    for option in (
        "--max-tool-output-chars",
        "--command-heartbeat-seconds",
        "--literature-search-timeout-seconds",
        "--recent-full-turns",
        "--max-model-retries",
        "--model-failover-after",
        "--ledger",
        "--skills-directory",
        "--capability-directory",
        "--use-glm",
        "--reason",
    ):
        assert option in plan.argv


def test_external_contract_paths_disable_automatic_resume(tmp_path: Path) -> None:
    output = tmp_path / "external-contract"
    materialize_operator_input(
        MVPLaunchRequest(
            hypothesis="External writable paths require an explicitly repeated command.",
            campaign_id="campaign-external-contract",
            output_directory=str(output),
            ledger=str(tmp_path / "outside.sqlite3"),
        )
    )
    with pytest.raises(ResumeError, match="non-self-contained"):
        prepare_resume(output)


def test_guided_commissioning_is_snapshotted_for_safe_resume(tmp_path: Path) -> None:
    package = tmp_path / "guided-package"
    (package / "guided").mkdir(parents=True)
    (package / "guided" / "experiment.py").write_text("print('guided')\n")
    (package / "guided" / "validation.json").write_text(
        '{"checks":{"ran":true}}\n'
    )
    manifest = package / "guided_commission.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "name": "guided-resume",
                "description": "A known-runnable non-evidentiary starting point.",
                "capability": "example-runtime",
                "program_path": "guided/experiment.py",
                "validated_argv": ["guided/experiment.py"],
                "validation_summary_path": "guided/validation.json",
                "operator_validation": "The smoke run completed.",
                "files": ["guided/experiment.py", "guided/validation.json"],
            }
        )
        + "\n"
    )
    output = tmp_path / "guided-run"
    plan = materialize_operator_input(
        MVPLaunchRequest(
            hypothesis="Guided inputs are copied into the immutable operator contract.",
            campaign_id="campaign-guided-resume",
            output_directory=str(output),
            guided_commission=str(manifest),
        )
    )
    assert plan.guided_commission_file is not None
    copied = Path(plan.guided_commission_file)
    assert copied.is_relative_to(output)
    assert copied.read_text() == manifest.read_text()
    loaded = load_launch_request(output)
    assert loaded is not None
    assert loaded.guided_commission == str(copied)
    resumed = prepare_resume(output)
    assert resumed.argv[resumed.argv.index("--guided-commission") + 1] == str(copied)


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
    with pytest.raises(ResumeError, match="complete MVP contract"):
        prepare_resume(output)


def test_mismatched_launch_never_overwrites_operator_input(tmp_path: Path) -> None:
    output = tmp_path / "immutable"
    first = MVPLaunchRequest(
        hypothesis="The first immutable hypothesis remains intact.",
        campaign_id="campaign-immutable",
        output_directory=str(output),
    )
    materialize_operator_input(first)
    hypothesis_path = output / "operator_input" / "hypothesis.txt"
    launch_path = output / "operator_input" / "launch.json"
    before = (hypothesis_path.read_bytes(), launch_path.read_bytes())
    with pytest.raises(LaunchConflictError, match="different launch contract"):
        materialize_operator_input(
            first.model_copy(update={"hypothesis": "A conflicting replacement hypothesis."})
        )
    assert (hypothesis_path.read_bytes(), launch_path.read_bytes()) == before


def test_active_output_lock_blocks_launch_and_resume(tmp_path: Path) -> None:
    output = tmp_path / "locked"
    request = MVPLaunchRequest(
        hypothesis="Only one runner may own a durable scientific record.",
        campaign_id="campaign-locked",
        output_directory=str(output),
    )
    materialize_operator_input(request)
    with MVPOutputLock(output):
        with pytest.raises(ResumeError, match="already owns"):
            prepare_resume(output)
        with pytest.raises(RuntimeError, match="another runner owns"):
            materialize_operator_input(request)
