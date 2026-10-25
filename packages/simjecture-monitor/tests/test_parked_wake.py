from simjecture_monitor.parked_wake import parked_wake_reason


def test_terminal_pipeline_does_not_consume_turns_during_an_explicit_help_wait():
    state = dict(
        terminal=True,
        terminal_delivered=False,
        waiting_for_feedback=True,
        fresh_feedback=False,
    )
    assert parked_wake_reason(**state, elapsed=0) is None
    assert parked_wake_reason(**state, elapsed=45) is None
    assert parked_wake_reason(**(state | {"fresh_feedback": True}), elapsed=50) == (
        "returned_attention"
    )
    assert parked_wake_reason(**state, elapsed=90) == "fixed_wait_fallback"


def test_terminal_completion_only_wakes_once_until_a_new_process_starts():
    state = dict(
        terminal=True,
        terminal_delivered=False,
        waiting_for_feedback=False,
        fresh_feedback=False,
    )
    assert parked_wake_reason(**state, elapsed=0) == "process_terminal"
    assert parked_wake_reason(**(state | {"terminal_delivered": True}), elapsed=0) is None
    assert parked_wake_reason(**(state | {"terminal_delivered": True}), elapsed=90) == (
        "fixed_wait_fallback"
    )
