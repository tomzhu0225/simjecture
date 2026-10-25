"""Prespecified same-input policy replay from observation-only live trajectories."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from simjecture_monitor.checks_policy import ChecksAwareRules
from simjecture_monitor.events import digest, put
from simjecture_monitor.generic_policy import GenericOperationalRules
from simjecture_monitor.server import request
from simjecture_monitor.startup import ready_request

from conjecture_solver.research_helper_runtime import process_stat


def load(path):
    return json.loads(path.read_text())


def select(root):
    design = load(root / "DESIGN.json")
    selection = []
    for block in design["blocks"]:
        for job in block["jobs"]:
            if job["arm"] != "observe":
                continue
            trial = root / job["root"]
            outcome = load(trial / "OUTCOME.json")
            periods = outcome.get("parking", [])
            observation_file = trial / "monitor/observations.jsonl"
            records = (
                [json.loads(line) for line in observation_file.read_text().splitlines()]
                if observation_file.exists()
                else []
            )
            for offset in [10, 25, 40]:
                entry = dict(job=job, target_offset_seconds=offset)
                if not periods:
                    selection.append(entry | {"missing": "No first parking interval"})
                    continue
                period = periods[0]
                candidates = []
                for packet in records:
                    if not packet["state"]["host_state"]["worker_parked"]:
                        continue
                    observed = max(e["observed_at"] for e in packet["state"]["events"])
                    if period["started_at"] + offset <= observed < period["ended_at"]:
                        candidates.append((observed, packet))
                if not candidates:
                    selection.append(
                        entry
                        | {"missing": "No observation in specified interval", "parking": period}
                    )
                    continue
                observed, packet = min(candidates, key=lambda item: item[0])
                assert packet["packet_sha256"] == digest(packet["state"])
                selection.append(
                    entry
                    | dict(
                        packet=packet,
                        selected_at=observed,
                        actual_offset_seconds=observed - period["started_at"],
                        parking=period,
                    )
                )
    return selection


def evidence(entry):
    """Descriptive evidence tags; never supplied to any policy or used for tuning."""
    host = entry["packet"]["state"]["host_state"]
    public = host["public_artifacts"]
    telemetry = host["telemetry"]
    tags = []
    for r in telemetry.get("source_records", []):
        common = set(r.get("request", {})) & set(r.get("source", {}))
        if any(r["request"][k] != r["source"][k] for k in common):
            tags.append("published_source_identity_disagreement")
    for r in public.get("diagnostic_rows", []):
        raw, reported = r.get("stored_peak_electric_field"), r.get("peak_electric_field_V_per_m")
        if (
            isinstance(raw, (int, float))
            and isinstance(reported, (int, float))
            and abs(raw - reported) > abs(raw) * 1e-6
        ):
            tags.append("published_absolute_quantity_disagrees_with_SI_storage")
    progress = public.get("progress", {})
    if progress.get("waiting_for"):
        tags.append("published_unmatched_input_pattern")
    history = host.get("progress_history", [])
    losses = [p["loss"] for p in history if isinstance(p.get("loss"), (int, float))]
    if len(losses) >= 3 and min(losses) > 1e-3 and max(losses) - min(losses) < 1e-8:
        tags.append("three_observed_updates_without_loss_reduction")
    if telemetry.get("terminal_exit_code") not in (None, 0):
        tags.append("nonzero_process_exit")
    return sorted(set(tags))


def run(source, output):
    if (output / "SELECTION.json").exists():
        raise ValueError("Retain previous replay; use a new directory")
    if not (source / "RESULTS.json").exists() or not (source / "MODEL_RELEASE.json").exists():
        raise ValueError("Wait for main collection and model release")
    repo = Path.cwd()
    output.mkdir(parents=True, exist_ok=True)
    selection = select(source)
    put(output / "SELECTION.json", selection)
    put(
        output / "PROVENANCE.json",
        dict(
            source=str(source),
            source_design_sha256=hashlib.sha256((source / "DESIGN.json").read_bytes()).hexdigest(),
            selection_sha256=hashlib.sha256((output / "SELECTION.json").read_bytes()).hexdigest(),
            created_at=time.time(),
            selection_rule=(
                "First parked observe-only packet at/after10,25,40seconds, "
                "before interval end; no replacements"
            ),
            model="unchanged frozen base; deterministic greedy; no LoRA",
            hybrid=(
                "Reuse the same deterministic model prediction only when checks-aware rules defer"
            ),
            label_access=(
                "Evidence tags and host family labels are added after inference "
                "and never sent to policies"
            ),
        ),
    )
    socket = Path("/tmp/simjecture-generalization-replay-" + uuid.uuid4().hex + ".sock")
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
    try:
        warmup = load(repo / "artifacts/inference-fast-20261024/packets.json")[0]
        put(output / "WARMUP.json", ready_request(socket, warmup, process=server))
        for number, entry in enumerate(selection):
            if entry.get("missing"):
                results.append(entry)
                continue
            packet = entry["packet"]
            record = {k: v for k, v in entry.items() if k != "packet"}
            record["packet_sha256"] = packet["packet_sha256"]
            record["operational_rules"] = GenericOperationalRules().predict(packet)
            record["rules"] = ChecksAwareRules().predict(packet)
            try:
                record["model"] = request(socket, packet, timeout=60)
                record["hybrid"] = (
                    record["rules"] if record["rules"]["choice"] != "defer" else record["model"]
                )
                record["observation_omissions"] = (
                    record["model"].get("model_view", {}).get("omitted_event_ids", [])
                )
            except Exception as error:
                record["error"] = type(error).__name__ + ": " + str(error)
            record["descriptive_evidence_tags"] = evidence(entry)
            put(output / ("prediction-" + str(number).zfill(3) + ".json"), record)
            results.append(record)
        put(output / "RESULTS.json", results)
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
                ended_at=time.time(), returncode=server.returncode, socket_present=socket.exists()
            ),
        )
    print(
        json.dumps(
            dict(
                selected=len(selection),
                missing=sum(bool(r.get("missing")) for r in results),
                errors=sum(bool(r.get("error")) for r in results),
            )
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
