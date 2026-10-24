"""Run a separate live parked-worker study after the checkpoint pilot finishes."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from simjecture_monitor.events import put

from conjecture_solver.research_helper_runtime import process_stat


def load(path):
    return json.loads(path.read_text())


def execute(root, job, budget, wrapper, socket, *, driver="parked_trials.py"):
    trial = root / job["root"]
    if trial.exists():
        raise ValueError("Retain prior trials; do not overwrite or silently rerun")
    env = dict(
        os.environ,
        SIMJECTURE_NATIVE_BUDGET=str(budget),
        SIMJECTURE_CONTINUATION=job["root"],
        SIMJECTURE_CONTINUATION_DEADLINE=str(time.time() + 680),
    )
    command = [
        sys.executable,
        "-u",
        str(Path(__file__).with_name(driver)),
        "--root",
        str(trial),
        "--case",
        job["case"],
        "--policy",
        job["policy"],
        "--socket",
        str(socket),
        "--wrapper",
        str(wrapper),
    ]
    with (root / (job["root"] + ".log")).open("w") as log:
        child = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
        put(
            root / (job["root"] + "-controller.json"),
            dict(identity=process_stat(child.pid), job=job),
        )
        try:
            code = child.wait(timeout=770)
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            code = 124
    result = dict(
        job=job,
        returncode=code,
        ended_at=time.time(),
        outcome=load(trial / "LIVE.json") if (trial / "LIVE.json").exists() else None,
    )
    put(root / (job["root"] + "-exit.json"), result)
    print(
        json.dumps(
            dict(
                root=job["root"],
                case=job["case"],
                policy=job["policy"],
                returncode=code,
                quality=result["outcome"].get("quality", {}).get("verified_quality")
                if result["outcome"]
                else None,
            )
        ),
        flush=True,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    pilot = args.pilot.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "DESIGN.json").exists():
        raise ValueError("Study design already exists; inspect retained results")
    jobs = [
        dict(root="trial-" + uuid.uuid4().hex, case=case, policy=policy, repeat=repeat)
        for case in ["healthy", "adapter"]
        for policy in ["observe", "rules", "model"]
        for repeat in range(2)
    ]
    random.Random(2026102403).shuffle(jobs)
    commissioning = [
        dict(root="trial-" + uuid.uuid4().hex, case=case, policy=policy, excluded=True)
        for case, policy in [("healthy", "observe"), ("adapter", "rules")]
    ]
    put(
        root / "DESIGN.json",
        dict(
            created_at=time.time(),
            jobs=jobs,
            commissioning=commissioning,
            source_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            fixed_fallback_seconds=90,
            maximum_parent_controllers=2,
            shared_native_budget=str(pilot / "native-budget.json"),
            question=(
                "Can attention during normal worker parking reduce "
                "a protected completion-adapter stall?"
            ),
            limitation=(
                "Injected private fixture; repeated known mechanism; "
                "no model generalization or superiority claim"
            ),
        ),
    )
    deadline = time.time() + 3 * 3600
    while not (pilot / "PAIRS.json").exists():
        if time.time() >= deadline:
            raise TimeoutError("Checkpoint pilot did not finish in the reserved window")
        time.sleep(5)
    budget = pilot / "native-budget.json"
    wrapper = pilot / "native-codex"
    socket = Path("/tmp/simjecture-parked-" + uuid.uuid4().hex + ".sock")
    repo = Path.cwd()
    model_python = repo / "artifacts/model-env/bin/python"
    server_script = root / "serve.py"
    server_script.write_text(
        "import torch\ntorch.set_num_threads(2)\n"
        "free,total=torch.cuda.mem_get_info()\n"
        "assert free>11*1024**3, 'Insufficient free GPU memory'\n"
        "torch.cuda.set_per_process_memory_fraction(.6)\n"
        "from simjecture_monitor.server import main\nmain()\n"
    )
    command = [
        str(model_python),
        str(server_script),
        "--checkpoint",
        str(repo / "artifacts/models/Decision-verified"),
        "--socket",
        str(socket),
        "--status",
        str(root / "model-status.json"),
        "--wall-seconds",
        "2400",
        "--idle-seconds",
        "600",
    ]
    env = dict(os.environ, PYTHONPATH=str(repo / "packages/simjecture-monitor/src"))
    with (root / "model.log").open("w") as log:
        server = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
    put(
        root / "MODEL_PROCESS.json",
        dict(identity=process_stat(server.pid), socket=str(socket), started_at=time.time()),
    )
    try:
        until = time.time() + 150
        while not socket.exists():
            if server.poll() is not None or time.time() > until:
                raise RuntimeError("Local monitor did not become ready")
            time.sleep(1)
        commission = []
        for job in commissioning:
            result = execute(root, job, budget, wrapper, socket)
            commission.append(result)
            outcome = result["outcome"] or {}
            if result["returncode"] or outcome.get("quality", {}).get("verified_quality") != 1:
                put(root / "COMMISSIONING.json", commission)
                raise RuntimeError("Commissioning did not meet the measured report contract")
            if job["case"] == "adapter" and outcome.get("wake_reason") != "adapter_completion":
                raise RuntimeError("Rules did not repair the adapter before fallback")
        put(root / "COMMISSIONING.json", commission)
        results = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(execute, root, job, budget, wrapper, socket) for job in jobs]
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
