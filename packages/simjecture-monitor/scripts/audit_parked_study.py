"""Export measured live-study components without inventing paired continuations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path

from simjecture_monitor.events import digest, put
from simjecture_monitor.feedback_audit import feedback_measurement


def load(path):
    return json.loads(path.read_text())


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root, budget):
    design = load(root / "DESIGN.json")
    jobs = design.get("jobs") or [job for b in design["blocks"] for job in b["jobs"]]
    results = load(root / "RESULTS.json")
    assert len(results) == len(jobs)
    assert {r["job"]["root"] for r in results} == {j["root"] for j in jobs}
    assert len({r["job"]["root"] for r in results}) == len(jobs)
    starts = load(budget)["starts"]
    rows = []
    for result in results:
        job, outcome = result["job"], result["outcome"]
        trial = root / job["root"]
        ledger = load(trial / "incident-ledger.json")
        feedback = feedback_measurement(ledger)
        native = [s for s in starts if s["continuation"] == trial.name and s.get("native")]
        judges = [s for s in native if Path(s["cwd"]).name == "authority-judge"]
        mismatch = outcome.get("first_mismatch_at")
        decisions = [load(p) for p in sorted((trial / "monitor").glob("decision-*.json"))]
        valid = [d for d in decisions if d.get("decision") and not d.get("error")]
        parked_decisions = [
            d for d in valid if d["packet"]["state"].get("host_state", {}).get("worker_parked")
        ]
        forward = [
            d["decision"]["total_seconds"] for d in valid if "total_seconds" in d["decision"]
        ]
        row = dict(
            job,
            returncode=result["returncode"],
            stage=outcome["stage"],
            quality=outcome.get("quality", {}).get("verified_quality"),
            elapsed_seconds=outcome["elapsed_seconds"],
            parked_seconds=outcome["worker_resumed_at"] - outcome["parked_at"],
            native_starts=len(native),
            judge_starts=len(judges),
            first_mismatch_at=mismatch,
            first_judge_at=min((s["started_at"] for s in judges), default=None),
            wake_reason=outcome.get("wake_reason"),
            model_records=len(decisions),
            model_errors=sum(bool(d.get("error")) for d in decisions),
            model_median_total_seconds=statistics.median(forward) if forward else None,
            parked_model_calls=len(parked_decisions),
            parked_judge_choices=sum(
                d["decision"]["choice"] == "request_repair_judge" for d in parked_decisions
            ),
            judge_while_parked=any(
                outcome["parked_at"] <= s["started_at"] < outcome["worker_resumed_at"]
                for s in judges
            ),
            required_feedback_misses=feedback["required_feedback_misses"],
            feedback_unknown=feedback["unknown_need_for_unacknowledged_help"],
            duplicate_wakeups=outcome["ledger"]["duplicate_wakeups"],
            authority_origins=[
                a.get("incident", {}).get("origin") for a in outcome["authority_results"]
            ],
            file_sha256={
                name: fingerprint(trial / name)
                for name in [
                    "LIVE.json",
                    "INITIAL.json",
                    "QUALITY.json",
                    "incident-ledger.json",
                    "VERIFIED.json",
                ]
            },
            report_sha256=fingerprint(trial / "research/REPORT.txt"),
            results_sha256=fingerprint(trial / "research/results.json"),
        )
        row["judge_response_seconds"] = (
            row["first_judge_at"] - mismatch if judges and mismatch is not None else None
        )
        assert row["native_starts"] == outcome["native_starts"]
        q = outcome["quality"]
        assert q == load(trial / "QUALITY.json")
        # Quality receipts canonicalize both strings and JSON through digest().
        assert digest((trial / "research/REPORT.txt").read_text()) == q["report_sha256"]
        assert digest(load(trial / "research/results.json")) == q["results_sha256"]
        assert all(s.get("ended_at") is not None for s in native)
        rows.append(row)
    groups = []

    def group_key(row):
        return row["case"], row["policy"], row.get("profile", "reference"), row.get("timer")

    for key in sorted({group_key(r) for r in rows}):
        subset = [r for r in rows if group_key(r) == key]
        group = dict(case=key[0], policy=key[1], profile=key[2], count=len(subset))
        if key[3] is not None:
            group["timer"] = key[3]
        for metric in [
            "elapsed_seconds",
            "parked_seconds",
            "native_starts",
            "judge_response_seconds",
            "model_records",
            "model_median_total_seconds",
        ]:
            values = [r[metric] for r in subset if r[metric] is not None]
            group[metric] = dict(values=values, mean=statistics.mean(values) if values else None)
        group["judges_while_parked"] = sum(r["judge_while_parked"] for r in subset)
        groups.append(group)
    return dict(
        scope="Fresh randomized live trajectories, not matched checkpoint pairs",
        root=str(root),
        design_sha256=fingerprint(root / "DESIGN.json"),
        results_sha256=fingerprint(root / "RESULTS.json"),
        source_revision=design["source_revision"],
        rows=rows,
        groups=groups,
        all_verified_complete=all(r["quality"] == 1 for r in rows),
        all_ended=all(r["stage"] == "completed" and r["returncode"] == 0 for r in rows),
        strict_feedback_eligible=sum(r["required_feedback_misses"] is not None for r in rows),
        native_starts=sum(r["native_starts"] for r in rows),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root.resolve(), args.budget.resolve())
    args.output.mkdir(parents=True, exist_ok=True)
    put(args.output / "audit.json", result)
    keys = [
        "root",
        "case",
        "policy",
        "profile",
        "repeat",
        "quality",
        "elapsed_seconds",
        "parked_seconds",
        "native_starts",
        "judge_response_seconds",
        "wake_reason",
        "required_feedback_misses",
        "duplicate_wakeups",
    ]
    if any("timer" in row for row in result["rows"]):
        keys.insert(4, "timer")
    with (args.output / "measurements.csv").open("w") as stream:
        writer = csv.DictWriter(stream, keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(result["rows"])
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "all_verified_complete",
                    "all_ended",
                    "strict_feedback_eligible",
                    "native_starts",
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
