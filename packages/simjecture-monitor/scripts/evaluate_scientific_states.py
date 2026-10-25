"""Score constructed scientific state decisions; never claim executed intervention value."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from simjecture_monitor import attention_support as protocol
from simjecture_monitor.decision_interface import ROUTES, choice_from_answers
from simjecture_monitor.events import put


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--adapter")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--kernel-profile", choices=("fla-prefill",))
    parser.add_argument("--maximum-tokens", type=int, default=4096)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    from simjecture_monitor.decision_model import DecisionModel

    policy = DecisionModel(
        args.base,
        adapter=args.adapter,
        max_tokens=args.maximum_tokens,
        kernel_profile=args.kernel_profile,
    )
    policy.temperature = 1.0
    rows = [json.loads(line) for line in args.data.read_text().splitlines() if line]
    fields = Counter()
    families = defaultdict(Counter)
    summary = Counter()
    started = time.time()
    experts = {
        name
        for name, (action, _, _) in ROUTES.items()
        if action in {"request_worker_help", "wake_director", "request_repair_judge"}
    }
    with (args.output / "predictions.jsonl").open("w") as stream:
        for row in rows:
            family = row.get("provenance", {}).get("mechanism", "unspecified")
            result = dict(id=row["id"], group_id=row.get("group_id"), family=family)
            summary["rows"] += 1
            gold = row["targets"]["route"]["label"]
            allowed = row.get("acceptable_routes", [gold])
            summary["expert_preference_rows" if gold in experts else "quiet_preference_rows"] += 1
            families[family]["rows"] += 1
            try:
                prediction = policy.predict(row)
                answers = prediction["answers"]
                route = answers["route"]
                summary["strict_route_correct"] += route == gold
                summary["acceptable_route_correct"] += route in allowed
                families[family]["acceptable_route_correct"] += route in allowed
                summary["unnecessary_expert_proposals"] += gold not in experts and route in experts
                summary["missed_expert_preferences"] += gold in experts and route not in experts
                for name, value in answers.items():
                    fields[name] += value == str(row["targets"][name]["label"])
                summary["all_fields_exact"] += all(
                    value == str(row["targets"][name]["label"]) for name, value in answers.items()
                )
                choice = choice_from_answers(answers)
                try:
                    packet = protocol.Observation.model_validate(row["observation"])
                    view = protocol.pack(
                        packet, len, token_counter_id="assembly:characters", budget_tokens=100000
                    )
                    if view.text != row["state"]:
                        raise ValueError("Scientific state no longer reproduces the supplied input")
                    decision = protocol.bind_choice(
                        packet, view, choice, policy_id="state-evaluation"
                    )
                    grounded = (
                        choice.action
                        not in {"request_worker_help", "wake_director", "request_repair_judge"}
                        or bool(choice.evidence)
                        and choice.basis != "unspecified"
                    )
                    summary["valid_choices"] += 1
                    summary["grounded_choices"] += grounded
                    summary["valid_acceptable_routes"] += route in allowed and grounded
                    result["bound_decision"] = decision.model_dump()
                except ValueError as error:
                    summary["invalid_choices"] += 1
                    result["binding_error"] = str(error)
                result["prediction"] = prediction
            except Exception as error:
                summary["inference_failures"] += 1
                result["error"] = type(error).__name__ + ": " + str(error)[:500]
            stream.write(json.dumps(result) + "\n")
            if summary["rows"] % 32 == 0:
                stream.flush()
                put(
                    args.output / "status.json",
                    dict(stage="running", updated_at=time.time(), **summary),
                )
    report = dict(
        scope=(
            "Constructed scientific states and authored attention preferences, "
            "not real intervention outcomes"
        ),
        counts=dict(summary),
        field_correct=dict(fields),
        families={k: dict(v) for k, v in families.items()},
        dataset_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
        model_identity=policy.identity,
        started_at=started,
        ended_at=time.time(),
        acceptable_route_accuracy=summary["acceptable_route_correct"] / len(rows),
        valid_cited_acceptable_route_accuracy=summary["valid_acceptable_routes"] / len(rows),
        citation_metric_scope=(
            "Structural validity plus a nonempty visible citation and a specified basis for "
            "expert requests. This does not test semantic entailment or intervention utility. "
            "The legacy valid_grounded_acceptable_route_accuracy key is an identical alias."
        ),
        valid_grounded_acceptable_route_accuracy=summary["valid_acceptable_routes"] / len(rows),
    )
    put(args.output / "metrics.json", report)
    put(args.output / "status.json", dict(stage="completed", **summary))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
