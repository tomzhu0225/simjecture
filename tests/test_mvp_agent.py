from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from conjecture_solver.cli import build_parser
from conjecture_solver.literature import LiteratureSearchRecord, LiteratureSearchStatus
from conjecture_solver.llm import CompletionResult, ModelRoute
from conjecture_solver.mvp_agent import (
    BubblewrapSandbox,
    MVPAgentConfig,
    MVPAgentRunner,
    MVPArtifactInput,
    MVPJudgeDecision,
    MVPJudgeVerdict,
)
from conjecture_solver.mvp_claims import (
    ClaimDisposition,
    ClaimEvidenceProvenance,
    ClaimEvidenceValidationCheck,
    ClaimKind,
    ClaimRelation,
    EvidencePurpose,
)
from conjecture_solver.mvp_guidance import MVPGuidedCommissioningPackage
from conjecture_solver.mvp_skills import (
    MVPCapabilityInstallation,
    MVPCapabilityRegistry,
    MVPSkillCatalog,
    discover_builtin_mvp_resources,
)


class ScriptedCompletionClient:
    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.calls: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> CompletionResult:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        content = self.contents[len(self.calls) - 1]
        return CompletionResult(
            request_id=f"request_{len(self.calls)}",
            model="test-model",
            content=content,
            finish_reason="stop",
            usage={"total_tokens": 1},
            route=ModelRoute.DEFAULT,
            route_reason="test",
        )


class TimeoutOnceCompletionClient(ScriptedCompletionClient):
    def __init__(self, contents: list[str]) -> None:
        super().__init__(contents)
        self.attempts = 0

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> CompletionResult:
        self.attempts += 1
        if self.attempts == 1:
            raise httpx.ReadTimeout("provider stalled after request dispatch")
        return super().complete(messages, **kwargs)


class RecoveringCompletionClient:
    def __init__(self, *, failures: int, empty: bool = False) -> None:
        self.failures = failures
        self.empty = empty
        self.calls: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> CompletionResult:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        route = kwargs.get("route", ModelRoute.DEFAULT)
        if len(self.calls) <= self.failures:
            if self.empty:
                return CompletionResult(
                    request_id=f"empty_{len(self.calls)}",
                    model="empty-test-model",
                    content="   ",
                    finish_reason="stop",
                    usage={"total_tokens": 10},
                    route=route,
                    route_reason="empty test",
                )
            raise httpx.ReadTimeout("provider stalled after request dispatch")
        return CompletionResult(
            request_id=f"request_{len(self.calls)}",
            model="recovery-test-model",
            content=_action(
                action="finish",
                research_note="Return a bounded result after automatic recovery.",
                final_answer="The alternate route recovered the campaign.",
            ),
            finish_reason="stop",
            usage={"total_tokens": 1},
            route=route,
            route_reason=str(kwargs.get("escalation_reason") or "default test route"),
        )


class DeterministicLiteratureSearch:
    def __init__(self, *, status: LiteratureSearchStatus) -> None:
        self.status = status
        self.calls: list[dict[str, Any]] = []

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "name": "deterministic-literature-test",
            "version": "1",
            "network_location": "host",
        }

    def search(
        self,
        *,
        hypothesis: str,
        query: str,
        purpose: str,
        max_results: int,
    ) -> LiteratureSearchRecord:
        self.calls.append(
            {
                "hypothesis": hypothesis,
                "query": query,
                "purpose": purpose,
                "max_results": max_results,
            }
        )
        return LiteratureSearchRecord(
            id="literature_search_0123456789abcdef",
            hypothesis_sha256=hashlib.sha256(hypothesis.encode()).hexdigest(),
            query=query,
            purpose=purpose,
            requested_results=max_results,
            status=self.status,
            provider_status={
                "test": "ok:0" if self.status is LiteratureSearchStatus.COMPLETED else "offline"
            },
            errors=("test provider unavailable",)
            if self.status is LiteratureSearchStatus.UNAVAILABLE
            else (),
            searched_at=datetime(2026, 8, 13, tzinfo=UTC),
        )


def _action(**values: Any) -> str:
    return json.dumps(values)


def _config(**updates: Any) -> MVPAgentConfig:
    return MVPAgentConfig(
        max_iterations=updates.get("max_iterations", 8),
        max_wall_seconds=updates.get("max_wall_seconds", 30),
        max_command_seconds=updates.get("max_command_seconds", 10),
        max_workspace_bytes=updates.get("max_workspace_bytes", 16 * 1024 * 1024),
        max_file_bytes=updates.get("max_file_bytes", 2 * 1024 * 1024),
        max_memory_bytes=updates.get("max_memory_bytes", 1024 * 1024 * 1024),
        max_tool_output_chars=updates.get("max_tool_output_chars", 10_000),
        command_heartbeat_seconds=updates.get("command_heartbeat_seconds", 30),
        recent_full_turns=updates.get("recent_full_turns", 12),
        max_model_retries=updates.get("max_model_retries", 3),
        model_failover_after=updates.get("model_failover_after", 2),
        enforce_repair_loop=updates.get("enforce_repair_loop", False),
    )


def _write_guided_commissioning(tmp_path: Path) -> Path:
    package = tmp_path / "guided-package"
    (package / "guided").mkdir(parents=True)
    (package / "guided/experiment.py").write_text(
        "from pathlib import Path\n"
        "Path('guided/validation.json').write_text('{\"checks\":{\"ran\":true}}\\n')\n"
    )
    (package / "guided/validation.json").write_text(
        '{"checks":{"ran":true},"scope":"operator prerun only"}\n'
    )
    (package / "guided/protocol.json").write_text(
        '{"commands":{"anchor":["guided/experiment.py"]}}\n'
    )
    manifest = package / "guided_commission.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "name": "known-runnable-anchor",
                "description": "A small operator-validated capability starting point.",
                "capability": "isolated-python",
                "program_path": "guided/experiment.py",
                "validated_argv": ["guided/experiment.py"],
                "validation_summary_path": "guided/validation.json",
                "protocol_path": "guided/protocol.json",
                "operator_validation": "The exact command exited zero and wrote the summary.",
                "limitations": ["The supplied output is not campaign evidence."],
                "files": [
                    "guided/experiment.py",
                    "guided/validation.json",
                    "guided/protocol.json",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    return manifest


@pytest.mark.parametrize(
    "status",
    (LiteratureSearchStatus.COMPLETED, LiteratureSearchStatus.UNAVAILABLE),
)
def test_startup_requires_one_search_attempt_but_not_a_hit(
    tmp_path: Path,
    status: LiteratureSearchStatus,
) -> None:
    search = DeterministicLiteratureSearch(status=status)
    client = ScriptedCompletionClient(
        [
            _action(
                action="write_file",
                research_note="Try to compute before startup reconnaissance.",
                path="premature.py",
                content="print('premature')\n",
            ),
            _action(
                action="search_literature",
                research_note="Attempt one bounded search before computation.",
                query="reference benchmark for the declared numerical hypothesis",
                purpose="Find analogous results and commissioning targets.",
                max_results=5,
            ),
            _action(
                action="finish",
                research_note="The required attempt is recorded; no hit was mandatory.",
                final_answer="Reconnaissance was attempted and the bounded run can proceed.",
            ),
        ]
    )
    output = tmp_path / f"literature-{status.value}"
    config = _config(max_iterations=4)
    report = MVPAgentRunner(
        hypothesis="A bounded numerical hypothesis should start with reconnaissance.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
        literature_search=search,
    ).run()

    assert report.status == "completed"
    assert report.iterations == 3
    assert len(search.calls) == 1
    assert len(report.literature_searches) == 1
    assert report.literature_searches[0].status is status
    assert not (output / "workspace" / "premature.py").exists()
    search_index = json.loads((output / "literature_searches.json").read_text())
    assert search_index["policy"]["zero_hit_or_unavailable_satisfies_attempt"] is True
    records = [json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()]
    first_tool = next(item for item in records if item["kind"] == "tool")
    assert "startup reconnaissance has not been attempted" in first_tool["content"]


def test_existing_017_campaign_is_not_retroactively_search_gated(
    tmp_path: Path,
) -> None:
    output = tmp_path / "legacy-campaign"
    config = _config(max_iterations=3)
    original = MVPAgentRunner(
        hypothesis="An already-started campaign retains its recorded run contract.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    legacy_manifest = original._manifest()
    legacy_manifest["schema_version"] = "0.17.0"
    legacy_manifest["system_prompt_sha256"] = "f" * 64
    legacy_manifest.pop("literature_search")
    original.manifest_path.write_text(json.dumps(legacy_manifest, indent=2) + "\n")

    resumed = MVPAgentRunner(
        hypothesis=original.hypothesis,
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
        literature_search=DeterministicLiteratureSearch(status=LiteratureSearchStatus.COMPLETED),
    )
    resumed._initialize()

    assert resumed._literature_startup_grandfathered
    assert not resumed._literature_attempt_required()
    assert json.loads(resumed.manifest_path.read_text())["schema_version"] == "0.17.0"


def test_transient_model_timeout_is_recorded_and_retried(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TimeoutOnceCompletionClient(
        [
            _action(
                action="finish",
                research_note="Return a bounded result after provider recovery.",
                final_answer="The provider retry recovered without losing the campaign.",
            )
        ]
    )
    monkeypatch.setattr("conjecture_solver.mvp_agent.time.sleep", lambda _delay: None)
    output = tmp_path / "model-retry"
    config = _config(max_iterations=3)
    report = MVPAgentRunner(
        hypothesis="A transient provider timeout should not destroy campaign state.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "completed"
    assert report.iterations == 1
    assert client.attempts == 2
    records = [json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()]
    assert records[0]["kind"] == "control"
    assert records[0]["event"] == "model_completion_retry"
    assert records[0]["attempt"] == 1
    assert records[0]["error_type"] == "ReadTimeout"
    assert records[1]["kind"] == "assistant"


def test_resume_records_dangling_action_as_interrupted_once(tmp_path: Path) -> None:
    output = tmp_path / "interrupted-action"
    config = _config(max_iterations=3)
    first = MVPAgentRunner(
        hypothesis="An interrupted action must not be mistaken for evidence.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    first._initialize()
    first._append(
        {
            "kind": "assistant",
            "iteration": 1,
            "content": _action(
                action="run_python",
                research_note="Begin a calculation that the host interrupts.",
                argv=["-c", "print('partial')"],
            ),
            "model": "test-model",
            "route": "default",
            "route_reason": "test",
            "request_id": "request_interrupted",
            "usage": {"total_tokens": 1},
        }
    )
    first._append(
        {
            "kind": "tool_heartbeat",
            "iteration": 1,
            "elapsed_wall_seconds": 30.0,
            "stdout_bytes": 0,
            "stderr_bytes": 0,
            "workspace_bytes": 0,
        }
    )

    client = ScriptedCompletionClient(
        [
            _action(
                action="finish",
                research_note="The interrupted outcome is explicitly unknown.",
                final_answer="The partial action was not treated as evidence.",
            )
        ]
    )
    resumed = MVPAgentRunner(
        hypothesis=first.hypothesis,
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    report = resumed.run()

    assert report.status == "completed"
    records = [json.loads(line) for line in resumed.transcript.read_text().splitlines()]
    recoveries = [
        record for record in records if record.get("event") == "interrupted_action_recovered"
    ]
    assert len(recoveries) == 1
    recovered_tools = [
        json.loads(record["content"])["tool_result"]
        for record in records
        if record.get("kind") == "tool" and record.get("iteration") == 1
    ]
    assert len(recovered_tools) == 1
    assert recovered_tools[0]["ok"] is False
    assert recovered_tools[0]["interrupted_action"] is True
    assert recovered_tools[0]["action"] == "run_python"
    sent = client.calls[0]["messages"]
    assert any(
        message["role"] == "user" and '"interrupted_action": true' in message["content"]
        for message in sent
    )

    resumed._recover_interrupted_action()
    records_after = [json.loads(line) for line in resumed.transcript.read_text().splitlines()]
    assert (
        sum(record.get("event") == "interrupted_action_recovered" for record in records_after) == 1
    )


def test_repeated_timeouts_fail_over_to_alternate_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecoveringCompletionClient(failures=2)
    monkeypatch.setattr("conjecture_solver.mvp_agent.time.sleep", lambda _delay: None)
    output = tmp_path / "model-failover"
    config = _config(max_iterations=3)
    report = MVPAgentRunner(
        hypothesis="Transient default-route failure should trigger model failover.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "completed"
    assert report.iterations == 1
    assert [call["kwargs"]["route"] for call in client.calls] == [
        ModelRoute.DEFAULT,
        ModelRoute.DEFAULT,
        ModelRoute.ESCALATION,
    ]
    assert "automatic recovery" in client.calls[-1]["kwargs"]["escalation_reason"]
    records = [json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()]
    retries = [record for record in records if record.get("event") == "model_completion_retry"]
    assert retries[0]["failover"] is False
    assert retries[1]["failover"] is True
    assert retries[1]["next_route"] == ModelRoute.ESCALATION.value
    assistant = next(record for record in records if record["kind"] == "assistant")
    assert assistant["route"] == ModelRoute.ESCALATION.value


def test_empty_completion_is_retried_without_consuming_a_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecoveringCompletionClient(failures=1, empty=True)
    monkeypatch.setattr("conjecture_solver.mvp_agent.time.sleep", lambda _delay: None)
    output = tmp_path / "empty-completion"
    config = _config(max_iterations=3)
    report = MVPAgentRunner(
        hypothesis="An empty provider response is not a valid agent turn.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "completed"
    assert report.iterations == 1
    records = [json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()]
    assert records[0]["event"] == "model_completion_retry"
    assert records[0]["error_type"] == "IncompleteCompletion"
    assert sum(record["kind"] == "assistant" for record in records) == 1


def test_cross_route_retry_exhaustion_has_distinct_terminal_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecoveringCompletionClient(failures=99)
    monkeypatch.setattr("conjecture_solver.mvp_agent.time.sleep", lambda _delay: None)
    output = tmp_path / "provider-failed"
    config = _config(
        max_iterations=3,
        max_model_retries=3,
        model_failover_after=2,
    )
    report = MVPAgentRunner(
        hypothesis="Provider failure must remain distinct from scientific failure.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "provider_failed"
    assert report.iterations == 0
    assert len(client.calls) == 4
    assert [call["kwargs"]["route"] for call in client.calls] == [
        ModelRoute.DEFAULT,
        ModelRoute.DEFAULT,
        ModelRoute.ESCALATION,
        ModelRoute.ESCALATION,
    ]
    records = [json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()]
    assert records[-1]["event"] == "model_completion_failed"
    assert records[-1]["failure_count"] == 4
    assert "no provider failure is scientific evidence" in report.final_answer


def test_messages_for_model_compacts_old_tool_payloads(tmp_path: Path) -> None:
    config = _config(max_iterations=20)
    # Override recent_full_turns for a tight compaction window.
    config = MVPAgentConfig(
        max_iterations=20,
        max_wall_seconds=30,
        max_command_seconds=10,
        max_workspace_bytes=16 * 1024 * 1024,
        max_file_bytes=2 * 1024 * 1024,
        max_memory_bytes=1024 * 1024 * 1024,
        max_tool_output_chars=10_000,
        recent_full_turns=2,
        enforce_repair_loop=False,
    )
    output = tmp_path / "compact"
    runner = MVPAgentRunner(
        hypothesis="Compaction preserves claim state.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    huge_stdout = "x" * 5000
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "initial"},
    ]
    for turn in range(1, 5):
        messages.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "action": "run_python",
                        "research_note": f"turn {turn}",
                        "argv": ["probe.py"],
                    }
                ),
            }
        )
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "tool_result": {
                            "ok": True,
                            "result": {
                                "returncode": 0,
                                "stdout": huge_stdout,
                                "stderr": "",
                                "claim_ledger": {
                                    "claim_count": 1,
                                    "open_count": 1,
                                    "claims": [{"id": "claim_root"}],
                                },
                            },
                        }
                    },
                    sort_keys=True,
                ),
            }
        )

    model_messages = runner._messages_for_model(messages)
    # system + initial + 4 assistant + 4 tool + sticky claim note
    assert model_messages[0]["role"] == "system"
    assert model_messages[1]["role"] == "user"
    assert model_messages[-1]["role"] == "user"
    sticky = json.loads(model_messages[-1]["content"])
    assert sticky["claim_ledger"]["claim_count"] == 1
    # First two turns (assistant/tool pairs) are compacted on both sides.
    first_assistant = json.loads(model_messages[2]["content"])
    assert first_assistant["compacted"] is True
    assert first_assistant["action"] == "run_python"
    assert first_assistant["research_note"] == "turn 1"
    first_tool = json.loads(model_messages[3]["content"])
    assert first_tool["tool_result"]["compacted"] is True
    assert first_tool["tool_result"]["result"]["stdout_chars"] == 5000
    assert len(first_tool["tool_result"]["result"]["stdout_head"]) == 500
    # Last two full turns keep full stdout.
    last_tool = json.loads(model_messages[-2]["content"])
    assert last_tool["tool_result"]["result"]["stdout"] == huge_stdout


def test_old_authored_source_is_hashed_not_replayed_to_model() -> None:
    source = "sensitive_or_large_source = 1\n" * 1000
    compacted = json.loads(
        MVPAgentRunner._compact_assistant_payload(
            _action(
                action="write_file",
                research_note="Author the bounded analyzer.",
                path="analyzer.py",
                content=source,
            )
        )
    )

    assert compacted["action"] == "write_file"
    assert compacted["path"] == "analyzer.py"
    parsed_source = source.rstrip()
    assert compacted["authored_content_chars"] == len(parsed_source)
    assert (
        compacted["authored_content_sha256"] == hashlib.sha256(parsed_source.encode()).hexdigest()
    )
    assert "sensitive_or_large_source" not in json.dumps(compacted)


def test_messages_for_model_pin_successfully_read_skill_resources(tmp_path: Path) -> None:
    config = _config(max_iterations=20, recent_full_turns=2)
    output = tmp_path / "pinned-skill"
    runner = MVPAgentRunner(
        hypothesis="Pinned instrument guidance survives ordinary turn compaction.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    exact_guidance = "Use simulation.fields.get('Efield_fp', dir=Direction.y, level=0)."
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "initial"},
        {
            "role": "assistant",
            "content": _action(
                action="read_skill",
                skill="warpx",
                path="references/diagnostics.md",
                research_note="Read the exact diagnostic API.",
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "tool_result": {
                        "ok": True,
                        "result": {
                            "skill": "warpx",
                            "path": "references/diagnostics.md",
                            "version": "26.07.7",
                            "skill_sha256": "a" * 64,
                            "content_sha256": "b" * 64,
                            "content": exact_guidance,
                            "truncated": False,
                        },
                    }
                },
                sort_keys=True,
            ),
        },
    ]
    for turn in range(2, 6):
        messages.extend(
            [
                {
                    "role": "assistant",
                    "content": _action(
                        action="run_python",
                        argv=["probe.py"],
                        research_note=f"ordinary turn {turn}",
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"tool_result": {"ok": True, "result": {"returncode": 0}}}
                    ),
                },
            ]
        )

    model_messages = runner._messages_for_model(messages)
    compacted_old_read = model_messages[3]["content"]
    sticky = json.loads(model_messages[-1]["content"])

    assert exact_guidance not in compacted_old_read
    assert sticky["pinned_skill_resources"] == [
        {
            "skill": "warpx",
            "path": "references/diagnostics.md",
            "version": "26.07.7",
            "skill_sha256": "a" * 64,
            "content_sha256": "b" * 64,
            "content": exact_guidance,
            "truncated": False,
        }
    ]
    assert "remain authoritative" in sticky["context_note"]


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_unknown_active_claim_id_is_rejected(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="run_python",
                research_note="Cite a missing claim on purpose.",
                argv=[
                    "-c",
                    "from pathlib import Path; Path('executed.txt').write_text('bad')",
                ],
                active_claim_id="claim_missing",
            ),
            _action(
                action="finish",
                research_note="Stop after the rejected binding.",
                final_answer="No scientific conclusion; binding rejected.",
            ),
        ]
    )
    output = tmp_path / "bad-claim"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Binding must reject unknown claims.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()
    assert report.status == "completed"
    tool = json.loads(
        [
            json.loads(line)
            for line in (output / "transcript.jsonl").read_text().splitlines()
            if json.loads(line)["kind"] == "tool"
        ][0]["content"]
    )
    assert tool["tool_result"]["ok"] is False
    assert "unknown active_claim_id" in tool["tool_result"]["error"]
    assert not (output / "workspace/executed.txt").exists()
    assert not (output / "workspace/.acs").exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_claim_relation_rejects_cross_kind_successor(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Attempt the invalid lineage exposed by run 0010.",
                claim_id="claim_invalid_successor",
                statement="A replacement instrument qualifies the scientific parent.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.SUCCEEDS.value,
                parent_id="claim_root",
                rationale="This deliberately uses a cross-kind successor relation.",
            ),
            _action(
                action="finish",
                research_note="Finish after the ledger rejects invalid lineage.",
                final_answer="The invalid successor was not registered.",
            ),
        ]
    )
    output = tmp_path / "invalid-successor"
    config = _config(max_iterations=3)
    report = MVPAgentRunner(
        hypothesis="A capability can test this scientific claim.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[0]["tool_result"]["ok"] is False
    assert "same claim kind" in tool_rows[0]["tool_result"]["error"]
    assert [claim["id"] for claim in report.claim_ledger["claims"]] == ["claim_root"]


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_closed_active_claim_is_rejected_before_python_side_effect(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a claim that will be closed before execution.",
                claim_id="claim_closed",
                statement="A closed claim must reject later bound executions.",
                kind=ClaimKind.CONTROL.value,
                relation=ClaimRelation.CONTROL_FOR.value,
                parent_id="claim_root",
                rationale="Exercise closed-claim preflight validation.",
            ),
            _action(
                action="close_claim",
                research_note="Close the claim before attempting execution.",
                claim_id="claim_closed",
                status=ClaimDisposition.UNRESOLVED.value,
                reason="No execution is needed for this validation fixture.",
            ),
            _action(
                action="run_python",
                research_note="Attempt a side effect against the closed claim.",
                argv=[
                    "-c",
                    "from pathlib import Path; Path('executed.txt').write_text('bad')",
                ],
                active_claim_id="claim_closed",
            ),
            _action(
                action="finish",
                research_note="Finish after observing the preflight rejection.",
                final_answer="The closed claim rejected execution.",
            ),
        ]
    )
    output = tmp_path / "closed-claim"
    config = _config()
    MVPAgentRunner(
        hypothesis="Closed claim bindings have no side effects.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    tools = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tools[2]["tool_result"]["ok"] is False
    assert "is not open (unresolved)" in tools[2]["tool_result"]["error"]
    assert not (output / "workspace/executed.txt").exists()
    assert not (output / "workspace/.acs").exists()


def test_action_parser_rejects_multiple_distinct_actions() -> None:
    content = "\nThen execute it.\n".join(
        [
            _action(
                action="write_file",
                research_note="Write the instrument input first.",
                path="input.py",
                content="print('input')\n",
            ),
            _action(
                action="run_capability",
                research_note="Execute the instrument in a later turn.",
                capability="instrument",
                argv=["input.py"],
                active_claim_id="claim_instrument",
            ),
        ]
    )

    with pytest.raises(ValueError, match="multiple distinct actions"):
        MVPAgentRunner._parse_action(content)


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_agent_has_no_default_iteration_ceiling(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="list_files",
                research_note=f"Continue the bounded investigation at turn {iteration}.",
                path=".",
            )
            for iteration in range(65)
        ]
        + [
            _action(
                action="finish",
                research_note="The scripted investigation is now complete.",
                final_answer="The agent continued beyond the former default ceiling.",
            )
        ]
    )
    output = tmp_path / "unbounded-turns"
    config = MVPAgentConfig(
        max_wall_seconds=30,
        max_command_seconds=10,
        max_workspace_bytes=16 * 1024 * 1024,
        max_file_bytes=2 * 1024 * 1024,
        max_memory_bytes=1024 * 1024 * 1024,
        max_tool_output_chars=10_000,
        enforce_repair_loop=False,
    )
    report = MVPAgentRunner(
        hypothesis="An investigation may require more than 64 model turns.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert config.max_iterations is None
    assert report.status == "completed"
    assert report.iterations == 66


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_natural_language_agent_writes_runs_reads_and_finishes(tmp_path: Path) -> None:
    hypothesis = "A particle invariant is conserved in a slowly varying field."
    instruction = "Use the installed reference integrator for the final check."
    client = ScriptedCompletionClient(
        [
            _action(
                action="write_file",
                research_note=(
                    "My first subhypothesis is that a converged numerical orbit will "
                    "show bounded invariant error, so I will write a minimal experiment."
                ),
                path="experiment.py",
                content=(
                    "from pathlib import Path\n"
                    "Path('result.txt').write_text('relative_error=0.002')\n"
                    "print('experiment complete')\n"
                ),
            ),
            _action(
                action="run_python",
                research_note="I will execute the experiment before interpreting it.",
                argv=["experiment.py"],
            ),
            _action(
                action="read_file",
                research_note="I will inspect the numerical result directly.",
                path="result.txt",
            ),
            _action(
                action="finish",
                research_note=(
                    "The bounded experiment supports the subhypothesis only in its "
                    "tested numerical scope."
                ),
                final_answer="The invariant was conserved to 0.2% in the tested case.",
            ),
        ]
    )
    output = tmp_path / "run"
    config = _config()
    report = MVPAgentRunner(
        hypothesis=hypothesis,
        campaign_instruction=instruction,
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "completed"
    assert report.campaign_instruction == instruction
    assert report.iterations == 4
    assert "experiment.py" in report.workspace_artifacts
    assert "result.txt" in report.workspace_artifacts
    assert all(call["kwargs"]["max_tokens"] is None for call in client.calls)
    first_prompt = client.calls[0]["messages"]
    assert hypothesis in first_prompt[1]["content"]
    initial_payload = json.loads(first_prompt[1]["content"])
    assert initial_payload["campaign_instruction"] == instruction
    action_schema = initial_payload["action_schema"]
    assert action_schema["discriminator"]["propertyName"] == "action"
    assert len(action_schema["oneOf"]) == 17
    assert "register_claim" in first_prompt[0]["content"]
    assert initial_payload["claim_ledger"]["claim_count"] == 1
    assert initial_payload["claim_ledger"]["claims"][0]["id"] == "claim_root"
    gate = initial_payload["claim_protocol"]["capability_commissioning_gate"]
    assert gate == {
        "available": False,
        "policy": "do_not_invent_unavailable_capabilities",
    }
    tree_policy = initial_payload["claim_protocol"]["hypothesis_tree_policy"]
    assert tree_policy["auxiliary_formula_belongs_in_parent_contract"] is True
    assert tree_policy["independently_audited_estimator_uses_kind"] == "diagnostic"
    assert "Do not create a scientific refines child merely" in first_prompt[0]["content"]
    assert "Capability work has two stages" not in first_prompt[0]["content"]
    assert "finite grid coverage alone cannot" in first_prompt[0]["content"]
    observable_identity = initial_payload["claim_protocol"]["scientific_observable_identity"]
    assert observable_identity["use_aspectless_validation_checks"] is True
    assert observable_identity["post_hoc_relabeling_forbidden"] is True
    assert observable_identity["metadata_fields"] == [
        "estimator_or_formula",
        "component_or_sign_convention",
        "units",
        "normalization",
        "time_or_window_rule",
    ]
    assert "do not relabel or reinterpret" in first_prompt[0]["content"]
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    assert len(transcript) == 7
    assert transcript[0]["kind"] == "assistant"
    assert transcript[-1]["kind"] == "assistant"
    assert report.claim_ledger["claims"][0]["id"] == "claim_root"
    assert (output / "hypothesis_ledger.json").is_file()
    provenance = json.loads((output / "artifact_provenance.json").read_text())["artifacts"]
    assert provenance["experiment.py"]["evidence_eligible"] is False
    assert provenance["result.txt"]["evidence_eligible"] is True

    replay_client = ScriptedCompletionClient([])
    replay = MVPAgentRunner(
        hypothesis=hypothesis,
        campaign_instruction=instruction,
        output_directory=output,
        completion_client=replay_client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()
    assert replay == report
    assert replay_client.calls == []


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_sandbox_cannot_see_host_home_credentials_or_network(tmp_path: Path) -> None:
    host_secret = tmp_path / "outside-secret.txt"
    host_secret.write_text("not visible")
    config = _config()
    sandbox = BubblewrapSandbox(tmp_path / "workspace", config)
    code = (
        "import json, os, socket\n"
        "from pathlib import Path\n"
        "network = 'unexpected'\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=0.2)\n"
        "except OSError:\n"
        "    network = 'blocked'\n"
        "print(json.dumps({\n"
        f"  'host_secret_exists': Path({str(host_secret)!r}).exists(),\n"
        "  'credential_present': os.getenv('CP_API_KEY') is not None,\n"
        "  'home_exists': Path('/home').exists(),\n"
        "  'network': network,\n"
        "}))\n"
    )
    result = sandbox.run_python(("-c", code))
    observed = json.loads(result.stdout)

    assert result.returncode == 0
    assert observed == {
        "host_secret_exists": False,
        "credential_present": False,
        "home_exists": False,
        "network": "blocked",
    }


def test_sandbox_rejects_host_path_traversal(tmp_path: Path) -> None:
    if shutil.which("bwrap") is None:
        pytest.skip("bubblewrap is unavailable")
    sandbox = BubblewrapSandbox(tmp_path / "workspace", _config())
    with pytest.raises(ValueError, match="relative"):
        sandbox.write_file("/tmp/escape.txt", "bad")
    with pytest.raises(ValueError, match="escapes"):
        sandbox.write_file("../escape.txt", "bad")


def test_sandbox_reads_stable_line_windows_without_execution(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(tmp_path / "workspace", _config())
    source = "".join(f"line {number}\n" for number in range(1, 11))
    sandbox.write_file("program.py", source)

    first = sandbox.read_file("program.py", start_line=3, line_count=4)
    second = sandbox.read_file(
        "program.py",
        start_line=first["next_start_line"],
        line_count=4,
    )

    assert first["content"] == "line 3\nline 4\nline 5\nline 6\n"
    assert first["start_line"] == 3
    assert first["end_line"] == 6
    assert first["total_lines"] == 10
    assert first["next_start_line"] == 7
    assert first["eof"] is False
    assert first["truncated"] is False
    assert first["sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert second["content"] == "line 7\nline 8\nline 9\nline 10\n"
    assert second["next_start_line"] is None
    assert second["eof"] is True
    assert not (tmp_path / "workspace/.acs").exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_sandbox_exposes_scientific_python_without_exposing_home(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(tmp_path / "workspace", _config())
    result = sandbox.run_python(
        (
            "-c",
            (
                "import json, matplotlib, numpy, pandas, scipy, sys; "
                "print(json.dumps({'python': list(sys.version_info[:2]), "
                "'versions': [matplotlib.__version__, numpy.__version__, "
                "pandas.__version__, scipy.__version__]}))"
            ),
        )
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    observed = json.loads(result.stdout)
    assert observed["python"] == list(sys.version_info[:2])
    assert all(observed["versions"])


def test_action_parser_tolerates_natural_language_around_protocol_json() -> None:
    content = (
        "I will now test the subhypothesis.\n"
        + _action(
            action="run_python",
            research_note="Testing the next natural-language subhypothesis.",
            argv=["experiment.py"],
        )
        + "\nI will inspect the output next."
    )
    parsed = MVPAgentRunner._parse_action(content)
    assert parsed.action.value == "run_python"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_link_claim_evidence_rejects_missing_path(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a claim before linking missing evidence.",
                claim_id="claim_pending_file",
                statement="A missing file should still link with a soft warning.",
                kind=ClaimKind.DIAGNOSTIC.value,
                relation=ClaimRelation.DIAGNOSTIC_OF.value,
                parent_id="claim_root",
                rationale="Exercise soft artifact warnings.",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link a path that does not exist yet.",
                claim_id="claim_pending_file",
                path="not_written_yet.txt",
                note="Will exist after a later write in a real campaign.",
                observation_sufficient=False,
                observation_note="The required artifact does not exist yet.",
            ),
            _action(
                action="finish",
                research_note="Done.",
                final_answer="Soft warning path exercised.",
            ),
        ]
    )
    output = tmp_path / "missing-evidence"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Evidence links may precede file materialization.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()
    assert report.status == "completed"
    tool = json.loads(
        [
            json.loads(line)
            for line in (output / "transcript.jsonl").read_text().splitlines()
            if json.loads(line)["kind"] == "tool"
        ][1]["content"]
    )
    assert tool["tool_result"]["ok"] is False
    assert "is not a workspace file" in tool["tool_result"]["error"]
    claim = {
        item["id"]: item
        for item in json.loads((output / "hypothesis_ledger.json").read_text())["claims"]
    }["claim_pending_file"]
    assert claim["evidence"] == []
    assert "claim_pending_file" in report.open_claim_ids
    assert any(
        "open non-root claims remain at finish: claim_pending_file" in note
        for note in report.finish_claim_notes
    )
    assert any("completed with open claims" in note for note in report.finish_claim_notes)


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_run_python_can_soft_bind_active_claim_id(tmp_path: Path) -> None:
    hypothesis = "A bounded numeric check can cite an open claim."
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a scientific working claim.",
                claim_id="claim_error_bound",
                statement="Relative error stays below one percent in the smoke case.",
                kind=ClaimKind.SCIENTIFIC.value,
                relation=ClaimRelation.REFINES.value,
                parent_id="claim_root",
                rationale="Operational form of the root for the smoke test.",
            ),
            _action(
                action="write_file",
                research_note="Author the smoke calculation.",
                path="smoke.py",
                content="print('relative_error=0.001')\n",
            ),
            _action(
                action="run_python",
                research_note="Execute against the open claim.",
                argv=["smoke.py"],
                active_claim_id="claim_error_bound",
            ),
            _action(
                action="finish",
                research_note="Smoke complete.",
                final_answer="Bound held in the smoke case.",
            ),
        ]
    )
    output = tmp_path / "active-claim"
    config = _config()
    report = MVPAgentRunner(
        hypothesis=hypothesis,
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()
    assert report.status == "completed"
    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    bound = tool_rows[2]["tool_result"]["result"]["claim_binding"]
    assert bound["active_claim_id"] == "claim_error_bound"
    assert bound["status"] == "open"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_execution_reminds_when_open_claims_lack_evidence(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a scientific working claim.",
                claim_id="claim_pending_evidence",
                statement="A bound will be tested after numeric artifacts appear.",
                kind=ClaimKind.SCIENTIFIC.value,
                relation=ClaimRelation.REFINES.value,
                parent_id="claim_root",
                rationale="Exercise mid-campaign evidence gap reminders.",
            ),
            _action(
                action="write_file",
                research_note="Author a smoke script before linking evidence.",
                path="smoke.py",
                content="print('ok')\n",
            ),
            _action(
                action="run_python",
                research_note="Run without linking evidence yet.",
                argv=["smoke.py"],
            ),
            _action(
                action="finish",
                research_note="Stop after observing reminders.",
                final_answer="Evidence gap reminders observed.",
            ),
        ]
    )
    output = tmp_path / "evidence-gap"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Open claims should be reminded to link evidence.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()
    assert report.status == "completed"
    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    write_result = tool_rows[1]["tool_result"]["result"]
    run_result = tool_rows[2]["tool_result"]["result"]
    assert "evidence_reminder" in write_result
    assert "claim_pending_evidence" in write_result["evidence_reminder"]
    assert "evidence_reminder" in run_result
    assert "claim_pending_evidence" in run_result["evidence_reminder"]
    assert run_result["claim_binding"]["active_claim_id"] is None


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_close_claim_soft_warns_without_evidence(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a claim that will close without evidence.",
                claim_id="claim_no_evidence",
                statement="Closing without an artifact link should emit a soft warning.",
                kind=ClaimKind.DIAGNOSTIC.value,
                relation=ClaimRelation.DIAGNOSTIC_OF.value,
                parent_id="claim_root",
                rationale="Exercise unevidenced close soft warning.",
            ),
            _action(
                action="close_claim",
                research_note="Close without linking workspace evidence.",
                claim_id="claim_no_evidence",
                status=ClaimDisposition.UNRESOLVED.value,
                reason="Instrument limit reached before an artifact was linked.",
            ),
            _action(
                action="finish",
                research_note="Done.",
                final_answer="Unevidenced close soft warning exercised.",
            ),
        ]
    )
    output = tmp_path / "close-no-evidence"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Soft warning on unevidenced close_claim.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()
    assert report.status == "completed"
    close_tool = json.loads(
        [
            json.loads(line)
            for line in (output / "transcript.jsonl").read_text().splitlines()
            if json.loads(line)["kind"] == "tool"
        ][1]["content"]
    )
    result = close_tool["tool_result"]["result"]
    assert "evidence_warning" in result
    assert "no linked evidence" in result["evidence_warning"]
    assert "claim_no_evidence" in report.closed_claim_ids
    assert any(
        "closed claims without evidence links: claim_no_evidence" in note
        for note in report.finish_claim_notes
    )


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_supported_close_without_contract_and_evidence_is_rejected(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="close_claim",
                research_note="Close root as supported without linking evidence.",
                claim_id="claim_root",
                status=ClaimDisposition.SUPPORTED.value,
                reason="Narrative support without a bound artifact link.",
            ),
            _action(
                action="finish",
                research_note="Done.",
                final_answer="Root closed supported without evidence.",
            ),
        ]
    )
    output = tmp_path / "supported-no-evidence"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Supported unevidenced root should be flagged softly.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()
    assert report.status == "completed"
    close_tool = json.loads(
        [
            json.loads(line)
            for line in (output / "transcript.jsonl").read_text().splitlines()
            if json.loads(line)["kind"] == "tool"
        ][0]["content"]
    )
    assert close_tool["tool_result"]["ok"] is False
    assert "without a registered evidence contract" in close_tool["tool_result"]["error"]
    assert report.open_claim_ids == ("claim_root",)
    assert report.closed_claim_ids == ()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_evidence_cannot_be_marked_sufficient_without_prospective_contract(
    tmp_path: Path,
) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="write_file",
                research_note="Create a commissioning failure record without a contract.",
                path="failure.json",
                content=json.dumps({"checks": {"valid": False}}),
            ),
            _action(
                action="link_claim_evidence",
                research_note="Attempt to mark pre-contract evidence sufficient.",
                claim_id="claim_root",
                path="failure.json",
                note="This artifact was produced before any decision rule.",
                observation_sufficient=True,
                observation_note="Deliberately invalid sufficiency classification.",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Retain the failure only as an insufficient observation.",
                claim_id="claim_root",
                path="failure.json",
                note="This records a failed design, not root evidence.",
                observation_sufficient=False,
                observation_note="No prospective root evidence contract existed.",
            ),
            _action(
                action="close_claim",
                research_note="Close the root honestly without a scientific conclusion.",
                claim_id="claim_root",
                status=ClaimDisposition.UNRESOLVED.value,
                reason="Only an uncommissioned failure record was available.",
            ),
            _action(
                action="finish",
                research_note="Finish with the bounded unresolved result.",
                final_answer="The root remains unresolved after failed commissioning.",
            ),
        ]
    )
    output = tmp_path / "precontract-sufficiency"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="A commissioned calculation will resolve this claim.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[1]["tool_result"]["ok"] is False
    assert "without a prospective evidence contract" in tool_rows[1]["tool_result"]["error"]
    root = report.claim_ledger["claims"][0]
    assert root["status"] == "unresolved"
    assert len(root["evidence"]) == 1
    assert root["evidence"][0]["observation_sufficient"] is False
    assert root["evidence"][0]["contract_version"] is None


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_insufficient_observation_cannot_support_claim_and_inline_code_is_preserved(
    tmp_path: Path,
) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register the observation rule before execution.",
                claim_id="claim_root",
                observable="The measured response after ten complete periods.",
                expected_outcomes="A bounded response supports; growth falsifies.",
                decision_rule="Classify only after ten complete periods are measured.",
                required_observation="At least ten complete periods must be recorded.",
                uncertainty_criterion="Signal must exceed the measured noise by fivefold.",
                inconclusive_conditions="Short duration or low signal is inconclusive.",
            ),
            _action(
                action="run_python",
                research_note="Generate a deliberately short observation.",
                argv=[
                    "-c",
                    ("from pathlib import Path; Path('short_result.txt').write_text('periods=2')"),
                ],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Record that the short observation is insufficient.",
                claim_id="claim_root",
                path="short_result.txt",
                note="Only two of ten required periods were observed.",
                observation_sufficient=False,
                observation_note="Two periods do not satisfy the required ten periods.",
            ),
            _action(
                action="close_claim",
                research_note="Attempt an invalid supported disposition.",
                claim_id="claim_root",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The short result appeared bounded despite inadequate coverage.",
            ),
            _action(
                action="close_claim",
                research_note="Close honestly after the support gate rejects the result.",
                claim_id="claim_root",
                status=ClaimDisposition.UNRESOLVED.value,
                reason="The observation covered only two of ten required periods.",
            ),
            _action(
                action="finish",
                research_note="Finish with the bounded unresolved disposition.",
                final_answer="The claim remains unresolved because coverage was short.",
            ),
        ]
    )
    output = tmp_path / "insufficient-observation"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="A response remains bounded over ten periods.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[3]["tool_result"]["ok"] is False
    assert "observation_sufficient=true" in tool_rows[3]["tool_result"]["error"]
    assert report.claim_ledger["claims"][0]["status"] == "unresolved"
    evidence = report.claim_ledger["claims"][0]["evidence"][0]
    assert evidence["observation_sufficient"] is False
    assert evidence["provenance"]["tracked"] is True
    assert evidence["provenance"]["action"] == "run_python"
    preserved = output / "workspace/.acs/evidence_programs/iteration_000002.py"
    assert preserved.is_file()
    assert "short_result.txt" in preserved.read_text()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_claim_ledger_registers_links_closes_and_survives_in_report(
    tmp_path: Path,
) -> None:
    hypothesis = "A particle invariant is conserved in a slowly varying field."
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register the first working scientific claim.",
                claim_id="claim_mu_bounded",
                statement=(
                    "Relative magnetic-moment drift stays below one percent over ten "
                    "bounce periods in an adiabatic mirror."
                ),
                kind=ClaimKind.SCIENTIFIC.value,
                relation=ClaimRelation.REFINES.value,
                parent_id="claim_root",
                rationale="Operational quantitative form of the root hypothesis.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Register the prospective numeric acceptance rule.",
                claim_id="claim_mu_bounded",
                observable="Maximum relative magnetic-moment drift over the orbit.",
                expected_outcomes=(
                    "Drift below one percent supports the scoped claim; larger drift "
                    "weakens or falsifies it."
                ),
                decision_rule="Support only when measured relative error is below 0.01.",
                required_observation="Observe all ten requested bounce periods.",
                uncertainty_criterion=(
                    "The reported error must remain separated from the 0.01 threshold."
                ),
                inconclusive_conditions=(
                    "Fewer than ten periods or unresolved numerical error is inconclusive."
                ),
            ),
            _action(
                action="write_file",
                research_note="Author a minimal numeric check for claim_mu_bounded.",
                path="check.py",
                content=(
                    "from pathlib import Path\n"
                    "Path('mu_error.txt').write_text('relative_error=0.004')\n"
                    "print('ok')\n"
                ),
            ),
            _action(
                action="run_python",
                research_note="Run the numeric check for claim_mu_bounded.",
                argv=["check.py"],
                active_claim_id="claim_mu_bounded",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Bind the numeric artifact to the active claim.",
                claim_id="claim_mu_bounded",
                path="mu_error.txt",
                note="Relative error 0.4% is inside the one-percent bound.",
                observation_sufficient=True,
                observation_note=("All ten periods were represented and 0.004 is below 0.01."),
            ),
            _action(
                action="close_claim",
                research_note="Close the working claim as supported in this scope.",
                claim_id="claim_mu_bounded",
                status=ClaimDisposition.SUPPORTED.value,
                reason="Observed relative error 0.4% within the stated bound.",
            ),
            _action(
                action="list_claims",
                research_note="Inspect the durable claim ledger before finishing.",
            ),
            _action(
                action="finish",
                research_note="Report a bounded conclusion using the claim ledger.",
                final_answer=(
                    "claim_mu_bounded is supported at 0.4% relative error in the "
                    "tested mirror case; the root remains open beyond that scope."
                ),
            ),
        ]
    )
    output = tmp_path / "claims"
    config = _config(max_iterations=12)
    report = MVPAgentRunner(
        hypothesis=hypothesis,
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "completed"
    assert report.iterations == 8
    claims = {claim["id"]: claim for claim in report.claim_ledger["claims"]}
    assert "claim_root" in claims
    assert claims["claim_mu_bounded"]["status"] == "supported"
    assert len(claims["claim_mu_bounded"]["evidence_contracts"]) == 1
    assert claims["claim_mu_bounded"]["evidence"][0]["path"] == "mu_error.txt"
    evidence = claims["claim_mu_bounded"]["evidence"][0]
    assert evidence["contract_version"] == 1
    assert evidence["observation_sufficient"] is True
    assert evidence["provenance"]["tracked"] is True
    assert evidence["provenance"]["generated_iteration"] == 4
    assert evidence["provenance"]["action"] == "run_python"
    assert evidence["provenance"]["program_path"] == "check.py"
    assert len(evidence["provenance"]["sha256"]) == 64
    assert "claim_mu_bounded" in report.closed_claim_ids
    assert "claim_root" in report.open_claim_ids
    assert any("claim_root remains open at finish" in note for note in report.finish_claim_notes)
    assert any("closed_claim_count=1" in note for note in report.finish_claim_notes)
    assert any("open_claim_count=1" in note for note in report.finish_claim_notes)
    durable = json.loads((output / "hypothesis_ledger.json").read_text())
    assert durable["claims"][-1]["id"] == "claim_mu_bounded"
    summary = (output / "claim_summary.md").read_text()
    assert "# Claim summary" in summary
    assert "claim_mu_bounded" in summary
    assert "supported" in summary
    assert "## Details" in summary
    assert "`mu_error.txt`" in summary
    assert "Evidence contracts: 1" in summary
    assert "sufficient" in summary
    assert "run_python" in summary
    # closed_reason must not break the claims table (no prose between rows)
    claims_section = summary.split("## Claims", 1)[1].split("## Details", 1)[0]
    assert "closed_reason" not in claims_section
    assert "| contracts | evidence |" in claims_section or "contracts |" in claims_section
    # Tool results should expose the compact ledger continuously.
    first_tool = json.loads(
        [
            json.loads(line)
            for line in (output / "transcript.jsonl").read_text().splitlines()
            if json.loads(line)["kind"] == "tool"
        ][0]["content"]
    )
    assert first_tool["tool_result"]["ok"] is True
    assert first_tool["tool_result"]["result"]["claim_ledger"]["claim_count"] == 2


def _write_test_skill_and_capability(
    tmp_path: Path,
) -> tuple[MVPSkillCatalog, MVPCapabilityRegistry]:
    skill = tmp_path / "skills" / "python-tool"
    skill.mkdir(parents=True)
    (skill / "manifest.json").write_text(
        json.dumps(
            {
                "name": "python-tool",
                "version": "1.0",
                "description": "A test executable skill",
                "entrypoint": "SKILL.md",
                "capability_names": ["isolated-python"],
            }
        )
    )
    (skill / "SKILL.md").write_text("# Test skill\nRun only a bounded test.\n")
    (skill / "examples").mkdir()
    (skill / "examples/audit.py").write_bytes(
        b"from pathlib import Path\r\n"
        b"Path('audit.json').write_text('{\"checks\":{\"healthy\":true}}\\n')\r\n"
    )
    (skill / "scripts").mkdir()
    (skill / "scripts/probe.py").write_text("print('operator only')\n")
    capability_root = tmp_path / "capabilities"
    capability_root.mkdir()
    (capability_root / "isolated-python.json").write_text(
        json.dumps(
            {
                "manifest": {
                    "name": "isolated-python",
                    "version": "1.0",
                    "description": "System Python mounted as a test capability",
                    "skill": "python-tool",
                    "executable_kind": "python",
                    "preflight_checks": ["checks.healthy"],
                    "preflight_resource": "examples/audit.py",
                    "preflight_result": "audit.json",
                },
                "runtime_root": "/usr",
                "executable": "bin/python3",
            }
        )
    )
    return (
        MVPSkillCatalog.discover(tmp_path / "skills"),
        MVPCapabilityRegistry.discover(capability_root),
    )


def test_installed_capability_keeps_full_commissioning_prompt(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    config = _config()
    output = tmp_path / "capability-prompt"
    runner = MVPAgentRunner(
        hypothesis="An installed instrument may test a bounded physical prediction.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    )

    system, initial = runner._initial_messages()
    payload = json.loads(initial["content"])
    gate = payload["claim_protocol"]["capability_commissioning_gate"]
    assert "Capability work has two stages" in system["content"]
    assert gate["available"] is True
    assert gate["required_aspects_in_one_contract"] == [
        "boundaries",
        "diagnostics",
        "numerical_regime",
        "physics_controls",
        "representation",
    ]
    assert gate["one_interface_stage_per_parent_and_capability"] is True
    assert gate["scientific_program_must_match_commissioned_source"] is True


def test_capability_runtime_identity_tracks_bounded_python_records(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    executable = runtime / "bin/tool"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    record = runtime / "lib/python3.11/site-packages/demo-1.0.dist-info/RECORD"
    record.parent.mkdir(parents=True)
    record.write_text("demo.py,sha256=first,1\n")

    capability_root = tmp_path / "capabilities"
    capability_root.mkdir()
    config = capability_root / "bounded-runtime.json"
    config.write_text(
        json.dumps(
            {
                "manifest": {
                    "name": "bounded-runtime",
                    "version": "1.0",
                    "description": "A bounded runtime-identity fixture",
                    "skill": "python-tool",
                    "executable_kind": "fixture",
                },
                "runtime_root": "../runtime",
                "executable": "bin/tool",
            }
        )
    )

    installed = MVPCapabilityInstallation.read(config)
    installed.assert_runtime_identity()
    record.write_text("demo.py,sha256=changed,1\n")
    with pytest.raises(RuntimeError, match="changed after campaign discovery"):
        installed.assert_runtime_identity()


def test_capability_runtime_identity_tracks_declared_sibling_files(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    executable = runtime / "bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    simulator = runtime / "bin/simulator"
    simulator.write_bytes(b"simulator-v1")
    build_record = runtime / "share/build-record.json"
    build_record.parent.mkdir(parents=True)
    build_record.write_text('{"build":"v1"}\n')
    untracked = runtime / "share/operator-note.txt"
    untracked.write_text("first\n")

    capability_root = tmp_path / "capabilities"
    capability_root.mkdir()
    config = capability_root / "composite-runtime.json"
    config.write_text(
        json.dumps(
            {
                "manifest": {
                    "name": "composite-runtime",
                    "version": "1.0",
                    "description": "A launcher with explicitly bound sibling files",
                    "skill": "simulation-tool",
                    "executable_kind": "python-simulator",
                },
                "runtime_root": "../runtime",
                "executable": "bin/python",
                "identity_files": ["share/build-record.json", "bin/simulator"],
            }
        )
    )

    installed = MVPCapabilityInstallation.read(config)
    assert installed.identity_files == (build_record, simulator)
    installed.assert_runtime_identity()
    untracked.write_text("changed but deliberately unbound\n")
    installed.assert_runtime_identity()
    simulator.write_bytes(b"simulator-v2")
    with pytest.raises(RuntimeError, match="changed after campaign discovery"):
        installed.assert_runtime_identity()


def test_empty_capability_identity_files_preserve_legacy_runtime_hash(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    executable = runtime / "bin/tool"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    capability_root = tmp_path / "capabilities"
    capability_root.mkdir()
    base = {
        "manifest": {
            "name": "legacy-runtime",
            "version": "1.0",
            "description": "A legacy executable-only identity",
            "skill": "simulation-tool",
            "executable_kind": "fixture",
        },
        "runtime_root": "../runtime",
        "executable": "bin/tool",
    }
    omitted = capability_root / "omitted.json"
    omitted.write_text(json.dumps(base))
    explicit = capability_root / "explicit.json"
    explicit.write_text(json.dumps({**base, "identity_files": []}))

    legacy = MVPCapabilityInstallation.read(omitted)
    empty = MVPCapabilityInstallation.read(explicit)
    assert legacy.identity_files == ()
    assert empty.identity_files == ()
    assert empty.runtime_identity == legacy.runtime_identity


@pytest.mark.parametrize(
    ("identity_files", "message"),
    [
        (["../outside"], "contained relative path"),
        (["/outside"], "contained relative path"),
        (["share/record.json", "share/record.json"], "must be unique"),
        (["bin/tool"], "executable is already part"),
    ],
)
def test_capability_identity_file_configuration_rejects_ambiguous_paths(
    tmp_path: Path,
    identity_files: list[str],
    message: str,
) -> None:
    runtime = tmp_path / "runtime"
    executable = runtime / "bin/tool"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    record = runtime / "share/record.json"
    record.parent.mkdir(parents=True)
    record.write_text("{}\n")
    capability_root = tmp_path / "capabilities"
    capability_root.mkdir()
    config = capability_root / "invalid-identity.json"
    config.write_text(
        json.dumps(
            {
                "manifest": {
                    "name": "invalid-identity",
                    "version": "1.0",
                    "description": "An invalid identity fixture",
                    "skill": "simulation-tool",
                    "executable_kind": "fixture",
                },
                "runtime_root": "../runtime",
                "executable": "bin/tool",
                "identity_files": identity_files,
            }
        )
    )

    with pytest.raises(ValueError, match=message):
        MVPCapabilityInstallation.read(config)


def test_capability_identity_files_must_be_available_regular_files(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    executable = runtime / "bin/tool"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    share = runtime / "share"
    share.mkdir()
    record = share / "record.json"
    record.write_text("{}\n")
    alias = share / "record-link.json"
    alias.symlink_to(record)
    capability_root = tmp_path / "capabilities"
    capability_root.mkdir()
    base = {
        "manifest": {
            "name": "invalid-identity-file",
            "version": "1.0",
            "description": "An invalid identity-file fixture",
            "skill": "simulation-tool",
            "executable_kind": "fixture",
        },
        "runtime_root": "../runtime",
        "executable": "bin/tool",
    }

    for index, (relative, error_type, message) in enumerate(
        (
            ("share/missing.json", FileNotFoundError, "is unavailable"),
            ("share", ValueError, "not a regular file"),
            ("share/record-link.json", ValueError, "cannot be symlinks"),
        )
    ):
        config = capability_root / f"invalid-{index}.json"
        config.write_text(json.dumps({**base, "identity_files": [relative]}))
        with pytest.raises(error_type, match=message):
            MVPCapabilityInstallation.read(config)


def test_skill_catalog_is_hashed_and_rejects_traversal(tmp_path: Path) -> None:
    skills, _capabilities = _write_test_skill_and_capability(tmp_path)
    descriptor = skills.descriptors()[0]
    assert descriptor["name"] == "python-tool"
    assert len(descriptor["content_sha256"]) == 64
    result = skills.read("python-tool", None, max_chars=1000)
    assert "bounded test" in result["content"]
    with pytest.raises(ValueError, match="contained"):
        skills.read("python-tool", "../outside", max_chars=1000)
    cache = tmp_path / "skills/python-tool/scripts/__pycache__"
    cache.mkdir()
    (cache / "probe.cpython-311.pyc").write_bytes(b"generated")
    assert "bounded test" in skills.read("python-tool", None, max_chars=1000)["content"]
    with pytest.raises(ValueError, match="generated artifacts"):
        skills.read(
            "python-tool",
            "scripts/__pycache__/probe.cpython-311.pyc",
            max_chars=1000,
        )
    (tmp_path / "skills/python-tool/SKILL.md").write_text("changed")
    with pytest.raises(RuntimeError, match="changed after campaign discovery"):
        skills.read("python-tool", None, max_chars=1000)


def test_agent_materializes_exact_hashed_skill_resource(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="materialize_skill_resource",
                skill="python-tool",
                source_path="examples/audit.py",
                destination_path="trusted/audit.py",
                research_note="Copy the trusted audit without transcription.",
            ),
            _action(
                action="finish",
                research_note="Stop after verifying exact materialization.",
                final_answer="The trusted audit was materialized but not executed.",
            ),
        ]
    )
    output = tmp_path / "materialized"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="A trusted audit can be reused exactly.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    expected = (tmp_path / "skills/python-tool/examples/audit.py").read_bytes()
    copied = output / "workspace/trusted/audit.py"
    assert report.status == "completed"
    assert copied.read_bytes() == expected

    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    result = json.loads(transcript[1]["content"])["tool_result"]["result"]
    assert result["scientific_evidence_eligible"] is False
    assert result["source_skill_resource"]["skill"] == "python-tool"
    assert result["source_skill_resource"]["path"] == "examples/audit.py"
    assert result["source_skill_resource"]["content_sha256"] == hashlib.sha256(expected).hexdigest()
    assert result["sha256"] == result["source_skill_resource"]["content_sha256"]
    provenance = json.loads((output / "artifact_provenance.json").read_text())
    record = provenance["artifacts"]["trusted/audit.py"]
    assert record["action"] == "materialize_skill_resource"
    assert record["skill_resource"] == result["source_skill_resource"]


def test_executable_skill_read_pins_exact_reuse_action(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="read_skill",
                skill="python-tool",
                path="examples/audit.py",
                research_note="Read the trusted executable audit.",
            ),
            _action(
                action="finish",
                research_note="Stop after inspecting the exact-reuse routing.",
                final_answer="The executable skill read exposed exact reuse.",
            ),
        ]
    )
    output = tmp_path / "executable-read"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Executable skill reads route toward exact reuse.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    result = json.loads(transcript[1]["content"])["tool_result"]["result"]
    exact_reuse = result["exact_reuse"]
    assert exact_reuse["action"] == {
        "action": "materialize_skill_resource",
        "skill": "python-tool",
        "source_path": "examples/audit.py",
        "destination_path": "skill_resources/python-tool/examples/audit.py",
        "research_note": (
            "Materialize the trusted executable skill resource without prompt transcription."
        ),
    }
    assert exact_reuse["run_python_argv_prefix"] == [
        "skill_resources/python-tool/examples/audit.py"
    ]
    assert exact_reuse["capability_execution_stage"] == "workbench"
    assert "not a prerequisite" in exact_reuse["policy"]
    sticky = json.loads(client.calls[1]["messages"][-1]["content"])
    assert sticky["pinned_skill_resources"][0]["exact_reuse"] == exact_reuse


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_workbench_capability_allows_free_revision_but_cannot_support_claim(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="author_and_run_capability",
                stage="workbench",
                research_note="Iterate on a candidate program before qualification.",
                path="candidate.py",
                content=(
                    "import json\nfrom pathlib import Path\n"
                    "Path('candidate.json').write_text(json.dumps({'value': 1}))\n"
                ),
                capability="isolated-python",
                argv=["candidate.py"],
            ),
            _action(
                action="register_evidence_contract",
                research_note="Prospectively define the root decision after scouting.",
                claim_id="claim_root",
                observable="The candidate JSON scalar response value.",
                expected_outcomes="One supports the claim; zero falsifies it.",
                decision_rule="Support only when the fresh qualified value is one.",
                required_observation="One fresh qualified execution is required.",
                uncertainty_criterion="The deterministic scalar has no sampling error.",
                inconclusive_conditions="Workbench-only output is inconclusive.",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Verify that scouting output cannot be promoted retroactively.",
                claim_id="claim_root",
                path="candidate.json",
                note="This artifact came from workbench commissioning.",
                observation_sufficient=True,
                observation_note="The value is one but was generated before promotion.",
            ),
            _action(
                action="author_and_run_capability",
                stage="workbench",
                research_note="Revise and rerun freely in the commissioning workbench.",
                path="candidate.py",
                content=(
                    "import json\nfrom pathlib import Path\n"
                    "Path('candidate_v2.json').write_text(json.dumps({'value': 2}))\n"
                ),
                capability="isolated-python",
                argv=["candidate.py"],
            ),
            _action(
                action="finish",
                research_note="Finish after checking workbench semantics.",
                final_answer="Workbench revisions ran but produced no scientific evidence.",
            ),
        ]
    )
    output = tmp_path / "workbench"
    config = _config(max_iterations=8)
    report = MVPAgentRunner(
        hypothesis="A candidate capability response equals one.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    assert (output / "workspace/candidate_v2.json").is_file()
    provenance = json.loads((output / "artifact_provenance.json").read_text())
    assert provenance["artifacts"]["candidate.json"]["execution_stage"] == "workbench"
    assert provenance["artifacts"]["candidate.json"]["evidence_eligible"] is False
    tools = [
        json.loads(json.loads(line)["content"])["tool_result"]
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tools[2]["ok"] is False
    assert "workbench artifact" in tools[2]["error"]
    assert report.claim_ledger["claims"][0]["evidence"] == []
    assert report.capability_preflights["isolated-python"]["healthy"] is True


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_run_python_cannot_launder_declared_workbench_input(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    anchor = "workbench observation\n"
    client = ScriptedCompletionClient(
        [
            _action(
                action="author_and_run_capability",
                stage="workbench",
                research_note="Create a deliberately non-evidentiary workbench observation.",
                path="anchor.py",
                content=(
                    "from pathlib import Path\n"
                    f"Path('anchor.txt').write_text({anchor!r})\n"
                ),
                capability="isolated-python",
                argv=["anchor.py"],
                input_artifacts=[],
            ),
            _action(
                action="run_python",
                research_note="Analyze the declared workbench input without promoting it.",
                argv=[
                    "-c",
                    "from pathlib import Path; "
                    "Path('derived.txt').write_text(Path('anchor.txt').read_text())",
                ],
                input_artifacts=[
                    {
                        "path": "anchor.txt",
                        "sha256": hashlib.sha256(anchor.encode()).hexdigest(),
                    }
                ],
            ),
            _action(
                action="finish",
                research_note="Finish after verifying direct-input taint propagation.",
                final_answer="The derived workbench analysis remains non-evidentiary.",
            ),
        ]
    )
    output = tmp_path / "workbench-lineage"
    config = _config(max_iterations=4)
    report = MVPAgentRunner(
        hypothesis="A derived analysis cannot promote workbench data into evidence.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    provenance = json.loads((output / "artifact_provenance.json").read_text())["artifacts"]
    anchor_record = provenance["anchor.txt"]
    derived = provenance["derived.txt"]
    assert anchor_record["execution_stage"] == "workbench"
    assert anchor_record["evidence_eligible"] is False
    assert derived["input_artifacts_declared"] is True
    assert derived["input_lineage_eligible"] is False
    assert derived["evidence_candidate"] is True
    assert derived["evidence_eligible"] is False
    assert derived["input_artifacts"] == [
        {
            "action": "author_and_run_capability",
            "action_sha256": anchor_record["action_sha256"],
            "bytes": len(anchor.encode()),
            "evidence_eligible": False,
            "generated_iteration": 1,
            "operation_id": None,
            "path": "anchor.txt",
            "sha256": hashlib.sha256(anchor.encode()).hexdigest(),
            "tracked": True,
        }
    ]


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_run_python_preserves_eligible_declared_input_lineage(tmp_path: Path) -> None:
    source = "qualified observation\n"
    client = ScriptedCompletionClient(
        [
            _action(
                action="run_python",
                research_note="Generate a fresh self-contained source observation.",
                argv=[
                    "-c",
                    f"from pathlib import Path; Path('source.txt').write_text({source!r})",
                ],
                input_artifacts=[],
            ),
            _action(
                action="run_python",
                research_note="Derive a result from the exact eligible source observation.",
                argv=[
                    "-c",
                    "from pathlib import Path; "
                    "Path('derived.txt').write_text(Path('source.txt').read_text())",
                ],
                input_artifacts=[
                    {
                        "path": "source.txt",
                        "sha256": hashlib.sha256(source.encode()).hexdigest(),
                    }
                ],
            ),
            _action(
                action="finish",
                research_note="Finish after verifying eligible lineage propagation.",
                final_answer="The content-addressed eligible lineage was preserved.",
            ),
        ]
    )
    output = tmp_path / "eligible-lineage"
    config = _config(max_iterations=4)
    report = MVPAgentRunner(
        hypothesis="Eligible direct inputs remain eligible through a successful analysis.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "completed"
    provenance = json.loads((output / "artifact_provenance.json").read_text())["artifacts"]
    assert provenance["source.txt"]["evidence_eligible"] is True
    assert provenance["derived.txt"]["input_lineage_eligible"] is True
    assert provenance["derived.txt"]["input_artifacts"][0]["evidence_eligible"] is True
    assert provenance["derived.txt"]["evidence_eligible"] is True


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_execution_rejects_changed_declared_input_before_side_effects(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="write_file",
                research_note="Create a tracked input whose declared digest will be wrong.",
                path="input.txt",
                content="actual\n",
            ),
            _action(
                action="run_python",
                research_note="Attempt execution against a mismatched content address.",
                argv=[
                    "-c",
                    "from pathlib import Path; Path('should_not_exist.txt').write_text('bad')",
                ],
                input_artifacts=[{"path": "input.txt", "sha256": "0" * 64}],
            ),
            _action(
                action="finish",
                research_note="Finish after the pre-execution mismatch rejection.",
                final_answer="The changed input was rejected before execution.",
            ),
        ]
    )
    output = tmp_path / "changed-input"
    config = _config(max_iterations=4)
    report = MVPAgentRunner(
        hypothesis="Changed declared inputs are rejected before execution.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    assert report.status == "completed"
    assert not (output / "workspace/should_not_exist.txt").exists()
    tool_rows = [
        json.loads(json.loads(line)["content"])["tool_result"]
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[1]["ok"] is False
    assert "declared input artifact 'input.txt' changed" in tool_rows[1]["error"]


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_explicit_input_view_hides_omitted_file_and_directory(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(tmp_path / "workspace", _config())
    program = (
        "import sys\n"
        "from pathlib import Path\n"
        "source = Path(sys.argv[1])\n"
        "if source.is_file():\n"
        "    payload = source.read_text()\n"
        "else:\n"
        "    payload = next(source.glob('*.h5')).read_text()\n"
        "Path(sys.argv[2]).write_text(payload)\n"
    )
    sandbox.write_file("analysis/analyze.py", program)
    sandbox.write_file("hidden.txt", "hidden-file")
    sandbox.write_file("evidence/run/out/chk_0001.h5", "hidden-directory")
    program_sha256 = hashlib.sha256(program.encode()).hexdigest()

    omitted_file = sandbox.run_python(
        ("analysis/analyze.py", "hidden.txt", "analysis/file-result.json"),
        input_artifacts=(),
        program_path="analysis/analyze.py",
        program_sha256=program_sha256,
    )
    omitted_directory = sandbox.run_python(
        (
            "analysis/analyze.py",
            "evidence/run/out",
            "analysis/directory-result.json",
        ),
        input_artifacts=(),
        program_path="analysis/analyze.py",
        program_sha256=program_sha256,
    )
    declared_directory = sandbox.run_python(
        (
            "analysis/analyze.py",
            "evidence/run/out",
            "analysis/declared-directory-result.json",
        ),
        input_artifacts=(
            MVPArtifactInput(
                path="evidence/run/out/chk_0001.h5",
                sha256=hashlib.sha256(b"hidden-directory").hexdigest(),
            ),
        ),
        program_path="analysis/analyze.py",
        program_sha256=program_sha256,
    )

    assert omitted_file.returncode != 0
    assert omitted_directory.returncode != 0
    assert declared_directory.returncode == 0, declared_directory.stderr
    assert not (sandbox.root / "analysis/file-result.json").exists()
    assert not (sandbox.root / "analysis/directory-result.json").exists()
    assert (sandbox.root / "analysis/declared-directory-result.json").read_text() == (
        "hidden-directory"
    )


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_explicit_input_view_mounts_input_read_only_and_collects_nested_output(
    tmp_path: Path,
) -> None:
    sandbox = BubblewrapSandbox(tmp_path / "workspace", _config())
    program = (
        "from pathlib import Path\n"
        "source = Path('inputs/source.txt')\n"
        "Path('results/nested/result.txt').parent.mkdir(parents=True)\n"
        "Path('results/nested/result.txt').write_text(source.read_text().upper())\n"
    )
    source = "qualified input\n"
    sandbox.write_file("analysis/analyze.py", program)
    sandbox.write_file("inputs/source.txt", source)
    result = sandbox.run_python(
        ("analysis/analyze.py",),
        input_artifacts=(
            MVPArtifactInput(
                path="inputs/source.txt",
                sha256=hashlib.sha256(source.encode()).hexdigest(),
            ),
        ),
        program_path="analysis/analyze.py",
        program_sha256=hashlib.sha256(program.encode()).hexdigest(),
    )

    assert result.returncode == 0, result.stderr
    assert (sandbox.root / "results/nested/result.txt").read_text() == source.upper()
    assert (sandbox.root / "inputs/source.txt").read_text() == source

    overwrite = sandbox.run_python(
        ("-c", "from pathlib import Path; Path('inputs/source.txt').write_text('bad')"),
        input_artifacts=(
            MVPArtifactInput(
                path="inputs/source.txt",
                sha256=hashlib.sha256(source.encode()).hexdigest(),
            ),
        ),
    )
    assert overwrite.returncode != 0
    assert (sandbox.root / "inputs/source.txt").read_text() == source


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_legacy_absent_input_field_keeps_full_workspace_visibility(tmp_path: Path) -> None:
    sandbox = BubblewrapSandbox(tmp_path / "workspace", _config())
    sandbox.write_file("legacy-input.txt", "legacy-visible")
    result = sandbox.run_python(
        (
            "-c",
            "from pathlib import Path; "
            "Path('legacy-result.txt').write_text(Path('legacy-input.txt').read_text())",
        )
    )

    assert result.returncode == 0
    assert (sandbox.root / "legacy-result.txt").read_text() == "legacy-visible"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_existing_explicit_action_with_uncovered_argv_directory_cannot_link_sufficient(
    tmp_path: Path,
) -> None:
    output = tmp_path / "argv-coverage"
    config = _config(max_iterations=2)
    sandbox = BubblewrapSandbox(output / "workspace", config)
    runner = MVPAgentRunner(
        hypothesis="A pre-upgrade artifact must retain auditable argv input coverage.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=sandbox,
        config=config,
    )
    sandbox.write_file("analysis/analyze_case.py", "print('sealed program')\n")
    sandbox.write_file("evidence/repair_s2000r512/out/chk_0001.h5", "hidden input")
    sandbox.write_file("analysis/probe_s2000r512_partial.json", '{"value": 1}')
    metadata = sandbox.artifact_metadata("analysis/probe_s2000r512_partial.json")
    runner._artifact_provenance["artifacts"][metadata["path"]] = {
        "bytes": metadata["bytes"],
        "mtime_ns": metadata["mtime_ns"],
        "generated_iteration": 1,
        "action": "run_python",
        "action_sha256": "a" * 64,
        "command_argv": [
            "analysis/analyze_case.py",
            "evidence/repair_s2000r512/out",
            "--output",
            "analysis/probe_s2000r512_partial.json",
        ],
        "program_path": "analysis/analyze_case.py",
        "program_sha256": hashlib.sha256(b"print('sealed program')\n").hexdigest(),
        "execution_succeeded": True,
        "execution_returncode": 0,
        "execution_timed_out": False,
        "execution_workspace_exceeded": False,
        "input_artifacts_declared": True,
        "input_artifacts": [],
        "input_lineage_eligible": True,
        "input_lineage_issues": [],
        "evidence_candidate": True,
        "evidence_eligible": True,
    }
    runner._persist_artifact_provenance()

    provenance = runner._evidence_provenance(metadata)
    assert provenance.argv_input_coverage_eligible is False
    assert provenance.evidence_eligible is False
    assert "evidence/repair_s2000r512/out" in provenance.argv_input_coverage_issues[0]
    followup = MVPAgentRunner._parse_action(
        _action(
            action="run_python",
            research_note="Attempt a new analysis of the pre-upgrade artifact.",
            argv=["-c", "print('bounded followup')"],
            input_artifacts=[
                {
                    "path": metadata["path"],
                    "sha256": metadata["sha256"],
                }
            ],
        )
    )
    _parents, lineage_eligible, lineage_issues = runner._resolve_input_artifacts(followup)
    assert lineage_eligible is False
    assert any("argv workspace path is not covered" in issue for issue in lineage_issues)

    contract = MVPAgentRunner._parse_action(
        _action(
            action="register_evidence_contract",
            research_note="Register a prospective root decision contract.",
            claim_id="claim_root",
            observable="The bounded scalar stored in the JSON artifact.",
            expected_outcomes="One supports the claim and zero falsifies it.",
            decision_rule="Accept only a qualifying fresh artifact with value one.",
            required_observation="One qualifying fresh observation is required.",
            uncertainty_criterion="The deterministic scalar has no sampling uncertainty.",
            inconclusive_conditions="Uncovered inputs make the observation inconclusive.",
        )
    )
    runner._perform_compat(contract, iteration=2, timeout_seconds=1)
    link = MVPAgentRunner._parse_action(
        _action(
            action="link_claim_evidence",
            research_note="Attempt to link the pre-upgrade artifact.",
            claim_id="claim_root",
            path="analysis/probe_s2000r512_partial.json",
            note="The result appears numerically complete.",
            observation_sufficient=True,
            observation_note="The scalar is present but its argv inputs were uncovered.",
        )
    )
    with pytest.raises(ValueError, match="derived artifact sufficient"):
        runner._perform_compat(link, iteration=3, timeout_seconds=1)


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_capability_preflight_is_shared_across_campaigns(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    cache = tmp_path / "preflight-cache"
    config = _config(max_iterations=2)

    def run(output: Path) -> MVPAgentRunner:
        return MVPAgentRunner(
            hypothesis="A workbench program can execute.",
            output_directory=output,
            completion_client=ScriptedCompletionClient(
                [
                    _action(
                        action="author_and_run_capability",
                        stage="workbench",
                        research_note="Execute a workbench candidate.",
                        path="candidate.py",
                        content="print('candidate')\n",
                        capability="isolated-python",
                        argv=["candidate.py"],
                    ),
                    _action(
                        action="finish",
                        research_note="Finish the cache test.",
                        final_answer="The candidate executed.",
                    ),
                ]
            ),
            sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
            config=config,
            skills=skills,
            capabilities=capabilities,
        )

    first = run(tmp_path / "first")
    second = run(tmp_path / "second")
    first.capability_preflight_cache = cache
    second.capability_preflight_cache = cache
    first_report = first.run()
    second_report = second.run()

    assert first_report.capability_preflights["isolated-python"]["healthy"] is True
    assert second_report.capability_preflights["isolated-python"]["healthy"] is True
    records = list(cache.glob("*/record.json"))
    assert len(records) == 1


def test_operator_skill_scripts_are_not_exact_reuse_targets(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="read_skill",
                skill="python-tool",
                path="scripts/probe.py",
                research_note="Read the operator host script.",
            ),
            _action(
                action="finish",
                research_note="Stop after inspecting the script routing.",
                final_answer="Operator scripts are not exact-reuse targets.",
            ),
        ]
    )
    output = tmp_path / "operator-script-read"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Operator skill scripts stay outside exact reuse.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    result = json.loads(transcript[1]["content"])["tool_result"]["result"]
    assert "exact_reuse" not in result
    sticky = json.loads(client.calls[1]["messages"][-1]["content"])
    assert "exact_reuse" not in sticky["pinned_skill_resources"][0]


def test_materialized_skill_resource_cannot_be_sufficient_evidence(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                claim_id="claim_trusted_copy",
                statement="The trusted copied file is itself a scientific observation.",
                kind=ClaimKind.SCIENTIFIC.value,
                relation=ClaimRelation.REFINES.value,
                parent_id="claim_root",
                rationale="Exercise the guidance-versus-observation boundary.",
                research_note="Register the deliberately invalid evidence target.",
            ),
            _action(
                action="register_evidence_contract",
                claim_id="claim_trusted_copy",
                observable="The copied skill resource exists in the workspace.",
                expected_outcomes="Existence would be claimed to support the target.",
                decision_rule="Mark the copy sufficient if the file exists exactly.",
                required_observation="One exact materialization after this contract.",
                uncertainty_criterion="The byte comparison is deterministic.",
                inconclusive_conditions="A missing or changed copy is inconclusive.",
                research_note="Register a prospective contract before copying.",
            ),
            _action(
                action="materialize_skill_resource",
                skill="python-tool",
                source_path="examples/audit.py",
                destination_path="trusted/audit.py",
                research_note="Materialize guidance after the contract.",
            ),
            _action(
                action="link_claim_evidence",
                claim_id="claim_trusted_copy",
                path="trusted/audit.py",
                note="Attempt to treat copied guidance as an observation.",
                observation_sufficient=True,
                observation_note="The exact file exists after the contract.",
                research_note="This invalid sufficient link must be rejected.",
            ),
            _action(
                action="finish",
                research_note="Stop after the evidence boundary is exercised.",
                final_answer="Copied guidance was correctly rejected as evidence.",
            ),
        ]
    )
    output = tmp_path / "materialized-evidence"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Skill guidance is not scientific evidence.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    claim = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_trusted_copy"]
    assert not claim["evidence"]
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    failed_link = json.loads(transcript[7]["content"])["tool_result"]
    assert failed_link["ok"] is False
    assert "guidance, not a generated scientific observation" in failed_link["error"]


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_agent_reads_skill_and_runs_generic_capability(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="list_skills",
                research_note="Inspect installed instruments before choosing one.",
            ),
            _action(
                action="read_skill",
                research_note="Read the selected instrument guidance before execution.",
                skill="python-tool",
            ),
            _action(
                action="register_claim",
                research_note="Register the capability-scoping instrument claim.",
                claim_id="claim_python_tool",
                statement="The isolated Python capability executes a bounded probe.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Capability executions require an explicit non-scientific target.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Commit the interface probe before capability execution.",
                claim_id="claim_python_tool",
                observable="The isolated capability process exit and standard output.",
                expected_outcomes="A zero exit with expected output supports the probe.",
                decision_rule="Treat only exact successful output as interface success.",
                required_observation="Execute the bounded print probe once.",
                uncertainty_criterion="The deterministic process result has no sampling error.",
                inconclusive_conditions="Timeout or changed output leaves the probe unresolved.",
            ),
            _action(
                action="run_capability",
                research_note="Commission the installed executable with a bounded probe.",
                capability="isolated-python",
                argv=["-c", "print('capability ok')"],
                active_claim_id="claim_python_tool",
            ),
            _action(
                action="finish",
                research_note="The capability interface completed its bounded probe.",
                final_answer="The generic capability interface is operational.",
            ),
        ]
    )
    output = tmp_path / "run"
    config = _config()
    sandbox = BubblewrapSandbox(output / "workspace", config, capabilities)
    report = MVPAgentRunner(
        hypothesis="An installed tool can execute a bounded calculation.",
        output_directory=output,
        completion_client=client,
        sandbox=sandbox,
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    assert report.skill_hashes == skills.hashes
    assert report.capability_hashes == capabilities.hashes
    initial_payload = json.loads(client.calls[0]["messages"][1]["content"])
    assert initial_payload["available_skills"][0]["name"] == "python-tool"
    assert initial_payload["available_capabilities"][0]["name"] == "isolated-python"
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    capability_result = json.loads(transcript[9]["content"])["tool_result"]["result"]
    assert capability_result["returncode"] == 0
    assert capability_result["stdout"].strip() == "capability ok"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_agent_atomically_authors_and_runs_capability_program(tmp_path: Path) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register the atomic capability's instrument claim.",
                claim_id="claim_atomic_tool",
                statement="The capability executes the exact authored program.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Every capability action requires an explicit claim binding.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Commit the atomic execution test before running it.",
                claim_id="claim_atomic_tool",
                observable="The authored program output and preserved result file.",
                expected_outcomes="Expected output and file support exact atomic execution.",
                decision_rule="Support only if the selected capability executes the authored path.",
                required_observation="Run the authored program once in the isolated capability.",
                uncertainty_criterion="This deterministic identity test has no sampling error.",
                inconclusive_conditions="Execution failure or missing output is inconclusive.",
            ),
            _action(
                action="author_and_run_capability",
                research_note=(
                    "Author and execute the bounded instrument probe as one admitted "
                    "laboratory action."
                ),
                path="probe.py",
                content=(
                    "from pathlib import Path\n"
                    "Path('atomic.txt').write_text('ok')\n"
                    "print('atomic capability ok')\n"
                ),
                capability="isolated-python",
                argv=["probe.py"],
                active_claim_id="claim_atomic_tool",
            ),
            _action(
                action="finish",
                research_note="The combined instrument action completed successfully.",
                final_answer="The atomic capability interface is operational.",
            ),
        ]
    )
    output = tmp_path / "run"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="An authored program can be executed by an installed instrument.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    assert "probe.py" in report.workspace_artifacts
    assert "atomic.txt" in report.workspace_artifacts
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    combined_result = json.loads(transcript[5]["content"])["tool_result"]["result"]
    assert combined_result["write_result"]["path"] == "probe.py"
    assert combined_result["execution_result"]["returncode"] == 0
    assert combined_result["execution_result"]["stdout"].strip() == "atomic capability ok"
    assert (output / "workspace/atomic.txt").read_text() == "ok"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_capability_execution_requires_prior_contract_before_side_effects(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register an instrument claim without a contract.",
                claim_id="claim_uncontracted_probe",
                statement="The isolated capability can execute an exploratory probe.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Verify that uncommitted capability scouting is rejected.",
            ),
            _action(
                action="author_and_run_capability",
                research_note="Attempt an uncontracted capability probe.",
                path="uncontracted.py",
                content=(
                    "from pathlib import Path\n"
                    "Path('uncontracted_result.txt').write_text('should not exist')\n"
                ),
                capability="isolated-python",
                argv=["uncontracted.py"],
                active_claim_id="claim_uncontracted_probe",
            ),
            _action(
                action="finish",
                research_note="Finish after verifying pre-side-effect rejection.",
                final_answer="The uncontracted capability probe was rejected.",
            ),
        ]
    )
    output = tmp_path / "uncontracted-capability"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Capability probes require prospective commitments.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert report.status == "completed"
    assert tool_rows[1]["tool_result"]["ok"] is False
    assert "register a prospective evidence contract" in tool_rows[1]["tool_result"]["error"]
    assert not (output / "workspace/uncontracted.py").exists()
    assert not (output / "workspace/uncontracted_result.txt").exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_evidence_contract_rejects_unavailable_capability_at_registration(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Attempt to bind a capability that is not installed.",
                claim_id="claim_root",
                observable="A result from one prospectively bound program.",
                expected_outcomes="A true result supports and false falsifies.",
                decision_rule="Support exactly when the result is true.",
                required_observation="Execute the exact bound program once.",
                uncertainty_criterion="The deterministic boolean must be present.",
                inconclusive_conditions="A missing output is inconclusive.",
                execution_binding={
                    "capability": "python",
                    "program_path": "analyze.py",
                    "commissioning_argv": ["analyze.py", "commission"],
                    "allowed_scientific_argv": [["analyze.py", "science"]],
                },
            ),
            _action(
                action="finish",
                research_note="Finish after the invalid binding is rejected.",
                final_answer="The unavailable capability was rejected prospectively.",
            ),
        ]
    )
    output = tmp_path / "unavailable-contract-capability"
    config = _config(max_iterations=4)
    report = MVPAgentRunner(
        hypothesis="One installed analysis program returns a true result.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    root = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_root"]
    assert tool_rows[0]["tool_result"]["ok"] is False
    assert "unknown or unavailable capabilities ['python']" in tool_rows[0]["tool_result"]["error"]
    assert "available_capabilities ['isolated-python']" in tool_rows[0]["tool_result"]["error"]
    assert root["evidence_contracts"] == []


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_capability_bound_instrument_cannot_be_supported_without_five_aspects(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    program = (
        "import json\n"
        "from pathlib import Path\n"
        "Path('interface.json').write_text("
        "json.dumps({'checks': {'interface_ok': True}}))\n"
    )
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a deliberately incomplete bound instrument.",
                claim_id="claim_incomplete_bound",
                statement="The analysis program is qualified for later scientific use.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Verify that interface checks cannot masquerade as qualification.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Bind science argv but register only an interface check.",
                claim_id="claim_incomplete_bound",
                observable="A JSON interface-availability report.",
                expected_outcomes="True reports an available interface.",
                decision_rule="Support when the interface boolean is true.",
                required_observation="Execute one commissioning command.",
                uncertainty_criterion="The exact boolean must be true.",
                inconclusive_conditions="A missing boolean is inconclusive.",
                validation_checks=[
                    {
                        "aspect": "interface",
                        "json_path": "checks.interface_ok",
                        "expected_value": True,
                    }
                ],
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "analyze.py",
                    "commissioning_argv": ["analyze.py", "commission"],
                    "allowed_scientific_argv": [["analyze.py", "science"]],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Generate the interface-only commissioning artifact.",
                path="analyze.py",
                content=program,
                capability="isolated-python",
                argv=["analyze.py", "commission"],
                active_claim_id="claim_incomplete_bound",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the passing interface-only artifact.",
                claim_id="claim_incomplete_bound",
                path="interface.json",
                note="The interface check is true.",
                observation_sufficient=True,
                observation_note="The sole registered interface assertion passed.",
            ),
            _action(
                action="close_claim",
                research_note="Attempt to use the shallow contract as qualification.",
                claim_id="claim_incomplete_bound",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The interface check passed.",
            ),
            _action(
                action="finish",
                research_note="Finish after incomplete qualification is rejected.",
                final_answer="The bound instrument remained open and unqualified.",
            ),
        ]
    )
    output = tmp_path / "incomplete-bound-instrument"
    config = _config(max_iterations=8)
    report = MVPAgentRunner(
        hypothesis="A qualified analyzer can produce scientific evidence.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    claim = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_incomplete_bound"]
    assert tool_rows[3]["tool_result"]["ok"] is True
    assert tool_rows[4]["tool_result"]["ok"] is False
    assert "missing required machine-checked aspects" in tool_rows[4]["tool_result"]["error"]
    assert claim["status"] == "open"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_bound_commissioning_contract_rejects_scouting_command(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a full bound instrument claim.",
                claim_id="claim_bound_instrument",
                statement="The exact experiment program qualifies the capability.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Scouting must not mutate a bound commissioning stage.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Bind the exact commissioning and science commands.",
                claim_id="claim_bound_instrument",
                observable="A JSON report from the exact commissioning command.",
                expected_outcomes="A valid report qualifies; any mismatch does not.",
                decision_rule="Accept only the prospectively bound command.",
                required_observation="Run experiment.py in commission mode once.",
                uncertainty_criterion="Command provenance must match exactly.",
                inconclusive_conditions="Any other capability argv is scouting.",
                validation_checks=[
                    {
                        "aspect": "interface",
                        "json_path": "checks.ready",
                        "expected_value": True,
                    }
                ],
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "experiment.py",
                    "commissioning_argv": ["experiment.py", "commission"],
                    "allowed_scientific_argv": [["experiment.py", "science"]],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Attempt a scouting probe under the bound claim.",
                path="scout.py",
                content=("from pathlib import Path\nPath('scout_ran.txt').write_text('bad')\n"),
                capability="isolated-python",
                argv=["scout.py"],
                active_claim_id="claim_bound_instrument",
            ),
            _action(
                action="finish",
                research_note="Finish after the bound-command rejection.",
                final_answer="The scouting command was rejected before execution.",
            ),
        ]
    )
    output = tmp_path / "bound-scout"
    config = _config(max_iterations=6)
    report = MVPAgentRunner(
        hypothesis="The exact capability program is a valid instrument.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[2]["tool_result"]["ok"] is False
    assert "commissioning_argv" in tool_rows[2]["tool_result"]["error"]
    assert not (output / "workspace/scout.py").exists()
    assert not (output / "workspace/scout_ran.txt").exists()
    claim = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_bound_instrument"]
    assert claim["status"] == "open"
    assert claim["evidence"] == []


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_bound_commissioning_contract_seals_source_before_first_execution(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    original_program = "from pathlib import Path\nPath('first_execution.txt').write_text('ran')"
    changed_program = "from pathlib import Path\nPath('source_mutation_ran.txt').write_text('bad')"
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a source-bound instrument claim.",
                claim_id="claim_source_bound",
                statement="One exact program source implements the instrument.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="A failed commission must not silently change its model.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Prospectively bind the instrument command.",
                claim_id="claim_source_bound",
                observable="The exact bound program's deterministic execution result.",
                expected_outcomes="Execution succeeds only for the sealed source.",
                decision_rule="Reject any changed source under this contract.",
                required_observation="Execute the bound commissioning command once.",
                uncertainty_criterion="Source identity is an exact SHA-256 comparison.",
                inconclusive_conditions="A source mismatch requires a new contract.",
                validation_checks=[
                    {
                        "aspect": "interface",
                        "json_path": "checks.ready",
                        "expected_value": True,
                    }
                ],
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "experiment.py",
                    "commissioning_argv": ["experiment.py", "commission"],
                    "allowed_scientific_argv": [["experiment.py", "science"]],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Execute and seal the first exact source.",
                path="experiment.py",
                content=original_program,
                capability="isolated-python",
                argv=["experiment.py", "commission"],
                active_claim_id="claim_source_bound",
            ),
            _action(
                action="author_and_run_capability",
                research_note="Attempt to replace the source under the same contract.",
                path="experiment.py",
                content=changed_program,
                capability="isolated-python",
                argv=["experiment.py", "commission"],
                active_claim_id="claim_source_bound",
            ),
            _action(
                action="finish",
                research_note="Finish after proving pre-side-effect source rejection.",
                final_answer="The source mutation was rejected before execution.",
            ),
        ]
    )
    output = tmp_path / "bound-source"
    config = _config(max_iterations=7)
    report = MVPAgentRunner(
        hypothesis="A commissioned instrument retains one exact implementation.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[2]["tool_result"]["ok"] is True
    assert tool_rows[3]["tool_result"]["ok"] is False
    assert "sealed program source" in tool_rows[3]["tool_result"]["error"]
    assert (output / "workspace/experiment.py").read_text() == original_program
    assert (output / "workspace/first_execution.txt").read_text() == "ran"
    assert not (output / "workspace/source_mutation_ran.txt").exists()
    claim = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_source_bound"]
    binding = claim["evidence_contracts"][0]["execution_binding"]
    assert binding["program_sha256"] == hashlib.sha256(original_program.encode()).hexdigest()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_machine_validation_rejects_false_commissioning_summary(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register a prospective instrument qualification claim.",
                claim_id="claim_instrument_invalid",
                statement="The capability realizes the intended geometry before use.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Scientific evidence requires a valid represented object.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Register an exact preflight assertion before execution.",
                claim_id="claim_instrument_invalid",
                observable="A JSON summary of the represented geometry.",
                expected_outcomes="A true geometry check qualifies; false does not.",
                decision_rule="Support only when checks.geometry_valid is exactly true.",
                required_observation="Inspect the complete initialized geometry.",
                uncertainty_criterion="The boolean follows a preserved deterministic check.",
                inconclusive_conditions="Missing or false JSON checks do not qualify.",
                validation_checks=[
                    {
                        "aspect": "representation",
                        "json_path": "checks.geometry_valid",
                        "expected_value": True,
                    }
                ],
            ),
            _action(
                action="author_and_run_capability",
                research_note="Run the preflight that detects an invalid geometry.",
                path="commission_invalid.py",
                content=(
                    "import json\n"
                    "from pathlib import Path\n"
                    "Path('commission.json').write_text("
                    "json.dumps({'checks': {'geometry_valid': False}}))\n"
                ),
                capability="isolated-python",
                argv=["commission_invalid.py"],
                active_claim_id="claim_instrument_invalid",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Attempt to misclassify the failed preflight as sufficient.",
                claim_id="claim_instrument_invalid",
                path="commission.json",
                note="The preflight JSON reports a false validity check.",
                observation_sufficient=True,
                observation_note="This deliberately contradicts the machine check.",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Record the failed preflight honestly as insufficient.",
                claim_id="claim_instrument_invalid",
                path="commission.json",
                note="The represented geometry did not pass commissioning.",
                observation_sufficient=False,
                observation_note="checks.geometry_valid is false, so qualification failed.",
            ),
            _action(
                action="close_claim",
                research_note="Close the failed qualification without enabling evidence.",
                claim_id="claim_instrument_invalid",
                status=ClaimDisposition.INSTRUMENT_LIMITED.value,
                reason="The exact geometry validation check failed.",
            ),
            _action(
                action="finish",
                research_note="Finish after exposing the invalid commissioning attempt.",
                final_answer="The instrument was not qualified for scientific evidence.",
            ),
        ]
    )
    output = tmp_path / "machine-validation"
    config = _config(max_iterations=10)
    report = MVPAgentRunner(
        hypothesis="The capability can measure the requested scientific effect.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[3]["tool_result"]["ok"] is False
    assert "machine-checkable validation failed" in tool_rows[3]["tool_result"]["error"]
    claim = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_instrument_invalid"]
    assert claim["status"] == "instrument_limited"
    assert len(claim["evidence"]) == 1
    assert claim["evidence"][0]["observation_sufficient"] is False
    assert claim["evidence"][0]["validation_passed"] is False
    assert claim["evidence"][0]["validation_results"][0]["actual_value"] is False


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_failed_capability_execution_cannot_qualify_its_written_summary(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register an instrument claim for the failure witness.",
                claim_id="claim_failed_runtime",
                statement="The capability completes the intended commissioning run.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="A summary written before a crash must not qualify the tool.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Register the summary assertion before the failed run.",
                claim_id="claim_failed_runtime",
                observable="A JSON commissioning completion summary.",
                expected_outcomes="A true predicate is usable only after execution succeeds.",
                decision_rule="Require the predicate and runner-owned execution success.",
                required_observation="The capability process must finish without failure.",
                uncertainty_criterion="The runner records the process return code directly.",
                inconclusive_conditions="A nonzero return code is failed commissioning.",
                validation_checks=[
                    {
                        "aspect": "interface",
                        "json_path": "checks.completed",
                        "expected_value": True,
                    }
                ],
            ),
            _action(
                action="author_and_run_capability",
                research_note="Write a misleading summary and then fail the process.",
                path="fails_after_summary.py",
                content=(
                    "import json\n"
                    "from pathlib import Path\n"
                    "Path('failed_summary.json').write_text("
                    "json.dumps({'checks': {'completed': True}}))\n"
                    "raise SystemExit(9)\n"
                ),
                capability="isolated-python",
                argv=["fails_after_summary.py"],
                active_claim_id="claim_failed_runtime",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Try to qualify from the pre-crash true predicate.",
                claim_id="claim_failed_runtime",
                path="failed_summary.json",
                note="The file says completed even though its process failed.",
                observation_sufficient=True,
                observation_note="The JSON predicate alone appears to satisfy the contract.",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Record the runner-witnessed failure honestly.",
                claim_id="claim_failed_runtime",
                path="failed_summary.json",
                note="The process exited nine after writing this file.",
                observation_sufficient=False,
                observation_note="Runner-owned execution provenance makes it insufficient.",
            ),
            _action(
                action="close_claim",
                research_note="Close the failed instrument without qualification.",
                claim_id="claim_failed_runtime",
                status=ClaimDisposition.INSTRUMENT_LIMITED.value,
                reason="The commissioning process returned a nonzero exit status.",
            ),
            _action(
                action="finish",
                research_note="Finish after verifying the independent execution witness.",
                final_answer="The failed execution did not qualify its own summary.",
            ),
        ]
    )
    output = tmp_path / "failed-execution-witness"
    config = _config(max_iterations=10)
    report = MVPAgentRunner(
        hypothesis="The capability can complete the intended measurement.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[2]["tool_result"]["result"]["execution_result"]["returncode"] == 9
    assert tool_rows[3]["tool_result"]["ok"] is False
    assert (
        "runner witnessed a successful capability execution" in tool_rows[3]["tool_result"]["error"]
    )
    claim = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_failed_runtime"]
    assert claim["status"] == "instrument_limited"
    provenance = claim["evidence"][0]["provenance"]
    assert provenance["execution_succeeded"] is False
    assert provenance["execution_returncode"] == 9
    assert provenance["execution_timed_out"] is False
    assert provenance["execution_workspace_exceeded"] is False


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_capability_scientific_evidence_requires_prior_commissioning(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    experiment_program = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "mode = sys.argv[1]\n"
        "if mode == 'commission':\n"
        "    Path('commission.json').write_text(json.dumps({'checks': {"
        "'representation_valid': True, 'physics_controls_valid': True, "
        "'boundaries_valid': True, "
        "'diagnostics_valid': True, 'numerical_regime_valid': True}}))\n"
        "elif mode == 'science':\n"
        "    Path('science.json').write_text(json.dumps({'response': 1.0}))\n"
        "else:\n"
        "    raise SystemExit('unknown mode')\n"
    )
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register the root decision rule before any evidence.",
                claim_id="claim_root",
                observable="A capability-generated scientific response summary.",
                expected_outcomes="A positive response supports; a negative response falsifies.",
                decision_rule="Support when the commissioned response is positive.",
                required_observation="Use a complete run from a qualified capability.",
                uncertainty_criterion="The response must be separated from zero.",
                inconclusive_conditions="Uncommissioned capability evidence is inconclusive.",
            ),
            _action(
                action="author_and_run_capability",
                research_note="Generate premature root evidence before commissioning.",
                path="premature.py",
                content=(
                    "import json\n"
                    "from pathlib import Path\n"
                    "Path('premature.json').write_text(json.dumps({'response': 1.0}))\n"
                ),
                capability="isolated-python",
                argv=["premature.py"],
                active_claim_id="claim_root",
            ),
            _action(
                action="register_claim",
                research_note="Register the separate capability qualification claim.",
                claim_id="claim_capability_ready",
                statement="The capability realizes and reports the intended test object.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Root evidence must follow prospective instrument qualification.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Pre-register the machine-readable qualification check.",
                claim_id="claim_capability_ready",
                observable="A JSON capability commissioning summary.",
                expected_outcomes="All four validity checks qualify; any false check fails.",
                decision_rule="Support only when every registered validity check is true.",
                required_observation=(
                    "Exercise representation, boundaries, diagnostics, and numerics."
                ),
                uncertainty_criterion="Use deterministic booleans computed by preserved code.",
                inconclusive_conditions="Missing or false checks leave the capability unqualified.",
                validation_checks=[
                    {
                        "aspect": "representation",
                        "json_path": "checks.representation_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "physics_controls",
                        "json_path": "checks.physics_controls_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "boundaries",
                        "json_path": "checks.boundaries_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "diagnostics",
                        "json_path": "checks.diagnostics_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "numerical_regime",
                        "json_path": "checks.numerical_regime_valid",
                        "expected_value": True,
                    },
                ],
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "experiment.py",
                    "commissioning_argv": ["experiment.py", "commission"],
                    "allowed_scientific_argv": [["experiment.py", "science"]],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Execute the prospective capability preflight.",
                path="experiment.py",
                content=experiment_program,
                capability="isolated-python",
                argv=["experiment.py", "commission"],
                active_claim_id="claim_capability_ready",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the machine-checked qualification summary.",
                claim_id="claim_capability_ready",
                path="commission.json",
                note="The intended representation and output path passed preflight.",
                observation_sufficient=True,
                observation_note="The exact registered JSON assertion is true.",
            ),
            _action(
                action="close_claim",
                research_note="Close the capability qualification before scientific use.",
                claim_id="claim_capability_ready",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The prospective representation check passed.",
            ),
            _action(
                action="author_and_run_capability",
                research_note="Attempt science from an uncommissioned program source.",
                path="different_science.py",
                content=(
                    "import json\n"
                    "from pathlib import Path\n"
                    "Path('science.json').write_text(json.dumps({'response': 1.0}))\n"
                ),
                capability="isolated-python",
                argv=["different_science.py"],
                active_claim_id="claim_root",
            ),
            _action(
                action="run_capability",
                research_note="Attempt an unregistered scientific configuration.",
                capability="isolated-python",
                argv=["experiment.py", "science-unplanned"],
                active_claim_id="claim_root",
            ),
            _action(
                action="run_capability",
                research_note=(
                    "Generate fresh scientific evidence with the immutable commissioned "
                    "program source and a scientific-mode argument."
                ),
                capability="isolated-python",
                argv=["experiment.py", "science"],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link fresh root evidence through the supported gate.",
                claim_id="claim_root",
                path="science.json",
                note="Fresh evidence was generated after capability qualification.",
                observation_sufficient=True,
                observation_note="The complete commissioned response is positive.",
                commissioning_claim_id="claim_capability_ready",
            ),
            _action(
                action="close_claim",
                research_note="Close the root using only commissioned evidence.",
                claim_id="claim_root",
                status=ClaimDisposition.SUPPORTED.value,
                reason="Fresh positive evidence followed machine-checked commissioning.",
            ),
            _action(
                action="finish",
                research_note="Report the bounded commissioned result.",
                final_answer="The scoped root is supported by commissioned evidence.",
            ),
        ]
    )
    output = tmp_path / "commissioning-gate"
    config = _config(max_iterations=17)
    report = MVPAgentRunner(
        hypothesis="The commissioned capability produces a positive response.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[1]["tool_result"]["ok"] is False
    assert (
        "require a supported machine-checked instrument_of claim"
        in tool_rows[1]["tool_result"]["error"]
    )
    assert not (output / "workspace/premature.py").exists()
    assert not (output / "workspace/premature.json").exists()
    assert tool_rows[7]["tool_result"]["ok"] is False
    assert "same program source" in tool_rows[7]["tool_result"]["error"]
    assert not (output / "workspace/different_science.py").exists()
    assert tool_rows[8]["tool_result"]["ok"] is False
    assert "execution_binding" in tool_rows[8]["tool_result"]["error"]
    assert (
        tool_rows[9]["tool_result"]["result"]["execution_commissioning_claim_id"]
        == "claim_capability_ready"
    )
    claims = {item["id"]: item for item in report.claim_ledger["claims"]}
    assert claims["claim_capability_ready"]["status"] == "supported"
    assert claims["claim_capability_ready"]["evidence"][0]["validation_passed"] is True
    commissioning_provenance = claims["claim_capability_ready"]["evidence"][0]["provenance"]
    assert commissioning_provenance["execution_succeeded"] is True
    assert commissioning_provenance["execution_returncode"] == 0
    assert claims["claim_root"]["status"] == "supported"
    assert len(claims["claim_root"]["evidence"]) == 1
    assert claims["claim_root"]["evidence"][0]["commissioning_claim_id"] == "claim_capability_ready"
    assert claims["claim_root"]["evidence"][0]["path"] == "science.json"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_one_scientific_contract_accepts_a_preregistered_command_sweep(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    program = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "mode = sys.argv[1]\n"
        "if mode == 'commission':\n"
        "    Path('commission.json').write_text(json.dumps({'checks': {"
        "'representation_valid': True, 'physics_controls_valid': True, "
        "'boundaries_valid': True, 'diagnostics_valid': True, "
        "'numerical_regime_valid': True}}))\n"
        "elif mode in {'s25', 's50', 's75'}:\n"
        "    Path(mode + '.json').write_text(json.dumps({'valid': True, "
        "'point': mode}))\n"
        "else:\n"
        "    raise SystemExit('unknown mode')\n"
    )
    commissioning_checks = [
        {"aspect": aspect, "json_path": f"checks.{aspect}_valid", "expected_value": True}
        for aspect in (
            "representation",
            "physics_controls",
            "boundaries",
            "diagnostics",
            "numerical_regime",
        )
    ]
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Preregister both scientific sweep points.",
                claim_id="claim_root",
                observable="Two prospectively declared parameter-point summaries.",
                expected_outcomes="Both valid points support; either invalid point challenges.",
                decision_rule="Require valid summaries at both declared parameter points.",
                required_observation="Execute and inspect both s25 and s50 commands.",
                uncertainty_criterion="Both exact validity booleans must be true.",
                inconclusive_conditions="A missing or invalid point is inconclusive.",
                validation_checks=[],
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "sweep.py",
                    "commissioning_argv": ["sweep.py", "commission"],
                    "allowed_scientific_argv": [
                        ["sweep.py", "s25"],
                        ["sweep.py", "s50"],
                    ],
                },
            ),
            _action(
                action="register_claim",
                research_note="Register the common sweep instrument.",
                claim_id="claim_sweep_instrument",
                statement="One source realizes and diagnoses both parameter points.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Both scientific commands require common qualification.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Bind commissioning and both later sweep commands.",
                claim_id="claim_sweep_instrument",
                observable="Machine-readable commissioning summary for the sweep program.",
                expected_outcomes="All five aspects true qualify the shared source.",
                decision_rule="Require every registered commissioning check.",
                required_observation="Run the bound commissioning command once.",
                uncertainty_criterion="All deterministic checks must be exactly true.",
                inconclusive_conditions="Any missing or false check fails qualification.",
                validation_checks=commissioning_checks,
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "sweep.py",
                    "commissioning_argv": ["sweep.py", "commission"],
                    "allowed_scientific_argv": [
                        ["sweep.py", "s25"],
                        ["sweep.py", "s50"],
                        ["sweep.py", "s75"],
                    ],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Commission the immutable multi-point program.",
                path="sweep.py",
                content=program,
                capability="isolated-python",
                argv=["sweep.py", "commission"],
                active_claim_id="claim_sweep_instrument",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the complete commissioning result.",
                claim_id="claim_sweep_instrument",
                path="commission.json",
                note="The shared source passed all five commissioning aspects.",
                observation_sufficient=True,
                observation_note="All prospectively registered checks are true.",
            ),
            _action(
                action="close_claim",
                research_note="Qualify the shared source before either science point.",
                claim_id="claim_sweep_instrument",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The common program passed complete commissioning.",
            ),
            _action(
                action="run_capability",
                research_note=(
                    "Attempt a point qualified by the instrument but absent from "
                    "the scientific contract."
                ),
                capability="isolated-python",
                argv=["sweep.py", "s75"],
                active_claim_id="claim_root",
            ),
            _action(
                action="run_capability",
                research_note="Generate the first preregistered point.",
                capability="isolated-python",
                argv=["sweep.py", "s25"],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the first point under the original contract.",
                claim_id="claim_root",
                path="s25.json",
                note="The first preregistered point completed.",
                observation_sufficient=True,
                observation_note="The s25 point is present and valid.",
                commissioning_claim_id="claim_sweep_instrument",
            ),
            _action(
                action="run_capability",
                research_note="Generate the second preregistered point.",
                capability="isolated-python",
                argv=["sweep.py", "s50"],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the second point under the same contract.",
                claim_id="claim_root",
                path="s50.json",
                note="The second preregistered point completed.",
                observation_sufficient=True,
                observation_note="The s50 point is present and valid.",
                commissioning_claim_id="claim_sweep_instrument",
            ),
            _action(
                action="close_claim",
                research_note="Close from both prospectively declared points.",
                claim_id="claim_root",
                status=ClaimDisposition.SUPPORTED.value,
                reason="Both sweep artifacts satisfied the one active contract.",
            ),
            _action(
                action="finish",
                research_note="Report the multi-point result.",
                final_answer="One prospective contract admitted both declared points.",
            ),
        ]
    )
    output = tmp_path / "command-sweep"
    config = _config(max_iterations=15)
    report = MVPAgentRunner(
        hypothesis="Both preregistered parameter points satisfy the declared response.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    root = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_root"]
    assert root["status"] == "supported"
    assert len(root["evidence_contracts"]) == 1
    assert [item["path"] for item in root["evidence"]] == ["s25.json", "s50.json"]
    assert {item["contract_version"] for item in root["evidence"]} == {1}
    assert not (output / "workspace/s75.json").exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_one_scientific_contract_accepts_a_preregistered_program_pipeline(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    simulation_program = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "checks = {'representation_valid': True, 'physics_controls_valid': True, "
        "'boundaries_valid': True, 'diagnostics_valid': True, "
        "'numerical_regime_valid': True}\n"
        "if sys.argv[1] == 'commission':\n"
        "    Path('simulation_commission.json').write_text(json.dumps({'checks': checks}))\n"
        "elif sys.argv[1] == 'science':\n"
        "    Path('raw.json').write_text(json.dumps({'value': 4}))\n"
        "else:\n"
        "    raise SystemExit('unknown mode')\n"
    )
    analysis_program = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "checks = {'representation_valid': True, 'physics_controls_valid': True, "
        "'boundaries_valid': True, 'diagnostics_valid': True, "
        "'numerical_regime_valid': True}\n"
        "if sys.argv[1] == 'commission':\n"
        "    Path('analysis_commission.json').write_text(json.dumps({'checks': checks}))\n"
        "elif sys.argv[1] == 'science':\n"
        "    raw = json.loads(Path('raw.json').read_text())\n"
        "    Path('final.json').write_text(json.dumps({'checks': {'complete': True}, "
        "'result': 2 * raw['value']}))\n"
        "else:\n"
        "    raise SystemExit('unknown mode')\n"
    )
    commissioning_checks = [
        {"aspect": aspect, "json_path": f"checks.{aspect}_valid", "expected_value": True}
        for aspect in (
            "representation",
            "physics_controls",
            "boundaries",
            "diagnostics",
            "numerical_regime",
        )
    ]
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Preregister the simulation-to-analysis evidence pipeline.",
                claim_id="claim_root",
                observable="A derived JSON result from one simulation and one analyzer.",
                expected_outcomes="A complete result of eight supports the claim.",
                decision_rule="Support exactly when the derived result is complete and eight.",
                required_observation="Run both frozen programs in their declared order.",
                uncertainty_criterion="The deterministic result must be exactly eight.",
                inconclusive_conditions="A missing stage or output is inconclusive.",
                validation_checks=[{"json_path": "checks.complete", "expected_value": True}],
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "simulate.py",
                    "commissioning_argv": ["simulate.py", "commission"],
                    "allowed_scientific_argv": [["simulate.py", "science"]],
                },
                additional_execution_bindings=[
                    {
                        "capability": "isolated-python",
                        "program_path": "analyze.py",
                        "commissioning_argv": ["analyze.py", "commission"],
                        "allowed_scientific_argv": [["analyze.py", "science"]],
                    }
                ],
            ),
            _action(
                action="register_claim",
                research_note="Register the simulation instrument.",
                claim_id="claim_simulator",
                statement="The simulation program realizes the declared experiment.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="The first evidence stage requires complete commissioning.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Bind and qualify the simulation program.",
                claim_id="claim_simulator",
                observable="A complete simulation commissioning JSON summary.",
                expected_outcomes="All five true aspects qualify the simulator.",
                decision_rule="Support only when every commissioning check is true.",
                required_observation="Execute the frozen simulation commissioning command.",
                uncertainty_criterion="All exact checks must be true.",
                inconclusive_conditions="Any missing or false check is inconclusive.",
                validation_checks=commissioning_checks,
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "simulate.py",
                    "commissioning_argv": ["simulate.py", "commission"],
                    "allowed_scientific_argv": [["simulate.py", "science"]],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Commission the frozen simulation source.",
                path="simulate.py",
                content=simulation_program,
                capability="isolated-python",
                argv=["simulate.py", "commission"],
                active_claim_id="claim_simulator",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the complete simulator commissioning summary.",
                claim_id="claim_simulator",
                path="simulation_commission.json",
                note="All simulator aspects passed.",
                observation_sufficient=True,
                observation_note="All five registered checks are true.",
            ),
            _action(
                action="close_claim",
                research_note="Qualify the simulator before scientific execution.",
                claim_id="claim_simulator",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The simulator passed complete commissioning.",
            ),
            _action(
                action="register_claim",
                research_note="Register the derived-analysis instrument.",
                claim_id="claim_analyzer",
                statement="The analysis program derives the contracted result.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="The second evidence stage has an independent source identity.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Bind and qualify the analysis program.",
                claim_id="claim_analyzer",
                observable="A complete analysis commissioning JSON summary.",
                expected_outcomes="All five true aspects qualify the analyzer.",
                decision_rule="Support only when every commissioning check is true.",
                required_observation="Execute the frozen analysis commissioning command.",
                uncertainty_criterion="All exact checks must be true.",
                inconclusive_conditions="Any missing or false check is inconclusive.",
                validation_checks=commissioning_checks,
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "analyze.py",
                    "commissioning_argv": ["analyze.py", "commission"],
                    "allowed_scientific_argv": [["analyze.py", "science"]],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Commission the frozen analysis source.",
                path="analyze.py",
                content=analysis_program,
                capability="isolated-python",
                argv=["analyze.py", "commission"],
                active_claim_id="claim_analyzer",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the complete analyzer commissioning summary.",
                claim_id="claim_analyzer",
                path="analysis_commission.json",
                note="All analyzer aspects passed.",
                observation_sufficient=True,
                observation_note="All five registered checks are true.",
            ),
            _action(
                action="close_claim",
                research_note="Qualify the analyzer before scientific execution.",
                claim_id="claim_analyzer",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The analyzer passed complete commissioning.",
            ),
            _action(
                action="run_capability",
                research_note="Generate the prospectively bound raw simulation output.",
                capability="isolated-python",
                argv=["simulate.py", "science"],
                active_claim_id="claim_root",
            ),
            _action(
                action="run_capability",
                research_note="Generate the prospectively bound derived evidence.",
                capability="isolated-python",
                argv=["analyze.py", "science"],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the final artifact from the declared pipeline.",
                claim_id="claim_root",
                path="final.json",
                note="The separately commissioned analyzer produced the final result.",
                observation_sufficient=True,
                observation_note="Both declared stages completed and the final check is true.",
                commissioning_claim_id="claim_analyzer",
            ),
            _action(
                action="close_claim",
                research_note="Close from the prospectively bound derived artifact.",
                claim_id="claim_root",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The complete frozen pipeline produced the contracted result.",
            ),
            _action(
                action="finish",
                research_note="Report the prospectively governed pipeline result.",
                final_answer="The multi-program evidence pipeline completed prospectively.",
            ),
        ]
    )
    output = tmp_path / "program-pipeline"
    config = _config(max_iterations=18, max_wall_seconds=120)
    report = MVPAgentRunner(
        hypothesis="A simulated value of four yields a derived value of eight.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    root = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_root"]
    contract = root["evidence_contracts"][0]
    assert root["status"] == "supported"
    assert root["evidence"][0]["path"] == "final.json"
    assert (
        contract["execution_binding"]["program_sha256"]
        == hashlib.sha256((output / "workspace/simulate.py").read_bytes()).hexdigest()
    )
    assert (
        contract["additional_execution_bindings"][0]["program_sha256"]
        == hashlib.sha256((output / "workspace/analyze.py").read_bytes()).hexdigest()
    )
    assert json.loads((output / "workspace/final.json").read_text())["result"] == 8


def test_new_contract_version_can_close_same_claim_from_fresh_evidence(
    tmp_path: Path,
) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register the first exact decision rule.",
                claim_id="claim_root",
                observable="A first deterministic JSON value.",
                expected_outcomes="One supports and zero challenges.",
                decision_rule="Support exactly when value is one.",
                required_observation="Produce one complete JSON result.",
                uncertainty_criterion="The exact integer has no sampling uncertainty.",
                inconclusive_conditions="A missing value is inconclusive.",
                validation_checks=[{"json_path": "value", "expected_value": 1}],
            ),
            _action(
                action="run_python",
                research_note="Generate evidence under the first contract.",
                argv=[
                    "-c",
                    "import json; from pathlib import Path; "
                    "Path('first.json').write_text(json.dumps({'value': 1}))",
                ],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the first contracted observation.",
                claim_id="claim_root",
                path="first.json",
                note="The first observation is complete.",
                observation_sufficient=True,
                observation_note="The registered exact value is present.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Attempt an adaptive replacement after evidence.",
                claim_id="claim_root",
                observable="A second deterministic JSON value.",
                expected_outcomes="Two supports and zero challenges.",
                decision_rule="Support exactly when value is two.",
                required_observation="Produce one replacement JSON result.",
                uncertainty_criterion="The exact integer has no sampling uncertainty.",
                inconclusive_conditions="A missing value is inconclusive.",
                validation_checks=[{"json_path": "value", "expected_value": 2}],
            ),
            _action(
                action="run_python",
                research_note="Generate a derived result under the adaptive contract.",
                argv=[
                    "-c",
                    "import json; from pathlib import Path; "
                    "Path('second.json').write_text(json.dumps({'value': 2}))",
                ],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the replacement observation.",
                claim_id="claim_root",
                path="second.json",
                note="The adaptive observation matches its replacement check.",
                observation_sufficient=True,
                observation_note="The replacement exact value is present.",
            ),
            _action(
                action="close_claim",
                research_note="Close under the fresh replacement contract.",
                claim_id="claim_root",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The adaptive result matches the replacement rule.",
                contract_version=2,
            ),
            _action(
                action="finish",
                research_note="Report the prospectively amended result.",
                final_answer="Fresh evidence under contract version two supports the claim.",
            ),
        ]
    )
    output = tmp_path / "adaptive-contract"
    config = _config(max_iterations=10)
    report = MVPAgentRunner(
        hypothesis="A deterministic value supports the registered rule.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    root = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_root"]
    assert tool_rows[6]["tool_result"]["ok"] is True
    assert tool_rows[6]["tool_result"]["result"]["decisive_contract_version"] == 2
    assert root["status"] == "supported"


def test_older_evidence_cannot_close_a_new_contract_version(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register the original prospective rule.",
                claim_id="claim_root",
                observable="A deterministic JSON value.",
                expected_outcomes="One supports and zero challenges.",
                decision_rule="Support exactly when value is one.",
                required_observation="Produce one complete JSON result.",
                uncertainty_criterion="The exact integer has no sampling uncertainty.",
                inconclusive_conditions="A missing value is inconclusive.",
                validation_checks=[{"json_path": "value", "expected_value": 1}],
            ),
            _action(
                action="run_python",
                research_note="Generate evidence under contract version one.",
                argv=[
                    "-c",
                    "import json; from pathlib import Path; "
                    "Path('first.json').write_text(json.dumps({'value': 1}))",
                ],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the version-one observation.",
                claim_id="claim_root",
                path="first.json",
                note="The original observation satisfies version one.",
                observation_sufficient=True,
                observation_note="The registered exact value is present.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Register a second prospective rule.",
                claim_id="claim_root",
                observable="A replacement deterministic JSON value.",
                expected_outcomes="Two supports and zero challenges.",
                decision_rule="Support exactly when value is two.",
                required_observation="Produce one replacement JSON result.",
                uncertainty_criterion="The exact integer has no sampling uncertainty.",
                inconclusive_conditions="A missing value is inconclusive.",
                validation_checks=[{"json_path": "value", "expected_value": 2}],
            ),
            _action(
                action="close_claim",
                research_note="Test whether stale evidence can decide version two.",
                claim_id="claim_root",
                status=ClaimDisposition.SUPPORTED.value,
                reason="This attempt must be rejected because no fresh result exists.",
                contract_version=2,
            ),
            _action(
                action="close_claim",
                research_note="Close non-decisively after the expected rejection.",
                claim_id="claim_root",
                status=ClaimDisposition.UNRESOLVED.value,
                reason="No observation was generated under contract version two.",
            ),
            _action(
                action="finish",
                research_note="Report the bounded unresolved result.",
                final_answer="The amended contract has no fresh evidence.",
            ),
        ]
    )
    output = tmp_path / "stale-contract-evidence"
    config = _config(max_iterations=9)
    report = MVPAgentRunner(
        hypothesis="A deterministic value supports the registered rule.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[4]["tool_result"]["ok"] is False
    assert "contract version 2" in tool_rows[4]["tool_result"]["error"]
    root = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_root"]
    assert root["status"] == "unresolved"


def test_falsified_claim_registers_a_typed_counterexample_repair(
    tmp_path: Path,
) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register the counterexample criterion prospectively.",
                claim_id="claim_root",
                observable="A deterministic counterexample flag.",
                expected_outcomes="True falsifies; false leaves the claim unresolved.",
                decision_rule="Falsify exactly when counterexample is true.",
                required_observation="Produce one complete counterexample record.",
                uncertainty_criterion="The deterministic flag has no sampling uncertainty.",
                inconclusive_conditions="A missing flag is inconclusive.",
                validation_checks=[{"json_path": "counterexample", "expected_value": True}],
            ),
            _action(
                action="run_python",
                research_note="Generate the prospectively declared counterexample.",
                argv=[
                    "-c",
                    "import json; from pathlib import Path; "
                    "Path('counterexample.json').write_text(json.dumps("
                    "{'counterexample': True, 'x': 2}))",
                ],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the qualified counterexample to the root.",
                claim_id="claim_root",
                path="counterexample.json",
                note="The declared domain contains a failing case at x=2.",
                observation_sufficient=True,
                observation_note="The deterministic flag and required case are present.",
            ),
            _action(
                action="close_claim",
                research_note="Falsify the exact root claim under contract version one.",
                claim_id="claim_root",
                status=ClaimDisposition.FALSIFIED.value,
                reason="The qualified x=2 case violates the universal root statement.",
            ),
            _action(
                action="register_claim",
                research_note="Test whether an unchanged statement can masquerade as a repair.",
                claim_id="claim_unchanged",
                statement="The relation holds for every tested x.",
                kind=ClaimKind.SCIENTIFIC.value,
                relation=ClaimRelation.REPAIRS.value,
                parent_id="claim_root",
                rationale="This deliberately leaves the falsified semantics unchanged.",
                repair={
                    "counterexample_paths": ["counterexample.json"],
                    "accommodation": "It does not actually accommodate the x=2 failure.",
                    "semantic_change": "No scientific semantic change was made.",
                    "falsification_condition": "The same x=2 case still falsifies it.",
                },
            ),
            _action(
                action="register_claim",
                research_note="Register the minimal repair that contains the x=2 case.",
                claim_id="claim_repair_one",
                statement="The relation holds for x < 2 and fails at and above x = 2.",
                kind=ClaimKind.SCIENTIFIC.value,
                relation=ClaimRelation.REPAIRS.value,
                parent_id="claim_root",
                rationale=(
                    "The boundary at x=2 is the smallest change suggested by the counterexample."
                ),
                repair={
                    "counterexample_paths": ["counterexample.json"],
                    "accommodation": "The x=2 failure is explicitly outside the holding interval.",
                    "semantic_change": (
                        "Replace the universal domain with the observed x < 2 boundary."
                    ),
                    "falsification_condition": "Any failing case with x < 2 falsifies this repair.",
                },
            ),
        ]
    )
    output = tmp_path / "typed-repair"
    config = _config(max_iterations=6, enforce_repair_loop=True)
    report = MVPAgentRunner(
        hypothesis="The relation holds for every tested x.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    claims = {item["id"]: item for item in report.claim_ledger["claims"]}
    assert claims["claim_root"]["status"] == "falsified"
    assert claims["claim_root"]["decisive_contract_version"] == 1
    repair = claims["claim_repair_one"]
    assert repair["relation"] == "repairs"
    assert repair["repair"]["counterexample_paths"] == ["counterexample.json"]
    assert repair["evidence"] == []
    loop = json.loads((output / "loop_state.json").read_text())
    assert loop["stage"] == "stopped"
    assert loop["cycle"] == 2
    assert report.status == "budget_exhausted"
    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[4]["tool_result"]["ok"] is False
    assert "cannot repeat" in tool_rows[4]["tool_result"]["error"]


def test_independent_judge_can_accept_and_close_a_bounded_claim(
    tmp_path: Path,
) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register a bounded ensemble decision rule.",
                claim_id="claim_root",
                observable="A deterministic ensemble pass flag.",
                expected_outcomes="True supports; false challenges.",
                decision_rule="Support exactly when ensemble_pass is true.",
                required_observation="Evaluate the complete declared ensemble.",
                uncertainty_criterion="Every declared member must pass independently.",
                inconclusive_conditions="Any missing ensemble member is inconclusive.",
                validation_checks=[{"json_path": "ensemble_pass", "expected_value": True}],
            ),
            _action(
                action="run_python",
                research_note="Generate the complete bounded ensemble record.",
                argv=[
                    "-c",
                    "import json; from pathlib import Path; "
                    "Path('ensemble.json').write_text(json.dumps("
                    "{'ensemble_pass': True, 'members': 12}))",
                ],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the complete prospective ensemble.",
                claim_id="claim_root",
                path="ensemble.json",
                note="All twelve prospectively declared members passed.",
                observation_sufficient=True,
                observation_note="All declared members and the exact pass flag are present.",
            ),
            _action(
                action="request_adjudication",
                research_note="Ask an independent judge whether the bounded search is sufficient.",
                claim_id="claim_root",
                contract_version=1,
                case_for_sufficiency=(
                    "The complete twelve-member prospective ensemble passed with no missing runs."
                ),
            ),
            json.dumps(
                {
                    "claim_id": "claim_root",
                    "contract_version": 1,
                    "decision": "sufficient",
                    "scientific_disposition": "supported",
                    "claim_tested": True,
                    "contract_preserves_claim_semantics": True,
                    "rationale": (
                        "The complete prospective ensemble, exact validation, and "
                        "provenance satisfy the bounded contract."
                    ),
                    "evidence_gaps": [],
                    "next_test": None,
                }
            ),
            _action(
                action="finish",
                research_note="Finish after the independent bounded adjudication.",
                final_answer="The declared bounded ensemble supports the root claim.",
            ),
        ]
    )
    output = tmp_path / "accepted-adjudication"
    config = _config(max_iterations=6, enforce_repair_loop=True)
    report = MVPAgentRunner(
        hypothesis="Every member of the declared ensemble satisfies the relation.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    root = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_root"]
    assert report.status == "completed"
    assert root["status"] == "supported"
    assert root["decisive_contract_version"] == 1
    adjudications = json.loads((output / "adjudications.json").read_text())
    assert adjudications[0]["verdict"]["decision"] == "sufficient"
    loop = json.loads((output / "loop_state.json").read_text())
    assert loop["stage"] == "complete"
    assert loop["role"] == "judge"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_adjudication_packet_keeps_failed_and_newest_evidence_with_previews(
    tmp_path: Path,
) -> None:
    output = tmp_path / "balanced-adjudication-packet"
    config = _config(max_tool_output_chars=10_000)
    sandbox = BubblewrapSandbox(output / "workspace", config)
    runner = MVPAgentRunner(
        hypothesis="Every bounded observation passes the declared check.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=sandbox,
        config=config,
    )
    validation_checks = tuple(
        ClaimEvidenceValidationCheck(
            json_path=f"checks.check_{index}",
            expected_value=True,
        )
        for index in range(10)
    )
    runner.claim_store.register_evidence_contract(
        claim_id="claim_root",
        observable="Ten deterministic checks over twelve bounded observations.",
        expected_outcomes="Passing observations support; failures challenge.",
        decision_rule="Judge all prospectively generated observations.",
        required_observation="Twelve observations including failed attempts.",
        uncertainty_criterion="All checks are deterministic booleans.",
        inconclusive_conditions="Missing observations are inconclusive.",
        validation_checks=validation_checks,
        iteration=0,
    )
    for index in range(12):
        values = {f"check_{check}": True for check in range(10)}
        if index == 1:
            values["check_0"] = False
        content = json.dumps({"checks": values})
        path = f"result_{index:02d}.json"
        sandbox.write_file(path, content)
        sufficient = index not in {1, 11}
        runner.claim_store.link_evidence(
            claim_id="claim_root",
            path=path,
            note=f"Bounded observation {index}.",
            observation_sufficient=sufficient,
            observation_note=(
                "All checks passed." if sufficient else "A failed or adverse observation."
            ),
            provenance=ClaimEvidenceProvenance(
                sha256=hashlib.sha256(content.encode()).hexdigest(),
                bytes=len(content.encode()),
                tracked=True,
                generated_iteration=index + 1,
                action="run_python",
                execution_succeeded=index != 1,
                execution_returncode=1 if index == 1 else 0,
                evidence_eligible=True,
            ),
            evidence_document={"checks": values},
            iteration=index + 1,
        )

    packet = runner._adjudication_packet(
        claim_id="claim_root",
        contract_version=1,
        case_for_sufficiency="The bounded record contains all declared observations.",
    )
    selected = packet["selected_contract_evidence"]
    iterations = [item["iteration"] for item in selected]
    preview_by_path = {item["path"]: item for item in packet["artifact_previews"]}

    assert len(selected) == 8
    assert iterations == sorted(iterations)
    assert 2 in iterations  # the early failed observation survives the long tail
    assert 12 in iterations  # the newest non-sufficient observation survives
    assert any(item["observation_sufficient"] is True for item in selected)
    assert packet["selected_contract_evidence_omitted_count"] == 4
    assert packet["selected_contract_evidence_selection_omissions"]["failed"] == 0
    assert "content_excerpt" in preview_by_path["result_01.json"]
    assert "content_excerpt" in preview_by_path["result_11.json"]
    failed = next(item for item in selected if item["iteration"] == 2)
    assert failed["validation_result_count"] == 10
    assert failed["validation_results_omitted_count"] == 2
    assert any(result["passed"] is False for result in failed["validation_results"])
    assert len(failed["validation_results_sha256"]) == 64


def test_insufficient_judgment_rejects_premature_finish(tmp_path: Path) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register a prospective sample criterion.",
                claim_id="claim_root",
                observable="A sample pass flag.",
                expected_outcomes="True is favorable; false challenges.",
                decision_rule="Support only if the declared domain is adequately sampled.",
                required_observation="Cover all three declared regimes.",
                uncertainty_criterion="Replicate every regime independently.",
                inconclusive_conditions="Missing regimes or replicas are inconclusive.",
            ),
            _action(
                action="run_python",
                research_note="Generate a deliberately incomplete sample.",
                argv=[
                    "-c",
                    "import json; from pathlib import Path; "
                    "Path('sample.json').write_text(json.dumps("
                    "{'sample_pass': True, 'regimes': 1}))",
                ],
                active_claim_id="claim_root",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the sample for transparent adjudication.",
                claim_id="claim_root",
                path="sample.json",
                note="Only one of three regimes was sampled.",
                observation_sufficient=True,
                observation_note="The agent proposes that this initial sample is enough.",
            ),
            _action(
                action="request_adjudication",
                research_note="Ask the judge whether one regime is enough.",
                claim_id="claim_root",
                contract_version=1,
                case_for_sufficiency=(
                    "The first sampled regime passed without an observed counterexample."
                ),
            ),
            json.dumps(
                {
                    "claim_id": "claim_root",
                    "contract_version": 1,
                    "decision": "insufficient",
                    "scientific_disposition": None,
                    "claim_tested": True,
                    "contract_preserves_claim_semantics": True,
                    "rationale": (
                        "The registered contract requires three regimes and independent "
                        "replicas, but only one regime is present."
                    ),
                    "evidence_gaps": [
                        "Two declared regimes are missing.",
                        "No independent replicas were supplied.",
                    ],
                    "next_test": "Run replicated observations in the two missing regimes.",
                }
            ),
            _action(
                action="finish",
                research_note="Attempt to finish despite the rejected evidence package.",
                final_answer="No counterexample was found in the one sampled regime.",
            ),
        ]
    )
    output = tmp_path / "rejected-adjudication"
    config = _config(max_iterations=5, enforce_repair_loop=True)
    report = MVPAgentRunner(
        hypothesis="The relation holds throughout three declared regimes.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[-1]["tool_result"]["ok"] is False
    assert "open scientific claims remain" in tool_rows[-1]["tool_result"]["error"]
    root = {item["id"]: item for item in report.claim_ledger["claims"]}["claim_root"]
    assert root["status"] == "open"
    assert report.status == "budget_exhausted"
    judge_system_prompt = client.calls[4]["messages"][0]["content"]
    assert "finite grid samples alone do not support" in judge_system_prompt


def _terminal_record_runner(tmp_path: Path, name: str) -> MVPAgentRunner:
    output = tmp_path / name
    config = _config(enforce_repair_loop=True)
    sandbox = BubblewrapSandbox(output / "workspace", config)
    runner = MVPAgentRunner(
        hypothesis="The declared experiment realizes and tests the bounded prediction.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=sandbox,
        config=config,
    )
    runner.claim_store.register_evidence_contract(
        claim_id="claim_root",
        observable="A scalar outcome from the prospectively attempted experiment.",
        expected_outcomes="One outcome supports while the other falsifies the claim.",
        decision_rule="Apply the frozen threshold to the realized scientific outcome.",
        required_observation="One complete prospective scientific execution attempt.",
        uncertainty_criterion="Report numerical uncertainty around the frozen threshold.",
        inconclusive_conditions="Failure to realize the antecedent is inconclusive.",
        iteration=1,
    )
    failed = '{"execution":"failed before antecedent realization"}'
    sandbox.write_file("failed_attempt.json", failed)
    runner.claim_store.link_evidence(
        claim_id="claim_root",
        path="failed_attempt.json",
        note="The registered scientific test was attempted but not realized.",
        observation_sufficient=False,
        observation_note="This is an attempted test, not a scientific outcome.",
        provenance=ClaimEvidenceProvenance(
            sha256=hashlib.sha256(failed.encode()).hexdigest(),
            bytes=len(failed.encode()),
            tracked=True,
            generated_iteration=2,
            action="run_python",
            command_argv=("-c", "attempt_test()"),
            execution_succeeded=False,
            execution_returncode=1,
            evidence_eligible=True,
        ),
        iteration=2,
    )
    runner.claim_store.register_evidence_contract(
        claim_id="claim_root",
        evidence_purpose=EvidencePurpose.TERMINAL_RECORD,
        observable="A structured record of the bounded experimental blocker.",
        expected_outcomes="The record distinguishes limitation from unresolved science.",
        decision_rule="Classify only the documented terminal status, not the claim.",
        required_observation="One fresh complete record of the failed realization.",
        uncertainty_criterion="State the scientific uncertainty that remains unresolved.",
        inconclusive_conditions="Missing blocker details leave the record incomplete.",
        iteration=3,
    )
    terminal = '{"record_complete":true,"claim_tested":false}'
    sandbox.write_file("terminal_record.json", terminal)
    runner.claim_store.link_evidence(
        claim_id="claim_root",
        path="terminal_record.json",
        note="Fresh terminal record documents why the claim was not tested.",
        observation_sufficient=True,
        observation_note="All prospectively required blocker fields are present.",
        provenance=ClaimEvidenceProvenance(
            sha256=hashlib.sha256(terminal.encode()).hexdigest(),
            bytes=len(terminal.encode()),
            tracked=True,
            generated_iteration=4,
            action="run_python",
            command_argv=("-c", "write_terminal_record()"),
            execution_succeeded=True,
            execution_returncode=0,
            evidence_eligible=True,
        ),
        iteration=4,
    )
    return runner


@pytest.mark.parametrize(
    "disposition",
    [ClaimDisposition.INSTRUMENT_LIMITED, ClaimDisposition.UNRESOLVED],
)
def test_explicit_terminal_adjudication_finishes_without_claim_support(
    tmp_path: Path,
    disposition: ClaimDisposition,
) -> None:
    runner = _terminal_record_runner(tmp_path, disposition.value)
    result = runner._record_adjudication_verdict(
        claim_id="claim_root",
        contract_version=2,
        case_for_sufficiency="The prospective terminal record completely documents the blocker.",
        verdict=MVPJudgeVerdict(
            claim_id="claim_root",
            contract_version=2,
            decision=MVPJudgeDecision.SUFFICIENT,
            scientific_disposition=disposition,
            claim_tested=False,
            contract_preserves_claim_semantics=True,
            rationale=("The terminal record is complete and preserves the untested claim."),
            evidence_gaps=(),
            next_test=None,
        ),
        iteration=5,
        model="test-judge",
        route="isolated",
        request_id="judge-terminal",
    )

    assert result["closure"]["closed"]["status"] == disposition.value
    assert result["closure"]["closed"]["decisive_contract_version"] == 2
    assert runner._finish_gate_error() is None


def test_terminal_record_cannot_be_laundered_into_support(tmp_path: Path) -> None:
    runner = _terminal_record_runner(tmp_path, "reject-terminal-support")

    with pytest.raises(ValueError, match="cannot support or falsify"):
        runner._record_adjudication_verdict(
            claim_id="claim_root",
            contract_version=2,
            case_for_sufficiency="The terminal record documents only the failed realization.",
            verdict=MVPJudgeVerdict(
                claim_id="claim_root",
                contract_version=2,
                decision=MVPJudgeDecision.SUFFICIENT,
                scientific_disposition=ClaimDisposition.SUPPORTED,
                claim_tested=True,
                contract_preserves_claim_semantics=True,
                rationale=(
                    "This deliberately invalid verdict attempts to convert a blocker "
                    "record into scientific support."
                ),
                evidence_gaps=(),
                next_test=None,
            ),
            iteration=5,
            model="test-judge",
            route="isolated",
            request_id="judge-invalid",
        )

    assert runner.claim_store.ledger.by_id()["claim_root"].status == ClaimDisposition.OPEN
    assert not runner.adjudications_path.exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_interface_only_commissioning_cannot_unlock_scientific_execution(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register the scientific decision rule prospectively.",
                claim_id="claim_root",
                observable="A capability-generated scientific response summary.",
                expected_outcomes="A positive response supports; a negative response falsifies.",
                decision_rule="Support when a fully commissioned response is positive.",
                required_observation="Use a complete run from a qualified capability.",
                uncertainty_criterion="The response must be separated from zero.",
                inconclusive_conditions="Incomplete commissioning is inconclusive.",
            ),
            _action(
                action="register_claim",
                research_note="Register an intentionally shallow instrument claim.",
                claim_id="claim_interface_only",
                statement="The capability API imports and can write a JSON file.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Test that interface availability alone cannot qualify science.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Register only an API availability assertion.",
                claim_id="claim_interface_only",
                observable="A JSON report of API availability.",
                expected_outcomes="True reports an available interface; false reports failure.",
                decision_rule="Support this narrow claim when api_available is true.",
                required_observation="Import and invoke the isolated capability once.",
                uncertainty_criterion="Use an exact deterministic boolean.",
                inconclusive_conditions="Missing output leaves interface availability unresolved.",
                validation_checks=[
                    {
                        "aspect": "interface",
                        "json_path": "checks.api_available",
                        "expected_value": True,
                    }
                ],
            ),
            _action(
                action="author_and_run_capability",
                research_note="Exercise only the capability interface.",
                path="api_probe.py",
                content=(
                    "import json\n"
                    "from pathlib import Path\n"
                    "Path('api_probe.json').write_text("
                    "json.dumps({'checks': {'api_available': True}}))\n"
                ),
                capability="isolated-python",
                argv=["api_probe.py"],
                active_claim_id="claim_interface_only",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the passing but interface-only probe.",
                claim_id="claim_interface_only",
                path="api_probe.json",
                note="The isolated API was available.",
                observation_sufficient=True,
                observation_note="The registered interface assertion passed.",
            ),
            _action(
                action="close_claim",
                research_note="Support only the narrow interface claim.",
                claim_id="claim_interface_only",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The exact API availability assertion passed.",
            ),
            _action(
                action="author_and_run_capability",
                research_note="Attempt science after interface-only commissioning.",
                path="blocked_science.py",
                content=(
                    "from pathlib import Path\n"
                    "Path('blocked_science.json').write_text('{\"response\": 1}')\n"
                ),
                capability="isolated-python",
                argv=["blocked_science.py"],
                active_claim_id="claim_root",
            ),
            _action(
                action="finish",
                research_note="Finish after verifying that shallow commissioning is blocked.",
                final_answer="Interface availability did not commission the experiment.",
            ),
        ]
    )
    output = tmp_path / "interface-only-commissioning"
    config = _config(max_iterations=12)
    report = MVPAgentRunner(
        hypothesis="The commissioned capability produces a positive response.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert tool_rows[6]["tool_result"]["ok"] is False
    assert (
        "representation, physics_controls, boundaries, diagnostics, and "
        "numerical_regime" in tool_rows[6]["tool_result"]["error"]
    )
    assert not (output / "workspace/blocked_science.py").exists()
    assert not (output / "workspace/blocked_science.json").exists()
    claims = {item["id"]: item for item in report.claim_ledger["claims"]}
    assert claims["claim_interface_only"]["status"] == "supported"
    assert claims["claim_root"]["status"] == "open"


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_supported_interface_stage_forces_next_sibling_to_complete_commissioning(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_claim",
                research_note="Register the single interface-discovery stage.",
                claim_id="claim_interface_stage",
                statement="The isolated capability interface can emit a JSON artifact.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="Discover the capability interface before physical commissioning.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Commit the interface discovery predicate.",
                claim_id="claim_interface_stage",
                observable="A JSON boolean reporting interface availability.",
                expected_outcomes="True supports interface availability; false rejects it.",
                decision_rule="Support only when checks.interface_ok is exactly true.",
                required_observation="Execute one isolated interface probe.",
                uncertainty_criterion="The deterministic boolean has no sampling error.",
                inconclusive_conditions="Missing JSON leaves the interface unresolved.",
                validation_checks=[
                    {
                        "aspect": "interface",
                        "json_path": "checks.interface_ok",
                        "expected_value": True,
                    }
                ],
            ),
            _action(
                action="author_and_run_capability",
                research_note="Run the contracted interface discovery.",
                path="first_interface.py",
                content=(
                    "import json\n"
                    "from pathlib import Path\n"
                    "Path('first_interface.json').write_text("
                    "json.dumps({'checks': {'interface_ok': True}}))\n"
                ),
                capability="isolated-python",
                argv=["first_interface.py"],
                active_claim_id="claim_interface_stage",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Link the passing interface artifact.",
                claim_id="claim_interface_stage",
                path="first_interface.json",
                note="The interface probe passed its exact check.",
                observation_sufficient=True,
                observation_note="The registered interface boolean is exactly true.",
            ),
            _action(
                action="close_claim",
                research_note="Close the completed interface stage.",
                claim_id="claim_interface_stage",
                status=ClaimDisposition.SUPPORTED.value,
                reason="The prospective interface check passed.",
            ),
            _action(
                action="register_claim",
                research_note="Register a later instrument sibling.",
                claim_id="claim_physical_stage",
                statement="The capability is commissioned for the intended physical test.",
                kind=ClaimKind.INSTRUMENT.value,
                relation=ClaimRelation.INSTRUMENT_OF.value,
                parent_id="claim_root",
                rationale="The next stage must transition from interface to physics.",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Attempt to fragment interface discovery into another sibling.",
                claim_id="claim_physical_stage",
                observable="Another JSON interface availability boolean.",
                expected_outcomes="True would report another available interface.",
                decision_rule="Treat checks.second_interface_ok=true as passing.",
                required_observation="Execute a second interface-only probe.",
                uncertainty_criterion="The deterministic boolean has no sampling error.",
                inconclusive_conditions="Missing JSON leaves the probe unresolved.",
                validation_checks=[
                    {
                        "aspect": "interface",
                        "json_path": "checks.second_interface_ok",
                        "expected_value": True,
                    }
                ],
            ),
            _action(
                action="author_and_run_capability",
                research_note="Attempt the forbidden second interface-only stage.",
                path="second_interface.py",
                content=(
                    "from pathlib import Path\nPath('second_interface.json').write_text('{}')\n"
                ),
                capability="isolated-python",
                argv=["second_interface.py"],
                active_claim_id="claim_physical_stage",
            ),
            _action(
                action="register_evidence_contract",
                research_note="Replace the fragmented probe with complete commissioning.",
                claim_id="claim_physical_stage",
                observable="A JSON summary covering all physical commissioning aspects.",
                expected_outcomes="Five true booleans qualify the complete physical stage.",
                decision_rule="Proceed only when every physical aspect is exactly true.",
                required_observation=(
                    "Exercise representation, boundaries, diagnostics, and numerics."
                ),
                uncertainty_criterion="Each deterministic predicate must be exactly true.",
                inconclusive_conditions="Any false or missing predicate is inconclusive.",
                validation_checks=[
                    {
                        "aspect": "representation",
                        "json_path": "checks.representation_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "physics_controls",
                        "json_path": "checks.physics_controls_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "boundaries",
                        "json_path": "checks.boundaries_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "diagnostics",
                        "json_path": "checks.diagnostics_valid",
                        "expected_value": True,
                    },
                    {
                        "aspect": "numerical_regime",
                        "json_path": "checks.numerical_regime_valid",
                        "expected_value": True,
                    },
                ],
                execution_binding={
                    "capability": "isolated-python",
                    "program_path": "physical_anchor.py",
                    "commissioning_argv": ["physical_anchor.py"],
                    "allowed_scientific_argv": [["physical_anchor.py", "science"]],
                },
            ),
            _action(
                action="author_and_run_capability",
                research_note="Execute the permitted complete physical commissioning stage.",
                path="physical_anchor.py",
                content=(
                    "import json\n"
                    "from pathlib import Path\n"
                    "Path('physical_anchor.json').write_text(json.dumps({'checks': {"
                    "'representation_valid': True, 'physics_controls_valid': True, "
                    "'boundaries_valid': True, "
                    "'diagnostics_valid': True, 'numerical_regime_valid': True}}))\n"
                ),
                capability="isolated-python",
                argv=["physical_anchor.py"],
                active_claim_id="claim_physical_stage",
            ),
            _action(
                action="finish",
                research_note="Finish after verifying interface-stage convergence.",
                final_answer="The second interface stage was blocked; complete commissioning ran.",
            ),
        ]
    )
    output = tmp_path / "interface-stage-convergence"
    config = _config(max_iterations=14)
    report = MVPAgentRunner(
        hypothesis="Interface discovery must converge into physical commissioning.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    tool_rows = [
        json.loads(json.loads(line)["content"])
        for line in (output / "transcript.jsonl").read_text().splitlines()
        if json.loads(line)["kind"] == "tool"
    ]
    assert report.status == "completed"
    assert tool_rows[7]["tool_result"]["ok"] is False
    assert "supported interface discovery already exists" in tool_rows[7]["tool_result"]["error"]
    assert not (output / "workspace/second_interface.py").exists()
    assert not (output / "workspace/second_interface.json").exists()
    assert tool_rows[9]["tool_result"]["ok"] is True
    assert (output / "workspace/physical_anchor.py").exists()
    assert (output / "workspace/physical_anchor.json").exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_atomic_capability_rejects_unknown_claim_before_write_or_execution(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    client = ScriptedCompletionClient(
        [
            _action(
                action="author_and_run_capability",
                research_note="Attempt a bound capability action with an unknown claim.",
                path="should_not_exist.py",
                content=("from pathlib import Path\nPath('executed.txt').write_text('bad')\n"),
                capability="isolated-python",
                argv=["should_not_exist.py"],
                active_claim_id="claim_missing",
            ),
            _action(
                action="finish",
                research_note="Finish after the preflight rejection.",
                final_answer="The invalid claim prevented capability side effects.",
            ),
        ]
    )
    output = tmp_path / "invalid-claim-capability"
    config = _config()
    report = MVPAgentRunner(
        hypothesis="Invalid claim bindings prevent capability side effects.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
    ).run()

    assert report.status == "completed"
    first_tool = json.loads(
        [
            json.loads(line)
            for line in (output / "transcript.jsonl").read_text().splitlines()
            if json.loads(line)["kind"] == "tool"
        ][0]["content"]
    )
    assert first_tool["tool_result"]["ok"] is False
    assert "unknown active_claim_id" in first_tool["tool_result"]["error"]
    assert not (output / "workspace/should_not_exist.py").exists()
    assert not (output / "workspace/executed.txt").exists()


def test_atomic_capability_action_must_execute_authored_path() -> None:
    with pytest.raises(ValueError, match=r"argv\[0\] to equal path"):
        MVPAgentRunner._parse_action(
            _action(
                action="author_and_run_capability",
                research_note="Attempt to execute a different program.",
                path="authored.py",
                content="print('authored')\n",
                capability="instrument",
                argv=["different.py"],
                active_claim_id="claim_instrument",
            )
        )


def test_capability_action_requires_active_claim_id() -> None:
    with pytest.raises(ValueError, match="active_claim_id"):
        MVPAgentRunner._parse_action(
            _action(
                action="run_capability",
                research_note="Attempt an unbound capability execution.",
                capability="instrument",
                argv=["probe.py"],
            )
        )


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_capability_preserves_sandbox_isolation_and_read_only_runtime(
    tmp_path: Path,
) -> None:
    _skills, capabilities = _write_test_skill_and_capability(tmp_path)
    host_secret = tmp_path / "outside-secret.txt"
    host_secret.write_text("not visible")
    sandbox = BubblewrapSandbox(tmp_path / "capability-workspace", _config(), capabilities)
    code = (
        "import json, os, socket\n"
        "from pathlib import Path\n"
        "network = 'unexpected'\n"
        "try:\n"
        "    socket.create_connection(('1.1.1.1', 53), timeout=0.2)\n"
        "except OSError:\n"
        "    network = 'blocked'\n"
        "runtime_writable = True\n"
        "try:\n"
        "    Path('/opt/acs-capabilities/isolated-python/acs-write-test').write_text('bad')\n"
        "except OSError:\n"
        "    runtime_writable = False\n"
        "print(json.dumps({\n"
        f"  'host_secret_exists': Path({str(host_secret)!r}).exists(),\n"
        "  'credential_present': os.getenv('CP_API_KEY') is not None,\n"
        "  'home_exists': Path('/home').exists(),\n"
        "  'network': network,\n"
        "  'runtime_writable': runtime_writable,\n"
        "}))\n"
    )
    result = sandbox.run_capability("isolated-python", ("-c", code))
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "host_secret_exists": False,
        "credential_present": False,
        "home_exists": False,
        "network": "blocked",
        "runtime_writable": False,
    }


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_sandbox_bounds_output_timeout_and_workspace(tmp_path: Path) -> None:
    output_config = _config(max_tool_output_chars=100)
    output_sandbox = BubblewrapSandbox(tmp_path / "output", output_config)
    output = output_sandbox.run_python(("-c", "print('x' * 10000)"))
    assert output.returncode == 0
    assert output.stdout_truncated
    assert "sandbox output truncated" in output.stdout

    timeout_config = _config(
        max_command_seconds=0.2,
        command_heartbeat_seconds=0.05,
    )
    timeout_sandbox = BubblewrapSandbox(tmp_path / "timeout", timeout_config)
    heartbeats: list[dict[str, Any]] = []
    timeout = timeout_sandbox.run_python(
        ("-c", "while True: pass"),
        progress_callback=heartbeats.append,
    )
    assert timeout.timed_out
    assert timeout.returncode is None
    assert timeout.heartbeat_count >= 1
    assert len(heartbeats) == timeout.heartbeat_count
    assert heartbeats[-1]["elapsed_wall_seconds"] > 0

    workspace_config = _config(
        max_workspace_bytes=20_000,
        max_file_bytes=10_000,
    )
    workspace_sandbox = BubblewrapSandbox(tmp_path / "workspace", workspace_config)
    workspace = workspace_sandbox.run_python(
        (
            "-c",
            "from pathlib import Path\n"
            "for i in range(4): Path(f'chunk-{i}').write_bytes(b'x' * 8000)\n",
        )
    )
    assert workspace.workspace_exceeded


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_cancelled_action_writes_terminal_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = ScriptedCompletionClient(
        [
            _action(
                action="run_python",
                research_note="Run a calculation that the operator will cancel.",
                argv=["experiment.py"],
            )
        ]
    )
    output = tmp_path / "cancelled"
    config = _config()
    sandbox = BubblewrapSandbox(output / "workspace", config)

    def cancel(*_args: Any, **_kwargs: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(sandbox, "run_python", cancel)
    report = MVPAgentRunner(
        hypothesis="A deliberately cancelled calculation has no scientific result.",
        output_directory=output,
        completion_client=client,
        sandbox=sandbox,
        config=config,
    ).run()

    assert report.status == "cancelled"
    assert (output / "mvp_report.json").is_file()
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    assert transcript[-1]["kind"] == "control"
    assert transcript[-1]["event"] == "campaign_cancelled"


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / ".runtime/warpx-cpu/bin/python").is_file(),
    reason="the optional WarpX runtime is unavailable",
)
def test_builtin_warpx_skill_executes_smoke_inside_sandbox(tmp_path: Path) -> None:
    skills, capabilities = discover_builtin_mvp_resources(Path(__file__).resolve().parents[1])
    assert "warpx" in skills
    assert "warpx-cpu-26.07" in capabilities
    interface = skills.read(
        "warpx",
        "references/picmi-interface.md",
        max_chars=100_000,
    )["content"]
    diagnostics = skills.read(
        "warpx",
        "references/diagnostics.md",
        max_chars=100_000,
    )["content"]
    time_integration = skills.read(
        "warpx",
        "references/time-integration.md",
        max_chars=100_000,
    )["content"]
    assert "Cartesian1DGrid` uses `z`" in interface
    assert "positions through `z`" in interface
    assert "velocities through `uz`" in interface
    assert "take proper velocity, `gamma*v`" in interface
    assert "never multiply it\nby particle mass" in interface
    assert "provide explicit expressions for all three magnetic" in interface
    assert "`Ex_expression`, `Ey_expression`, `Ez_expression`" in interface
    assert "**no** `.iteration` attribute" in diagnostics
    assert "`warpx_momentum_spread_expressions`" in interface
    assert "disappearing from the realized native\ninput" in interface
    assert "series.flush()" in diagnostics
    assert "Do not close the series before `flush()`" in diagnostics
    assert 'warpx_format="openpmd"' in diagnostics
    assert 'warpx_openpmd_backend="h5"' in diagnostics
    assert 'generic keyword `format="openpmd"` is rejected' in diagnostics
    assert "Reduced energy accounting" in diagnostics
    assert "field[:, 2] + particle[:, 2]" in diagnostics
    assert "decline in field energy alone" in diagnostics
    assert "identical step/time coordinates" in diagnostics
    assert "boundary\nflux/work/source terms" in diagnostics
    assert "`picmi.ThetaImplicitEMEvolveScheme" in time_integration
    assert "`picmi.SemiImplicitEMEvolveScheme" in time_integration
    assert "c*dt*sqrt(sum_i(1/dx_i**2)) < 1" in time_integration
    assert "does not remove accuracy restrictions" in time_integration
    assert "Require nonlinear\nconvergence" in time_integration
    commissioning_2d = skills.read(
        "warpx",
        "references/2d-xz-commissioning.md",
        max_chars=100_000,
    )["content"]
    assert "vectors as `[x, z]`" in commissioning_2d
    assert "`AnalyticInitialField` initializes grid fields" in commissioning_2d
    assert "`AnalyticAppliedField` configure external fields" in commissioning_2d
    assert "checks.interior" in commissioning_2d
    assert "field assigned a periodic boundary has matching values" in commissioning_2d
    assert "cannot\n  be made periodic merely by moving" in commissioning_2d
    assert "MLMG projection rejects `open` field" in commissioning_2d
    assert "does not expose\n  a `do_initial_div_cleaning` keyword" in commissioning_2d
    assert "Evaluate `curl(B)/mu0`" in commissioning_2d
    assert "`physics_controls` validation check" in commissioning_2d
    assert "initial seed perturbation as continuing drive" in commissioning_2d
    assert "multiplying by `1e6`" in commissioning_2d
    assert "reject it\n  if `abs(v) >= c`" in commissioning_2d
    assert "convert its energy\n  `k_B*T` to eV" in commissioning_2d
    example = skills.read(
        "warpx",
        "examples/minimal_smoke.py",
        max_chars=100_000,
    )["content"]
    config = _config(max_command_seconds=30)
    sandbox = BubblewrapSandbox(tmp_path / "warpx", config, capabilities)
    sandbox.write_file("minimal_smoke.py", example)
    result = sandbox.run_capability("warpx-cpu-26.07", ("minimal_smoke.py",))
    assert result.returncode == 0, result.stderr
    observed = json.loads((tmp_path / "warpx/capability_smoke.json").read_text())
    implicit_example = skills.read(
        "warpx",
        "examples/implicit_em_smoke.py",
        max_chars=100_000,
    )["content"]
    implicit_sandbox = BubblewrapSandbox(tmp_path / "warpx-implicit", config, capabilities)
    implicit_sandbox.write_file("implicit_em_smoke.py", implicit_example)
    implicit_result = implicit_sandbox.run_capability("warpx-cpu-26.07", ("implicit_em_smoke.py",))
    assert implicit_result.returncode == 0, implicit_result.stderr
    implicit_observed = json.loads(
        (tmp_path / "warpx-implicit/implicit_capability_smoke.json").read_text()
    )
    assert implicit_observed == {
        "checks": {
            "completed": True,
            "theta_implicit_native": True,
            "picard_native": True,
            "convergence_required_native": True,
            "scientific_evidence_eligible": False,
        }
    }
    openpmd_example = skills.read(
        "warpx",
        "examples/openpmd_field_smoke.py",
        max_chars=100_000,
    )["content"]
    openpmd_sandbox = BubblewrapSandbox(tmp_path / "warpx-openpmd", config, capabilities)
    openpmd_sandbox.write_file("openpmd_field_smoke.py", openpmd_example)
    openpmd_result = openpmd_sandbox.run_capability("warpx-cpu-26.07", ("openpmd_field_smoke.py",))
    assert openpmd_result.returncode == 0, openpmd_result.stderr
    openpmd_observed = json.loads(
        (tmp_path / "warpx-openpmd/openpmd_capability_smoke.json").read_text()
    )
    assert openpmd_observed == {
        "checks": {
            "completed": True,
            "openpmd_format_native": True,
            "h5_backend_native": True,
            "h5_file_nonempty": True,
            "iteration_readable": True,
            "mesh_records_readable": True,
            "scientific_evidence_eligible": False,
        }
    }
    assert observed == {"checks": {"completed": True, "scientific_evidence_eligible": False}}


def test_builtin_scientific_markdown_skill_preserves_machine_readable_evidence() -> None:
    skills, _capabilities = discover_builtin_mvp_resources(Path(__file__).resolve().parents[1])
    assert "scientific-markdown" in skills
    content = skills.read("scientific-markdown", None, max_chars=20_000)["content"]
    assert "$R = \\mu_1/\\mu_{20}$" in content
    assert "never wrap that JSON object in a Markdown" in content
    assert "validation_checks" in content
    assert "never replaces exact JSON evidence metadata" in MVPAgentRunner.SYSTEM_PROMPT


def test_builtin_python_experiment_skill_separates_plain_python_from_capabilities() -> None:
    skills, _capabilities = discover_builtin_mvp_resources(Path(__file__).resolve().parents[1])
    assert "python-experiment" in skills
    content = skills.read("python-experiment", None, max_chars=20_000)["content"]
    assert "There is no generic capability named `python`" in content
    assert "omit `execution_binding`" in content
    assert "normally omit `aspect`" in content
    assert "only fresh evidence produced under that version" in content
    assert "records contract compliance" in content
    assert "python-experiment skill is available" in MVPAgentRunner.SYSTEM_PROMPT
    assert "it is not a self-issued" in MVPAgentRunner.SYSTEM_PROMPT


def test_builtin_warpx_skill_has_no_demo_science() -> None:
    skill_root = Path(__file__).resolve().parents[1] / "skills" / "warpx"
    text = "\n".join(
        path.read_text(errors="replace")
        for path in sorted(skill_root.rglob("*"))
        if path.is_file() and path.suffix in {".md", ".py", ".sh", ".yaml", ".json"}
    )
    forbidden = (
        "GEM",
        "Sweet-Parker",
        "Sweet–Parker",
        "reconnection",
        "Harris",
        "Z-pinch",
        "zpinch",
        "magnetic mirror",
        "loss cone",
        "radiation reaction",
        "Lundquist",
        "delta_SP",
        "mass-ratio",
    )
    for phrase in forbidden:
        assert phrase.casefold() not in text.casefold()
    assert "demos/" not in text


def test_builtin_flash_skill_has_no_campaign_science_or_flash_distribution() -> None:
    project_root = Path(__file__).resolve().parents[1]
    skill_root = project_root / "skills" / "flash-mhd"
    text = "\n".join(
        path.read_text(errors="replace")
        for path in sorted(skill_root.rglob("*"))
        if path.is_file() and path.suffix in {".md", ".py", ".sh", ".yaml", ".json"}
    )
    forbidden = (
        "GEM",
        "Sweet-Parker",
        "Sweet–Parker",
        "Harris",
        "Z-pinch",
        "zpinch",
        "Lundquist",
        "delta_SP",
        "island coalescence",
        "plasmoid threshold",
    )
    for phrase in forbidden:
        assert phrase.casefold() not in text.casefold()
    assert "demos/" not in text
    assert not any(path.suffix.casefold() in {".f", ".f90"} for path in skill_root.rglob("*"))
    assert not any(
        path.name == "flash4"
        for path in project_root.rglob("*")
        if ".runtime" not in path.parts
    )


def test_flash_guided_commission_is_self_contained_and_nonevidentiary() -> None:
    project_root = Path(__file__).resolve().parents[1]
    package = MVPGuidedCommissioningPackage.read(
        project_root
        / "demos/resistive_mhd_island_coalescence/guided_commission.json"
    )
    descriptor = package.descriptor()

    assert package.spec.capability == "flash-island-coalescence-resistive-mhd-4.8"
    assert descriptor["scientific_evidence_eligible"] is False
    assert all(record.bytes > 0 for record in package.file_records)
    assert not any("anchor_run" in record.path for record in package.file_records)
    package.assert_identity()

    anchor = json.loads(
        package.read_file("guided/anchor_validation.json").decode()
    )
    operator = json.loads(
        package.read_file("guided/operator_validation.json").decode()
    )
    assert anchor["scientific_status"] == "permanently_non_evidentiary"
    assert anchor["checks"]["scientific_evidence_eligible"] is False
    assert operator["scientific_status"] == "permanently_non_evidentiary"
    assert operator["checks"]["scientific_evidence_eligible"] is False


@pytest.mark.skipif(
    not (
        Path(__file__).resolve().parents[1]
        / ".runtime/flash-island-coalescence-resistive-mhd-4.8/bin/flash4"
    ).is_file(),
    reason="the operator-supplied FLASH runtime is unavailable",
)
def test_builtin_flash_skill_executes_neutral_smoke_inside_sandbox(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    skills, capabilities = discover_builtin_mvp_resources(project_root)
    capability = "flash-island-coalescence-resistive-mhd-4.8"
    assert "flash-mhd" in skills
    assert capability in capabilities
    assert "compiled simulation unit" in skills.read(
        "flash-mhd",
        "references/execution-output.md",
        max_chars=30_000,
    )["content"]
    example = skills.read(
        "flash-mhd",
        "examples/runtime_smoke.py",
        max_chars=100_000,
    )["content"]
    config = _config(
        max_command_seconds=120,
        max_workspace_bytes=128 * 1024 * 1024,
        max_file_bytes=64 * 1024 * 1024,
        max_memory_bytes=4 * 1024 * 1024 * 1024,
    )
    sandbox = BubblewrapSandbox(tmp_path / "flash-smoke", config, capabilities)
    sandbox.write_file("runtime_smoke.py", example)
    result = sandbox.run_capability(capability, ("runtime_smoke.py",))
    assert result.returncode == 0, result.stderr
    observed = json.loads(
        (tmp_path / "flash-smoke/flash_mhd_capability_smoke.json").read_text()
    )
    assert observed["scientific_status"] == "permanently_non_evidentiary"
    assert observed["checks"]["completed"] is True
    assert observed["checks"]["hdf5_output_readable"] is True
    assert observed["return_code"] == 0


@pytest.mark.skipif(
    not (
        (Path(__file__).resolve().parents[1] / ".runtime/warpx-cuda-openpmd/bin/python").is_file()
        and Path("/dev/dxg").exists()
    ),
    reason="the optional WSL CUDA/openPMD runtime is unavailable",
)
def test_builtin_warpx_cuda_openpmd_executes_inside_sandbox(
    tmp_path: Path,
) -> None:
    skills, capabilities = discover_builtin_mvp_resources(Path(__file__).resolve().parents[1])
    assert "warpx-cuda-openpmd-26.07" in capabilities
    descriptor = next(
        item for item in capabilities.descriptors() if item["name"] == "warpx-cuda-openpmd-26.07"
    )
    assert descriptor["executable_kind"] == "python-picmi-cuda-openpmd"
    example = skills.read(
        "warpx",
        "examples/openpmd_field_smoke.py",
        max_chars=100_000,
    )["content"]
    config = _config(
        max_command_seconds=60,
        max_workspace_bytes=64 * 1024 * 1024,
        max_file_bytes=16 * 1024 * 1024,
        max_memory_bytes=16 * 1024 * 1024 * 1024,
    )
    sandbox = BubblewrapSandbox(tmp_path / "warpx-cuda", config, capabilities)
    sandbox.write_file("openpmd_field_smoke.py", example)
    probe = sandbox.run_capability(
        "warpx-cuda-openpmd-26.07",
        (
            "-c",
            "import json, pathlib, amrex.space2d as a; "
            "print(json.dumps({'gpu': bool(a.Config.have_gpu), "
            "'backend': str(a.Config.gpu_backend), "
            "'dxg': pathlib.Path('/dev/dxg').exists()}))",
        ),
    )
    assert probe.returncode == 0, probe.stderr
    assert json.loads(probe.stdout) == {
        "gpu": True,
        "backend": "CUDA",
        "dxg": True,
    }
    result = sandbox.run_capability("warpx-cuda-openpmd-26.07", ("openpmd_field_smoke.py",))
    assert result.returncode == 0, result.stderr
    observed = json.loads((tmp_path / "warpx-cuda/openpmd_capability_smoke.json").read_text())
    assert all(observed["checks"].values()) is False
    assert observed["checks"] == {
        "completed": True,
        "openpmd_format_native": True,
        "h5_backend_native": True,
        "h5_file_nonempty": True,
        "iteration_readable": True,
        "mesh_records_readable": True,
        "scientific_evidence_eligible": False,
    }


def test_mvp_cli_accepts_natural_language_hypothesis_and_instruction() -> None:
    args = build_parser().parse_args(
        [
            "mvp",
            "--hypothesis",
            "A charged particle's magnetic moment is conserved when the field varies slowly.",
            "--instruction",
            "Use the installed WarpX capability.",
        ]
    )
    assert args.command == "mvp"
    assert not hasattr(args, "tool_config")
    assert args.instruction == "Use the installed WarpX capability."
    assert args.max_iterations is None


def test_mvp_cli_accepts_guided_commission_manifest() -> None:
    args = build_parser().parse_args(
        [
            "mvp",
            "--hypothesis",
            "A bounded hypothesis.",
            "--guided-commission",
            "guided_commission.json",
        ]
    )
    assert args.guided_commission == "guided_commission.json"


def test_optional_guided_protocol_preserves_legacy_package_identity(
    tmp_path: Path,
) -> None:
    package_root = tmp_path / "legacy-guided"
    (package_root / "guided").mkdir(parents=True)
    files = {
        "guided/experiment.py": b"print('legacy anchor')\n",
        "guided/validation.json": b'{"checks":{"ran":true}}\n',
    }
    for relative, content in files.items():
        (package_root / relative).write_bytes(content)
    payload = {
        "schema_version": "0.1.0",
        "name": "legacy-anchor",
        "description": "A manifest created before protocol_path was available.",
        "capability": "isolated-python",
        "program_path": "guided/experiment.py",
        "validated_argv": ["guided/experiment.py"],
        "validation_summary_path": "guided/validation.json",
        "operator_validation": "The exact command exited zero.",
        "limitations": [],
        "files": list(files),
    }
    manifest = package_root / "guided_commission.json"
    manifest.write_text(json.dumps(payload, indent=2) + "\n")

    expected = hashlib.sha256()
    encoded_spec = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    expected.update(len(encoded_spec).to_bytes(8, "big"))
    expected.update(encoded_spec)
    for relative in sorted(files):
        name = relative.encode()
        content = files[relative]
        expected.update(len(name).to_bytes(8, "big"))
        expected.update(name)
        expected.update(len(content).to_bytes(8, "big"))
        expected.update(content)

    package = MVPGuidedCommissioningPackage.read(manifest)
    assert package.package_sha256 == expected.hexdigest()
    assert "protocol_path" not in package.descriptor()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_guided_commission_is_pinned_hashed_and_initially_nonevidentiary(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    package = MVPGuidedCommissioningPackage.read(_write_guided_commissioning(tmp_path))
    client = ScriptedCompletionClient(
        [
            _action(
                action="register_evidence_contract",
                research_note="Register before trying to reuse the supplied output.",
                claim_id="claim_root",
                observable="A fresh campaign observation.",
                expected_outcomes="The fresh observation either supports or challenges the root.",
                decision_rule="Require a freshly generated sufficient artifact.",
                required_observation="A post-contract execution artifact.",
                uncertainty_criterion="Do not reuse an operator prerun as an observation.",
                inconclusive_conditions="No fresh execution is inconclusive.",
            ),
            _action(
                action="link_claim_evidence",
                research_note="Confirm that the supplied validation cannot be promoted directly.",
                claim_id="claim_root",
                path="guided/validation.json",
                note="This was supplied by the operator before the campaign.",
                observation_sufficient=True,
                observation_note="It should be rejected as sufficient.",
            ),
            _action(
                action="run_capability",
                research_note="Exercise the handed-over command in workbench first.",
                capability="isolated-python",
                argv=["guided/experiment.py"],
                stage="workbench",
            ),
            _action(
                action="finish",
                research_note="Stop after exercising the guided-input boundary.",
                final_answer="The guided program is available, but its old output is not evidence.",
            ),
        ]
    )
    output = tmp_path / "guided-run"
    config = _config(max_iterations=4)
    report = MVPAgentRunner(
        hypothesis="A guided starting point still requires fresh evidence.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
        guided_commissioning=package,
    ).run()

    assert report.status == "completed"
    assert report.guided_commissioning["package_sha256"] == package.package_sha256
    assert report.guided_commissioning["scientific_evidence_eligible"] is False
    initial = json.loads(client.calls[0]["messages"][1]["content"])
    assert initial["guided_commissioning"]["available"] is True
    assert initial["guided_commissioning"]["validated_argv"] == ["guided/experiment.py"]
    assert initial["guided_commissioning"]["protocol_path"] == "guided/protocol.json"
    sticky = json.loads(client.calls[-1]["messages"][-1]["content"])
    assert sticky["guided_commissioning"]["package_sha256"] == package.package_sha256
    provenance = json.loads((output / "artifact_provenance.json").read_text())
    record = provenance["artifacts"]["guided/validation.json"]
    assert record["action"] == "run_capability"
    assert record["execution_stage"] == "workbench"
    assert record["evidence_eligible"] is False
    transcript = [
        json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()
    ]
    failed_link = [item for item in transcript if item["kind"] == "tool"][1]
    assert json.loads(failed_link["content"])["tool_result"]["ok"] is False
    assert "fresh evidence-stage artifact" in failed_link["content"]
    snapshot = output / "guided_commissioning_input/guided/experiment.py"
    assert snapshot.read_bytes() == package.read_file("guided/experiment.py")


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_guided_commission_resume_does_not_overwrite_agent_revision(
    tmp_path: Path,
) -> None:
    skills, capabilities = _write_test_skill_and_capability(tmp_path)
    package = MVPGuidedCommissioningPackage.read(_write_guided_commissioning(tmp_path))
    output = tmp_path / "guided-resume"
    config = _config()
    first = MVPAgentRunner(
        hypothesis="A guided program may be revised after installation.",
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
        guided_commissioning=package,
    )
    first._initialize()
    revised = "print('agent revision')\n"
    first.sandbox.write_file("guided/experiment.py", revised)

    resumed = MVPAgentRunner(
        hypothesis=first.hypothesis,
        output_directory=output,
        completion_client=ScriptedCompletionClient([]),
        sandbox=BubblewrapSandbox(output / "workspace", config, capabilities),
        config=config,
        skills=skills,
        capabilities=capabilities,
        guided_commissioning=package,
    )
    resumed._initialize()
    assert (output / "workspace/guided/experiment.py").read_text() == revised
    assert (
        output / "guided_commissioning_input/guided/experiment.py"
    ).read_bytes() == package.read_file("guided/experiment.py")


def test_guided_commission_rejects_traversal_and_changed_identity(
    tmp_path: Path,
) -> None:
    manifest = _write_guided_commissioning(tmp_path)
    package = MVPGuidedCommissioningPackage.read(manifest)
    (manifest.parent / "guided/experiment.py").write_text("print('changed')\n")
    with pytest.raises(ValueError, match="identity changed"):
        package.assert_identity()

    payload = json.loads(manifest.read_text())
    payload["files"][0] = "../outside.py"
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="workspace-relative"):
        MVPGuidedCommissioningPackage.read(manifest)

    manifest = _write_guided_commissioning(tmp_path / "missing-protocol")
    payload = json.loads(manifest.read_text())
    payload["files"].remove(payload["protocol_path"])
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="protocol_path must be listed"):
        MVPGuidedCommissioningPackage.read(manifest)
