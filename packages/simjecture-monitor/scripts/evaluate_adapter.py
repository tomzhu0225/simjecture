"""Fresh base/adapter worker continuations on tasks excluded from optimization."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from simjecture_monitor.events import put
from simjecture_monitor.server import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--base-socket", type=Path, required=True)
    parser.add_argument("--adapter-socket", type=Path, required=True)
    parser.add_argument("--probe-data", type=Path, required=True)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=False)
    packet = json.loads(args.probe_data.read_text())["episodes"][0]["decisions"][0]["packet"]
    sockets = {"base": args.base_socket, "adapter": args.adapter_socket}
    probes = {key: request(value, packet, timeout=90) for key, value in sockets.items()}
    put(args.root / "identity-probes.json", probes)
    identity = {key: value["model_identity"] for key, value in probes.items()}
    if identity["base"]["adapter_files_sha256"]:
        raise ValueError("Base server unexpectedly contains an adapter")
    if not identity["adapter"]["adapter_files_sha256"]:
        raise ValueError("Adapted server has no adapter identity")
    if (
        identity["base"]["checkpoint_config_sha256"]
        != identity["adapter"]["checkpoint_config_sha256"]
    ):
        raise ValueError("Base and adapted checkpoint configurations differ")
    manifest = dict(
        started_at=time.time(),
        revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        model_identity=identity,
        cases=["healthy", "discrepancy"],
        jobs=[
            dict(case=case, policy=policy, trial_id="trial-" + uuid.uuid4().hex)
            for case in ["healthy", "discrepancy"]
            for policy in sockets
        ],
        directory_layout="Opaque trial identifiers; policy/case mapping stays in host metadata",
        results=[],
        note=(
            "Exploratory fresh continuations; task families seen in earlier design, "
            "excluded from optimizer input."
        ),
    )
    put(args.root / "EVALUATION.json", manifest)

    def run(case, policy):
        name = f"{policy}-{case}"
        job = next(
            job for job in manifest["jobs"] if job["case"] == case and job["policy"] == policy
        )
        root = args.root / job["trial_id"]
        if (args.root / "STOP").exists():
            return dict(name=name, trial_id=job["trial_id"], status="not_started")
        with (args.root / (name + ".log")).open("w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).with_name("live_trials.py")),
                    "--root",
                    str(root),
                    "--case",
                    case,
                    "--policy",
                    "model",
                    "--socket",
                    str(sockets[policy]),
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
                        dict(command="cancel", reason="Evaluation bound"),
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

    # Pair contemporaneous arms; retain all results, including transport or worker failures.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for case in manifest["cases"]:
            futures = [pool.submit(run, case, policy) for policy in sockets]
            for future in futures:
                manifest["results"].append(future.result())
                put(args.root / "EVALUATION.json", manifest)
    manifest["ended_at"] = time.time()
    put(args.root / "EVALUATION.json", manifest)
    print(json.dumps(manifest["results"]))


if __name__ == "__main__":
    main()
