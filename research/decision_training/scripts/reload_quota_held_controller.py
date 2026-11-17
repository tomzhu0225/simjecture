"""Reload engineering fixes only at a verified, closed-study quota boundary."""

import json
import os
import stat
import time
from pathlib import Path

from research_decision.processes import manage
from research_decision.remote_control import Remote
from research_decision.storage import read_json, write_json

root = Path(__file__).resolve().parents[1]
cfg = read_json(root / "config/pipeline.local.json")
status = read_json(root / "pilot/status.json")
if status["phase"] != "quota_hold" or status.get("quota_resume_epoch", 0) <= time.time():
    raise RuntimeError("Only a pending, persisted provider-quota hold permits this controlled reload")
cases = list((Path(cfg["case_store"]) / "runs").glob("*pilot*"))
if not cases or any(not (c / "phase_conclusion.json").exists() for c in cases):
    raise RuntimeError("A pilot study is still open; do not invalidate a mounted transport socket")
remote = Remote(cfg)
if any(remote.process("policy-" + str(slot), "status")["active"] for slot in range(2)):
    raise RuntimeError("An inference actor is still active")
before = {
    "controller": manage(root, "pilot-controller", "status"),
    "deadline": manage(root, "pilot-deadline", "status"),
    "trainer": remote.process("pilot-trainer", "status"),
    "request": remote.read("data/pilot/rloo-inbox/rollout-request.json"),
    "quota_resume_epoch": status["quota_resume_epoch"],
}
manage(root, "pilot-controller", "stop")
if manage(root, "pilot-controller", "status")["active"]:
    raise RuntimeError("The previous controller has not stopped")
transport = Path(read_json(root / "config/isolation.local.json")["transport_socket"])
if transport.exists():
    info = transport.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError("Refuse to remove a non-owned, non-socket transport path")
    transport.unlink()
manage(root, "pilot-deadline", "stop")
after = {
    "controller": manage(
        root, "pilot-controller", "start", [str(root / "bin/controller-python"), "-m", "research_decision.pilot"]
    ),
    "deadline": manage(
        root, "pilot-deadline", "start",
        [str(root / "bin/controller-python"), "-m", "research_decision.pilot_deadline"],
    ),
    "trainer": remote.process("pilot-trainer", "status"),
}
assert before["trainer"]["record"]["pid"] == after["trainer"]["record"]["pid"]
write_json(
    root / "pilot/autonomy-reload.json",
    dict(before=before, after=after, reloaded_at=time.time(),
         scientific_clocks_reset=False, new_model_calls=0, pending_group_preserved=True),
)
print(json.dumps(dict(controller=after["controller"]["active"], deadline_guard=after["deadline"]["active"],
                      trainer_unchanged=True, quota_resume_epoch=status["quota_resume_epoch"])))
