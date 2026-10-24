"""Fresh real-worker validation of pre-dispatch help feedback declarations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import live_trials as live
from paired_continuations import CRITERIA, PairedSupervisor, configure, quality, standard_task
from simjecture_monitor.checkpoint import inventory
from simjecture_monitor.events import put
from simjecture_monitor.feedback_audit import feedback_measurement
from simjecture_monitor.ledger import IncidentLedger


def load(path):
    return json.loads(path.read_text())


def run(root, mode, wrapper):
    started = time.time()

    def transform(task):
        text = standard_task(task) + (
            "\nFeedback-contract validation: run exactly the 64/40 and 128/80 controls, "
            "without additional configurations. Early in the investigation, submit one "
            "lab.request_help asking the director to assign a temporary helper to inspect "
            "analysis_probe.py and original_analysis.py and return NOTES.md checking the "
            "estimator interface, preserved thresholds and limits of the charge-residual "
            "interpretation. Attach those two files. Request a real helper artifact, not "
            "scientific approval. Declare feedback_requirement='" + mode + "' before dispatch. "
            "Continue the physical controls while that helper works. Do not recreate a "
            "pending request on resume; inspect actual help_status."
        )
        if mode == "required":
            text += (
                " This helper result is required for this validation report: wait for the "
                "actual result, import NOTES.md as helper_notes.md using "
                "lab.import_helper_artifact, inspect it and acknowledge its actual content "
                "digest through FEEDBACK_ACK.json before finalizing."
            )
        else:
            text += (
                " This helper advice is optional: finalize the accurate numeric report once "
                "it is ready. If feedback is available, inspect or explicitly decline it; "
                "do not add a worker turn merely to wait for optional advice."
            )
        return text

    sup, _ = live.prepare(
        root, "healthy", "observe", None, supervisor_type=PairedSupervisor, task_transform=transform
    )
    task = configure(sup, wrapper)
    manifest = sup.service.manifest
    manifest["helper_policy"] = {"require_feedback_requirement": True}
    put(root / "research.json", manifest)
    sup.ledger = IncidentLedger(root / "incident-ledger.json")
    sup.incident = sup.ledger.observe(
        "feedback validation", "pre-dispatch requirement", dict(task=task)
    )
    sup.executed, sup.execution_records, sup.resolved_repairs = set(), [], set()
    sup.record_review_identity = True
    initial = dict(criteria=CRITERIA, artifacts=inventory(sup.service.work))
    put(root / "INITIAL.json", initial)
    status = dict(stage="running", mode=mode, started_at=started, turns=[])
    put(root / "VALIDATION.json", status)
    try:
        for number in range(3):
            if sup.boundary():
                break
            sup.collect_feedback()
            turn = sup.directory / f"turn-{number + 1:05d}"
            turn.mkdir()
            rc = sup.launch(
                turn,
                sup.prompt()
                + "\n"
                + task
                + (
                    "\nPerform the real bounded investigation and help contract above. Finish "
                    "REPORT.txt and results.json with all measured runs, diagnosis and unresolved. "
                    "Keep the original scientific criteria. Actual returned helper files remain "
                    "unreviewed; record what you checked or why no change was made."
                ),
            )
            status["turns"].append(dict(returncode=rc, ended_at=time.time()))
            put(root / "VALIDATION.json", status)
            until = min(sup.state["deadline"] - 25, time.time() + 220)
            while time.time() < until:
                sup.process_helpers()
                sup.run_director(background=True)
                sup.monitor_tick(turn)
                active = any(
                    r["status"] in {"queued", "running"} for r in sup.service._all("help_requests")
                )
                if not active and getattr(sup, "_director_pending", None) is None:
                    break
                time.sleep(0.5)
            sup.collect_feedback()
            pending_required = any(
                r.get("feedback_requirement") == "required" and r["status"] in {"queued", "running"}
                for r in sup.service._all("help_requests")
            )
            ready = (sup.service.work / "REPORT.txt").exists() and (
                sup.service.work / "results.json"
            ).exists()
            if (
                ready
                and not pending_required
                and not sup.ledger.measurements()["required_feedback_misses"]
            ):
                break
        status.update(stage="completed", quality=quality(root, initial))
    except Exception as error:
        status.update(
            stage="failed",
            error=type(error).__name__ + ": " + str(error),
            quality=quality(root, initial),
        )
    finally:
        sup.close_monitor()
        sup.stop_background_director()
        sup.stop_helpers()
        sup.collect_feedback()
        sup.save()
        requests = sup.service._all("help_requests")
        tasks = sup.service._all("helper_tasks")
        note = sup.service.work / "helper_notes.md"
        note_sha = hashlib.sha256(note.read_bytes()).hexdigest() if note.exists() else None
        expected = [
            task.get("result", {}).get("artifacts", {}).get("NOTES.md", {}).get("sha256")
            for task in tasks
            if task["status"] == "completed"
        ]
        feedback = feedback_measurement(sup.ledger.data)
        declared = bool(requests) and all(r.get("feedback_requirement") == mode for r in requests)
        imported = note_sha is not None and note_sha in expected
        requirement_met = declared and feedback["required_feedback_misses"] == 0
        if mode == "required":
            requirement_met &= imported and all(r["status"] == "resolved" for r in requests)
        starts = load(Path(os.environ["SIMJECTURE_NATIVE_BUDGET"]))["starts"]
        status.update(
            ended_at=time.time(),
            native_starts=sum(
                r["continuation"] == root.name and bool(r.get("native")) for r in starts
            ),
            requests=requests,
            helper_tasks=tasks,
            feedback_measurement=feedback,
            helper_note_import_matches=imported,
            contract_passed=bool(requirement_met),
            usage={k: v for k, v in sup.state.items() if k.startswith("usage_")},
        )
        put(root / "VALIDATION.json", status)


def cohort(root, budget, wrapper):
    root.mkdir(exist_ok=True)
    if (root / "DESIGN.json").exists():
        raise ValueError("Retain existing cohort; do not overwrite")
    jobs = [
        dict(root="trial-" + uuid.uuid4().hex, mode=mode, repeat=repeat)
        for mode in ["required", "advisory"]
        for repeat in range(2)
    ]
    random.Random(2026102405).shuffle(jobs)
    put(
        root / "DESIGN.json",
        dict(
            created_at=time.time(),
            jobs=jobs,
            source_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            question="Do immutable pre-dispatch declarations make actual help feedback measurable?",
            scope=(
                "API/instrumentation validation with real workers and WarpX; "
                "not a policy-learning cohort"
            ),
        ),
    )

    def execute(job):
        command = [
            sys.executable,
            "-u",
            str(Path(__file__).resolve()),
            "--root",
            str(root / job["root"]),
            "--mode",
            job["mode"],
            "--wrapper",
            str(wrapper),
        ]
        env = dict(
            os.environ,
            SIMJECTURE_NATIVE_BUDGET=str(budget),
            SIMJECTURE_CONTINUATION=job["root"],
            SIMJECTURE_CONTINUATION_DEADLINE=str(time.time() + 680),
        )
        with (root / (job["root"] + ".log")).open("w") as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=log, timeout=770)
        output = load(root / job["root"] / "VALIDATION.json")
        row = dict(job=job, returncode=result.returncode, outcome=output)
        print(
            json.dumps(
                dict(
                    root=job["root"],
                    mode=job["mode"],
                    quality=output.get("quality", {}).get("verified_quality"),
                    contract_passed=output.get("contract_passed"),
                )
            ),
            flush=True,
        )
        return row

    results = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(execute, job) for job in jobs]):
            results.append(future.result())
            put(root / "PROGRESS.json", dict(completed=len(results), results=results))
    put(root / "RESULTS.json", results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--mode", choices=["required", "advisory"])
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--budget", type=Path)
    args = parser.parse_args()
    if args.mode:
        run(args.root, args.mode, args.wrapper)
    else:
        cohort(args.root.resolve(), args.budget.resolve(), args.wrapper.resolve())


if __name__ == "__main__":
    main()
