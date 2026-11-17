"""Restore closed partial reports from their original evidence, without resetting any clock."""

import time
from pathlib import Path

from research_decision.case import closeout
from research_decision.processes import manage
from research_decision.storage import read_json, write_json

root = Path(__file__).resolve().parents[1]
hold = read_json(root / "pilot/quota-hold.json")
if time.time() < hold["resume_after_epoch"]:
    raise RuntimeError("The requested five-hour recovery interval has not elapsed")
cfg = read_json(root / "config/pipeline.local.json")
for case in (Path(cfg["case_store"]) / "runs").glob("*teacher-*"):
    if (case / "phase_conclusion.json").exists():
        old = read_json(case / "phase_conclusion.json")
        closeout(case, old["termination_reason"])
write_json(
    root / "pilot/quota-hold-completed.json",
    dict(
        resumed_at=time.time(),
        original_hit_epoch=hold["quota_first_observed_epoch"],
        waited_seconds=time.time() - hold["quota_first_observed_epoch"],
        task_deadlines_reset=False,
        final_test_opened=False,
    ),
)
print(
    manage(
        root,
        "pilot-controller",
        "start",
        [str(root / "bin/controller-python"), "-m", "research_decision.pilot"],
    )
)
