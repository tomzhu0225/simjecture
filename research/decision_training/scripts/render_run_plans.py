"""Render research job manifests and balanced online groups. No jobs are launched."""

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(name, rows):
    path = ROOT / "plans" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main():
    protocol = json.loads((ROOT / "config/protocol.json").read_bytes())
    train = [
        json.loads(line) for line in (ROOT / "tasks/train.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    dev = [json.loads(line) for line in (ROOT / "tasks/dev.jsonl").read_text(encoding="utf-8").splitlines()]
    tests = json.loads((ROOT / "tasks/test_manifest.json").read_bytes())["task_ids"]
    teachers = [
        dict(
            job_id=f"{task['task_id']}-teacher-{trial}",
            stage="sft_collection",
            task_id=task["task_id"],
            split="train",
            teacher="gpt-6.1-sol",
            total_wall_seconds=task["total_wall_seconds"],
            trial=trial,
            status="prepared_not_started",
        )
        for task in train
        for trial in range(1, 4)
    ]
    baseline = [
        dict(
            job_id=task["task_id"] + "-dev-baseline",
            task_id=task["task_id"],
            split="dev",
            arm="simjecture",
            total_wall_seconds=task["total_wall_seconds"],
            status="prepared_not_started",
        )
        for task in dev
    ]
    formal = []
    attribution = []
    for index, identifier in enumerate(tests):
        arms = list(protocol["arms"])
        random.Random(20261116 + index).shuffle(arms)
        for order, arm in enumerate(arms):
            formal.append(
                dict(
                    job_id=f"{identifier}-{arm}",
                    task_id=identifier,
                    split="test",
                    arm=arm,
                    paired_seed_group=identifier,
                    randomized_order=order,
                    task_contract="evaluator_releases_after_freeze",
                    status="sealed_not_started",
                )
            )
        for arm in ["independent_host", "host_with_final9b_advice"]:
            attribution.append(
                dict(
                    job_id=f"{identifier}-attribution-{arm}",
                    task_id=identifier,
                    split="test",
                    arm=arm,
                    pair_id=identifier + "-advice-pair",
                    anchor="precommitted_baseline_prefix_state",
                    equal_remaining_budget=True,
                    common_random_stream=True,
                    status="sealed_not_started",
                )
            )
    groups = []
    order = list(range(len(train)))
    random.Random(20261116).shuffle(order)
    for index, task_index in enumerate(order):
        task = train[task_index]
        groups.append(
            dict(
                group_template=f"sweep-1-group-{index + 1:04d}",
                task_id=task["task_id"],
                split="train",
                trajectories=4,
                total_wall_seconds_per_trajectory=task["total_wall_seconds"],
                freeze_policy_during_group=True,
                development_after_group=(index + 1) % 20 == 0,
                initial_state_shared_by_group=True,
                status="prepared_not_started",
            )
        )
    write("teacher_collection.jsonl", teachers)
    write("development_baselines.jsonl", baseline)
    write("formal_comparison.jsonl", formal)
    write("advice_attribution.jsonl", attribution)
    write("rl_first_balanced_sweep.jsonl", groups)
    print(
        json.dumps(
            dict(
                teacher_studies=len(teachers),
                development_baselines=len(baseline),
                formal_studies=len(formal),
                attribution_branches=len(attribution),
                initial_RL_groups=len(groups),
                initial_RL_trajectories=4 * len(groups),
                jobs_started=0,
            )
        )
    )


if __name__ == "__main__":
    main()
