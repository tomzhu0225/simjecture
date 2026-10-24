"""Measure resident local inference against saved A100 predictions on identical packets."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from simjecture_monitor.events import put
from simjecture_monitor.model import MonitorModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--adapter")
    parser.add_argument("--kernel-profile", choices=["fla-prefill"])
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    packets = json.loads(args.packets.read_text())
    reference = json.loads(args.reference.read_text())
    import torch

    free_before, total_memory = torch.cuda.mem_get_info()
    started = time.time()
    model = MonitorModel(args.checkpoint, adapter=args.adapter, kernel_profile=args.kernel_profile)
    torch = model.torch
    torch.cuda.synchronize()
    loaded = time.time()
    status = dict(
        stage="running",
        started_at=started,
        model_identity=model.identity,
        device=torch.cuda.get_device_name(),
        torch_version=torch.__version__,
        cuda_version=torch.version.cuda,
        cpu_threads=torch.get_num_threads(),
        device_total_bytes=total_memory,
        cuda_reported_used_bytes_before_model=total_memory - free_before,
        load_seconds=loaded - started,
        resident_allocated_bytes=torch.cuda.memory_allocated(),
        resident_reserved_bytes=torch.cuda.memory_reserved(),
    )
    put(args.output / "status.json", status)
    rows = []
    for repetition in range(2):
        for index, packet in enumerate(packets):
            result = model.predict(packet)
            expected = reference[index]
            if result["prompt_sha256"] != expected["prompt_sha256"]:
                raise ValueError("Local and remote benchmark prompts differ")
            if (
                model.identity["adapter_files_sha256"]
                != expected["model_identity"]["adapter_files_sha256"]
            ):
                raise ValueError("Local and remote adapter identities differ")
            if (
                model.identity["checkpoint_config_sha256"]
                != expected["model_identity"]["checkpoint_config_sha256"]
            ):
                raise ValueError("Local and remote checkpoint configurations differ")
            rows.append(
                dict(
                    repetition=repetition,
                    packet_index=index,
                    prediction=result,
                    reference_choice=expected["choice"],
                    choice_agrees=result["choice"] == expected["choice"],
                    maximum_probability_difference=max(
                        abs(p - expected["probabilities"][key])
                        for key, p in result["probabilities"].items()
                    ),
                )
            )
            put(args.output / "predictions.json", rows)
    warm = [row["prediction"] for row in rows if row["repetition"] == 1]
    status.update(
        stage="completed",
        ended_at=time.time(),
        packets=len(packets),
        repetitions=2,
        warm_median_forward_seconds=statistics.median(r["forward_seconds"] for r in warm),
        warm_median_total_seconds=statistics.median(r["total_seconds"] for r in warm),
        warm_maximum_total_seconds=max(r["total_seconds"] for r in warm),
        peak_cuda_bytes=torch.cuda.max_memory_allocated(),
        choice_agreements=sum(row["choice_agrees"] for row in rows),
        comparisons=len(rows),
        maximum_probability_difference=max(row["maximum_probability_difference"] for row in rows),
        input_tokens=[r["input_tokens"] for r in warm],
        limitation=(
            "Resident inference on retained monitoring packets; no throughput or power benchmark."
        ),
    )
    put(args.output / "status.json", status)
    print(json.dumps(status))


if __name__ == "__main__":
    main()
