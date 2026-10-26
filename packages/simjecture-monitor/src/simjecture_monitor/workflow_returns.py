"""Episode returns for the deployed parked-worker policy, with independent controls.

Episodes share a scientific configuration and host policy, not a private worker
prefix. Controls estimate configuration-level expected waiting value. Every
sampled decision retains the episode advantage; polls are not independent
scientific outcomes and must not inflate the reported evaluation sample size.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from . import attention_support as protocol
from .attention_server import sampled_answers
from .decision_interface import scientific_request
from .measured_wait import read_receipt
from .reward import RewardWeights

CONTEXT_KEYS = {
    "configuration_sha256",
    "worker_config_sha256",
    "host_policy_sha256",
    "criteria_sha256",
    "environment_sha256",
}
CHECKS = {
    "collector_completed",
    "solver_outcomes_confirmed",
    "monitor_coverage_complete",
    "native_invocations_closed",
    "no_recorded_provider_errors",
    "artifact_audit_passed",
}


class WorkflowMeasurements(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    verified_quality: float = Field(ge=0, le=1)
    native_starts: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    required_feedback_misses: int = Field(ge=0)
    duplicate_wakeups: int = Field(ge=0)
    invalid_proposals: int = Field(ge=0)


def workflow_utility(measured):
    measured = WorkflowMeasurements.model_validate(measured)
    weights = RewardWeights()
    components = dict(
        verified_quality=weights.quality * measured.verified_quality,
        native_starts=-weights.agent_start * measured.native_starts,
        elapsed_time=-weights.wall_time * measured.elapsed_seconds / weights.time_scale_seconds,
        required_feedback=-weights.required_feedback_miss * measured.required_feedback_misses,
        duplicate_wakeups=-weights.duplicate_wakeup * measured.duplicate_wakeups,
    )
    # Host-suppressed malformed proposals are recorded but do not get an
    # invented action-to-reward penalty. Any downstream delay/failure is already
    # measured, and language-format rehearsal is a separate supervised target.
    return dict(total=sum(components.values()), components=components)


def validate_episode(episode):
    if (
        episode.get("source_kind") != "executed_parked_workflow"
        or episode.get("status") != "completed"
        or episode.get("role") not in {"sampled", "wait"}
        or episode.get("lifecycle") != "parked_until_terminal_fallback_or_returned_attention/v1"
    ):
        raise ValueError("Require a completed episode of the actual parked-worker lifecycle")
    if any(episode.get("checks", {}).get(key) is not True for key in CHECKS):
        raise ValueError("Incomplete or unconfirmed workflow evidence")
    context = episode["context"]
    if set(context) != CONTEXT_KEYS | {"budget_seconds"}:
        raise ValueError("Workflow context is missing a required comparison binding")
    if any(
        not isinstance(context[k], str) or not re.fullmatch(r"[0-9a-f]{64}", context[k])
        for k in CONTEXT_KEYS
    ):
        raise ValueError("Malformed comparison-context digest")
    if (
        isinstance(context["budget_seconds"], bool)
        or not isinstance(context["budget_seconds"], (int, float))
        or not math.isfinite(context["budget_seconds"])
        or context["budget_seconds"] <= 0
    ):
        raise ValueError("Invalid workflow budget")
    measured = WorkflowMeasurements.model_validate(episode["measurements"])
    calculated = workflow_utility(measured)["total"]
    value = episode["utility"]
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not math.isclose(value, calculated, abs_tol=1e-10, rel_tol=1e-10)
    ):
        raise ValueError("Workflow utility differs from its measured components")
    ids = episode["decision_ids"]
    if len(ids) != len(set(ids)) or episode["requested_decisions"] != len(ids):
        raise ValueError("Missing or duplicate sampled decisions in a workflow")
    if episode["role"] == "wait" and (
        ids or measured.invalid_proposals or episode["automatic_alerts"]
    ):
        raise ValueError("Wait controls cannot contain automatic interventions or policy samples")
    if ids:
        temperature = episode.get("temperature")
        if (
            not episode.get("model_identity")
            or isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(temperature)
            or temperature <= 0
        ):
            raise ValueError("Sampled episodes require a model identity and positive temperature")
    return calculated


def workflow_advantages(rows, root):
    """Validate the complete frozen cohort, then assign episode-level advantages.

    A common return for all decisions is the episodic likelihood-ratio signal.
    The optimizer rescales its row average by decision rows / sampled episodes,
    including zero-opportunity episodes. It must not divide each episode by its
    own poll count or treat polls as independent scientific outcomes.
    This is an episodic clipped-policy update, not a collection of independent
    contextual-bandit outcomes or a paired private-state counterfactual.
    """
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Require distinct sampled training rows")
    manifest_ref = rows[0]["episode_manifest"]
    if any(
        row.get("split") != "train" or row.get("episode_manifest") != manifest_ref for row in rows
    ):
        raise ValueError("All rows must reference the same complete training episode manifest")
    manifest = read_receipt(root, manifest_ref)
    if manifest.get("schema") != "parked-workflow-return-dataset/v1":
        raise ValueError("Unknown episode return dataset")
    plan = read_receipt(root, manifest["plan"])
    if plan.get("split") != "train" or plan.get("schema") != "parked-workflow-return-plan/v1":
        raise ValueError("Require the frozen training-only workflow plan")
    planned, groups = {}, {}
    for block in plan["blocks"]:
        key = block["id"]
        if key in groups:
            raise ValueError("Duplicate configuration block")
        groups[key] = block
        for trial in block["trials"]:
            if trial["id"] in planned or trial["role"] not in {"sampled", "wait"}:
                raise ValueError("Invalid or duplicate planned episode")
            planned[trial["id"]] = dict(block=key, role=trial["role"], context=block["context"])
    episodes, values = {}, {}
    for reference in manifest["episodes"]:
        episode = read_receipt(root, reference)
        identity = episode["id"]
        if identity in episodes or identity not in planned:
            raise ValueError("Unexpected or duplicate episode receipt")
        assigned = planned[identity]
        if (
            episode["role"] != assigned["role"]
            or episode["context"] != assigned["context"]
            or episode["plan_sha256"] != manifest["plan"]["sha256"]
        ):
            raise ValueError("Episode differs from its prospective assignment")
        values[identity] = validate_episode(episode)
        if episode["decision_ids"] and (
            episode["model_identity"] != manifest["model_identity"]
            or episode["temperature"] != plan["temperature"]
        ):
            raise ValueError("Behavior changed across the frozen episode cohort")
        episodes[identity] = episode
    if set(episodes) != set(planned):
        raise ValueError("The assigned cohort is incomplete; do not select completed outcomes")
    expected_rows = {name for episode in episodes.values() for name in episode["decision_ids"]}
    if sum(len(e["decision_ids"]) for e in episodes.values()) != len(
        expected_rows
    ) or expected_rows != {row["id"] for row in rows}:
        raise ValueError("Training must retain every sampled decision from the cohort")
    invalid, rows_by_episode = defaultdict(int), defaultdict(list)
    for row in rows:
        episode = episodes.get(row["episode_id"])
        if (
            episode is None
            or episode["role"] != "sampled"
            or row["id"] not in episode["decision_ids"]
        ):
            raise ValueError("Training row is not an assigned sampled episode decision")
        record = read_receipt(root, row["decision_receipt"])
        result, behavior = record["result"], row["behavior"]
        if record["submitted"] != row["observation"] or result.get("behavior") != behavior:
            raise ValueError("Training behavior or observation differs from its live decision")
        packet = protocol.Observation.model_validate(record["submitted"])
        view = protocol.PackedView.model_validate(result["view"])
        rendered = scientific_request(packet, view)
        if (row["state"], row["questions"]) != (
            rendered["state"],
            rendered["questions"],
        ) or packet.worker_state != "parked":
            raise ValueError("Training input is not the actual parked-state observation")
        if (
            behavior["prompt_sha256"] != result["input_prompt_sha256"]
            or behavior.get("model_identity") != episode["model_identity"]
            or behavior.get("temperature") != episode["temperature"]
        ):
            raise ValueError("Behavior input, temperature or model identity mismatch")
        answers, logp = sampled_answers(behavior["probabilities"], behavior["seed"])
        if (
            answers != behavior["sampled_answers"]
            or answers != {key: target["label"] for key, target in row["targets"].items()}
            or not math.isclose(
                logp, behavior["sampled_joint_log_probability"], abs_tol=1e-10, rel_tol=1e-10
            )
        ):
            raise ValueError("Decision was not drawn from the recorded behavior distribution")
        invalid[episode["id"]] += result["decision"]["status"] == "inference_error"
        rows_by_episode[episode["id"]].append(row)
    result, audit = {}, {}
    for key, block in groups.items():
        waits = [t["id"] for t in block["trials"] if t["role"] == "wait"]
        sampled = [t["id"] for t in block["trials"] if t["role"] == "sampled"]
        if len(waits) < 2 or len(sampled) < 2:
            raise ValueError(
                "Require at least two independent wait and policy episodes per configuration"
            )
        wait_mean = sum(values[name] for name in waits) / len(waits)
        samples = []
        for name in sampled:
            episode = episodes[name]
            if invalid[name] != episode["measurements"]["invalid_proposals"]:
                raise ValueError("Invalid-proposal cost differs from the actual logged decisions")
            advantage = values[name] - wait_mean
            for row in rows_by_episode[name]:
                result[row["id"]] = advantage
            samples.append(
                dict(
                    episode=name,
                    decisions=len(rows_by_episode[name]),
                    utility=values[name],
                    advantage=advantage,
                )
            )
        audit[key] = dict(
            wait_episodes=waits,
            wait_utilities=[values[name] for name in waits],
            wait_mean=wait_mean,
            sampled_episodes=samples,
        )
    if not result or max(map(abs, result.values())) < 1e-8:
        raise ValueError("No measured episodic advantage; skip the RL update")
    return result, audit
