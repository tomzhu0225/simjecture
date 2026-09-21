from __future__ import annotations

import json

import pytest

from conjecture_solver.evidence_paths import evidence_path_parts, evidence_value
from conjecture_solver.research_client import ResearchClient


def client(tmp_path):
    p = tmp_path / "binding.json"
    p.write_text(json.dumps(dict(role="researcher", claim_id="claim_root", assignment_id="test-1")))
    return ResearchClient(p)


def test_bookkeeping_is_host_owned_replay_safe_and_claim_explicit(tmp_path):
    c = client(tmp_path)
    args = {"argv": ["measure.py"], "input_artifacts": []}
    first = c.prepare("run_python", args)
    assert first["operation_id"].startswith("test-1:client-")
    assert first["active_claim_id"] == "claim_root"
    assert first == c.prepare("run_python", args)
    assert (
        first["operation_id"]
        != c.prepare("run_python", args, request_key="replicate-2")["operation_id"]
    )
    assert (
        c.prepare("run_python", {**args, "active_claim_id": "claim_repair"})["active_claim_id"]
        == "claim_repair"
    )
    assert args == {"argv": ["measure.py"], "input_artifacts": []}
    assert "input_artifacts" not in c.prepare("run_python", {"argv": ["measure.py"]})


def test_client_cannot_approve_or_finalize(tmp_path):
    c = client(tmp_path)
    for tool in ["record_adjudication", "finalize_campaign"]:
        with pytest.raises(ValueError):
            c.prepare(tool, {})
    result = c.request_review("contract")
    assert result["decision"] == "pending"
    with pytest.raises(ValueError):
        c.request_review("contract", "claim_other")


@pytest.mark.parametrize("path", ["rows.0.N", "rows[0].N", "$.rows[0].N"])
def test_equivalent_array_paths(path):
    assert evidence_value({"rows": [{"N": 16}]}, path) == 16


def test_object_numeric_keys_stay_object_keys():
    assert evidence_value({"rows": {"0": {"N": 16}}}, "rows.0.N") == 16


@pytest.mark.parametrize(
    "path", ["rows[-1].N", "rows[*].N", "rows[0:2].N", "rows[1+1].N", "rows..N"]
)
def test_no_wildcards_expressions_or_negative_indices(path):
    with pytest.raises(ValueError):
        evidence_path_parts(path)


def test_missing_and_non_scalar_paths_are_not_fabricated():
    with pytest.raises(KeyError):
        evidence_value({"rows": []}, "rows[0].N")
    assert evidence_value({"rows": [{"N": 16}]}, "rows") == [{"N": 16}]


def test_run_identity_tracks_program_and_contract_revision(tmp_path, monkeypatch):
    c = client(tmp_path)
    current = {"sha": "a" * 64, "version": 1}
    ids = []

    def call(tool, args, request_key=None):
        if tool == "claims":
            return {"claims": [{"evidence_contracts": [{"version": current["version"]}]}]}
        if tool == "read_workspace_file":
            return {"sha256": current["sha"]}
        prepared = c.prepare(tool, args, request_key=request_key)
        ids.append(prepared["operation_id"])
        return prepared

    monkeypatch.setattr(c, "call", call)
    c.run_python(["measurement.py"], inputs=[])
    c.run_python(["measurement.py"], inputs=[])
    assert ids[-1] == ids[-2]
    current["sha"] = "b" * 64
    c.run_python(["measurement.py"], inputs=[])
    assert ids[-1] != ids[-2]
    current["version"] = 2
    c.run_python(["measurement.py"], inputs=[])
    assert ids[-1] != ids[-2]


def test_kernel_validation_checks_support_array_paths_without_type_coercion():
    from conjecture_solver.mvp_claims import ClaimEvidenceValidationCheck, MVPClaimLedgerStore

    checks = tuple(
        ClaimEvidenceValidationCheck(json_path=path, expected_value=16)
        for path in ["rows[0].N", "$.rows[0].N", "rows.0.N"]
    )
    passed, results = MVPClaimLedgerStore._evaluate_validation_checks(
        checks, evidence_document={"rows": [{"N": 16}]}, evidence_document_error=None
    )
    assert passed is True
    assert all(r.passed for r in results)
    bad = (ClaimEvidenceValidationCheck(json_path="rows[0].N", expected_value=True),)
    passed, _ = MVPClaimLedgerStore._evaluate_validation_checks(
        bad, evidence_document={"rows": [{"N": 1}]}, evidence_document_error=None
    )
    assert passed is False


def test_design_approval_can_suggest_execution_but_cannot_retain_required_gaps():
    from conjecture_solver.scientific_review import ReviewVerdict

    approved = ReviewVerdict(
        decision="approved",
        rationale="The prospective finite-domain test is adequate.",
        evidence_gaps=[],
        next_test="Execute the approved test design.",
    )
    assert approved.decision == "approved"
    with pytest.raises(ValueError):
        ReviewVerdict(
            decision="approved",
            rationale="The prospective finite-domain test is adequate.",
            evidence_gaps=["Missing domain coverage"],
            next_test="Run more cases",
        )
