"""Counterbalanced live comparison of unchanged 4B inference runtimes."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from run_parked_study import execute
from simjecture_monitor.events import put
from simjecture_monitor.server import request

from conjecture_solver.research_helper_runtime import process_stat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    args = parser.parse_args()
    root, pilot, repo = args.root.resolve(), args.pilot.resolve(), Path.cwd()
    root.mkdir(parents=True, exist_ok=True)
    if (root / "DESIGN.json").exists():
        raise ValueError("Retain existing trials; never overwrite")
    rng = random.Random(2026102406)
    blocks = []
    for number, profile in enumerate(["reference", "fla-prefill", "fla-prefill", "reference"]):
        jobs = [
            dict(
                root="trial-" + uuid.uuid4().hex,
                case=case,
                policy="model",
                profile=profile,
                repeat=number // 2,
            )
            for case in ["healthy", "adapter"]
        ]
        rng.shuffle(jobs)
        blocks.append(dict(number=number, profile=profile, jobs=jobs))
    put(
        root / "DESIGN.json",
        dict(
            created_at=time.time(),
            blocks=blocks,
            source_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            seed=2026102406,
            maximum_parent_controllers=2,
            shared_native_budget=str(pilot / "native-budget.json"),
            question="Does the faster same-weight runtime reduce fault-response latency?",
            limitations=(
                "Eight fresh trajectories; known injected mechanism; sequential ABBA blocks "
                "on shared GPU; no LoRA training or generalization claim"
            ),
            warmup="First frozen packet once per server; retained separately from live calls",
        ),
    )
    wrapper = root / "serve.py"
    wrapper.write_text(
        "import torch\ntorch.set_num_threads(2)\n"
        "free,total=torch.cuda.mem_get_info()\n"
        "assert free>11*1024**3\n"
        "torch.cuda.set_per_process_memory_fraction(.6)\n"
        "from simjecture_monitor.server import main\nmain()\n"
    )
    packet = json.loads((repo / "artifacts/inference-fast-20261024/packets.json").read_text())[0]
    # Benchmark packet container also retains a human-readable identifier.
    packet = packet.get("packet", packet)
    results = []
    for block in blocks:
        block_root = root / ("block-" + str(block["number"]))
        block_root.mkdir()
        profile = block["profile"]
        python = repo / (
            "artifacts/model-env/bin/python"
            if profile == "reference"
            else "artifacts/model-fast-env/bin/python"
        )
        socket = Path("/tmp/simjecture-kernel-" + uuid.uuid4().hex + ".sock")
        command = [
            str(python),
            str(wrapper),
            "--checkpoint",
            str(repo / "artifacts/models/Decision-verified"),
            "--socket",
            str(socket),
            "--status",
            str(block_root / "MODEL_STATUS.json"),
            "--wall-seconds",
            "900",
            "--idle-seconds",
            "300",
        ]
        if profile != "reference":
            command += ["--kernel-profile", profile]
        env = dict(
            os.environ,
            PYTHONPATH=str(repo / "packages/simjecture-monitor/src"),
            TRITON_CACHE_DIR=str(root / "triton-cache"),
        )
        with (block_root / "model.log").open("w") as log:
            server = subprocess.Popen(
                command, env=env, stdout=log, stderr=log, start_new_session=True
            )
        put(
            block_root / "MODEL_PROCESS.json",
            dict(identity=process_stat(server.pid), command=command, socket=str(socket)),
        )
        try:
            until = time.time() + 180
            while not socket.exists():
                if server.poll() is not None or time.time() > until:
                    raise RuntimeError("Model server did not become ready")
                time.sleep(1)
            put(block_root / "WARMUP.json", request(socket, packet, timeout=120))
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(
                        execute,
                        root,
                        job,
                        pilot / "native-budget.json",
                        pilot / "native-codex",
                        socket,
                    )
                    for job in block["jobs"]
                ]
                for future in futures:
                    results.append(future.result())
                    put(root / "PROGRESS.json", dict(completed=len(results), results=results))
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()
            put(
                block_root / "MODEL_RELEASE.json",
                dict(
                    ended_at=time.time(),
                    returncode=server.returncode,
                    socket_present=socket.exists(),
                ),
            )
    put(root / "RESULTS.json", results)


if __name__ == "__main__":
    main()
