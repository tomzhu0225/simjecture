"""Copy small authoritative checkpoint state/manifest; never deserialize weights."""

import json
import time
from pathlib import Path

from research_decision.remote_control import Remote
from research_decision.storage import read_json, write_json

root = Path(__file__).resolve().parents[1]
remote = Remote(read_json(root / "config/pipeline.local.json"))
request = remote.read("data/pilot-autonomous/rloo-inbox/rollout-request.json")
if not request.get("completed_updates"):
    raise RuntimeError("No committed autonomous RL checkpoint")
relative = Path(request["policy_path"]).relative_to(remote.root)
state = remote.read(str(relative / "state.json"))
manifest = remote.read(str(relative / "manifest.json"))
assert state["optimizer_steps"] > 0 and manifest["adapter_model.safetensors"] == request["policy_sha256"]
receipt = dict(observed_at=time.time(), request=request, state=state, manifest=manifest,
               copied_metadata_only=True, full_archive_status="see checkpoint-backups backup-receipt.json")
write_json(root / "pilot" / (relative.name + "-verified-metadata.json"), receipt)
print(json.dumps(dict(checkpoint=str(relative), optimizer_steps=state["optimizer_steps"],
                      adapter_sha256=request["policy_sha256"], optimizer_and_two_RNG_files_present=all(
                          name in manifest for name in ["optimizer.pt", "rank-0.pt", "rank-1.pt"]))))
