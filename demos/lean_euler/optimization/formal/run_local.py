"""Run formal stage 2 and empirical correspondence checks in Simjecture."""

import argparse
import json
import shutil
import time
from pathlib import Path

from conjecture_solver.research_service import ResearchService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    formal = Path(__file__).resolve().parent
    optimization = formal.parent
    repo = optimization.parents[2]
    config = out / "capabilities"
    config.mkdir()
    cap = json.loads((repo / "capabilities/lean-4.24.0.json").read_text())
    cap["runtime_root"] = str(repo / ".runtime/lean-4.24.0")
    (config / "lean-4.24.0.json").write_text(json.dumps(cap, indent=2))
    lab = ResearchService.create(
        out / "study",
        "Prove exact Euler cache equivalence and restricted schedule optimality.",
        capabilities=config,
        wall_seconds=600,
        completion_policy="answer",
        allow_solver_development=True,
    )
    for name in ["EulerCache.lean", "CacheSchedule.lean", "check_formal.py", "instrument.py"]:
        shutil.copy2(formal / name, lab.work / name)
    shutil.copy2(optimization / "experiment.py", lab.work / "experiment.py")
    shutil.copy2(optimization.parent / "euler.py", lab.work / "euler.py")
    outputs = ["formal-results.json"]
    for stem in ["EulerCache", "CacheSchedule"]:
        outputs.extend(
            f"{stem}/{name}"
            for name in ["result.json", "Candidate.lean", "Audit.lean", "compile.log", "audit.log"]
        )
    jobs = [
        lab.run(
            "check_formal.py",
            inputs=["EulerCache.lean", "CacheSchedule.lean"],
            capability="lean-4.24.0",
            outputs=outputs,
            stage="exploration",
            timeout=240,
        ),
        lab.run(
            "instrument.py",
            inputs=["euler.py", "experiment.py"],
            outputs=["instrumentation.json"],
            stage="exploration",
            timeout=120,
        ),
    ]
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        receipts = [
            json.loads((lab.root / "experiments" / f"{j['id']}.json").read_text()) for j in jobs
        ]
        if all(r["status"] not in {"queued", "running"} for r in receipts):
            break
        time.sleep(0.5)
    else:
        for job in jobs:
            lab.cancel(job["id"], reason="Formal Euler stage deadline")
        raise TimeoutError("See lab receipts")
    (out / "receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")
    if not all(r["status"] == "succeeded" for r in receipts):
        raise RuntimeError(f"See {out / 'receipts.json'}")
    for job, name in zip(jobs, ["formal-results.json", "instrumentation.json"], strict=True):
        shutil.copy2(lab.root / "experiments" / job["id"] / "workspace" / name, out / name)
    proofs = json.loads((out / "formal-results.json").read_text())
    assert all(p["checked"] for p in proofs.values())
    ledger = {
        "stage": "2: exact-arithmetic equivalence and restricted caching-schedule optimum",
        "experiments": [j["id"] for j in jobs],
        "formal_theorems": [n for p in proofs.values() for n in p["theorems"]],
        "claims": {
            "exact_real_cached_step_and_iterates_equal_reference": "proved",
            "conservation_of_all_five_components": "proved",
            "cold_cache_thermodynamic_eval_lower_bound_N": "proved",
            "cached_N_vs_reference_3N_evaluations": "proved",
            "minimal_weighted_library_cost_for_complete_single_pass_schedules": "proved",
            "numpy_correspondence_and_call_counts": "empirical",
            "wall_clock_speed_advantage": "stage-1 empirical record, not a formal consequence",
            "verified_floating_point_refinement": "open",
            "general_Euler_time_to_accuracy_optimality": "open",
        },
        "algorithm_class": (
            "Immutable old state, cold cache, Eval/Use/Drop commands; only Eval creates "
            "thermodynamic data; every cell/direction is used; weighted comparison has "
            "exactly 3N Uses; no algebraic bypass, cross-cell sharing, warm start, "
            "or changed flux/time integrator"
        ),
        "cost": (
            "Eval=t, Use=f, Drop=d, nonnegative integer weights: cached=(t+3f)N; "
            "reference=(3t+3f)N; saving=2tN. This is a library cost model, "
            "not a measured hardware model."
        ),
        "scope": (
            "Scripted assistant-authored formalization; no autonomous discovery "
            "or independent scientific review"
        ),
    }
    (out / "ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(json.dumps(ledger, indent=2))


if __name__ == "__main__":
    main()
