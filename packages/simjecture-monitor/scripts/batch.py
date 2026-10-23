"""Bounded overnight comparison; preserve completed and failed trials without overwriting."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from simjecture_monitor.events import put


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--socket", type=Path, default=Path("/tmp/simjecture-monitor-20261023.sock")
    )
    parser.add_argument("--wall-seconds", type=int, default=7200)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).resolve().parent
    # Run model arms first so the GPU can be released promptly; no outcome-dependent selection.
    cases = ["harness", "healthy", "discrepancy", "recoverable-analysis"]
    jobs = [
        dict(case=case, policy=policy, root=str(root / f"live-{policy}-{case}"))
        for policy in ["model", "rules", "periodic"]
        for case in cases
    ]
    source = scripts.parent / "src/simjecture_monitor"
    manifest = dict(
        started_at=time.time(),
        stop_by=time.time() + args.wall_seconds,
        revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        source_sha256={
            str(p.relative_to(scripts.parent)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*source.glob("*.py"), scripts / "live_trials.py"]
        },
        jobs=jobs,
        maximum_parent_workers=2,
        notes=(
            "Exploratory unpaired stochastic continuations; same task construction across "
            "policies. Commissioning smoke is separate."
        ),
    )
    put(root / "BATCH.json", manifest)
    active = {}
    handles = {}
    started = set()
    try:
        while time.time() < manifest["stop_by"] and not (root / "STOP").exists():
            running = []
            terminal = []
            for index, job in enumerate(jobs):
                path = Path(job["root"]) / "TRIAL.json"
                record = None
                if path.exists():
                    with contextlib.suppress(ValueError):
                        record = json.loads(path.read_text())
                process = active.get(index)
                if process is not None and process.poll() is not None:
                    handles[index].close()
                    del active[index]
                    if record is None or record["stage"] == "running":
                        put(
                            path,
                            dict(
                                stage="failed",
                                case=job["case"],
                                policy=job["policy"],
                                error="Trial process exited without a completed receipt",
                                returncode=process.returncode,
                                ended_at=time.time(),
                            ),
                        )
                        record = json.loads(path.read_text())
                if record and record["stage"] in ["completed", "failed"]:
                    terminal.append(index)
                elif (record and record["stage"] == "running") or index in active:
                    running.append(index)
            if len(terminal) == len(jobs):
                put(
                    root / "batch-progress.json",
                    dict(
                        updated_at=time.time(), completed=len(terminal), running=[], total=len(jobs)
                    ),
                )
                break
            for index, job in enumerate(jobs):
                if len(running) >= 2:
                    break
                if index in terminal or index in running or index in started:
                    continue
                if Path(job["root"]).exists():
                    raise RuntimeError(
                        "Existing trial has no valid durable receipt: " + job["root"]
                    )
                log = (root / f"batch-{job['policy']}-{job['case']}.log").open("w")
                process = subprocess.Popen(
                    [
                        sys.executable,
                        str(scripts / "live_trials.py"),
                        "--root",
                        job["root"],
                        "--case",
                        job["case"],
                        "--policy",
                        job["policy"],
                        "--socket",
                        str(args.socket),
                    ],
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                handles[index] = log
                active[index] = process
                started.add(index)
                running.append(index)
                job.update(pid=process.pid, launched_at=time.time())
                put(root / "BATCH.json", manifest)
            put(
                root / "batch-progress.json",
                dict(
                    updated_at=time.time(),
                    completed=len(terminal),
                    running=[jobs[i] for i in running],
                    total=len(jobs),
                ),
            )
            # Bound each child via its normal operator-control channel before forced cleanup.
            for index in list(active):
                if time.time() - jobs[index]["launched_at"] > 800:
                    put(
                        Path(jobs[index]["root"]) / "supervisor/control.json",
                        dict(command="cancel", reason="Overnight trial limit"),
                    )
            time.sleep(3)
    finally:
        for index in active:
            put(
                Path(jobs[index]["root"]) / "supervisor/control.json",
                dict(command="cancel", reason="Overnight batch stopping"),
            )
        for index, process in active.items():
            try:
                process.wait(timeout=90)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            handles[index].close()
        manifest["ended_at"] = time.time()
        put(root / "BATCH.json", manifest)


if __name__ == "__main__":
    main()
