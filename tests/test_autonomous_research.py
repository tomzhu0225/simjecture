from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from conjecture_solver.adapters.base import CostEstimate, ValidationReport
from conjecture_solver.adapters.fake import DeterministicKineticAdapter
from conjecture_solver.autonomous_research import (
    CandidateResult,
    InjectedResearchCrash,
    NoveltyStatus,
    ObservablePrediction,
    ProposedToolCall,
    ResearchBudget,
    ResearchCampaignReport,
    ResearchConclusion,
    ResearchCrashPoint,
    ResearchDecision,
    ResearchDecisionKind,
    ResearchDecisionRejected,
    ResearchDisposition,
    ResearchEvidencePolicy,
    ResearchEvidenceStage,
    ResearchHypothesis,
    ResearchProblemContract,
    ResearchPropositionClass,
    ResearchResultClass,
    ResearchToolKind,
    ResearchToolManifest,
    ResearchToolRegistry,
    ResearchToolResult,
    UniversalResearchRunner,
)
from conjecture_solver.campaign import planted_campaign_problem
from conjecture_solver.cli import build_parser
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.llm import CompletionResult, ModelRoute
from conjecture_solver.models import EvidenceRole, HypothesisOrigin
from conjecture_solver.research_tools import (
    SimulatorAdapterResearchTool,
    SubprocessResearchTool,
    SubprocessResearchToolConfig,
)


def observation_id(decision_id: str) -> str:
    canonical = json.dumps(decision_id, sort_keys=True, separators=(",", ":"))
    return f"observation_{hashlib.sha256(canonical.encode()).hexdigest()[:20]}"


def root_hypothesis() -> ResearchHypothesis:
    return ResearchHypothesis(
        id="hypothesis_root_scaling",
        statement="The normalized outcome follows one power law over the declared domain.",
        machine_predicate="observable_rate = coefficient * control_parameter ** exponent",
        formal_specification={
            "form": "power_law",
            "dependent": "observable_rate",
            "independent": "control_parameter",
        },
        proposition_class=ResearchPropositionClass.SCALING_LAW,
        model_family="test_model",
        scope="bounded deterministic test domain",
        coordinates=("control_parameter",),
        observables=("observable_rate",),
        origin=HypothesisOrigin.HUMAN,
    )


def contract(**budget_updates: int | float) -> ResearchProblemContract:
    budget = {
        "maximum_iterations": 4,
        "maximum_tool_calls": 3,
        "maximum_compute_units": 5.0,
        "maximum_wall_seconds": 50.0,
        "maximum_storage_bytes": 5000,
        **budget_updates,
    }
    return ResearchProblemContract(
        id="contract_universal_test",
        question="What law best describes the declared observable?",
        significance="Tests that the model, rather than a fixed DAG, chooses the path.",
        root_hypotheses=(root_hypothesis(),),
        allowed_result_classes=(
            ResearchResultClass.SCALING_LAW,
            ResearchResultClass.BOUNDED_NULL,
        ),
        allowed_model_families=("test_model",),
        allowed_tools=("deterministic.measure",),
        forbidden_shortcuts=("Do not inspect held-out results before preregistration.",),
        budget=ResearchBudget(**budget),
        evidence_policy=ResearchEvidencePolicy(
            minimum_independent_confirmations=1,
            require_deliberate_falsification=True,
        ),
    )


class ScriptedCompletionClient:
    def __init__(self, decisions: list[ResearchDecision]) -> None:
        self.decisions = decisions
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int | None = 1024,
        temperature: float = 0.0,
    ) -> CompletionResult:
        del escalation_reason
        self.calls.append(
            {
                "messages": messages,
                "route": route,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        decision = self.decisions.pop(0)
        return CompletionResult(
            request_id=f"scripted_{len(self.calls)}",
            model="unbounded-test-model",
            content=decision.model_dump_json(),
            finish_reason="stop",
            usage={"total_tokens": 10},
            route=route,
            route_reason="test route",
        )


class DeterministicResearchTool:
    manifest = ResearchToolManifest(
        name="deterministic.measure",
        version="1.0",
        description="Deterministic generic measurement tool used by kernel tests",
        kind=ResearchToolKind.SIMULATOR,
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "number"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"observable_rate": {"type": "number"}},
        },
        supported_model_families=("test_model",),
        supported_coordinates=("control_parameter",),
        supported_observables=("observable_rate",),
    )

    def __init__(self) -> None:
        self.calls = 0
        self.keys: list[str] = []

    def validate(self, arguments: dict[str, object]) -> ValidationReport:
        valid = isinstance(arguments.get("value"), (int, float))
        return ValidationReport(
            valid=valid,
            errors=() if valid else ("value must be numeric",),
        )

    def estimate_cost(self, arguments: dict[str, object]) -> CostEstimate:
        del arguments
        return CostEstimate(compute_units=1.0, wall_seconds=2.0, storage_bytes=100)

    def execute(
        self,
        arguments: dict[str, object],
        *,
        idempotency_key: str,
    ) -> ResearchToolResult:
        self.calls += 1
        self.keys.append(idempotency_key)
        return ResearchToolResult(
            completed=True,
            observables={"observable_rate": float(arguments["value"])},
            diagnostics={"independent_check": "passed"},
            validity_checks={"finite": True, "instrument_qualified": True},
            artifact_hashes=(hashlib.sha256(idempotency_key.encode()).hexdigest(),),
            cost=self.estimate_cost(arguments),
            scientific_scope="deterministic test model",
        )


class DeterministicLiteratureTool(DeterministicResearchTool):
    manifest = DeterministicResearchTool.manifest.model_copy(
        update={
            "name": "deterministic.literature",
            "description": "Deterministic literature reconnaissance used by kernel tests",
            "kind": ResearchToolKind.LITERATURE_SEARCH,
        }
    )


def tool_decision(
    iteration: int,
    *,
    stage: ResearchEvidenceStage,
    group: str,
    value: float = 2.0,
    tool_name: str = "deterministic.measure",
) -> ResearchDecision:
    return ResearchDecision(
        id=f"decision_{iteration}_{stage.value}",
        iteration=iteration,
        kind=ResearchDecisionKind.USE_TOOL,
        rationale="Choose a quantitative destructive measurement from the capability manifest.",
        tool_call=ProposedToolCall(
            tool_name=tool_name,
            arguments={"value": value},
            purpose="Challenge the active scaling on a preregistered point.",
            evidence_stage=stage,
            evidence_role=(
                EvidenceRole.CONFIRMATION
                if stage
                in {
                    ResearchEvidenceStage.CONFIRMATION,
                    ResearchEvidenceStage.FALSIFICATION,
                }
                else EvidenceRole.DISCOVERY
            ),
            independence_group=group,
            predictions=(
                ObservablePrediction(
                    hypothesis_id="hypothesis_root_scaling",
                    observable="observable_rate",
                    condition="At the declared point the rate lies in the frozen interval.",
                    minimum=1.9,
                    maximum=2.1,
                ),
            ),
            falsification_condition="A rate outside [1.9, 2.1] falsifies this point prediction.",
        ),
    )


def conclude_decision(*supporting_decisions: ResearchDecision) -> ResearchDecision:
    evidence = tuple(observation_id(item.id) for item in supporting_decisions)
    candidate = CandidateResult(
        id="candidate_scaling_v1",
        hypothesis_id="hypothesis_root_scaling",
        result_class=ResearchResultClass.SCALING_LAW,
        statement="The candidate scaling survived the declared destructive held-out test.",
        formal_specification={"form": "power_law", "exponent": -0.5},
        scope="deterministic test model only",
        supporting_evidence_ids=evidence,
        limitations=("This kernel test is not a physical discovery.",),
        novelty_status=NoveltyStatus.UNASSESSED,
    )
    return ResearchDecision(
        id="decision_conclude",
        iteration=len(supporting_decisions),
        kind=ResearchDecisionKind.CONCLUDE,
        rationale="Stop only after independent destructive confirmation.",
        conclusion=ResearchConclusion(
            disposition=ResearchDisposition.VALIDATED_WITHIN_TOOLS,
            reason="All frozen confirmation predictions passed valid tool executions.",
            evidence_ids=evidence,
            candidate=candidate,
        ),
    )


def test_model_owns_iterative_path_and_replay_has_no_side_effects(tmp_path: Path) -> None:
    explore = tool_decision(
        0,
        stage=ResearchEvidenceStage.EXPLORATION,
        group="exploration_seed",
    )
    falsify = tool_decision(
        1,
        stage=ResearchEvidenceStage.FALSIFICATION,
        group="heldout_seed",
    )
    provider = ScriptedCompletionClient([explore, falsify, conclude_decision(explore, falsify)])
    tool = DeterministicResearchTool()
    ledger_path = tmp_path / "research.sqlite3"
    with SQLiteEventLedger(ledger_path) as ledger:
        runner = UniversalResearchRunner(
            campaign_id="campaign_universal",
            ledger=ledger,
            contract=contract(),
            completion_client=provider,
            tools=ResearchToolRegistry((tool,)),
        )
        report = runner.run()
        events = ledger.load("campaign_universal")

        assert report.conclusion.disposition is ResearchDisposition.VALIDATED_WITHIN_TOOLS
        assert report.consumed_tool_calls == 2
        assert not report.budget_overrun
        assert all(item.evidence_eligible for item in report.observations)
        assert all(all(item.prediction_checks.values()) for item in report.observations)
        assert tool.calls == 2
        assert len(provider.calls) == 3
        assert all(item["max_tokens"] is None for item in provider.calls)
        assert ledger.verify_chain("campaign_universal")

        replay_provider = ScriptedCompletionClient([])
        replay_tool = DeterministicResearchTool()
        replay = UniversalResearchRunner(
            campaign_id="campaign_universal",
            ledger=ledger,
            contract=contract(),
            completion_client=replay_provider,
            tools=ResearchToolRegistry((replay_tool,)),
        ).run()
        assert replay == report
        assert ledger.load("campaign_universal") == events
        assert replay_provider.calls == []
        assert replay_tool.calls == 0

        path = report.write(tmp_path / "package")
        assert ResearchCampaignReport.read_verified(path) == report


def test_universal_kernel_requires_search_attempt_only_when_tool_is_allowed(
    tmp_path: Path,
) -> None:
    literature = DeterministicLiteratureTool()
    simulator = DeterministicResearchTool()
    startup_search = tool_decision(
        0,
        stage=ResearchEvidenceStage.EXPLORATION,
        group="startup_reconnaissance",
        tool_name=literature.manifest.name,
    )
    simulation = tool_decision(
        1,
        stage=ResearchEvidenceStage.EXPLORATION,
        group="post_search_simulation",
    )
    base = contract(maximum_iterations=2, maximum_tool_calls=2)
    grounded = base.model_copy(
        update={
            "allowed_tools": (
                literature.manifest.name,
                simulator.manifest.name,
            )
        }
    )
    provider = ScriptedCompletionClient(
        [
            simulation.model_copy(update={"iteration": 0}),
            startup_search,
            simulation,
        ]
    )

    with SQLiteEventLedger(tmp_path / "literature-gate.sqlite3") as ledger:
        report = UniversalResearchRunner(
            campaign_id="campaign_literature_gate",
            ledger=ledger,
            contract=grounded,
            completion_client=provider,
            tools=ResearchToolRegistry((literature, simulator)),
        ).run()

    assert report.consumed_tool_calls == 2
    assert report.conclusion.disposition is ResearchDisposition.BUDGET_EXHAUSTED
    assert report.observations[0].tool_name == literature.manifest.name
    assert literature.calls == 1
    assert simulator.calls == 1
    assert len(provider.calls) == 3


@pytest.mark.parametrize(
    "crash_at",
    (
        ResearchCrashPoint.AFTER_DECISION_COMMITTED,
        ResearchCrashPoint.AFTER_TOOL_RECEIPT,
        ResearchCrashPoint.AFTER_OBSERVATION_COMMITTED,
        ResearchCrashPoint.AFTER_REPORT_COMMITTED,
    ),
)
def test_crash_recovery_reuses_decisions_receipts_and_results(
    tmp_path: Path,
    crash_at: ResearchCrashPoint,
) -> None:
    explore = tool_decision(
        0,
        stage=ResearchEvidenceStage.EXPLORATION,
        group="exploration_seed",
    )
    falsify = tool_decision(
        1,
        stage=ResearchEvidenceStage.FALSIFICATION,
        group="heldout_seed",
    )
    decisions = [explore, falsify, conclude_decision(explore, falsify)]
    first_provider = ScriptedCompletionClient(list(decisions))
    first_tool = DeterministicResearchTool()
    ledger_path = tmp_path / f"{crash_at.value}.sqlite3"
    with SQLiteEventLedger(ledger_path) as ledger:
        with pytest.raises(InjectedResearchCrash):
            UniversalResearchRunner(
                campaign_id="campaign_recovery",
                ledger=ledger,
                contract=contract(),
                completion_client=first_provider,
                tools=ResearchToolRegistry((first_tool,)),
                crash_at=crash_at,
            ).run()

        committed_decisions = len(
            [
                event
                for event in ledger.load("campaign_recovery")
                if event.event_type == "research_decision_committed"
            ]
        )
        remaining = decisions[committed_decisions:]
        resumed_provider = ScriptedCompletionClient(remaining)
        resumed_tool = DeterministicResearchTool()
        report = UniversalResearchRunner(
            campaign_id="campaign_recovery",
            ledger=ledger,
            contract=contract(),
            completion_client=resumed_provider,
            tools=ResearchToolRegistry((resumed_tool,)),
        ).run()

        assert report.conclusion.disposition is ResearchDisposition.VALIDATED_WITHIN_TOOLS
        assert report.consumed_tool_calls == 2
        assert first_tool.calls + resumed_tool.calls == 2
        assert ledger.verify_chain("campaign_recovery")


def test_invalid_model_decision_is_repaired_without_a_token_ceiling(tmp_path: Path) -> None:
    invalid = tool_decision(
        0,
        stage=ResearchEvidenceStage.EXPLORATION,
        group="bad",
        tool_name="invented.tool",
    )
    valid = ResearchDecision(
        id="bounded_null",
        iteration=0,
        kind=ResearchDecisionKind.CONCLUDE,
        rationale="Stop honestly when the proposed route is outside available capabilities.",
        conclusion=ResearchConclusion(
            disposition=ResearchDisposition.BOUNDED_NULL,
            reason="No admissible experiment was selected within this test attempt.",
        ),
    )
    provider = ScriptedCompletionClient([invalid, valid])
    with SQLiteEventLedger(tmp_path / "repair.sqlite3") as ledger:
        report = UniversalResearchRunner(
            campaign_id="campaign_repair",
            ledger=ledger,
            contract=contract(),
            completion_client=provider,
            tools=ResearchToolRegistry((DeterministicResearchTool(),)),
        ).run()
    assert report.conclusion.disposition is ResearchDisposition.BOUNDED_NULL
    assert len(provider.calls) == 2
    assert all(item["max_tokens"] is None for item in provider.calls)


def test_iteration_budget_produces_deterministic_stop(tmp_path: Path) -> None:
    explore = tool_decision(
        0,
        stage=ResearchEvidenceStage.EXPLORATION,
        group="only_allowed_action",
    )
    provider = ScriptedCompletionClient([explore])
    with SQLiteEventLedger(tmp_path / "budget.sqlite3") as ledger:
        report = UniversalResearchRunner(
            campaign_id="campaign_budget",
            ledger=ledger,
            contract=contract(maximum_iterations=1),
            completion_client=provider,
            tools=ResearchToolRegistry((DeterministicResearchTool(),)),
        ).run()
    assert report.conclusion.disposition is ResearchDisposition.BUDGET_EXHAUSTED
    assert report.consumed_tool_calls == 1


def test_validated_result_without_falsification_is_rejected(tmp_path: Path) -> None:
    confirmation = tool_decision(
        0,
        stage=ResearchEvidenceStage.CONFIRMATION,
        group="confirmation_without_challenge",
    )
    invalid_conclusion = conclude_decision(confirmation)
    provider = ScriptedCompletionClient(
        [confirmation, invalid_conclusion, invalid_conclusion, invalid_conclusion]
    )
    with (
        SQLiteEventLedger(tmp_path / "no_falsification.sqlite3") as ledger,
        pytest.raises(ResearchDecisionRejected, match="falsification"),
    ):
        UniversalResearchRunner(
            campaign_id="campaign_no_falsification",
            ledger=ledger,
            contract=contract(),
            completion_client=provider,
            tools=ResearchToolRegistry((DeterministicResearchTool(),)),
        ).run()


def test_candidate_must_be_bound_to_its_preregistered_confirmation(tmp_path: Path) -> None:
    explore = tool_decision(
        0,
        stage=ResearchEvidenceStage.EXPLORATION,
        group="candidate_discovery",
    )
    falsify = tool_decision(
        1,
        stage=ResearchEvidenceStage.FALSIFICATION,
        group="root_challenge",
    )
    alternative = root_hypothesis().model_copy(
        update={
            "id": "hypothesis_unconfirmed_alternative",
            "statement": "An unconfirmed alternative law describes the same domain.",
            "origin": HypothesisOrigin.AI,
            "parent_ids": ("hypothesis_root_scaling",),
        }
    )
    valid_shape = conclude_decision(explore, falsify)
    assert valid_shape.conclusion is not None
    assert valid_shape.conclusion.candidate is not None
    unbound_candidate = valid_shape.conclusion.candidate.model_copy(
        update={"hypothesis_id": alternative.id}
    )
    invalid = valid_shape.model_copy(
        update={
            "new_hypotheses": (alternative,),
            "conclusion": valid_shape.conclusion.model_copy(
                update={"candidate": unbound_candidate}
            ),
        }
    )
    provider = ScriptedCompletionClient([explore, falsify, invalid, invalid, invalid])
    with (
        SQLiteEventLedger(tmp_path / "unbound_candidate.sqlite3") as ledger,
        pytest.raises(ResearchDecisionRejected, match="not preregistered"),
    ):
        UniversalResearchRunner(
            campaign_id="campaign_unbound_candidate",
            ledger=ledger,
            contract=contract(),
            completion_client=provider,
            tools=ResearchToolRegistry((DeterministicResearchTool(),)),
        ).run()


def test_any_simulator_adapter_can_be_exposed_without_a_domain_workflow() -> None:
    adapter = DeterministicKineticAdapter()
    tool = SimulatorAdapterResearchTool(
        adapter,
        name="generic-kinetic-oracle",
        supported_observables=(
            "maxwellian_growth_rate",
            "two_stream_growth_rate",
            "moments_match",
            "hypothesis_falsified",
        ),
    )
    _, experiment = planted_campaign_problem()
    arguments = {"experiment": experiment.model_dump(mode="json")}

    assert tool.validate(arguments).valid
    result = tool.execute(arguments, idempotency_key="generic-adapter-test")

    assert result.completed
    assert result.validity_checks == {
        "adapter_admission": True,
        "job_completed": True,
    }
    assert result.observables["hypothesis_falsified"] is True
    assert adapter.submitted_job_count == 1
    replay = tool.execute(arguments, idempotency_key="generic-adapter-test")
    assert replay == result
    assert adapter.submitted_job_count == 1


def test_subprocess_tool_is_schema_checked_and_never_uses_a_shell(tmp_path: Path) -> None:
    script = tmp_path / "tool.py"
    script.write_text(
        """import json, sys
request = json.load(sys.stdin)
value = float(request[\"arguments\"][\"value\"])
print(json.dumps({
    \"completed\": True,
    \"observables\": {\"observable_rate\": value},
    \"diagnostics\": {\"received_idempotency_key\": request[\"idempotency_key\"]},
    \"validity_checks\": {\"finite\": True},
    \"artifact_hashes\": [],
    \"cost\": {\"compute_units\": 0.1, \"wall_seconds\": 0.1, \"storage_bytes\": 1},
    \"scientific_scope\": \"subprocess tool test\",
    \"failure_detail\": None
}))
"""
    )
    config = SubprocessResearchToolConfig(
        manifest=DeterministicResearchTool.manifest,
        command=(sys.executable, str(script)),
        timeout_seconds=5.0,
        estimated_cost=CostEstimate(
            compute_units=0.1,
            wall_seconds=1.0,
            storage_bytes=1,
        ),
    )
    tool = SubprocessResearchTool(config)

    assert not tool.validate({"value": 2.0, "invented": True}).valid
    result = tool.execute({"value": 2.0}, idempotency_key="subprocess-key")
    assert result.observables == {"observable_rate": 2.0}
    assert result.diagnostics["received_idempotency_key"] == "subprocess-key"


def test_public_research_command_has_tools_and_no_token_ceiling() -> None:
    args = build_parser().parse_args(
        [
            "research",
            "problem.json",
            "--tool-config",
            "kinetic-tool.json",
        ]
    )
    assert args.contract == "problem.json"
    assert args.tool_config == ["kinetic-tool.json"]
    assert not hasattr(args, "max_tokens")
