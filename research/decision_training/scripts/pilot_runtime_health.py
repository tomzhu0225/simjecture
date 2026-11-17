"""Read-only runtime health; no model calls or scientific computation."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from research_decision.processes import manage
from research_decision.remote_control import Remote
from research_decision.storage import read_json


def main():
    root = Path(__file__).resolve().parents[1]
    cfg = read_json(root / "config/pipeline.local.json")
    remote = Remote(cfg)
    queries = {
        "trainer": lambda: remote.process("pilot-trainer", "status"),
        "autonomous_trainer": lambda: remote.process("autonomous-trainer", "status"),
        "autonomous_request": lambda: remote.read("data/pilot-autonomous/rloo-inbox/rollout-request.json"),
        "policy_0": lambda: remote.process("policy-0", "status"),
        "policy_1": lambda: remote.process("policy-1", "status"),
        "rollout_request": lambda: remote.read("data/pilot/rloo-inbox/rollout-request.json"),
        "RL_stop": lambda: remote.read("data/pilot/rloo-inbox/stop.json"),
        "SFT_state": lambda: remote.read("checkpoints/pilot-sft/sft-epoch-2/state.json"),
        "disk": lambda: remote.call("disk"),
    }

    def query(item):
        key, function = item
        try:
            return key, function()
        except Exception as error:
            return key, {"error": repr(error)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        result = dict(pool.map(query, queries.items()))
    result.update(
        observed_at=time.time(),
        status=read_json(root / "pilot/status.json"),
        controller=manage(root, "pilot-controller", "status"),
        autonomous_controller=manage(root, "autonomous-controller", "status"),
        deadline_guard=manage(root, "pilot-deadline", "status"),
        lab_authority=manage(root, "lab-authority", "status"),
        cases=[],
    )
    for case in sorted((Path(cfg["case_store"]) / "runs").glob("*pilot*")):
        run = read_json(case / "study-run.json", {})
        counts, workers = {}, {}
        for path in (case / "experiments").glob("*.json"):
            receipt = read_json(path)
            state = receipt["status"]
            counts[state] = counts.get(state, 0) + 1
            machine = receipt.get("machine", "unknown")
            if isinstance(machine, dict):
                machine = machine.get("id", "unknown")
            workers[machine] = workers.get(machine, 0) + 1
        result["cases"].append(
            dict(
                case=case.name,
                deadline=run.get("deadline"),
                closed=(case / "phase_conclusion.json").exists(),
                executions=counts,
                workers=workers,
                independently_reviewed=(case / "assessment-receipt.json").exists(),
            )
        )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
