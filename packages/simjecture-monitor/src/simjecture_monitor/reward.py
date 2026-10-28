"""Prospective paired rewards for interventions on the same observable checkpoint.

This consumes independently verified host records. It does not infer unobserved
counterfactual outcomes, create labels from judge approvals, or relabel v1 data.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Action = Literal["defer", "request_worker_help", "wake_director", "request_repair_judge"]


class RewardWeights(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    quality: float = Field(default=1.0, ge=0)
    agent_start: float = Field(default=0.02, ge=0)
    wall_time: float = Field(default=0.1, ge=0)
    required_feedback_miss: float = Field(default=0.05, ge=0)
    duplicate_wakeup: float = Field(default=0.02, ge=0)
    time_scale_seconds: float = Field(default=650, gt=0)


class ContinuationOutcome(BaseModel):
    """One measured continuation; zero quality includes verified worker failure.

    Quality is independently checked reporting/progress, including correctly
    reported scientific falsification. It is not the fraction of physics checks
    that pass. Feedback misses require an actual needed result and an explicit
    delivery/acknowledgment audit. Duplicate wakes count dispatched redundant
    work, never proposals suppressed by the host. None means unmeasured.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    record_id: str = Field(min_length=1)
    replicate_id: str = Field(min_length=1)
    action: Action
    common_prefix_sha256: Sha256
    observation_sha256: Sha256
    worker_config_sha256: Sha256
    downstream_policy_sha256: Sha256
    criteria_sha256: Sha256
    continuation_budget_seconds: float = Field(gt=0)
    verified_quality: float | None = Field(default=None, ge=0, le=1)
    quality_receipt_sha256: Sha256 | None = None
    capable_agent_starts: int | None = Field(default=None, ge=0)
    elapsed_seconds: float | None = Field(default=None, ge=0)
    required_feedback_misses: int | None = Field(default=None, ge=0)
    duplicate_wakeups: int | None = Field(default=None, ge=0)


MEASUREMENTS = (
    "verified_quality",
    "quality_receipt_sha256",
    "capable_agent_starts",
    "elapsed_seconds",
    "required_feedback_misses",
    "duplicate_wakeups",
)
MATCHING_CONTEXT = (
    "replicate_id",
    "common_prefix_sha256",
    "observation_sha256",
    "worker_config_sha256",
    "downstream_policy_sha256",
    "criteria_sha256",
    "continuation_budget_seconds",
)


def utility(outcome: ContinuationOutcome, weights: RewardWeights):
    missing = [key for key in MEASUREMENTS if getattr(outcome, key) is None]
    if missing:
        raise ValueError("Unmeasured reward components: " + ", ".join(missing))
    components = dict(
        verified_quality=weights.quality * outcome.verified_quality,
        agent_starts=-weights.agent_start * outcome.capable_agent_starts,
        elapsed_time=-weights.wall_time * outcome.elapsed_seconds / weights.time_scale_seconds,
        required_feedback=-weights.required_feedback_miss * outcome.required_feedback_misses,
        duplicate_wakeups=-weights.duplicate_wakeup * outcome.duplicate_wakeups,
    )
    return dict(total=sum(components.values()), components=components)


def paired_reward(
    chosen: ContinuationOutcome,
    waiting: ContinuationOutcome | None,
    weights: RewardWeights | None = None,
):
    """Compare measured immediate action with a measured waiting continuation.

    A matched public checkpoint does not make native agents deterministic.
    Repeated randomized continuation pairs are needed to estimate expected value.
    The returned eligibility concerns complete comparable measurements only;
    cohort blinding, split integrity, receipt authenticity and eligibility for an
    on-policy optimizer need separate checks.
    """
    weights = weights or RewardWeights()
    reasons = []
    if waiting is None:
        reasons.append("missing_wait_continuation")
    elif waiting.action != "defer":
        reasons.append("comparison_action_must_be_defer")
    else:
        reasons.extend(
            "mismatched_" + key
            for key in MATCHING_CONTEXT
            if getattr(chosen, key) != getattr(waiting, key)
        )
    for label, outcome in [("chosen", chosen), ("wait", waiting)]:
        if outcome is not None:
            reasons.extend(
                label + "_unmeasured_" + key
                for key in MEASUREMENTS
                if getattr(outcome, key) is None
            )
    result = dict(
        eligible=not reasons,
        reasons=reasons,
        chosen_record=chosen.record_id,
        wait_record=waiting.record_id if waiting else None,
        weights=weights.model_dump(),
        reward=None,
        scope="Paired measured utility difference; no inferred counterfactual or causal guarantee",
    )
    if not reasons:
        chosen_utility = utility(chosen, weights)
        waiting_utility = utility(waiting, weights)
        result.update(
            chosen_utility=chosen_utility,
            waiting_utility=waiting_utility,
            reward=chosen_utility["total"] - waiting_utility["total"],
        )
    return result
