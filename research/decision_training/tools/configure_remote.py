"""Prepare wrappers on one remote node using existing Python environments."""

import argparse
import json
import shlex
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["training", "cpu"])
    parser.add_argument("--python", type=Path, required=True, help="Existing node-specific Python interpreter")
    parser.add_argument("--cann-env", type=Path)
    parser.add_argument("--ld-preload", type=Path)
    parser.add_argument("--driver-lib", action="append", default=[])
    parser.add_argument("--cpu-affinity", help="Optional taskset mask, e.g.0-3 for the NPU host's training process")
    parser.add_argument("--cpus", type=int, default=16)
    parser.add_argument("--memory-mb", type=int, default=24576)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    repo = root.parents[1]
    if not args.python.is_file():
        parser.error("The supplied Python interpreter does not exist")
    resources = root / "resources"
    resources.mkdir(exist_ok=True)
    name = "training-python" if args.kind == "training" else "cpu-python"
    target = resources / name
    if target.exists():
        raise FileExistsError("Do not overwrite a live wrapper: " + str(target))
    lines = ["#!/bin/bash", "set -e", "set -o pipefail"]
    if args.cann_env:
        lines += ["source " + shlex.quote(str(args.cann_env))]
    if args.ld_preload:
        lines += ["export LD_PRELOAD=" + shlex.quote(str(args.ld_preload))]
    if args.driver_lib:
        lines += ["export LD_LIBRARY_PATH=" + shlex.quote(":".join(args.driver_lib)) + '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}']
    lines += ["export PYTHONPATH=" + shlex.quote(str(root) + ":" + str(repo / "src")) + '${PYTHONPATH:+:$PYTHONPATH}']
    if args.kind == "cpu":
        lines += ["export ASCEND_RT_VISIBLE_DEVICES= CUDA_VISIBLE_DEVICES= TORCH_DEVICE_BACKEND_AUTOLOAD=0",
                  "export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1"]
    else:
        lines += ["export OMP_NUM_THREADS=2"]
    prefix = "taskset -c " + shlex.quote(args.cpu_affinity) + " " if args.cpu_affinity else ""
    lines += ["exec " + prefix + shlex.quote(str(args.python)) + ' "$@"']
    target.write_text("\n".join(lines) + "\n")
    target.chmod(0o755)
    if args.kind == "cpu":
        import subprocess
        # Native worker configuration/probe only; no scientific job is run.
        code = (
            "from conjecture_solver.execution_worker import Worker; import json; "
            + "worker=Worker(" + repr(str(root / "cpu-worker")) + "); "
            + "worker.configure(" + repr(dict(execution_backend="process-cooperative", capabilities=[],
                 cpus=args.cpus, memory_mb=args.memory_mb, gpu_ids=[], max_jobs=args.cpus)) + "); "
            + "print(json.dumps(worker.probe()))"
        )
        subprocess.run([str(target), "-c", code], check=True)
    print(json.dumps(dict(wrapper=str(target), scientific_jobs_started=0)))


if __name__ == "__main__":
    main()
