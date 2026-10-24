"""Compare new-event-only inference with bounded timed observations, after runtime trials."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from run_parked_study import execute
from simjecture_monitor.events import put
from simjecture_monitor.server import request

from conjecture_solver.research_helper_runtime import process_stat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    parser.add_argument("--grace-commissioning", action="store_true")
    parser.add_argument("--triton-cache", type=Path)
    args = parser.parse_args()
    root, pilot, previous, repo = (
        args.root.resolve(),
        args.pilot.resolve(),
        args.previous.resolve(),
        Path.cwd(),
    )
    root.mkdir(parents=True, exist_ok=True)
    if (root / "DESIGN.json").exists():
        raise ValueError("Retain existing trials")
    jobs = [
        dict(
            root="trial-" + uuid.uuid4().hex,
            case=case,
            policy="model",
            profile="fla-prefill",
            timer=timer,
            repeat=repeat,
        )
        for case in ["healthy", "adapter"]
        for timer in [False, True]
        for repeat in range(2)
    ]
    if args.grace_commissioning:
        jobs = [j for j in jobs if j["case"] == "adapter" and j["repeat"] == 0]
    random.Random(2026102408 if args.grace_commissioning else 2026102407).shuffle(jobs)
    put(
        root / "DESIGN.json",
        dict(
            jobs=jobs,
            created_at=time.time(),
            source_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            question="Can bounded elapsed-time observations repair a no-new-event blind spot?",
            kind="mechanism commissioning" if args.grace_commissioning else "live comparison",
            grace_seconds=10 if args.grace_commissioning else 0,
            interval_seconds=15,
            fixed_fallback_seconds=90,
            maximum_parent_controllers=2,
            shared_native_budget=str(pilot / "native-budget.json"),
            limits=(
                "Repeated injected known mechanism; no training; "
                "no deterministic re-poll of identical inputs"
            ),
        ),
    )
    until = time.time() + 3600
    while not (previous / "RESULTS.json").exists():
        if time.time() > until:
            raise TimeoutError("Previous runtime comparison did not finish")
        time.sleep(5)
    releases = (
        [previous / "MODEL_RELEASE.json"]
        if args.grace_commissioning
        else [previous / f"block-{block}/MODEL_RELEASE.json" for block in range(4)]
    )
    for path in releases:
        while not path.exists():
            if time.time() > until:
                raise TimeoutError("Previous server release is missing")
            time.sleep(1)
        release = json.loads(path.read_text())
        if release["socket_present"]:
            raise RuntimeError("Previous server did not release socket")
    budget = json.loads((pilot / "native-budget.json").read_text())
    minimum = len(jobs) * budget["maximum_per_continuation"] if args.grace_commissioning else 40
    put(
        root / "LEASE_PREFLIGHT.json",
        dict(
            measured_at=time.time(),
            minimum_slots=minimum,
            existing_starts=len(budget["starts"]),
            maximum_starts=budget["maximum_starts"],
            maximum_per_continuation=budget["maximum_per_continuation"],
        ),
    )
    if budget["maximum_starts"] - len(budget["starts"]) < minimum:
        raise RuntimeError("Insufficient remaining native start allowance")
    socket = Path("/tmp/simjecture-timer-" + uuid.uuid4().hex + ".sock")
    launcher = root / "serve.py"
    launcher.write_text(
        "import torch\ntorch.set_num_threads(2)\n"
        "free,total=torch.cuda.mem_get_info()\nassert free>11*1024**3\n"
        "torch.cuda.set_per_process_memory_fraction(.6)\n"
        "from simjecture_monitor.server import main\nmain()\n"
    )
    command = [
        str(repo / "artifacts/model-fast-env/bin/python"),
        str(launcher),
        "--checkpoint",
        str(repo / "artifacts/models/Decision-verified"),
        "--socket",
        str(socket),
        "--status",
        str(root / "MODEL_STATUS.json"),
        "--kernel-profile",
        "fla-prefill",
        "--wall-seconds",
        "1800",
        "--idle-seconds",
        "300",
    ]
    env = dict(
        os.environ,
        PYTHONPATH=str(repo / "packages/simjecture-monitor/src"),
        TRITON_CACHE_DIR=str(
            args.triton_cache.resolve() if args.triton_cache else previous / "triton-cache"
        ),
    )
    with (root / "model.log").open("w") as log:
        server = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
    put(root / "MODEL_PROCESS.json", dict(identity=process_stat(server.pid), socket=str(socket)))
    try:
        until = time.time() + 180
        while not socket.exists():
            if server.poll() is not None or time.time() > until:
                raise RuntimeError("Model server did not become ready")
            time.sleep(1)
        packet = json.loads((repo / "artifacts/inference-fast-20261024/packets.json").read_text())[
            0
        ]
        put(root / "WARMUP.json", request(socket, packet, timeout=120))
        results = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    execute,
                    root,
                    job,
                    pilot / "native-budget.json",
                    pilot / "native-codex",
                    socket,
                    driver=(
                        ("grace_timer_trials.py" if job["timer"] else "grace_trials.py")
                        if args.grace_commissioning
                        else ("heartbeat_trials.py" if job["timer"] else "parked_trials.py")
                    ),
                )
                for job in jobs
            ]
            for future in as_completed(futures):
                results.append(future.result())
                put(root / "PROGRESS.json", dict(completed=len(results), results=results))
        put(root / "RESULTS.json", results)
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        put(
            root / "MODEL_RELEASE.json",
            dict(
                ended_at=time.time(), returncode=server.returncode, socket_present=socket.exists()
            ),
        )


if __name__ == "__main__":
    main()
