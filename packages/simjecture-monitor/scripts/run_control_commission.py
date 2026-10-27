"""Run the bounded control commission after the original comparison is audited.

Runs on the scientific coordinator with its configured native-worker provider
and SSH physics backend. It does not allocate a GPU or load a decision model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

from simjecture_monitor.control_commission import ARMS, SCHEMA, check_predecessor, check_tool_hashes
from simjecture_monitor.native_guard import process_stat, stop_session


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in [
        "plan",
        "root",
        "source",
        "python",
        "codex",
        "backend",
        "plasma-assets",
        "physics-qualification",
        "predecessor-summary",
        "predecessor-guard",
        "predecessor-budget",
    ]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    for name, value in vars(args).items():
        # Preserve the virtualenv interpreter's symlink path.
        if isinstance(value, Path):
            setattr(args, name, value.absolute())
    plan = read(args.plan)
    if (
        plan["schema"] != SCHEMA
        or plan["arms"] != list(ARMS)
        or not plan.get("source_archive_sha256")
    ):
        raise ValueError("Require the registered non-model commissioning arms")
    check_predecessor(
        read(args.predecessor_summary), read(args.predecessor_guard), read(args.predecessor_budget)
    )
    check_tool_hashes(Path(__file__).parents[1], plan["commissioning_tools_sha256"])
    for name, expected in plan["source_files_sha256"].items():
        if sha(args.source / name) != expected:
            raise ValueError("Control source differs from registration: " + name)
    qualification = read(args.physics_qualification)
    if (
        qualification["stage"] != "completed"
        or not 0 <= time.time() - qualification["ended_at"] <= 900
        or qualification["backend_sha256"] != sha(args.backend)
        or {(row["cells"], row["steps"]) for row in qualification["cases"]} != {(64, 40), (128, 80)}
        or not all(row["measured"]["original_checks_passed"] for row in qualification["cases"])
    ):
        raise ValueError("Require fresh matched physics qualification of this backend")
    args.root.mkdir(parents=True, exist_ok=False)
    (args.root / "PLAN.json").write_bytes(args.plan.read_bytes())
    bounds = plan["resource_bounds"]
    started = time.time()
    deadline = started + bounds["wall_seconds"]
    budget_path = args.root / "native-budget.json"
    budget_path.write_text(
        json.dumps(
            dict(
                deadline=deadline,
                maximum_starts=bounds["native_starts"],
                maximum_per_continuation=bounds["starts_per_workflow"],
                maximum_concurrent=bounds["concurrent_native_roles"],
                executable=str(args.codex),
                starts=[],
            ),
            indent=2,
        )
    )
    state = dict(stage="authenticating", started_at=started, blocks=[])

    def save():
        temporary = args.root / "CAMPAIGN.tmp"
        temporary.write_text(json.dumps(state, indent=2))
        temporary.replace(args.root / "CAMPAIGN.json")

    env = dict(
        os.environ,
        PYTHONPATH=str(args.source / "src")
        + ":"
        + str(args.source / "packages/simjecture-monitor/src"),
        SIMJECTURE_NATIVE_BUDGET=str(budget_path.resolve()),
        SIMJECTURE_PLASMA_BACKEND=str(args.backend.resolve()),
        OMP_NUM_THREADS="2",
        OPENBLAS_NUM_THREADS="2",
    )
    wrapper = args.root / "native-codex"
    wrapper.write_text(
        "#!" + str(args.python) + "\nfrom simjecture_monitor.native_guard import main\nmain()\n"
    )
    wrapper.chmod(0o700)
    inputs = [
        args.plan,
        args.backend,
        args.physics_qualification,
        args.predecessor_summary,
        args.predecessor_guard,
        args.predecessor_budget,
        Path(__file__),
    ]
    (args.root / "EXECUTION.json").write_text(
        json.dumps(
            dict(
                deadline=deadline,
                inputs_sha256={str(p.resolve()): sha(p) for p in inputs},
                decision_model_calls=0,
                scope="Separate integration commission; no checkpoint updates",
            ),
            indent=2,
        )
    )

    def execute(command, log_root, trial_id, seconds, prompt=None):
        child_env = dict(
            env,
            SIMJECTURE_CONTINUATION=trial_id,
            SIMJECTURE_CONTINUATION_DEADLINE=str(min(deadline, time.time() + seconds)),
        )
        with (
            (log_root / "stdout.log").open("wb") as output,
            (log_root / "stderr.log").open("wb") as error,
        ):
            child = subprocess.Popen(
                command,
                cwd=log_root,
                env=child_env,
                stdin=subprocess.PIPE,
                stdout=output,
                stderr=error,
                start_new_session=True,
            )
            owner = process_stat(child.pid)
            try:
                child.communicate(prompt, timeout=max(1, min(seconds, deadline - time.time())))
            except subprocess.TimeoutExpired:
                pass
            finally:
                if child.poll() is None:
                    stop_session(owner)
                    child.wait(timeout=10)
            return child.returncode

    save()
    try:
        auth = args.root / "authentication"
        auth.mkdir()
        auth_started = time.time()
        result = execute(
            [
                str(wrapper.resolve()),
                "exec",
                "--ephemeral",
                "--json",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--model",
                "gpt-6-astra",
                "-c",
                'model_reasoning_effort="high"',
                "-c",
                "features.shell_tool=false",
                "-c",
                "features.unified_exec=false",
                "-c",
                'web_search="disabled"',
                "--output-last-message",
                str((auth / "last.txt").resolve()),
                "-",
            ],
            auth,
            "control-authentication",
            330,
            b"Return exactly READY. Do not use tools. This is an authentication preflight.",
        )
        ready = (auth / "last.txt").is_file() and (auth / "last.txt").read_text().strip() == "READY"
        (auth / "EXECUTION.json").write_text(
            json.dumps(
                dict(
                    started_at=auth_started,
                    ended_at=time.time(),
                    returncode=result,
                    expected_response_matches=ready,
                ),
                indent=2,
            )
        )
        if result != 0 or not ready:
            raise RuntimeError("Native authentication failed; no scientific assignment started")
        previous_end = time.time()
        state["stage"] = "collecting"
        save()
        for block in plan["blocks"]:
            selected = dict(id=block["id"], started_at=time.time(), trials=[])
            state["blocks"].append(selected)
            for trial in block["trials"]:
                wait = previous_end + bounds["minimum_gap_seconds"] - time.time()
                while wait > 0:
                    time.sleep(min(1, wait))
                    wait = previous_end + bounds["minimum_gap_seconds"] - time.time()
                if time.time() + bounds["controller_seconds_per_workflow"] >= deadline:
                    raise TimeoutError("No new assignment fits; remaining IDs stay unstarted")
                logs = args.root / (trial["id"] + "-controller")
                logs.mkdir()
                root = args.root / trial["id"]
                receipt = dict(**trial, started_at=time.time(), controller_exit=None, outcome={})
                marker = dict(id=trial["id"], arm=trial["arm"], started_at=receipt["started_at"])
                selected["trials"].append(marker)
                receipt_path = args.root / (trial["id"] + "-receipt.json")
                receipt_path.write_text(json.dumps(receipt, indent=2))
                save()  # Reserve the attempted ID before process launch or any fallible parsing.
                command = [
                    str(args.python),
                    str(
                        args.source
                        / "packages/simjecture-monitor/scripts/scientific_workflow_trials.py"
                    ),
                    "--root",
                    str(root.resolve()),
                    "--family",
                    trial["family"],
                    "--arm",
                    trial["arm"],
                    "--seed",
                    str(trial["seed"]),
                    "--worker-prompt",
                    trial["worker_prompt"],
                    "--socket",
                    str((args.root / "no-decision-model.sock").resolve()),
                    "--wrapper",
                    str(wrapper.resolve()),
                    "--python",
                    str(args.python),
                    "--plasma-assets",
                    str(args.plasma_assets.resolve()),
                ]
                if plan.get("parent_turn_limit", 4) != 4:
                    command += ["--parent-turn-limit", str(plan["parent_turn_limit"])]
                try:
                    receipt["controller_exit"] = execute(
                        command, logs, trial["id"], bounds["controller_seconds_per_workflow"]
                    )
                    outcome = root / "OUTCOME.json"
                    receipt["outcome"] = read(outcome) if outcome.is_file() else {}
                finally:
                    receipt["ended_at"] = previous_end = time.time()
                    marker["ended_at"] = previous_end
                    receipt_path.write_text(json.dumps(receipt, indent=2))
                    save()
                if receipt["controller_exit"] != 0 or not receipt["outcome"].get(
                    "verified_complete"
                ):
                    raise RuntimeError(
                        "Commissioning assignment unsuccessful; preserve it before diagnosis"
                    )
            selected["ended_at"] = time.time()
            save()
        state.update(stage="completed", ended_at=time.time())
    except Exception:
        state.update(stage="failed", error=traceback.format_exc(), ended_at=time.time())
    finally:
        save()
    attempted = {trial["id"] for block in state["blocks"] for trial in block["trials"]}
    finalization = dict(
        stage="unstarted",
        attempted=len(attempted),
        unstarted=[
            trial["id"]
            for block in plan["blocks"]
            for trial in block["trials"]
            if trial["id"] not in attempted
        ],
    )
    if attempted:
        blocks = [
            block | dict(trials=[trial for trial in block["trials"] if trial["id"] in attempted])
            for block in plan["blocks"]
            if any(trial["id"] in attempted for trial in block["trials"])
        ]
        selected = args.root / "STARTED.json"
        selected.write_text(
            json.dumps(plan | dict(blocks=blocks, workflows=len(attempted)), indent=2)
        )
        ordinary = args.root / "workflow-audit"
        commands = [
            (
                [
                    str(args.python),
                    str(
                        args.source
                        / "packages/simjecture-monitor/scripts/audit_scientific_workflows.py"
                    ),
                    "--root",
                    str(args.root),
                    "--manifest",
                    str(selected),
                    "--budget",
                    str(budget_path),
                    "--output",
                    str(ordinary),
                    "--arm",
                    "observe",
                    "--arm",
                    "routine_help",
                    "--learned-arm",
                    "routine_help",
                ],
                env,
            ),
            (
                [
                    sys.executable,
                    str(Path(__file__).with_name("audit_control_commission.py")),
                    "--plan",
                    str(args.root / "PLAN.json"),
                    "--audited-manifest",
                    str(selected),
                    "--campaign",
                    str(args.root),
                    "--workflow-audit",
                    str(ordinary),
                    "--source",
                    str(args.source),
                    "--output",
                    str(args.root / "COMMISSION.json"),
                ],
                os.environ.copy(),
            ),
        ]
        finalization["audit_returncodes"] = []
        for index, (command, audit_env) in enumerate(commands):
            try:
                with (args.root / f"audit-{index}.log").open("w") as log:
                    result = subprocess.run(
                        command, env=audit_env, stdout=log, stderr=subprocess.STDOUT, timeout=120
                    )
            except Exception:
                finalization["error"] = traceback.format_exc()
                finalization["audit_returncodes"].append(None)
                break
            finalization["audit_returncodes"].append(result.returncode)
            if result.returncode:
                break
        finalization["stage"] = (
            "qualified" if finalization["audit_returncodes"] == [0, 0] else "incomplete"
        )
    (args.root / "FINALIZATION.json").write_text(json.dumps(finalization, indent=2))
    print(json.dumps(dict(campaign=state, finalization=finalization)))
    if finalization["stage"] != "qualified":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
