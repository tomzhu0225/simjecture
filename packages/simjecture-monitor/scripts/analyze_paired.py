"""Audit the saved paired cohort and expose utility-component sensitivity."""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
from collections import defaultdict
from pathlib import Path

from simjecture_monitor.accounting import native_usage
from simjecture_monitor.events import digest, put
from simjecture_monitor.reward import ContinuationOutcome, RewardWeights, paired_reward


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def audit(root):
    design = load(root / "DESIGN.json")
    budget = load(root / "native-budget.json")
    pairs, failures, audits = [], [], []
    for case in design["cases"]:
        checkpoint = root / case["checkpoint"]
        manifest = load(checkpoint / "checkpoint.json")
        packet = load(checkpoint / "observation.json")
        if manifest is None or packet is None:
            failures.append(dict(checkpoint=case["checkpoint"], reason="missing_checkpoint"))
            continue
        audits.append(
            dict(
                checkpoint=case["checkpoint"],
                kind=case["kind"],
                observation_hash_matches=digest(packet["state"]) == packet["packet_sha256"],
                context_hashes_match=all(
                    digest(manifest[k]) == manifest[k + "_sha256"]
                    for k in ["criteria", "worker_config", "downstream_policy"]
                ),
                actor_view_contains_assignment_label=any(
                    label in json.dumps(packet)
                    for label in [c["kind"] for c in design["cases"] if c["kind"] != "healthy"]
                ),
            )
        )
        for pair in case["pairs"]:
            outcomes = []
            receipts = []
            for branch in pair["branches"]:
                path = root / branch["root"] / "OUTCOME.json"
                if not path.exists():
                    failures.append(dict(root=branch["root"], reason="missing_outcome"))
                    continue
                outcome = ContinuationOutcome.model_validate(load(path))
                quality = load(root / branch["root"] / "QUALITY.json")
                restore = load(root / branch["root"] / "RESTORE.json")
                native = [
                    r
                    for r in budget["starts"]
                    if r["continuation"] == branch["root"] and r.get("native")
                ]
                receipt = dict(
                    root=branch["root"],
                    action=branch["action"],
                    quality_digest_matches=digest(quality) == outcome.quality_receipt_sha256,
                    restored_exact_checkpoint=restore["restored"]
                    == restore["expected"]
                    == manifest["artifacts"],
                    native_start_count_matches=len(native) == outcome.capable_agent_starts,
                    checkpoint_bindings_match=all(
                        getattr(outcome, key) == expected
                        for key, expected in {
                            "common_prefix_sha256": manifest["common_prefix_sha256"],
                            "observation_sha256": packet["packet_sha256"],
                            "criteria_sha256": manifest["criteria_sha256"],
                            "worker_config_sha256": manifest["worker_config_sha256"],
                            "downstream_policy_sha256": manifest["downstream_policy_sha256"],
                        }.items()
                    ),
                    quality=outcome.verified_quality,
                    starts=outcome.capable_agent_starts,
                    elapsed_seconds=outcome.elapsed_seconds,
                    required_feedback_misses=outcome.required_feedback_misses,
                    duplicates=outcome.duplicate_wakeups,
                )
                receipts.append(receipt)
                outcomes.append(outcome)
            action = next((o for o in outcomes if o.action != "defer"), None)
            waiting = next((o for o in outcomes if o.action == "defer"), None)
            score = paired_reward(action, waiting) if action else dict(eligible=False, reward=None)
            pairs.append(dict(kind=case["kind"], pair=pair["id"], receipts=receipts, score=score))
    families = defaultdict(list)
    for pair in pairs:
        if pair["score"]["eligible"]:
            families[pair["kind"]].append(pair)
    summaries = []
    for kind, rows in families.items():
        intervention = [next(r for r in p["receipts"] if r["action"] != "defer") for p in rows]
        waiting = [next(r for r in p["receipts"] if r["action"] == "defer") for p in rows]
        summaries.append(
            dict(
                kind=kind,
                pairs=len(rows),
                rewards=[p["score"]["reward"] for p in rows],
                mean_reward=statistics.mean(p["score"]["reward"] for p in rows),
                intervention_quality=[r["quality"] for r in intervention],
                waiting_quality=[r["quality"] for r in waiting],
                intervention_starts=[r["starts"] for r in intervention],
                waiting_starts=[r["starts"] for r in waiting],
                intervention_seconds=[r["elapsed_seconds"] for r in intervention],
                waiting_seconds=[r["elapsed_seconds"] for r in waiting],
                intervention_feedback_misses=[r["required_feedback_misses"] for r in intervention],
                waiting_feedback_misses=[r["required_feedback_misses"] for r in waiting],
                intervention_duplicates=[r["duplicates"] for r in intervention],
                waiting_duplicates=[r["duplicates"] for r in waiting],
            )
        )
    sensitivity = []
    for starts, wall, feedback, duplicate in itertools.product(
        [0, 0.01, 0.02, 0.05, 0.1], [0, 0.1, 0.3], [0, 0.05], [0, 0.02]
    ):
        weights = RewardWeights(
            agent_start=starts,
            wall_time=wall,
            required_feedback_miss=feedback,
            duplicate_wakeup=duplicate,
        )
        rewards = []
        for case in design["cases"]:
            for pair in case["pairs"]:
                outcomes = [load(root / b["root"] / "OUTCOME.json") for b in pair["branches"]]
                if any(o is None for o in outcomes):
                    continue
                outcomes = [ContinuationOutcome.model_validate(o) for o in outcomes]
                chosen = next(o for o in outcomes if o.action != "defer")
                waiting = next(o for o in outcomes if o.action == "defer")
                score = paired_reward(chosen, waiting, weights)
                if score["eligible"]:
                    rewards.append(score["reward"])
        sensitivity.append(
            dict(
                weights=weights.model_dump(),
                pairs=len(rewards),
                positive=sum(r > 0 for r in rewards),
                mean_reward=statistics.mean(rewards) if rewards else None,
            )
        )
    receipt_checks = [
        all(
            r[k]
            for k in [
                "quality_digest_matches",
                "restored_exact_checkpoint",
                "native_start_count_matches",
                "checkpoint_bindings_match",
            ]
        )
        for p in pairs
        for r in p["receipts"]
    ]
    complete = (
        len(receipt_checks) == 32
        and all(receipt_checks)
        and not failures
        and all(
            a["observation_hash_matches"]
            and a["context_hashes_match"]
            and not a["actor_view_contains_assignment_label"]
            for a in audits
        )
    )
    model_gate = dict(
        collection_complete=complete,
        reason=(
            "Pilot actions were prespecified; no on-policy learning data. Eight task "
            "templates alone do not provide task-disjoint training and test cohorts."
        ),
        on_policy_training_eligible=False,
        consistent_positive_cases=[
            s["kind"]
            for s in summaries
            if len(s["rewards"]) == 2 and all(r > 0.03 for r in s["rewards"])
        ],
        interpretation=(
            "Positive repeated utility suggests an expanded study; "
            "it does not establish model efficacy"
        ),
    )
    return dict(
        schema=1,
        design_sha256=design["design_sha256"],
        pairs=pairs,
        families=summaries,
        checkpoints=audits,
        failures=failures,
        receipts_complete=complete,
        sensitivity=sensitivity,
        model_study_gate=model_gate,
        native_usage_by_continuation={
            b["root"]: native_usage(root / b["root"])
            for c in design["cases"]
            for p in c["pairs"]
            for b in p["branches"]
            if (root / b["root"] / "OUTCOME.json").exists()
        },
        scope=(
            "Small matched public-context continuation study; "
            "no hidden-state or population causal estimate"
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    put(args.output, result)
    print(
        json.dumps(
            dict(
                receipts_complete=result["receipts_complete"],
                families=result["families"],
                gate=result["model_study_gate"],
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
