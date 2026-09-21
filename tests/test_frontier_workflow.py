from __future__ import annotations

import argparse
import json

import pytest

from conjecture_solver.agent_supervisor import AgentSupervisor, parse_judge_stream
from conjecture_solver.role_assignments import AssignmentStore


def researcher(tmp_path):
    store = AssignmentStore(tmp_path)
    record = store.issue(
        dict(
            assignment_id="research-1",
            agent_id="glm",
            role="researcher",
            claim_id="claim_root",
            max_operations=80,
        )
    )
    return store, record


def test_researcher_can_register_repair_and_test_it_without_role_change(tmp_path):
    store, record = researcher(tmp_path)
    args = dict(
        operation_id="research-1:repair",
        claim_id="claim_repair",
        parent_id="claim_root",
        kind="scientific",
        relation="repairs",
        repair={},
    )
    store.authorize(record, "register_claim", args)
    op = store.reserve(record, "register_claim", args)
    store.completed(record, op, "register_claim", args, {"claim": {"id": "claim_repair"}})
    store.authorize(record, "run_python", {"active_claim_id": "claim_repair"})
    store.authorize(record, "register_evidence_contract", {"claim_id": "claim_repair"})
    assert record["spec"]["role"] == "researcher"


@pytest.mark.parametrize(
    "name,args",
    [
        ("record_adjudication", {}),
        ("finalize_campaign", {}),
        (
            "register_claim",
            {"claim_id": "claim_other", "parent_id": "foreign", "kind": "scientific"},
        ),
        ("run_python", {"active_claim_id": "foreign"}),
        ("close_claim", {"claim_id": "claim_root", "status": "supported"}),
    ],
)
def test_researcher_does_not_gain_approval_or_unrelated_claim_authority(tmp_path, name, args):
    store, record = researcher(tmp_path)
    with pytest.raises(ValueError):
        store.authorize(record, name, args)


def test_codex_judge_requires_completed_tool_free_turn(tmp_path):
    path = tmp_path / "trace.jsonl"
    events = [
        {"type": "thread.started", "thread_id": "example"},
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": '{"decision":"rejected"}'},
        },
        {"type": "turn.completed"},
    ]
    path.write_text("\n".join(map(json.dumps, events)))
    assert parse_judge_stream(path, "codex-glm")["decision"] == "rejected"
    events.insert(
        1, {"type": "item.started", "item": {"type": "command_execution", "command": "cat file"}}
    )
    path.write_text("\n".join(map(json.dumps, events)))
    with pytest.raises(ValueError, match="used a tool"):
        parse_judge_stream(path, "codex-glm")


def test_frontier_resume_prompt_does_not_repeat_operator_packet(tmp_path):
    root = tmp_path / "campaign"
    root.mkdir()
    instruction = tmp_path / "task"
    instruction.write_text("UNIQUE_LONG_OPERATOR_PACKET")
    supervisor = AgentSupervisor(
        argparse.Namespace(
            campaign=root,
            state_dir=tmp_path / "state",
            workflow="frontier",
            wall_seconds=60,
            instructions_file=instruction,
        )
    )
    spec = dict(claim_id="claim_root", assignment_id="research-1")
    initial = supervisor.researcher_prompt(tmp_path, spec, tmp_path / "kernel_call.py")
    supervisor.state["worker_cursor"] = "existing-session"
    resumed = supervisor.researcher_prompt(tmp_path, spec, tmp_path / "kernel_call.py")
    assert "UNIQUE_LONG_OPERATOR_PACKET" in initial
    assert "UNIQUE_LONG_OPERATOR_PACKET" not in resumed
    assert "do not restart orientation" in resumed
    assert "cannot approve your own result" in resumed


def test_review_request_survives_boundary_and_is_processed_before_resume(tmp_path, monkeypatch):
    root = tmp_path / "campaign"
    root.mkdir()
    store, record = researcher(root)
    args = argparse.Namespace(
        campaign=root, state_dir=tmp_path / "state", workflow="frontier", wall_seconds=60
    )
    supervisor = AgentSupervisor(args)
    research = tmp_path / "research"
    research.mkdir()
    request = {"claim_id": "claim_root"}
    (research / "contract-review-request.json").write_text(json.dumps(request))
    supervisor.enqueue_reviews(research, record)
    calls = []
    monkeypatch.setattr(supervisor, "review", lambda directory, record: calls.append(directory))
    supervisor.cancelled = True
    supervisor.pending_reviews()
    assert not calls
    assert not list((supervisor.directory / "review-queue").rglob("resolution.json"))
    supervisor.cancelled = False
    supervisor.pending_reviews()
    assert len(calls) == 1
    assert json.loads((calls[0] / "contract-review-request.json").read_text()) == request
    assert (calls[0] / "resolution.json").exists()
    supervisor.pending_reviews()
    assert len(calls) == 1
