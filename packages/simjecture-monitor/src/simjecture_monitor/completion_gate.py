"""Separate a finished worker handoff from provisional report artifacts."""

from __future__ import annotations


def may_complete(
    *,
    report_ready,
    pipeline_complete,
    worker_returncode,
    worker_waiting,
    pending_required_help,
    unacknowledged_required,
):
    """Draft files do not override an explicit wait or an outstanding obligation."""
    return bool(
        report_ready
        and pipeline_complete
        and worker_returncode == 0
        and not worker_waiting
        and not pending_required_help
        and not unacknowledged_required
    )
