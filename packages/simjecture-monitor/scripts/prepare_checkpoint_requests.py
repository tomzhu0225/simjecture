"""Build sampling inputs from an explicit training-only public-checkpoint design."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path

from simjecture_monitor.checkpoint_attention import from_checkpoint, request_row


def prepare(prefixes, design):
    if design.get("split") != "train":
        raise ValueError("Require an explicitly declared training-only checkpoint design")
    names = [item["id"] for item in design["assignments"]]
    if not names or len(set(names)) != len(names):
        raise ValueError("Checkpoint design must be nonempty and contain distinct identities")
    rows = []
    for name in names:
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("Checkpoint identifiers must be simple opaque names")
        checkpoint = prefixes / name
        packet = from_checkpoint(
            checkpoint,
            packet_id=name,
            clock_id="checkpoint-request-preparation",
            captured_ms=int(time.monotonic() * 1000),
            sequence=1,
        )
        manifest = json.loads((checkpoint / "checkpoint.json").read_text())
        row = request_row(packet)
        row.update(
            split="train",
            return_group=manifest["common_prefix_sha256"],
            host_checkpoint_id=name,
        )
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefixes", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = prepare(args.prefixes, json.loads(args.design.read_text()))
    raw = "".join(json.dumps(row) + "\n" for row in rows)
    with args.output.open("x") as stream:
        stream.write(raw)
    print(json.dumps(dict(rows=len(rows), sha256=hashlib.sha256(raw.encode()).hexdigest())))


if __name__ == "__main__":
    main()
