"""Reproduce the staged local example through Simjecture's real lab executor."""

import argparse
import json
import shutil
import time
from pathlib import Path

from conjecture_solver.research_service import ResearchService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New artifact directory")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    demo = Path(__file__).resolve().parent
    repo = demo.parents[1]
    capability = json.loads((repo / "capabilities/lean-4.24.0.json").read_text())
    capability["runtime_root"] = str(repo / ".runtime/lean-4.24.0")
    config = output / "capabilities"
    config.mkdir()
    (config / "lean-4.24.0.json").write_text(json.dumps(capability, indent=2))
    service = ResearchService.create(
        output / "study",
        "Explore exact periodic finite-volume conservation and unrestricted Euler positivity.",
        capabilities=config,
        wall_seconds=600,
        completion_policy="answer",
        allow_solver_development=True,
    )
    for path in demo.iterdir():
        if path.suffix in {".lean", ".py"} and path.name != "run_local.py":
            shutil.copy2(path, service.work / path.name)
    proof_outputs = ["proofs.json"]
    for name in ["Decay", "Conservation", "Witness"]:
        proof_outputs += [
            f"{name}/{file}"
            for file in ["result.json", "Candidate.lean", "Audit.lean", "compile.log", "audit.log"]
        ]
    jobs = [
        service.run("euler.py", outputs=["numerics.json"], stage="exploration", timeout=120),
        service.run(
            "check_proofs.py",
            inputs=["Decay.lean", "Conservation.lean", "Witness.lean"],
            outputs=proof_outputs,
            capability="lean-4.24.0",
            stage="exploration",
            timeout=180,
        ),
    ]
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        receipts = [
            json.loads((service.root / "experiments" / f"{j['id']}.json").read_text()) for j in jobs
        ]
        if all(r["status"] not in {"queued", "running"} for r in receipts):
            break
        time.sleep(0.5)
    else:
        for j in jobs:
            service.cancel(j["id"], reason="Local demonstration deadline")
        raise TimeoutError("Local demonstration exceeded 240 seconds")
    (output / "receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")
    if not all(r["status"] == "succeeded" for r in receipts):
        raise RuntimeError(f"See experiment receipts in {output}")
    numeric_path = service.root / "experiments" / jobs[0]["id"] / "workspace/numerics.json"
    proof_path = service.root / "experiments" / jobs[1]["id"] / "workspace/proofs.json"
    numerics = json.loads(numeric_path.read_text())
    proofs = json.loads(proof_path.read_text())
    assert all(result["checked"] for result in proofs.values())
    ledger = {
        "workflow": (
            "Scripted commissioning example executed through Simjecture; "
            "no autonomous discovery claim"
        ),
        "experiments": [j["id"] for j in jobs],
        "proofs": proofs,
        "numerics": numerics,
        "claims": [
            {
                "claim": "Scalar decay Euler step preserves nonnegativity when y >= 0 and h <= 1",
                "status": "proved",
                "evidence": "Decay.nonnegative",
            },
            {
                "claim": (
                    "Uniform-volume periodic shared-flux update conserves each component "
                    "over any finite cell type"
                ),
                "status": "proved",
                "evidence": "FiniteVolume.conservation / conservation3D",
            },
            {
                "claim": (
                    "Rusanov compressible Euler preserves positive density "
                    "for every positive time step"
                ),
                "status": "falsified",
                "evidence": "Exact rational search and EulerWitness.negative_density",
            },
            {
                "claim": "Smooth periodic 3D contact wave error decreases on the tested grids",
                "status": "empirically_supported",
                "evidence": jobs[0]["id"],
            },
            {
                "claim": "General Euler positivity under an appropriate CFL condition",
                "status": "open",
            },
            {
                "claim": (
                    "PDE convergence, verified floating-point refinement, and solver optimality"
                ),
                "status": "open",
            },
        ],
        "review": (
            "Exploration receipts only; no independent scientific review "
            "or accepted campaign conclusion"
        ),
    }
    (output / "ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "experiments": ledger["experiments"],
                "claims": ledger["claims"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
