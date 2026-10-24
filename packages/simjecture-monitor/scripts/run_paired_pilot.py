"""Freeze and run bounded, randomized continuation pairs with retained failures."""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from paired_continuations import CASES, CRITERIA, DOWNSTREAM, WORKER
from simjecture_monitor.events import digest, put
from simjecture_monitor.reward import ContinuationOutcome, paired_reward


def load(path):
    return json.loads(Path(path).read_text())


def design(root):
    if (root / "DESIGN.json").exists():
        return load(root / "DESIGN.json")
    rng = random.Random(2026102401)
    cases = []
    for kind, action in CASES:
        row = dict(
            kind=kind,
            intervention=action,
            prefix="trial-" + uuid.uuid4().hex,
            checkpoint="checkpoint-" + uuid.uuid4().hex,
            pairs=[],
        )
        for repeat in range(2):
            branches = [dict(action=a, root="trial-" + uuid.uuid4().hex) for a in (action, "defer")]
            rng.shuffle(branches)
            row["pairs"].append(dict(id=uuid.uuid4().hex, repeat=repeat, branches=branches))
        cases.append(row)
    result = dict(
        created_at=time.time(),
        cases=cases,
        worker=WORKER,
        downstream_policy=DOWNSTREAM,
        criteria=CRITERIA,
        parent_continuations=32,
        prefix_workers=8,
        route_selection="Prespecified from checkpoint public-evidence templates before outcomes",
        replay=(
            "Fresh native sessions on matched public transcript/artifacts, not private state forks"
        ),
        randomized_branch_order_seed=2026102401,
        optimizer_eligibility="Prespecified actions are not on-policy PPO samples",
        limitations=[
            "Small injected-defect engineering study; not a model-effectiveness trial",
            "Concurrent local GPU workload and native provider stochasticity remain",
            "Duplicates count concurrent identical routes or repeated judges "
            "for an unchanged repaired adapter",
            "No long-duration healthy or hidden native-state cloning claim",
        ],
        limits=dict(
            parent_concurrency=2,
            native_concurrency=4,
            native_starts=240,
            starts_per_continuation=12,
            simulations_per_workspace=4,
            maximum_colab_units=40,
            maximum_colab_hours=3,
        ),
        source_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    )
    result["design_sha256"] = digest(result)
    put(root / "DESIGN.json", result)
    return result


def execute(root, trial, checkpoint, mode, **kwargs):
    output = root / trial
    marker = output / ("PREFIX.json" if mode == "prefix" else "OUTCOME.json")
    if marker.exists() and (mode != "prefix" or load(marker).get("stage") == "completed"):
        return dict(root=trial, resumed_completed=True)
    if output.exists():
        return dict(root=trial, skipped_existing_incomplete=True)
    command = [
        sys.executable,
        "-u",
        str(Path(__file__).with_name("paired_continuations.py")),
        mode,
        "--root",
        str(output),
        "--checkpoint",
        str(root / checkpoint),
        "--wrapper",
        str(root / "native-codex"),
    ]
    for key, value in kwargs.items():
        command += ["--" + key, str(value)]
    duration = 500 if mode == "prefix" else 680
    env = dict(
        os.environ,
        SIMJECTURE_NATIVE_BUDGET=str(root / "native-budget.json"),
        SIMJECTURE_CONTINUATION=trial,
        SIMJECTURE_CONTINUATION_DEADLINE=str(time.time() + duration),
    )
    started = time.time()
    with (root / (trial + ".log")).open("w") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
        put(
            root / (trial + "-controller.json"),
            dict(pid=process.pid, started_at=started, command=command),
        )
        try:
            code = process.wait(timeout=duration + 90)
        except subprocess.TimeoutExpired:
            # Main native roles have their own identity-bound deadline leases.
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            code = 124
    row = dict(
        root=trial,
        mode=mode,
        returncode=code,
        started_at=started,
        ended_at=time.time(),
        outcome_present=marker.exists(),
    )
    put(root / (trial + "-exit.json"), row)
    print(json.dumps(row), flush=True)
    return row


def pair(root, case, spec):
    result = dict(id=spec["id"], kind=case["kind"], branches=[])
    if not (root / case["checkpoint"] / "checkpoint.json").is_file():
        result["error"] = "missing_checkpoint"
        return result
    for branch in spec["branches"]:
        result["branches"].append(
            execute(
                root,
                branch["root"],
                case["checkpoint"],
                "continue",
                action=branch["action"],
                replicate=spec["id"],
            )
        )
    outcomes = []
    for branch in spec["branches"]:
        path = root / branch["root"] / "OUTCOME.json"
        if path.is_file():
            outcomes.append(ContinuationOutcome.model_validate(load(path)))
    intervention = next((o for o in outcomes if o.action != "defer"), None)
    waiting = next((o for o in outcomes if o.action == "defer"), None)
    result["score"] = (
        paired_reward(intervention, waiting)
        if intervention
        else dict(eligible=False, reason="missing_intervention")
    )
    put(root / ("pair-" + spec["id"] + ".json"), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["design", "prefixes", "collect"])
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(exist_ok=True)
    protocol = design(root)
    if args.mode == "design":
        return
    results = []
    if args.mode == "prefixes":
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(execute, root, c["prefix"], c["checkpoint"], "prefix", kind=c["kind"])
                for c in protocol["cases"]
            ]
            for future in as_completed(futures):
                results.append(future.result())
                put(root / "PREFIX_PROGRESS.json", dict(completed=len(results), results=results))
    else:
        if not (root / "COMMISSIONING_PASS.json").is_file():
            raise ValueError("Commissioning must pass before cohort continuation collection")
        pairs = [(case, spec) for case in protocol["cases"] for spec in case["pairs"]]
        random.Random(2026102402).shuffle(pairs)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(pair, root, case, spec) for case, spec in pairs]
            for future in as_completed(futures):
                results.append(future.result())
                put(root / "PAIR_PROGRESS.json", dict(completed=len(results), results=results))
    put(root / ("PREFIXES.json" if args.mode == "prefixes" else "PAIRS.json"), results)


if __name__ == "__main__":
    main()
