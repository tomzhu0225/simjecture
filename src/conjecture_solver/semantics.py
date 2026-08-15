"""Deterministic scientific evidence rules."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .models import (
    AttemptOutcome,
    AttemptRecord,
    EvidenceRole,
    HypothesisNode,
    PropositionClass,
    RunEvidence,
    StrictModel,
)


class EvidenceVerdict(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE_PENDING = "ineligible_pending"
    INELIGIBLE_INTERRUPTED = "ineligible_interrupted"
    INELIGIBLE_INFRASTRUCTURE = "ineligible_infrastructure"
    INELIGIBLE_SPECIFICATION = "ineligible_specification"
    INELIGIBLE_NUMERICAL = "ineligible_numerical"
    INELIGIBLE_VALIDITY = "ineligible_validity"


class EligibilityDecision(StrictModel):
    verdict: EvidenceVerdict
    eligible: bool
    reason: str


class MatchedObservation(StrictModel):
    evidence_id: str
    coordinates: dict[str, float]
    outcome: float
    outcome_uncertainty: float = Field(default=0.0, ge=0)


class SufficiencyWitness(StrictModel):
    hypothesis_id: str
    left_evidence_id: str
    right_evidence_id: str
    coordinates_match: bool
    outcome_separation: float
    required_separation: float
    falsifies: bool
    reason: str


def classify_attempt(attempt: AttemptRecord) -> EligibilityDecision:
    verdicts = {
        AttemptOutcome.INTERRUPTED: EvidenceVerdict.INELIGIBLE_INTERRUPTED,
        AttemptOutcome.INFRASTRUCTURE_FAILURE: EvidenceVerdict.INELIGIBLE_INFRASTRUCTURE,
        AttemptOutcome.SPECIFICATION_FAILURE: EvidenceVerdict.INELIGIBLE_SPECIFICATION,
        AttemptOutcome.NUMERICAL_FAILURE: EvidenceVerdict.INELIGIBLE_NUMERICAL,
        AttemptOutcome.VALIDITY_FAILURE: EvidenceVerdict.INELIGIBLE_VALIDITY,
    }
    if attempt.outcome is None:
        return EligibilityDecision(
            verdict=EvidenceVerdict.INELIGIBLE_PENDING,
            eligible=False,
            reason="a pending attempt is not physical evidence",
        )
    if attempt.outcome is AttemptOutcome.SUCCESS:
        return EligibilityDecision(
            verdict=EvidenceVerdict.ELIGIBLE,
            eligible=True,
            reason="attempt completed and passed execution-level gates",
        )
    return EligibilityDecision(
        verdict=verdicts[attempt.outcome],
        eligible=False,
        reason=f"{attempt.outcome.value} is not physical evidence",
    )


def may_confirm(hypothesis: HypothesisNode, evidence: RunEvidence) -> EligibilityDecision:
    if not evidence.eligible:
        return EligibilityDecision(
            verdict=EvidenceVerdict.INELIGIBLE_VALIDITY,
            eligible=False,
            reason=evidence.eligibility_reason,
        )
    if evidence.role is not EvidenceRole.CONFIRMATION:
        return EligibilityDecision(
            verdict=EvidenceVerdict.INELIGIBLE_VALIDITY,
            eligible=False,
            reason="only evidence preregistered as confirmation may confirm a claim",
        )
    if evidence.id in hypothesis.motivating_evidence_ids:
        return EligibilityDecision(
            verdict=EvidenceVerdict.INELIGIBLE_VALIDITY,
            eligible=False,
            reason="evidence used to construct a hypothesis cannot independently confirm it",
        )
    return EligibilityDecision(
        verdict=EvidenceVerdict.ELIGIBLE,
        eligible=True,
        reason="evidence is eligible and independent of hypothesis construction",
    )


def evaluate_predictive_sufficiency(
    hypothesis: HypothesisNode,
    left: MatchedObservation,
    right: MatchedObservation,
    *,
    coordinate_atol: float = 1e-10,
) -> SufficiencyWitness:
    if hypothesis.proposition_class is not PropositionClass.PREDICTIVE_SUFFICIENCY:
        raise ValueError("matched-pair evaluation requires a predictive-sufficiency hypothesis")

    coordinate_names = set(hypothesis.coordinates)
    if coordinate_names != set(left.coordinates) or coordinate_names != set(right.coordinates):
        raise ValueError("observations must provide exactly the hypothesis coordinates")

    coordinates_match = all(
        abs(left.coordinates[name] - right.coordinates[name]) <= coordinate_atol
        for name in hypothesis.coordinates
    )
    separation = abs(left.outcome - right.outcome)
    required = (
        hypothesis.evidence_contract.primary_tolerance
        + left.outcome_uncertainty
        + right.outcome_uncertainty
    )
    falsifies = coordinates_match and separation > required
    reason = (
        "matched coordinates produce outcomes separated beyond the evidence contract"
        if falsifies
        else "the pair is not a valid destructive witness"
    )
    return SufficiencyWitness(
        hypothesis_id=hypothesis.id,
        left_evidence_id=left.evidence_id,
        right_evidence_id=right.evidence_id,
        coordinates_match=coordinates_match,
        outcome_separation=separation,
        required_separation=required,
        falsifies=falsifies,
        reason=reason,
    )
