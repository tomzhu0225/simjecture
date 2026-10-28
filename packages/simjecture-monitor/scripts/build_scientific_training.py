"""Mix reviewed constructed science preferences with procedural and generic rehearsal data.

Public general benchmark tests are never rehearsal inputs. The generic examples
here are independently constructed routing/priority records with known labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from simjecture_monitor.decision_interface import compile_messages


def rehearsal(count, *, seed):
    rng = random.Random(seed)
    topics = {
        "billing": "An invoice contains a duplicate charge.",
        "delivery": "A parcel has not arrived at the listed address.",
        "account": "The user cannot sign in after changing a password.",
        "catalog": "The product listing has the wrong colour description.",
    }
    for i in range(count):
        topic = rng.choice(list(topics))
        waiting = rng.randint(0, 90)
        urgent = bool(rng.randrange(2))
        wants_reply = bool(rng.randrange(2))
        order = list(topics)
        rng.shuffle(order)
        state = dict(
            message=topics[topic],
            waiting_hours=waiting,
            urgent_flag=urgent,
            requests_reply=wants_reply,
        )
        questions = {
            "team": dict(
                type="choice",
                instructions="Select the team responsible for the message.",
                criteria={key: key.capitalize() + " support" for key in order},
            ),
            "priority": dict(
                type="score",
                instructions=(
                    "Use priority2 if the urgent flag is true or waiting_hours exceeds48; "
                    "otherwise priority1 if waiting_hours exceeds12; otherwise priority0."
                ),
                criteria=["Routine", "Elevated", "High"],
            ),
            "reply": dict(type="noul", instructions="Does this record request a reply?"),
        }
        targets = dict(
            team=topic,
            priority=str(2 if urgent or waiting > 48 else 1 if waiting > 12 else 0),
            reply="yes" if wants_reply else "no",
        )
        yield dict(
            id=hashlib.sha256(f"rehearsal:{seed}:{i}".encode()).hexdigest()[:24],
            state=state,
            questions=questions,
            targets={k: {"label": v} for k, v in targets.items()},
            split="train",
            provenance=dict(origin="constructed", generator="general-rehearsal-v1"),
            supervision=dict(
                label_source="explicit_routing_and_priority_contract",
                utility_label=None,
                rollout_validated=False,
            ),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--science", type=Path, required=True)
    parser.add_argument("--procedural", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rehearsal", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=20261025)
    args = parser.parse_args()
    if args.rehearsal < 0:
        raise ValueError("Rehearsal count cannot be negative")
    args.output.mkdir(parents=True, exist_ok=False)
    counts = Counter()
    seen = set()
    inputs = {}

    def external(path):
        with path.open() as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)

    with (args.output / "train.jsonl").open("w") as stream:
        for source, rows in [
            ("science", external(args.science)),
            ("procedural", external(args.procedural)),
            ("general_rehearsal", rehearsal(args.rehearsal, seed=args.seed)),
        ]:
            for row in rows:
                if row.get("split") != "train" or row["id"] in seen:
                    raise ValueError("Only unique training rows may enter this mixture")
                seen.add(row["id"])
                messages, _ = compile_messages(row)
                identity = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
                target = json.dumps(row["targets"], sort_keys=True)
                if identity in inputs and inputs[identity] != target:
                    raise ValueError("Identical visible input received conflicting targets")
                inputs[identity] = target
                row["training_source"] = source
                stream.write(json.dumps(row, allow_nan=False) + "\n")
                counts[source] += 1
    manifest = dict(
        rows=sum(counts.values()),
        counts=dict(counts),
        unique_inputs=len(inputs),
        seed=args.seed,
        sha256=hashlib.sha256((args.output / "train.jsonl").read_bytes()).hexdigest(),
        sources={
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [args.science, args.procedural]
        },
        scope=(
            "Supervised preferences and independently constructed rehearsal; "
            "no public test data or RL utility labels"
        ),
    )
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
