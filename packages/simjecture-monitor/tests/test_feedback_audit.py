from simjecture_monitor.feedback_audit import feedback_measurement


def row(identifier, *, required=False, ack=None, result=None):
    return dict(id=identifier, required=required, acknowledgment=ack, result=result or {})


def test_optional_ledger_flag_does_not_prove_worker_help_was_unneeded():
    result = feedback_measurement(dict(feedback=[row("help_worker")]))
    assert result["required_feedback_misses"] is None
    assert result["unknown_need_for_unacknowledged_help"] == ["help_worker"]


def test_acknowledged_help_has_no_miss_even_when_necessity_was_not_declared():
    result = feedback_measurement(dict(feedback=[row("help_worker", ack={"disposition": "used"})]))
    assert result["required_feedback_misses"] == 0


def test_explicit_advisory_and_required_results_remain_distinct():
    result = feedback_measurement(
        dict(
            feedback=[
                row("help_advice", result=dict(feedback_requirement="advisory")),
                row("help_needed", result=dict(feedback_requirement="required")),
                row("repair", required=True),
                row("director_continue"),
            ]
        )
    )
    assert result["required_feedback_misses"] == 2
