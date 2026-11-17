"""Compact truthful progress, including actual optimizer steps, not just groups."""

import json
from pathlib import Path

from research_decision.processes import manage
from research_decision.remote_control import Remote
from research_decision.storage import read_json

root = Path(__file__).resolve().parents[1]
cfg = read_json(root / "config/pipeline.local.json")
remote = Remote(cfg)
request = remote.read("data/pilot-autonomous/rloo-inbox/rollout-request.json") or {}
state = None
if request.get("completed_updates", 0):
    relative = Path(request["policy_path"]).relative_to(remote.root)
    state = remote.read(str(relative / "state.json"))
    manifest = remote.read(str(relative / "manifest.json"))
else:
    manifest = {}
counts = dict(cases=0, closed=0, successful_experiments=0, failed_experiments=0, worker_ids=[])
workers = set()
for case in (Path(cfg["case_store"]) / "runs").glob("*pilot-auto-*"):
    counts["cases"] += 1
    counts["closed"] += (case / "phase_conclusion.json").exists()
    for path in (case / "experiments").glob("*.json"):
        value = read_json(path)
        counts["successful_experiments"] += value["status"] == "succeeded"
        counts["failed_experiments"] += value["status"] in {"failed", "timed_out", "cancelled", "interrupted"}
        workers.add(value.get("machine", "unknown"))
counts["worker_ids"] = sorted(workers)
print(json.dumps(dict(
    phase=read_json(root / "pilot/status.json").get("phase"),
    controller_active=manage(root, "autonomous-controller", "status")["active"],
    trainer_active=remote.process("autonomous-trainer", "status")["active"],
    completed_groups=request.get("completed_updates", 0),
    optimizer_steps=(state or {}).get("optimizer_steps", 0),
    eligible_actions=(state or {}).get("eligible_actions"),
    policy_sha256=request.get("policy_sha256"),
    checkpoint_manifest_files=len(manifest), counts=counts,
    GPT_calls_in_autonomous_training=0,
)))
