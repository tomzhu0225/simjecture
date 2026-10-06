"""Qualify native examples through the hosted experiment launcher, as its user."""

import argparse
import json
import time
from pathlib import Path

from conjecture_solver.public.store import Store
from conjecture_solver.public.worker import run_native_case
from conjecture_solver.research_service import ResearchService

TOOLS = Path("/opt/simjecture-public/tools")
ROOT = Path("/srv/simjecture-public/qualification-20261006")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Recheck one installed example, preserving other receipts")
    args = parser.parse_args()
    ROOT.mkdir(exist_ok=True, mode=0o700)
    candidate = json.loads((TOOLS / "registry.json").read_text())
    for entry in candidate["tools"]:
        entry["qualified"] = True  # Private commissioning registry, never public admission.
    (ROOT / "candidates.json").write_text(json.dumps(candidate, indent=2))
    (ROOT / "settings.json").write_text(
        json.dumps(
            {
                "tools_registry": str(ROOT / "candidates.json"),
                "experiments_per_job": 10,
            }
        )
    )
    store = Store(ROOT)
    _, visitor = store.create_visitor("operator-native-qualification")
    report_path = ROOT / "qualification.json"
    reports = json.loads(report_path.read_text()) if args.only and report_path.exists() else []
    if args.only:
        reports = [row for row in reports if row["id"] != args.only]
    for entry in candidate["tools"]:
        if args.only and entry["id"] != args.only:
            continue
        job = store.enqueue(
            visitor["id"],
            "reproduce",
            "Numerical qualification: " + entry["name"],
            privileged=True,
            wall_seconds=180,
            limits={"interactive": None, "research": None},
        )
        store.claim(max_active=1)
        service = ResearchService.create(
            ROOT / "jobs" / job["id"] / "study",
            job["hypothesis"],
            wall_seconds=180,
            execution_backend="process-cooperative",
            completion_policy="answer",
        )
        service.freeze_protocol(
            "Operator readiness case, executed through the public launcher. "
            "Not independent approval of a physical conjecture."
        )
        print("Qualifying", entry["id"], flush=True)
        try:
            result = run_native_case(store, job["id"], service, entry["id"], {})
            if result["status"] != "succeeded":
                raise RuntimeError(result)
            workspace = service.root / "experiments" / result["experiment"] / "workspace"
            log = (workspace / "native.log").read_text()
            gpu = "CUDA initialized" in log if entry["family"] == "warpx" else None
            if entry["family"] == "warpx" and not gpu:
                raise RuntimeError("The native startup did not confirm CUDA initialization")
            reports.append(
                {
                    "id": entry["id"],
                    "passed": True,
                    "job": job["id"],
                    "experiment": result["experiment"],
                    "seconds": result["execution_seconds"],
                    "metrics": result["metrics"],
                    "cuda_initialized": gpu,
                }
            )
            print("PASS", entry["id"], result["execution_seconds"], flush=True)
        except Exception as error:
            reports.append(
                {"id": entry["id"], "passed": False, "job": job["id"], "error": str(error)}
            )
            print("FAIL", entry["id"], str(error), flush=True)
        finally:
            service.cancel_active()
            store.update(job["id"], status="completed", finished=time.time())
        (ROOT / "qualification.json").write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
