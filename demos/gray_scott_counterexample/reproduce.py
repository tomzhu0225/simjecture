#!/usr/bin/env python3
"""Run the exact agent-authored decisive program in a clean output directory."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEMO_DIRECTORY = Path(__file__).resolve().parent
RECORDED_WORKSPACE = DEMO_DIRECTORY / "record" / "workspace"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/gray-scott-reproduction"),
    )
    args = parser.parse_args()
    output = args.output.resolve()
    record = (DEMO_DIRECTORY / "record").resolve()
    if output == record or output.is_relative_to(record):
        parser.error("refusing to overwrite the immutable recorded run")
    if output.exists() and any(output.iterdir()):
        parser.error(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    program = (RECORDED_WORKSPACE / "simulate_gs_root.py").resolve()
    completed = subprocess.run(
        [sys.executable, str(program)],
        cwd=output,
        check=False,
    )
    if completed.returncode:
        return completed.returncode
    print(f"Reproduction written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
