"""Separate C/D scoring and sequential paired checkpoint selection."""

from __future__ import annotations

import json
import math
import os
import random
import statistics
from collections import defaultdict
from pathlib import Path

C_WEIGHTS = {
    "truth_or_valid_evidence": 40,
    "independent_replication_and_prediction": 35,
    "numerical_validity_scope_uncertainty": 25,
}
D_WEIGHTS = {
    "experiment_choice_discrimination": 30,
    "parameters_resolution_scale": 25,
    "evidence_adaptation": 25,
    "series_and_budget": 20,
}


def score(components, weights):
    if set(components) != set(weights):
        raise ValueError("All registered score components are required")
    if any(not math.isfinite(value) or not 0 <= value <= weights[key] for key, value in components.items()):
        raise ValueError("Component score outside its registered range")
    return math.fsum(components.values())


def paired_interval(records, metric, alpha, seed=20261116, replicates=20000):
    groups = defaultdict(list)
    for record in records:
        groups[record["mechanism_group"]].append(record["candidate"][metric] - record["baseline"][metric])
    if len(groups) < 8:
        raise ValueError("Too few independent mechanisms for the registered bootstrap selection procedure")
    clusters = list(groups.values())
    rng = random.Random(seed)
    sampled_means = []
    for _ in range(replicates):
        sample = [value for _ in clusters for value in rng.choice(clusters)]
        sampled_means.append(statistics.fmean(sample))
    sampled_means.sort()
    lo = sampled_means[max(0, min(replicates - 1, int(replicates * alpha / 2)))]
    hi = sampled_means[max(0, min(replicates - 1, math.ceil(replicates * (1 - alpha / 2)) - 1))]
    return dict(
        mean=statistics.fmean([x for cluster in clusters for x in cluster]),
        low=lo,
        high=hi,
        alpha=alpha,
        mechanism_groups=len(clusters),
        replicates=replicates,
    )


def checkpoint_result(records, evaluation_index):
    if any(record.get("comparison") != "current_best_checkpoint" for record in records):
        raise ValueError("Checkpoint improvement must be paired against the current incumbent")
    alpha = 0.05 / (evaluation_index * (evaluation_index + 1))
    # Divide the per-look allowance across the two simultaneously monitored scores.
    C = paired_interval(records, "C", alpha / 2)
    D = paired_interval(records, "D", alpha / 2)
    return dict(
        C=C,
        D=D,
        reliable_improvement=C["low"] > 2 and D["low"] > -2,
        reliable_regression=C["high"] < -2 or D["high"] < -2,
        inference="approximate_cluster_bootstrap; alpha spending does not establish exact finite-sample coverage",
    )


def stopping_update(previous, result, checkpoint, collapse_with_adaptation_loss=False):
    state = dict(previous)
    if result["reliable_improvement"]:
        state.update(best_checkpoint=checkpoint, no_improvement=0)
    else:
        state["no_improvement"] = state.get("no_improvement", 0) + 1
    state["regression"] = state.get("regression", 0) + 1 if result["reliable_regression"] else 0
    state["collapse"] = state.get("collapse", 0) + 1 if collapse_with_adaptation_loss else 0
    state["stop"] = (
        state.get("no_improvement", 0) >= 4 or result["reliable_regression"] or collapse_with_adaptation_loss
    )
    return state


def persist_development_result(
    *,
    records,
    evaluation_index,
    candidate_checkpoint,
    checkpoint_directory,
    rl_inbox,
    initial_checkpoint,
    collapse_with_adaptation_loss=False,
):
    directory = Path(checkpoint_directory)
    selection_path = directory / "selection.json"
    state = (
        json.loads(selection_path.read_bytes())
        if selection_path.exists()
        else {"best_checkpoint": str(initial_checkpoint)}
    )
    if evaluation_index != state.get("last_evaluation_index", 0) + 1:
        raise ValueError("Development results must be applied once in sequence")
    if len(records) != 16 or len({row["task_id"] for row in records}) != 16:
        raise ValueError("Every development evaluation must include all sixteen tasks")
    result = checkpoint_result(records, evaluation_index)
    updated = stopping_update(state, result, str(candidate_checkpoint), collapse_with_adaptation_loss)
    updated["last_evaluation_index"] = evaluation_index
    updated["last_result"] = result
    directory.mkdir(parents=True, exist_ok=True)

    def save(path, value):
        partial = path.with_suffix(path.suffix + ".partial")
        with partial.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(partial, path)

    # Pin the chosen model before exposing the updated selection state to the trainer.
    best = updated.get("best_checkpoint")
    if best:
        save(directory / "retain.json", [Path(best).name])
    save(selection_path, updated)
    if updated["stop"]:
        inbox = Path(rl_inbox)
        inbox.mkdir(parents=True, exist_ok=True)
        save(
            inbox / "stop.json",
            dict(evaluation_index=evaluation_index, best_checkpoint=best, reason="development_stopping_rule"),
        )
    return updated
