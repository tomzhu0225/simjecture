"""Resume closed autonomous records without resetting any scientific clock."""

import json
import os
import stat
from pathlib import Path

from research_decision.processes import manage
from research_decision.storage import read_json

root = Path(__file__).resolve().parents[1]
if manage(root, "autonomous-controller", "status")["active"]:
    raise RuntimeError("Existing autonomous controller is active")
cfg = read_json(root / "config/pipeline.local.json")
for case in (Path(cfg["case_store"]) / "runs").glob("*pilot-auto-*"):
    if not (case / "phase_conclusion.json").exists():
        raise RuntimeError("An interrupted scientific case requires settlement before controller recovery")
socket = Path(read_json(root / "config/isolation.local.json")["transport_socket"])
if socket.exists():
    info = socket.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError("Unexpected stale transport identity")
    socket.unlink()
print(json.dumps(manage(root, "autonomous-controller", "start",
                       [str(root / "bin/controller-python"), "-m", "research_decision.autonomous_pilot"])))
