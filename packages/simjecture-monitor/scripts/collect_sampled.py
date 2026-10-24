"""Collect the four prespecified real-worker policy episodes with bounded concurrency."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from simjecture_monitor.events import put


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--socket", type=Path, default=Path("/tmp/simjecture-monitor-20261023.sock")
    )
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).with_name("live_trials.py")
    jobs = [
        dict(case=case, seed=seed, trial_id="trial-" + uuid.uuid4().hex)
        for seed in [71, 97]
        for case in ["harness", "recoverable-analysis"]
    ]
    manifest = dict(
        started_at=time.time(),
        revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        jobs=jobs,
        directory_layout="Opaque trial identifiers; case/seed mapping stays in host metadata",
        results=[],
    )
    put(args.root / "COLLECTION.json", manifest)

    def run(job):
        name = f"{job['case']}-{job['seed']}"
        root = args.root / job["trial_id"]
        if (args.root / "STOP").exists():
            return dict(name=name, trial_id=job["trial_id"], status="not_started")
        with (args.root / (name + ".log")).open("w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(script),
                    "--root",
                    str(root),
                    "--case",
                    job["case"],
                    "--policy",
                    "sampled",
                    "--seed",
                    str(job["seed"]),
                    "--socket",
                    str(args.socket),
                ],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            started = time.time()
            while process.poll() is None:
                if time.time() - started > 800 or (args.root / "STOP").exists():
                    put(
                        root / "supervisor/control.json",
                        dict(command="cancel", reason="Collection bound"),
                    )
                if time.time() - started > 900:
                    process.terminate()
                    break
                time.sleep(1)
            try:
                rc = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                rc = process.wait()
        return dict(
            name=name,
            trial_id=job["trial_id"],
            returncode=rc,
            started_at=started,
            ended_at=time.time(),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(run, job) for job in jobs]):
            manifest["results"].append(future.result())
            put(args.root / "COLLECTION.json", manifest)
    manifest["ended_at"] = time.time()
    put(args.root / "COLLECTION.json", manifest)
    print(json.dumps(manifest["results"]))


if __name__ == "__main__":
    main()
