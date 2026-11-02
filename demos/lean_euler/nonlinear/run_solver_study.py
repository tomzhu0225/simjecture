"""Replay the active nonlinear solver foundations through the bounded local lab."""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from assemble_solver import COMPONENTS

from conjecture_solver.execution_pool import MachineRegistry
from conjecture_solver.research_service import ResearchService


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    demo = Path(__file__).resolve().parent
    repo = demo.parents[2]
    caps = out / "capabilities"
    caps.mkdir()
    cap = json.loads((repo / "capabilities/lean-4.24.0.json").read_text())
    cap["runtime_root"] = str(repo / ".runtime/lean-4.24.0")
    (caps / "lean-4.24.0.json").write_text(json.dumps(cap, indent=2) + "\n")
    registry = MachineRegistry(out / "registry")
    registry.save(
        {
            "id": "local-lean",
            "kind": "local",
            "root": str(out / "worker"),
            "python": sys.executable,
            "config": {"cpus": 1, "memory_mb": 8192, "max_jobs": 1, "capabilities": [str(caps)]},
        }
    )
    registry.prepare("local-lean")
    lab = ResearchService.create(
        out / "study",
        "Check the nonlinear Euler candidate foundations; "
        "continuum accuracy and optimality remain open.",
        capabilities=caps,
        wall_seconds=900,
        completion_policy="answer",
        allow_solver_development=True,
        execution_pool=registry.freeze(["local-lean"]),
        artifact_policy="eager",
    )
    components = [f"formal/{name}" for name in COMPONENTS]
    files = components + [
        "assemble_solver.py",
        "check_solver.py",
        "finite_volume.py",
        "validate_candidate.py",
        "contract.json",
    ]
    for name in files:
        target = lab.work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(demo / name, target)
    receipts = []

    def execute(source, argv, inputs, outputs, capability=None, timeout=180):
        job = lab.run(
            source,
            argv,
            inputs=inputs,
            outputs=outputs,
            capability=capability,
            stage="exploration",
            timeout=timeout,
            resources={"cpus": 1, "memory_mb": 8192 if capability else 2048, "gpus": 0},
        )
        deadline = time.monotonic() + timeout + 30
        while time.monotonic() < deadline:
            lab.status()
            receipt = json.loads((lab.root / "experiments" / f"{job['id']}.json").read_text())
            if receipt["status"] not in {"queued", "running"}:
                break
            time.sleep(0.5)
        else:
            lab.cancel(job["id"], reason="Optimality demonstration deadline")
            raise TimeoutError(source)
        receipts.append(receipt)
        (out / "receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")
        if receipt["status"] != "succeeded":
            raise RuntimeError(f"See {out / 'receipts.json'}")
        workspace = lab.root / "experiments" / job["id"] / "workspace"
        for name in outputs:
            target = out / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workspace / name, target)

    execute(
        "validate_candidate.py",
        ["--output", "numeric"],
        ["finite_volume.py", "contract.json"],
        ["numeric/validation.json"],
        timeout=120,
    )
    proof_outputs = ["checked/solver-formal.json"]
    proof_outputs += [
        f"checked/proof/{name}"
        for name in ["Candidate.lean", "Audit.lean", "result.json", "compile.log", "audit.log"]
    ]
    execute(
        "check_solver.py",
        ["--output", "checked"],
        ["assemble_solver.py"] + components,
        proof_outputs,
        "lean-4.24.0--at-local-lean",
        timeout=240,
    )
    result = json.loads((out / "checked/solver-formal.json").read_text())
    assert result["result"]["checked"]
    print(
        json.dumps(
            {
                "status": result["result"]["status"],
                "theorems": len(result["result"]["theorems"]),
                "jobs": [r["id"] for r in receipts],
                "scope": result["scope"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
