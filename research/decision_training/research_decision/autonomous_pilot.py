"""User-authorized, quota-independent student RLOO with real native Lab jobs."""

from __future__ import annotations

import hashlib
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .autonomous_reward import RULES, export_trajectory, numerical_review
from .autonomous_tools import TOOL_CONTRACT, translate
from .case import TERMINAL, closeout, receipts
from .collect import live_record
from .contracts import DECISION_COMPONENTS, fingerprint
from .gateway import ScienceGateway
from .network import model_network
from .pilot import Pilot
from .remote_control import Remote
from .rloo import validate_group
from .simjecture_bridge import DecisionLab
from .storage import read_json, write_json


def materialize(pilot, task, case_id, slot, policy_sha):
    from conjecture_solver.execution_pool import MachineRegistry
    from conjecture_solver.research_service import ResearchService

    from .pipeline import initial_anchor

    case = Path(pilot.cfg["case_store"]) / "runs" / case_id
    if (case / "research.json").exists():
        if read_json(case / "task.json") != task or read_json(case / "study-run.json")["policy_sha256"] != policy_sha:
            raise ValueError("An autonomous resume changed its task or frozen policy")
        return case
    pool = MachineRegistry(pilot.cfg["machine_registry"]).freeze(["independent-cpu"])
    service = ResearchService.create(
        case, task["question"], wall_seconds=task["total_wall_seconds"],
        execution_pool=pool, execution_backend="process-cooperative", artifact_policy="remote",
        report_reserve_seconds=15, max_experiment_bytes=4 * 1024**3, max_total_bytes=8 * 1024**3,
        allow_solver_development=True,
    )
    write_json(case / "task.json", task, immutable=True)
    write_json(case / "initial-state.json", initial_anchor(task, pilot.cfg), immutable=True)
    run = dict(
        pilot=True, autonomous_student=True, decision_host_model="deterministic_execution_adapter_v1; no LLM host",
        arm="simjecture_sftrl9b", task_id=task["task_id"], deadline=service.manifest["deadline"],
        transport_token=uuid.uuid4().hex, policy_sha256=policy_sha,
        policy_sampling_seed=int(fingerprint(case_id)[:8], 16), advice_endpoint=f"gateway:{slot}",
        public_resources=dict(worker="independent-cpu", cpus=16, memory_mb=24576, gpus=0,
                              local_scientific_fallback=False, training_NPU_access=False,
                              executable_tool=TOOL_CONTRACT),
    )
    if not (case / "study-run.json").exists():
        write_json(case / "study-run.json", run, immutable=True)
    for name in ["mhd_core.py", "mhd_experiment.py"]:
        target = case / "research" / name
        data = (pilot.root / "science_tools" / name).read_bytes()
        if target.exists() and target.read_bytes() != data:
            raise ValueError("Frozen simulation source changed during a student research episode")
        target.write_bytes(data)
    return case


def study(pilot, task, case_id, slot, policy_sha):
    from conjecture_solver.research_service import ResearchService

    case = materialize(pilot, task, case_id, slot, policy_sha)
    if (case / "phase_conclusion.json").exists():
        record = live_record(case)
        return export_trajectory(record, task, read_json(case / "autonomous-numerical-review.json"))
    lab = DecisionLab(case)
    outputs = {}
    history = read_json(case / "public-history.json", [])
    reason = "total_wall_budget_exhausted"
    try:
        while lab.native.status()["remaining_seconds"] > 20 and pilot.time_left() > 120:
            # Explicitly selected recent receipts keep the state within the
            # qualified context size; omitted receipt identities remain indexed.
            actual = receipts(case)
            selected = [r["id"] for r in actual if r["status"] in TERMINAL][-3:]
            state = lab.state(receipt_ids=selected)
            reply = lab.advise(state)
            advice = reply.get("advice")
            if not advice:
                history.append(dict(event="tool_request_rejected", reason=reply.get("validation_error")))
            elif advice["action"] == "closeout":
                reason = "student_chose_closeout"
                history.append(dict(event="student_closeout", statement=advice["public_justification"],
                                    verification="provisional student interpretation; numerical claims checked separately"))
                break
            else:
                for index, experiment in enumerate(advice["experiments"]):
                    if lab.native.status()["remaining_seconds"] <= 20:
                        break
                    try:
                        config, defaults = translate(experiment, task)
                        name = "experiment-" + uuid.uuid4().hex + ".json"
                        write_json(case / "research" / name, config, immutable=True)
                        # The remote wrapper consumes a stable filename. Its
                        # source and the chosen JSON are frozen in each receipt.
                        run_source = "run-" + name[:-5] + ".py"
                        script = (
                            "from pathlib import Path\nimport shutil\n"
                            + "shutil.copyfile(" + repr(name) + ", 'experiment.json')\n"
                            + "from mhd_experiment import main\nmain()\n"
                        )
                        (case / "research" / run_source).write_text(script)
                        sources = {c: "student" for c in DECISION_COMPONENTS}
                        reasons = {}
                        if defaults:
                            sources["parameters"] = "modified"
                            reasons["parameters"] = "Declared deterministic tool defaults: " + str(defaults)
                        receipt = lab.run(
                            run_source, inputs=[name, "mhd_core.py", "mhd_experiment.py"],
                            outputs=["observations.json", "raw.npz"], machine="independent-cpu",
                            resources=config["resources"], key=reply["advice_id"] + "-" + str(index),
                            advice_id=reply["advice_id"], executed_plan=dict(experiment, tool_inputs=config),
                            component_sources=sources, override_reasons=reasons,
                        )
                        while True:
                            lab.native.status()
                            terminal = read_json(case / "experiments" / (receipt["id"] + ".json"))
                            if terminal["status"] in TERMINAL:
                                break
                            if lab.native.status()["remaining_seconds"] <= 0:
                                ResearchService(case).cancel_active()
                            time.sleep(.5)
                        artifacts = terminal.get("remote_artifacts") or terminal.get("artifacts") or {}
                        if "observations.json" in artifacts:
                            lab.fetch_remote(experiment=terminal["id"], path="observations.json")
                            path = case / "experiments" / terminal["id"] / "workspace/observations.json"
                            data = path.read_bytes()
                            if hashlib.sha256(data).hexdigest() != artifacts["observations.json"]["sha256"]:
                                raise ValueError("A numerical observation changed after execution")
                            outputs[terminal["id"]] = read_json(path)
                        history.append(dict(event="actual_experiment", receipt_id=terminal["id"],
                                            terminal_status=terminal["status"], parameters=config,
                                            deterministic_defaults=defaults))
                    except (ValueError, KeyError, TypeError) as error:
                        history.append(dict(event="tool_request_rejected", reason=str(error),
                                            advice_id=reply["advice_id"]))
            write_json(case / "public-history.json", history[-6:])
    except Exception as error:
        reason = "runtime_interruption: " + repr(error)
        write_json(case / "autonomous-runtime-error.json", dict(error=repr(error), at=time.time()))
    finally:
        ResearchService(case).cancel_active()
        lab.journal.close()
    supported = []
    for identifier, document in outputs.items():
        if document.get("measurements"):
            evidence_id = "measurement:" + identifier
            supported.append(dict(claim="Recorded periodic 1D-MHD measurements in observations.json",
                                  evidence_ids=[evidence_id]))
    ledger = [dict(evidence_id="measurement:" + identifier, claim="Executed numerical measurements",
                   receipt_ids=[identifier], diagnostics=document.get("measurements", []),
                   scope="1D3V smooth ideal MHD, fixed numerical scheme", uncertainty="convergence and independent review may remain incomplete",
                   verification_method="source/receipt/artifact integrity; not independent replication")
              for identifier, document in outputs.items() if document.get("measurements")]
    write_json(case / "verified-evidence.json", ledger)
    write_json(case / "proposed-conclusion.json", dict(
        supported=supported, falsified=[], unresolved=[
            "Independent numerical replication and scientific review remain pending; no discovery claim.",
            "Evidence applies only to actually executed parameters and the stated one-dimensional model.",
        ], scope="User-authorized autonomous student training pilot; no GPT research host or reward assessor",
    ))
    (case / "research/RESULTS.md").write_text(
        "# Partial numerical research conclusion\n\n" + str(len(outputs))
        + " actual experimental observation documents were retained.\n\n"
        + "See verified-evidence.json for measured quantities and receipt identities. "
        + "No unverified hypothesis is a discovery. Independent replication, broader validity "
        + "and the final C/D assessment remain unresolved. Termination: " + reason + "\n"
    )
    closeout(case, reason)
    record = live_record(case)
    review = numerical_review(record, outputs)
    write_json(case / "autonomous-numerical-review.json", review, immutable=True)
    return export_trajectory(record, task, review)


def train(pilot):
    pilot.state.pop("error", None)
    plan = read_json(pilot.root / "pilot/autonomous-plan.json")
    if not plan["user_authorized"]:
        raise PermissionError("Autonomous branch not authorized")
    remote = pilot.pipeline.remote
    root = pilot.cfg["remote_root"]
    initial = plan["teacher_checkpoint"]
    start = read_json(pilot.root / "pilot/autonomous-status.json", {}).get("started_at", time.time())
    reserve = 3 * 3600 if plan.get("post_training_comparison", True) else 600
    stop_at = min(start + plan["RL_wall_window_hours"] * 3600, pilot.deadline - reserve)
    write_json(pilot.root / "pilot/autonomous-reward-rules.json", RULES, immutable=True)
    previous = remote.read(plan["inbox"] + "/rollout-request.json") or {}
    resume = previous.get("policy_path")
    argv = [root + "/resources/training-python", "-m", "torch.distributed.run", "--nproc-per-node=2",
            "--master-port=29617", "-m", "research_decision.train_adapter", "rloo", "--base",
            root + "/models/Qwen3.5-9B", "--config", root + "/config/pilot-training.json",
            "--data", root + "/" + plan["inbox"], "--output", root + "/" + plan["output"], "--initial", initial]
    if resume and resume != initial:
        argv += ["--resume", resume]
    active = remote.process("autonomous-trainer", "status")
    if active["active"]:
        if root + "/" + plan["inbox"] not in active["record"]["argv"]:
            raise RuntimeError("An existing autonomous trainer uses another inbox")
    else:
        remote.process("autonomous-trainer", "start", argv, dict(PYTHONPATH=root, OMP_NUM_THREADS="2", HCCL_CONNECT_TIMEOUT="300"))
    last, completed = initial, 0
    while remote.process("autonomous-trainer", "status")["active"]:
        request = remote.read(plan["inbox"] + "/rollout-request.json")
        if not request:
            time.sleep(2)
            continue
        last = request["policy_path"]
        index = request["completed_updates"]
        completed = index
        if time.time() + plan["study_seconds"] + 600 >= stop_at:
            remote.write(plan["inbox"] + "/stop.json", dict(reason="autonomous_pilot_wall_budget", checkpoint=last))
            break
        pilot.save("autonomous_student_RLOO_running", autonomous_branch=True, GPT_required_for_training=False,
                   autonomous_checkpoint=last, autonomous_completed_groups=index)
        write_json(pilot.root / "pilot/autonomous-status.json", dict(
            started_at=start, stop_at=stop_at, completed_groups=index, policy_path=last,
            phase="collecting_student_trajectories", GPT_calls=0,
        ))
        group_cases = [Path(pilot.cfg["case_store"]) / "runs" / f"T01-L1-pilot-auto-rl-{index + 1:06d}-{trial}"
                       for trial in range(4)]
        if all((case / "phase_conclusion.json").exists() for case in group_cases):
            shas = [request["policy_sha256"]] * 2
        else:
            shas = [pilot.pipeline.ensure_policy(slot, "simjecture_sftrl9b", last) for slot in range(2)]
        if len(set(shas)) != 1:
            raise ValueError("Autonomous actors have different policy weights")
        task = dict(pilot.pipeline.tasks[plan["training_task_ids"][index % len(plan["training_task_ids"])]] )
        task.update(total_wall_seconds=plan["study_seconds"], original_total_wall_seconds=task["total_wall_seconds"],
                    solver_candidates=["MHD1D"], budget_variant="autonomous quota-independent pilot")
        def work(trial):
            return study(pilot, task, f"T01-L1-pilot-auto-rl-{index + 1:06d}-{trial}", trial % 2, shas[trial % 2])
        with ThreadPoolExecutor(max_workers=4) as pool:
            trajectories = list(pool.map(work, range(4)))
        validate_group(trajectories)
        for slot in range(2):
            pilot.pipeline.stop_policy(slot)
        group = dict(trajectories=trajectories)
        remote.write(plan["inbox"] + f"/group-{index + 1:06d}.json", group, immutable=True)
        write_json(pilot.root / f"data/pilot-autonomous/group-{index + 1:06d}.json", group, immutable=True)
        remote.write(plan["inbox"] + "/" + request["request_id"] + "-actors-stopped.json",
                     dict(request_id=request["request_id"], all_owned_policy_services_stopped=True), immutable=True)
        while remote.process("autonomous-trainer", "status")["active"]:
            following = remote.read(plan["inbox"] + "/rollout-request.json")
            if following and following["request_id"] != request["request_id"]:
                last, completed = following["policy_path"], following["completed_updates"]
                break
            time.sleep(2)
    while remote.process("autonomous-trainer", "status")["active"]:
        time.sleep(2)
    pilot.save("autonomous_RLOO_paused_for_comparison", autonomous_checkpoint=last,
               autonomous_completed_groups=completed, scientific_convergence_claimed=False)
    return initial, last


def main():
    root = Path(__file__).resolve().parents[1]
    pilot = Pilot(root)
    cfg = read_json(root / "config/isolation.local.json")
    socket = Path(cfg["transport_socket"])
    if socket.exists():
        raise RuntimeError("Another controller owns the scientific transport")
    cpu = Remote(dict(pilot.cfg, ssh_route=str(root / "config/ssh-cpu-route.local.json")))
    with model_network(cfg["network_proxy"]), ScienceGateway(
        socket, pilot.pipeline.remote.route, pilot.pipeline.remote.root,
        {"cannlab-cpu": (cpu.route, cpu.root)},
    ) as gateway:
        socket.chmod(0o600)
        os.environ["SCIENCE_TRANSPORT_SOCKET"] = str(socket)
        threading.Thread(target=gateway.serve_forever, daemon=True).start()
        try:
            sft, rl = train(pilot)
            if not read_json(root / "pilot/autonomous-plan.json").get("post_training_comparison", True):
                pilot.save("complete", completed_scope="autonomous_training_only", autonomous_checkpoint=rl,
                           independent_C_D_review_pending=True, finished_at=time.time(), final_test_opened=False)
                return
            # Training never waits for GPT. Only independent downstream C/D
            # assessment and the original four-arm comparison use the quota.
            from .pilot_training import evaluation, wait_quota_recovery
            if pilot.state.get("quota_resume_epoch"):
                wait_quota_recovery(pilot, pilot.state["quota_resume_epoch"])
            pilot.pipeline = __import__("research_decision.pipeline", fromlist=["Pipeline"]).Pipeline(root, pilot.cfg)
            for identifier in pilot.plan["development_task_ids"]:
                task = dict(pilot.pipeline.tasks[identifier])
                task.update(original_total_wall_seconds=task["total_wall_seconds"], total_wall_seconds=pilot.plan["study_seconds"])
                pilot.pipeline.tasks[identifier] = task
            report = evaluation(pilot, sft, rl)
            pilot.save("complete", preliminary_results=report, finished_at=time.time(), final_test_opened=False)
        except Exception as error:
            pilot.save("autonomous_needs_resume", error=repr(error), final_test_opened=False)
            raise
        finally:
            gateway.shutdown()
            socket.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
