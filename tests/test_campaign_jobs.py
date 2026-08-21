from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

from conjecture_solver.campaign_jobs import (
    CampaignInterprocessLock,
    CampaignJobStatus,
    CampaignJobSupervisor,
    CampaignLockBusyError,
    JobConflictError,
)


def _command(*source: str) -> tuple[str, ...]:
    return (sys.executable, "-c", *source)


def test_campaign_interprocess_lock_is_exclusive_and_reopens(tmp_path: Path) -> None:
    first = CampaignInterprocessLock(tmp_path)
    second = CampaignInterprocessLock(tmp_path)
    first.acquire()
    try:
        with pytest.raises(CampaignLockBusyError):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()
    assert (tmp_path / ".campaign-write.lock").is_file()


def test_restart_reopen_preserves_terminal_receipt(tmp_path: Path) -> None:
    supervisor = CampaignJobSupervisor(tmp_path)
    initial = supervisor.start(
        operation_id="restart-safe",
        argv=_command("print('durable')"),
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = supervisor.status(initial.job_id)
        if state.status.terminal:
            break
        time.sleep(0.01)
    assert state.status is CampaignJobStatus.SUCCEEDED
    assert supervisor.result_record(initial.job_id) is not None

    reopened = CampaignJobSupervisor(tmp_path)
    assert reopened.status(initial.job_id).status is CampaignJobStatus.SUCCEEDED
    job_dir = tmp_path / "jobs" / initial.job_id
    assert all(
        (job_dir / name).is_file()
        for name in ("request.json", "state.json", "result.json", "supervisor.json")
    )


def test_same_operation_id_replays_and_conflict_is_rejected(tmp_path: Path) -> None:
    supervisor = CampaignJobSupervisor(tmp_path)
    first = supervisor.start(
        operation_id="same-operation",
        argv=_command("import time; time.sleep(0.2)"),
    )
    replay = supervisor.start(
        operation_id="same-operation",
        argv=_command("import time; time.sleep(0.2)"),
    )
    assert replay.job_id == first.job_id
    with pytest.raises(JobConflictError):
        supervisor.start(
            operation_id="same-operation",
            argv=_command("print('different request')"),
        )
    process = supervisor._processes[first.job_id]
    process.terminate()
    process.wait(timeout=5)


def test_reopen_marks_dead_unreceipted_job_outcome_unknown(tmp_path: Path) -> None:
    supervisor = CampaignJobSupervisor(tmp_path)
    initial = supervisor.start(
        operation_id="unreceipted",
        argv=_command("print('exited before receipt')"),
    )
    # Do not ask the creating supervisor for status: the durable result was
    # intentionally never receipted before this simulated restart.
    time.sleep(0.2)
    reopened = CampaignJobSupervisor(tmp_path)
    state = reopened.status(initial.job_id)
    assert state.status is CampaignJobStatus.OUTCOME_UNKNOWN
    result = reopened.result_record(initial.job_id)
    assert result is not None
    assert result.status is CampaignJobStatus.OUTCOME_UNKNOWN
    assert "no longer matches" in (state.reconciliation_note or "") or "dead" in (
        state.reconciliation_note or ""
    )


def test_cancel_refuses_mismatched_pid_without_signalling(tmp_path: Path) -> None:
    supervisor = CampaignJobSupervisor(tmp_path)
    initial = supervisor.start(
        operation_id="mismatched-pid",
        argv=_command("import time; time.sleep(10)"),
    )
    record_path = tmp_path / "jobs" / initial.job_id / "supervisor.json"
    payload = json.loads(record_path.read_text())
    payload["identity"]["pid"] = initial.pid + 100_000
    record_path.write_text(json.dumps(payload))

    state = supervisor.cancel(initial.job_id, wait_interrupt_seconds=0, wait_terminate_seconds=0)
    assert state.status is CampaignJobStatus.OUTCOME_UNKNOWN
    process = supervisor._processes[initial.job_id]
    assert process.poll() is None
    process.terminate()
    process.wait(timeout=5)


def test_reopened_supervisor_persists_verified_cancellation(tmp_path: Path) -> None:
    supervisor = CampaignJobSupervisor(tmp_path)
    initial = supervisor.start(
        operation_id="restart-cancel",
        argv=_command("import time; time.sleep(60)"),
    )
    reopened = supervisor.reopen()
    state = reopened.cancel(
        initial.job_id,
        wait_interrupt_seconds=2,
        wait_terminate_seconds=1,
    )

    assert state.status is CampaignJobStatus.CANCELLED
    receipt = reopened.result_record(initial.job_id)
    assert receipt is not None
    assert receipt.status is CampaignJobStatus.CANCELLED
    assert "verified cancellation" in (receipt.detail or "")
    assert reopened.reopen().status(initial.job_id).status is CampaignJobStatus.CANCELLED
