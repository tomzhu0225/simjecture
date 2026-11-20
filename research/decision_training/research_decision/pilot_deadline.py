"""Enforce the user-authorized 20-hour boundary using only project-owned jobs."""

import time
from pathlib import Path

from .storage import read_json, write_json


def main():
    root = Path(__file__).resolve().parents[1]
    plan = read_json(root / "pilot/plan.json")
    if not plan.get("user_authorized"):
        raise PermissionError("No pilot authorization")
    cutoff = plan["deadline_epoch"] - 60
    while time.time() < cutoff:
        status = read_json(root / "pilot/status.json", {})
        if status.get("phase") == "complete":
            return
        time.sleep(min(30, cutoff - time.time()))
    from concurrent.futures import ThreadPoolExecutor

    from conjecture_solver.research_service import ResearchService
    from conjecture_solver.study_launch import control_native

    from .case import closeout
    from .processes import manage
    from .remote_control import Remote

    cfg = read_json(root / "config/pipeline.local.json")
    # Stop admission before closing studies; otherwise a quota-waiting
    # controller could wake and overwrite this final boundary or launch an
    # inference service after its budget expired.
    manage(root, "pilot-controller", "stop")
    manage(root, "autonomous-controller", "stop")
    cases = []
    for case in (Path(cfg["case_store"]) / "runs").iterdir():
        run = read_json(case / "study-run.json", {})
        if run.get("pilot") or (
            run.get("verification_only") and "pilot" in run.get("original_scientific_case", "")
        ):
            cases.append(case)
            if not run.get("autonomous_student"):
                try:
                    control_native(case, "cancel")
                except (ValueError, FileNotFoundError):
                    pass

    def settle(case):
        service = ResearchService(case)
        service.cancel_active()
        if not (case / "phase_conclusion.json").exists():
            try:
                closeout(case, "global_20_hour_pilot_budget")
            except ValueError:
                pass

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(settle, cases))
    remote = Remote(cfg)
    for name in ["policy-0", "policy-1", "pilot-trainer", "autonomous-trainer"]:
        remote.process(name, "stop")
    status = read_json(root / "pilot/status.json", {})
    status.update(
        phase="deadline_reached",
        ended_at=time.time(),
        all_scientific_records_retained=True,
        unreviewed_cases_remain_in_evaluation=True,
        final_test_opened=False,
    )
    write_json(root / "pilot/status.json", status)
    write_json(
        root / "pilot/deadline-closeout.json",
        dict(
            cases=[str(c) for c in cases],
            deadline_epoch=plan["deadline_epoch"],
            closed_at=time.time(),
            no_unvalidated_discovery_claims=True,
        ),
    )


if __name__ == "__main__":
    main()
