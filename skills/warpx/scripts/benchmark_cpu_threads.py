#!/usr/bin/env python3
"""Benchmark one exact operator-supplied program argv across OpenMP settings."""

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

EVOLVE_RE = re.compile(
    r"Evolve time = ([0-9.eE+-]+) s;.*Avg\. per step = ([0-9.eE+-]+) s"
)
PROFILE_EVOLVE_RE = re.compile(
    r"^WarpX::Evolve\(\)\s+1\s+([0-9.eE+-]+)", re.MULTILINE
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--program", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument(
        "--affinity", choices=("none", "close", "spread"), default="close"
    )
    parser.add_argument("--places", choices=("cores", "threads"), default="cores")
    parser.add_argument("--required-path", action="append", required=True)
    parser.add_argument("program_argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.program_argv[:1] == ["--"]:
        args.program_argv = args.program_argv[1:]
    return args


def contained_paths(values: list[str]) -> tuple[Path, ...]:
    paths = tuple(Path(value) for value in values)
    for path in paths:
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("--required-path must be a contained relative path")
    return paths


def amrex_capabilities(python: Path) -> dict[str, object]:
    probe = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import json, amrex.space2d as a; "
                "print(json.dumps({'have_mpi': bool(a.Config.have_mpi), "
                "'have_omp': bool(a.Config.have_omp)}))"
            ),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(probe.stdout)


def launch_environment(threads: int, affinity: str, places: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "OMP_NUM_THREADS": str(threads),
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    if affinity == "none":
        env.pop("OMP_PROC_BIND", None)
        env.pop("OMP_PLACES", None)
    else:
        env["OMP_PROC_BIND"] = affinity
        env["OMP_PLACES"] = places
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
    required: tuple[Path, ...],
    threads: int,
    repeat: int,
) -> dict[str, object]:
    run = args.output / f"omp-{threads:03d}-{args.affinity}-{args.places}-r{repeat}"
    run.mkdir(parents=True, exist_ok=False)
    command = [str(args.python), str(args.program), *args.program_argv]
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=run,
        env=launch_environment(threads, args.affinity, args.places),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    wall_s = time.perf_counter() - started
    (run / "benchmark.log").write_text(completed.stdout)
    if completed.returncode:
        raise RuntimeError(
            f"threads={threads} repeat={repeat} exited {completed.returncode}; "
            f"see {run / 'benchmark.log'}"
        )
    outputs = require_outputs(run, required)
    evolve_s, step_s = timing_from_log(completed.stdout)
    return {
        "threads": threads,
        "affinity": args.affinity,
        "places": args.places,
        "repeat": repeat,
        "wall_s": wall_s,
        "warpx_evolve_s": evolve_s,
        "warpx_step_s": step_s,
        "required_outputs": json.dumps(outputs, sort_keys=True),
        "run_dir": str(run),
    }


def main() -> int:
    args = parse_args()
    args.python = args.python.resolve()
    args.program = args.program.resolve()
    args.output = args.output.resolve()
    required = contained_paths(args.required_path)
    threads = [int(value) for value in args.threads.split(",")]
    if not threads or any(value <= 0 for value in threads):
        raise ValueError("--threads must contain positive integers")
    if args.repeats <= 0:
        raise ValueError("--repeats must be positive")
    capabilities = amrex_capabilities(args.python)
    mpi_world_size = int(
        os.environ.get("OMPI_COMM_WORLD_SIZE")
        or os.environ.get("PMI_SIZE")
        or os.environ.get("MPI_LOCALNRANKS")
        or "1"
    )
    if mpi_world_size > 1 and not capabilities["have_mpi"]:
        raise RuntimeError(
            "refusing MPI launch: loaded AMReX reports have_mpi=false"
        )
    args.output.mkdir(parents=True, exist_ok=False)
    rows = [
        run_one(args, required, count, repeat)
        for count in threads
        for repeat in range(1, args.repeats + 1)
    ]
    with (args.output / "runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summaries = [
        {
            "threads": count,
            "median_wall_s": statistics.median(
                float(row["wall_s"]) for row in rows if row["threads"] == count
            ),
        }
        for count in threads
    ]
    result = {
        "capabilities": capabilities,
        "observed_mpi_world_size": mpi_world_size,
        "program": str(args.program),
        "program_argv": args.program_argv,
        "required_paths": [path.as_posix() for path in required],
        "repeats": args.repeats,
        "affinity": args.affinity,
        "places": args.places,
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
