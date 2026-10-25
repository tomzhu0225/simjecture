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


def test_repair_consumed_during_active_turn_does_not_spend_final_reporting_turn():
    from simjecture_monitor.parked_wake import unconsumed_attention

    # Help woke turn3. A separate judge returned during that active turn; the
    # worker inspected/acknowledged it and submitted diagnostic reprocessing.
    delivered = {"help_first"}
    feedback = [
        dict(id="help_first", required=True, acknowledgment={"disposition": "used"}),
        dict(id="authority-late", required=True, acknowledgment={"disposition": "used"}),
    ]
    assert unconsumed_attention(feedback, delivered) == []
    assert (
        parked_wake_reason(
            terminal=False,
            terminal_delivered=False,
            waiting_for_feedback=False,
            fresh_feedback=bool(unconsumed_attention(feedback, delivered)),
            elapsed=0,
        )
        is None
    )
    # Turn4 remains available until the new pipeline actually finishes.
    assert (
        parked_wake_reason(
            terminal=True,
            terminal_delivered=False,
            waiting_for_feedback=False,
            fresh_feedback=False,
            elapsed=45,
        )
        == "process_terminal"
    )
    unacknowledged = dict(id="authority-other", required=True, acknowledgment=None)
    assert unconsumed_attention(feedback + [unacknowledged], delivered) == [unacknowledged]
