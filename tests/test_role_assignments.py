from __future__ import annotations

import pytest

from conjecture_solver.role_assignments import AssignmentStore


def issued(tmp_path, role="falsifier", budget=3):
    store = AssignmentStore(tmp_path)
    record = store.issue(
        {
            "assignment_id": "experiment-1",
            "agent_id": "grok-bot",
            "role": role,
            "claim_id": "claim_root",
            "max_operations": budget,
        }
    )
    return store, record


@pytest.mark.parametrize(
    "name,args",
    [
        ("record_adjudication", {}),
        ("finalize_campaign", {}),
        ("close_claim", {"claim_id": "claim_root", "status": "supported"}),
        ("register_evidence_contract", {"claim_id": "claim_other"}),
        (
            "register_claim",
            {"claim_id": "claim_child", "parent_id": "claim_root", "kind": "scientific"},
        ),
        ("run_python", {"active_claim_id": "claim_other"}),
        ("run_python", {}),
        ("claims", {"view": "full"}),
        ("cancel_job", {"job_id": "foreign-job"}),
    ],
)
def test_falsifier_cannot_escape_assignment(tmp_path, name, args):
    store, record = issued(tmp_path)
    with pytest.raises(ValueError):
        store.authorize(record, name, args)


def test_restart_preserves_identity_budget_and_exact_replay(tmp_path):
    store, record = issued(tmp_path, budget=1)
    args = {"operation_id": "experiment-1:write", "path": "test.py", "content": "x=1"}
    operation = store.reserve(record, "write_workspace_file", args)
    assert operation == "experiment-1:write"
    recovered = AssignmentStore(tmp_path)
    record = recovered.bind("experiment-1", "grok-bot", "fresh-session")
    assert recovered.reserve(record, "write_workspace_file", args) == operation
    with pytest.raises(ValueError, match="different arguments"):
        recovered.reserve(record, "write_workspace_file", {**args, "content": "x=2"})
    with pytest.raises(ValueError, match="budget"):
        recovered.reserve(
            record, "write_workspace_file", {**args, "operation_id": "experiment-1:new"}
        )
    with pytest.raises(ValueError, match="does not belong"):
        recovered.bind("experiment-1", "another-bot", "another-session")
    with pytest.raises(ValueError, match="immutable"):
        recovered.issue({**record["spec"], "agent_id": "another-bot"})


def test_repair_cannot_contract_parent_or_create_two_children(tmp_path):
    store, record = issued(tmp_path, "repair_scientist")
    with pytest.raises(ValueError, match="registered child"):
        store.authorize(record, "register_evidence_contract", {"claim_id": "claim_root"})
    child = {
        "claim_id": "claim_repair",
        "parent_id": "claim_root",
        "kind": "scientific",
        "relation": "repairs",
        "repair": {},
        "operation_id": "experiment-1:repair",
    }
    store.authorize(record, "register_claim", child)
    operation = store.reserve(record, "register_claim", child)
    store.completed(record, operation, "register_claim", child, {"claim": {"id": "claim_repair"}})
    recovered = AssignmentStore(tmp_path)
    record = recovered.bind("experiment-1", "grok-bot", "resumed-session")
    recovered.authorize(record, "register_evidence_contract", {"claim_id": "claim_repair"})
    with pytest.raises(ValueError, match="one repairs child"):
        recovered.authorize(record, "register_claim", {**child, "claim_id": "claim_second"})


def test_handoff_needs_kernel_state_and_is_immutable(tmp_path):
    store, record = issued(tmp_path)
    result = {
        "assignment_id": "experiment-1",
        "claim_id": "claim_root",
        "outcome": "falsified",
        "evidence_paths": ["evidence.json"],
        "next_test": None,
    }
    claim = {"id": "claim_root", "status": "open", "evidence": [{"path": "evidence.json"}]}
    with pytest.raises(ValueError, match="kernel-accepted"):
        store.handoff(record, result, [claim])
    claim["status"] = "falsified"
    assert store.handoff(record, result, [claim]) == result
    with pytest.raises(ValueError, match="ended"):
        store.authorize(record, "write_workspace_file", {})
    store.authorize(record, "snapshot", {})
    with pytest.raises(ValueError, match="immutable"):
        store.handoff(record, {**result, "outcome": "inconclusive"}, [claim])


def test_judge_has_no_scientific_tools(tmp_path):
    store, record = issued(tmp_path, "judge")
    for name in ("snapshot", "read_workspace_file", "record_adjudication"):
        with pytest.raises(ValueError, match="judge cannot"):
            store.authorize(record, name, {})
