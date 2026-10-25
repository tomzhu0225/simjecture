"""Audit all assignments, including failures, in the raw-observation experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter
from pathlib import Path

from simjecture_monitor.events import digest, put
from simjecture_monitor.feedback_audit import feedback_measurement

HEALTHY = {"progressing_work", "announced_quiet", "publication_retry", "recovered_history"}


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def lines(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s] if path.exists() else []


def mean(values):
    return statistics.mean(values) if values else None


def audit(root, budget):
    design = load(root / "DESIGN.json")
    jobs = [j for b in design["blocks"] for j in b["jobs"]]
    completed = load(root / "RESULTS.json", [])
    results = {r["job"]["root"]: r for r in completed}
    starts = load(budget)["starts"]
    records = []
    inconsistencies = []
    for job in jobs:
        trial = root / job["root"]
        out = load(trial / "OUTCOME.json", {})
        result = results.get(job["root"], load(root / (job["root"] + "-exit.json"), {}))
        if result.get("outcome") is not None and result["outcome"] != out:
            inconsistencies.append([job["root"], "result/outcome mismatch"])
        native = [s for s in starts if s["continuation"] == trial.name and s.get("native")]
        decisions = [load(p) for p in sorted((trial / "monitor").glob("decision-*.json"))]
        model = [d for d in decisions if "model_identity" in (d.get("decision") or {})]
        alerts = load(trial / "monitor/alerts.json", [])
        ledger = load(trial / "incident-ledger.json", {})
        feedback = feedback_measurement(ledger) if ledger else {}
        observations = lines(trial / "monitor/observations.jsonl")
        for packet in observations:
            if digest(packet["state"]) != packet["packet_sha256"]:
                inconsistencies.append([job["root"], "packet digest mismatch"])
        q = out.get("quality", {})
        if q and q != load(trial / "QUALITY.json"):
            inconsistencies.append([job["root"], "quality receipt mismatch"])
        if (
            q.get("report_sha256")
            and digest((trial / "research/REPORT.txt").read_text()) != q["report_sha256"]
        ):
            inconsistencies.append([job["root"], "report digest mismatch"])
        if (
            q.get("results_sha256")
            and digest(load(trial / "research/results.json", {})) != q["results_sha256"]
        ):
            inconsistencies.append([job["root"], "results digest mismatch"])
        if "native_starts" in out and len(native) != out["native_starts"]:
            inconsistencies.append([job["root"], "native accounting mismatch"])
        receipts = [load(p) for p in (trial / "research/runs").glob("*/receipt.json")]
        active_starts = [s["id"] for s in native if s.get("ended_at") is None]
        if active_starts and out.get("ended_at"):
            inconsistencies.append([job["root"], "unclosed native records", active_starts])
        requests = [load(p) for p in (trial / "help_requests").glob("*.json")]
        first_park = out.get("parking", [{}])[0] if out.get("parking") else {}
        first_start, first_end = first_park.get("started_at"), first_park.get("ended_at")
        dispatched = ledger.get("dispatches", [])
        attention_during_first_park = [
            d for d in dispatched if first_start is not None and first_start <= d["at"] <= first_end
        ]
        # A dispatch's ledger timestamp can lag the native start; export native times too.
        native_during_first_park = [
            s
            for s in native
            if first_start is not None and first_start <= s["started_at"] < first_end
        ]
        model_times = [d["decision"]["total_seconds"] for d in model]
        row = dict(
            **job,
            healthy=job["family"] in HEALTHY,
            assigned=True,
            started=bool(out),
            stage=out.get("stage", "not_started"),
            returncode=result.get("returncode"),
            error=out.get("error"),
            verified_complete=bool(out.get("verified_complete")),
            numeric_quality=q.get("verified_quality"),
            numeric_metrics_ok=q.get("metrics_ok"),
            report_present=q.get("report_ok"),
            quantity_report_ok=out.get("quantity_report_ok"),
            quantity_pipeline_ok=out.get("quantity_pipeline_ok"),
            calibration_report_ok=out.get("calibration_report_ok"),
            workflow_complete=out.get("workflow_complete"),
            elapsed_seconds=out.get("elapsed_seconds"),
            native_starts=len(native),
            native_unclosed=len(active_starts),
            parent_turns=len(out.get("turns", [])),
            parent_returncodes=[t["returncode"] for t in out.get("turns", [])],
            native_role_counts=dict(
                Counter(
                    "helper"
                    if "/helpers/" in s["cwd"]
                    else "authority_judge"
                    if "authority-judge" in s["cwd"]
                    else "repair_proposer"
                    if "repair-proposer" in s["cwd"]
                    else "director_or_reviewer"
                    if s["readonly"]
                    else "worker"
                    for s in native
                )
            ),
            native_seconds=sum(
                s["ended_at"] - s["started_at"] for s in native if s.get("ended_at")
            ),
            solver_executions=len(receipts),
            solver_successes=sum(r["status"] == "succeeded" for r in receipts),
            solver_seconds=sum(r.get("wall_seconds", 0) for r in receipts),
            diagnostic_processes=len(out.get("job_runs", [])),
            parked_seconds=sum(p["ended_at"] - p["started_at"] for p in out.get("parking", [])),
            first_park_seconds=(first_end - first_start) if first_start is not None else None,
            wake_reasons=dict(Counter(p["wake_reason"] for p in out.get("parking", []))),
            fallback_count=sum(
                p["wake_reason"] == "fixed_wait_fallback" for p in out.get("parking", [])
            ),
            observations=len(observations),
            decisions=len(decisions),
            model_calls=len(model),
            model_seconds=sum(model_times),
            model_median_seconds=statistics.median(model_times) if model_times else None,
            decision_errors=[d.get("error") for d in decisions if d.get("error")],
            raw_choices=dict(
                Counter(d["decision"]["choice"] for d in decisions if d.get("decision"))
            ),
            accepted_alerts=len(alerts),
            accepted_actions=[a["action"] for a in alerts],
            host_suppressed_choices=sum(
                d.get("effective_action") == "defer"
                and (d.get("decision") or {}).get("choice") != "defer"
                for d in decisions
            ),
            first_alert_at=min((a["created_at"] for a in alerts), default=None),
            dispatches=len(dispatched),
            attention_during_first_park=len(attention_during_first_park),
            native_during_first_park=len(native_during_first_park),
            first_native_attention_at=min(
                (s["started_at"] for s in native_during_first_park), default=None
            ),
            explicit_help_requests=sum(r.get("origin") != "coprocessor" for r in requests),
            inferred_help_requests=sum(r.get("origin") == "coprocessor" for r in requests),
            required_feedback_misses=feedback.get("required_feedback_misses"),
            feedback_unknown=feedback.get("unknown_need_for_unacknowledged_help"),
            duplicate_wakeups=out.get("ledger", {}).get("duplicate_wakeups"),
            observation_violations=out.get("observation_violations", []),
            authority_origins=[
                a.get("incident", {}).get("origin") for a in out.get("authority_results", [])
            ],
            protected_ok=all(q.get("protected_artifacts_qualified", {}).values())
            and all(out.get("protected_extra", {}).values())
            if out.get("ended_at")
            else None,
            file_sha256={
                name: sha(trial / name)
                for name in [
                    "OUTCOME.json",
                    "INITIAL.json",
                    "QUALITY.json",
                    "VERIFIED.json",
                    "QUANTITY_VERIFIED.json",
                    "incident-ledger.json",
                    "monitor/observations.jsonl",
                    "research/REPORT.txt",
                    "research/results.json",
                    "execution/PROCESSES.json",
                ]
            },
        )
        records.append(row)
    source_checks = {}
    for name, expected in design["source_hashes"].items():
        value = subprocess.run(
            ["git", "show", design["source_revision"] + ":" + name],
            capture_output=True,
            check=False,
        )
        source_checks[name] = (
            value.returncode == 0 and hashlib.sha256(value.stdout).hexdigest() == expected
        )
    groups = []
    for subset_name in ["all", "healthy", "problem"]:
        for arm in ["observe", "rules", "model", "hybrid"]:
            selected = [
                r
                for r in records
                if r["arm"] == arm
                and (subset_name == "all" or r["healthy"] == (subset_name == "healthy"))
            ]
            groups.append(
                dict(
                    subset=subset_name,
                    arm=arm,
                    assigned=len(selected),
                    started=sum(r["started"] for r in selected),
                    verified=sum(r["verified_complete"] for r in selected),
                    numeric_correct=sum(r["numeric_quality"] == 1 for r in selected),
                    quantity_correct=sum(r["quantity_report_ok"] is True for r in selected),
                    pipeline_quantity_correct=sum(
                        r["quantity_pipeline_ok"] is True for r in selected
                    ),
                    complete=sum(r["workflow_complete"] is True for r in selected),
                    alerts=sum(r["accepted_alerts"] for r in selected),
                    alerted_trajectories=sum(r["accepted_alerts"] > 0 for r in selected),
                    native_starts=sum(r["native_starts"] for r in selected),
                    fallback_trajectories=sum(r["fallback_count"] > 0 for r in selected),
                    mean_seconds=mean(
                        [r["elapsed_seconds"] for r in selected if r["elapsed_seconds"] is not None]
                    ),
                    mean_native_starts=mean([r["native_starts"] for r in selected]),
                    model_calls=sum(r["model_calls"] for r in selected),
                    model_seconds=sum(r["model_seconds"] for r in selected),
                )
            )
    differences = []
    for row in records:
        if row["arm"] == "observe":
            continue
        reference = next(
            (
                r
                for r in records
                if r["arm"] == "observe"
                and (r["family"], r["seed"]) == (row["family"], row["seed"])
            ),
            None,
        )
        if reference is not None:
            differences.append(
                dict(
                    family=row["family"],
                    arm=row["arm"],
                    seed=row["seed"],
                    both_verified=row["verified_complete"] and reference["verified_complete"],
                    completion_difference=int(row["verified_complete"])
                    - int(reference["verified_complete"]),
                    elapsed_difference=(row["elapsed_seconds"] - reference["elapsed_seconds"])
                    if row["elapsed_seconds"] is not None
                    and reference["elapsed_seconds"] is not None
                    else None,
                    native_difference=row["native_starts"] - reference["native_starts"],
                )
            )
    return dict(
        scope=(
            "Authored mechanisms, frozen policies; fresh histories, descriptive seed matching only"
        ),
        root=str(root),
        source_revision=design["source_revision"],
        design_sha256=sha(root / "DESIGN.json"),
        results_sha256=sha(root / "RESULTS.json"),
        source_checks=source_checks,
        inconsistencies=inconsistencies,
        expected=len(jobs),
        results_present=len(completed),
        rows=records,
        groups=groups,
        differences_from_observe=differences,
        native_starts=sum(r["native_starts"] for r in records),
        solver_executions=sum(r["solver_executions"] for r in records),
        model_calls=sum(r["model_calls"] for r in records),
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
    fields = [k for k, v in result["rows"][0].items() if not isinstance(v, (dict, list))]
    with (args.output / "measurements.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(result["rows"])
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "expected",
                    "results_present",
                    "native_starts",
                    "solver_executions",
                    "model_calls",
                    "inconsistencies",
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
