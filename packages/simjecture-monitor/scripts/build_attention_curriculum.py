"""Build an auditable scripted SFT curriculum, without training or model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from simjecture_monitor import attention_support, synthetic_attention


def build(output, *, groups, seed):
    if groups < 1:
        raise ValueError("At least one context group is required")
    output.mkdir(parents=True, exist_ok=False)
    counts = {name: Counter() for name in ("split", "target", "mechanism")}
    group_splits, inputs = {}, {}
    files, hashes = {}, {}
    duplicate_inputs = 0
    try:
        for split in ("train", "validation", "synthetic_audit"):
            files[split] = (output / (split + ".jsonl")).open("wb")
            hashes[split] = hashlib.sha256()
        for row in synthetic_attention.generate(groups, seed=seed):
            group, split = row["group_id"], row["split"]
            if group_splits.setdefault(group, split) != split:
                raise ValueError("Context group leaked between splits")
            input_hash = hashlib.sha256(row["input_text"].encode()).hexdigest()
            if input_hash != row["input_sha256"]:
                raise ValueError("Input checksum mismatch")
            target_hash = synthetic_attention.digest(row["target"])
            if input_hash in inputs:
                duplicate_inputs += 1
                if inputs[input_hash] != (target_hash, split):
                    raise ValueError("Conflicting labels or identical inputs across splits")
            inputs[input_hash] = target_hash, split
            counts["split"][split] += 1
            counts["target"][row["target"]["action"] + "." + row["target"]["support_kind"]] += 1
            counts["mechanism"][row["provenance"]["mechanism"]] += 1
            data = (json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode()
            files[split].write(data)
            hashes[split].update(data)
    finally:
        for handle in files.values():
            handle.close()
    sources = [Path(__file__), Path(attention_support.__file__), Path(synthetic_attention.__file__)]
    report = dict(
        schema_version="scientific-attention-curriculum-manifest/0.1-draft",
        seed=seed,
        groups=len(group_splits),
        rows=sum(counts["split"].values()),
        counts={name: dict(value) for name, value in counts.items()},
        group_counts=dict(Counter(group_splits.values())),
        exact_duplicate_inputs=duplicate_inputs,
        conflicting_targets=0,
        cross_split_group_leaks=0,
        files={split + ".jsonl": value.hexdigest() for split, value in hashes.items()},
        source_sha256={
            path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
        },
        scope=(
            "Scripted procedural preferences from synthetic visible states. "
            "No model predictions, actual scientific outcomes, intervention utility labels, "
            "or RL behavior probabilities. Synthetic audit is not a real-task test set. "
            "Context grouping does not hold out mechanisms or vocabulary templates."
        ),
        training_fields=["input_text", "target"],
        tokenization="Full text only; tokenize using the eventual training chat template.",
    )
    (output / "manifest.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--groups", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261025)
    args = parser.parse_args()
    print(json.dumps(build(args.output, groups=args.groups, seed=args.seed), indent=2))


if __name__ == "__main__":
    main()
