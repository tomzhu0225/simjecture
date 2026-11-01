"""Reproduce the frozen accuracy sweep, reference audits, and conditional proofs."""

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
    demo = Path(__file__).resolve().parent
    repo = demo.parents[2]
    caps = out / "capabilities"
    caps.mkdir()
    cap = json.loads((repo / "capabilities/lean-4.24.0.json").read_text())
    cap["runtime_root"] = str(repo / ".runtime/lean-4.24.0")
    (caps / "lean-4.24.0.json").write_text(json.dumps(cap, indent=2))
    lab = ResearchService.create(
        out / "study",
        "Measure and audit total work at prescribed 3D Euler solution error.",
        capabilities=caps,
        wall_seconds=1800,
        completion_policy="answer",
        allow_solver_development=True,
    )
    for name in [
        "study.py",
        "contract.json",
        "validate.py",
        "representation.py",
        "check_formal.py",
        "ContactReference.lean",
        "WaveDerivative.lean",
        "ErrorWork.lean",
    ]:
        shutil.copy2(demo / name, lab.work / name)
    shutil.copy2(demo.parent / "euler.py", lab.work / "euler.py")
    shutil.copy2(demo.parent / "optimization/experiment.py", lab.work / "experiment.py")
    receipts = []

    def execute(source, inputs, outputs, *, capability=None, timeout=120):
        job = lab.run(
            source,
            inputs=inputs,
            outputs=outputs,
            capability=capability,
            stage="exploration",
            timeout=timeout,
        )
        stop = time.monotonic() + timeout + 30
        while time.monotonic() < stop:
            receipt = json.loads((lab.root / "experiments" / f"{job['id']}.json").read_text())
            if receipt["status"] not in {"running", "queued"}:
                break
            time.sleep(0.5)
        else:
            lab.cancel(job["id"], reason="Accuracy study job deadline")
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
        return receipt

    # Keep proof/validation workloads away from the primary timing sweep.
    execute(
        "study.py", ["contract.json", "euler.py", "experiment.py"], ["accuracy.json"], timeout=1200
    )
    execute("validate.py", ["study.py", "euler.py", "experiment.py"], ["validation.json"])
    execute(
        "representation.py",
        ["study.py", "euler.py", "experiment.py"],
        ["representation.json"],
        timeout=240,
    )
    outputs = ["formal-results.json"]
    for stem in ["ContactReference", "WaveDerivative", "ErrorWork"]:
        outputs += [
            f"{stem}/{name}"
            for name in ["result.json", "Candidate.lean", "Audit.lean", "compile.log", "audit.log"]
        ]
    execute(
        "check_formal.py",
        ["ContactReference.lean", "WaveDerivative.lean", "ErrorWork.lean"],
        outputs,
        capability="lean-4.24.0",
        timeout=300,
    )
    result = json.loads((out / "accuracy.json").read_text())
    proof = json.loads((out / "formal-results.json").read_text())
    assert all(r["checked"] for r in proof.values())
    assert all(
        abs(row["final_time"] - result["contract"]["final_time"]) < 1e-12 for row in result["rows"]
    )
    ledger = dict(
        experiments=[r["id"] for r in receipts],
        scope=(
            "Empirical matched-error Euler work frontier plus checked reference "
            "and conditional budget lemmas"
        ),
        claims=dict(
            reference_algebra_and_affine_sine_derivative="proved",
            error_accumulation_and_work_conversion="proved under explicit hypotheses",
            hypotheses_discharged_for_nonlinear_solvers="open",
            measured_cell_average_error_targets="empirically attained in finite catalogue",
            reconstructed_density_error="numerical quadrature audit, not certified",
            global_optimality_at_fixed_physical_error="open",
        ),
        calibration=dict(
            solver_seconds=sum(r["solver_seconds"] for r in result["rows"]),
            analysis_seconds=sum(r["analysis_seconds"] for r in result["rows"]),
            cell_stage_updates=sum(r["cell_stage_updates"] for r in result["rows"]),
            eos_cell_evaluations=sum(r["eos_cell_evaluations"] for r in result["rows"]),
            primary_job_wall_seconds=receipts[0]["execution"]["wall_seconds"],
        ),
    )
    (out / "ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(json.dumps(ledger, indent=2))


if __name__ == "__main__":
    main()
