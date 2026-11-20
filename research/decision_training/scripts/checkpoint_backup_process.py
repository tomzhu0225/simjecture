"""Manage the I/O-only checkpoint backup service; never starts a research role."""

import json
import sys
from pathlib import Path

from research_decision.processes import manage

root = Path(__file__).resolve().parents[1]
operation = sys.argv[1] if len(sys.argv) > 1 else "status"
argv = [str(root / "bin/controller-python"), "-m", "research_decision.checkpoint_backup"]
print(json.dumps(manage(root, "pilot-backup", operation, argv if operation == "start" else None)))
