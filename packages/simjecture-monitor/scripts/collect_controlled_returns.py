"""Collect sampled decisions and independent wait controls in randomized order.

Planning freezes every assignment before any continuation runs. Execution is
off-host orchestration: native workers use the bounded wrapper and physics uses
the configured remote backend. There is no model load or optimizer in this CLI.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from execute_checkpoint_decision import require_confirmed_solver_outcomes
from simjecture_monitor.events import digest, put
from simjecture_monitor.measured_wait import wait_controlled_advantages
from simjecture_monitor.native_guard import process_stat, stop_session
from simjecture_monitor.reward import ContinuationOutcome, RewardWeights, utility

SCRIPTS = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text())


def reference(path):
    return dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Record and checkpoint identifiers must be simple opaque names")
    return value


def assignments(rows, *, repeats, seed):
    if repeats < 2 or not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Require distinct policy samples and at least two wait repetitions")
    grouped = defaultdict(list)
    for row in rows:
        if row.get("split") != "train" or "outcome_receipt" in row:
            raise ValueError("Plan from unexecuted training proposals, never selected outcomes")
        identity(row["id"])
        identity(row["host_checkpoint_id"])
        grouped[row["return_group"]].append(row)
    rng, blocks = random.Random(seed), []
    used = {row["id"] for row in rows}
    for key, group in sorted(grouped.items()):
        if len(group) < 2:
            raise ValueError("Require at least two policy samples for every state")
        if (
            len({row["host_checkpoint_id"] for row in group}) != 1
            or len(
                {
                    digest([r["state"], r["questions"], r["behavior"]["prompt_sha256"]])
                    for r in group
                }
            )
            != 1
        ):
            raise ValueError("A comparison group must contain the same public model input")
        trials = [dict(id=row["id"], kind="sampled") for row in group]
        for repeat in range(repeats):
            # Same opaque namespace as sampled records; branch paths must not
            # announce the treatment to a worker reading its own workspace.
            name = "draw-" + digest([seed, key, repeat])[:16]
            if name in used:
                raise ValueError("Duplicate assigned execution identity")
            used.add(name)
            trials.append(dict(id=name, kind="wait", repetition=repeat))
        rng.shuffle(trials)
        blocks.append(dict(group=key, checkpoint_id=group[0]["host_checkpoint_id"], trials=trials))
    rng.shuffle(blocks)
    return blocks


def source_identity():
    package = SCRIPTS.parent
    return {
        str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
        for folder in [package / "scripts", package / "src"]
        for path in sorted(folder.rglob("*.py"))
    }


def plan(args):
    manifest = read(args.samples / "manifest.json")
    rows = [read(args.samples / (identity(name) + ".json")) for name in manifest["records"]]
    if [row["id"] for row in rows] != manifest["records"]:
        raise ValueError("Sample manifest differs from the referenced proposal identities")
    blocks = assignments(rows, repeats=args.repetitions, seed=args.seed)
    for block in blocks:
        checkpoint = (args.prefixes / block["checkpoint_id"]).resolve()
        block.update(
            checkpoint=str(checkpoint),
            checkpoint_sha256=reference(checkpoint / "checkpoint.json")["sha256"],
            observation_sha256=reference(checkpoint / "observation.json")["sha256"],
        )
    args.root.mkdir(parents=True, exist_ok=False)
    (args.root / "samples").mkdir()
    for row in rows:
        put(args.root / "samples" / (row["id"] + ".json"), row)
    value = dict(
        schema=1,
        created_at=time.time(),
        seed=args.seed,
        repetitions=args.repetitions,
        blocks=blocks,
        source_files_sha256=source_identity(),
        sample_manifest_sha256=reference(args.samples / "manifest.json")["sha256"],
        sample_files_sha256={
            row["id"]: reference(args.root / "samples" / (row["id"] + ".json"))["sha256"]
            for row in rows
        },
        scope="Randomized public-context development continuations; no private worker state",
        baseline="Independent wait controls, excluded from behavior-policy samples",
    )
    put(args.root / "PLAN.json", value)
    (args.root / "PLAN.sha256").write_text(reference(args.root / "PLAN.json")["sha256"] + "\n")
    return value


def wait_receipt(root):
    outcome = ContinuationOutcome.model_validate_json((root / "OUTCOME.json").read_bytes())
    status = read(root / "CONTINUATION.json")
    if status["stage"] != "completed" or outcome.action != "defer":
        raise ValueError("Wait collector did not produce a completed unaided continuation")
    require_confirmed_solver_outcomes(root)
    measured = utility(outcome, RewardWeights())
    return dict(
        source_kind="executed_wait_continuation",
        status="completed",
        verification_sha256=digest(status["quality"]),
        outcome_sha256=reference(root / "OUTCOME.json")["sha256"],
        outcome=outcome.model_dump(),
        solver_outcomes_confirmed=True,
        utility=measured["total"],
        utility_components=measured["components"],
    )


def execute(args):
    root = args.root.resolve()
    frozen = read(root / "PLAN.json")
    if (root / "PLAN.sha256").read_text().strip() != reference(root / "PLAN.json")["sha256"]:
        raise ValueError("Frozen assignment manifest changed")
    if frozen["source_files_sha256"] != source_identity():
        raise ValueError("Collector sources changed after planning")
    for name, expected in frozen["sample_files_sha256"].items():
        if reference(root / "samples" / (identity(name) + ".json"))["sha256"] != expected:
            raise ValueError("Frozen proposal changed")
    for block in frozen["blocks"]:
        for name, key in [
            ("checkpoint.json", "checkpoint_sha256"),
            ("observation.json", "observation_sha256"),
        ]:
            if reference(Path(block["checkpoint"]) / name)["sha256"] != block[key]:
                raise ValueError("Frozen public checkpoint changed")
    if (root / "CAMPAIGN.json").exists():
        raise ValueError(
            "Campaign already attempted; inspect retained receipts instead of restarting"
        )
    lease = read(args.budget)
    if any(row.get("ended_at") is None for row in lease["starts"]):
        raise ValueError("Other native work is active; do not mix timed cohorts")
    status = dict(stage="collecting", started_at=time.time(), blocks=[])
    receipts = root / "receipts"
    receipts.mkdir()
    (root / "continuations").mkdir()

    def save():
        put(root / "CAMPAIGN.json", status)

    def one(block, trial):
        name = trial["id"]
        result = dict(**trial, started_at=time.time())
        deadline = min(time.time() + 750, read(args.budget)["deadline"])
        destination = root / "continuations" / name
        env = dict(
            os.environ,
            OMP_NUM_THREADS="2",
            OPENBLAS_NUM_THREADS="2",
            SIMJECTURE_PLASMA_BACKEND=str(args.backend.resolve()),
            SIMJECTURE_NATIVE_BUDGET=str(args.budget.resolve()),
            SIMJECTURE_CONTINUATION=name,
            SIMJECTURE_CONTINUATION_DEADLINE=str(deadline),
        )
        common = [
            "--root",
            str(destination),
            "--checkpoint",
            block["checkpoint"],
            "--wrapper",
            str(args.wrapper.absolute()),
            "--python",
            str(args.python.absolute()),
            "--plasma-assets",
            str(args.plasma_assets.resolve()),
        ]
        if trial["kind"] == "sampled":
            command = [
                sys.executable,
                str(SCRIPTS / "execute_checkpoint_decision.py"),
                *common,
                "--sample",
                str(root / "samples" / (name + ".json")),
                "--receipts",
                str(receipts),
            ]
        else:
            command = [
                sys.executable,
                str(SCRIPTS / "scientific_counterfactual_trials.py"),
                "continue",
                *common,
                "--action",
                "defer",
                "--replicate",
                block["group"],
            ]
        try:
            with (root / (name + ".log")).open("w") as log:
                process = subprocess.Popen(
                    command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
                )
                owner = process_stat(process.pid)
                try:
                    result["returncode"] = process.wait(timeout=max(1, deadline - time.time()))
                except subprocess.TimeoutExpired:
                    stop_session(owner)
                    process.wait(timeout=10)
                    raise RuntimeError(
                        "Continuation exceeded its recorded resource bound"
                    ) from None
            if result["returncode"]:
                raise RuntimeError("Continuation collector returned a failure")
            if trial["kind"] == "wait":
                put(receipts / (name + "-reward.json"), wait_receipt(destination))
            result.update(stage="completed", receipt=reference(receipts / (name + "-reward.json")))
        except Exception as error:
            result.update(stage="ineligible", error=type(error).__name__ + ": " + str(error))
        result["ended_at"] = time.time()
        put(root / (name + "-controller.json"), result)
        return result

    save()
    try:
        for block in frozen["blocks"]:
            lease = read(args.budget)
            count = len(block["trials"])
            # Reserve enough room for the entire randomized block, without
            # changing its composition after seeing favorable/unfavorable returns.
            if (
                lease["maximum_starts"] - len(lease["starts"])
                < count * lease["maximum_per_continuation"]
                or time.time() + math.ceil(count / args.parallel) * 760 + 60 >= lease["deadline"]
            ):
                status["stop_reason"] = "No complete new comparison block fits the remaining lease"
                break
            record = dict(group=block["group"], started_at=time.time(), results=[])
            status["blocks"].append(record)
            save()
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
                futures = [pool.submit(one, block, trial) for trial in block["trials"]]
                for future in concurrent.futures.as_completed(futures):
                    record["results"].append(future.result())
                    save()
            record["ended_at"] = time.time()
            if any(row["stage"] != "completed" for row in record["results"]):
                status["stop_reason"] = (
                    "Incomplete measured block; preserve all assignments and inspect"
                )
                break
        complete = len(status["blocks"]) == len(frozen["blocks"]) and all(
            len(block["results"]) == len(assigned["trials"])
            and all(row["stage"] == "completed" for row in block["results"])
            for block, assigned in zip(status["blocks"], frozen["blocks"], strict=False)
        )
        status["eligible"] = False
        if complete:
            rows = []
            for block in frozen["blocks"]:
                waits = [
                    reference(receipts / (t["id"] + "-reward.json"))
                    for t in block["trials"]
                    if t["kind"] == "wait"
                ]
                for trial in block["trials"]:
                    if trial["kind"] == "sampled":
                        row = read(receipts / (trial["id"] + "-training.json"))
                        row["wait_outcome_receipts"] = waits
                        rows.append(row)
            # A failed/incomplete cohort never silently becomes a selected training subset.
            (receipts / "train.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
            _, audit = wait_controlled_advantages(rows, receipts)
            put(receipts / "ADVANTAGES.json", audit)
            status.update(eligible=True, training=reference(receipts / "train.jsonl"))
        status["stage"] = "completed"
    except Exception as error:
        status.update(stage="failed", error=type(error).__name__ + ": " + str(error))
    status["ended_at"] = time.time()
    status["unstarted_groups"] = [b["group"] for b in frozen["blocks"][len(status["blocks"]) :]]
    save()
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    planning = commands.add_parser("plan")
    planning.add_argument("--samples", type=Path, required=True)
    planning.add_argument("--prefixes", type=Path, required=True)
    planning.add_argument("--repetitions", type=int, default=2)
    planning.add_argument("--seed", type=int, required=True)
    running = commands.add_parser("run")
    for key in ["budget", "backend", "wrapper", "python", "plasma-assets"]:
        running.add_argument("--" + key, type=Path, required=True)
    running.add_argument("--parallel", type=int, choices=[1, 2], default=2)
    for command in [planning, running]:
        command.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = plan(args) if args.mode == "plan" else execute(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
