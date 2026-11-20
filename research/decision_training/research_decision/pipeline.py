"""Prepared study scheduler. Default inspection never launches an experiment.

Execution additionally requires an operator authorization record, absent during
preparation. All actual calls use fresh, filesystem-isolated native Simjecture
roles and the existing remote worker. There is no local physics fallback.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .case import closeout
from .collect import live_record, rl_trajectory, sft_samples
from .contracts import TASK_FIELDS, fingerprint
from .remote_control import Remote
from .review import run_review
from .rloo import validate_group
from .storage import read_json, write_json


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def require_authorization(root, stage):
    record = read_json(root / "launch-authorization.json", {})
    if not record.get("authorized") or stage not in record.get("stages", []):
        raise PermissionError("Preparation-only: scientific collection/training/evaluation is not authorized")
    if record.get("protocol_sha256") != fingerprint(read_json(root / "config/protocol.json")):
        raise PermissionError("Authorization does not match the frozen experimental protocol")


def initial_anchor(task, config):
    return dict(
        task_contract={k: task[k] for k in TASK_FIELDS if k in task},
        common_random_seed=task.get("perturbation_seed"),
        budget_seconds=task["total_wall_seconds"],
        toolchain=read_json(Path(config["package"]) / "reports/toolchain-lock.json"),
    )


def research_instruction(arm, *, verification_only=False):
    common = """You are part of the GPT-6.1 Sol Director/Worker/Reviewer team.
Read task.json and study-run.json. Use the installed Simjecture tools on remote workers.
Prefer independent-cpu (16 CPUs, 24576 MB, NumPy/SciPy) for compatible CPU studies;
remote-cpu (32 CPUs, 131072 MB) also has the existing Athena++ and WarpX installations.
Use real worker capabilities and resource reservations. Training NPUs are unavailable to simulations.
Use `from research_decision.simjecture_bridge import DecisionLab; lab=DecisionLab(CASE_ROOT)`
for EVERY simulation/analysis submission. Local CPU/NPU/GPU scientific execution is prohibited.
Only total study wall time limits research; choose experiment duration, count, mesh, particles,
solver hierarchy, scans, convergence and cross-scale validation dynamically within real capacity.
Do not pass arbitrary per-experiment timeout ceilings: its default is the remaining study budget.
Use task perturbation_seed and deterministic seeds derived from the experiment signature for
matching physical configurations. Account for model latency, queueing, diagnostics and closeout.
Before claiming evidence, inspect real terminal receipts, units, initial/boundary conditions,
physical balances and convergence. Keep verified-evidence.json as a public JSON array with
evidence_id, claim, receipt_ids, diagnostics, scope, uncertainty and verification_method.
Only scientifically reviewed observations go in that ledger. public-history.json is an array
of short evidence-linked decisions, never private reasoning or grades. The student state is
lab.state(); never transmit full status(), private reviews, scores, hidden references or thoughts.
At closeout write proposed-conclusion.json with supported/falsified claim objects (each with
evidence_ids), unresolved (including unverified hypotheses), and scope. Write RESULTS.md.
If time expires or the goal remains unfinished, still report the actual partial evidence,
falsifications and unresolved questions and their scope. Never invent a receipt or discovery.
"""
    if verification_only:
        common += """This is an independent verifier, without the original solver source.
Read task.json replication_targets. Use a different implementation or discretization and check
new physical conditions as well as direct replication. Preregister tolerances, units and error
criteria in measurement-plan.json before confirming runs. Record independent-measurements.json
as an array: observable, reference_method (name only), reference_kwargs (physical inputs),
estimate, units, receipt_ids, uncertainty, scope. Never insert an expected oracle value as a result.
Use numerical evolution/discretization, not a copied theoretical formula, to check the physics.
Record failure to reproduce and unresolved questions honestly.
"""
    if arm == "teacher":
        return (
            common
            + """For each decision, first create a concise public JSON decision conforming
to /app/schemas/advice.schema.json. Record it with lab.record_teacher_decision(lab.state(), advice).
Bind every executed plan using that advice_id, executed_plan, all five component_sources and
override_reasons. Teacher demonstration targets contain public decisions only.
"""
        )
    if arm == "simjecture":
        return common + "Make all scientific decisions independently; no student service is available.\n"
    return (
        common
        + """Before each decision call lab.advise(seed=..., state=lab.state()).
The 9B model advises experiment choice/organization, parameters, model hierarchy and scale.
Prefer its proposed scale whenever physically executable. You may correct or reject it, retaining
the exact raw suggestion, the concrete reason, and final executed plan. Bind lab.run to advice_id,
executed_plan, component_sources for experiment_selection,organization,parameters,model_hierarchy,scale
(student/modified/host/unused), and a reason for each modified/host component.
Malformed suggestions and complete takeovers stay in the log and earn no student positive credit.
The GPT-6.1 Sol team retains scientific reasoning, code execution, review and final authority.
"""
    )


class Pipeline:
    def __init__(self, root, config):
        self.root, self.cfg = Path(root), config
        self.remote = Remote(config)
        self.tasks = {
            r["task_id"]: r for name in ("train", "dev") for r in rows(self.root / f"tasks/{name}.jsonl")
        }
        self._services = [None, None]
        self._stop = threading.Event()

    def ensure_policy(self, slot, arm, adapter):
        if arm in {"simjecture", "teacher"}:
            self.stop_policy(slot)
            return None
        desired = (arm, str(adapter) if adapter else None)
        if self._services[slot] != desired:
            self.stop_policy(slot)
            root = self.cfg["remote_root"]
            argv = [
                root + "/resources/training-python",
                "-m",
                "research_decision.policy_service",
                "--base",
                root + "/models/Qwen3.5-9B",
                "--config",
                root + "/config/training.json",
                "--device",
                str(slot),
                "--arm",
                arm,
                "--port",
                str(19190 + slot),
                "--receipts",
                root + "/data/policy-receipts/" + arm + "-" + str(slot),
            ]
            if adapter:
                argv += ["--adapter", str(adapter)]
            self.remote.process(
                "policy-" + str(slot), "start", argv, env={"PYTHONPATH": root, "OMP_NUM_THREADS": "2"}
            )
            cutoff = time.monotonic() + self.cfg["policy_start_timeout_seconds"]
            while time.monotonic() < cutoff:
                health = self.remote.call("health", slot=slot)
                if health.get("ready"):
                    if health["arm"] != arm:
                        raise ValueError("Policy endpoint reports an incorrect intervention arm")
                    self._services[slot] = desired
                    return health["policy_sha256"]
                if not self.remote.process("policy-" + str(slot), "status")["active"]:
                    raise RuntimeError("Policy service failed before health readiness")
                time.sleep(2)
            raise TimeoutError("Policy startup timed out before any research study began")
        return self.remote.call("health", slot=slot)["policy_sha256"]

    def stop_policy(self, slot):
        self.remote.process("policy-" + str(slot), "stop")
        self._services[slot] = None

    def materialize(self, job, task, slot, policy_sha):
        from conjecture_solver.study_launch import NativeStudyRequest, materialize_native, resume_native

        root = Path(self.cfg["case_store"]) / "runs" / job["job_id"]
        if (root / "study-launch.json").exists():
            return root, resume_native(root)
        request = NativeStudyRequest(
            hypothesis=task["question"],
            instruction=research_instruction(
                job["arm"], verification_only=job.get("verification_only", False)
            ),
            campaign_id=job["job_id"],
            output_directory=str(root),
            max_wall_seconds=float(task["total_wall_seconds"]),
            max_command_seconds=float(task["total_wall_seconds"]),
            backend="codex",
            model="gpt-6.1-sol",
            judge_backend="codex",
            judge_model="gpt-6.1-sol",
            director_model="gpt-6.1-sol",
            director_enabled=not job.get("autonomous_student", False),
            agent_executable=self.cfg["codex_wrapper"],
            judge_executable=self.cfg["codex_wrapper"],
            machine_registry=self.cfg["machine_registry"],
            machine_ids=read_json(self.root / "config/pipeline.local.json").get(
                "machine_ids", ["remote-cpu"]
            ),
            execution_backend="process-cooperative",
            allow_solver_development=True,
            artifact_policy="remote",
            max_experiment_bytes=self.cfg["study_disk_bytes"],
            max_total_bytes=self.cfg["study_disk_bytes"],
            report_reserve_seconds=min(90.0, task["total_wall_seconds"] / 20),
        )
        plan = materialize_native(request)
        write_json(root / "task.json", task, immutable=True)
        write_json(root / "initial-state.json", initial_anchor(task, self.cfg), immutable=True)
        manifest = read_json(root / "research.json")
        write_json(
            root / "study-run.json",
            dict(
                job,
                deadline=manifest["deadline"],
                policy_sampling_seed=int(fingerprint(job["job_id"])[:8], 16),
                transport_token=__import__("uuid").uuid4().hex,
                policy_sha256=policy_sha,
                advice_endpoint=f"gateway:{slot}",
                public_resources=self.cfg["public_resources"],
            ),
            immutable=True,
        )
        return root, plan

    def study(self, job, *, slot, adapter=None, assess=True, private_contract=None):
        from conjecture_solver.mvp_launch import start_managed_campaign
        from conjecture_solver.research_service import ResearchService

        task = self.tasks[job["task_id"]]
        existing = Path(self.cfg["case_store"]) / "runs" / job["job_id"]
        if (existing / "phase_conclusion.json").exists():
            return (
                self.assess(existing, task, slot=slot, private_contract=private_contract)
                if assess
                else dict(case=str(existing))
            )
        policy_sha = self.ensure_policy(slot, job["arm"], adapter)
        disk = self.remote.call("disk")
        if disk["free"] < self.cfg["remote_minimum_free_bytes"]:
            raise RuntimeError("Remote disk backpressure: archive completed studies before admitting another")
        case, plan = self.materialize(job, task, slot, policy_sha)
        if read_json(case / "study-run.json")["deadline"] <= time.time():
            reason = "wall_budget_expired_before_resume"
        else:
            campaign = start_managed_campaign(plan)
            try:
                deadline = read_json(case / "study-run.json")["deadline"]
                while campaign.poll() is None:
                    if self._stop.is_set() or time.time() >= deadline:
                        campaign.cancel(wait_interrupt_seconds=3, wait_terminate_seconds=3)
                        break
                    time.sleep(1)
                reason = "wall_budget_exhausted" if time.time() >= deadline else "native_controller_closed"
            finally:
                campaign.close()
        ResearchService(case).cancel_active()
        closeout(case, reason)
        return (
            self.assess(case, task, slot=slot, private_contract=private_contract)
            if assess
            else dict(case=str(case))
        )

    def assess(self, case, task, *, slot=0, private_contract=None):
        from .evidence_materialization import materialize

        materialize(case)
        from .verification import run_verification

        if not (case / "independent-verification-receipts.json").exists():
            run_verification(self, case, task, slot=slot)
        if private_contract and private_contract.get("evaluation_type") == "known":
            from .objective import evaluate_known

            evaluate_known(self, case, task, private_contract)
        record = live_record(case)
        if not record["receipts"] and not record["events"]:
            # This is an observed empty provider-failure run, not a fabricated
            # model review. It stays in every score table and cannot enter SFT.
            from .evaluation import C_WEIGHTS, D_WEIGHTS

            review = dict(
                C_components={k: 0 for k in C_WEIGHTS},
                D_components={k: 0 for k in D_WEIGHTS},
                C=0,
                D=0,
                accepted_for_training=False,
                terminal_validity=0,
                unsupported_claims=0,
                process_gains=[],
                independent_verifications=[],
                reviewer_model=None,
                evaluation_method="deterministic_empty_execution_and_decision_record",
                reviewed_record_sha256=fingerprint(record),
                rationale="No execution, recorded decision, or scientific evidence exists; retained as an unsuccessful run.",
            )
            path = case / "assessment-receipt.json"
            write_json(path, review)
            return dict(case=str(case), task=task, record=record, review=review, review_path=str(path))
        destination = Path(self.cfg["case_store"]) / "assessments" / fingerprint(record)[:24]
        result = read_json(destination / "review-receipt.json")
        if result is None:
            participants = []
            for path in list(case.rglob("*.jsonl")) + list(case.rglob("response.json")):
                if ".role-runtime" in path.parts:
                    continue
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("type") == "thread.started":
                        participants.append(event["thread_id"])
            result = run_review(
                self.cfg,
                destination,
                record,
                task,
                objective=read_json(case / "objective-validation.json"),
                participant_sessions=participants,
            )
        write_json(case / "assessment-receipt.json", result)
        return dict(
            case=str(case),
            task=task,
            record=record,
            review=result,
            review_path=str(destination / "review-receipt.json"),
        )

    def jobs(self, jobs, adapter=None, private_contracts=None):
        results = [None] * len(jobs)

        def worker(slot):
            for index in range(slot, len(jobs), 2):
                current_adapter = adapter.get(jobs[index]["arm"]) if isinstance(adapter, dict) else adapter
                results[index] = self.study(
                    jobs[index],
                    slot=slot,
                    adapter=current_adapter,
                    private_contract=(private_contracts or {}).get(jobs[index]["task_id"]),
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, slot) for slot in range(2)]
            for future in futures:
                future.result()
        return results

    def collect_teacher(self):
        jobs = [dict(row, arm="teacher") for row in rows(self.root / "plans/teacher_collection.jsonl")]
        results = self.jobs(jobs)
        samples = [
            sample
            for result in results
            for sample in sft_samples(
                result["record"], result["task"], result["review"], result["review_path"]
            )
        ]
        accepted = {s["trajectory_id"] for s in samples}
        if len(accepted) != 240:
            raise ValueError(
                "SFT initialization requires 240 accepted actual teacher trajectories; no padding by invented data"
            )
        # Full-study reattempts are extra measured collection cost. A review
        # failure never rewrites the already closed scientific record.
        output = self.root / "data/sft/decisions.jsonl"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in samples), encoding="utf-8"
        )
        self.remote.write("data/sft/decisions.json", samples, immutable=True)
        # Publish actual JSONL bytes through the owned data RPC.
        self.remote.call("write_jsonl", path="data/sft/decisions.jsonl", values=samples)
        return dict(accepted_trajectories=240, decisions=len(samples), output=str(output))

    def start_trainer(self, stage, initial=None, resume=None):
        root = self.cfg["remote_root"]
        for slot in range(2):
            self.stop_policy(slot)
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
            root + "/config/training.json",
            "--data",
            root + ("/data/sft/decisions.jsonl" if stage == "sft" else "/data/rloo-inbox"),
            "--output",
            root + "/checkpoints",
        ]
        if initial:
            argv += ["--initial", str(initial)]
        if resume:
            argv += ["--resume", str(resume)]
        return self.remote.process(
            "trainer",
            "start",
            argv,
            env={"PYTHONPATH": root, "OMP_NUM_THREADS": "2", "HCCL_CONNECT_TIMEOUT": "300"},
        )

    def development(self, checkpoint, *, initial=False):
        protocol = read_json(self.root / "config/protocol.json")
        state = self.remote.read("checkpoints/selection.json") or {}
        look = 1 if initial else state.get("last_evaluation_index", 1) + 1
        jobs = [
            dict(
                job_id=f"{t['task_id']}-dev-{look:03d}",
                task_id=t["task_id"],
                arm="simjecture_sft9b" if initial else "simjecture_sftrl9b",
            )
            for t in self.tasks.values()
            if t["split"] == "dev"
        ]
        current = self.jobs(jobs, adapter=checkpoint)
        incumbent = read_json(self.root / "data/dev-incumbent.json")
        if initial:
            if incumbent is None:
                basejobs = [
                    dict(job_id=t["task_id"] + "-dev-baseline", task_id=t["task_id"], arm="simjecture")
                    for t in self.tasks.values()
                    if t["split"] == "dev"
                ]
                baseline = self.jobs(basejobs)
                incumbent = {r["task"]["task_id"]: {k: r["review"][k] for k in ("C", "D")} for r in baseline}
                write_json(self.root / "data/dev-original-baseline.json", incumbent, immutable=True)
            state = dict(
                best_checkpoint=checkpoint,
                no_improvement=0,
                last_evaluation_index=1,
                initial_C_D={r["task"]["task_id"]: {k: r["review"][k] for k in ("C", "D")} for r in current},
                stop=False,
            )
        else:
            from .evaluation import checkpoint_result, stopping_update

            paired = [
                dict(
                    task_id=r["task"]["task_id"],
                    mechanism_group=r["task"]["mechanism_group"],
                    comparison="current_best_checkpoint",
                    baseline=incumbent[r["task"]["task_id"]],
                    candidate={k: r["review"][k] for k in ("C", "D")},
                )
                for r in current
            ]
            # The first look documents SFT vs native. Subsequent sequential
            # selection uses only incumbent-matched, unseen-development cases.
            result = checkpoint_result(paired, look - 1)
            state = stopping_update(
                state, result, checkpoint, collapse_with_adaptation_loss=detect_collapse(current, protocol)
            )
            state.update(last_evaluation_index=look, last_result=result)
            write_json(
                self.root / f"data/dev-look-{look:03d}.json", dict(paired=paired, state=state), immutable=True
            )
        if initial or state["best_checkpoint"] == checkpoint:
            write_json(
                self.root / "data/dev-incumbent.json",
                {r["task"]["task_id"]: {k: r["review"][k] for k in ("C", "D")} for r in current},
            )
        self.remote.write("checkpoints/retain.json", [Path(state["best_checkpoint"]).name])
        self.remote.write("checkpoints/selection.json", state)
        if state["stop"]:
            self.remote.write(
                "data/rloo-inbox/stop.json",
                dict(best_checkpoint=state["best_checkpoint"], reason="development_stopping_rule"),
            )
        return state

    def online(self, initial, resume=None):
        if not self.remote.read("checkpoints/selection.json"):
            self.development(initial, initial=True)
        self.start_trainer("rloo", initial=initial, resume=resume)
        evaluated = set()
        while self.remote.process("trainer", "status")["active"]:
            request = self.remote.read("data/rloo-inbox/rollout-request.json")
            if not request or not request["model_offloaded"]:
                time.sleep(2)
                continue
            update = request["completed_updates"]
            group_id = f"group-{update + 1:06d}"
            if group_id in request["consumed_group_ids"]:
                time.sleep(2)
                continue
            if request["evaluate_before_next_group"] and update not in evaluated:
                state = self.development(request["policy_path"])
                evaluated.add(update)
                if state["stop"]:
                    break
            task = balanced_task(self.tasks, update)
            jobs = [
                dict(
                    job_id=f"{task['task_id']}-rl-{update + 1:06d}-{trial}",
                    task_id=task["task_id"],
                    arm="simjecture_sftrl9b",
                )
                for trial in range(4)
            ]
            results = self.jobs(jobs, adapter=request["policy_path"])
            group = [rl_trajectory(r["record"], r["task"], r["review"]) for r in results]
            validate_group(group)
            for slot in range(2):
                self.stop_policy(slot)
            self.remote.write(
                "data/rloo-inbox/" + group_id + ".json", dict(trajectories=group), immutable=True
            )
            self.remote.write(
                "data/rloo-inbox/" + request["request_id"] + "-actors-stopped.json",
                dict(request_id=request["request_id"], all_owned_policy_services_stopped=True),
                immutable=True,
            )
            # Wait for the immutable request index to advance; never replay a
            # just-published group while the trainer is restoring device state.
            while self.remote.process("trainer", "status")["active"]:
                following = self.remote.read("data/rloo-inbox/rollout-request.json")
                if following and following["request_id"] != request["request_id"]:
                    break
                time.sleep(2)
        state = self.remote.read("checkpoints/selection.json")
        if not state or not state.get("stop"):
            raise RuntimeError("Trainer stopped without its scientific development stopping receipt")
        return state


def balanced_task(tasks, group_index):
    train = [t for t in tasks.values() if t["split"] == "train"]
    # Round-robin difficulty and physical mechanism. Every 20 groups collect
    # exactly 80 complete trajectories, and each 80-group sweep covers all cards.
    families = sorted({t["family_group"] for t in train})
    lookup = {(t["family_group"], t["difficulty"]): t for t in train}
    ordered = [
        lookup[(family, (index + sweep) % 4 + 1)]
        for sweep in range(4)
        for index, family in enumerate(families)
    ]
    return ordered[group_index % len(ordered)]


def detect_collapse(results, protocol):
    signatures, adaptation = [], []
    for row in results:
        audits = [e["payload"] for e in row["record"]["events"] if e["kind"] == "decision_audit"]
        signatures.extend(
            fingerprint(
                {
                    k: a.get("executed_plan", {}).get(k)
                    for k in ("solver", "parameters", "scale", "organization")
                }
            )
            for a in audits
        )
        adaptation.append(row["review"]["D_components"]["evidence_adaptation"])
    # Constant advice alone is not proof of collapse. Require repeated policy
    # output AND loss of evidence-responsive decisions across the held-out set.
    return bool(
        len(signatures) >= 16
        and len(set(signatures)) / len(signatures) < 0.1
        and sum(adaptation) / len(adaptation) < 5
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["inspect", "collect-sft", "sft", "online", "dev"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--initial")
    parser.add_argument("--resume")
    args = parser.parse_args()
    root = args.root.resolve()
    cfg = read_json(root / "config/pipeline.local.json")
    if args.operation == "inspect":
        print(
            json.dumps(
                dict(
                    preparation_only=True,
                    authorized=False,
                    training_cards=len(rows(root / "tasks/train.jsonl")),
                    development_cards=len(rows(root / "tasks/dev.jsonl")),
                    teacher_jobs=len(rows(root / "plans/teacher_collection.jsonl")),
                    formal_jobs=80,
                    attribution_jobs=40,
                ),
                ensure_ascii=False,
            )
        )
        return
    require_authorization(root, args.operation)
    pipeline = Pipeline(root, cfg)
    # Controller gateway is outside every case's filesystem namespace.
    from .gateway import ScienceGateway

    remote = pipeline.remote
    socket_path = Path(read_json(root / "config/isolation.local.json")["transport_socket"])
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    if socket_path.exists():
        raise RuntimeError("Transport socket already exists; inspect the owning controller before reuse")
    from .network import model_network

    with (
        model_network(read_json(root / "config/isolation.local.json")["network_proxy"]),
        ScienceGateway(
            socket_path, remote.route, remote.root,
            {"cannlab-cpu": (Remote(dict(cfg, ssh_route=str(root / "config/ssh-cpu-route.local.json"))).route, remote.root)}
            if (root / "config/ssh-cpu-route.local.json").exists() else {},
        ) as gateway,
    ):
        socket_path.chmod(0o600)
        thread = threading.Thread(target=gateway.serve_forever, daemon=True)
        thread.start()
        try:
            if args.operation == "collect-sft":
                result = pipeline.collect_teacher()
            elif args.operation == "sft":
                result = pipeline.start_trainer("sft", resume=args.resume)
            elif args.operation == "online":
                if not args.initial:
                    parser.error("online requires the immutable SFT --initial checkpoint")
                result = pipeline.online(args.initial, args.resume)
            else:
                if not args.initial:
                    parser.error("dev requires a pinned --initial checkpoint")
                result = pipeline.development(args.initial, initial=True)
            print(json.dumps(result, ensure_ascii=False))
        finally:
            gateway.shutdown()
            socket_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
