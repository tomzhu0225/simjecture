#!/usr/bin/env python3
"""Execute and postprocess one immutable restricted WarpX matched pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from conjecture_solver.adapters.base import RunPackage
from conjecture_solver.adapters.warpx import (
    WarpXCaseSummary,
    WarpXCompiledCase,
    WarpXPairSummary,
)


def _canonical_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _versions_equivalent(left: str, right: str) -> bool:
    try:
        return tuple(int(part) for part in left.split(".")) == tuple(
            int(part) for part in right.split(".")
        )
    except ValueError:
        return left == right


def _run_logged(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout: float,
    log_prefix: Path,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    log_prefix.with_suffix(".stdout.log").write_text(completed.stdout)
    log_prefix.with_suffix(".stderr.log").write_text(completed.stderr)
    return completed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warpx-python", type=Path, required=True)
    parser.add_argument("--case-timeout-seconds", type=float, default=600.0)
    parser.add_argument("--omp-threads", type=int, default=1)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--work-directory", type=Path, required=True)
    args = parser.parse_args()
    if args.omp_threads < 1:
        raise ValueError("omp-threads must be positive")
    warpx_python = args.warpx_python.resolve()
    if not warpx_python.is_file():
        raise ValueError("WarpX Python executable does not exist")
    run = RunPackage.model_validate_json(args.package.read_text())
    if run.adapter_name != "warpx_picmi":
        raise ValueError("runner received a package for a different adapter")
    if _canonical_hash(run.payload) != run.package_hash:
        raise ValueError("run-package hash does not match its payload")
    if run.payload.get("compiler") != "restricted_picmi_template_v2":
        raise ValueError("real execution requires restricted PICMI compiler v2")
    cases = tuple(WarpXCompiledCase.model_validate(item) for item in run.payload["cases"])
    if tuple(case.case_name for case in cases) != (
        "unit_maxwellian_reference",
        "symmetric_mixture_candidate",
    ):
        raise ValueError("run package does not contain the required ordered matched pair")

    version_call = subprocess.run(
        [
            str(warpx_python),
            "-c",
            "import importlib.metadata; print(importlib.metadata.version('pywarpx'))",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    runtime_version = version_call.stdout.strip()
    expected_version = str(run.payload["expected_warpx_version"])
    if version_call.returncode != 0 or not _versions_equivalent(runtime_version, expected_version):
        raise RuntimeError("WarpX runtime import or release check failed")

    project_root = Path(__file__).resolve().parents[1]
    postprocessor = project_root / "scripts" / "postprocess_warpx_case.py"
    environment = os.environ.copy()
    environment["OMP_NUM_THREADS"] = str(args.omp_threads)
    environment["OPENBLAS_NUM_THREADS"] = "1"
    source_path = str(project_root / "src")
    environment["PYTHONPATH"] = (
        source_path
        if not environment.get("PYTHONPATH")
        else f"{source_path}{os.pathsep}{environment['PYTHONPATH']}"
    )
    execution_root = args.work_directory.resolve() / "execution"
    execution_root.mkdir(parents=True, exist_ok=False)
    summaries: dict[str, WarpXCaseSummary] = {}
    for case in cases:
        case_directory = execution_root / case.case_name
        case_directory.mkdir()
        script_path = case_directory / "run_picmi.py"
        script_path.write_text(case.script + "\n")
        metadata_path = case_directory / "case_metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "case_name": case.case_name,
                    "package_hash": run.package_hash,
                    "physical": run.payload["physical"],
                    "numerical": run.payload["numerical"],
                    "runtime_warpx_version": runtime_version,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        try:
            simulation = _run_logged(
                [str(warpx_python), str(script_path)],
                cwd=case_directory,
                environment=environment,
                timeout=args.case_timeout_seconds,
                log_prefix=case_directory / "simulation",
            )
        except subprocess.TimeoutExpired as error:
            print(f"{case.case_name} timed out: {error}", file=sys.stderr)
            return 2
        if simulation.returncode != 0:
            print(
                f"{case.case_name} WarpX exit={simulation.returncode}: {simulation.stderr[-4000:]}",
                file=sys.stderr,
            )
            return 2
        summary_path = case_directory / "case_summary.json"
        try:
            postprocess = _run_logged(
                [
                    str(warpx_python),
                    str(postprocessor),
                    "--case-directory",
                    str(case_directory),
                    "--metadata",
                    str(metadata_path),
                    "--output",
                    str(summary_path),
                ],
                cwd=case_directory,
                environment=environment,
                timeout=180,
                log_prefix=case_directory / "postprocess",
            )
        except subprocess.TimeoutExpired as error:
            print(f"{case.case_name} postprocessor timed out: {error}", file=sys.stderr)
            return 3
        if postprocess.returncode != 0 or not summary_path.exists():
            print(
                f"{case.case_name} postprocess exit={postprocess.returncode}: "
                f"{postprocess.stderr[-4000:]}",
                file=sys.stderr,
            )
            return 3
        summaries[case.case_name] = WarpXCaseSummary.model_validate_json(summary_path.read_text())

    pair = WarpXPairSummary(
        runtime_warpx_version=runtime_version,
        reference=summaries["unit_maxwellian_reference"],
        candidate=summaries["symmetric_mixture_candidate"],
    )
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_suffix(args.result.suffix + ".tmp")
    temporary.write_text(pair.model_dump_json(indent=2) + "\n")
    temporary.replace(args.result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
