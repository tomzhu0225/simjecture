"""Bounded commissioning and frozen four-arm live comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from generalization_fixture import CASES
from simjecture_monitor.events import put
from simjecture_monitor.native_guard import locked, reap, stop_session
from simjecture_monitor.server import request

from conjecture_solver.research_helper_runtime import process_stat


def load(path):
    return json.loads(path.read_text())


def setup_budget(shared):
    budget = shared / "native-budget.json"
    if not budget.exists():
        put(
            budget,
            dict(
                deadline=time.time() + 6 * 3600,
                maximum_starts=288,
                maximum_per_continuation=10,
                maximum_concurrent=4,
                executable=shutil.which("codex"),
                starts=[],
            ),
        )
    wrapper = shared / "native-codex"
    if not wrapper.exists():
        wrapper.write_text(
            "#!" + str(Path(sys.executable).absolute()) + "\n"
            "from simjecture_monitor.native_guard import main\nmain()\n"
        )
        wrapper.chmod(0o755)
    return budget, wrapper


def execute(root, job, budget, wrapper, socket):
    trial = root / job["root"]
    if trial.exists():
        raise ValueError("Retain prior runs; never overwrite")
    env = dict(
        os.environ,
        SIMJECTURE_NATIVE_BUDGET=str(budget),
        SIMJECTURE_CONTINUATION=job["root"],
        SIMJECTURE_CONTINUATION_DEADLINE=str(time.time() + 690),
    )
    command = [
        sys.executable,
        "-u",
        str(Path(__file__).with_name("generalization_trials.py")),
        "--root",
        str(trial),
        "--family",
        job["family"],
        "--arm",
        job["arm"],
        "--seed",
        str(job["seed"]),
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
    processes = trial / "execution/PROCESSES.json"
    if processes.exists():
        for row in load(processes):
            stop_session(row["identity"])
    with locked(budget) as state:
        reap(state)
    outcome = load(trial / "OUTCOME.json") if (trial / "OUTCOME.json").exists() else None
    result = dict(job=job, returncode=code, ended_at=time.time(), outcome=outcome)
    put(root / (job["root"] + "-exit.json"), result)
    print(
        json.dumps(
            dict(
                job=job,
                returncode=code,
                verified=outcome.get("verified_complete") if outcome else None,
                elapsed=outcome.get("elapsed_seconds") if outcome else None,
            )
        ),
        flush=True,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--phase", choices=["commissioning", "main"], required=True)
    parser.add_argument("--commission", type=Path)
    args = parser.parse_args()
    root, shared, repo = args.root.resolve(), args.shared.resolve(), Path.cwd()
    shared.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    if (root / "DESIGN.json").exists():
        raise ValueError("Retain an existing design")
    frozen = load(shared / "POLICY_FREEZE.json")
    for name, sha in frozen["files"].items():
        if name.endswith(".py") and hashlib.sha256(Path(name).read_bytes()).hexdigest() != sha:
            raise ValueError("Frozen policy code changed: " + name)
    budget, wrapper = setup_budget(shared)
    if args.phase == "main":
        if args.commission is None:
            raise ValueError("A completed commissioning root is required")
        commission = load(args.commission / "RESULTS.json")
        if len(commission) != 4 or any(
            r["returncode"]
            or not r["outcome"].get("verified_complete")
            or r["outcome"].get("observation_violations")
            for r in commission
        ):
            raise ValueError("Commissioning did not satisfy the instrumentation contract")
    blocks = []
    if args.phase == "commissioning":
        scenarios = [
            ("progressing_work", "observe"),
            ("development_failure", "rules"),
            ("announced_quiet", "model"),
            ("development_failure", "hybrid"),
        ]
        for family, arm in scenarios:
            blocks.append(
                dict(
                    jobs=[
                        dict(
                            root="trial-" + uuid.uuid4().hex,
                            family=family,
                            arm=arm,
                            seed=2026102500,
                            repeat=0,
                        )
                    ],
                    commissioning=True,
                )
            )
    else:
        order = ["observe", "rules", "model", "hybrid"]
        random.Random(2026102501).shuffle(order)
        for repeat in range(2):
            for arm in order if repeat == 0 else list(reversed(order)):
                jobs = [
                    dict(
                        root="trial-" + uuid.uuid4().hex,
                        family=family,
                        arm=arm,
                        seed=2026102500 + repeat,
                        repeat=repeat,
                    )
                    for family in CASES
                ]
                random.Random(2026102502 + repeat).shuffle(jobs)
                blocks.append(dict(arm=arm, repeat=repeat, jobs=jobs))
    files = [
        "packages/simjecture-monitor/scripts/generalization_fixture.py",
        "packages/simjecture-monitor/scripts/generalization_trials.py",
        "packages/simjecture-monitor/scripts/run_generalization_study.py",
        "packages/simjecture-monitor/src/simjecture_monitor/repair_roles.py",
        "research/evaluations/monitor-generalization-20261025/PROTOCOL.md",
    ]
    put(
        root / "DESIGN.json",
        dict(
            phase=args.phase,
            blocks=blocks,
            created_at=time.time(),
            source_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            source_hashes={p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files},
            policy_freeze=frozen,
            maximum_parents=2,
            native_budget=str(budget),
            ordering="Counterbalanced arm blocks; two simultaneous tasks from the same arm",
            label_access="Host-only assignments; raw observation collector never reads them",
        ),
    )
    socket = Path("/tmp/simjecture-generalization-" + uuid.uuid4().hex + ".sock")
    launch = root / "serve.py"
    launch.write_text(
        "import torch\ntorch.set_num_threads(2)\n"
        "free,total=torch.cuda.mem_get_info()\nassert free>11*1024**3\n"
        "torch.cuda.set_per_process_memory_fraction(.6)\n"
        "from simjecture_monitor.server import main\nmain()\n"
    )
    command = [
        str(repo / "artifacts/model-fast-env/bin/python"),
        str(launch),
        "--checkpoint",
        str(repo / "artifacts/models/Decision-verified"),
        "--socket",
        str(socket),
        "--status",
        str(root / "MODEL_STATUS.json"),
        "--kernel-profile",
        "fla-prefill",
        "--wall-seconds",
        "21600",
        "--idle-seconds",
        "1800",
    ]
    env = dict(
        os.environ,
        PYTHONPATH=str(repo / "packages/simjecture-monitor/src"),
        TRITON_CACHE_DIR=str(repo / "artifacts/kernel-live-20261024/triton-cache"),
    )
    with (root / "model.log").open("w") as log:
        server = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
    put(root / "MODEL_PROCESS.json", dict(identity=process_stat(server.pid), socket=str(socket)))
    results = []
    try:
        until = time.time() + 180
        while not socket.exists():
            if server.poll() is not None or time.time() > until:
                raise RuntimeError("Model not ready")
            time.sleep(1)
        packet = load(repo / "artifacts/inference-fast-20261024/packets.json")[0]
        put(root / "WARMUP.json", request(socket, packet, timeout=120))
        for number, block in enumerate(blocks):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(execute, root, job, budget, wrapper, socket)
                    for job in block["jobs"]
                ]
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    put(
                        root / "PROGRESS.json",
                        dict(completed=len(results), block=number, results=results),
                    )
                    if args.phase == "commissioning" and (
                        result["returncode"]
                        or not result["outcome"]
                        or not result["outcome"].get("verified_complete")
                        or result["outcome"].get("observation_violations")
                    ):
                        put(root / "RESULTS.json", results)
                        raise RuntimeError("Commissioning stopped; retain and inspect this result")
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
