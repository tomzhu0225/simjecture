"""Qualification requirements for prospective scientific workflow controls.

This commissioning set tests integration, not model effectiveness. It neither
loads a model nor authorizes execution before the original comparison finishes.
"""

from __future__ import annotations

import hashlib
import random
import re

SCHEMA = "scientific-attention-control-commission/v1"
CASES = ("progressing_work", "unit_conversion", "source_binding")
ARMS = ("observe", "routine_help")
PROMPT_SOURCE = "packages/simjecture-monitor/src/simjecture_monitor/workflow_prompt.py"
SOURCE_FILES = (
    PROMPT_SOURCE,
    "packages/simjecture-monitor/src/simjecture_monitor/routine_help.py",
    "packages/simjecture-monitor/scripts/scientific_workflow_trials.py",
    "packages/simjecture-monitor/scripts/generalization_trials.py",
    "packages/simjecture-monitor/scripts/generalization_fixture.py",
    "packages/simjecture-monitor/scripts/audit_scientific_workflows.py",
)
TOOL_FILES = (
    "scripts/plan_control_commission.py",
    "scripts/run_control_commission.py",
    "scripts/audit_control_commission.py",
    "src/simjecture_monitor/control_commission.py",
)


def check_tool_hashes(package, hashes):
    if set(hashes) != set(TOOL_FILES):
        raise ValueError("Require all commissioning tool identities")
    for name, expected in hashes.items():
        if hashlib.sha256((package / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Commissioning tool differs from registration: " + name)


def plan(source_revision, source_hashes, *, seed=202610271031, parent_turn_limit=4):
    if type(parent_turn_limit) is not int or not 1 <= parent_turn_limit <= 12:
        raise ValueError("Parent-turn limit must be an integer from 1 to 12")
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ValueError("Pin a complete source commit")
    if not set(SOURCE_FILES) <= set(source_hashes) or any(
        not re.fullmatch(r"[0-9a-f]{64}", value) for value in source_hashes.values()
    ):
        raise ValueError("Require hashes of all control and execution sources")
    blocks = []
    for index, family in enumerate(CASES):
        arms = ARMS if index % 2 == 0 else tuple(reversed(ARMS))
        trials = []
        for arm in arms:
            key = f"{SCHEMA}:{source_revision}:{seed}:{family}:{arm}"
            if parent_turn_limit != 4:
                key += f":parent-turn-limit={parent_turn_limit}"
            trials.append(
                dict(
                    id="ctl-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                    family=family,
                    seed=seed + index,
                    repeat=0,
                    arm=arm,
                    worker_prompt="task_protocol",
                )
            )
        blocks.append(dict(id=f"control-{index + 1:02d}", family=family, trials=trials))
    random.Random(seed).shuffle(blocks)
    return dict(
        schema=SCHEMA,
        purpose="Integration commissioning; no model-effect estimate or training targets",
        source_revision=source_revision,
        source_files_sha256=source_hashes,
        seed=seed,
        arms=list(ARMS),
        blocks=blocks,
        workflows=6,
        parent_turn_limit=parent_turn_limit,
        decision_model_calls=0,
        optimizer_updates=0,
        execution_started=False,
        resource_bounds=dict(
            wall_seconds=7200,
            native_starts=73,
            authentication_preflight_starts=1,
            starts_per_workflow=12,
            concurrent_native_roles=6,
            concurrent_workflows=1,
            controller_seconds_per_workflow=750,
            minimum_gap_seconds=90,
        ),
        prerequisites=[
            "Original comparison has all assigned outcomes and no audit violations",
            "Original native roles have all closed and its owned GPU is released",
            "Fresh native authentication and physics checks pass before new assignments",
        ],
    )


def check_predecessor(summary, guard, budget):
    """Do not confuse a terminal partial phase with a completed comparison."""
    primary = summary["primary_all_attempts"]
    if (
        primary.get("complete_design") is not True
        or primary.get("planned", 0) <= 0
        or primary.get("started") != primary.get("planned")
        or primary.get("unstarted")
        or primary.get("audit_violations") != []
    ):
        raise ValueError("Original comparison is incomplete or has audit violations")
    if guard.get("stage") != "released":
        raise ValueError("Original owned model runtime is not released")
    if any(start.get("ended_at") is None for start in budget["starts"]):
        raise ValueError("Original native roles remain active")


def check_audited_subset(plan_value, selected, records):
    """Audit attempted IDs without inventing outcomes for unstarted assignments."""
    if selected != plan_value | dict(blocks=selected["blocks"], workflows=selected["workflows"]):
        raise ValueError("Selected audit manifest changed the commissioning protocol")
    planned = {t["id"]: (b["id"], t) for b in plan_value["blocks"] for t in b["trials"]}
    selected_ids = []
    for block in selected["blocks"]:
        for trial in block["trials"]:
            if planned.get(trial["id"]) != (block["id"], trial):
                raise ValueError("Selected audit manifest changed an assignment")
            selected_ids.append(trial["id"])
    if (
        len(selected_ids) != selected["workflows"]
        or len(set(selected_ids)) != len(selected_ids)
        or len(records) != len(selected_ids)
        or {row["id"] for row in records} != set(selected_ids)
    ):
        raise ValueError("Selected audit coverage differs from attempted records")


def audit(plan_value, records, evidence, *, audit_violations):
    """Add prompt and exercised-path checks to the ordinary workflow audit.

    Records must come from the pinned workflow auditor. Evidence is read from
    each actual trial directory, not supplied by a worker as a pass/fail label.
    Missing paths remain missing; a proposal never counts as an expert dispatch.
    """
    planned = {t["id"]: t for b in plan_value["blocks"] for t in b["trials"]}
    if len(planned) != plan_value["workflows"] or len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate or inconsistent commission assignments")
    if any(r["id"] not in planned for r in records) or set(evidence) != {r["id"] for r in records}:
        raise ValueError("Unassigned or missing trial evidence")
    problems = list(audit_violations)
    returned_help = False
    authorized_repair = False
    routine_dispatch = False
    extended_parent_return = False
    parent_turn_limit = plan_value.get("parent_turn_limit", 4)
    for row in records:
        identity = row["id"]
        trial, files = planned[identity], evidence[identity]
        if any(row.get(key) != trial[key] for key in ("family", "seed", "arm")):
            problems.append([identity, "assignment_mismatch"])
        if row.get("whole_workflow_verified") != 1:
            problems.append([identity, "workflow_not_verified"])
        if parent_turn_limit != 4:
            count = files.get("parent_turn_count")
            if (
                files.get("parent_turn_limit") != parent_turn_limit
                or type(count) is not int
                or not 0 < count <= parent_turn_limit
            ):
                problems.append([identity, "parent_turn_limit_not_verified"])
            elif count > 4:
                extended_parent_return = True
        receipt = files.get("prompt_receipt") or {}
        task = files.get("task_protocol")
        if (
            receipt.get("mode") != trial["worker_prompt"]
            or not isinstance(task, str)
            or receipt.get("task_sha256") != hashlib.sha256(task.encode()).hexdigest()
            or receipt.get("renderer_sha256") != plan_value["source_files_sha256"][PROMPT_SOURCE]
        ):
            problems.append([identity, "prompt_control_not_verified"])
        count = row.get("automatic_alerts")
        if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 1:
            problems.append([identity, "automatic_dispatch_allowance_not_verified"])
        elif trial["arm"] == "observe" and count:
            problems.append([identity, "worker_only_arm_dispatched_automatic_help"])
        elif trial["arm"] == "routine_help" and count == 1:
            routine_dispatch = True
        if row.get("monitor_error_count") != 0:
            problems.append([identity, "monitor_errors_or_missing_error_accounting"])
        if row.get("required_feedback_misses") != 0:
            problems.append([identity, "required_feedback_not_reconciled"])
        for feedback in files.get("feedback", []):
            if (
                feedback.get("id", "").startswith("help_")
                and feedback.get("result")
                and feedback.get("acknowledgment") is not None
            ):
                returned_help = True
        for repair in files.get("authority_results", []):
            if (
                trial["family"] == "source_binding"
                and repair.get("stage") == "completed"
                and repair.get("verdict", {}).get("decision") == "grant"
                and repair.get("deployment", {}).get("status") == "applied"
            ):
                authorized_repair = True
    exercised = dict(
        routine_expert_dispatch=routine_dispatch,
        help_return_acknowledged=returned_help,
        judge_authorized_protected_repair=authorized_repair,
    )
    if parent_turn_limit != 4:
        exercised["resumption_after_four_turns"] = extended_parent_return
    missing = [identity for identity in planned if identity not in {r["id"] for r in records}]
    return dict(
        schema=SCHEMA,
        commissioned=not problems and not missing and all(exercised.values()),
        attempted=len(records),
        unstarted=missing,
        violations=problems,
        exercised=exercised,
        interpretation=(
            "Integration evidence only; unsupported-alert rate and model benefit unmeasured"
        ),
        eligible_for_optimizer=False,
    )
