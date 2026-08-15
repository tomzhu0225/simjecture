from __future__ import annotations

from conjecture_solver.mvp_claims import (
    ClaimEvidenceValidationCheck,
    MVPClaimLedgerStore,
)


def evaluate(actual: object, expected: object) -> bool:
    passed, results = MVPClaimLedgerStore._evaluate_validation_checks(
        (
            ClaimEvidenceValidationCheck(
                json_path="value",
                expected_value=expected,
            ),
        ),
        evidence_document={"value": actual},
        evidence_document_error=None,
    )
    assert len(results) == 1
    assert results[0].passed is passed
    return bool(passed)


def test_machine_validation_accepts_equivalent_json_numeric_types() -> None:
    assert evaluate(25.0, 25)
    assert evaluate(25, 25.0)


def test_machine_validation_does_not_treat_booleans_as_numbers() -> None:
    assert not evaluate(True, 1)
    assert not evaluate(1, True)


def test_machine_validation_keeps_non_numeric_scalars_type_strict() -> None:
    assert evaluate("25", "25")
    assert not evaluate("25", 25)
    assert evaluate(None, None)
