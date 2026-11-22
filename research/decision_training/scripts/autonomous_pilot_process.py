"""Manage autonomous student RL independently of this chat and GPT quota."""

import json
import sys
from pathlib import Path

from research_decision.processes import manage

root = Path(__file__).resolve().parents[1]
operation = sys.argv[1] if len(sys.argv) > 1 else "status"
argv = [str(root / "bin/controller-python"), "-m", "research_decision.autonomous_pilot"]
print(json.dumps(manage(root, "autonomous-controller", operation, argv if operation == "start" else None)))
