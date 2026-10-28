import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from simjecture_monitor import attention_support as protocol
from simjecture_monitor.synthetic_attention import generate, make_observation, scripted_preference


def encode(packet, **changes):
    return protocol.pack(
        packet, len, token_counter_id="test:characters", budget_tokens=100_000, **changes
    )


def proposal(packet, view, *, action="recheck", support="knowledge_lookup", question="q0"):
    return protocol.bind_choice(
        packet,
        view,
        protocol.Choice(
            action=action,
            support_kind=support,
            question_ref=question,
            basis="missing",
            evidence=["e0"],
        ),
        policy_id="conformance",
    )


def evaluate(gate, packet, **changes):
    view = encode(packet)
    return gate.evaluate(
        packet, view, proposal(packet, view, **changes), packet, now_ms=packet.captured_ms
    )


def advance(packet, **changes):
    return protocol.Observation.model_validate(
        packet.model_dump()
        | dict(
            packet_id=packet.packet_id + "x",
            sequence=packet.sequence + 1,
            captured_ms=packet.captured_ms + 5000,
        )
        | changes
    )


@pytest.mark.parametrize(
    "scenario,reason",
    [
        ("lookup_active", "question_investigation_active"),
        ("literature_active", "question_investigation_active"),
        ("lookup_recent_no_match", "recent_support_result_available"),
        ("lookup_recent_matches", "recent_support_result_available"),
        ("lookup_failed_cooldown", "retrieval_retry_cooldown"),
        ("question_resolved", "question_already_resolved"),
        ("lookup_stale", "policy_choice"),
        ("lookup_context_changed", "policy_choice"),
    ],
)
def test_support_reuse_depends_on_scope_freshness_and_investigation_state(scenario, reason):
    assert evaluate(protocol.AdmissionGate(), make_observation(1, scenario))["reason"] == reason


def test_recent_search_allows_interpretation_or_review_but_not_repeating_the_search():
    packet = make_observation(1, "lookup_recent_matches")
    assert (
        evaluate(protocol.AdmissionGate(), packet, action="request_worker_help")["reason"]
        == "awaiting_persistence"
    )
    packet = make_observation(1, "lookup_recent_no_match")
    assert (
        evaluate(
            protocol.AdmissionGate(),
            packet,
            action="request_worker_help",
            support="literature_review",
        )["reason"]
        == "awaiting_persistence"
    )
    packet = make_observation(1, "literature_recent")
    assert (
        evaluate(
            protocol.AdmissionGate(), packet, action="wake_director", support="literature_review"
        )["reason"]
        == "recent_support_result_available"
    )


def test_unknown_history_and_closed_workflows_cannot_trigger_a_lookup():
    packet = make_observation(1, "lookup_needed")
    packet.retrieval_history_complete = False
    assert evaluate(protocol.AdmissionGate(), packet)["reason"] == "retrieval_context_unknown"
    packet.retrieval_history_complete = True
    packet.workflow_state = "complete"
    assert evaluate(protocol.AdmissionGate(), packet)["reason"] == "workflow_closed"
    packet.workflow_state = "running"
    packet.assistance = "unknown"
    assert evaluate(protocol.AdmissionGate(), packet)["reason"] == "required_state_unknown"


def test_context_changes_invalidate_inflight_requests_even_before_revision_update():
    packet = make_observation(1, "lookup_needed")
    view = encode(packet)
    current = advance(packet)
    current.questions[0].context_sha256 = "f" * 64
    assert (
        protocol.AdmissionGate().evaluate(
            packet, view, proposal(packet, view), current, now_ms=current.captured_ms
        )["reason"]
        == "question_context_changed"
    )


def test_recovery_interrupts_support_persistence_and_real_dispatch_is_shared_across_routes():
    gate = protocol.AdmissionGate()
    first = make_observation(1, "lookup_recent_no_match")
    request = dict(action="request_worker_help", support="literature_review")
    assert evaluate(gate, first, **request)["disposition"] == "pending"
    second = advance(first)
    assert (
        evaluate(gate, second, action="observe", support="none", question=None)["disposition"]
        == "observe"
    )
    third = advance(second)
    assert evaluate(gate, third, **request)["disposition"] == "pending"
    fourth = advance(third)
    assert evaluate(gate, fourth, **request)["disposition"] == "admitted"
    gate.record_dispatch(fourth)
    assert (
        evaluate(gate, advance(fourth), action="wake_director")["reason"]
        == "incident_already_dispatched"
    )


def test_different_questions_do_not_combine_confirmations():
    packet = make_observation(1, "lookup_needed")
    second_question = packet.questions[0].model_copy(update={"id": "other-question"})
    packet.questions.append(second_question)
    gate = protocol.AdmissionGate()
    assert evaluate(gate, packet, action="request_worker_help")["disposition"] == "pending"
    later = advance(packet)
    assert (
        evaluate(gate, later, action="request_worker_help", question="q1")["disposition"]
        == "pending"
    )
    assert (
        evaluate(gate, advance(later), action="request_worker_help", question="q0")["disposition"]
        == "pending"
    )


def test_retrieval_evidence_is_pinned_and_model_aliases_cannot_invent_questions():
    packet = make_observation(1, "lookup_recent_no_match")
    packet.evidence[-1].required = False
    view = protocol.pack(packet, len, token_counter_id="test:characters", budget_tokens=10)
    assert view.status == "insufficient_budget"
    assert packet.retrieval_history[0].evidence_ids[0] in view.included_ids
    with pytest.raises(ValueError, match="ready view"):
        proposal(packet, view)
    view = encode(packet)
    with pytest.raises(ValueError, match="Unknown model question"):
        proposal(packet, view, question="q9")
    with pytest.raises(ValidationError, match="compatible action"):
        proposal(packet, view, action="request_repair_judge")
    with pytest.raises(ValidationError, match="result receipt"):
        protocol.Retrieval.model_validate(
            packet.retrieval_history[0].model_dump() | {"evidence_ids": []}
        )


def test_curriculum_groups_do_not_leak_and_labels_are_not_rl_outcomes():
    rows = list(generate(30))
    assert len(rows) == 480
    groups = {}
    for row in rows:
        assert groups.setdefault(row["group_id"], row["split"]) == row["split"]
        assert hashlib.sha256(row["input_text"].encode()).hexdigest() == row["input_sha256"]
        assert row["supervision"]["utility_label"] is None
        assert row["supervision"]["behavior_probability"] is None
        assert not row["supervision"]["rollout_validated"]
        assert row["provenance"]["mechanism"] not in row["input_text"]
        assert row["group_id"] not in row["input_text"]
        assert "scripted_preference" not in row["input_text"]
        packet = protocol.Observation.model_validate(row["observation"])
        view = encode(packet)
        protocol.bind_choice(
            packet, view, protocol.Choice.model_validate(row["target"]), policy_id="test"
        )
    assert {row["split"] for row in rows} == {"train", "validation", "synthetic_audit"}
    assert rows == list(generate(30))


def test_quiet_near_miss_and_real_silence_have_distinct_scripted_preferences():
    for scenario in ("quiet_active", "quiet_just_ended", "persistent_silence"):
        packet = make_observation(1, scenario)
        choice = scripted_preference(packet, encode(packet))
        assert choice.action == (
            "request_worker_help" if scenario == "persistent_silence" else "observe"
        )


def load_script(name):
    path = Path(__file__).parents[1] / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_records_actual_file_hashes_and_refuses_overwrite(tmp_path):
    build = load_script("build_attention_curriculum").build
    output = tmp_path / "curriculum"
    report = build(output, groups=3, seed=1)
    assert report["rows"] == 48 and report["groups"] == 3
    for name, expected in report["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    assert report["exact_duplicate_inputs"] == report["conflicting_targets"] == 0
    with pytest.raises(FileExistsError):
        build(output, groups=3, seed=1)


def test_separate_v02_exports_match_source_and_example_bindings():
    folder = Path(__file__).parents[1] / "specs/scientific-attention-0.2-draft"
    for name, value in load_script("export_attention_support").exports().items():
        stored = (folder / name).read_text()
        assert (stored if isinstance(value, str) else json.loads(stored)) == value
