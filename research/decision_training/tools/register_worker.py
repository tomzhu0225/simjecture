"""Register an already prepared remote CPU worker with the native registry."""

import argparse
import json
from pathlib import Path

from conjecture_solver.execution_pool import MachineRegistry

from research_decision.storage import read_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", choices=["remote-cpu", "independent-cpu"], required=True)
    parser.add_argument("--cpus", type=int, required=True)
    parser.add_argument("--memory-mb", type=int, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cfg = read_json(root / "config/pipeline.local.json")
    registry = MachineRegistry(cfg["machine_registry"])
    remote = cfg["remote_root"]
    registry.save(dict(
        id=args.id, label=args.id, kind="ssh",
        host="cannlab-cpu" if args.id == "independent-cpu" else "cannlab-science",
        root=remote + "/cpu-worker", python=remote + "/resources/cpu-python",
        config=dict(execution_backend="process-cooperative", capabilities=[], cpus=args.cpus,
                    memory_mb=args.memory_mb, gpu_ids=[], max_jobs=args.cpus),
    ))
    # Use only profiles actually registered here; adding a second worker later
    # affects new studies, never the immutable pool of an existing study.
    cfg["machine_ids"] = [name for name in ["remote-cpu", "independent-cpu"] if registry.path(name).is_file()]
    write_json(root / "config/pipeline.local.json", cfg)
    if args.check:
        print(json.dumps(registry.check(args.id)))
    else:
        print(json.dumps(dict(registered=args.id, machine_ids=cfg["machine_ids"])))


if __name__ == "__main__":
    main()
