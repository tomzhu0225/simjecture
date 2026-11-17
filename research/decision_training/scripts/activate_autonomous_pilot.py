"""Switch the closed, quota-held pilot to the explicitly requested student branch."""

import hashlib
import json
import os
import shutil
import stat
import time
from pathlib import Path

from research_decision.processes import manage
from research_decision.remote_control import Remote
from research_decision.storage import read_json, write_json

root = Path(__file__).resolve().parents[1]
cfg = read_json(root / "config/pipeline.local.json")
status = read_json(root / "pilot/status.json")
if status.get("phase") != "quota_hold":
    raise RuntimeError("Stop and inspect an active scientific stage before changing the branch")
cases = list((Path(cfg["case_store"]) / "runs").glob("*pilot*"))
if any(not (c / "phase_conclusion.json").exists() for c in cases):
    raise RuntimeError("A scientific case remains open")
remote = Remote(cfg)
request = remote.read("data/pilot/rloo-inbox/rollout-request.json")
if request.get("completed_updates") != 0:
    raise RuntimeError("Branch transition requires explicit preservation of any existing RL optimizer")
manage(root, "pilot-controller", "stop")
for name in ["policy-0", "policy-1", "pilot-trainer"]:
    remote.process(name, "stop")
transport = Path(read_json(root / "config/isolation.local.json")["transport_socket"])
if transport.exists():
    info = transport.lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError("Refuse a non-owned transport socket")
    transport.unlink()
source = Path(cfg["case_store"]) / "runs/T01-L1-pilot-rl-000001-2/research/calculation.py"
target = root / "science_tools/mhd_core.py"
target.parent.mkdir(exist_ok=True)
if target.exists() and target.read_bytes() != source.read_bytes():
    raise ValueError("An existing scientific tool differs from its frozen source")
shutil.copyfile(source, target)
write_json(
    root / "science_tools/source-provenance.json",
    dict(source_case="T01-L1-pilot-rl-000001-2", source="calculation.py",
         sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
         reuse="solver code only; no prior results, rewards or trajectories copied", at=time.time()),
    immutable=True,
)
write_json(root / "pilot/autonomous-transition.json", dict(
    at=time.time(), previous_status=status, previous_rollout_request=request,
    user_instruction="考虑到额度问题，可以先让小模型rl先自己进行",
    pending_original_trajectories_retained=True, final_test_opened=False,
), immutable=True)
status.update(phase="autonomous_student_RL_preparing", updated_at=time.time(),
              autonomous_branch=True, GPT_required_for_training=False)
write_json(root / "pilot/status.json", status)
print(json.dumps(dict(previous_controller_stopped=True, previous_trainer_stopped=True,
                      preserved_original_RL_cases=len(cases), scientific_tool_sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
