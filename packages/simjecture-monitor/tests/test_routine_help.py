from simjecture_monitor import attention_support as protocol
from simjecture_monitor.routine_help import RoutineHelpPolicy
from test_workflow_attention import packet, raw


def decision(observed):
    view = protocol.pack(observed, len, token_counter_id="test:characters", budget_tokens=100000)
    choice = RoutineHelpPolicy().predict(observed, view)
    return view, protocol.bind_choice(observed, view, choice, policy_id="routine-help-test")


def test_routine_help_uses_the_same_persistence_and_duplicate_admission():
    first = packet(raw())  # A progressing workflow with no identified anomaly.
    view, proposed = decision(first)
    assert proposed.action == "request_worker_help"
    gate = protocol.AdmissionGate()
    assert gate.evaluate(first, view, proposed, first, now_ms=first.captured_ms)["reason"] == (
        "awaiting_persistence"
    )
    second = first.model_copy(update={"packet_id": "second", "sequence": 2, "captured_ms": 106000})
    view, proposed = decision(second)
    assert gate.evaluate(second, view, proposed, second, now_ms=106000)["disposition"] == "admitted"
    gate.record_dispatch(second)
    third = second.model_copy(update={"packet_id": "third", "sequence": 3, "captured_ms": 112000})
    view, proposed = decision(third)
    assert gate.evaluate(third, view, proposed, third, now_ms=112000)["reason"] == (
        "incident_already_dispatched"
    )


def test_routine_request_cannot_bypass_closed_workflow_or_existing_assistance():
    observed = packet(raw())
    view, proposed = decision(observed)
    gate = protocol.AdmissionGate()
    closed = observed.model_copy(update={"workflow_state": "complete"})
    assert gate.evaluate(observed, view, proposed, closed, now_ms=closed.captured_ms)["reason"] == (
        "workflow_closed"
    )
    pending = observed.model_copy(update={"assistance": "pending"})
    assert gate.evaluate(observed, view, proposed, pending, now_ms=pending.captured_ms)[
        "reason"
    ] == ("same_incident_already_served")
