from __future__ import annotations

import pytest

from conjecture_solver.campaign_kernel import CampaignKernel
from conjecture_solver.mvp_agent import MVPAgentConfig, parse_mvp_action
from conjecture_solver.scientific_review import ScientificReviews


def setup_case(tmp_path, checks=()):
    kernel = CampaignKernel.open(
        workspace=tmp_path / "campaign",
        hypothesis="Every one of 18 cases meets the tolerance.",
        config=MVPAgentConfig(require_independent_contract_review=True),
    )
    kernel.claim_store.register_evidence_contract(
        claim_id="claim_root",
        observable="Onset timing with bounding separatrix and persistence.",
        expected_outcomes="Observed onset differences with uncertainty in all cases.",
        decision_rule="Support only all cases within tolerance; one decisive case can falsify.",
        required_observation="Fresh qualified measurements for the finite matrix.",
        uncertainty_criterion="Spatial and temporal uncertainty smaller than the tolerance.",
        inconclusive_conditions="Censored events cannot establish timing agreement.",
        validation_checks=checks,
        iteration=1,
    )
    return kernel, ScientificReviews(kernel.host)


def verdict(decision="approved"):
    return dict(
        decision=decision,
        rationale="Independent review of the actual contract and scope.",
        evidence_gaps=[] if decision == "approved" else ["Missing boundary validation"],
        next_test=None if decision == "approved" else "Validate physical boundary fluxes",
    )


def test_unreviewed_execution_blocked_and_workbench_allowed(tmp_path):
    _, reviews = setup_case(tmp_path)
    action = parse_mvp_action(
        '{"action":"run_python","research_note":"test", "argv":["test.py"],'
        '"active_claim_id":"claim_root","input_artifacts":[]}'
    )
    with pytest.raises(ValueError, match="Independent contract review required"):
        reviews.guard(action)
    workbench = parse_mvp_action(
        '{"action":"run_capability","research_note":"test","capability":"flash","stage":"workbench","argv":["test.py"],'
        '"active_claim_id":"claim_root","input_artifacts":[]}'
    )
    reviews.guard(workbench)
    packet = reviews.packet("claim_root", "contract")
    reviews.record(packet, verdict(), reviewer="independent", transcript_sha256="a" * 64)
    reviews.guard(action)


def test_scope_or_contract_changes_invalidate_approval(tmp_path):
    k, reviews = setup_case(tmp_path)
    packet = reviews.packet("claim_root", "contract")
    reviews.record(packet, verdict(), reviewer="independent", transcript_sha256="a" * 64)
    contract = k.claim_store.ledger.by_id()["claim_root"].evidence_contracts[-1]
    # In-memory adversarial change exercises digest binding, independent of ledger immutability.
    object.__setattr__(contract, "decision_rule", "Support all 18 cases using only one case.")
    with pytest.raises(ValueError, match="Independent contract review required"):
        reviews.require("claim_root", "contract")
    with pytest.raises(ValueError, match="case changed"):
        reviews.record(packet, verdict(), reviewer="independent", transcript_sha256="a" * 64)


def test_metadata_labels_cannot_be_approved(tmp_path):
    from conjecture_solver.mvp_claims import ClaimEvidenceValidationCheck

    checks = (
        ClaimEvidenceValidationCheck(
            aspect="boundaries", json_path="stage", expected_value="commissioning"
        ),
    )
    _, reviews = setup_case(tmp_path, checks)
    packet = reviews.packet("claim_root", "contract")
    assert packet["deterministic_issues"]
    with pytest.raises(ValueError, match="metadata-only"):
        reviews.record(packet, verdict(), reviewer="independent", transcript_sha256="a" * 64)
    reviews.record(packet, verdict("rejected"), reviewer="independent", transcript_sha256="b" * 64)
    with pytest.raises(ValueError, match="Independent contract review required"):
        reviews.require("claim_root", "contract")


def test_qualification_requires_actual_linked_evidence(tmp_path):
    k, reviews = setup_case(tmp_path)
    k.claim_store.register(
        claim_id="claim_instrument",
        statement="Instrument accurately measures onset.",
        kind="instrument",
        relation="instrument_of",
        parent_id="claim_root",
        rationale="Qualification",
        iteration=2,
    )
    # No contract or linked output is never a qualified instrument.
    with pytest.raises(ValueError, match="proposed contract"):
        reviews.packet("claim_instrument", "qualification")


def test_kernel_blocks_unreviewed_action_before_execution(tmp_path, monkeypatch):
    k, _ = setup_case(tmp_path)
    monkeypatch.setattr(k.host, "_enforce_literature_startup", lambda action: None)
    called = []
    monkeypatch.setattr(k.host, "_perform_compat", lambda *args, **kwargs: called.append(True))
    action = parse_mvp_action(
        '{"action":"run_python","research_note":"attempt unapproved execution",'
        '"argv":["test.py"],"active_claim_id":"claim_root","input_artifacts":[]}'
    )
    with pytest.raises(ValueError, match="Independent contract review required"):
        k._run_host_action(action, iteration=2, timeout_seconds=1)
    assert called == []


def test_approval_cannot_be_reused_for_changed_program(tmp_path):
    import hashlib

    from conjecture_solver.mvp_claims import ClaimExecutionBinding

    k, reviews = setup_case(tmp_path)
    source = 'print("measured quantity")'
    k.host.sandbox.write_file("measurement.py", source)
    binding = ClaimExecutionBinding(
        capability="private-flash",
        program_path="measurement.py",
        program_sha256=hashlib.sha256(source.encode()).hexdigest(),
        commissioning_argv=("measurement.py",),
        allowed_scientific_argv=(("measurement.py", "science"),),
    )
    contract = k.claim_store.ledger.by_id()["claim_root"].evidence_contracts[-1]
    object.__setattr__(contract, "execution_binding", binding)
    packet = reviews.packet("claim_root", "contract")
    reviews.record(packet, verdict(), reviewer="independent", transcript_sha256="a" * 64)
    k.host.sandbox.write_file("measurement.py", 'print("fabricated quantity")')
    with pytest.raises(ValueError, match="program hash"):
        reviews.require("claim_root", "contract")


def test_worker_has_no_review_approval_tool():
    from conjecture_solver.role_assignments import ROLE_TOOLS

    for role in ["falsifier", "repair_scientist", "blocker_resolver"]:
        assert not any(
            "approve" in name or "record_adjudication" in name for name in ROLE_TOOLS[role]
        )


def test_instrument_cannot_close_on_contract_approval_alone(tmp_path, monkeypatch):
    k, reviews = setup_case(tmp_path)
    # Even an approved prospective design is not approval of its measured results.
    item = k.claim_store.ledger.by_id()["claim_root"]
    from conjecture_solver.mvp_claims import ClaimKind

    object.__setattr__(item, "kind", ClaimKind.INSTRUMENT)
    called = []

    def require(claim_id, stage):
        called.append(stage)
        if stage == "qualification":
            raise ValueError("Independent qualification review required")

    monkeypatch.setattr(reviews, "require", require)
    action = parse_mvp_action(
        '{"action":"close_claim","research_note":"attempt premature closure",'
        '"claim_id":"claim_root","status":"supported","reason":"execution passed"}'
    )
    with pytest.raises(ValueError, match="qualification review"):
        reviews.guard(action)
    assert called == ["contract", "qualification"]
