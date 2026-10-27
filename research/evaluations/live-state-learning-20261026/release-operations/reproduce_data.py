"""Reproduce the frozen SFT data without training or loading model weights.

Use the source checkout at 37f4773bee1af218c3687b2bdce5d9b2120ad875.
Every scientific split and the final mixture must match its recorded byte hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = args.source.resolve() / "packages/simjecture-monitor"
    sys.path.insert(0, str(package / "src"))
    from simjecture_monitor import attention_support as protocol
    from simjecture_monitor.decision_interface import scientific_request
    from simjecture_monitor.scientific_curriculum import generate
    from simjecture_monitor.synthetic_attention import generate as procedural

    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    data = root / "data"
    data.mkdir()
    splits = [
        (
            "train",
            256,
            202610250000,
            0,
            "ac1074af55dcfe47dc5b2d9210e7e13961f93dfebc8e59987c1c7cfa95be153f",
        ),
        (
            "development",
            32,
            202610260000,
            1,
            "9feca2b1f24b3714e80949211759968ed118854ab9ffd573a617de56a400d9b4",
        ),
        (
            "test",
            64,
            202610270000,
            2,
            "006dc11cafed9b33122a6f477ac2adc4aeea1fccb252b6a28ebdcc6feb9e7a4e",
        ),
    ]
    for split, groups, seed, wording, expected in splits:
        path = data / ("scientific-" + split + ".jsonl")
        with path.open("x") as stream:
            for row in generate(groups, split=split, seed=seed, wording=wording):
                gold = row["targets"]["route"]["label"]
                family = row["provenance"]["mechanism"]
                row["acceptable_routes"] = (
                    ["director", "worker_help"]
                    if family == "dimensional_reporting" and gold == "director"
                    else ["lookup_helper", "lookup_director"]
                    if family == "retrieval_applicability" and gold == "lookup_helper"
                    else [gold]
                )
                stream.write(json.dumps(row) + "\n")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen {split} data mismatch: {actual}")
    with (data / "procedural-train.jsonl").open("x") as stream:
        count = 0
        for row in procedural(1000, seed=20261025):
            if row["split"] != "train":
                continue
            packet = protocol.Observation.model_validate(row["observation"])
            view = protocol.pack(
                packet, len, token_counter_id="assembly:characters", budget_tokens=100000
            )
            request = scientific_request(
                packet, view, target=protocol.Choice.model_validate(row["target"])
            )
            request.update(
                split="train", provenance=row["provenance"], supervision=row["supervision"]
            )
            stream.write(json.dumps(request) + "\n")
            count += 1
            if count == 400:
                break
    if count != 400:
        raise ValueError("Procedural training selection is incomplete")
    subprocess.run(
        [
            sys.executable,
            str(package / "scripts/build_scientific_training.py"),
            "--science",
            str(data / "scientific-train.jsonl"),
            "--procedural",
            str(data / "procedural-train.jsonl"),
            "--output",
            str(root / "mixture"),
            "--rehearsal",
            "1024",
            "--seed",
            "20261025",
        ],
        env=dict(os.environ, PYTHONPATH=str(package / "src")),
        check=True,
    )
    mixture = json.loads((root / "mixture/manifest.json").read_text())
    expected = "af040302d72ec38c1ce29e73b0cf0bf1809bec072baff5d8db5cb3f8ee160756"
    if mixture["sha256"] != expected:
        raise ValueError("Mixture differs from the recorded training input")
    result = dict(
        recipe_source_revision="37f4773bee1af218c3687b2bdce5d9b2120ad875",
        source_package_files={
            str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((package / "src").rglob("*.py"))
        },
        scientific_splits={
            s: dict(groups=g, seed=n, wording=w, sha256=h) for s, g, n, w, h in splits
        },
        training_mixture=mixture,
        scope="Byte-identical constructed data; development/test splits remain optimizer-excluded",
    )
    (root / "REPRODUCED.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(dict(reproduced=True, training_rows=mixture["rows"], training_sha256=expected))
    )


if __name__ == "__main__":
    main()
