from simjecture_monitor.completion_gate import may_complete


def test_draft_report_waits_for_required_result_and_acknowledgment():
    state = dict(
        report_ready=True,
        pipeline_complete=True,
        worker_returncode=124,
        worker_waiting=True,
        pending_required_help=1,
        unacknowledged_required=0,
    )
    assert not may_complete(**state)
    # A returned required result still needs reconciliation by the worker.
    state.update(
        worker_returncode=0,
        worker_waiting=False,
        pending_required_help=0,
        unacknowledged_required=1,
    )
    assert not may_complete(**state)
    state["unacknowledged_required"] = 0
    assert may_complete(**state)


def test_pending_required_help_blocks_normal_exit_without_an_explicit_wait():
    assert not may_complete(
        report_ready=True,
        pipeline_complete=True,
        worker_returncode=0,
        worker_waiting=False,
        pending_required_help=1,
        unacknowledged_required=0,
    )


def test_advisory_work_does_not_force_wait_but_explicit_wait_and_checkpoint_are_respected():
    state = dict(
        report_ready=True,
        pipeline_complete=True,
        worker_returncode=0,
        worker_waiting=False,
        pending_required_help=0,
        unacknowledged_required=0,
    )
    assert may_complete(**state)
    assert not may_complete(**(state | {"worker_waiting": True}))
    assert not may_complete(**(state | {"worker_returncode": 124}))
