from __future__ import annotations

from datetime import UTC, datetime

import pytest

from conjecture_solver.benchmarks.kinetic_sufficiency import build_problem
from conjecture_solver.models import (
    AttemptOutcome,
    AttemptRecord,
    EvidenceRole,
    RunEvidence,
)
from conjecture_solver.semantics import (
    EvidenceVerdict,
    MatchedObservation,
    classify_attempt,
    evaluate_predictive_sufficiency,
    may_confirm,
)


def make_attempt(outcome: AttemptOutcome, detail: str | None = None) -> AttemptRecord:
    return AttemptRecord(
        id="attempt_test",
        experiment_id="experiment_test",
        idempotency_key="campaign:test",
        outcome=outcome,
        completed_at=datetime.now(UTC),
        failure_detail=detail,
    )


def test_pending_attempt_is_not_physical_evidence() -> None:
    decision = classify_attempt(
        AttemptRecord(
            id="attempt_pending",
            experiment_id="experiment_test",
            idempotency_key="campaign:pending",
        )
    )
    assert not decision.eligible
    assert decision.verdict is EvidenceVerdict.INELIGIBLE_PENDING


@pytest.mark.parametrize(
    ("outcome", "verdict"),
    [
        (AttemptOutcome.INTERRUPTED, EvidenceVerdict.INELIGIBLE_INTERRUPTED),
        (AttemptOutcome.INFRASTRUCTURE_FAILURE, EvidenceVerdict.INELIGIBLE_INFRASTRUCTURE),
        (AttemptOutcome.SPECIFICATION_FAILURE, EvidenceVerdict.INELIGIBLE_SPECIFICATION),
        (AttemptOutcome.NUMERICAL_FAILURE, EvidenceVerdict.INELIGIBLE_NUMERICAL),
        (AttemptOutcome.VALIDITY_FAILURE, EvidenceVerdict.INELIGIBLE_VALIDITY),
    ],
)
def test_failed_or_interrupted_attempt_is_not_physical_evidence(
    outcome: AttemptOutcome,
    verdict: EvidenceVerdict,
) -> None:
    decision = classify_attempt(make_attempt(outcome, "deliberate test failure"))
    assert not decision.eligible
    assert decision.verdict is verdict


def test_discovery_evidence_cannot_confirm_repaired_hypothesis() -> None:
    hypothesis, _ = build_problem()
    evidence = RunEvidence(
        id="evidence_discovery",
        source_attempt_id="attempt_1",
        role=EvidenceRole.DISCOVERY,
        eligible=True,
        eligibility_reason="valid run",
        observable_values={"growth_rate": 0.1},
        independence_group="seed_1",
    )
    repaired = hypothesis.model_copy(
        update={"motivating_evidence_ids": (evidence.id,)}
    )
    decision = may_confirm(repaired, evidence)
    assert not decision.eligible
    assert "confirmation" in decision.reason


def test_matched_coordinates_are_required_for_sufficiency_witness() -> None:
    hypothesis, _ = build_problem()
    left = MatchedObservation(
        evidence_id="left",
        coordinates={"density": 1.0, "mean_velocity": 0.0, "variance": 1.0},
        outcome=-0.1,
    )
    right = MatchedObservation(
        evidence_id="right",
        coordinates={"density": 1.0, "mean_velocity": 0.0, "variance": 1.1},
        outcome=0.1,
    )
    witness = evaluate_predictive_sufficiency(hypothesis, left, right)
    assert not witness.coordinates_match
    assert not witness.falsifies
