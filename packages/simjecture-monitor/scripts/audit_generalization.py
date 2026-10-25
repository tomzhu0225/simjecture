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

from replay_generalization import evidence
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


def completion_measurement(out, wait, feedback):
    """Separate a collector truncation from an ordinary bounded actor failure.

    Old collectors broke on report files before processing an explicit wait.
    Teardown could then wake/cancel that wait, so inspect its timestamp at the
    final worker return rather than its final on-disk status. New collectors
    record their completion checks and process every denied return normally.
    """
    turns = out.get("turns", [])
    last = turns[-1] if turns else {}
    returned_at = last.get("ended_at")
    waiting = (
        returned_at is not None
        and wait.get("created_at", float("inf")) <= returned_at
        and (wait.get("woken_at") is None or returned_at < wait["woken_at"])
    )
    old_early_break = (
        bool(out.get("ended_at"))
        and "completion_checks" not in out
        and len(out.get("parking", [])) < len(turns)
        and last.get("returncode") != 0
    )
    reasons = []
    if old_early_break:
        reasons.append("collector_accepted_report_files_after_non_normal_worker_return")
        if waiting:
            reasons.append("explicit_worker_wait_still_pending_at_last_return")
    # An obligation failure is not automatically a collector defect; report it
    # separately even when it accompanies a censored return.
    obligations_reconciled = not feedback.get("required_feedback_misses", 0)
    return dict(
        completion_censored=bool(reasons),
        completion_censor_reasons=reasons,
        worker_waiting_at_last_return=waiting,
        finish_reason=out.get("finish_reason"),
        completion_checks=out.get("completion_checks", []),
        whole_workflow_verified=bool(
            out.get("verified_complete")
            and not reasons
            and last.get("returncode") == 0
            and not waiting
            and obligations_reconciled
        ),
    )


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
        completion = completion_measurement(out, load(trial / "worker_wait.json", {}), feedback)
        observations = lines(trial / "monitor/observations.jsonl")
        for packet in observations:
            if digest(packet["state"]) != packet["packet_sha256"]:
                inconsistencies.append([job["root"], "packet digest mismatch"])
        first_evidence = {}
        first_parked_evidence = {}
        for packet in observations:
            when = max(e["observed_at"] for e in packet["state"]["events"])
            for tag in evidence({"packet": packet}):
                first_evidence.setdefault(tag, when)
                if packet["state"]["host_state"]["worker_parked"]:
                    first_parked_evidence.setdefault(tag, when)
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
        pipeline_receipt_agrees = None
        if out.get("workflow_complete") and out.get("job_runs"):
            private_log = trial / "execution" / Path(out["job_runs"][-1]["stdout"]).name
            terminal = None
            if private_log.exists():
                for line in private_log.read_text().splitlines():
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if entry.get("phase") == "finished" and entry.get("status") == "completed":
                        terminal = {
                            k: v
                            for k, v in entry.items()
                            if k not in {"phase", "sequence", "observed_at"}
                        }
            pipeline_receipt_agrees = terminal is not None and terminal == load(
                trial / "research/pipeline_summary.json"
            )
            if not pipeline_receipt_agrees:
                inconsistencies.append([job["root"], "public/private pipeline result mismatch"])
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
            **completion,
            numeric_quality=q.get("verified_quality"),
            numeric_metrics_ok=q.get("metrics_ok"),
            report_present=q.get("report_ok"),
            quantity_report_ok=out.get("quantity_report_ok"),
            quantity_pipeline_ok=out.get("quantity_pipeline_ok"),
            calibration_report_ok=out.get("calibration_report_ok"),
            workflow_complete=out.get("workflow_complete"),
            pipeline_receipt_agrees=pipeline_receipt_agrees,
            started_at=out.get("started_at"),
            ended_at=out.get("ended_at"),
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
            first_public_evidence=first_evidence,
            first_parked_evidence=first_parked_evidence,
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
                    "worker_wait.json",
                    "monitor/observations.jsonl",
                    "research/REPORT.txt",
                    "research/results.json",
                    "execution/PROCESSES.json",
                ]
            },
        )
        records.append(row)
    censored_configurations = {
        (r["family"], r["seed"]) for r in records if r["completion_censored"]
    }
    for row in records:
        row["balanced_cost_eligible"] = (row["family"], row["seed"]) not in censored_configurations
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
                    whole_workflow_verified=sum(r["whole_workflow_verified"] for r in selected),
                    completion_censored=sum(r["completion_censored"] for r in selected),
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
            cost_eligible = row["balanced_cost_eligible"] and reference["balanced_cost_eligible"]
            differences.append(
                dict(
                    family=row["family"],
                    arm=row["arm"],
                    seed=row["seed"],
                    both_verified=row["verified_complete"] and reference["verified_complete"],
                    balanced_cost_eligible=cost_eligible,
                    completion_difference=int(row["verified_complete"])
                    - int(reference["verified_complete"]),
                    elapsed_difference=(row["elapsed_seconds"] - reference["elapsed_seconds"])
                    if cost_eligible
                    and row["elapsed_seconds"] is not None
                    and reference["elapsed_seconds"] is not None
                    else None,
                    native_difference=(row["native_starts"] - reference["native_starts"])
                    if cost_eligible
                    else None,
                )
            )
    blocks = []
    for block in design["blocks"]:
        names = {job["root"] for job in block["jobs"]}
        selected = [r for r in records if r["root"] in names]
        finished = all(r["ended_at"] is not None for r in selected)
        blocks.append(
            dict(
                arm=block.get("arm"),
                repeat=block.get("repeat"),
                assigned=len(selected),
                finished=finished,
                elapsed_seconds=(
                    max(r["ended_at"] for r in selected) - min(r["started_at"] for r in selected)
                )
                if finished
                else None,
                native_starts=sum(r["native_starts"] for r in selected),
            )
        )
    model_status = load(root / "MODEL_STATUS.json", {})
    maintenance = load(root / "RESIDENCY_MAINTENANCE.json", {})
    maintenance_successes = sum("result" in call for call in maintenance.get("calls", []))
    warmup = int((root / "WARMUP.json").exists())
    recorded_model_calls = sum(r["model_calls"] for r in records)
    model_accounting = dict(
        server_successful_calls=model_status.get("calls"),
        recorded_monitor_calls=recorded_model_calls,
        initial_warmup_calls=warmup,
        maintenance_successful_calls=maintenance_successes,
        maintenance_errors=[c for c in maintenance.get("calls", []) if c.get("error")],
        unaccounted_successful_calls=(
            model_status["calls"] - recorded_model_calls - warmup - maintenance_successes
        )
        if "calls" in model_status
        else None,
    )
    lease = load(budget)
    occupancy = []
    for start in lease["starts"]:
        occupancy.append((start["started_at"], 1))
        if start.get("ended_at") is not None:
            occupancy.append((start["ended_at"], -1))
    count = maximum_concurrent = 0
    for _, delta in sorted(occupancy):
        count += delta
        maximum_concurrent = max(maximum_concurrent, count)
    lease_accounting = dict(
        reservations=len(lease["starts"]),
        actual_native_starts=sum(bool(s.get("native")) for s in lease["starts"]),
        unfinished=sum(s.get("ended_at") is None for s in lease["starts"]),
        observed_maximum_concurrent=maximum_concurrent,
        declared_maximum_concurrent=lease["maximum_concurrent"],
        observed_maximum_per_continuation=max(
            Counter(s["continuation"] for s in lease["starts"]).values(), default=0
        ),
        declared_maximum_per_continuation=lease["maximum_per_continuation"],
        declared_maximum_starts=lease["maximum_starts"],
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
        model_accounting=model_accounting,
        lease_accounting=lease_accounting,
        inconsistencies=inconsistencies,
        expected=len(jobs),
        results_present=len(completed),
        rows=records,
        groups=groups,
        cost_scope=(
            "groups contain raw recorded costs, including censored lower bounds. "
            "balanced_cost_groups are a post-collection descriptive subset that removes "
            "every arm of each configuration/seed with any collector-truncated return; "
            "ordinary actor failures remain. Separate follow-up runs are not pooled."
        ),
        censored_configurations=[
            dict(family=family, seed=seed) for family, seed in sorted(censored_configurations)
        ],
        balanced_cost_groups=[
            dict(
                arm=arm,
                trajectories=len(selected),
                scientifically_verified=sum(r["verified_complete"] for r in selected),
                whole_workflow_verified=sum(r["whole_workflow_verified"] for r in selected),
                mean_seconds=mean(
                    [r["elapsed_seconds"] for r in selected if r["elapsed_seconds"] is not None]
                ),
                median_seconds=statistics.median(
                    [r["elapsed_seconds"] for r in selected if r["elapsed_seconds"] is not None]
                )
                if any(r["elapsed_seconds"] is not None for r in selected)
                else None,
                native_starts=sum(r["native_starts"] for r in selected),
                mean_native_starts=mean([r["native_starts"] for r in selected]),
            )
            for arm in ["observe", "rules", "model", "hybrid"]
            if (selected := [r for r in records if r["arm"] == arm and r["balanced_cost_eligible"]])
        ],
        blocks=blocks,
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
