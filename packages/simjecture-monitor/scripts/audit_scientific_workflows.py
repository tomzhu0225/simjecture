"""Audit the frozen four-arm scientific workflow cohort, including failed trials."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from audit_generalization import completion_measurement
from simjecture_monitor.events import digest, put
from simjecture_monitor.feedback_audit import feedback_measurement

ARMS = ["observe", "rules", "base", "adapted"]
QUIET = {"progressing_work", "announced_quiet", "publication_retry", "recovered_history"}


def read(path, default=None):
    return json.loads(path.read_text()) if path.is_file() else default


def verifier_report_value(path):
    """Reproduce the verifier's explicit empty report for absent/invalid JSON.

    Missing reports remain completion failures. Their empty parsed-value digest
    must not be mislabeled as a later mutation of a nonexistent artifact.
    """
    try:
        return read(path, {})
    except ValueError:
        return {}


def paired_interval(records, baseline, metric, *, seed=20261026, draws=10000, learned="adapted"):
    blocks = defaultdict(dict)
    for record in records:
        blocks[record["block"]][record["arm"]] = record
    families = defaultdict(list)
    for block in blocks.values():
        if learned in block and baseline in block:
            families[block[learned]["family"]].append(
                block[learned][metric] - block[baseline][metric]
            )
    values = [statistics.mean(x) for x in families.values()]
    if not values:
        return None
    rng = random.Random(seed)
    samples = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(draws))
    return dict(
        difference=statistics.mean(values),
        interval95=[samples[int(draws * 0.025)], samples[int(draws * 0.975) - 1]],
        clusters=len(values),
        cluster_unit="mechanism family; both fresh-seed pairs kept together",
        scope="Descriptive paired percentile bootstrap; eight known families are not new domains",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", action="append")
    parser.add_argument("--learned-arm", default="adapted")
    args = parser.parse_args()
    arms = args.arm or ARMS
    if len(set(arms)) != len(arms) or args.learned_arm not in arms:
        parser.error("Require distinct arms including the learned arm")
    campaign = read(args.root / "CAMPAIGN.json")
    if campaign["stage"] not in {"completed", "failed"}:
        raise ValueError("Do not summarize an actively collecting cohort")
    manifest = read(args.manifest)
    starts = read(args.budget)["starts"]
    records, violations, hashes = [], [], {}
    for block in manifest["blocks"]:
        for trial in block["trials"]:
            root = args.root / trial["id"]
            receipt = read(args.root / (trial["id"] + "-receipt.json"), {})
            out = read(root / "OUTCOME.json", {})
            if not receipt:
                violations.append([trial["id"], "assigned_trial_has_no_controller_receipt"])
            if receipt.get("outcome", {}) != out:
                violations.append([trial["id"], "outcome_differs_from_controller_receipt"])
            ledger = read(root / "incident-ledger.json", {})
            feedback = feedback_measurement(ledger) if ledger else {}
            completion = completion_measurement(out, read(root / "worker_wait.json", {}), feedback)
            native = [s for s in starts if s["continuation"] == trial["id"] and s.get("native")]
            if out.get("native_starts", len(native)) != len(native):
                violations.append([trial["id"], "native_start_count_mismatch"])
            if any(s.get("ended_at") is None for s in native):
                violations.append([trial["id"], "native_start_not_closed"])
            elapsed = out.get("elapsed_seconds")
            if elapsed is None and receipt:
                elapsed = receipt["ended_at"] - receipt["started_at"]
            alerts = read(root / "monitor/alerts.json", [])
            error_path = root / "monitor/attention-errors.jsonl"
            errors = (
                [json.loads(line) for line in error_path.read_text().splitlines() if line]
                if error_path.is_file()
                else []
            )
            admissions, proposed, input_tokens, latencies = Counter(), Counter(), [], []
            for path in sorted((root / "monitor").glob("attention-*.json")):
                value = read(path)
                admission = value.get("admission", {})
                admissions[admission.get("reason", "unrecorded")] += 1
                response = value.get("result", {})
                proposed[response.get("decision", {}).get("action", "none")] += 1
                prediction = response.get("prediction", {})
                if prediction.get("input_tokens") is not None:
                    input_tokens.append(prediction["input_tokens"])
                if prediction.get("total_seconds") is not None:
                    latencies.append(prediction["total_seconds"])
            quality = out.get("quality", {})
            if quality and quality != read(root / "QUALITY.json"):
                violations.append([trial["id"], "quality_receipt_mismatch"])
            report, results = root / "research/REPORT.txt", root / "research/results.json"
            for key, value in [
                ("report_sha256", report.read_text() if report.is_file() else None),
                ("results_sha256", verifier_report_value(results)),
            ]:
                if quality.get(key) and digest(value) != quality[key]:
                    violations.append([trial["id"], key + "_mismatch"])
            for path in [
                root / "OUTCOME.json",
                root / "QUALITY.json",
                root / "incident-ledger.json",
            ]:
                if path.is_file():
                    hashes[str(path.relative_to(args.root))] = hashlib.sha256(
                        path.read_bytes()
                    ).hexdigest()
            records.append(
                dict(
                    **trial,
                    block=block["id"],
                    stage=out.get("stage", "missing"),
                    whole_workflow_verified=int(completion["whole_workflow_verified"]),
                    raw_quality=quality.get("verified_quality", 0),
                    elapsed_seconds=elapsed,
                    restricted_completion_seconds=elapsed
                    if completion["whole_workflow_verified"]
                    else 650.0,
                    native_starts=len(native),
                    automatic_alerts=len(alerts),
                    alert_actions=[a["action"] for a in alerts],
                    quiet_family=trial["family"] in QUIET,
                    required_feedback_misses=feedback.get("required_feedback_misses"),
                    finish_reason=out.get("finish_reason"),
                    error=out.get("error"),
                    monitor_error_count=len(errors),
                    monitor_error_messages=sorted({e["error"] for e in errors}),
                    results_artifact_exists=results.is_file(),
                    admissions=dict(admissions),
                    proposed_actions=dict(proposed),
                    input_token_range=[min(input_tokens), max(input_tokens)]
                    if input_tokens
                    else None,
                    prediction_latency_mean=statistics.mean(latencies) if latencies else None,
                    completion_censored=completion["completion_censored"],
                )
            )
    summary = {}
    for arm in arms:
        subset = [r for r in records if r["arm"] == arm]
        quiet = [r for r in subset if r["quiet_family"]]
        summary[arm] = dict(
            assigned=len(subset),
            verified=sum(r["whole_workflow_verified"] for r in subset),
            mean_native_starts=statistics.mean(r["native_starts"] for r in subset),
            mean_elapsed_seconds=statistics.mean(r["elapsed_seconds"] for r in subset)
            if all(r["elapsed_seconds"] is not None for r in subset)
            else None,
            mean_restricted_completion_seconds=statistics.mean(
                r["restricted_completion_seconds"] for r in subset
            ),
            automatic_alerts=sum(r["automatic_alerts"] for r in subset),
            quiet_trials=len(quiet),
            quiet_trials_with_alert=sum(r["automatic_alerts"] > 0 for r in quiet),
            collector_failed=sum(r["stage"] != "completed" for r in subset),
            trials_with_monitor_errors=sum(r["monitor_error_count"] > 0 for r in subset),
        )
    comparisons = {
        baseline: {
            metric: paired_interval(records, baseline, metric, learned=args.learned_arm)
            for metric in [
                "whole_workflow_verified",
                "native_starts",
                "restricted_completion_seconds",
            ]
        }
        for baseline in arms
        if baseline != args.learned_arm
    }
    args.output.mkdir(parents=True, exist_ok=False)
    put(args.output / "records.json", records)
    put(args.output / "hashes.json", hashes)
    put(
        args.output / "summary.json",
        dict(
            manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            arms=summary,
            **{args.learned_arm + "_minus_baseline": comparisons},
            violations=violations,
            limitations=[
                "All assigned failures retained; no patched-host results mixed into this cohort.",
                "Quiet-family alerts are a proxy for unnecessary attention, "
                "not independently adjudicated false alerts.",
                "Restricted completion assigns 650 seconds to failures; "
                "it is not actual measured runtime.",
                "Native sessions are stochastic; only one execution per arm/configuration.",
            ],
        ),
    )
    print(json.dumps(dict(arms=summary, violations=violations), indent=2))


if __name__ == "__main__":
    main()
