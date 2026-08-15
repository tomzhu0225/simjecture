"""Domain-neutral, verifier-governed autonomous research loop.

The model owns the scientific path.  Infrastructure owns immutable history,
tool admission, preregistration, budgets, evidence eligibility, and stopping.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import Field, model_validator

from .adapters.base import CostEstimate, ValidationReport
from .control import CampaignControl
from .ledger import SQLiteEventLedger, StoredEvent
from .llm import ModelRoute
from .models import EvidenceRole, HypothesisOrigin, StrictModel, utc_now
from .outbox import ExternalOperation, ExternalOutbox, create_intent


def _canonical_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class ResearchResultClass(StrEnum):
    COUNTEREXAMPLE = "counterexample"
    SCALING_LAW = "scaling_law"
    PHASE_BOUNDARY = "phase_boundary"
    CLOSURE = "closure"
    IMPOSSIBILITY = "impossibility"
    BOUNDED_NULL = "bounded_null"


class ResearchPropositionClass(StrEnum):
    CONTRIBUTION = "contribution"
    SUFFICIENCY = "sufficiency"
    INVARIANCE = "invariance"
    THRESHOLD = "threshold"
    PATH_DEPENDENCE = "path_dependence"
    SCALING_LAW = "scaling_law"
    PHASE_BOUNDARY = "phase_boundary"
    CLOSURE = "closure"
    AUXILIARY_VALIDITY = "auxiliary_validity"


class ResearchRelationKind(StrEnum):
    SPECIALIZES = "specializes"
    PREDICTED_BY = "predicted_by"
    TESTS = "tests"
    ALTERNATIVE_TO = "alternative_to"
    REPAIRS = "repairs"
    AUXILIARY_TO = "auxiliary_to"
    REQUIRES = "requires"
    INCOMPATIBLE_WITH = "incompatible_with"


class ResearchToolKind(StrEnum):
    SIMULATOR = "simulator"
    ANALYSIS = "analysis"
    VERIFIER = "verifier"
    LITERATURE_SEARCH = "literature_search"


class ResearchEvidenceStage(StrEnum):
    EXPLORATION = "exploration"
    QUALIFICATION = "qualification"
    CONFIRMATION = "confirmation"
    FALSIFICATION = "falsification"


class ResearchDecisionKind(StrEnum):
    USE_TOOL = "use_tool"
    CONCLUDE = "conclude"


class ResearchDisposition(StrEnum):
    VALIDATED_WITHIN_TOOLS = "validated_within_tools"
    BOUNDED_NULL = "bounded_null"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    BUDGET_EXHAUSTED = "budget_exhausted"


class NoveltyStatus(StrEnum):
    UNASSESSED = "unassessed"
    KNOWN_RESULT = "known_result"
    CANDIDATE_NEW = "candidate_new"
    VERIFIED_NEW = "verified_new"


class ResearchHypothesis(StrictModel):
    """Open scientific proposition whose details are authored during the run."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    machine_predicate: str = Field(min_length=1)
    formal_specification: dict[str, Any]
    proposition_class: ResearchPropositionClass
    model_family: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    coordinates: tuple[str, ...] = Field(min_length=1)
    observables: tuple[str, ...] = Field(min_length=1)
    assumptions: tuple[str, ...] = ()
    origin: HypothesisOrigin
    parent_ids: tuple[str, ...] = ()
    motivating_evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def declarative_and_unique(self) -> ResearchHypothesis:
        if self.statement.endswith("?"):
            raise ValueError("a research hypothesis must be declarative")
        if len(self.coordinates) != len(set(self.coordinates)):
            raise ValueError("hypothesis coordinates must be unique")
        if len(self.observables) != len(set(self.observables)):
            raise ValueError("hypothesis observables must be unique")
        return self


class ResearchRelation(StrictModel):
    source_hypothesis_id: str
    target_hypothesis_id: str
    kind: ResearchRelationKind
    evidence_rule: str = Field(min_length=1)
    justification: str = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_nodes(self) -> ResearchRelation:
        if self.source_hypothesis_id == self.target_hypothesis_id:
            raise ValueError("a hypothesis relation must connect distinct nodes")
        return self


class ResearchBudget(StrictModel):
    maximum_iterations: int = Field(ge=1)
    maximum_tool_calls: int = Field(ge=0)
    maximum_compute_units: float = Field(gt=0)
    maximum_wall_seconds: float = Field(gt=0)
    maximum_storage_bytes: int = Field(gt=0)


class ResearchEvidencePolicy(StrictModel):
    preregistration_required: Literal[True] = True
    require_numerical_validity: Literal[True] = True
    minimum_independent_confirmations: int = Field(default=1, ge=1)
    require_deliberate_falsification: bool = True
    allow_bounded_null: bool = True


class ResearchProblemContract(StrictModel):
    """Human direction and constitution, without a prescribed research path."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    significance: str = Field(min_length=1)
    root_hypotheses: tuple[ResearchHypothesis, ...] = Field(min_length=1)
    allowed_result_classes: tuple[ResearchResultClass, ...] = Field(min_length=1)
    allowed_model_families: tuple[str, ...] = Field(min_length=1)
    allowed_tools: tuple[str, ...] = Field(min_length=1)
    forbidden_shortcuts: tuple[str, ...] = ()
    scientific_constraints: tuple[str, ...] = ()
    budget: ResearchBudget
    evidence_policy: ResearchEvidencePolicy = Field(default_factory=ResearchEvidencePolicy)
    maximum_invalid_decisions_per_iteration: int = Field(default=3, ge=1, le=10)

    @model_validator(mode="after")
    def coherent_contract(self) -> ResearchProblemContract:
        ids = [item.id for item in self.root_hypotheses]
        if len(ids) != len(set(ids)):
            raise ValueError("root hypothesis IDs must be unique")
        if len(self.allowed_tools) != len(set(self.allowed_tools)):
            raise ValueError("allowed tools must be unique")
        if any(
            item.model_family not in self.allowed_model_families
            for item in self.root_hypotheses
        ):
            raise ValueError("every root hypothesis must use an allowed model family")
        return self

    @property
    def contract_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


class ResearchToolManifest(StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    kind: ResearchToolKind
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    supported_model_families: tuple[str, ...] = Field(min_length=1)
    supported_coordinates: tuple[str, ...] = ()
    supported_observables: tuple[str, ...] = ()
    idempotent: Literal[True] = True


class ObservablePrediction(StrictModel):
    hypothesis_id: str = Field(min_length=1)
    observable: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    minimum: float | None = None
    maximum: float | None = None
    exact: bool | str | None = None

    @model_validator(mode="after")
    def one_testable_predicate(self) -> ObservablePrediction:
        has_interval = self.minimum is not None or self.maximum is not None
        if has_interval == (self.exact is not None):
            raise ValueError("prediction requires either a numeric interval or exact value")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("prediction minimum cannot exceed maximum")
        return self


class ProposedToolCall(StrictModel):
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any]
    purpose: str = Field(min_length=1)
    evidence_stage: ResearchEvidenceStage
    evidence_role: EvidenceRole
    independence_group: str = Field(min_length=1)
    predictions: tuple[ObservablePrediction, ...] = Field(min_length=1)
    falsification_condition: str = Field(min_length=1)


class CandidateResult(StrictModel):
    id: str = Field(min_length=1)
    hypothesis_id: str = Field(min_length=1)
    result_class: ResearchResultClass
    statement: str = Field(min_length=1)
    formal_specification: dict[str, Any]
    scope: str = Field(min_length=1)
    supporting_evidence_ids: tuple[str, ...] = Field(min_length=1)
    contradicting_evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = Field(min_length=1)
    novelty_status: NoveltyStatus = NoveltyStatus.UNASSESSED


class ResearchConclusion(StrictModel):
    disposition: ResearchDisposition
    reason: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    candidate: CandidateResult | None = None

    @model_validator(mode="after")
    def candidate_matches_disposition(self) -> ResearchConclusion:
        if self.disposition is ResearchDisposition.VALIDATED_WITHIN_TOOLS:
            if self.candidate is None:
                raise ValueError("a validated result requires a candidate")
        elif self.candidate is not None:
            raise ValueError("only a validated result may carry a candidate")
        return self


class ResearchDecision(StrictModel):
    """One model-authored transition, committed before any tool execution."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    iteration: int = Field(ge=0)
    kind: ResearchDecisionKind
    rationale: str = Field(min_length=1)
    new_hypotheses: tuple[ResearchHypothesis, ...] = ()
    new_relations: tuple[ResearchRelation, ...] = ()
    tool_call: ProposedToolCall | None = None
    conclusion: ResearchConclusion | None = None

    @model_validator(mode="after")
    def exactly_one_transition(self) -> ResearchDecision:
        if self.kind is ResearchDecisionKind.USE_TOOL:
            if self.tool_call is None or self.conclusion is not None:
                raise ValueError("use_tool decision requires only a tool call")
        elif self.conclusion is None or self.tool_call is not None:
            raise ValueError("conclude decision requires only a conclusion")
        ids = [item.id for item in self.new_hypotheses]
        if len(ids) != len(set(ids)):
            raise ValueError("new hypothesis IDs must be unique within a decision")
        return self


class ResearchToolResult(StrictModel):
    completed: bool
    observables: dict[str, float | bool | str] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    validity_checks: dict[str, bool] = Field(default_factory=dict)
    artifact_hashes: tuple[str, ...] = ()
    cost: CostEstimate
    scientific_scope: str = Field(min_length=1)
    failure_detail: str | None = None

    @model_validator(mode="after")
    def coherent_completion(self) -> ResearchToolResult:
        if self.completed and self.failure_detail is not None:
            raise ValueError("completed tool result cannot carry a failure")
        if not self.completed and not self.failure_detail:
            raise ValueError("incomplete tool result requires a failure detail")
        return self


class ResearchObservation(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    iteration: int = Field(ge=0)
    decision_id: str
    tool_name: str
    evidence_stage: ResearchEvidenceStage
    evidence_role: EvidenceRole
    independence_group: str
    hypothesis_ids: tuple[str, ...] = Field(min_length=1)
    preregistered_predictions: tuple[ObservablePrediction, ...] = Field(min_length=1)
    prediction_checks: dict[str, bool]
    result: ResearchToolResult
    evidence_eligible: bool

    @model_validator(mode="after")
    def eligibility_is_derived(self) -> ResearchObservation:
        expected = (
            self.result.completed
            and bool(self.result.validity_checks)
            and all(self.result.validity_checks.values())
        )
        if self.evidence_eligible != expected:
            raise ValueError("observation eligibility must follow tool validity checks")
        return self


class ResearchCampaignReport(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    package_kind: Literal["universal_research_campaign"] = "universal_research_campaign"
    campaign_id: str
    contract: ResearchProblemContract
    hypotheses: tuple[ResearchHypothesis, ...]
    relations: tuple[ResearchRelation, ...]
    decisions: tuple[ResearchDecision, ...]
    observations: tuple[ResearchObservation, ...]
    conclusion: ResearchConclusion
    consumed_tool_calls: int = Field(ge=0)
    consumed_compute_units: float = Field(ge=0)
    consumed_wall_seconds: float = Field(ge=0)
    consumed_storage_bytes: int = Field(ge=0)
    budget_overrun: bool
    provenance_event_hashes: tuple[str, ...] = Field(min_length=1)
    generated_at: datetime
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def hash_and_budget_are_valid(self) -> ResearchCampaignReport:
        if self.package_hash != self.calculated_hash():
            raise ValueError("research campaign package hash does not match its content")
        budget = self.contract.budget
        expected_overrun = (
            self.consumed_tool_calls > budget.maximum_tool_calls
            or self.consumed_compute_units > budget.maximum_compute_units + 1e-12
            or self.consumed_wall_seconds > budget.maximum_wall_seconds + 1e-12
            or self.consumed_storage_bytes > budget.maximum_storage_bytes
        )
        if self.budget_overrun != expected_overrun:
            raise ValueError("research report budget-overrun flag is not derived")
        return self

    def calculated_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json", exclude={"package_hash"}))

    @classmethod
    def create(cls, **values: object) -> ResearchCampaignReport:
        provisional = cls.model_construct(package_hash="0" * 64, **values)
        return cls.model_validate(
            {
                **provisional.model_dump(mode="json", exclude={"package_hash"}),
                "package_hash": provisional.calculated_hash(),
            }
        )

    def write(self, output_directory: str | Path) -> Path:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        path = output / "research_campaign_report.json"
        temporary = output / ".research_campaign_report.json.tmp"
        temporary.write_text(self.model_dump_json(indent=2) + "\n")
        os.replace(temporary, path)
        return path

    @classmethod
    def read_verified(cls, path: str | Path) -> ResearchCampaignReport:
        report = cls.model_validate_json(Path(path).read_text())
        if report.package_hash != report.calculated_hash():
            raise ValueError("research campaign package failed hash verification")
        return report


@runtime_checkable
class ResearchTool(Protocol):
    manifest: ResearchToolManifest

    def validate(self, arguments: dict[str, Any]) -> ValidationReport: ...

    def estimate_cost(self, arguments: dict[str, Any]) -> CostEstimate: ...

    def execute(
        self,
        arguments: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> ResearchToolResult: ...


@dataclass(frozen=True)
class ResearchToolRegistry:
    tools: tuple[ResearchTool, ...]

    def __post_init__(self) -> None:
        names = [tool.manifest.name for tool in self.tools]
        if len(names) != len(set(names)):
            raise ValueError("research tool names must be unique")

    def get(self, name: str) -> ResearchTool:
        for tool in self.tools:
            if tool.manifest.name == name:
                return tool
        raise ValueError(f"unknown research tool {name!r}")

    @property
    def manifests(self) -> tuple[ResearchToolManifest, ...]:
        return tuple(sorted((tool.manifest for tool in self.tools), key=lambda item: item.name))


class ResearchDecisionRejected(ValueError):
    pass


class ResearchCrashPoint(StrEnum):
    AFTER_CONTRACT_REGISTERED = "after_contract_registered"
    AFTER_DECISION_COMMITTED = "after_decision_committed"
    AFTER_TOOL_RECEIPT = "after_tool_receipt"
    AFTER_OBSERVATION_COMMITTED = "after_observation_committed"
    AFTER_REPORT_COMMITTED = "after_report_committed"


class InjectedResearchCrash(RuntimeError):
    def __init__(self, point: ResearchCrashPoint) -> None:
        super().__init__(f"injected universal research crash at {point.value}")
        self.point = point


class ResearchProjection:
    def __init__(self) -> None:
        self.contract: ResearchProblemContract | None = None
        self.decisions: dict[int, ResearchDecision] = {}
        self.observations: dict[int, ResearchObservation] = {}
        self.report: ResearchCampaignReport | None = None

    @classmethod
    def replay(cls, events: tuple[StoredEvent, ...]) -> ResearchProjection:
        state = cls()
        for event in events:
            if event.event_type == "research_contract_registered":
                state.contract = ResearchProblemContract.model_validate(event.payload["contract"])
            elif event.event_type == "research_decision_committed":
                decision = ResearchDecision.model_validate(event.payload["decision"])
                state.decisions[decision.iteration] = decision
            elif event.event_type == "research_observation_committed":
                observation = ResearchObservation.model_validate(event.payload["observation"])
                state.observations[observation.iteration] = observation
            elif event.event_type == "research_campaign_completed":
                state.report = ResearchCampaignReport.model_validate(event.payload["report"])
        return state

    def hypotheses(self) -> tuple[ResearchHypothesis, ...]:
        if self.contract is None:
            return ()
        result = {item.id: item for item in self.contract.root_hypotheses}
        for decision in self.ordered_decisions:
            result.update({item.id: item for item in decision.new_hypotheses})
        return tuple(result.values())

    def relations(self) -> tuple[ResearchRelation, ...]:
        return tuple(
            relation
            for decision in self.ordered_decisions
            for relation in decision.new_relations
        )

    @property
    def ordered_decisions(self) -> tuple[ResearchDecision, ...]:
        return tuple(self.decisions[key] for key in sorted(self.decisions))

    @property
    def ordered_observations(self) -> tuple[ResearchObservation, ...]:
        return tuple(self.observations[key] for key in sorted(self.observations))

    @property
    def consumed_tool_calls(self) -> int:
        return len(self.observations)

    @property
    def consumed_cost(self) -> CostEstimate:
        return CostEstimate(
            compute_units=sum(
                item.result.cost.compute_units for item in self.observations.values()
            ),
            wall_seconds=sum(item.result.cost.wall_seconds for item in self.observations.values()),
            storage_bytes=sum(
                item.result.cost.storage_bytes for item in self.observations.values()
            ),
        )


class UniversalResearchRunner:
    """Restart-safe open-ended loop controlled by model decisions and hard verifiers."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        contract: ResearchProblemContract,
        completion_client: Any,
        tools: ResearchToolRegistry,
        control: CampaignControl | None = None,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        crash_at: ResearchCrashPoint | None = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.ledger = ledger
        self.contract = contract
        self.completion_client = completion_client
        self.tools = tools
        self.control = control
        self.route = route
        self.escalation_reason = escalation_reason
        self.crash_at = crash_at
        installed = {item.name for item in tools.manifests}
        missing = set(contract.allowed_tools) - installed
        if missing:
            raise ValueError(f"problem contract names unavailable tools: {sorted(missing)}")

    def _crash(self, point: ResearchCrashPoint) -> None:
        if self.crash_at is point:
            raise InjectedResearchCrash(point)

    def _state(self) -> ResearchProjection:
        return ResearchProjection.replay(self.ledger.load(self.campaign_id))

    def _append(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        suffix: str,
    ) -> None:
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            idempotency_key=f"{self.campaign_id}:research:{suffix}",
        )

    def _register_contract(self) -> None:
        state = self._state()
        if state.contract is not None:
            if state.contract != self.contract:
                raise ValueError("campaign already has a different research contract")
            return
        self._append(
            "research_contract_registered",
            "research_contract",
            self.contract.id,
            {"contract": self.contract.model_dump(mode="json")},
            "contract",
        )
        self._crash(ResearchCrashPoint.AFTER_CONTRACT_REGISTERED)

    def _prompt_state(self, state: ResearchProjection, iteration: int) -> dict[str, Any]:
        cost = state.consumed_cost
        return {
            "iteration": iteration,
            "contract": self.contract.model_dump(mode="json"),
            "available_tools": [item.model_dump(mode="json") for item in self.tools.manifests],
            "hypotheses": [item.model_dump(mode="json") for item in state.hypotheses()],
            "relations": [item.model_dump(mode="json") for item in state.relations()],
            "observations": [
                item.model_dump(mode="json") for item in state.ordered_observations
            ],
            "budget_used": {
                "iterations": len(state.decisions),
                "tool_calls": state.consumed_tool_calls,
                "compute_units": cost.compute_units,
                "wall_seconds": cost.wall_seconds,
                "storage_bytes": cost.storage_bytes,
            },
        }

    def _messages(
        self,
        state: ResearchProjection,
        iteration: int,
        rejected: list[tuple[str, str]],
    ) -> list[dict[str, str]]:
        system = (
            "You are the scientific decision-maker inside a universal computational "
            "conjecture solver. You own hypothesis formation, coordinates, experiment "
            "selection, analysis, falsification, and stopping. Infrastructure owns tool "
            "admission, immutable evidence, preregistration, and budgets. Return exactly "
            "one JSON object matching the supplied ResearchDecision schema, with no code "
            "fence. Never invent a tool or evidence ID. A tool decision must preregister "
            "numeric intervals or exact predictions before execution. Register a new "
            "hypothesis before using a tool to test it. Prefer destructive tests. Do not "
            "claim scientific novelty unless literature-search evidence verifies it. A "
            "bounded null or insufficient-evidence conclusion is valid. When an allowed "
            "literature-search tool is installed, the first research action must attempt "
            "reconnaissance. No useful hit is required; the recorded attempt is enough "
            "to continue."
        )
        payload = {
            "research_state": self._prompt_state(state, iteration),
            "decision_schema": ResearchDecision.model_json_schema(),
        }
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, sort_keys=True)},
        ]
        for content, error in rejected:
            messages.extend(
                (
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": (
                            "The deterministic admission gate rejected that decision: "
                            f"{error}. Return one corrected complete JSON object only."
                        ),
                    },
                )
            )
        return messages

    def _remaining_budget(self, state: ResearchProjection) -> CostEstimate:
        used = state.consumed_cost
        budget = self.contract.budget
        return CostEstimate(
            compute_units=max(0.0, budget.maximum_compute_units - used.compute_units),
            wall_seconds=max(0.0, budget.maximum_wall_seconds - used.wall_seconds),
            storage_bytes=max(0, budget.maximum_storage_bytes - used.storage_bytes),
        )

    def _admit_decision(
        self,
        decision: ResearchDecision,
        state: ResearchProjection,
        iteration: int,
    ) -> CostEstimate | None:
        if decision.iteration != iteration:
            raise ResearchDecisionRejected("decision iteration does not match campaign state")
        known = {item.id for item in state.hypotheses()}
        new = {item.id for item in decision.new_hypotheses}
        if known & new:
            raise ResearchDecisionRejected("new hypothesis ID already exists")
        all_hypotheses = known | new
        evidence_ids = {item.id for item in state.ordered_observations}
        literature_tools = {
            item.name
            for item in self.tools.manifests
            if item.kind is ResearchToolKind.LITERATURE_SEARCH
            and item.name in self.contract.allowed_tools
        }
        literature_attempted = any(
            item.tool_name in literature_tools for item in state.ordered_observations
        )
        if (
            literature_tools
            and not literature_attempted
            and (
                decision.kind is not ResearchDecisionKind.USE_TOOL
                or decision.tool_call is None
                or decision.tool_call.tool_name not in literature_tools
            )
        ):
            raise ResearchDecisionRejected(
                "an allowed literature-search tool is available; attempt it before "
                "simulation or conclusion. A completed no-hit or unavailable result "
                "satisfies this startup requirement"
            )
        for hypothesis in decision.new_hypotheses:
            if hypothesis.model_family not in self.contract.allowed_model_families:
                raise ResearchDecisionRejected("new hypothesis uses a forbidden model family")
            if not set(hypothesis.parent_ids) <= all_hypotheses:
                raise ResearchDecisionRejected("new hypothesis names an unknown parent")
            if not set(hypothesis.motivating_evidence_ids) <= evidence_ids:
                raise ResearchDecisionRejected("new hypothesis names unknown motivating evidence")
        for relation in decision.new_relations:
            if not {
                relation.source_hypothesis_id,
                relation.target_hypothesis_id,
            } <= all_hypotheses:
                raise ResearchDecisionRejected("new relation names an unknown hypothesis")

        if decision.kind is ResearchDecisionKind.USE_TOOL:
            call = decision.tool_call
            assert call is not None
            if call.tool_name not in self.contract.allowed_tools:
                raise ResearchDecisionRejected("decision selected a tool outside the contract")
            if state.consumed_tool_calls >= self.contract.budget.maximum_tool_calls:
                raise ResearchDecisionRejected("tool-call budget is exhausted")
            tool = self.tools.get(call.tool_name)
            if not set(item.hypothesis_id for item in call.predictions) <= all_hypotheses:
                raise ResearchDecisionRejected("prediction names an unknown hypothesis")
            if any(
                item.observable not in tool.manifest.supported_observables
                for item in call.predictions
            ):
                raise ResearchDecisionRejected("prediction requests an unsupported observable")
            report = tool.validate(call.arguments)
            if not report.valid:
                raise ResearchDecisionRejected(
                    "tool rejected arguments: " + "; ".join(report.errors)
                )
            estimate = tool.estimate_cost(call.arguments)
            remaining = self._remaining_budget(state)
            if (
                estimate.compute_units > remaining.compute_units + 1e-12
                or estimate.wall_seconds > remaining.wall_seconds + 1e-12
                or estimate.storage_bytes > remaining.storage_bytes
            ):
                raise ResearchDecisionRejected("tool estimate exceeds remaining campaign budget")
            if call.evidence_stage in {
                ResearchEvidenceStage.CONFIRMATION,
                ResearchEvidenceStage.FALSIFICATION,
            }:
                prior_groups = {
                    item.independence_group for item in state.ordered_observations
                }
                if call.independence_group in prior_groups:
                    raise ResearchDecisionRejected(
                        "confirmation or falsification must use a fresh independence group"
                    )
            return estimate

        conclusion = decision.conclusion
        assert conclusion is not None
        if not set(conclusion.evidence_ids) <= evidence_ids:
            raise ResearchDecisionRejected("conclusion names unknown evidence")
        if conclusion.disposition is ResearchDisposition.BOUNDED_NULL:
            if not self.contract.evidence_policy.allow_bounded_null:
                raise ResearchDecisionRejected("contract does not allow a bounded null")
            return None
        if conclusion.disposition is not ResearchDisposition.VALIDATED_WITHIN_TOOLS:
            return None
        candidate = conclusion.candidate
        assert candidate is not None
        if candidate.hypothesis_id not in all_hypotheses:
            raise ResearchDecisionRejected("candidate result names an unknown hypothesis")
        if candidate.result_class not in self.contract.allowed_result_classes:
            raise ResearchDecisionRejected("candidate result class is outside the contract")
        if set(candidate.supporting_evidence_ids) != set(conclusion.evidence_ids):
            raise ResearchDecisionRejected("candidate and conclusion evidence sets differ")
        if not set(candidate.contradicting_evidence_ids) <= evidence_ids:
            raise ResearchDecisionRejected("candidate names unknown contradicting evidence")
        by_id = {item.id: item for item in state.ordered_observations}
        support = [by_id[item] for item in conclusion.evidence_ids]
        if not support or any(not item.evidence_eligible for item in support):
            raise ResearchDecisionRejected("validated result requires eligible evidence")
        confirmation = [
            item
            for item in support
            if item.evidence_stage
            in {ResearchEvidenceStage.CONFIRMATION, ResearchEvidenceStage.FALSIFICATION}
        ]
        groups = {item.independence_group for item in confirmation}
        if len(groups) < self.contract.evidence_policy.minimum_independent_confirmations:
            raise ResearchDecisionRejected("validated result lacks independent confirmation")
        if any(not all(item.prediction_checks.values()) for item in confirmation):
            raise ResearchDecisionRejected("confirmation violated a preregistered prediction")
        if any(candidate.hypothesis_id not in item.hypothesis_ids for item in confirmation):
            raise ResearchDecisionRejected(
                "candidate hypothesis was not preregistered in its confirmation"
            )
        if self.contract.evidence_policy.require_deliberate_falsification and not any(
            item.evidence_stage is ResearchEvidenceStage.FALSIFICATION for item in support
        ):
            raise ResearchDecisionRejected("validated result lacks a deliberate falsification test")
        if (
            candidate.novelty_status is NoveltyStatus.VERIFIED_NEW
            and not any(item.tool_name in literature_tools for item in support)
        ):
            raise ResearchDecisionRejected(
                "verified-new status requires literature-search evidence"
            )
        return None

    def _generate_decision(
        self,
        state: ResearchProjection,
        iteration: int,
    ) -> tuple[ResearchDecision, CostEstimate | None]:
        rejected: list[tuple[str, str]] = []
        for _attempt in range(self.contract.maximum_invalid_decisions_per_iteration):
            result = self.completion_client.complete(
                self._messages(state, iteration, rejected),
                route=self.route,
                escalation_reason=self.escalation_reason,
                max_tokens=None,
                temperature=0.2,
            )
            if result.finish_reason != "stop":
                rejected.append(
                    (result.content, f"incomplete completion: {result.finish_reason}")
                )
                continue
            try:
                decision = ResearchDecision.model_validate_json(result.content)
                estimate = self._admit_decision(decision, state, iteration)
                return decision, estimate
            except (ValueError, ResearchDecisionRejected) as error:
                rejected.append((result.content, str(error)))
        raise ResearchDecisionRejected(
            "model exhausted structural decision repairs: "
            + (rejected[-1][1] if rejected else "no decision")
        )

    @staticmethod
    def _prediction_checks(
        predictions: tuple[ObservablePrediction, ...],
        result: ResearchToolResult,
    ) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        for index, prediction in enumerate(predictions):
            key = f"{index}:{prediction.hypothesis_id}:{prediction.observable}"
            observed = result.observables.get(prediction.observable)
            if prediction.exact is not None:
                checks[key] = observed == prediction.exact
                continue
            if not isinstance(observed, (int, float)) or isinstance(observed, bool):
                checks[key] = False
                continue
            checks[key] = (
                (prediction.minimum is None or observed >= prediction.minimum)
                and (prediction.maximum is None or observed <= prediction.maximum)
            )
        return checks

    def _tool_result(
        self,
        decision: ResearchDecision,
        estimate: CostEstimate,
    ) -> ResearchToolResult:
        call = decision.tool_call
        assert call is not None
        tool = self.tools.get(call.tool_name)
        payload = {
            "tool": tool.manifest.model_dump(mode="json"),
            "arguments": call.arguments,
            "estimated_cost": estimate.model_dump(mode="json"),
            "decision_id": decision.id,
        }
        intent = create_intent(
            campaign_id=self.campaign_id,
            operation=ExternalOperation.RESEARCH_TOOL,
            logical_action_id=decision.id,
            idempotency_key=f"research-tool:{self.campaign_id}:{decision.id}",
            payload=payload,
            external_idempotency_supported=True,
        )
        outbox = ExternalOutbox(campaign_id=self.campaign_id, ledger=self.ledger)
        state = outbox.register(intent)
        if state.receipt is not None:
            return ResearchToolResult.model_validate(state.receipt.response["result"])
        if state.active_attempt is not None:
            outbox.interrupt_active(
                intent.id,
                "controller restarted; idempotent research tool will reattach or replay",
            )
        outbox.begin(intent.id)
        try:
            result = tool.execute(call.arguments, idempotency_key=intent.idempotency_key)
        except Exception as error:
            outbox.fail(intent.id, f"{type(error).__name__}: {error}")
            raise
        outbox.succeed(
            intent.id,
            response={"result": result.model_dump(mode="json")},
            external_id=intent.idempotency_key,
        )
        self._crash(ResearchCrashPoint.AFTER_TOOL_RECEIPT)
        return result

    def _commit_observation(
        self,
        decision: ResearchDecision,
        result: ResearchToolResult,
        estimate: CostEstimate,
    ) -> ResearchObservation:
        call = decision.tool_call
        assert call is not None
        if (
            result.cost.compute_units > estimate.compute_units + 1e-12
            or result.cost.wall_seconds > estimate.wall_seconds + 1e-12
            or result.cost.storage_bytes > estimate.storage_bytes
        ):
            result = result.model_copy(
                update={
                    "validity_checks": {
                        **result.validity_checks,
                        "preauthorized_cost_not_exceeded": False,
                    }
                }
            )
        checks = self._prediction_checks(call.predictions, result)
        observation = ResearchObservation(
            id=f"observation_{_canonical_hash(decision.id)[:20]}",
            iteration=decision.iteration,
            decision_id=decision.id,
            tool_name=call.tool_name,
            evidence_stage=call.evidence_stage,
            evidence_role=call.evidence_role,
            independence_group=call.independence_group,
            hypothesis_ids=tuple(sorted({item.hypothesis_id for item in call.predictions})),
            preregistered_predictions=call.predictions,
            prediction_checks=checks,
            result=result,
            evidence_eligible=(
                result.completed
                and bool(result.validity_checks)
                and all(result.validity_checks.values())
            ),
        )
        self._append(
            "research_observation_committed",
            "research_observation",
            observation.id,
            {"observation": observation.model_dump(mode="json")},
            f"iteration:{decision.iteration}:observation",
        )
        self._crash(ResearchCrashPoint.AFTER_OBSERVATION_COMMITTED)
        return observation

    def _budget_conclusion(self, reason: str) -> ResearchConclusion:
        return ResearchConclusion(
            disposition=ResearchDisposition.BUDGET_EXHAUSTED,
            reason=reason,
        )

    def _build_report(
        self,
        state: ResearchProjection,
        conclusion: ResearchConclusion,
    ) -> ResearchCampaignReport:
        cost = state.consumed_cost
        events = self.ledger.load(self.campaign_id)
        return ResearchCampaignReport.create(
            campaign_id=self.campaign_id,
            contract=self.contract,
            hypotheses=state.hypotheses(),
            relations=state.relations(),
            decisions=state.ordered_decisions,
            observations=state.ordered_observations,
            conclusion=conclusion,
            consumed_tool_calls=state.consumed_tool_calls,
            consumed_compute_units=cost.compute_units,
            consumed_wall_seconds=cost.wall_seconds,
            consumed_storage_bytes=cost.storage_bytes,
            budget_overrun=(
                state.consumed_tool_calls > self.contract.budget.maximum_tool_calls
                or cost.compute_units
                > self.contract.budget.maximum_compute_units + 1e-12
                or cost.wall_seconds > self.contract.budget.maximum_wall_seconds + 1e-12
                or cost.storage_bytes > self.contract.budget.maximum_storage_bytes
            ),
            provenance_event_hashes=tuple(event.event_hash for event in events),
            generated_at=utc_now(),
        )

    def _complete(
        self,
        state: ResearchProjection,
        conclusion: ResearchConclusion,
    ) -> ResearchCampaignReport:
        report = self._build_report(state, conclusion)
        self._append(
            "research_campaign_completed",
            "research_campaign",
            self.campaign_id,
            {"report": report.model_dump(mode="json")},
            "completed",
        )
        self._crash(ResearchCrashPoint.AFTER_REPORT_COMMITTED)
        committed = self._state().report
        assert committed is not None
        return committed

    def run(self) -> ResearchCampaignReport:
        self._register_contract()
        while True:
            state = self._state()
            if state.report is not None:
                return state.report
            concluding = next(
                (
                    item
                    for item in reversed(state.ordered_decisions)
                    if item.kind is ResearchDecisionKind.CONCLUDE
                ),
                None,
            )
            if concluding is not None:
                conclusion = concluding.conclusion
                assert conclusion is not None
                return self._complete(state, conclusion)
            pending = next(
                (
                    item
                    for item in state.ordered_decisions
                    if item.kind is ResearchDecisionKind.USE_TOOL
                    and item.iteration not in state.observations
                ),
                None,
            )
            iteration = pending.iteration if pending is not None else len(state.decisions)
            if iteration >= self.contract.budget.maximum_iterations:
                return self._complete(
                    state,
                    self._budget_conclusion("maximum autonomous iterations exhausted"),
                )
            if self.control is not None:
                self.control.require_processing_authority()
            decision = pending
            estimate: CostEstimate | None = None
            if decision is None:
                decision, estimate = self._generate_decision(state, iteration)
                self._append(
                    "research_decision_committed",
                    "research_decision",
                    decision.id,
                    {"decision": decision.model_dump(mode="json")},
                    f"iteration:{iteration}:decision",
                )
                self._crash(ResearchCrashPoint.AFTER_DECISION_COMMITTED)
                state = self._state()
            else:
                call = decision.tool_call
                assert call is not None
                estimate = self.tools.get(call.tool_name).estimate_cost(call.arguments)

            if decision.kind is ResearchDecisionKind.CONCLUDE:
                conclusion = decision.conclusion
                assert conclusion is not None
                return self._complete(self._state(), conclusion)

            state = self._state()
            if iteration not in state.observations:
                if estimate is None:
                    estimate = self._admit_decision(decision, state, iteration)
                assert estimate is not None
                result = self._tool_result(decision, estimate)
                self._commit_observation(decision, result, estimate)
