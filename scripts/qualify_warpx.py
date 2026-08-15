#!/usr/bin/env python3
"""Compile the restricted matched-pair package in a candidate WarpX runtime."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from conjecture_solver.adapters.warpx import (
    SubprocessWarpXScheduler,
    WarpXAdapter,
    WarpXExecutionProfile,
    WarpXRunnerKind,
    build_warpx_experiment,
    qualify_warpx_picmi_compiler,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(".runtime/warpx-cpu/bin/python"),
        help="Python executable in the WarpX runtime",
    )
    parser.add_argument(
        "--work-directory",
        type=Path,
        default=Path(".runtime/warpx-qualification"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/warpx_compile_qualification.json"),
    )
    parser.add_argument("--expected-version", default="26.07")
    args = parser.parse_args()

    profile = WarpXExecutionProfile(
        profile_id="warpx_cpu_26_07_compile",
        runner_kind=WarpXRunnerKind.LOCAL_CPU,
        warpx_version=args.expected_version,
    )
    scheduler = SubprocessWarpXScheduler(
        work_root=args.work_directory / "unused-jobs",
        command=(str(args.python),),
        profile=profile,
    )
    run = WarpXAdapter(scheduler).compile_input(build_warpx_experiment())
    record = qualify_warpx_picmi_compiler(
        run,
        python_executable=args.python,
        work_directory=args.work_directory,
        profile_id=profile.profile_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(record.model_dump_json(indent=2) + "\n")
    record_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"passed={record.passed}")
    print(f"scientific_evidence_eligible={record.scientific_evidence_eligible}")
    print(f"observed_warpx_version={record.observed_warpx_version}")
    print(f"record_hash={record_hash}")
    print(f"record={args.output}")
    return 0 if record.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
