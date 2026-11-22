"""Create public train/dev tasks and a 240-trajectory collection manifest. No solver calls."""

import json
import random
from collections import Counter
from pathlib import Path

from task_families import FAMILIES

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ["基础规律验证", "多参数耦合", "竞争机制辨别", "开放性科学探索"]
BUDGETS = [3600, 10800, 21600, 43200]


def make_family_tasks(family):
    (
        split,
        family_id,
        domain,
        mechanism,
        title,
        equations,
        initial,
        parameters,
        hypotheses,
        observables,
        questions,
        solvers,
        source,
    ) = family
    records = []
    for level, question in enumerate(questions, 1):
        seed = int.from_bytes((family_id + str(level)).encode(), "little") % 2147483647
        rng = random.Random(seed)
        instance = {key: round(rng.uniform(*bounds), 8) for key, bounds in parameters.items()}
        records.append(
            dict(
                task_id=f"{family_id}-L{level}",
                split=split,
                domain=domain,
                difficulty=level,
                difficulty_name=LEVELS[level - 1],
                mechanism_group=mechanism,
                family_group=family_id,
                question=question,
                topic=title,
                equations=equations,
                initial_boundary_conditions=initial,
                parameter_space=parameters,
                initial_parameter_configuration=instance,
                perturbation_seed=seed,
                hypotheses=hypotheses,
                observables=observables,
                solver_candidates=solvers,
                total_wall_seconds=BUDGETS[level - 1],
                controls=[
                    "独立空间和时间收敛",
                    "守恒或物理收支",
                    "初态及边界一致性",
                    "随机误差或统计不确定性",
                    "预注册新条件预测与留出复核",
                ],
                numerical_tolerances="由参考程序误差、独立收敛及效应大小预注册，禁止观察处理组后放宽",
                scope_statement="研究问题与物理范围固定，单次规模、精度、次数及层级由研究者在总预算内决定",
                expected_answer_visible=False,
                task_intent=[
                    "law_validation",
                    "applicability_boundary",
                    "competing_mechanisms",
                    "open_exploration",
                ][level - 1],
                source_urls=[source],
                authoring_status="authored_pending_solver_qualification",
            )
        )
    return records


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


def main():
    tasks = [task for family in FAMILIES if family[0] == "train" for task in make_family_tasks(family)]
    # Development tasks cover independent research questions instead of four
    # difficulty variants of the same development mechanism.
    from development_tasks import development_tasks

    tasks.extend(development_tasks())
    for split in ["train", "dev"]:
        selected = [task for task in tasks if task["split"] == split]
        write_jsonl(ROOT / "tasks" / f"{split}.jsonl", selected)
    manifest = [
        dict(
            collection_id=f"{task['task_id']}-SFT-{trial}",
            task_id=task["task_id"],
            split="train",
            teacher="gpt-6.1-sol",
            trial=trial,
            teacher_strategy=["证伪优先", "多精度与资源分配", "竞争机制辨别"][trial - 1],
            evidence_source="future_actual_live_Simjecture_execution",
            status="not_generated",
        )
        for task in tasks
        if task["split"] == "train"
        for trial in range(1, 4)
    ]
    write_jsonl(ROOT / "data" / "sft_collection_manifest.jsonl", manifest)
    counts = {
        split: dict(Counter(task["domain"] for task in tasks if task["split"] == split))
        for split in ["train", "dev"]
    }
    (ROOT / "tasks" / "public_catalog_summary.json").write_text(
        json.dumps(
            dict(
                counts=counts,
                train_tasks=80,
                development_tasks=16,
                initial_trajectories=240,
                generated_trajectories=0,
                historical_training_data_reused=0,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    lines = [
        "# 训练与开发命题",
        "",
        "每个研究问题保留独立初值、状态与执行目录。同一机制的全部难度留在同一数据划分内。",
        "",
        "|编号|划分|等级|领域|研究问题|",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"|{t['task_id']}|{t['split']}|{t['difficulty_name']}|{t['domain']}|{t['question']}|" for t in tasks
    ]
    (ROOT / "tasks" / "训练与开发命题目录.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(dict(counts=counts, tasks=len(tasks), planned_sft=len(manifest), simulations=0)))


if __name__ == "__main__":
    main()
