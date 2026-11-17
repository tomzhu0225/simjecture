"""Owned pilot lifecycle on the controller (not a scientific compute worker)."""

import json
import sys
from pathlib import Path

from research_decision.processes import manage

root = Path(__file__).resolve().parents[1]
operation = sys.argv[1] if len(sys.argv) > 1 else "status"
argv = (
    [str(root / "bin/controller-python"), "-m", "research_decision.pilot"] if operation == "start" else None
)
print(json.dumps(manage(root, "pilot-controller", operation, argv)))
