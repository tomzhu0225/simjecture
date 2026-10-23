"""Audit frozen v1 learning data without inventing rewards or worker continuations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from simjecture_monitor.events import digest, put


def observed_view(record):
    packet = record["packet"]
    if digest(packet["state"]) != packet["packet_sha256"]:
        raise ValueError("Original observation packet hash mismatch")
    receipt = record.get("model_view")
    if receipt is None:
        return None
    view = copy.deepcopy(packet["state"])
    included = receipt["included_event_ids"]
    view["events"] = [event for event in view["events"] if event["id"] in included]
    if [event["id"] for event in view["events"]] != included:
        raise ValueError("Model view receipt has invalid event identities or ordering")
    if digest(view) != receipt["state_sha256"]:
        raise ValueError("Reconstructed model-visible state does not match its receipt")
    return view


def visible_status_mismatch(view):
    for event in view["events"]:
        body = event["body"]
        if body.get("type") != "command_execution":
            continue
        for line in body.get("aggregated_output", "").splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if (
                isinstance(value, dict)
                and value.get("reported_status") == "running"
                and value.get("process_receipt_status") in {"succeeded", "failed"}
            ):
                return True
    return False


def request_provenance(episode_root, request):
    alerts_path = episode_root / "monitor/alerts.json"
    alerts = json.loads(alerts_path.read_text()) if alerts_path.exists() else []
    if request.get("origin") == "coprocessor" or any(
        alert.get("help_request") == request["id"] for alert in alerts
    ):
        return dict(origin="coprocessor", evidence="host request/alert binding")
    path = episode_root / "monitor/events.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            event = json.loads(line)
            body = event["body"]
            if (
                body.get("type") == "command_execution"
                and ".request_help(" in body.get("command", "")
                and re.search(
                    r'(?m)^\s*\{\s*"id"\s*:\s*"' + re.escape(request["id"]) + '"',
                    body.get("aggregated_output", ""),
                )
            ):
                return dict(
                    origin="worker", evidence="public request creation event", event_id=event["id"]
                )
    return dict(origin="unknown", evidence="no verified creation provenance")


def audit(root, dataset_path):
    before = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    data = json.loads(dataset_path.read_text())
    episodes = []
    totals = Counter()
    for episode in data["episodes"]:
        episode_root = root / "rl-clean" / episode["id"]
        rows = {}
        for path in (episode_root / "monitor").glob("decision-*.json"):
            row = json.loads(path.read_text())
            if row.get("decision"):
                rows[(row["packet"]["packet_sha256"], row["decision"]["prompt_sha256"])] = row
        counts = Counter()
        proposals = []
        for record in episode["decisions"]:
            view = observed_view(record)
            counts["decisions"] += 1
            if view is None:
                counts["model_views_unmeasured"] += 1
                continue
            counts["model_views_verified"] += 1
            identifier_visible = episode["id"] in json.dumps(view)
            counts["episode_identifier_visible"] += identifier_visible
            if record["action"] == "defer":
                continue
            row = rows[(record["packet"]["packet_sha256"], record["prompt_sha256"])]
            accepted = bool(row.get("alert"))
            counts["nondefer_proposals"] += 1
            counts["alerts_accepted"] += accepted
            counts["proposals_suppressed_by_gate"] += not accepted
            if row["decision"].get("greedy_choice") == "defer":
                counts["nondefer_sample_with_greedy_defer"] += 1
            proposals.append(
                dict(
                    received_at=row["received_at"],
                    action=record["action"],
                    greedy_action=row["decision"].get("greedy_choice"),
                    accepted_by_gate=accepted,
                    episode_identifier_visible=identifier_visible,
                    visible_process_status_mismatch=visible_status_mismatch(view),
                    last_visible_repair_applied=(
                        (view.get("host_state", {}).get("last_authority_outcome") or {}).get(
                            "deployment"
                        )
                        == "applied"
                    ),
                    packet_sha256=record["packet"]["packet_sha256"],
                )
            )
        report = episode_root / "research/REPORT.txt"
        after_report_cancellations = 0
        canceled_requests = []
        for path in (episode_root / "help_requests").glob("*.json"):
            request = json.loads(path.read_text())
            if (
                report.exists()
                and request.get("cancellation_reason")
                and request["created_at"] > report.stat().st_mtime
            ):
                after_report_cancellations += 1
                canceled_requests.append(
                    dict(
                        request_id=request["id"],
                        provenance=request_provenance(episode_root, request),
                    )
                )
        independently_reported = bool(episode["outcome"]["worker_metrics_agree"])
        verified = json.loads((episode_root / "VERIFIED.json").read_text())
        controls = {64, 128} <= {r["cells"] for r in verified.get("verified_runs", [])}
        metric_only_quality = int(independently_reported and controls and report.exists())
        costs = 0.02 * episode["capable_agent_invocations"] + 0.1 * min(
            episode["elapsed_seconds"] / 650, 1
        )
        episodes.append(
            dict(
                episode=episode["id"],
                family=episode["case"],
                counts=dict(counts),
                original_quality=episode["quality"],
                original_return=episode["reward"],
                report_metrics_agree=independently_reported,
                metric_only_quality_sensitivity=metric_only_quality,
                metric_only_return_sensitivity=metric_only_quality - costs,
                post_report_canceled_help_requests=after_report_cancellations,
                canceled_request_provenance=canceled_requests,
                proposals=proposals,
                reward_v2_eligible=False,
                missing_measurements=[
                    "matched waiting continuation",
                    "explicit needed-feedback acknowledgment audit",
                    "dispatched duplicate accounting by incident identity",
                ],
            )
        )
        totals.update(counts)
    family_sensitivity = {}
    for family in sorted({e["family"] for e in episodes}):
        group = [e for e in episodes if e["family"] == family]
        old = max(e["original_return"] for e in group) - min(e["original_return"] for e in group)
        new = max(e["metric_only_return_sensitivity"] for e in group) - min(
            e["metric_only_return_sensitivity"] for e in group
        )
        family_sensitivity[family] = dict(
            original_return_gap=old,
            metric_only_return_gap=new,
            relative_gap_reduction=1 - new / old if old else None,
        )
    if hashlib.sha256(dataset_path.read_bytes()).hexdigest() != before:
        raise ValueError("Frozen source dataset changed during audit")
    return dict(
        scope=(
            "Historical data audit and reward-definition sensitivity only; no new model "
            "training, new labels, paired worker outcomes or causal effect estimate."
        ),
        source_dataset_sha256=before,
        counts=dict(totals),
        episodes=episodes,
        family_return_sensitivity=family_sensitivity,
        interpretations=[
            "Visible case-labelled identifiers are a leakage risk, not proof the model used them.",
            "Missing a parsed status mismatch does not prove an alert was unjustified.",
            "A judge denial is not automatically an unnecessary intervention.",
            "The metric-only sensitivity omits feedback quality and is not a recommended reward.",
            "Suppressed proposals are not actual capable-agent dispatches.",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.data)
    put(args.output, result)
    print(
        json.dumps(
            dict(
                counts=result["counts"],
                family_return_sensitivity=result["family_return_sensitivity"],
            )
        )
    )


if __name__ == "__main__":
    main()
