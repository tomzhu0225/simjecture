"""Strict student observations and auditable research decisions."""

from __future__ import annotations

import hashlib
import json
import math

TASK_FIELDS = (
    "task_id",
    "question",
    "equations",
    "initial_boundary_conditions",
    "initial_parameter_configuration",
    "parameter_space",
    "hypotheses",
    "observables",
    "solver_candidates",
    "total_wall_seconds",
    "scope_statement",
    "perturbation_seed",
)
STATE_FIELDS = (
    "schema_version",
    "task_contract",
    "hypotheses",
    "physical_models",
    "available_resources",
    "completed_receipts",
    "verified_evidence",
    "necessary_history",
    "remaining_wall_seconds",
    "observed_at",
)
PRIVATE_KEYS = {
    "hidden_evaluator",
    "reference_answer",
    "hidden_answer",
    "review_score",
    "review_scores",
    "reward",
    "process_reward",
    "terminal_reward",
    "C_score",
    "D_score",
    "chain_of_thought",
    "private_reasoning",
    "future_results",
    "validation_seed",
    "future_configurations",
    "reference_contract",
}
DECISION_COMPONENTS = ("experiment_selection", "organization", "parameters", "model_hierarchy", "scale")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def reject_private_fields(value):
    if isinstance(value, dict):
        forbidden = PRIVATE_KEYS.intersection(value)
        if forbidden:
            raise ValueError(f"Private evaluation fields in student input: {sorted(forbidden)}")
        for item in value.values():
            reject_private_fields(item)
    elif isinstance(value, list):
        for item in value:
            reject_private_fields(item)


def observation(
    *,
    task,
    hypotheses,
    physical_models,
    available_resources,
    completed_receipts,
    verified_evidence,
    necessary_history,
    remaining_wall_seconds,
    observed_at,
):
    if not math.isfinite(remaining_wall_seconds) or remaining_wall_seconds < 0:
        raise ValueError("Remaining budget must be a nonnegative finite host value")
    for receipt in completed_receipts:
        if receipt["finished_at"] > observed_at:
            raise ValueError("A future result cannot enter the observation")
        if receipt["status"] not in {"succeeded", "failed", "cancelled", "timed_out", "partial"}:
            raise ValueError("Only actual terminal or partial execution receipts are observations")
    state = dict(
        schema_version="research-decision/1",
        task_contract={k: task[k] for k in TASK_FIELDS if k in task},
        hypotheses=hypotheses,
        physical_models=physical_models,
        available_resources=available_resources,
        completed_receipts=completed_receipts,
        verified_evidence=verified_evidence,
        necessary_history=necessary_history,
        remaining_wall_seconds=remaining_wall_seconds,
        observed_at=observed_at,
    )
    reject_private_fields(state)
    return state


def decision_audit(
    *,
    study_id,
    decision_id,
    state,
    original_advice,
    executed_plan,
    component_sources,
    override_reasons,
    host_model="gpt-6.1-sol",
):
    if set(component_sources) != set(DECISION_COMPONENTS):
        raise ValueError("Every decision component requires an attribution source")
    for component, source in component_sources.items():
        if source not in {"student", "modified", "host", "unused"}:
            raise ValueError("Unknown component source")
        if source in {"modified", "host"} and not override_reasons.get(component):
            raise ValueError("Host changes require a concrete recorded reason")
    retained = [key for key, value in component_sources.items() if value == "student"]
    if retained and original_advice is None:
        raise ValueError("Student credit requires an actual recorded student suggestion")
    return dict(
        study_id=study_id,
        decision_id=decision_id,
        observation_sha256=fingerprint(state),
        original_advice=original_advice,
        executed_plan=executed_plan,
        component_sources=component_sources,
        override_reasons=override_reasons,
        host_model=host_model,
        student_positive_credit_eligible=bool(retained),
        retained_student_components=retained,
        scale_default="prefer_student_subject_to_capacity_and_physical_consistency",
    )


def phase_conclusion(*, supported, falsified, unresolved, scope, evidence_ids, termination_reason):
    if not scope or not termination_reason:
        raise ValueError("Every closeout requires scope and the actual termination reason")
    if (supported or falsified) and not evidence_ids:
        raise ValueError("Scientific claims require real evidence identifiers")
    return dict(
        supported=supported,
        falsified=falsified,
        unresolved=unresolved,
        scope=scope,
        evidence_ids=evidence_ids,
        termination_reason=termination_reason,
        include_in_C=True,
        include_in_D=True,
    )
