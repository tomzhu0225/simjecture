"""Measure a fixed monitor on fresh blinded checkpoints, without routing actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from simjecture_monitor.events import digest, put
from simjecture_monitor.model import MonitorModel
from simjecture_monitor.policy import RulesPolicy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--adapter")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    design = json.loads((args.root / "DESIGN.json").read_text())
    import torch

    torch.set_num_threads(2)
    free, total = torch.cuda.mem_get_info()
    if free < 11 * 1024**3:
        raise ValueError("Insufficient free GPU memory for the bounded inference probe")
    torch.cuda.set_per_process_memory_fraction(0.6)
    started = time.time()
    model = MonitorModel(args.checkpoint, adapter=args.adapter)
    rows = []
    for index, case in enumerate(design["cases"]):
        packet = json.loads((args.root / case["checkpoint"] / "observation.json").read_text())
        prediction = model.predict(packet)
        batch, _, _, prompt_hash, view = model.encode(packet)
        if prediction["prompt_sha256"] != prompt_hash:
            raise ValueError("Prediction and reconstructed prompt differ")
        rows.append(
            dict(
                checkpoint=case["checkpoint"],
                host_case_label=case["kind"],
                packet_sha256=packet["packet_sha256"],
                prediction=prediction,
                rules=RulesPolicy().predict(packet),
                encoded_ids_sha256=hashlib.sha256(
                    batch.input_ids.cpu().numpy().tobytes()
                ).hexdigest(),
                view_receipt=view,
            )
        )
        put(args.output / "predictions.json", rows)
        print(
            json.dumps(
                dict(
                    index=index,
                    checkpoint=case["checkpoint"],
                    choice=prediction["choice"],
                    tokens=prediction["input_tokens"],
                )
            ),
            flush=True,
        )
    # Identical visible inputs must not acquire incompatible oracle labels merely
    # because a host-only latent fault assignment is different.
    packet = json.loads(
        (args.root / design["cases"][0]["checkpoint"] / "observation.json").read_text()
    )
    twins = [
        dict(host_only_latent_fault=label, packet_sha256=digest(packet)) for label in [False, True]
    ]
    put(
        args.output / "identifiability.json",
        dict(
            twins=twins,
            visible_inputs_identical=twins[0]["packet_sha256"] == twins[1]["packet_sha256"],
            instruction=(
                "Do not train contradictory action labels from unobserved host fault metadata"
            ),
        ),
    )
    put(
        args.output / "status.json",
        dict(
            stage="completed",
            started_at=started,
            ended_at=time.time(),
            model_identity=model.identity,
            packets=len(rows),
            device=torch.cuda.get_device_name(),
            peak_cuda_bytes=torch.cuda.max_memory_allocated(),
            device_used_bytes_before=total - free,
            scope="Fixed-policy replay on new decision points; no live model-effectiveness claim",
        ),
    )


if __name__ == "__main__":
    main()
