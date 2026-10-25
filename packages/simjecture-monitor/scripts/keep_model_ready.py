"""Bounded, separately accounted warmup during long rule-only experiment blocks."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from simjecture_monitor.events import put
from simjecture_monitor.server import request

from conjecture_solver.research_helper_runtime import owned_alive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--process", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    process = json.loads(args.process.read_text())
    controller = json.loads(args.controller.read_text())["identity"]
    packet = json.loads(args.packet.read_text())[0]
    started = time.time()
    status = dict(
        started_at=started,
        purpose="Keep the one frozen model resident across long rule-only blocks",
        scope="Fixed archived warmup only; no study observation, worker action or model update",
        calls=[],
    )
    put(args.output, status)
    try:
        while owned_alive(controller) and owned_alive(process["identity"]):
            model = json.loads(args.status.read_text())
            # Retain the original absolute six-hour server bound.
            if time.time() >= model["started_at"] + 21600:
                break
            if time.time() - model.get("last_call_at", model["started_at"]) >= 600:
                called_at = time.time()
                try:
                    result = request(Path(process["socket"]), packet, timeout=60)
                    status["calls"].append(dict(at=called_at, result=result))
                except Exception as error:
                    status["calls"].append(dict(at=called_at, error=repr(error)))
                    put(args.output, status)
                    break
                put(args.output, status)
            time.sleep(5)
    finally:
        status["ended_at"] = time.time()
        put(args.output, status)


if __name__ == "__main__":
    main()
