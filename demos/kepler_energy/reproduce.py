"""Rerun one retained numerical experiment into a new directory; no model calls."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from verify_record import HERE, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Recorded exp_... identifier")
    parser.add_argument("--output", required=True, type=Path, help="New, empty output directory")
    args = parser.parse_args()
    verify()
    root = HERE / "record"
    available = {p.stem for p in (root / "experiments").glob("*.json")}
    if args.experiment not in available:
        parser.error("Choose a recorded experiment: " + ", ".join(sorted(available)))
    record = json.loads((root / "experiments" / (args.experiment + ".json")).read_text())
    workspace = root / "experiments" / args.experiment / "workspace"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for relative in record["binding"]["inputs"]:
        destination = output / relative
        if not destination.resolve().is_relative_to(output):
            raise ValueError("Recorded input escapes output directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(workspace / relative, destination)
    command = [sys.executable, record["binding"]["source"], *record["binding"]["args"]]
    subprocess.run(command, cwd=output, check=True, timeout=300)
    print(f"Fresh numerical outputs: {output}")


if __name__ == "__main__":
    main()
