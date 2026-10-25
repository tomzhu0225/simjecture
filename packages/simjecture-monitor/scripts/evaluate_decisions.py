"""Persist exact masked predictions and score frozen public decision suites.

Uses the pinned upstream Jevbench scorer. Benchmark labels never enter prompts.
This is decision retention evaluation, not scientific-worker outcome evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

from simjecture_monitor.decision_interface import options
from simjecture_monitor.events import put


def target(question, row_target):
    value = question.get("answer", row_target)
    result = value["label"] if "label" in value else value[question["type"]]
    if question["type"] == "noul":
        return "yes" if str(result).lower() in {"yes", "true", "1", "1.0"} else "no"
    return str(int(result) if isinstance(result, float) and result.is_integer() else result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--adapter")
    parser.add_argument("--suite-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-tokens", type=int, default=8192)
    parser.add_argument("--kernel-profile", choices=("fla-prefill",))
    parser.add_argument("--temperature", type=float, default=1.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    from jevbench.scoring import score_task
    from jevbench.tasks import Task
    from simjecture_monitor.decision_model import DecisionModel

    policy = DecisionModel(
        args.base,
        adapter=args.adapter,
        max_tokens=args.maximum_tokens,
        kernel_profile=args.kernel_profile,
    )
    policy.temperature = args.temperature
    datasets = [
        ("jevbench-" + name, args.suite_root / "jevbench" / (name + ".jsonl"))
        for name in ("easy", "original", "hard")
    ]
    datasets += [
        (name, args.suite_root / name / "test.jsonl")
        for name in ("toolace", "typed_decisions", "agnews", "wildjailbreak")
    ]
    started = time.time()
    results = {}
    for name, path in datasets:
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        correct, total, failures = 0, 0, 0
        with (args.output / (name + ".jsonl")).open("w") as stream:
            for number, raw in enumerate(rows):
                row = (
                    dict(id=raw["id"], state=raw["state"], questions={"decision": raw["question"]})
                    if "question" in raw
                    else raw
                )
                result = dict(id=row["id"], source_line=number + 1)
                tasks = {}
                for field, question in row["questions"].items():
                    tasks[field] = (
                        Task.from_dict(raw)
                        if "question" in raw
                        else SimpleNamespace(
                            question=question,
                            labels=[k for k, _ in options(question)],
                            expected=target(question, raw.get("targets", {}).get(field, {})),
                            family=raw.get("category", question["type"]),
                        )
                    )
                try:
                    prediction = policy.predict(row)
                    scores = {
                        field: score_task(prediction["probabilities"][field], task)
                        for field, task in tasks.items()
                    }
                    if any(not score["valid"] for score in scores.values()):
                        raise ValueError("Invalid benchmark probability distribution")
                    result.update(prediction=prediction, scores=scores)
                    correct += sum(
                        int(score["correct"])
                        for score in scores.values()
                        if score["correct"] is not None
                    )
                    total += sum(score["correct"] is not None for score in scores.values())
                except Exception as error:
                    failures += 1
                    total += sum(task.expected is not None for task in tasks.values())
                    result["error"] = type(error).__name__ + ": " + str(error)[:500]
                stream.write(json.dumps(result) + "\n")
                if (number + 1) % 50 == 0:
                    stream.flush()
                    put(
                        args.output / "status.json",
                        dict(
                            stage="running",
                            dataset=name,
                            completed=number + 1,
                            total_rows=len(rows),
                            failures=failures,
                            updated_at=time.time(),
                        ),
                    )
            results[name] = dict(
                rows=len(rows),
                correct=correct,
                total=total,
                failures=failures,
                accuracy=correct / total if total else None,
                data_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            put(args.output / "metrics.json", results)
            print(json.dumps({name: results[name]}), flush=True)
    put(
        args.output / "status.json",
        dict(
            stage="completed",
            started_at=started,
            ended_at=time.time(),
            model_identity=policy.identity,
            temperature=policy.temperature,
            macro_accuracy=sum(v["accuracy"] for v in results.values()) / len(results),
            failures=sum(v["failures"] for v in results.values()),
        ),
    )


if __name__ == "__main__":
    main()
