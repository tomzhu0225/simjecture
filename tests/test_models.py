from __future__ import annotations

import pytest
from pydantic import ValidationError

from conjecture_solver.benchmarks.kinetic_sufficiency import build_problem


def test_question_cannot_be_silently_stored_as_hypothesis() -> None:
    hypothesis, _ = build_problem()
    with pytest.raises(ValidationError, match="declarative"):
        hypothesis.model_copy(
            update={"statement": "Are low-order moments sufficient?"},
        ).__class__.model_validate(
            {
                **hypothesis.model_dump(),
                "statement": "Are low-order moments sufficient?",
            }
        )


def test_hypothesis_schema_forbids_unknown_fields() -> None:
    hypothesis, _ = build_problem()
    document = hypothesis.model_dump()
    document["silent_endpoint_change"] = True
    with pytest.raises(ValidationError, match="Extra inputs"):
        hypothesis.__class__.model_validate(document)


def test_formal_predicate_must_match_evidence_contract() -> None:
    hypothesis, _ = build_problem()
    document = hypothesis.model_dump(mode="json")
    document["formal_predicate"]["maximum_outcome_difference"] = 0.03
    with pytest.raises(ValidationError, match="tolerance must match"):
        hypothesis.__class__.model_validate(document)
