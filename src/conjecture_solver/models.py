"""Versioned scientific records shared by reasoning and deterministic tools."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class PropositionClass(StrEnum):
    EXISTENTIAL_CONTRIBUTION = "existential_contribution"
    UNIVERSAL_NON_CONTRIBUTION = "universal_non_contribution"
    PREDICTIVE_SUFFICIENCY = "predictive_sufficiency"
    CAUSAL_EXHAUSTIVENESS = "causal_exhaustiveness"
    INVARIANCE = "invariance"
    THRESHOLD = "threshold"
    PATH_DEPENDENCE = "path_dependence"


class HypothesisOrigin(StrEnum):
    HUMAN = "human"
    AI = "ai"
    MIXED = "mixed"


class EvidenceRole(StrEnum):
    DISCOVERY = "discovery"
    CONFIRMATION = "confirmation"
    QUALIFICATION = "qualification"


class AttemptOutcome(StrEnum):
    SUCCESS = "success"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    SPECIFICATION_FAILURE = "specification_failure"
    NUMERICAL_FAILURE = "numerical_failure"
    VALIDITY_FAILURE = "validity_failure"
    INTERRUPTED = "interrupted"


class ClaimDisposition(StrEnum):
    SUPPORTED_WITHIN_MODEL = "supported_within_model"
    REFUTED_WITHIN_MODEL = "refuted_within_model"
    UNRESOLVED = "unresolved"


class CampaignStatus(StrEnum):
    ACTIVE = "active"
    PAUSE_REQUESTED = "pause_requested"
    QUIESCING = "quiescing"
    PAUSED = "paused"
    RESUMING = "resuming"
    RECOVERING = "recovering"
    EMERGENCY_STOPPED = "emergency_stopped"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class InterventionType(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    EMERGENCY_STOP = "emergency_stop"
    ACTION_VETO = "action_veto"
    PRIORITY_UPDATE = "priority_update"
    TACTICAL_SUGGESTION = "tactical_suggestion"
    REVIEWER_CHALLENGE = "reviewer_challenge"
    EVIDENCE_INJECTION = "evidence_injection"
    CONTRACT_AMENDMENT = "contract_amendment"
    CAMPAIGN_BRANCH = "campaign_branch"


class DomainSpec(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("domain"))
    description: str = Field(min_length=1)
    model_family: str = Field(min_length=1)
    assumptions: tuple[str, ...] = ()
    fixed_parameters: dict[str, float | int | str] = Field(default_factory=dict)


class ObservableSpec(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("observable"))
    name: str = Field(min_length=1)
    semantic_kind: str = Field(min_length=1)
    mathematical_definition: str = Field(min_length=1)
    estimator: str = Field(min_length=1)
    units: str = "dimensionless"
    tolerance: float = Field(gt=0)


class EvidenceContract(StrictModel):
    primary_observable_id: str
    falsifying_witness: str = Field(min_length=1)
    primary_tolerance: float = Field(gt=0)
    minimum_independent_confirmation_attempts: int = Field(default=1, ge=1)


class MatchedPairFormalPredicate(StrictModel):
    """Executable semantics for a finite predictive-sufficiency witness."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    predicate_type: Literal["matched_pair_predictive_sufficiency"] = (
        "matched_pair_predictive_sufficiency"
    )
    matched_coordinates: tuple[str, ...] = Field(min_length=1)
    outcome_observable_id: str = Field(min_length=1)
    coordinate_tolerance: float = Field(default=1e-10, ge=0)
    maximum_outcome_difference: float = Field(gt=0)


class HypothesisNode(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("hypothesis"))
    statement: str = Field(min_length=1)
    machine_predicate: str = Field(min_length=1)
    formal_predicate: MatchedPairFormalPredicate | None = None
    proposition_class: PropositionClass
    domain: DomainSpec
    coordinates: tuple[str, ...]
    evidence_contract: EvidenceContract
    origin: HypothesisOrigin
    parent_ids: tuple[str, ...] = ()
    motivating_evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_declarative_statement(self) -> HypothesisNode:
        if self.statement.endswith("?"):
            raise ValueError("a hypothesis must be declarative, not a research question")
        if not self.coordinates:
            raise ValueError("a hypothesis must declare its tested coordinates")
        if self.formal_predicate is not None:
            if self.proposition_class is not PropositionClass.PREDICTIVE_SUFFICIENCY:
                raise ValueError(
                    "the matched-pair predicate is only valid for predictive sufficiency"
                )
            if self.formal_predicate.matched_coordinates != self.coordinates:
                raise ValueError("formal predicate coordinates must match hypothesis coordinates")
            if (
                self.formal_predicate.outcome_observable_id
                != self.evidence_contract.primary_observable_id
            ):
                raise ValueError("formal predicate observable must match the evidence contract")
            if (
                abs(
                    self.formal_predicate.maximum_outcome_difference
                    - self.evidence_contract.primary_tolerance
                )
                > 1e-15
            ):
                raise ValueError("formal predicate tolerance must match the evidence contract")
        return self


class ExperimentSpec(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("experiment"))
    hypothesis_ids: tuple[str, ...]
    action_type: str
    physical_parameters: dict[str, float | int | str]
    numerical_parameters: dict[str, float | int | str] = Field(default_factory=dict)
    required_diagnostics: tuple[str, ...]
    predictions: dict[str, str]
    falsification_condition: str


class AttemptRecord(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("attempt"))
    experiment_id: str
    idempotency_key: str = Field(min_length=1)
    outcome: AttemptOutcome | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    external_job_id: str | None = None
    failure_detail: str | None = None

    @model_validator(mode="after")
    def outcome_fields_are_consistent(self) -> AttemptRecord:
        if self.outcome is None:
            if self.completed_at or self.failure_detail:
                raise ValueError("a pending attempt cannot be completed or failed")
            return self
        if self.completed_at is None:
            raise ValueError("an attempt with an outcome requires completed_at")
        failed = self.outcome is not AttemptOutcome.SUCCESS
        if failed and not self.failure_detail:
            raise ValueError("a non-successful attempt requires failure_detail")
        if not failed and self.failure_detail:
            raise ValueError("a successful attempt cannot carry failure_detail")
        return self


class RunEvidence(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("evidence"))
    source_attempt_id: str
    role: EvidenceRole
    eligible: bool
    eligibility_reason: str
    observable_values: dict[str, float]
    uncertainties: dict[str, float] = Field(default_factory=dict)
    independence_group: str
    artifact_hashes: tuple[str, ...] = ()


class Claim(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("claim"))
    hypothesis_id: str
    statement: str
    disposition: ClaimDisposition
    scope: str
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    limitations: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)


class DecisionRecord(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("decision"))
    campaign_id: str
    checkpoint_id: str
    candidate_action_ids: tuple[str, ...]
    selected_action_id: str
    predicted_outcomes: dict[str, str]
    validator_report: dict[str, Any]
    model_id: str | None = None
    model_route_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class CampaignCheckpoint(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("checkpoint"))
    campaign_id: str
    status: CampaignStatus
    last_event_sequence: int = Field(ge=0)
    state_hash: str
    pending_action_ids: tuple[str, ...] = ()
    external_job_ids: tuple[str, ...] = ()
    budget_reserved: float = Field(default=0.0, ge=0)
    component_versions: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class HumanIntervention(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("intervention"))
    actor: str
    intervention_type: InterventionType
    scope: str
    reason: str
    checkpoint_before: str
    payload: dict[str, Any] = Field(default_factory=dict)
    impact: dict[str, Any] = Field(default_factory=dict)
    checkpoint_after: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
