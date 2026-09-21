"""Read-only pilot measurements; no model-provided success label is trusted alone."""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path

from token_usage import collect_run, session_index


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def arithmetic(task, doc):
    if (
        not isinstance(doc, dict)
        or doc.get("task") != task
        or not isinstance(doc.get("rows"), list)
    ):
        return {"passed": False, "reason": "missing or invalid numerical result"}
    try:
        if task == "euler":
            rows = {int(r["N"]): r for r in doc["rows"]}
            if set(rows) != {16, 32, 64, 128}:
                raise ValueError("wrong finite domain")
            errors = []
            for n, r in rows.items():
                e = abs((1 - 1 / n) ** n - math.exp(-1))
                e2 = abs((1 - 1 / (2 * n)) ** (2 * n) - math.exp(-1))
                for key, ref in [("E_N", e), ("E_2N", e2), ("ratio", e / e2)]:
                    v = float(r[key])
                    if not math.isfinite(v):
                        raise ValueError("nonfinite measurement")
                    errors.append(abs(v - ref))
            return {
                "passed": max(errors) < 1e-8,
                "max_absolute_reference_error": max(errors),
                "scope": "numerical consistency only; repair semantics require independent review",
            }
        rows = {float(r["h"]): r for r in doc["rows"]}
        if set(rows) != {0.2, 0.1, 0.05}:
            raise ValueError("wrong finite domain")
        for h, r in rows.items():
            if int(r["steps"]) != round(20 / h):
                raise ValueError("wrong horizon")
            error = float(r["max_energy_error"])
            if not math.isfinite(error) or not 0 <= error <= 1e-11:
                raise ValueError("reported error contradicts reference bound")
        return {
            "passed": True,
            "scope": "finite-domain error-bound consistency, not source verification",
        }
    except (ValueError, TypeError, KeyError, OverflowError) as e:
        return {"passed": False, "reason": str(e)}


def collect(directory, sessions=None):
    name = directory.name
    task, workflow = name.split("-", 1)
    supervisor = directory / "supervisor"
    campaign = directory / "campaign"
    state = read_json(supervisor / "state.json", {})
    ledger = read_json(campaign / "hypothesis_ledger.json", {})
    claims = ledger.get("claims", [])
    report = read_json(campaign / "mvp_report.json", {})
    assignments = read_json(campaign / "role_assignments.json", {}).get("assignments", {})
    threads = set()
    commands = []
    turns = 0
    for path in sorted(supervisor.glob("turn-*/response.json")):
        turns += 1
        for line in path.read_text().splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") == "thread.started":
                threads.add(d.get("thread_id"))
            item = d.get("item", {})
            if d.get("type") == "item.completed" and item.get("type") == "command_execution":
                commands.append(item.get("command", ""))
    doc = read_json(campaign / "workspace/benchmark-result.json")
    result = {
        "task": task,
        "workflow": workflow,
        "state": state.get("status", "not_started"),
        "wall_seconds": max(
            0,
            (
                time.time()
                if state.get("status") == "running"
                else state.get("updated_at", time.time())
            )
            - state.get("started_at", time.time()),
        ),
        "kernel_report_status": report.get("status"),
        "worker_sessions_started": turns,
        "distinct_native_worker_threads": len(threads),
        "native_commands": len(commands),
        "kernel_mutations": sum(len(a["operations"]) for a in assignments.values()),
        "assignments": len(assignments),
        "token_accounting": collect_run(directory, sessions or {}),
        "orientation_command_heuristic_count": sum(
            bool(
                re.search(
                    r"kernel_call.py.*\b(snapshot|catalog|list_skills|read_skill)\b"
                    r"|cat .*catalog.json",
                    c,
                )
            )
            for c in commands
        ),
        "arithmetic_check": arithmetic(task, doc),
        "claims": [
            {k: c.get(k) for k in ["id", "kind", "status", "relation", "parent_id", "statement"]}
            for c in claims
        ],
        "scientific_reviews": [],
        "last_error": state.get("last_error"),
    }
    reviews = read_json(campaign / "scientific_reviews.json", {})
    result["scientific_reviews"] = [
        {"stage": r["stage"], "decision": r["verdict"]["decision"], "claim_id": r["claim_id"]}
        for r in reviews.values()
    ]
    result["numerical_artifact_present"] = doc is not None
    exploratory = []
    for path in (campaign / "workspace").glob("*.json"):
        candidate = read_json(path)
        if not isinstance(candidate, dict):
            continue
        checked = arithmetic(task, dict(candidate, task=task))
        if checked["passed"]:
            exploratory.append(
                {
                    "path": path.name,
                    "check": checked,
                    "file_timestamp_seconds_after_start": path.stat().st_mtime
                    - state.get("started_at", path.stat().st_mtime),
                }
            )
    result["reference_consistent_numerical_artifacts"] = exploratory
    result["completed_with_reference_consistent_artifact"] = (
        report.get("status") == "completed" and result["arithmetic_check"]["passed"]
    )
    if doc is not None:
        result["numerical_result"] = doc
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sessions", type=Path, default=Path.home() / ".codex/sessions")
    a = parser.parse_args()
    sessions = session_index(a.sessions)
    report = {
        "measured_at": time.time(),
        "runs": [
            collect(d, sessions)
            for d in sorted(a.root.iterdir())
            if d.is_dir() and (d / "campaign").exists()
        ],
        "limitations": [
            "One run per task/condition; no statistical superiority claim.",
            "Elapsed times include concurrent service and host load.",
            "Reported tokens include worker/reviewer session counters; "
            "requests cut off before usage remain unmeasured.",
            "Arithmetic consistency does not substitute for scientific review.",
        ],
    }
    encoded = json.dumps(report, indent=2) + "\n"
    if a.output:
        a.output.write_text(encoded)
    print(encoded)


if __name__ == "__main__":
    main()
