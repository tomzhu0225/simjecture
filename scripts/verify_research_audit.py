"""Check a compact research audit's retained bytes and recorded dispositions.

This does not rerun omitted simulations or independently endorse a claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify(root: Path) -> dict:
    root = root.resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    files = manifest["files"]

    def contained(name: str) -> Path:
        path = root / name
        if Path(name).is_absolute() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Audit path escapes its record: {name}")
        return path

    for name, expected in files.items():
        if digest(contained(name)) != expected:
            raise ValueError(f"Retained file hash mismatch: {name}")
    for required in ["research.json", "research_report.json"]:
        if required not in files:
            raise ValueError(f"Missing required audit file: {required}")
    study = json.loads((root / "research.json").read_text())
    report = json.loads((root / "research_report.json").read_text())
    for item in study.get("guided_commissioning", {}).get("files", []):
        name = "guided_commissioning_input/" + item["path"]
        if files.get(name) != item["sha256"]:
            raise ValueError(f"Missing or changed commissioning input: {name}")

    experiments = []
    for path in sorted((root / "experiments").glob("*.json")):
        if str(path.relative_to(root)) not in files:
            raise ValueError(f"Unlisted receipt: {path.name}")
        record = json.loads(path.read_text())
        experiments.append(record)
        prefix = f"experiments/{record['id']}/workspace/"
        for name, artifact in record.get("artifacts", {}).items():
            relative = prefix + name
            present = contained(relative).is_file()
            if present and files.get(relative) != artifact["sha256"]:
                raise ValueError(f"Retained artifact differs from receipt: {relative}")
            omission = manifest.get("omitted_declared_files", {}).get(relative)
            if omission and omission["sha256"] != artifact["sha256"]:
                raise ValueError(f"Omitted artifact identity differs from receipt: {relative}")
        for name, expected in record["binding"]["inputs"].items():
            if (
                name not in record.get("input_mutations", [])
                and prefix + name in files
                and files[prefix + name] != expected
            ):
                raise ValueError(f"Retained input differs from binding: {prefix + name}")

    counts = dict(Counter(row["status"] for row in experiments))
    if counts != manifest["experiments"]:
        raise ValueError("Experiment counts differ from manifest")
    if report["completed"] != manifest["recorded_completed"]:
        raise ValueError("Completion disposition differs from manifest")
    return {
        "verified_files": len(files),
        "experiments": counts,
        "completed": report["completed"],
        "accepted_reviews": [
            {"claim": r["claim"], "disposition": r["verdict"]["disposition"]}
            for r in report.get("reviews", [])
            if r.get("verdict", {}).get("decision") == "approved"
        ],
        "scope": (
            "Retained-file integrity and recorded dispositions; "
            "not numerical replay or scientific endorsement."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    print(json.dumps(verify(parser.parse_args().record), indent=2))
