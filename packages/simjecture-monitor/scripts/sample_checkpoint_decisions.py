"""Log actual categorical proposals from frozen public development checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from simjecture_monitor.attention_server import sampled_answers
from simjecture_monitor.events import put


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temperature", type=float, default=3.0)
    parser.add_argument("--draws", type=int, default=4)
    parser.add_argument("--seed", type=int, default=2026102601)
    args = parser.parse_args()
    if args.temperature <= 0 or args.draws < 2:
        raise ValueError("Require positive temperature and at least two draws per prefix")
    args.output.mkdir(parents=True, exist_ok=False)
    from simjecture_monitor.decision_model import DecisionModel

    model = DecisionModel(
        args.base, adapter=args.adapter, max_tokens=8192, kernel_profile="fla-prefill"
    )
    model.temperature = args.temperature
    rows = [json.loads(line) for line in args.data.read_text().splitlines() if line]
    records = []
    for group, row in enumerate(rows):
        prediction = model.predict(row)
        for draw in range(args.draws):
            seed = args.seed + group * 100 + draw
            answers, logp = sampled_answers(prediction["probabilities"], seed)
            identity = hashlib.sha256(f"{seed}:{row['id']}".encode()).hexdigest()[:16]
            result = dict(
                row,
                id="draw-" + identity,
                split="train",
                targets={key: dict(label=value) for key, value in answers.items()},
                behavior=dict(
                    prompt_sha256=prediction["prompt_sha256"],
                    probabilities=prediction["probabilities"],
                    sampled_answers=answers,
                    sampled_joint_log_probability=logp,
                    seed=seed,
                    temperature=args.temperature,
                    model_identity=model.identity,
                    offline_scoring_seconds=prediction["total_seconds"],
                    input_tokens=prediction["input_tokens"],
                ),
            )
            records.append(result)
            put(args.output / (result["id"] + ".json"), result)
    put(
        args.output / "manifest.json",
        dict(
            data_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
            model_identity=model.identity,
            temperature=args.temperature,
            draws_per_prefix=args.draws,
            records=[r["id"] for r in records],
        ),
    )


if __name__ == "__main__":
    main()
