from __future__ import annotations

from pathlib import Path

import pytest

from conjecture_solver.mvp_claims import (
    ClaimEvidenceProvenance,
    ClaimEvidenceValidationCheck,
    ClaimExecutionBinding,
    ClaimKind,
    ClaimRelation,
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


def test_bound_partial_instrument_contract_is_rejected_at_registration(
    tmp_path: Path,
) -> None:
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A commissioned analyzer produces valid evidence.",
    )
    store.register(
        claim_id="claim_analyzer",
        statement="The analyzer is commissioned for the scientific pipeline.",
        kind=ClaimKind.INSTRUMENT,
        relation=ClaimRelation.INSTRUMENT_OF,
        parent_id="claim_root",
        rationale="Scientific analysis requires a qualified frozen program.",
        iteration=1,
    )
    binding = ClaimExecutionBinding(
        capability="isolated-python",
        program_path="analyze.py",
        commissioning_argv=("analyze.py", "commission"),
        allowed_scientific_argv=(("analyze.py", "science"),),
    )

    with pytest.raises(ValueError, match="missing required aspects"):
        store.register_evidence_contract(
            claim_id="claim_analyzer",
            observable="A deterministic analyzer commissioning summary.",
            expected_outcomes="Passing checks qualify the analyzer program.",
            decision_rule="Support only when every registered check passes.",
            required_observation="Run the frozen analyzer commissioning command.",
            uncertainty_criterion="Every check is an exact JSON boolean.",
            inconclusive_conditions="A missing check leaves commissioning open.",
            validation_checks=(
                ClaimEvidenceValidationCheck(
                    aspect="diagnostics",
                    json_path="checks.diagnostics_valid",
                    expected_value=True,
                ),
                ClaimEvidenceValidationCheck(
                    aspect="numerical_regime",
                    json_path="checks.numerics_valid",
                    expected_value=True,
                ),
            ),
            execution_binding=binding,
            iteration=2,
        )

    registered = store.register_evidence_contract(
        claim_id="claim_analyzer",
        observable="A deterministic interface discovery summary.",
        expected_outcomes="A true interface check permits later commissioning.",
        decision_rule="Support interface discovery only when the check is true.",
        required_observation="Run the frozen interface discovery command.",
        uncertainty_criterion="The interface check is an exact JSON boolean.",
        inconclusive_conditions="A missing check leaves discovery unresolved.",
        validation_checks=(
            ClaimEvidenceValidationCheck(
                aspect="interface",
                json_path="checks.interface_valid",
                expected_value=True,
            ),
        ),
        execution_binding=binding,
        iteration=3,
    )
    assert registered["registered_evidence_contract"]["version"] == 1


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
