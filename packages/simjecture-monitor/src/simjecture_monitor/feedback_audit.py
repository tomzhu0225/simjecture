"""Withhold strict rewards when unacknowledged helper need was never declared.

The prospective pilot's operational contract marks repairs/replans required and
helper advice advisory. That does not establish whether a worker-requested help
result was actually needed. Preserve that uncertainty rather than relabeling it.
"""

from __future__ import annotations


def feedback_measurement(ledger):
    rows = ledger["feedback"]
    unknown = []
    for row in rows:
        if row["acknowledgment"] is not None or not row["id"].startswith("help_"):
            continue
        result = row.get("result", {})
        declaration = result.get("feedback_requirement")
        if declaration not in {"required", "advisory"}:
            unknown.append(row["id"])
    missed = sum(
        (row["required"] or row.get("result", {}).get("feedback_requirement") == "required")
        and row["acknowledgment"] is None
        for row in rows
    )
    return dict(
        required_feedback_misses=None if unknown else missed,
        unknown_need_for_unacknowledged_help=unknown,
        available_feedback=len(rows),
        scope=(
            "Declared required-feedback reconciliation; "
            "no inferred necessity from case labels or cancellation"
        ),
    )
