"Observe real historical tool traces; this does not measure intervention benefit."

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from simjecture_monitor.events import PublicStream, put
from simjecture_monitor.policy import RulesPolicy
from simjecture_monitor.server import request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, action="append", required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum", type=int, default=60)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    started = time.time()
    for index, trace in enumerate(args.trace):
        scratch = args.output / f"stream-{index}.jsonl"
        scratch.touch()
        stream = PublicStream(scratch, subject=f"trace-{index}", maximum=8)
        for line in trace.read_text().splitlines():
            with scratch.open("a") as file:
                file.write(line + "\n")
            new = stream.poll()
            if not new:
                continue
            packet = stream.packet(
                "Investigate actual WarpX Langmuir charge-residual failure wh"
                "ile preserving the original scientific thresholds. Observe w"
                "hether current evidence warrants assistance or director atte"
                "ntion."
            )
            row = dict(packet=packet, rules=RulesPolicy().predict(packet), source=str(trace))
            try:
                row["model"] = request(args.socket, packet)
            except Exception as error:
                row["error"] = str(error)
            records.append(row)
            put(args.output / f"decision-{len(records):04d}.json", row)
            if len(records) >= args.maximum:
                break
        if len(records) >= args.maximum:
            break
    model = [r["model"] for r in records if "model" in r]
    summary = dict(
        scope=(
            "Real historical traces; no worker was intervened on and no d"
            "ownstream benefit is measured."
        ),
        records=len(records),
        successful_inferences=len(model),
        errors=len(records) - len(model),
        elapsed_seconds=time.time() - started,
        choice_counts={
            choice: sum(r["choice"] == choice for r in model)
            for choice in {r["choice"] for r in model}
        },
        median_forward_seconds=statistics.median(r["forward_seconds"] for r in model)
        if model
        else None,
        median_transport_seconds=statistics.median(r["transport_seconds"] for r in model)
        if model
        else None,
    )
    put(args.output / "RESULTS.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
