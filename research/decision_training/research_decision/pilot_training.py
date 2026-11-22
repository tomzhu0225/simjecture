"""Post-teacher pilot stages, resumed from actual receipts and immutable checkpoints."""

import time
from pathlib import Path

from .collect import rl_trajectory
from .rloo import validate_group
from .storage import read_json, write_json


def launch_trainer(pilot, stage, initial=None, resume=None):
    remote = pilot.pipeline.remote
    root = pilot.cfg["remote_root"]
    output = root + ("/checkpoints/pilot-sft" if stage == "sft" else "/checkpoints/pilot-rloo")
    data = root + ("/data/pilot/sft.eligible.jsonl" if stage == "sft" else "/data/pilot/rloo-inbox")
    argv = [
        root + "/resources/training-python",
        "-m",
        "torch.distributed.run",
        "--nproc-per-node=2",
        "--master-port=29617",
        "-m",
        "research_decision.train_adapter",
        stage,
        "--base",
        root + "/models/Qwen3.5-9B",
        "--config",
        root + "/config/pilot-training.json",
        "--data",
        data,
        "--output",
        output,
    ]
    if initial:
        argv += ["--initial", initial]
    if resume:
        argv += ["--resume", resume]
    for slot in range(2):
        pilot.pipeline.stop_policy(slot)
    return remote.process(
        "pilot-trainer", "start", argv, dict(PYTHONPATH=root, OMP_NUM_THREADS="2", HCCL_CONNECT_TIMEOUT="300")
    )


def wait_sft(pilot):
    remote = pilot.pipeline.remote
    path = "checkpoints/pilot-sft/sft-epoch-2"
    if remote.read(path + "/manifest.json"):
        pilot.save(
            "SFT_complete",
            sft_checkpoint=pilot.cfg["remote_root"] + "/" + path,
            sft_state=remote.read(path + "/state.json"),
        )
        return pilot.cfg["remote_root"] + "/" + path
    pilot.save("SFT_running")
    previous = "checkpoints/pilot-sft/sft-epoch-1"
    resume = pilot.cfg["remote_root"] + "/" + previous if remote.read(previous + "/manifest.json") else None
    if not remote.process("pilot-trainer", "status")["active"]:
        launch_trainer(pilot, "sft", resume=resume)
    while remote.process("pilot-trainer", "status")["active"]:
        if pilot.time_left() < 8 * 3600:
            remote.process("pilot-trainer", "stop")
            raise TimeoutError(
                "Keep six hours for RL/evaluation and final report; interrupted SFT state retained"
            )
        time.sleep(10)
    if not remote.read(path + "/manifest.json"):
        raise RuntimeError("SFT exited before a complete verified checkpoint; inspect the owned trainer log")
    state = remote.read(path + "/state.json")
    pilot.save("SFT_complete", sft_checkpoint=pilot.cfg["remote_root"] + "/" + path, sft_state=state)
    return pilot.cfg["remote_root"] + "/" + path


def online_window(pilot, sft):
    remote = pilot.pipeline.remote
    inbox = "data/pilot/rloo-inbox"
    # This is a wall-time pause for the finite pilot, never the full experiment's
    # convergence stopping rule or a fixed maximum number of RL updates.
    stop_at = pilot.state.get("RL_window_deadline") or min(time.time() + 2 * 3600, pilot.deadline - 5 * 3600)
    pilot.save("online_RLOO_running", RL_window_deadline=stop_at)
    if remote.read(inbox + "/stop.json"):
        # An already-completed pilot is immutable; resume the full project in a
        # separate inbox with the saved optimizer/RNG/group-consumption ledger.
        return remote.read(inbox + "/stop.json").get("checkpoint") or pilot.state.get("rl_checkpoint", sft)
    trainer = remote.process("pilot-trainer", "status")
    if trainer["active"]:
        if "rloo" not in trainer["record"]["argv"]:
            raise RuntimeError("An active pilot trainer is not the expected RLOO stage")
    else:
        previous = remote.read(inbox + "/rollout-request.json") or {}
        previous_policy = previous.get("policy_path")
        resume = previous_policy if previous_policy and previous_policy != sft else None
        launch_trainer(pilot, "rloo", initial=sft, resume=resume)
    last = sft
    completed = read_json(pilot.root / "pilot/RL-index.json", {}).get("cases", [])
    while remote.process("pilot-trainer", "status")["active"]:
        packet = remote.read(inbox + "/rollout-request.json")
        if not packet:
            time.sleep(2)
            continue
        last = packet["policy_path"]
        pending_index = packet["completed_updates"]
        pending_task = pilot.plan["training_task_ids"][pending_index % len(pilot.plan["training_task_ids"])]
        pending_case = (
            Path(pilot.cfg["case_store"]) / "runs" / f"{pending_task}-pilot-rl-{pending_index + 1:06d}-0"
        )
        if stop_at - time.time() < pilot.plan["study_seconds"] + 900 and not pending_case.exists():
            for slot in range(2):
                pilot.pipeline.stop_policy(slot)
            remote.write(
                inbox + "/stop.json",
                dict(
                    reason="pilot_wall_budget_pause",
                    resume_permitted=True,
                    checkpoint=last,
                    scientific_convergence_claimed=False,
                ),
            )
            break
        index = packet["completed_updates"]
        group_id = f"group-{index + 1:06d}"
        task = pilot.plan["training_task_ids"][index % len(pilot.plan["training_task_ids"])]
        jobs = [
            dict(
                job_id=f"{task}-pilot-rl-{index + 1:06d}-{i}",
                task_id=task,
                arm="simjecture_sftrl9b",
                pilot=True,
            )
            for i in range(4)
        ]
        actual = pilot.batch(jobs, adapter=last)
        trajectories = [rl_trajectory(row["record"], row["task"], row["review"]) for row in actual]
        validate_group(trajectories)
        for slot in range(2):
            pilot.pipeline.stop_policy(slot)
        remote.write(inbox + "/" + group_id + ".json", dict(trajectories=trajectories), immutable=True)
        remote.write(
            inbox + "/" + packet["request_id"] + "-actors-stopped.json",
            dict(request_id=packet["request_id"], all_owned_policy_services_stopped=True),
            immutable=True,
        )
        completed = list(dict.fromkeys(completed + [row["case"] for row in actual]))
        write_json(
            pilot.root / "pilot/RL-index.json",
            dict(cases=completed, consumed_groups=index + 1, actual_stopping="wall-clock pilot window"),
        )
        while remote.process("pilot-trainer", "status")["active"]:
            following = remote.read(inbox + "/rollout-request.json")
            if following and following["request_id"] != packet["request_id"]:
                last = following["policy_path"]
                break
            # stop_at closes admission of NEW studies. A group already studied
            # and reviewed must be consumed before publishing stop.json: the
            # trainer deliberately gives stop.json priority over its inbox.
            # In particular, a five-hour provider pause can outlive stop_at.
            # The independent overall deadline guard still bounds this update.
            if pilot.time_left() <= 60:
                raise TimeoutError("Overall pilot deadline during pending RLOO update; immutable group retained")
            time.sleep(2)
    # Inference and optimizer updates never occupy these NPUs simultaneously.
    cutoff = time.monotonic() + 120
    while remote.process("pilot-trainer", "status")["active"] and time.monotonic() < cutoff:
        time.sleep(2)
    if remote.process("pilot-trainer", "status")["active"]:
        remote.process("pilot-trainer", "stop")
    final_request = remote.read(inbox + "/rollout-request.json")
    if final_request:
        last = final_request["policy_path"]
    pilot.save(
        "online_RLOO_paused",
        rl_checkpoint=last,
        actual_RL_cases=len(completed),
        full_RL_convergence_claimed=False,
    )
    return last


def _evaluation_once(pilot, sft, rl):
    results = []
    adapters = {
        "simjecture": None,
        "simjecture_raw9b": None,
        "simjecture_sft9b": sft,
        "simjecture_sftrl9b": rl,
    }
    for arm in pilot.plan["development_arms"]:
        adapter = adapters[arm]
        pilot.save("development_comparison", evaluating_arm=arm)
        jobs = [
            dict(job_id=f"{task}-pilot-{arm}", task_id=task, arm=arm, pilot=True)
            for task in pilot.plan["development_task_ids"]
        ]
        results.extend(pilot.batch(jobs, adapter=adapter))
    from .test_campaign import summarize

    report = summarize(pilot.root / "pilot/preliminary-results.json", results)
    paired = []
    for task in pilot.plan["development_task_ids"]:
        subset = {
            read_json(Path(r["case"]) / "study-run.json")["arm"]: r
            for r in results
            if r["task"]["task_id"] == task
        }
        base = subset["simjecture"]["review"]
        paired.append(
            dict(
                task_id=task,
                arms={
                    arm: dict(
                        C=r["review"]["C"],
                        D=r["review"]["D"],
                        delta_C=r["review"]["C"] - base["C"],
                        delta_D=r["review"]["D"] - base["D"],
                    )
                    for arm, r in subset.items()
                },
            )
        )
    write_json(
        pilot.root / "pilot/paired-development.json",
        dict(
            cases=paired,
            n=len(pilot.plan["development_task_ids"]),
            statistical_claim="descriptive pilot only; no reliable cross-task improvement claim",
            final_test_opened=False,
            dev_used_for_gradient_updates=False,
        ),
    )
    return report


def evaluation(pilot, sft, rl):
    """Review-only recovery never restarts a closed research clock or RL."""
    while True:
        started = time.time()
        try:
            return _evaluation_once(pilot, sft, rl)
        except Exception:
            store = Path(pilot.cfg["case_store"])
            paths = list((store / "runs").glob("*/supervisor/**/response.json"))
            paths += list((store / "assessments").glob("*/assessor.jsonl"))
            hits = [p.stat().st_mtime for p in paths if p.stat().st_mtime >= started
                    and "hit your usage limit" in p.read_text(encoding="utf-8", errors="replace").lower()]
            if not hits:
                raise
            resume_at = min(hits) + 5 * 3600
            pilot.save("quota_hold", quota_resume_epoch=resume_at, training_already_checkpointed=True,
                       task_deadlines_reset=False)
            for slot in range(2):
                pilot.pipeline.stop_policy(slot)
            wait_quota_recovery(pilot, resume_at)


def wait_quota_recovery(pilot, resume_at):
    """Persisted quota holds also apply after an operator/runtime restart."""
    if time.time() < resume_at:
        pilot.save("quota_hold", quota_resume_epoch=resume_at, task_deadlines_reset=False)
    while time.time() < resume_at:
        if time.time() >= pilot.deadline:
            raise TimeoutError("20-hour pilot deadline during provider quota recovery")
        time.sleep(min(30, resume_at - time.time()))
    if pilot.state.get("quota_resume_epoch") == resume_at:
        pilot.state.pop("quota_resume_epoch", None)
    pilot.save("quota_recovered", quota_recovered_at=time.time(), task_deadlines_reset=False)


def continue_pilot(pilot):
    # Reload configuration written during independent CPU qualification. Native
    # running cases keep their original frozen pools and clocks.
    import importlib

    for name in ("case", "collect", "review", "evaluation", "pipeline"):
        importlib.reload(importlib.import_module("research_decision." + name))
    pilot.cfg = read_json(pilot.root / "config/pipeline.local.json")
    pilot.plan = read_json(pilot.root / "pilot/plan.json")
    from .pipeline import Pipeline

    pilot.pipeline = Pipeline(pilot.root, pilot.cfg)
    pilot.state.pop("error", None)
    for identifier in pilot.plan["training_task_ids"] + pilot.plan["development_task_ids"]:
        task = dict(pilot.pipeline.tasks[identifier])
        task["original_total_wall_seconds"] = task["total_wall_seconds"]
        task["total_wall_seconds"] = pilot.plan["study_seconds"]
        task["budget_variant"] = "bounded_pilot; original full-protocol card retained"
        pilot.pipeline.tasks[identifier] = task
    if pilot.state.get("quota_resume_epoch"):
        wait_quota_recovery(pilot, pilot.state["quota_resume_epoch"])
    while True:
        attempt_started = time.time()
        try:
            sft = wait_sft(pilot)
            rl = online_window(pilot, sft)
            report = evaluation(pilot, sft, rl)
            break
        except Exception:
            # A genuine provider usage-limit event pauses admission. Existing
            # research clocks never reset, and unfinished records stay scored.
            hits = []
            store = Path(pilot.cfg["case_store"])
            paths = list((store / "runs").glob("*/supervisor/**/response.json")) + list(
                (store / "assessments").glob("*/assessor.jsonl")
            )
            for path in paths:
                if path.stat().st_mtime < attempt_started:
                    continue
                if "hit your usage limit" in path.read_text(encoding="utf-8", errors="replace").lower():
                    hits.append(path.stat().st_mtime)
            if not hits:
                raise
            resume_at = min(hits) + 5 * 3600
            pilot.save("quota_hold", quota_resume_epoch=resume_at, task_deadlines_reset=False)
            for slot in range(2):
                pilot.pipeline.stop_policy(slot)
            wait_quota_recovery(pilot, resume_at)
    pilot.save(
        "complete",
        preliminary_results=report,
        finished_at=time.time(),
        total_wall_seconds=time.time() - pilot.plan["start_epoch"],
        final_test_opened=False,
    )
    return pilot.state
