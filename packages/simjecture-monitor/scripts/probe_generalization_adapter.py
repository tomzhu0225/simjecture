"""Secondary same-input probe of the already frozen V1 adapter; no live rollouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from simjecture_monitor.events import digest, put
from simjecture_monitor.server import request
from simjecture_monitor.startup import ready_request

from conjecture_solver.research_helper_runtime import process_stat

EXPECTED_ADAPTER = "e0f4d4c66ee3444193a952bcaa41f210f02bb4308cf7cc8303d8f4ffe7aa871c"


def load(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(base, adapter, output):
    if (output / "PROVENANCE.json").exists():
        raise ValueError("Keep previous probes; use a new directory")
    if not (base / "RESULTS.json").exists() or not (base / "MODEL_RELEASE.json").exists():
        raise ValueError("Wait for the primary exact-input replay and model release")
    if sha(adapter / "adapter_model.safetensors") != EXPECTED_ADAPTER:
        raise ValueError("Adapter weights changed since the original V1 freeze")
    selection = load(base / "SELECTION.json")
    baseline = load(base / "RESULTS.json")
    if len(selection) != len(baseline):
        raise ValueError("Primary selection/results count differs")
    output.mkdir(parents=True, exist_ok=True)
    repo = Path.cwd()
    put(
        output / "PROVENANCE.json",
        dict(
            created_at=time.time(),
            base_replay=str(base),
            selection_sha256=sha(base / "SELECTION.json"),
            base_results_sha256=sha(base / "RESULTS.json"),
            adapter_path=str(adapter),
            adapter_sha256=EXPECTED_ADAPTER,
            scope=(
                "Secondary frozen-adapter decision comparison; no training or worker-outcome claim"
            ),
            selection="Every primary slot; no substitution or selection by policy outcome",
        ),
    )
    socket = Path("/tmp/simjecture-adapter-probe-" + uuid.uuid4().hex + ".sock")
    launch = output / "serve.py"
    launch.write_text(
        "import torch\ntorch.set_num_threads(2)\n"
        "free,total=torch.cuda.mem_get_info()\nassert free>11*1024**3\n"
        "torch.cuda.set_per_process_memory_fraction(.6)\n"
        "from simjecture_monitor.server import main\nmain()\n"
    )
    env = dict(
        os.environ,
        PYTHONPATH=str(repo / "packages/simjecture-monitor/src"),
        TRITON_CACHE_DIR=str(repo / "artifacts/kernel-live-20261024/triton-cache"),
    )
    with (output / "model.log").open("w") as log:
        server = subprocess.Popen(
            [
                str(repo / "artifacts/model-fast-env/bin/python"),
                str(launch),
                "--checkpoint",
                str(repo / "artifacts/models/Decision-verified"),
                "--adapter",
                str(adapter),
                "--socket",
                str(socket),
                "--status",
                str(output / "MODEL_STATUS.json"),
                "--kernel-profile",
                "fla-prefill",
                "--wall-seconds",
                "1200",
                "--idle-seconds",
                "120",
            ],
            stdout=log,
            stderr=log,
            env=env,
            start_new_session=True,
        )
    put(output / "MODEL_PROCESS.json", dict(identity=process_stat(server.pid), socket=str(socket)))
    results = []
    until = time.time() + 900
    try:
        packet = load(repo / "artifacts/inference-fast-20261024/packets.json")[0]
        put(output / "WARMUP.json", ready_request(socket, packet, process=server))
        for number, (entry, old) in enumerate(zip(selection, baseline, strict=True)):
            record = dict(job=entry["job"], target_offset_seconds=entry["target_offset_seconds"])
            if entry.get("missing") or old.get("error"):
                results.append(record | {"missing": entry.get("missing") or old["error"]})
                continue
            packet = entry["packet"]
            assert digest(packet["state"]) == old["packet_sha256"] == packet["packet_sha256"]
            try:
                remaining = until - time.time()
                if remaining <= 0:
                    raise TimeoutError("Probe wall allowance exhausted")
                result = request(socket, packet, timeout=min(60, remaining))
                if (
                    result["model_identity"]["adapter_files_sha256"]["adapter_model.safetensors"]
                    != EXPECTED_ADAPTER
                ):
                    raise ValueError("Served adapter identity differs")
                if result["prompt_sha256"] != old["model"]["prompt_sha256"]:
                    raise ValueError("Encoded prompt messages differ between base and adapter")
                if result["model_view"] != old["model"]["model_view"]:
                    raise ValueError("Model observations differ between base and adapter")
                record.update(
                    packet_sha256=packet["packet_sha256"],
                    base=old["model"],
                    adapter=result,
                    same_choice=result["choice"] == old["model"]["choice"],
                    maximum_probability_difference=max(
                        abs(result["probabilities"][a] - p)
                        for a, p in old["model"]["probabilities"].items()
                    ),
                )
            except Exception as error:
                record["error"] = type(error).__name__ + ": " + str(error)
            put(output / ("prediction-" + str(number).zfill(3) + ".json"), record)
            results.append(record)
        put(output / "RESULTS.json", results)
        valid = [r for r in results if "same_choice" in r]
        put(
            output / "SUMMARY.json",
            dict(
                assigned=len(selection),
                compared=len(valid),
                missing=sum(bool(r.get("missing")) for r in results),
                errors=[r for r in results if r.get("error")],
                same_choices=sum(r["same_choice"] for r in valid),
                maximum_probability_difference=max(
                    (r["maximum_probability_difference"] for r in valid), default=None
                ),
                changed_choices=[
                    {k: r[k] for k in ["job", "target_offset_seconds", "packet_sha256"]}
                    | dict(base=r["base"]["choice"], adapter=r["adapter"]["choice"])
                    for r in valid
                    if not r["same_choice"]
                ],
                scope="Changed predictions alone do not establish improved workflow utility",
            ),
        )
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        put(
            output / "MODEL_RELEASE.json",
            dict(
                ended_at=time.time(),
                returncode=server.returncode,
                socket_present=socket.exists(),
            ),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.base.resolve(), args.adapter.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
