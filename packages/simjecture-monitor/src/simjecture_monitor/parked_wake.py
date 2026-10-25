"""Wake selection for the bounded asynchronous experiment driver."""

from __future__ import annotations


def parked_wake_reason(
    *, terminal, terminal_delivered, waiting_for_feedback, fresh_feedback, elapsed
):
    """A finished process does not satisfy a worker's independent help wait.

    Completion is an edge, not a permanent reason to restart a native worker.
    The common timeout still permits a bounded recheck if assistance never returns.
    """
    if fresh_feedback:
        return "returned_attention"
    if terminal and not terminal_delivered and not waiting_for_feedback:
        return "process_terminal"
    if elapsed >= 90:
        return "fixed_wait_fallback"
    return None


def unconsumed_attention(feedback, delivered):
    """Do not deliver again a result consumed during the worker's active turn."""
    return [
        item
        for item in feedback
        if item["id"] not in delivered
        and not item.get("acknowledgment")
        and (
            item["id"].startswith("help_")
            or item["id"].startswith("authority-")
            or item["required"]
        )
    ]
