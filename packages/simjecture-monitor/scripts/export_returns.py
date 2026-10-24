"""Build learning records exclusively from actual sampled worker continuations."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path

from simjecture_monitor.events import put


def agent_starts(root):
    paths = [root / "supervisor/events.jsonl"]
    paths += list(root.glob("supervisor/director-*/events.jsonl"))
    paths += list(root.glob("helpers/*/events.jsonl"))
    paths += list(root.glob("monitor_authority/*/events.jsonl"))
    starts = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("kind") in {"worker_started", "judge_started"}:
                starts.add((row["kind"], row.get("pid"), row["time"]))
    return len(starts)


def export(root, output):
    source = Path(__file__).with_name("analyze.py")
    spec = importlib.util.spec_from_file_location("monitor_outcome_audit", source)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    episodes = []
    excluded = []
    for path in sorted(root.glob("*/TRIAL.json")):
        trial = json.loads(path.read_text())
        if trial["stage"] not in {"completed", "failed"}:
            continue
        rows = [
            json.loads(p.read_text())
            for p in sorted((path.parent / "monitor").glob("decision-*.json"))
        ]
        if any(r.get("error") for r in rows):
            excluded.append(
                dict(episode=path.parent.name, reason="Incomplete model-service coverage")
            )
            continue
        decisions = []
        for row in rows:
            decision = row.get("decision")
            if not decision or row["received_at"] > trial.get("ended_at", float("inf")):
                continue  # No treatment can be delivered after the worker phase terminates.
            if decision.get("selection_kind") != "sampled":
                raise ValueError("Non-sampled behavior cannot enter the on-policy dataset")
            p = decision["probabilities"]
            expected = p[decision["choice"]] / sum(p.values())
            if not math.isclose(expected, decision["behavior_probability"], rel_tol=1e-7):
                raise ValueError("Behavior probability does not match the sampled distribution")
            decisions.append(
                dict(
                    packet=row["packet"],
                    action=decision["choice"],
                    behavior_probability=expected,
                    reference_probabilities=p,
                    prompt_sha256=decision["prompt_sha256"],
                    model_view=decision.get("model_view"),
                )
            )
        if not decisions:
            excluded.append(dict(episode=path.parent.name, reason="No sampled policy decisions"))
            continue
        measured = audit.summarize(path.parent)
        verified = (
            json.loads((path.parent / "VERIFIED.json").read_text())
            if (path.parent / "VERIFIED.json").exists()
            else {}
        )
        cells = {r["cells"] for r in verified.get("verified_runs", [])}
        controls = {64, 128} <= cells
        feedback = [
            json.loads(p.read_text()).get("resolved_at", 0)
            for p in (path.parent / "help_requests").glob("*.json")
        ]
        feedback += [
            json.loads(p.read_text()).get("ended_at", 0)
            for p in (path.parent / "monitor_authority").glob("*/result.json")
        ]
        report = path.parent / "research/REPORT.txt"
        feedback_delivered = report.exists() and report.stat().st_mtime >= max(feedback, default=0)
        quality = int(
            measured["worker_metrics_agree"]
            and controls
            and measured["report_present"]
            and feedback_delivered
            and not measured["pending_feedback_after_final_report"]
        )
        calls = agent_starts(path.parent)
        elapsed = max(0, path.stat().st_mtime - trial["started_at"])
        reward = quality - 0.02 * calls - 0.1 * min(elapsed / 650, 1)
        episodes.append(
            dict(
                id=path.parent.name,
                case=trial["case"],
                reward=reward,
                quality=quality,
                capable_agent_invocations=calls,
                elapsed_seconds=elapsed,
                decisions=decisions,
                outcome=measured,
            )
        )
    dataset = dict(
        protocol="Real sampled continuations; reward is declared utility, not currency",
        episodes=episodes,
        excluded=excluded,
    )
    put(output, dataset)
    return dataset


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    d = export(args.root, args.output)
    print(
        json.dumps(
            dict(
                eligible=len(d["episodes"]),
                excluded=d["excluded"],
                returns=[
                    {k: e[k] for k in ("id", "quality", "reward", "capable_agent_invocations")}
                    for e in d["episodes"]
                ],
            )
        )
    )


if __name__ == "__main__":
    main()
