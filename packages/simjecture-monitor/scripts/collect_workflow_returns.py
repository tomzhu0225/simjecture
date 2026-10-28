"""Plan and execute sampled parked workflows with ordinary-wakeup controls."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from pathlib import Path

from collect_controlled_returns import source_identity
from export_workflow_returns import export, require_native_evidence
from generalization_fixture import CASES
from paired_continuations import CRITERIA, WORKER
from simjecture_monitor.action_distribution import DISTRIBUTIONS, INDEPENDENT
from simjecture_monitor.attention_server import request
from simjecture_monitor.events import digest, put
from simjecture_monitor.native_guard import process_stat, stop_session
from simjecture_monitor.sampling_trace import file_reference
from simjecture_monitor.workflow_collection import DEFAULTS, block_wall_seconds, settings

SCRIPTS = Path(__file__).resolve().parent
HOST_POLICY = dict(
    wall_seconds=650,
    maximum_parent_turns=4,
    simulation_limit=4,
    poll_seconds=5,
    fallback_seconds=90,
    maximum_discretionary_attention=1,
    explicit_worker_help=True,
    explicit_repair_requests=True,
    lifecycle="parked_until_terminal_fallback_or_returned_attention/v1",
    reward_version="verified_workflow_quality_and_execution_cost/v1",
)


def read(path):
    return json.loads(path.read_text())


def sources():
    root = SCRIPTS.parents[2]
    return source_identity() | {
        "core/" + str(path.relative_to(root / "src")): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((root / "src").rglob("*.py"))
    }


def plan(args):
    configuration = settings({key: getattr(args, key, value) for key, value in DEFAULTS.items()})
    host_policy = HOST_POLICY | dict(maximum_parent_turns=configuration["parent_turn_limit"])
    distribution = getattr(args, "decision_distribution", INDEPENDENT)
    if distribution not in DISTRIBUTIONS:
        raise ValueError("Unknown action distribution")
    if args.replicates < 1 or args.purpose == "train" and args.replicates < 2:
        raise ValueError(
            "Training requires at least two policy and two control episodes per configuration"
        )
    if args.native_cap < 1 or not math.isfinite(args.temperature) or args.temperature <= 0:
        raise ValueError("Require positive resource limits and temperature")
    if not args.family or len(set(args.family)) != len(args.family):
        raise ValueError("Declare distinct scientific mechanism families")
    fingerprint = sources()
    backend_hash = file_reference(args.backend)["sha256"]
    rng = random.Random(args.order_seed)
    blocks = []
    for index, family in enumerate(sorted(args.family)):
        seed = args.configuration_seed + index
        context = dict(
            configuration_sha256=digest(dict(family=family, seed=seed)),
            worker_config_sha256=digest(WORKER),
            host_policy_sha256=digest(
                dict(
                    policy=host_policy,
                    collection=configuration,
                    native_cap=args.native_cap,
                    sources=fingerprint,
                )
            ),
            criteria_sha256=digest(CRITERIA),
            environment_sha256=backend_hash,
            budget_seconds=650,
        )
        trials = []
        for replicate in range(args.replicates):
            for role in ["sampled", "wait"]:
                identity = [args.order_seed, family, seed, replicate, role]
                if configuration != DEFAULTS:
                    identity.append(configuration)
                name = "episode-" + digest(identity)[:16]
                trials.append(
                    dict(
                        id=name,
                        role=role,
                        replicate=replicate,
                        sampling_seed=int(digest([args.order_seed, name])[:16], 16)
                        if role == "sampled"
                        else None,
                    )
                )
        rng.shuffle(trials)
        blocks.append(
            dict(
                id="configuration-" + str(index + 1),
                family=family,
                seed=seed,
                context=context,
                trials=trials,
            )
        )
    rng.shuffle(blocks)
    result = dict(
        schema="parked-workflow-return-plan/v1",
        split=args.purpose,
        created_at=time.time(),
        blocks=blocks,
        source_files_sha256=fingerprint,
        worker=WORKER,
        host_policy=host_policy,
        collection_settings=configuration,
        native_cap=args.native_cap,
        backend_sha256=backend_hash,
        model_policy=args.model_policy,
        adapter_sha256=args.adapter_sha256,
        temperature=args.temperature,
        decision_distribution=distribution,
        order_seed=args.order_seed,
        scope="Fresh native episodes sharing task configuration; no matched private worker prefix",
        maximum_parallel_workflows=configuration["maximum_parallel_workflows"],
    )
    args.root.mkdir(parents=True, exist_ok=False)
    put(args.root / "PLAN.json", result)
    (args.root / "PLAN.sha256").write_text(file_reference(args.root / "PLAN.json")["sha256"] + "\n")
    return result


def run(args):
    root = args.root.resolve()
    frozen = read(root / "PLAN.json")
    plan_hash = file_reference(root / "PLAN.json")["sha256"]
    if (root / "PLAN.sha256").read_text().strip() != plan_hash or frozen[
        "source_files_sha256"
    ] != sources():
        raise ValueError("Frozen plan or collector sources changed")
    if (root / "CAMPAIGN.json").exists():
        raise ValueError("Campaign already attempted; never restart over recorded outcomes")
    configuration = settings(frozen.get("collection_settings"))
    if (
        frozen["maximum_parallel_workflows"] != configuration["maximum_parallel_workflows"]
        or frozen["host_policy"]["maximum_parent_turns"] != configuration["parent_turn_limit"]
    ):
        raise ValueError("Inconsistent frozen execution settings")
    if file_reference(args.backend)["sha256"] != frozen["backend_sha256"]:
        raise ValueError("Physical backend differs from the frozen environment")
    lease = read(args.budget)
    if any(row.get("ended_at") is None for row in lease["starts"]):
        raise ValueError("Other native work is active")
    if lease["maximum_per_continuation"] != frozen["native_cap"]:
        raise ValueError("Native per-episode cap differs from the planned policy")
    token = args.auth_token_file.read_text().strip()

    def health():
        value = request(args.socket, dict(operation="health", auth_token=token), timeout=30)[
            "status"
        ]
        identity = value.get("model_identities", {}).get(
            frozen["model_policy"], value.get("model_identity")
        )
        if (
            value["stage"] != "ready"
            or frozen["model_policy"] not in value["policies"]
            or value.get("temperature") != frozen["temperature"]
            or value.get("decision_distribution", INDEPENDENT)
            != frozen.get("decision_distribution", INDEPENDENT)
        ):
            raise ValueError("Serving policy or temperature differs from the planned behavior")
        if (
            identity["adapter_files_sha256"]["adapter_model.safetensors"]
            != frozen["adapter_sha256"]
        ):
            raise ValueError("Serving weights differ from the planned behavior adapter")
        return identity

    model_identity = health()
    state = dict(
        stage="collecting",
        started_at=time.time(),
        plan_sha256=plan_hash,
        model_identity=model_identity,
        blocks=[],
    )

    def save():
        put(root / "CAMPAIGN.json", state)

    def one(block, trial):
        result = dict(**trial, started_at=time.time(), plan_sha256=plan_hash)
        put(root / (trial["id"] + "-controller.json"), result | dict(stage="started"))
        deadline = min(time.time() + 750, read(args.budget)["deadline"])
        env = dict(
            os.environ,
            OMP_NUM_THREADS="2",
            OPENBLAS_NUM_THREADS="2",
            SIMJECTURE_PLASMA_BACKEND=str(args.backend.absolute()),
            SIMJECTURE_NATIVE_BUDGET=str(args.budget.absolute()),
            SIMJECTURE_ATTENTION_TOKEN_FILE=str(args.auth_token_file.absolute()),
            SIMJECTURE_CONTINUATION=trial["id"],
            SIMJECTURE_CONTINUATION_DEADLINE=str(deadline),
        )
        command = [
            sys.executable,
            str(SCRIPTS / "scientific_workflow_trials.py"),
            "--root",
            str(root / trial["id"]),
            "--family",
            block["family"],
            "--seed",
            str(block["seed"]),
            "--arm",
            "adapted" if trial["role"] == "sampled" else "observe",
            "--socket",
            str(args.socket.absolute()),
            "--wrapper",
            str(args.wrapper.absolute()),
            "--python",
            str(args.python.absolute()),
            "--plasma-assets",
            str(args.plasma_assets.absolute()),
            "--worker-prompt",
            configuration["worker_prompt"],
            "--parent-turn-limit",
            str(configuration["parent_turn_limit"]),
        ]
        if trial["role"] == "sampled":
            command += [
                "--model-policy",
                frozen["model_policy"],
                "--sampling-seed",
                str(trial["sampling_seed"]),
                "--sampling-split",
                frozen["split"],
                "--decision-distribution",
                frozen.get("decision_distribution", INDEPENDENT),
            ]
        try:
            with (root / (trial["id"] + ".log")).open("w") as log:
                process = subprocess.Popen(
                    command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
                )
                owner = process_stat(process.pid)
                try:
                    result["returncode"] = process.wait(timeout=max(1, deadline - time.time()))
                except subprocess.TimeoutExpired:
                    stop_session(owner)
                    process.wait(timeout=10)
                    raise RuntimeError("Workflow exceeded its resource bound") from None
            result["stage"] = "completed" if result["returncode"] == 0 else "collector_failed"
        except Exception as error:
            result.update(stage="collector_failed", error=type(error).__name__ + ": " + str(error))
        result["ended_at"] = time.time()
        put(root / (trial["id"] + "-controller.json"), result)
        return result

    save()
    previous_end = time.time()
    try:
        for block in frozen["blocks"]:
            lease = read(args.budget)
            count = len(block["trials"])
            if (
                lease["maximum_starts"] - len(lease["starts"]) < count * frozen["native_cap"]
                or time.time() + block_wall_seconds(count, configuration) >= lease["deadline"]
            ):
                state["stop_reason"] = "No full new block fits the existing lease"
                break
            if health() != model_identity:
                raise ValueError("Behavior model changed during the cohort")
            if sources() != frozen["source_files_sha256"]:
                raise ValueError("Collector sources changed during the cohort")
            if file_reference(args.backend)["sha256"] != frozen["backend_sha256"]:
                raise ValueError("Physical backend changed during the cohort")
            record = dict(id=block["id"], started_at=time.time(), results=[])
            state["blocks"].append(record)
            save()
            if configuration["maximum_parallel_workflows"] == 1:
                for trial in block["trials"]:
                    while time.time() < previous_end + configuration["minimum_gap_seconds"]:
                        time.sleep(
                            max(
                                0,
                                min(
                                    1,
                                    previous_end
                                    + configuration["minimum_gap_seconds"]
                                    - time.time(),
                                ),
                            )
                        )
                    if time.time() + 750 >= read(args.budget)["deadline"]:
                        raise TimeoutError("No further assignment fits the existing lease")
                    result = one(block, trial)
                    record["results"].append(result)
                    previous_end = result["ended_at"]
                    save()
                    if result["stage"] != "completed":
                        raise RuntimeError("Collector failure; later assignments remain unstarted")
            else:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=configuration["maximum_parallel_workflows"]
                ) as pool:
                    futures = [pool.submit(one, block, t) for t in block["trials"]]
                    for future in concurrent.futures.as_completed(futures):
                        record["results"].append(future.result())
                        save()
            record["ended_at"] = time.time()
            save()
            if sources() != frozen["source_files_sha256"]:
                raise ValueError("Collector sources changed within a comparison block")
            if file_reference(args.backend)["sha256"] != frozen["backend_sha256"]:
                raise ValueError("Physical backend changed within a comparison block")
            if any(r["stage"] != "completed" for r in record["results"]):
                state["stop_reason"] = "Collector failure; preserve the full started block"
                break
            infrastructure = []
            for _ in range(20):
                if not any(row.get("ended_at") is None for row in read(args.budget)["starts"]):
                    break
                time.sleep(1)
            for trial in block["trials"]:
                directory = root / trial["id"]
                try:
                    require_native_evidence(directory, read(args.budget)["starts"])
                except ValueError:
                    infrastructure.append(dict(id=trial["id"], kind="native_evidence_unconfirmed"))
                errors = directory / "monitor/attention-errors.jsonl"
                if errors.is_file() and errors.read_text().strip():
                    infrastructure.append(dict(id=trial["id"], kind="monitor_error"))
                outcome = directory / "OUTCOME.json"
                if not outcome.is_file() or read(outcome).get("stage") != "completed":
                    infrastructure.append(dict(id=trial["id"], kind="collector_incomplete"))
                for path in (directory / "research/runs").glob("*/receipt.json"):
                    value = read(path)
                    if value.get("status") not in {"succeeded", "failed", "timeout"} or value.get(
                        "transport_status"
                    ) in {"failed", "timeout"}:
                        infrastructure.append(
                            dict(id=trial["id"], kind="unconfirmed_solver_transport")
                        )
            if infrastructure:
                state.update(
                    stop_reason="Infrastructure defect; preserve the started block",
                    infrastructure_failures=infrastructure,
                )
                break
        state.update(
            stage="completed",
            ended_at=time.time(),
            unstarted_blocks=[b["id"] for b in frozen["blocks"][len(state["blocks"]) :]],
        )
    except Exception as error:
        state.update(
            stage="failed", ended_at=time.time(), error=type(error).__name__ + ": " + str(error)
        )
    state["unstarted_episodes"] = [
        trial["id"]
        for block in frozen["blocks"]
        for trial in block["trials"]
        if not (root / (trial["id"] + "-controller.json")).exists()
    ]
    save()
    # Let owned wrapper accounting settle after bounded helper cancellation.
    for _ in range(20):
        if not any(row.get("ended_at") is None for row in read(args.budget)["starts"]):
            break
        time.sleep(1)
    try:
        state["export"] = export(root, root / "receipts", args.budget)
    except Exception as error:
        state["export"] = dict(eligible=False, error=type(error).__name__ + ": " + str(error))
    save()
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    planning = commands.add_parser("plan")
    running = commands.add_parser("run")
    for command in [planning, running]:
        command.add_argument("--root", type=Path, required=True)
    planning.add_argument("--purpose", choices=["train", "commissioning"], default="train")
    planning.add_argument("--family", choices=CASES, action="append", required=True)
    planning.add_argument("--replicates", type=int, default=2)
    planning.add_argument("--configuration-seed", type=int, required=True)
    planning.add_argument("--order-seed", type=int, required=True)
    planning.add_argument("--native-cap", type=int, default=12)
    planning.add_argument("--model-policy", default="adapted")
    planning.add_argument("--adapter-sha256", required=True)
    planning.add_argument("--temperature", type=float, default=3.0)
    planning.add_argument("--decision-distribution", choices=DISTRIBUTIONS, default=INDEPENDENT)
    planning.add_argument("--backend", type=Path, required=True)
    planning.add_argument(
        "--worker-prompt", choices=["inherited", "task_protocol"], default="inherited"
    )
    planning.add_argument("--parent-turn-limit", type=int, choices=range(1, 13), default=4)
    planning.add_argument("--maximum-parallel-workflows", type=int, choices=[1, 2], default=2)
    planning.add_argument("--minimum-gap-seconds", type=float, default=0.0)
    for name in [
        "budget",
        "backend",
        "socket",
        "auth-token-file",
        "wrapper",
        "python",
        "plasma-assets",
    ]:
        running.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(plan(args) if args.mode == "plan" else run(args), indent=2))


if __name__ == "__main__":
    main()
