"""Run the first 3D optimization experiment through Simjecture's local lab."""

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
    service = ResearchService.create(
        output / "study",
        "Test old-state thermodynamic reuse in a fixed 3D Euler update.",
        wall_seconds=600,
        completion_policy="answer",
        allow_solver_development=True,
    )
    shutil.copy2(demo / "experiment.py", service.work / "experiment.py")
    shutil.copy2(demo.parent / "euler.py", service.work / "euler.py")
    job = service.run(
        "experiment.py",
        inputs=["euler.py"],
        outputs=["optimization.json"],
        stage="exploration",
        timeout=240,
    )
    stop = time.monotonic() + 300
    while time.monotonic() < stop:
        receipt = json.loads((service.root / "experiments" / f"{job['id']}.json").read_text())
        if receipt["status"] not in {"queued", "running"}:
            break
        time.sleep(0.5)
    else:
        service.cancel(job["id"], reason="3D optimization stage deadline")
        raise TimeoutError("See experiment receipt")
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if receipt["status"] != "succeeded":
        raise RuntimeError(f"See {output / 'receipt.json'}")
    shutil.copy2(
        service.root / "experiments" / job["id"] / "workspace/optimization.json",
        output / "optimization.json",
    )
    result = json.loads((output / "optimization.json").read_text())
    print(
        json.dumps(
            {
                "experiment": job["id"],
                "checks": result["equivalence_checks"],
                "speed_ratios": [[r["n"], r["reference_over_cached"]] for r in result["timings"]],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
