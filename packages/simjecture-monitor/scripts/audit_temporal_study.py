"""Bind time observations, raw model choices and actual native repair dispatches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_parked_study import audit, fingerprint, load
from simjecture_monitor.events import digest, put


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    result = audit(root, args.budget.resolve())
    for row in result["rows"]:
        trial = root / row["root"]
        events_file = trial / "monitor/events.jsonl"
        events = [json.loads(line) for line in events_file.read_text().splitlines()]
        clocks = [e for e in events if e["id"].startswith("parking-clock:")]
        for event in clocks:
            assert digest(event["body"]) == event["source_sha256"]
        decisions = {
            d["packet"]["packet_sha256"]: (d, p)
            for p in (trial / "monitor").glob("decision-*.json")
            for d in [load(p)]
        }
        deferred_file = trial / "GRACE_DEFERRALS.json"
        deferrals = load(deferred_file) if deferred_file.exists() else []
        for item in deferrals:
            decision, _ = decisions[item["packet_sha256"]]
            assert decision["decision"]["choice"] == "request_repair_judge"
            assert item["contradiction_age_seconds"] < 10
        clock_routes = []
        for authority in load(trial / "LIVE.json")["authority_results"]:
            incident = authority.get("incident", {})
            if incident.get("origin") != "coprocessor":
                continue
            selected = decisions.get(incident.get("packet_sha256"))
            if selected is None:
                continue
            decision, path = selected
            clock_ids = [
                e["id"]
                for e in decision["packet"]["state"]["events"]
                if e["id"].startswith("parking-clock:")
            ]
            if clock_ids:
                clock_routes.append(
                    dict(
                        packet_sha256=incident["packet_sha256"],
                        raw_choice=decision["decision"]["choice"],
                        clock_ids=clock_ids,
                        decision_file_sha256=fingerprint(path),
                        authority_started_at=authority["started_at"],
                        verdict=authority.get("verdict", {}).get("decision"),
                        deployment=authority.get("deployment", {}).get("status"),
                    )
                )
        row.update(
            timer_events=len(clocks),
            timer_event_ids=[e["id"] for e in clocks],
            events_file_sha256=fingerprint(events_file),
            host_grace_deferrals=deferrals,
            grace_file_sha256=fingerprint(deferred_file) if deferred_file.exists() else None,
            clock_driven_authority=clock_routes,
            timer_repair_loop_exercised_before_fallback=(
                bool(deferrals)
                and bool(clocks)
                and any(r["deployment"] == "applied" for r in clock_routes)
                and row["wake_reason"] == "adapter_completion"
                and row["quality"] == 1
                and row["required_feedback_misses"] == 0
            ),
        )
    result["total_timer_events"] = sum(r["timer_events"] for r in result["rows"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    put(args.output, result)
    print(
        json.dumps(
            dict(
                trajectories=len(result["rows"]),
                timer_events=result["total_timer_events"],
                exercised=sum(
                    r["timer_repair_loop_exercised_before_fallback"] for r in result["rows"]
                ),
            )
        )
    )


if __name__ == "__main__":
    main()
