from __future__ import annotations

import json
from pathlib import Path

import pytest

from conjecture_solver.mvp_claims import (
    ClaimDisposition,
    ClaimEvidenceContract,
    ClaimEvidenceProvenance,
    ClaimEvidenceValidationCheck,
    ClaimExecutionBinding,
    ClaimKind,
    ClaimRelation,
    EvidencePurpose,
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


def test_execution_binding_reserves_commissioning_command_from_science(
    tmp_path: Path,
) -> None:
    binding = ClaimExecutionBinding(
        capability="isolated-python",
        program_path="analyze.py",
        commissioning_argv=("analyze.py", "--output", "commissioning.json"),
        allowed_scientific_argv=(
            ("analyze.py", "--output", "commissioning.json"),
            ("analyze.py", "--output", "science.json"),
        ),
    )
    # Historical ledgers admitted before this invariant must remain readable.
    assert ClaimExecutionBinding.model_validate(binding.model_dump()).commissioning_argv == (
        "analyze.py",
        "--output",
        "commissioning.json",
    )
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A prospective analysis command produces valid evidence.",
    )
    with pytest.raises(ValueError, match="commissioning_argv is reserved"):
        store.register_evidence_contract(
            claim_id="claim_root",
            observable="A deterministic analysis result is recorded.",
            expected_outcomes="The scientific result differs from qualification.",
            decision_rule="The reported result decides the bounded claim.",
            required_observation="Run the prospectively bound analysis command.",
            uncertainty_criterion="The deterministic result is reported exactly.",
            inconclusive_conditions="A missing result remains inconclusive.",
            execution_binding=binding,
            iteration=1,
        )


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
        execution_stage="evidence",
        evidence_eligible=False,
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


def decision_contract_fields() -> dict[str, str]:
    return {
        "observable": "A prospective scalar observation from the attempted test.",
        "expected_outcomes": "One outcome supports and another outcome falsifies.",
        "decision_rule": "Apply the stated threshold to the prospective observation.",
        "required_observation": "At least one provenance-tracked attempted observation.",
        "uncertainty_criterion": "Report the numerical uncertainty with the observation.",
        "inconclusive_conditions": "A failed or incomplete observation is inconclusive.",
    }


def terminal_contract_fields() -> dict[str, str]:
    return {
        "observable": "A structured record of the terminal experimental limitation.",
        "expected_outcomes": "The record distinguishes unresolved from instrument-limited.",
        "decision_rule": "Use only the recorded limitation to choose a terminal status.",
        "required_observation": "One fresh provenance-tracked terminal record is required.",
        "uncertainty_criterion": "The record must state remaining scientific uncertainty.",
        "inconclusive_conditions": "Missing blocker details leave the claim open.",
    }


def failed_attempt_provenance(*, generated_iteration: int) -> ClaimEvidenceProvenance:
    return ClaimEvidenceProvenance(
        sha256="b" * 64,
        bytes=24,
        tracked=True,
        generated_iteration=generated_iteration,
        action="run_python",
        command_argv=("-c", "raise SystemExit(7)"),
        execution_succeeded=False,
        execution_returncode=7,
        evidence_eligible=True,
    )


def terminal_record_provenance(*, generated_iteration: int) -> ClaimEvidenceProvenance:
    return ClaimEvidenceProvenance(
        sha256="c" * 64,
        bytes=48,
        tracked=True,
        generated_iteration=generated_iteration,
        action="run_python",
        command_argv=("-c", "write_terminal_record()"),
        execution_succeeded=True,
        execution_returncode=0,
        evidence_eligible=True,
    )


def store_with_terminal_record(tmp_path: Path) -> MVPClaimLedgerStore:
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A prospective test decides this scientific hypothesis.",
    )
    store.register_evidence_contract(
        claim_id="claim_root",
        **decision_contract_fields(),
        iteration=1,
    )
    store.link_evidence(
        claim_id="claim_root",
        path="failed_attempt.json",
        note="The prospective test ran but did not produce a decisive observation.",
        observation_sufficient=False,
        observation_note="The execution failure is an attempted test, not a result.",
        provenance=failed_attempt_provenance(generated_iteration=2),
        iteration=2,
    )
    store.register_evidence_contract(
        claim_id="claim_root",
        evidence_purpose=EvidencePurpose.TERMINAL_RECORD,
        **terminal_contract_fields(),
        iteration=3,
    )
    store.link_evidence(
        claim_id="claim_root",
        path="terminal_record.json",
        note="This fresh record documents the terminal limitation.",
        observation_sufficient=True,
        observation_note="The terminal record satisfies its prospective contract.",
        provenance=terminal_record_provenance(generated_iteration=4),
        iteration=4,
    )
    return store


def test_old_evidence_contracts_default_to_claim_decision() -> None:
    contract = ClaimEvidenceContract.model_validate(
        {
            "version": 1,
            **decision_contract_fields(),
            "registered_iteration": 1,
        }
    )

    assert contract.evidence_purpose == EvidencePurpose.CLAIM_DECISION


def test_old_claim_ledger_without_evidence_purpose_remains_readable(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "claims.json"
    hypothesis = "A prospective test decides this scientific hypothesis."
    store = MVPClaimLedgerStore(ledger_path, root_hypothesis=hypothesis)
    store.register_evidence_contract(
        claim_id="claim_root",
        **decision_contract_fields(),
        iteration=1,
    )
    legacy = json.loads(ledger_path.read_text())
    legacy["schema_version"] = "0.9.0"
    del legacy["claims"][0]["evidence_contracts"][0]["evidence_purpose"]
    ledger_path.write_text(json.dumps(legacy))

    reloaded = MVPClaimLedgerStore(ledger_path, root_hypothesis=hypothesis)

    assert reloaded.ledger.schema_version == "0.9.0"
    assert (
        reloaded.ledger.claims[0].evidence_contracts[0].evidence_purpose
        == EvidencePurpose.CLAIM_DECISION
    )


def test_scientific_terminal_contract_requires_a_prior_linked_attempt(
    tmp_path: Path,
) -> None:
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A prospective test decides this scientific hypothesis.",
    )

    with pytest.raises(ValueError, match="requires at least one.*attempt"):
        store.register_evidence_contract(
            claim_id="claim_root",
            evidence_purpose=EvidencePurpose.TERMINAL_RECORD,
            **terminal_contract_fields(),
            iteration=1,
        )

    store.register_evidence_contract(
        claim_id="claim_root",
        **decision_contract_fields(),
        iteration=1,
    )
    store.link_evidence(
        claim_id="claim_root",
        path="failed_attempt.json",
        note="The prospective decision test was attempted and failed.",
        observation_sufficient=False,
        observation_note="This records an attempt, not scientific support.",
        provenance=failed_attempt_provenance(generated_iteration=2),
        iteration=2,
    )
    registered = store.register_evidence_contract(
        claim_id="claim_root",
        evidence_purpose=EvidencePurpose.TERMINAL_RECORD,
        **terminal_contract_fields(),
        iteration=3,
    )

    assert registered["registered_evidence_contract"]["evidence_purpose"] == "terminal_record"


def test_terminal_record_contract_is_rejected_for_non_scientific_claim(
    tmp_path: Path,
) -> None:
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A prospective test decides this scientific hypothesis.",
    )
    store.register(
        claim_id="claim_diagnostic",
        statement="The diagnostic resolves the proposed scientific observable.",
        kind=ClaimKind.DIAGNOSTIC,
        relation=ClaimRelation.DIAGNOSTIC_OF,
        parent_id="claim_root",
        rationale="The scientific test depends on this diagnostic.",
        iteration=1,
    )

    with pytest.raises(ValueError, match="only for scientific claims"):
        store.register_evidence_contract(
            claim_id="claim_diagnostic",
            evidence_purpose=EvidencePurpose.TERMINAL_RECORD,
            **terminal_contract_fields(),
            iteration=2,
        )


def test_workbench_artifact_does_not_unlock_scientific_terminal_record(
    tmp_path: Path,
) -> None:
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A prospective test decides this scientific hypothesis.",
    )
    store.register_evidence_contract(
        claim_id="claim_root",
        **decision_contract_fields(),
        iteration=1,
    )
    provenance = failed_attempt_provenance(generated_iteration=2).model_copy(
        update={"execution_stage": "workbench"}
    )
    store.link_evidence(
        claim_id="claim_root",
        path="workbench_failure.json",
        note="This was an exploratory workbench execution only.",
        observation_sufficient=False,
        observation_note="Workbench output is not a prospective test attempt.",
        provenance=provenance,
        iteration=2,
    )

    with pytest.raises(ValueError, match="requires at least one.*attempt"):
        store.register_evidence_contract(
            claim_id="claim_root",
            evidence_purpose=EvidencePurpose.TERMINAL_RECORD,
            **terminal_contract_fields(),
            iteration=3,
        )


@pytest.mark.parametrize(
    "status",
    [ClaimDisposition.SUPPORTED, ClaimDisposition.FALSIFIED],
)
def test_terminal_record_contract_cannot_decide_scientific_claim(
    tmp_path: Path,
    status: ClaimDisposition,
) -> None:
    store = store_with_terminal_record(tmp_path)

    with pytest.raises(ValueError, match="cannot support or falsify"):
        store.close(
            claim_id="claim_root",
            status=status,
            reason="A terminal record cannot decide the scientific proposition.",
            contract_version=2,
            iteration=5,
        )


@pytest.mark.parametrize(
    "status",
    [ClaimDisposition.INSTRUMENT_LIMITED, ClaimDisposition.UNRESOLVED],
)
def test_terminal_record_can_back_honest_terminal_disposition(
    tmp_path: Path,
    status: ClaimDisposition,
) -> None:
    store = store_with_terminal_record(tmp_path)

    result = store.close(
        claim_id="claim_root",
        status=status,
        reason="The terminal record is complete but does not decide the hypothesis.",
        contract_version=2,
        iteration=5,
    )

    assert result["decisive_contract_version"] == 2
    assert result["closed"]["decisive_contract_version"] == 2
    assert result["closed"]["status"] == status.value


def test_claim_decision_contract_cannot_back_unresolved_closure(tmp_path: Path) -> None:
    store = MVPClaimLedgerStore(
        tmp_path / "claims.json",
        root_hypothesis="A prospective test decides this scientific hypothesis.",
    )
    store.register_evidence_contract(
        claim_id="claim_root",
        **decision_contract_fields(),
        iteration=1,
    )

    with pytest.raises(ValueError, match="use a terminal_record contract"):
        store.close(
            claim_id="claim_root",
            status=ClaimDisposition.UNRESOLVED,
            reason="This request incorrectly treats a decision contract as terminal.",
            contract_version=1,
            iteration=2,
        )
