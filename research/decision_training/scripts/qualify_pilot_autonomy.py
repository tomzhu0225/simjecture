"""Regression checks for quota recovery and a pending update past admission close.

Uses fake process/inbox objects only. Never invokes GPT, NPUs or a simulator.
"""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_decision import pilot_training
from research_decision.pilot import Pilot
from research_decision.storage import write_json


def pending_update_is_not_discarded():
    class Remote:
        def __init__(self):
            self.running = True
            self.group = False
            self.actors_stopped = False
            self.committed = False
            self.request_reads_after_handoff = 0
            self.events = []

        def process(self, name, operation, *args, **kwargs):
            if operation != "status":
                raise AssertionError("The running trainer must not restart")
            return {"active": self.running, "record": {"argv": ["rloo"]}}

        def read(self, path):
            if path.endswith("stop.json"):
                return None
            assert path.endswith("rollout-request.json")
            if self.actors_stopped and not self.committed:
                self.request_reads_after_handoff += 1
                if self.request_reads_after_handoff >= 3:
                    self.committed = True
                    self.events.append("optimizer_checkpoint_committed")
            return dict(
                policy_path="rl-new" if self.committed else "sft-old",
                completed_updates=int(self.committed),
                request_id="rollout-000001" if self.committed else "rollout-000000",
            )

        def write(self, path, value, **kwargs):
            if path.endswith("group-000001.json"):
                self.group = True
                self.events.append("reviewed_group_published")
            elif path.endswith("actors-stopped.json"):
                assert self.group
                self.actors_stopped = True
            elif path.endswith("stop.json"):
                assert self.committed, "An expired admission window discarded the pending RLOO group"
                assert value["checkpoint"] == "rl-new"
                self.events.append("admission_closed")
                self.running = False
            else:
                raise AssertionError(path)

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        # Window expired during a genuine quota pause, but all four studies
        # already exist. Their immutable reviewed group still needs an update.
        pending = root / "cases/runs/T01-L1-pilot-rl-000001-0"
        pending.mkdir(parents=True)
        remote = Remote()
        pipeline = SimpleNamespace(remote=remote, stop_policy=lambda slot: None)
        pilot = SimpleNamespace(
            root=root,
            cfg={"case_store": str(root / "cases")},
            state={"RL_window_deadline": 900},
            plan={"training_task_ids": ["T01-L1"], "study_seconds": 1800},
            deadline=20000,
            pipeline=pipeline,
            save=lambda *args, **kwargs: None,
            time_left=lambda: 19000,
            batch=lambda *args, **kwargs: [
                {"record": {}, "task": {}, "review": {}, "case": f"case-{i}"} for i in range(4)
            ],
        )
        with (
            patch.object(pilot_training.time, "time", return_value=1000),
            patch.object(pilot_training.time, "sleep"),
            patch.object(pilot_training, "rl_trajectory", return_value={}),
            patch.object(pilot_training, "validate_group"),
        ):
            assert pilot_training.online_window(pilot, "sft-old") == "rl-new"
        assert remote.events == [
            "reviewed_group_published", "optimizer_checkpoint_committed", "admission_closed"
        ]


def closed_studies_do_not_start_actors():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        jobs = []
        for i in range(4):
            job = dict(job_id=f"closed-{i}", task_id="T01-L1", arm="simjecture_sftrl9b")
            write_json(root / "runs" / job["job_id"] / "phase_conclusion.json", {})
            jobs.append(job)

        def unexpected(*args, **kwargs):
            raise AssertionError("Closed quota-held studies reloaded an unnecessary NPU actor")

        pilot = Pilot.__new__(Pilot)
        pilot.cfg = {"case_store": str(root)}
        pilot.plan = {"study_seconds": 1800}
        pilot.pipeline = SimpleNamespace(
            ensure_policy=unexpected,
            stop_policy=lambda slot: None,
            study=lambda job, **kwargs: {"case": str(root / "runs" / job["job_id"])},
            assess=lambda case, task, **kwargs: {"case": str(case)},
            tasks={"T01-L1": {}},
        )
        assert len(pilot.batch(jobs, adapter="frozen-adapter")) == 4


def restart_respects_quota_hold():
    pilot = SimpleNamespace(
        state={"quota_resume_epoch": 1001},
        deadline=2000,
        save=lambda *args, **kwargs: None,
    )
    calls = []
    times = iter([1000, 1000, 1000, 1000, 1002, 1002])
    with (
        patch.object(pilot_training.time, "time", side_effect=lambda: next(times)),
        patch.object(pilot_training.time, "sleep", side_effect=calls.append),
    ):
        pilot_training.wait_quota_recovery(pilot, 1001)
    assert calls == [1]
    assert "quota_resume_epoch" not in pilot.state


if __name__ == "__main__":
    pending_update_is_not_discarded()
    closed_studies_do_not_start_actors()
    restart_respects_quota_hold()
    print(json.dumps(dict(passed=3, model_calls=0, optimizer_steps=0, simulations=0)))
