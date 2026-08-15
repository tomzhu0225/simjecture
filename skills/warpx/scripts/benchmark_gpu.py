#!/usr/bin/env python3
"""Benchmark exact operator-supplied program argv cases on the CUDA runtime."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

EVOLVE_RE = re.compile(
    r"Evolve time = ([0-9.eE+-]+) s;.*Avg\. per step = ([0-9.eE+-]+) s"
)
PROFILE_EVOLVE_RE = re.compile(
    r"^WarpX::Evolve\(\)\s+1\s+([0-9.eE+-]+)", re.MULTILINE
)
LABEL_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--required-path", action="append", required=True)
    return parser.parse_args()


def contained_paths(values: list[str]) -> tuple[Path, ...]:
    paths = tuple(Path(value) for value in values)
    for path in paths:
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("--required-path must be a contained relative path")
    return paths


def read_cases(path: Path) -> tuple[dict[str, Any], ...]:
    payload = json.loads(path.read_text())
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases file must contain a nonempty 'cases' list")
    result = []
    labels = set()
    for item in cases:
        if not isinstance(item, dict) or set(item) != {"label", "argv"}:
            raise ValueError("each case must contain exactly 'label' and 'argv'")
        label = item["label"]
        argv = item["argv"]
        if not isinstance(label, str) or not LABEL_RE.fullmatch(label):
            raise ValueError("case labels may contain only letters, digits, ._- ")
        if label in labels:
            raise ValueError(f"duplicate case label: {label}")
        if not isinstance(argv, list) or not all(isinstance(v, str) for v in argv):
            raise ValueError(f"case {label!r} argv must be a list of strings")
        labels.add(label)
        result.append({"label": label, "argv": argv})
    return tuple(result)


def amrex_capabilities(python: Path) -> dict[str, object]:
    code = (
        "import json, amrex.space2d as a; "
        "print(json.dumps({'have_mpi': bool(a.Config.have_mpi), "
        "'have_omp': bool(a.Config.have_omp), "
        "'have_gpu': bool(a.Config.have_gpu), "
        "'gpu_backend': str(a.Config.gpu_backend)}))"
    )
    probe = subprocess.run(
        [str(python), "-c", code], check=True, text=True, capture_output=True
    )
    return json.loads(probe.stdout)


def gpu_identity() -> dict[str, str]:
    query = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,compute_cap,driver_version",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    name, memory_mib, compute_cap, driver = (
        value.strip() for value in query.stdout.splitlines()[0].split(",")
    )
    return {
        "name": name,
        "memory_mib": memory_mib,
        "compute_capability": compute_cap,
        "driver_version": driver,
    }


def capability_environment(python: Path) -> dict[str, str]:
    env = os.environ.copy()
    python_site = subprocess.run(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    bundled_site = str(Path(python_site) / "pywarpx" / "site-packages")
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (bundled_site, python_site, env.get("PYTHONPATH", "")) if value
    )
    env["WARPX_PYTHON_SITE"] = python_site
    env.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    return env


def require_outputs(run: Path, paths: tuple[Path, ...]) -> dict[str, int]:
    observed: dict[str, int] = {}
    for relative in paths:
        target = run / relative
        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError(f"required nonempty output is absent: {relative}")
        observed[relative.as_posix()] = target.stat().st_size
    return observed


def timing_from_log(output: str) -> tuple[float | None, float | None]:
    timings = EVOLVE_RE.findall(output)
    if timings:
        return tuple(float(value) for value in timings[-1])  # type: ignore[return-value]
    profile = [float(value) for value in PROFILE_EVOLVE_RE.findall(output)]
    return (max(profile), None) if profile else (None, None)


def run_one(
    args: argparse.Namespace,
    case: dict[str, Any],
    required: tuple[Path, ...],
    repeat: int,
    env: dict[str, str],
) -> dict[str, object]:
    run = args.output / f"{case['label']}-r{repeat}"
    run.mkdir(parents=True, exist_ok=False)
    command = [str(args.python), str(args.program), *case["argv"]]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=run,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    wall_s = time.perf_counter() - started
    (run / "benchmark.log").write_text(completed.stdout)
    if completed.returncode:
        raise RuntimeError(
            f"case={case['label']} repeat={repeat} exited {completed.returncode}; "
            f"see {run / 'benchmark.log'}"
        )
    outputs = require_outputs(run, required)
    evolve_s, step_s = timing_from_log(completed.stdout)
    return {
        "label": case["label"],
        "repeat": repeat,
        "wall_s": wall_s,
        "warpx_evolve_s": evolve_s,
        "warpx_step_s": step_s,
        "argv": json.dumps(case["argv"]),
        "required_outputs": json.dumps(outputs, sort_keys=True),
        "run_dir": str(run),
    }


def main() -> int:
    args = parse_args()
    args.python = args.python.resolve()
    args.program = args.program.resolve()
    args.output = args.output.resolve()
    cases = read_cases(args.cases.resolve())
    required = contained_paths(args.required_path)
    if args.repeats <= 0:
        raise ValueError("--repeats must be positive")
    capabilities = amrex_capabilities(args.python)
    if not capabilities["have_gpu"]:
        raise RuntimeError("refusing benchmark: loaded AMReX reports have_gpu=false")
    if str(capabilities["gpu_backend"]).upper() != "CUDA":
        raise RuntimeError(
            f"this harness expects CUDA, got {capabilities['gpu_backend']}"
        )
    args.output.mkdir(parents=True, exist_ok=False)
    env = capability_environment(args.python)
    rows = [
        run_one(args, case, required, repeat, env)
        for case in cases
        for repeat in range(1, args.repeats + 1)
    ]
    with (args.output / "runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summaries = [
        {
            "label": case["label"],
            "argv": case["argv"],
            "median_wall_s": statistics.median(
                float(row["wall_s"])
                for row in rows
                if row["label"] == case["label"]
            ),
        }
        for case in cases
    ]
    result = {
        "capabilities": capabilities,
        "gpu": gpu_identity(),
        "program": str(args.program),
        "required_paths": [path.as_posix() for path in required],
        "repeats": args.repeats,
        "summaries": summaries,
        "best": min(summaries, key=lambda value: value["median_wall_s"]),
    }
    (args.output / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
