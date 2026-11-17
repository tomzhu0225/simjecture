"""Record explicitly selected full-pipeline stages and the exact protocol hash."""

import argparse
import json
from pathlib import Path

from research_decision.contracts import fingerprint
from research_decision.storage import read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stages", nargs="+", choices=["collect-sft", "sft", "online", "dev"])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    write_json(root / "launch-authorization.json", dict(
        authorized=True, stages=args.stages, protocol_sha256=fingerprint(read_json(root / "config/protocol.json")),
        source="Explicit operator command; no experiment launched by this helper",
    ))
    print(json.dumps(dict(configured_stages=args.stages, experiments_started=0)))


if __name__ == "__main__":
    main()
