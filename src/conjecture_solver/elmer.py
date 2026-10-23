"""Run user-authored Elmer models and ElmerGrid commands with recorded process logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import resource
import signal
import subprocess
import sys
import time
from pathlib import Path

FAILURES = (
    "iteration halted due to problem in algorithm",
    "rnrm^2 is negative",
    "kappal^2 is non-positive",
    "kappa0^2 is non-positive",
    "error::",
    "fatal",
    "not converged",
    "failed to converge",
)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read(path):
    return json.loads(Path(path).read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive(value, name, *, zero=False):
    require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and (value >= 0 if zero else value > 0),
        f"{name} must be finite and {'nonnegative' if zero else 'positive'}",
    )


def runtime():
    home = Path(os.environ["SIMJECTURE_ELMER_HOME"]).resolve()
    solver = home / "bin/ElmerSolver"
    if not solver.is_file():
        solver = home / "bin/ElmerSolver_mpi"
    grid = home / "bin/ElmerGrid"
    require(solver.is_file() and grid.is_file(), "ElmerSolver and ElmerGrid are required")
    env = os.environ | {
        "ELMER_HOME": str(home),
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", "1"),
        "OPENBLAS_NUM_THREADS": "1",
    }
    library_dirs = [home / "lib/elmersolver", home / "lib", home / "deps"]
    env["LD_LIBRARY_PATH"] = ":".join(map(str, library_dirs))
    # Every run binds the actual installed core, modules and dependency bundle.
    identity = {
        str(p.relative_to(home)): digest(p)
        for p in sorted(home.rglob("*"))
        if p.is_file() and (".so" in p.name or p in (solver, grid) or p.name == "elements.def")
    }
    record = home.parent / "share/build-record.json"
    if record.is_file():
        require(identity == read(record)["elmer_identity"], "Installed Elmer files changed")
    return solver, grid, env, identity


def run_process(command, directory, stem, *, timeout, memory_gib, env, solver=False):
    positive(timeout, "timeout")
    positive(memory_gib, "memory_gib")
    directory = Path(directory)
    require(not (directory / f"{stem}.json").exists(), "Preserve previous trials; use a fresh case")

    def limits():
        size = int(memory_gib * 1024**3)
        resource.setrlimit(resource.RLIMIT_AS, (size, size))

    start = time.monotonic()
    peak_rss = 0
    timed_out = False
    logpath = directory / f"{stem}.log"
    with logpath.open("x") as log:
        child = subprocess.Popen(
            command,
            cwd=directory,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=limits,
        )
        try:
            while child.poll() is None:
                try:
                    status = Path(f"/proc/{child.pid}/status").read_text()
                    values = re.findall(r"^VmHWM:\s+(\d+)", status, re.M)
                    if values:
                        peak_rss = max(peak_rss, int(values[0]))
                except (FileNotFoundError, ProcessLookupError):
                    pass
                if time.monotonic() - start >= timeout:
                    timed_out = True
                    break
                time.sleep(0.2)
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
        code = child.wait()
    logtext = logpath.read_text(errors="replace")
    # Elmer may echo an unused option named "Linear System Abort Not Converged".
    # That option's name is not a report of nonconvergence.
    diagnostics = "\n".join(
        line
        for line in logtext.lower().splitlines()
        if "linear system abort not converged" not in line
    )
    failures = [marker for marker in FAILURES if marker in diagnostics]
    accepted = code == 0 and not timed_out and not failures
    if solver or stem == "run":
        accepted = accepted and "ELMER SOLVER FINISHED" in logtext
    record = {
        "command": list(map(str, command)),
        "returncode": code,
        "timed_out": timed_out,
        "execution_pass": accepted,
        "failure_markers": failures,
        "elapsed_s": time.monotonic() - start,
        "peak_process_RSS_KiB": peak_rss,
        "address_space_limit_GiB": memory_gib,
        "timeout_s": timeout,
        "log_sha256": digest(logpath),
    }
    save(directory / f"{stem}.json", record)
    return record


def run_native(kind, case, arguments, *, timeout=900, memory_gib=8, threads=1, record=None):
    """Forward native arguments unchanged. Physics and mesh choices belong to the SIF."""
    case = Path(case).resolve()
    require(case.is_dir(), "Case directory does not exist")
    require(kind in ("solver", "grid"), "Choose solver or grid")
    require(type(threads) is int and threads > 0, "threads must be a positive integer")
    solver, grid, env, identity = runtime()
    env["OMP_NUM_THREADS"] = str(threads)
    stem = record or f".simjecture/{kind}-{time.time_ns()}"
    (case / stem).parent.mkdir(parents=True, exist_ok=True)
    suffixes = {".sif", ".definitions", ".grd", ".msh"}
    inputs = {
        str(p.relative_to(case)): digest(p)
        for p in case.rglob("*")
        if p.is_file()
        and (
            p.suffix in suffixes
            or p.name in ("mesh.nodes", "mesh.elements", "mesh.boundary", "mesh.header")
        )
    }
    result = run_process(
        [str(solver if kind == "solver" else grid), *arguments],
        case,
        stem,
        timeout=timeout,
        memory_gib=memory_gib,
        env=env,
        solver=kind == "solver",
    )
    result.update(
        runtime_identity=identity,
        input_hashes=inputs,
        driver_sha256=digest(__file__),
        scope="Process execution only; model validation is chosen for the problem.",
    )
    save(case / f"{stem}.json", result)
    return result


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    split = arguments.index("--") if "--" in arguments else len(arguments)
    native = arguments[split + 1 :] if split < len(arguments) else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("solver", "grid"))
    parser.add_argument("case", type=Path)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--memory-gib", type=float, default=8)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--record", help="Log basename relative to case, without extension")
    args = parser.parse_args(arguments[:split])
    try:
        result = run_native(
            args.kind,
            args.case,
            native,
            timeout=args.timeout,
            memory_gib=args.memory_gib,
            threads=args.threads,
            record=args.record,
        )
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("runtime_identity", "input_hashes")}
        )
    )
    return 0 if result["execution_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
