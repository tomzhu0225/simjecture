"""Trajectory RLOO accounting. Does not invoke a model or a simulator."""

from __future__ import annotations

import math


def leave_one_out(returns):
    if len(returns) < 2 or any(not math.isfinite(r) for r in returns):
        raise ValueError("RLOO needs at least two finite returns")
    total = math.fsum(returns)
    return [value - (total - value) / (len(returns) - 1) for value in returns]


def rollout_importance(log_ratio, maximum=2.0):
    if not math.isfinite(log_ratio) or maximum <= 0:
        raise ValueError("Importance correction needs a finite log ratio and positive cap")
    return min(maximum, math.exp(max(-20.0, min(20.0, log_ratio))))


def scientific_return(
    *, process_gains, terminal_validity, unsupported_claims, audits, sampled_sequence_kl=0.0, beta=0.02
):
    if not 0 <= terminal_validity <= 1:
        raise ValueError("Terminal scientific validity must lie in [0,1]")
    if unsupported_claims < 0 or not math.isfinite(unsupported_claims):
        raise ValueError("Unsupported-claim penalties must be finite and nonnegative")
    if beta < 0 or not math.isfinite(beta) or not math.isfinite(sampled_sequence_kl):
        raise ValueError("KL shaping parameters must be finite")
    audit_by_id = {audit["decision_id"]: audit for audit in audits}
    seen = set()
    attributable = 0.0
    evidence_rewards = []
    decision_credits = {identifier: 0.0 for identifier in audit_by_id}
    for gain in process_gains:
        if not math.isfinite(gain["value"]):
            raise ValueError("Evidence reward must be finite")
        if gain["evidence_id"] in seen:
            continue
        seen.add(gain["evidence_id"])
        if not gain["verified"]:
            continue
        parents = [audit_by_id[identifier] for identifier in gain["causal_decision_ids"]]
        # The complete host intervention remains in the record but contributes
        # no positive reward to the student's trajectory or individual actions.
        eligible = [audit for audit in parents if audit["student_positive_credit_eligible"]]
        if not eligible:
            continue
        amount = max(0.0, min(1.0, gain["value"]))
        attributable += amount
        for audit in eligible:
            # Split a verified gain across its actual executed ancestors. This
            # prevents one downstream observation rewarding every preceding turn.
            decision_credits[audit["decision_id"]] += amount / len(eligible)
        evidence_rewards.append(
            dict(
                evidence_id=gain["evidence_id"],
                value=amount,
                eligible_decision_ids=[a["decision_id"] for a in eligible],
            )
        )
    active = sum(a["student_positive_credit_eligible"] for a in audits)
    # This is explicitly a conservative attribution surrogate. It cannot prove
    # a causal fraction of the final result without the paired advice experiment.
    terminal_credit = terminal_validity * active / max(1, len(audits))
    process_credit = min(1.0, attributable)
    if attributable > 1:
        decision_credits = {key: value / attributable for key, value in decision_credits.items()}
    value = 0.30 * process_credit + 0.70 * terminal_credit - unsupported_claims - beta * sampled_sequence_kl
    return dict(
        value=value,
        process_credit=process_credit,
        terminal_credit=terminal_credit,
        evidence_rewards=evidence_rewards,
        decision_credits=decision_credits,
        credit_kind="conservative_component_provenance_surrogate",
    )


def action_advantages(trajectory, trajectory_advantage):
    """Conservative multi-turn evidence credit, with the initial-state LOO baseline.

    No leave-one-out matching of different later research states is attempted.
    The process redistribution and component masks are explicitly a shaped
    surrogate objective; causal benefit is measured separately by paired advice.
    """
    metadata = trajectory["return_metadata"]
    credits = metadata["decision_credits"]
    active = [a for a in trajectory["actions"] if a["student_executed_components"]]
    average = metadata["process_credit"] / max(1, len(active))
    result = []
    for action in trajectory["actions"]:
        local = sum(credits.get(key, 0) for key in action.get("decision_ids", []))
        result.append(
            trajectory_advantage + 0.3 * (local - average) if action["student_executed_components"] else 0.0
        )
    return result


def validate_group(trajectories):
    if len(trajectories) != 4:
        raise ValueError("The prepared RLOO group contains four complete research trajectories")
    for field in ["task_id", "initial_state_sha256", "old_policy_sha256", "budget_seconds"]:
        if len({t[field] for t in trajectories}) != 1:
            raise ValueError(f"RLOO group differs in {field}")
    if any(not t["closeout"] for t in trajectories):
        raise ValueError("Every trajectory, including timeout, requires an evidence-based closeout")
    return leave_one_out([t["return"] for t in trajectories])
