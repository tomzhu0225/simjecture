"""Audit native invocation coverage without counting resumed thread totals twice."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def native_usage(root):
    receipts = []
    for path in sorted(Path(root).rglob("usage.json")):
        value = json.loads(path.read_text())
        if isinstance(value, dict) and "backend" in value and "scope" in value:
            receipts.append(dict(value, path=str(path.relative_to(root))))
    threads = {}
    latest = {}
    unknown = []
    for row in sorted(receipts, key=lambda r: r.get("reported_at", 0)):
        identifier = row.get("thread_id")
        if not identifier:
            unknown.append(row["path"])
            continue
        latest[identifier] = row
        if row.get("usage"):
            threads[identifier] = row
        elif identifier not in threads:
            threads[identifier] = None
    covered = [r for r in threads.values() if r is not None]
    fields = ["input_tokens", "cached_input_tokens", "output_tokens"]
    totals = {key: sum(r["usage"].get(key, 0) or 0 for r in covered) for key in fields}
    missing_fields = {key: sum(r["usage"].get(key) is None for r in covered) for key in fields}
    return dict(
        invocation_receipts=len(receipts),
        unique_threads=len(threads),
        measured_threads=len(covered),
        uncovered_thread_ids=[k for k, v in latest.items() if not v.get("usage")],
        unidentified_invocations=unknown,
        invocation_receipts_without_usage=sum(not r.get("usage") for r in receipts),
        known_cumulative_thread_totals=totals,
        threads_missing_token_fields=missing_fields,
        role_invocations=dict(Counter(r["role"] for r in receipts)),
        scope=(
            "Latest reported cumulative counter per native thread; "
            "not provider request counts or a billing estimate"
        ),
    )
