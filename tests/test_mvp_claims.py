from __future__ import annotations

from pathlib import Path

import pytest

from conjecture_solver.mvp_claims import (
    ClaimEvidenceProvenance,
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


def test_failed_python_artifact_cannot_be_sufficient_scientific_evidence(
    tmp_path: Path,
) -> None:
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A failed execution cannot prove its own output.",
    )
    store.register_evidence_contract(
        claim_id="claim_root",
        observable="A scalar written by the scientific program.",
        expected_outcomes="One supports and zero falsifies.",
        decision_rule="Use the scalar only after a successful execution.",
        required_observation="One provenance-tracked program result.",
        uncertainty_criterion="The deterministic value has no sampling error.",
        inconclusive_conditions="A failed execution is inconclusive.",
        iteration=1,
    )
    provenance = ClaimEvidenceProvenance(
        sha256="a" * 64,
        bytes=12,
        tracked=True,
        generated_iteration=2,
        action="run_python",
        command_argv=("-c", "raise SystemExit(7)"),
        execution_succeeded=False,
        execution_returncode=7,
        evidence_eligible=True,
    )
    with pytest.raises(ValueError, match="successful execution"):
        store.link_evidence(
            claim_id="claim_root",
            path="partial.json",
            note="The process wrote this before failing.",
            observation_sufficient=True,
            observation_note="It must remain non-evidence.",
            provenance=provenance,
            iteration=3,
        )
