"""Create a fresh operator-selected pilot plan; does not launch an experiment."""

import argparse
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial", required=True, help="Absolute SFT checkpoint path on the NPU host")
    parser.add_argument("--total-hours", type=float, default=20)
    parser.add_argument("--rl-hours", type=float, default=2.5)
    parser.add_argument("--study-seconds", type=int, default=900)
    parser.add_argument("--with-comparison", action="store_true", help="After training, run the GPT-led four-arm pilot comparison")
    args = parser.parse_args()
    if not 0 < args.total_hours <= 20 or not 0 < args.rl_hours < args.total_hours or args.study_seconds <= 30:
        parser.error("Choose positive research budgets within the bounded 20-hour pilot")
    if args.total_hours * 3600 <= args.study_seconds + 900:
        parser.error("The total budget cannot admit one complete research group and an update reserve")
    root = Path(__file__).resolve().parents[1]
    pilot = root / "pilot"
    pilot.mkdir(exist_ok=True)
    if (pilot / "plan.json").exists() or (pilot / "autonomous-plan.json").exists():
        raise FileExistsError("Use the existing plan for resume; do not reset its clock")
    start = time.time()
    plan = dict(
        user_authorized=True, authorization="Explicit operator invocation of tools/init_pilot.py",
        start_epoch=start, deadline_epoch=start + args.total_hours * 3600,
        study_seconds=1800, training_task_ids=["T01-L1"], development_task_ids=["D02-L1"],
        development_arms=["simjecture", "simjecture_sftrl9b", "simjecture_sft9b", "simjecture_raw9b"],
        final_tests_remain_sealed=True,
    )
    autonomous = dict(
        user_authorized=True, training_task_ids=["T01-L1"], study_seconds=args.study_seconds,
        RL_wall_window_hours=args.rl_hours, group_size=4, max_updates=None,
        teacher_checkpoint=args.initial, inbox="data/pilot-autonomous/rloo-inbox",
        output="checkpoints/pilot-autonomous-rloo", post_training_comparison=args.with_comparison,
        scope="One smooth 1D plasma mechanism; independent final C/D assessment is separate",
        final_test_opened=False,
    )
    for name, value in [("plan.json", plan), ("autonomous-plan.json", autonomous)]:
        (pilot / name).write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(dict(configured=True, experiments_started=0, deadline_epoch=plan["deadline_epoch"])))


if __name__ == "__main__":
    main()
