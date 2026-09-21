"""Account native cumulative usage once per thread, including interrupted turns.

Only read session files whose IDs occur in this evaluation's provider output.
Never interpret absent usage as zero. These are reported tokens, not billing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


def records(path):
    try:
        with path.open() as stream:
            for line in stream:
                try:
                    value = json.loads(line)
                except ValueError:
                    continue  # A writer may currently be appending the last line.
                if isinstance(value, dict):
                    yield value
    except OSError:
        return


def cumulative_usage(path):
    latest = None
    events = 0
    regressions = []
    last_timestamp = None
    for event in records(path):
        payload = event.get("payload", {})
        if not isinstance(payload, dict) or payload.get("type") != "token_count":
            continue
        info = payload.get("info") or {}
        total = info.get("total_token_usage")
        if not isinstance(total, dict):
            continue
        current = {
            k: v
            for k, v in total.items()
            if k in FIELDS and isinstance(v, int) and not isinstance(v, bool)
        }
        if latest is not None:
            for key, value in current.items():
                if value < latest.get(key, 0):
                    regressions.append(
                        {
                            "field": key,
                            "previous": latest[key],
                            "current": value,
                            "timestamp": event.get("timestamp"),
                        }
                    )
        latest = current
        events += 1
        last_timestamp = event.get("timestamp")
    return {
        "usage": latest,
        "usage_events": events,
        "last_usage_timestamp": last_timestamp,
        "counter_regressions": regressions,
    }


def add_usage(items):
    totals = {}
    for item in items:
        item = dict(item or {})
        if "input_tokens" in item and "output_tokens" in item:
            item.setdefault("total_tokens", item["input_tokens"] + item["output_tokens"])
        for key, value in item.items():
            if key in FIELDS:
                totals[key] = totals.get(key, 0) + value
    return totals or None


def session_index(root):
    # Names contain the UUID. No unrelated session contents are opened.
    index = {}
    for path in root.rglob("rollout-*.jsonl"):
        index.setdefault(path.stem[-36:], []).append(path)
    return index


def collect_run(directory, index):
    invocations = []
    threads = {}
    supervisor = directory / "supervisor"
    if not supervisor.exists() and (directory / "campaign/supervisor").exists():
        supervisor = directory / "campaign/supervisor"
    for path in sorted(supervisor.rglob("response.json")):
        category = "worker" if path.parent.name.startswith("turn-") else "reviewer"
        ids = set()
        completed = []
        for event in records(path):
            if event.get("type") == "thread.started" and event.get("thread_id"):
                ids.add(event["thread_id"])
            if event.get("type") == "turn.completed":
                completed.append(event.get("usage", {}))
        invocations.append(
            {
                "path": str(path.relative_to(directory)),
                "category": category,
                "thread_ids": sorted(ids),
                "turn_completed": bool(completed),
                "completed_turn_usage": completed[-1] if completed else None,
            }
        )
        for tid in ids:
            threads.setdefault(tid, {"category": category, "invocations": 0})["invocations"] += 1
    for tid, thread in threads.items():
        paths = index.get(tid, [])
        thread["session_file_count"] = len(paths)
        if len(paths) == 1:
            thread.update(cumulative_usage(paths[0]))
            thread["source"] = "native_cumulative_session_usage"
        else:
            # Old ephemeral reviewers may have only a completed-turn receipt.
            fallback = [
                i["completed_turn_usage"]
                for i in invocations
                if tid in i["thread_ids"] and i["completed_turn_usage"]
            ]
            thread.update(
                usage=fallback[-1] if fallback else None,
                usage_events=0,
                counter_regressions=[],
                source="completed_turn_fallback",
            )
    categories = {}
    for category in ("worker", "reviewer"):
        group = [v for v in threads.values() if v["category"] == category]
        calls = [i for i in invocations if i["category"] == category]
        categories[category] = {
            "reported_usage": add_usage(t["usage"] for t in group),
            "unique_threads": len(group),
            "invocations": len(calls),
            "invocations_without_turn_completed": sum(not i["turn_completed"] for i in calls),
            "invocations_without_thread_id": sum(not i["thread_ids"] for i in calls),
            "threads_without_usage": sum(t["usage"] is None for t in group),
            "threads_with_counter_regressions": sum(bool(t["counter_regressions"]) for t in group),
        }
    return {
        "run": directory.name,
        "categories": categories,
        "combined_reported_usage": add_usage(t["usage"] for t in threads.values()),
        "threads": threads,
        "invocations": invocations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    index = session_index(args.sessions)
    result = {
        "runs": [
            collect_run(d, index)
            for d in sorted(args.root.iterdir())
            if d.is_dir() and (d / "campaign").exists()
        ],
        "accounting": "Last cumulative usage per unique thread, including workers and reviewers.",
        "limitations": [
            "Provider requests interrupted before emitting usage are not measured.",
            "Cached input is a subset of input; reasoning output is a subset of output.",
            "No subscription-credit or monetary cost is inferred.",
            "Missing usage is null, never zero. Counter regressions require investigation.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    for run in result["runs"]:
        print(run["run"], json.dumps(run["combined_reported_usage"]))


if __name__ == "__main__":
    main()
