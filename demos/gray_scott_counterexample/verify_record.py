#!/usr/bin/env python3
"""Verify every archived workspace artifact against the terminal report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEMO_DIRECTORY = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record",
        type=Path,
        default=DEMO_DIRECTORY / "record",
    )
    args = parser.parse_args()
    record = args.record.resolve()
    report = json.loads((record / "mvp_report.json").read_text())
    expected = report["workspace_artifacts"]
    workspace = record / "workspace"
    actual_names = {path.name for path in workspace.iterdir() if path.is_file()}
    if actual_names != set(expected):
        missing = sorted(set(expected) - actual_names)
        extra = sorted(actual_names - set(expected))
        raise SystemExit(f"workspace file set differs: missing={missing}, extra={extra}")

    failures = []
    for name, expected_digest in sorted(expected.items()):
        actual_digest = sha256(workspace / name)
        if actual_digest != expected_digest:
            failures.append((name, expected_digest, actual_digest))
    if failures:
        for name, expected_digest, actual_digest in failures:
            print(f"FAIL {name}: expected {expected_digest}, found {actual_digest}")
        return 1
    print(f"verified {len(expected)} immutable workspace artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
