"""Authorized, resumable <=20-hour pilot; sealed final tests are never opened."""

from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .collect import sft_samples
from .gateway import ScienceGateway
from .network import model_network
from .pipeline import Pipeline, rows
from .remote_control import Remote
from .storage import read_json, write_json


class Pilot:
    def __init__(self, root):
        self.root = Path(root)
        self.cfg = read_json(self.root / "config/pipeline.local.json")
        self.plan = read_json(self.root / "pilot/plan.json")
        if not self.plan.get("user_authorized"):
            raise PermissionError("The 20-hour pilot requires the explicit user instruction")
        self.deadline = self.plan["deadline_epoch"]
        self.pipeline = Pipeline(self.root, self.cfg)
        self.state_path = self.root / "pilot/status.json"
        self.state = read_json(self.state_path, dict(started_at=time.time(), phase="starting"))
        self.state.update(deadline_epoch=self.deadline, final_test_opened=False)

    def save(self, phase, **fields):
        self.state.update(phase=phase, updated_at=time.time(), **fields)
        write_json(self.state_path, self.state)

    def time_left(self):
        return self.deadline - time.time()

    def batch(self, jobs, adapter=None):
        if not jobs:
            return []
        arm = jobs[0]["arm"]
        if len({j["arm"] for j in jobs}) != 1:
            raise ValueError("Pilot batches keep one pinned arm throughout simultaneous studies")
        # A provider-quota recovery can resume at independent review, after all
        # studies have closed. Do not reload two NPU actors just to read those
        # immutable records; the pending optimizer handoff needs them stopped.
        needs_actor = any(
            not (Path(self.cfg["case_store"]) / "runs" / job["job_id"] / "phase_conclusion.json").exists()
            for job in jobs
        )
        if needs_actor:
            for slot in range(min(2, len(jobs))):
                self.pipeline.ensure_policy(slot, arm, adapter)

        def work(index):
            existing = Path(self.cfg["case_store"]) / "runs" / jobs[index]["job_id"] / "phase_conclusion.json"
            if not existing.exists() and self.time_left() < self.plan["study_seconds"] + 900:
                raise TimeoutError("Global pilot deadline: no new complete study can be admitted")
            return self.pipeline.study(jobs[index], slot=index % 2, adapter=adapter, assess=False)

        with ThreadPoolExecutor(max_workers=4) as pool:
            cases = list(pool.map(work, range(len(jobs))))
        for slot in range(2):
            self.pipeline.stop_policy(slot)

        def assess(index):
            case = Path(cases[index]["case"])
            return self.pipeline.assess(case, self.pipeline.tasks[jobs[index]["task_id"]], slot=index % 2)

        with ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(assess, range(len(jobs))))

    def teachers(self):
        existing = rows(self.root / "plans/teacher_collection.jsonl")
        by_id = {r["job_id"]: r for r in existing}
        # Interleave four mechanisms across the first wave, then independent
        # teacher attempts. The exact original collection IDs are reused later.
        jobs = [
            dict(by_id[f"{task}-teacher-{trial}"], arm="teacher", pilot=True)
            for trial in range(1, 4)
            for task in self.plan["training_task_ids"]
        ]
        self.save("teacher_collection", teacher_jobs=[j["job_id"] for j in jobs])
        results = self.batch(jobs)
        samples = []
        accepted = []
        for row in results:
            if row["review"]["accepted_for_training"]:
                try:
                    samples.extend(sft_samples(row["record"], row["task"], row["review"], row["review_path"]))
                    accepted.append(row["record"]["study_id"])
                except ValueError as error:
                    self.state.setdefault("collection_warnings", []).append(str(error))
        if not samples:
            raise RuntimeError(
                "No quality-reviewed executed teacher decision; no synthetic replacement is permitted"
            )
        write_json(
            self.root / "pilot/teacher-index.json",
            dict(
                trajectories=len(results),
                accepted_trajectories=accepted,
                decision_count=len(samples),
                cases=[r["case"] for r in results],
            ),
            immutable=True,
        )
        self.pipeline.remote.call("write_jsonl", path="data/pilot/sft.jsonl", values=samples)
        output = self.root / "data/pilot/sft.jsonl"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples), encoding="utf-8"
        )
        self.save(
            "teacher_collection_complete",
            teacher_trajectories=len(results),
            accepted_teacher_trajectories=len(accepted),
            teacher_decisions=len(samples),
        )
        return results

    def wait_engineering(self):
        self.save("awaiting_verified_training_handoff")
        while not (self.root / "pilot/progression-ready.json").exists():
            if self.time_left() < 5 * 3600:
                raise TimeoutError("Insufficient pilot time for the remaining phases")
            time.sleep(5)

    def run(self):
        if not (self.root / "pilot/teacher-index.json").exists():
            self.teachers()
        self.wait_engineering()
        # The next stages are written into a separate module before the
        # progression flag is published. Existing studies remain independent
        # of preparation code edits and their wall clocks never reset.
        from .pilot_training import continue_pilot

        return continue_pilot(self)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    pilot = Pilot(args.root)
    socket_path = Path(read_json(args.root / "config/isolation.local.json")["transport_socket"])
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        raise RuntimeError("Inspect the existing pilot controller before starting another")
    cpu = Remote(dict(pilot.cfg, ssh_route=str(args.root / "config/ssh-cpu-route.local.json")))
    extra = {"cannlab-cpu": (cpu.route, cpu.root)}
    with (
        model_network(read_json(args.root / "config/isolation.local.json")["network_proxy"]),
        ScienceGateway(
            socket_path, pilot.pipeline.remote.route, pilot.pipeline.remote.root, extra
        ) as gateway,
    ):
        socket_path.chmod(0o600)
        thread = threading.Thread(target=gateway.serve_forever, daemon=True)
        thread.start()
        try:
            print(json.dumps(pilot.run(), ensure_ascii=False), flush=True)
        except Exception as error:
            pilot.save("needs_resume", error=repr(error))
            raise
        finally:
            gateway.shutdown()
            socket_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
