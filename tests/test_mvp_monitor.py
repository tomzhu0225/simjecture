from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

from conjecture_solver.mvp_agent import (
    MVPAgentRunner,
    MVPCloseClaimAction,
    MVPFinishAction,
    MVPListClaimsAction,
    MVPListFilesAction,
    MVPListSkillsAction,
    MVPMaterializeSkillResourceAction,
    MVPReadFileAction,
    MVPReadSkillAction,
    MVPRegisterClaimAction,
    MVPRegisterEvidenceContractAction,
    MVPRequestAdjudicationAction,
    MVPRunCapabilityAction,
    MVPRunPythonAction,
    MVPSearchLiteratureAction,
    MVPWriteFileAction,
    parse_mvp_action,
)
from conjecture_solver.mvp_claims import ClaimDisposition, ClaimKind, ClaimRelation
from conjecture_solver.mvp_monitor import (
    MVPRunMonitor,
    RunPhase,
    TranscriptCursor,
    discover_recent_runs,
    format_human_status,
    humanize_action,
    list_contained_artifacts,
    load_run_snapshot,
    read_new_transcript_records,
    watch_run,
)


def _write(path: Path, payload: str | dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload)
        return
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _append_transcript(root: Path, *records: dict[str, Any], trailing: str = "") -> None:
    path = root / "transcript.jsonl"
    existing = path.read_text() if path.exists() else ""
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text(existing + "".join(line + "\n" for line in lines) + trailing)


def _action(**values: Any) -> str:
    return json.dumps(values)


def _manifest(hypothesis: str, **updates: Any) -> dict[str, Any]:
    payload = {
        "schema_version": "0.20.0",
        "hypothesis": hypothesis,
        "campaign_instruction": None,
        "config": {
            "max_iterations": None,
            "max_wall_seconds": 21600.0,
            "max_command_seconds": 600.0,
            "max_workspace_bytes": 536870912,
            "max_file_bytes": 67108864,
            "max_memory_bytes": 4294967296,
            "max_tool_output_chars": 30000,
            "command_heartbeat_seconds": 30.0,
            "recent_full_turns": 12,
            "max_model_retries": 3,
            "model_failover_after": 2,
        },
        "skill_hashes": {},
        "capability_hashes": {},
        "guided_commissioning": {},
        "claim_ledger_schema_version": "0.8.0",
        "literature_search": {"required_when_available": True, "identity": None},
        "system_prompt_sha256": "0" * 64,
    }
    payload.update(updates)
    return payload


def _claim(
    claim_id: str,
    *,
    statement: str,
    status: str = "open",
    kind: str = "scientific",
    relation: str = "root",
    parent_id: str | None = None,
    evidence: int = 0,
    closed_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": claim_id,
        "statement": statement,
        "kind": kind,
        "relation": relation,
        "parent_id": parent_id,
        "status": status,
        "rationale": "Test claim rationale that is long enough.",
        "evidence_contracts": [],
        "evidence": [
            {
                "path": f"artifact_{index}.json",
                "note": "linked test artifact",
                "iteration": index,
            }
            for index in range(evidence)
        ],
        "closed_reason": closed_reason,
        "created_iteration": 0,
        "updated_iteration": 1,
    }


def _ledger(hypothesis: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "0.8.0",
        "root_hypothesis": hypothesis,
        "claims": claims,
    }


def _report(**updates: Any) -> dict[str, Any]:
    payload = {
        "schema_version": "0.6.0",
        "package_kind": "natural_language_sandbox_mvp",
        "hypothesis": "The root hypothesis is long enough to store.",
        "campaign_instruction": None,
        "status": "completed",
        "final_answer": "A bounded conclusion was recorded.",
        "iterations": 2,
        "elapsed_wall_seconds": 12.5,
        "workspace_artifacts": {"result.json": "abc"},
        "open_claim_ids": ["claim_root"],
        "closed_claim_ids": ["claim_instrument"],
        "finish_claim_notes": ["closed_claim_count=1"],
        "transcript_path": "transcript.jsonl",
        "started_at": "2026-08-14T00:00:00+00:00",
        "finished_at": "2026-08-14T00:00:13+00:00",
    }
    payload.update(updates)
    return payload


def test_parse_mvp_action_is_the_public_runner_helper() -> None:
    content = _action(
        action="write_file",
        research_note="Write a diagnostic script.",
        path="analyze.py",
        content="print(1)\n",
    )
    public = parse_mvp_action(content)
    private = MVPAgentRunner._parse_action(content)
    assert public == private
    assert isinstance(public, MVPWriteFileAction)


def test_humanize_every_typed_action() -> None:
    cases = [
        (
            parse_mvp_action(
                _action(
                    action="search_literature",
                    research_note="Look for an analogous benchmark.",
                    query="magnetic moment conservation",
                    purpose="Find a validation observable for the invariant.",
                )
            ),
            "Searching literature",
        ),
        (
            parse_mvp_action(
                _action(
                    action="write_file",
                    research_note="Write the script.",
                    path="run.py",
                    content="pass\n",
                )
            ),
            "Writing run.py",
        ),
        (
            parse_mvp_action(
                _action(
                    action="read_file",
                    research_note="Inspect the output.",
                    path="result.json",
                )
            ),
            "Reading result.json",
        ),
        (
            parse_mvp_action(
                _action(
                    action="list_files",
                    research_note="See the workspace.",
                    path=".",
                )
            ),
            "Listing .",
        ),
        (
            parse_mvp_action(
                _action(
                    action="run_python",
                    research_note="Execute the script.",
                    argv=["analyze.py"],
                )
            ),
            "Running Python analyze.py",
        ),
        (
            parse_mvp_action(
                _action(action="list_skills", research_note="See installed instruments.")
            ),
            "Listing installed skills and capabilities",
        ),
        (
            parse_mvp_action(
                _action(
                    action="read_skill",
                    research_note="Read the skill entrypoint.",
                    skill="example",
                )
            ),
            "Reading skill example",
        ),
        (
            parse_mvp_action(
                _action(
                    action="materialize_skill_resource",
                    research_note="Copy a frozen example.",
                    skill="example",
                    source_path="examples/smoke.py",
                    destination_path="smoke.py",
                )
            ),
            "Materializing example:examples/smoke.py → smoke.py",
        ),
        (
            parse_mvp_action(
                _action(
                    action="run_capability",
                    research_note="Execute the installed instrument.",
                    capability="example-runtime",
                    argv=["program.py"],
                    stage="workbench",
                )
            ),
            "Running capability example-runtime",
        ),
        (
            parse_mvp_action(
                _action(
                    action="author_and_run_capability",
                    research_note="Author then execute.",
                    path="program.py",
                    content="print(1)\n",
                    capability="example-runtime",
                    argv=["program.py"],
                    stage="workbench",
                )
            ),
            "Authoring and running program.py",
        ),
        (
            parse_mvp_action(
                _action(
                    action="register_claim",
                    research_note="Split a measurable child claim.",
                    claim_id="claim_child",
                    statement="The child claim is specific enough.",
                    kind="scientific",
                    relation="refines",
                    parent_id="claim_root",
                    rationale="Need a measurable daughter statement.",
                )
            ),
            "Registering claim_child",
        ),
        (
            parse_mvp_action(
                _action(
                    action="register_evidence_contract",
                    research_note="Freeze the observation rule.",
                    claim_id="claim_child",
                    observable="late-time spatial variance",
                    expected_outcomes="increase or not",
                    decision_rule="compare against the declared threshold",
                    required_observation="three independent seeds",
                    uncertainty_criterion="interval must exclude the threshold",
                    inconclusive_conditions="if seeds disagree, remain unresolved",
                )
            ),
            "Registering evidence contract for claim_child",
        ),
        (
            parse_mvp_action(
                _action(
                    action="link_claim_evidence",
                    research_note="Attach the artifact.",
                    claim_id="claim_child",
                    path="summary.json",
                    note="seed ensemble summary",
                    observation_sufficient=True,
                    observation_note="Required seeds and uncertainty were met.",
                )
            ),
            "Linking evidence summary.json to claim_child",
        ),
        (
            parse_mvp_action(
                _action(
                    action="close_claim",
                    research_note="Resolve the child.",
                    claim_id="claim_child",
                    status="supported",
                    reason="The contracted observation was met.",
                )
            ),
            "Closing claim_child as supported",
        ),
        (
            parse_mvp_action(
                _action(
                    action="request_adjudication",
                    research_note="Ask the independent judge.",
                    claim_id="claim_child",
                    contract_version=1,
                    case_for_sufficiency=(
                        "The complete prospective ensemble found no counterexample."
                    ),
                )
            ),
            "Requesting independent adjudication for claim_child",
        ),
        (
            parse_mvp_action(_action(action="list_claims", research_note="Review the ledger.")),
            "Listing claims",
        ),
        (
            parse_mvp_action(
                _action(
                    action="finish",
                    research_note="Stop with a bounded answer.",
                    final_answer="The campaign reached a bounded conclusion.",
                )
            ),
            "Finishing the campaign",
        ),
    ]
    assert all(expected in humanize_action(action) for action, expected in cases)
    assert isinstance(cases[0][0], MVPSearchLiteratureAction)
    assert isinstance(cases[4][0], MVPRunPythonAction)
    assert isinstance(cases[5][0], MVPListSkillsAction)
    assert isinstance(cases[6][0], MVPReadSkillAction)
    assert isinstance(cases[7][0], MVPMaterializeSkillResourceAction)
    assert isinstance(cases[8][0], MVPRunCapabilityAction)
    assert isinstance(cases[10][0], MVPRegisterClaimAction)
    assert isinstance(cases[11][0], MVPRegisterEvidenceContractAction)
    assert isinstance(cases[13][0], MVPCloseClaimAction)
    assert isinstance(cases[14][0], MVPRequestAdjudicationAction)
    assert isinstance(cases[15][0], MVPListClaimsAction)
    assert isinstance(cases[16][0], MVPFinishAction)
    assert isinstance(cases[2][0], MVPReadFileAction)
    assert isinstance(cases[3][0], MVPListFilesAction)
    assert cases[8][0].stage.value == "workbench"
    assert cases[10][0].kind is ClaimKind.SCIENTIFIC
    assert cases[10][0].relation is ClaimRelation.REFINES
    assert cases[13][0].status is ClaimDisposition.SUPPORTED


def test_manifest_only_run_is_initialized_not_running(tmp_path: Path) -> None:
    root = tmp_path / "new-run"
    root.mkdir()
    hypothesis = "A newly initialized campaign has no scientific status yet."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    snapshot = load_run_snapshot(root)
    assert snapshot.phase is RunPhase.INITIALIZED
    assert snapshot.phase_label == "initialized"
    assert snapshot.identity.hypothesis == hypothesis
    assert snapshot.current_action is None
    assert snapshot.loop_state.stage.value == "falsification"
    assert snapshot.loop_state.role.value == "falsifier"
    assert snapshot.report is None
    assert "running" not in snapshot.phase_label
    text = format_human_status(snapshot)
    assert "initialized" in text
    assert "running" not in text.lower()


def test_in_progress_transcript_is_incomplete_without_report(tmp_path: Path) -> None:
    root = tmp_path / "active-run"
    root.mkdir()
    hypothesis = "An active campaign without a report is incomplete, not running."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 1,
            "model": "test-model",
            "content": _action(
                action="list_files",
                research_note="Inspect the empty workspace.",
                path=".",
            ),
        },
        {
            "kind": "tool",
            "iteration": 1,
            "content": json.dumps({"tool_result": {"ok": True, "result": {"entries": []}}}),
        },
    )
    snapshot = load_run_snapshot(root)
    assert snapshot.phase is RunPhase.INCOMPLETE
    assert "no terminal report" in snapshot.phase_label
    assert snapshot.iterations == 1
    assert snapshot.action_counts["list_files"] == 1
    assert snapshot.current_action is None
    assert snapshot.report is None


def test_pending_action_and_heartbeat_are_projected(tmp_path: Path) -> None:
    root = tmp_path / "heartbeat-run"
    root.mkdir()
    hypothesis = "A pending capability action should be visible from the transcript."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        root / "hypothesis_ledger.json",
        _ledger(
            hypothesis,
            [
                _claim("claim_root", statement=hypothesis),
                _claim(
                    "claim_rate_threshold",
                    statement="The measured rate stays above the contracted threshold.",
                    kind="scientific",
                    relation="refines",
                    parent_id="claim_root",
                    evidence=1,
                ),
            ],
        ),
    )
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 3,
            "model": "deepseek-test",
            "route": "default",
            "content": _action(
                action="run_capability",
                research_note="Collect the next contracted observation.",
                capability="example-runtime",
                argv=["program.py", "--seed", "3"],
                stage="evidence",
                active_claim_id="claim_rate_threshold",
            ),
        },
        {
            "kind": "tool_heartbeat",
            "iteration": 3,
            "elapsed_wall_seconds": 184.0,
            "stdout_bytes": 128,
            "stderr_bytes": 0,
            "workspace_bytes": 1_398_101_197,
        },
    )
    now = datetime(2026, 8, 14, 12, 0, 4, tzinfo=UTC)
    snapshot = load_run_snapshot(root, now=now)
    assert snapshot.phase is RunPhase.INCOMPLETE
    assert snapshot.current_action is not None
    assert snapshot.current_action.pending is True
    assert snapshot.current_action.action_name == "run_capability"
    assert snapshot.current_action.capability == "example-runtime"
    assert snapshot.current_action.stage == "evidence"
    assert snapshot.current_action.active_claim_id == "claim_rate_threshold"
    assert snapshot.current_action.research_note == "Collect the next contracted observation."
    assert snapshot.latest_heartbeat is not None
    assert snapshot.latest_heartbeat.elapsed_wall_seconds == 184.0
    assert snapshot.workspace_bytes == 1_398_101_197
    claim = next(item for item in snapshot.claims if item.id == "claim_rate_threshold")
    assert claim.status == "open"
    assert claim.evidence_count == 1
    assert claim.active is True
    assistant_event = next(event for event in snapshot.recent_events if event.kind == "assistant")
    assert assistant_event.capability == "example-runtime"
    assert assistant_event.research_note == "Collect the next contracted observation."
    heartbeat_event = next(
        event for event in snapshot.recent_events if event.kind == "tool_heartbeat"
    )
    assert heartbeat_event.action_name == "run_capability"
    assert heartbeat_event.outcome == "running"
    text = format_human_status(snapshot)
    assert "Running capability example-runtime" in text
    assert "evidence 1" in text
    assert "percentage" not in text.lower()


def test_open_and_closed_claims_are_read_from_the_ledger(tmp_path: Path) -> None:
    root = tmp_path / "claims-run"
    root.mkdir()
    hypothesis = "Claims come from the durable ledger rather than model prose."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        root / "hypothesis_ledger.json",
        _ledger(
            hypothesis,
            [
                _claim("claim_root", statement=hypothesis),
                _claim(
                    "claim_instrument",
                    statement="The instrument interface was commissioned.",
                    status="supported",
                    kind="instrument",
                    relation="instrument_of",
                    parent_id="claim_root",
                    evidence=2,
                    closed_reason="Machine-checked commissioning passed.",
                ),
                _claim(
                    "claim_population_result",
                    statement="The population threshold remains unresolved.",
                    status="unresolved",
                    kind="scientific",
                    relation="refines",
                    parent_id="claim_root",
                    evidence=3,
                    closed_reason="The interval still crosses the threshold.",
                ),
            ],
        ),
    )
    snapshot = load_run_snapshot(root)
    by_id = {claim.id: claim for claim in snapshot.claims}
    assert by_id["claim_root"].status == "open"
    assert by_id["claim_instrument"].status == "supported"
    assert by_id["claim_instrument"].evidence_count == 2
    assert by_id["claim_population_result"].status == "unresolved"
    assert "claim_root" in snapshot.open_claim_ids
    assert "claim_instrument" in snapshot.closed_claim_ids


def test_malformed_trailing_jsonl_is_ignored_until_complete(tmp_path: Path) -> None:
    root = tmp_path / "partial-line"
    root.mkdir()
    hypothesis = "A torn JSONL line must not crash the monitor or invent status."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 1,
            "content": _action(
                action="list_files",
                research_note="List the workspace.",
                path=".",
            ),
        },
        trailing='{"kind": "tool", "iteration": 1, "content":',
    )
    snapshot = load_run_snapshot(root)
    assert snapshot.iterations == 1
    assert snapshot.current_action is not None
    assert snapshot.current_action.pending is True
    assert snapshot.phase is RunPhase.INCOMPLETE
    complete = tmp_path / "complete-after-partial"
    complete.mkdir()
    _write(complete / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        complete,
        {
            "kind": "assistant",
            "iteration": 1,
            "content": _action(
                action="list_files",
                research_note="List the workspace.",
                path=".",
            ),
        },
        {
            "kind": "tool",
            "iteration": 1,
            "content": json.dumps({"tool_result": {"ok": True, "result": {}}}),
        },
    )
    monitor = MVPRunMonitor(complete)
    first = monitor.snapshot()
    assert first.current_action is None
    _append_transcript(
        complete,
        {
            "kind": "assistant",
            "iteration": 2,
            "content": _action(
                action="read_file",
                research_note="Read a result.",
                path="result.json",
            ),
        },
        trailing='{"kind":"tool"',
    )
    second = monitor.snapshot()
    assert second.iterations == 2
    assert second.current_action is not None
    assert second.current_action.action_name == "read_file"
    assert second.transcript_cursor.offset < (complete / "transcript.jsonl").stat().st_size


def test_completed_and_cancelled_reports_are_terminal(tmp_path: Path) -> None:
    completed = tmp_path / "completed"
    completed.mkdir()
    hypothesis = "A completed report is the authoritative terminal state."
    _write(completed / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        completed / "mvp_report.json",
        _report(hypothesis=hypothesis, status="completed", final_answer="Done."),
    )
    done = load_run_snapshot(completed)
    assert done.phase is RunPhase.COMPLETED
    assert done.report is not None
    assert done.report.final_answer == "Done."

    cancelled = tmp_path / "cancelled"
    cancelled.mkdir()
    _write(cancelled / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        cancelled / "mvp_report.json",
        _report(
            hypothesis=hypothesis,
            status="cancelled",
            final_answer="The campaign was cancelled. Partial artifacts are not evidence.",
        ),
    )
    stopped = load_run_snapshot(cancelled)
    assert stopped.phase is RunPhase.CANCELLED
    assert "not evidence" in stopped.report.final_answer

    failed = tmp_path / "provider-failed"
    failed.mkdir()
    _write(failed / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        failed / "mvp_report.json",
        _report(
            hypothesis=hypothesis,
            status="provider_failed",
            final_answer="Provider recovery budget exhausted.",
        ),
    )
    assert load_run_snapshot(failed).phase is RunPhase.PROVIDER_FAILED

    exhausted = tmp_path / "budget"
    exhausted.mkdir()
    _write(exhausted / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        exhausted / "mvp_report.json",
        _report(
            hypothesis=hypothesis,
            status="budget_exhausted",
            final_answer="The wall-time envelope was exhausted.",
        ),
    )
    assert load_run_snapshot(exhausted).phase is RunPhase.BUDGET_EXHAUSTED


def test_missing_optional_files_do_not_fail(tmp_path: Path) -> None:
    root = tmp_path / "sparse"
    root.mkdir()
    snapshot = load_run_snapshot(root)
    assert snapshot.phase is RunPhase.INCOMPLETE
    assert snapshot.identity.hypothesis is None
    assert snapshot.claims == ()
    assert snapshot.artifacts.manifest is None


def test_transcript_cursor_tracks_inode_and_offset(tmp_path: Path) -> None:
    path = tmp_path / "transcript.jsonl"
    path.write_text(json.dumps({"kind": "control", "event": "start", "iteration": 1}) + "\n")
    records, cursor, warnings = read_new_transcript_records(path, TranscriptCursor())
    assert len(records) == 1
    assert warnings == ()
    assert cursor.offset == path.stat().st_size
    more, same, _ = read_new_transcript_records(path, cursor)
    assert more == []
    assert same.offset == cursor.offset
    path.write_bytes(path.read_bytes() + b'{"kind": "control", "event": "again"')
    incomplete, held, _ = read_new_transcript_records(path, cursor)
    assert incomplete == []
    assert held.offset == cursor.offset
    path.write_bytes(path.read_bytes() + b', "iteration": 2}\n')
    finished, advanced, _ = read_new_transcript_records(path, held)
    assert len(finished) == 1
    assert finished[0]["event"] == "again"
    assert advanced.offset == path.stat().st_size


def test_watch_stops_when_a_terminal_report_appears(tmp_path: Path) -> None:
    root = tmp_path / "watch-run"
    root.mkdir()
    hypothesis = "Watch must exit when the durable report appears."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 1,
            "content": _action(
                action="list_files",
                research_note="Look around.",
                path=".",
            ),
        },
    )
    ticks = {"n": 0}

    def sleep(_seconds: float) -> None:
        ticks["n"] += 1
        if ticks["n"] == 1:
            _write(
                root / "mvp_report.json",
                _report(hypothesis=hypothesis, status="completed", final_answer="Stopped."),
            )

    buffer = StringIO()
    code = watch_run(
        root,
        poll_seconds=0.01,
        output=buffer,
        sleep=sleep,
    )
    assert code == 0
    assert ticks["n"] >= 1
    assert "completed" in buffer.getvalue()
    assert "Stopped." in buffer.getvalue()


def test_watch_jsonl_emits_snapshots_then_exits(tmp_path: Path) -> None:
    root = tmp_path / "watch-jsonl"
    root.mkdir()
    hypothesis = "JSONL watch emits machine-readable snapshots."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        root / "mvp_report.json",
        _report(hypothesis=hypothesis, status="cancelled", final_answer="Cancelled."),
    )
    buffer = StringIO()
    code = watch_run(root, jsonl=True, output=buffer, sleep=lambda _s: None)
    assert code == 0
    payload = json.loads(buffer.getvalue().splitlines()[0])
    assert payload["phase"] == "cancelled"
    assert payload["report"]["status"] == "cancelled"


def test_contained_artifact_listing_does_not_escape(tmp_path: Path) -> None:
    root = tmp_path / "artifacts-run"
    (root / "workspace").mkdir(parents=True)
    _write(root / "mvp_manifest.json", _manifest("Artifact listing stays in the run directory."))
    (root / "workspace" / "result.json").write_text("{}\n")
    outside = tmp_path / "secret.txt"
    outside.write_text("do-not-read\n")
    (root / "escape").symlink_to(outside)
    entries = list_contained_artifacts(root)
    relatives = {item.relative_path for item in entries}
    assert "mvp_manifest.json" in relatives
    assert "workspace/result.json" in relatives
    assert "escape" in relatives
    symlink = next(item for item in entries if item.relative_path == "escape")
    assert symlink.kind == "symlink"


def test_discover_recent_runs_scans_shallow_artifact_trees(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    first = artifacts / "campaign-a"
    first.mkdir(parents=True)
    _write(first / "mvp_manifest.json", _manifest("First campaign hypothesis is recorded."))
    second = artifacts / "campaign-b"
    second.mkdir()
    _write(second / "mvp_manifest.json", _manifest("Second campaign hypothesis is recorded."))
    _write(second / "mvp_report.json", _report(status="completed"))
    found = discover_recent_runs([artifacts], limit=10)
    directories = {item.run_directory for item in found}
    assert str(first.resolve()) in directories
    assert str(second.resolve()) in directories
    completed = next(item for item in found if item.run_directory.endswith("campaign-b"))
    assert completed.phase is RunPhase.COMPLETED


def test_token_usage_is_aggregated_from_assistant_records(tmp_path: Path) -> None:
    root = tmp_path / "tokens"
    root.mkdir()
    hypothesis = "Token usage is projected from durable assistant records."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 1,
            "model": "deepseek-v4-flash",
            "content": _action(
                action="list_files",
                research_note="Inspect the workspace.",
                path=".",
            ),
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "prompt_tokens_details": {"cached_tokens": 8},
            },
        },
        {
            "kind": "tool",
            "iteration": 1,
            "content": json.dumps({"tool_result": {"ok": True, "result": {}}}),
        },
        {
            "kind": "assistant",
            "iteration": 2,
            "model": "deepseek-v4-flash",
            "content": _action(
                action="list_files",
                research_note="Inspect again.",
                path=".",
            ),
            "usage": {"input_tokens": 50, "output_tokens": 10},
        },
    )
    snapshot = load_run_snapshot(root)
    assert snapshot.token_usage.prompt_tokens == 150
    assert snapshot.token_usage.completion_tokens == 30
    assert snapshot.token_usage.total_tokens == 180
    assert snapshot.token_usage.cached_tokens == 8
    assert snapshot.token_usage.turns == 2
    assert "150 in" in snapshot.token_usage.label
    text = format_human_status(snapshot)
    assert "tokens:" in text
    assert "150 in" in text


def test_pause_state_is_a_distinct_non_running_phase(tmp_path: Path) -> None:
    from conjecture_solver.mvp_control import pause_at_boundary

    root = tmp_path / "paused"
    root.mkdir()
    hypothesis = "A paused campaign is incomplete, not running, and not cancelled."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 1,
            "content": _action(
                action="list_files",
                research_note="Inspect the workspace.",
                path=".",
            ),
            "usage": {"total_tokens": 12},
        },
        {
            "kind": "tool",
            "iteration": 1,
            "content": json.dumps({"tool_result": {"ok": True, "result": {}}}),
        },
        {"kind": "control", "iteration": 1, "event": "campaign_paused"},
    )
    pause_at_boundary(root, iterations=1)
    snapshot = load_run_snapshot(root)
    assert snapshot.phase is RunPhase.PAUSED
    assert "paused" in snapshot.phase_label
    assert "running" not in snapshot.phase_label
    text = format_human_status(snapshot)
    assert "action boundary" in text


def test_watch_keeps_emitting_after_the_recent_event_window_fills(
    tmp_path: Path,
) -> None:
    root = tmp_path / "long-watch"
    root.mkdir()
    transcript = root / "transcript.jsonl"
    initial: list[dict[str, Any]] = []
    for iteration in range(1, 21):
        initial.extend(
            [
                {
                    "kind": "assistant",
                    "iteration": iteration,
                    "content": _action(
                        action="list_files",
                        research_note=f"Inspect iteration {iteration}.",
                        path=f"initial-{iteration}",
                    ),
                },
                {
                    "kind": "tool",
                    "iteration": iteration,
                    "content": json.dumps(
                        {"tool_result": {"ok": True, "result": {}}}
                    ),
                },
            ]
        )
    _append_transcript(root, *initial)
    advanced = {"done": False}

    def advance(_seconds: float) -> None:
        _append_transcript(
            root,
            {
                "kind": "assistant",
                "iteration": 21,
                "content": _action(
                    action="list_files",
                    research_note="This event arrived after the retained window filled.",
                    path="unique-after-window",
                ),
            },
            {
                "kind": "tool",
                "iteration": 21,
                "content": json.dumps(
                    {"tool_result": {"ok": True, "result": {}}}
                ),
            },
        )
        advanced["done"] = True

    output = StringIO()
    assert (
        watch_run(
            root,
            output=output,
            poll_seconds=0.01,
            sleep=advance,
            should_stop=lambda: advanced["done"],
        )
        == 0
    )
    assert "unique-after-window" in output.getvalue()
    assert transcript.is_file()


def test_terminal_report_supersedes_the_unpaired_finish_action(tmp_path: Path) -> None:
    root = tmp_path / "finished"
    root.mkdir()
    hypothesis = "A terminal report means the finish action is no longer pending."
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 1,
            "content": _action(
                action="finish",
                research_note="Return the bounded conclusion.",
                final_answer="Done.",
            ),
        },
    )
    _write(
        root / "mvp_report.json",
        _report(hypothesis=hypothesis, status="completed", final_answer="Done."),
    )
    snapshot = load_run_snapshot(root)
    assert snapshot.phase is RunPhase.COMPLETED
    assert snapshot.current_action is None
    assert "terminal report" in format_human_status(snapshot)


def test_historical_heartbeat_age_uses_durable_time_not_attach_time(
    tmp_path: Path,
) -> None:
    root = tmp_path / "historical-heartbeat"
    root.mkdir()
    _append_transcript(
        root,
        {
            "kind": "tool_heartbeat",
            "iteration": 1,
            "elapsed_wall_seconds": 10.0,
            "workspace_bytes": 1024,
        },
    )
    observed_at = datetime(2026, 8, 15, 12, tzinfo=UTC)
    historical = observed_at - timedelta(hours=2)
    os.utime(root / "transcript.jsonl", (historical.timestamp(), historical.timestamp()))
    snapshot = load_run_snapshot(root, now=observed_at)
    assert snapshot.latest_heartbeat is not None
    assert snapshot.latest_heartbeat.age_seconds == 7200
