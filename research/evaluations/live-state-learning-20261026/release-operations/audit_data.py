"""Audit provenance and exact visible-input overlap in the reproduced data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source.resolve() / "packages/simjecture-monitor/src"))
    from simjecture_monitor.decision_interface import compile_messages

    records, splits, inputs = {}, {}, {}
    for split, relative in [
        ("train", "mixture/train.jsonl"),
        ("development", "data/scientific-development.jsonl"),
        ("test", "data/scientific-test.jsonl"),
    ]:
        path = args.data / relative
        with path.open("rb") as stream:
            inputs[relative] = hashlib.file_digest(stream, "sha256").hexdigest()
        rows, origins, generators, labels, families = [], Counter(), Counter(), Counter(), Counter()
        with path.open() as stream:
            for line in stream:
                row = json.loads(line)
                if row["split"] != split:
                    raise ValueError(f"Unexpected split in {relative}")
                messages, _ = compile_messages(row)
                identity = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
                provenance = row.get("provenance", {})
                rows.append(
                    dict(id=row["id"], prompt_sha256=identity, family=provenance.get("mechanism"))
                )
                origins[provenance.get("origin")] += 1
                generators[provenance.get("generator")] += 1
                labels[row.get("supervision", {}).get("label_source")] += 1
                families[provenance.get("mechanism")] += 1
        records[split] = rows
        splits[split] = dict(
            rows=len(rows),
            unique_prompts=len({v["prompt_sha256"] for v in rows}),
            origins=dict(origins),
            generators=dict(generators),
            label_sources=dict(labels),
            families=dict(families),
        )
    overlaps = {}
    for first, second in [("train", "development"), ("train", "test"), ("development", "test")]:
        prompts = {v["prompt_sha256"] for v in records[first]}
        ids = {v["id"] for v in records[first]}
        hits = [v for v in records[second] if v["prompt_sha256"] in prompts]
        overlaps[first + "_" + second] = dict(
            id_overlap=sum(v["id"] in ids for v in records[second]),
            visible_input_overlap_rows=len(hits),
            overlap_families=dict(Counter(v["family"] for v in hits)),
            overlap_rows=hits,
        )
    report = dict(
        inputs_sha256=inputs,
        splits=splits,
        overlaps=overlaps,
        scope=(
            "Exact compiled visible-message identity only; shared templates and mechanisms "
            "remain, so this does not establish semantic or task-disjoint generalization"
        ),
    )
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(rows={k: v["rows"] for k, v in splits.items()}, overlaps=overlaps)))


if __name__ == "__main__":
    main()
