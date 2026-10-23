"""Audit actual interventions, returned work, raw diagnostics and accounting coverage."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from simjecture_monitor.events import put


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def summarize(root):
    trial = load(root / "TRIAL.json", {})
    verified = load(root / "VERIFIED.json", {}).get("verified_runs", [])
    reported = load(root / "research/results.json", {}).get("runs", [])
    reported = {r.get("name"): r for r in reported if isinstance(r, dict)}
    checks = []
    for measured in verified:
        row = reported.get(measured["name"], {})
        agreement = {}
        for key in ("relative_field_error", "relative_charge_residual"):
            value = row.get(key)
            agreement[key] = isinstance(value, (int, float)) and math.isclose(
                value, measured[key], rel_tol=1e-8, abs_tol=1e-22
            )
        agreement["original_checks_passed"] = (
            row.get("original_checks_passed") is measured["original_checks_passed"]
        )
        checks.append(dict(name=measured["name"], agreement=agreement))
    decisions = [load(p) for p in sorted((root / "monitor").glob("decision-*.json"))]
    model = [
        r["decision"]
        for r in decisions
        if r.get("decision", {}) and r["decision"].get("policy") == "intern-decision-4b"
    ]
    alerts = load(root / "monitor/alerts.json", [])
    authorities = [load(p) for p in (root / "monitor_authority").glob("*/result.json")]
    usage = dict(trial.get("usage", {}))
    measured_threads = {}
    missing = []
    for role, bundle in [
        ("parent_and_helpers", usage),
        *[(f"authority_{i}", r.get("usage", {})) for i, r in enumerate(authorities)],
    ]:
        for thread, counts in bundle.get("usage_by_thread", {}).items():
            # Thread IDs are unique across native actors; resumed counters are cumulative.
            measured_threads[thread] = counts
        if bundle.get("usage_unreported_threads") or bundle.get("usage_unidentified_calls", 0):
            missing.append(
                dict(
                    role=role,
                    threads=bundle.get("usage_unreported_threads", {}),
                    unidentified=bundle.get("usage_unidentified_calls", 0),
                )
            )
    totals = {
        key: sum(v.get(key, 0) or 0 for v in measured_threads.values())
        for key in ("input_tokens", "cached_input_tokens", "output_tokens")
    }
    if len(model) > 0:
        latencies = dict(
            median_forward=statistics.median(r["forward_seconds"] for r in model),
            median_transport=statistics.median(r["transport_seconds"] for r in model),
            total_forward=sum(r["forward_seconds"] for r in model),
            input_tokens=sum(r["input_tokens"] for r in model),
        )
    else:
        latencies = None
    receipts = [load(p) for p in (root / "research/runs").glob("*/receipt.json")]
    return dict(
        trial=root.name,
        case=trial.get("case"),
        policy=trial.get("policy"),
        stage=trial.get("stage"),
        error=trial.get("error"),
        wall_seconds=trial.get("ended_at", 0) - trial.get("started_at", 0)
        if trial.get("ended_at")
        else None,
        worker_turns=len(trial.get("turns", [])),
        parent_session_count=len(
            {r.get("session") for r in trial.get("turns", []) if r.get("session")}
        ),
        report_present=trial.get("report_present", False),
        pending_feedback_after_final_report=trial.get("pending_feedback_after_final_report"),
        fresh_simulations=len(receipts),
        solver_seconds=sum(r.get("wall_seconds", 0) for r in receipts),
        verified_runs=len(verified),
        worker_metrics_agree=bool(checks) and all(all(r["agreement"].values()) for r in checks),
        metric_checks=checks,
        model_inferences=len(model),
        monitor_errors=sum(bool(r.get("error")) for r in decisions),
        model_choices=dict(Counter(r["choice"] for r in model)),
        alert_choices=dict(Counter(a["action"] for a in alerts)),
        director_calls=len(list((root / "director").glob("*.json"))),
        helper_tasks=len(list((root / "helper_tasks").glob("*.json"))),
        authority_calls=len(authorities),
        authority_origins=dict(
            Counter(r.get("incident", {}).get("origin", "unknown") for r in authorities)
        ),
        authority_verdicts=dict(
            Counter(r.get("verdict", {}).get("decision", "failed") for r in authorities)
        ),
        repairs_applied=sum(
            r.get("deployment", {}).get("status") == "applied" for r in authorities
        ),
        latency=latencies,
        reported_usage=totals,
        usage_gaps=missing,
        usage_is_lower_bound=bool(missing),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [summarize(p.parent) for p in sorted(args.root.glob("live-*/TRIAL.json"))]
    result = dict(
        scope=(
            "Exploratory real-worker outcomes. No statistical effect estimate, calibrated "
            "detector score, or RL benefit is established."
        ),
        source=load(args.root / "BATCH.json"),
        trials=rows,
        limitations=[
            "One stochastic trajectory per case/policy; downstream judge behavior varies.",
            "Initial model arms include transport outages; errors are retained.",
            "The fixed two-turn cap can leave late feedback undelivered; flagged explicitly.",
            "Missing provider counters remain missing, not zero-cost calls.",
            (
                "Injected harness and analysis defects are engineering fixtures; actual WarpX"
                " outputs are independently checked."
            ),
            (
                "The nominal healthy task advertised four runs while its wrapper allowed two;"
                " escalations after exhausting that wrapper are not clean false-alarm "
                "examples."
            ),
        ],
    )
    put(args.output, result)
    for r in rows:
        print(
            r["case"],
            r["policy"],
            r["stage"],
            "metrics",
            r["worker_metrics_agree"],
            "alerts",
            r["alert_choices"],
            "monitor_errors",
            r["monitor_errors"],
            "pending_feedback",
            r["pending_feedback_after_final_report"],
        )


if __name__ == "__main__":
    main()
