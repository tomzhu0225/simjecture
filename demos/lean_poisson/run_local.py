"""Execute the full Poisson proof and measurements as Simjecture lab jobs."""

import argparse
import json
import shutil
import time
from pathlib import Path

from conjecture_solver.research_service import ResearchService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    demo = Path(__file__).resolve().parent
    repo = demo.parents[1]
    config = output / "capabilities"
    config.mkdir()
    capability = json.loads((repo / "capabilities/lean-4.24.0.json").read_text())
    capability["runtime_root"] = str(repo / ".runtime/lean-4.24.0")
    (config / "lean-4.24.0.json").write_text(json.dumps(capability, indent=2))
    lab = ResearchService.create(
        output / "study",
        "Check full-solve 1D discrete Poisson correctness and scalar-work optimality.",
        capabilities=config,
        wall_seconds=600,
        completion_policy="answer",
        allow_solver_development=True,
    )
    for name in ["poisson.py", "check_proof.py", "Optimality.lean"]:
        shutil.copy2(demo / name, lab.work / name)
    jobs = [
        lab.run("poisson.py", outputs=["measurements.json"], stage="exploration", timeout=120),
        lab.run(
            "check_proof.py",
            inputs=["Optimality.lean"],
            capability="lean-4.24.0",
            outputs=[
                "proof.json",
                "proof/Candidate.lean",
                "proof/Audit.lean",
                "proof/compile.log",
                "proof/audit.log",
                "proof/result.json",
            ],
            stage="exploration",
            timeout=120,
        ),
    ]
    stop = time.monotonic() + 180
    while time.monotonic() < stop:
        receipts = [
            json.loads((lab.root / "experiments" / f"{job['id']}.json").read_text()) for job in jobs
        ]
        if all(r["status"] not in {"running", "queued"} for r in receipts):
            break
        time.sleep(0.5)
    else:
        for job in jobs:
            lab.cancel(job["id"], reason="Poisson demo deadline")
        raise TimeoutError("See experiment receipts")
    (output / "receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")
    if not all(r["status"] == "succeeded" for r in receipts):
        raise RuntimeError(f"See {output / 'receipts.json'}")
    for job, name in zip(jobs, ["measurements.json", "proof.json"], strict=True):
        shutil.copy2(lab.root / "experiments" / job["id"] / "workspace" / name, output / name)
    proof = json.loads((output / "proof.json").read_text())
    measurements = json.loads((output / "measurements.json").read_text())
    assert proof["checked"]
    ledger = {
        "workflow": (
            "Scripted Simjecture commissioning; not autonomous discovery or independent review"
        ),
        "experiments": [j["id"] for j in jobs],
        "contract": {
            "problem": "2*u_i-u_(i-1)-u_(i+1)=f_i, zero Dirichlet boundaries",
            "inputs": "arbitrary finite rational RHS, N interior unknowns",
            "output": "all N exact solution values, explicitly materialized",
            "cost": (
                "unit-cost scalar arithmetic/casts, input reads, branch inspection, output writes"
            ),
            "precomputation": "none; all per-instance work charged; no compressed or lazy output",
            "upper": "11*N+6",
            "lower": "N",
            "comparison": "at most 17 times every correct trace when N>0",
        },
        "claims": [
            {
                "claim": "Exact discrete correctness and uniqueness for all finite rational RHS",
                "status": "proved",
            },
            {
                "claim": "Theta(N) work optimality in the stated scalar trace model",
                "status": "proved",
            },
            {
                "claim": "Floating-point accuracy and timing on the sampled smooth problems",
                "status": "empirical",
            },
            {
                "claim": (
                    "Bit complexity, best hardware constant, Euler optimality, "
                    "and general PDE convergence"
                ),
                "status": "open",
            },
        ],
        "theorems": proof["theorems"],
        "exact_cases": len(measurements["exact"]["cases"]),
        "strict_backward_error_failures": [
            r["n"] for r in measurements["timings"] if not r["meets_backward_error_target"]
        ],
    }
    (output / "ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(json.dumps(ledger, indent=2))


if __name__ == "__main__":
    main()
