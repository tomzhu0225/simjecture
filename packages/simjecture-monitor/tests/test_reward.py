"""Reward contracts prevent unmeasured success and unrelated continuation comparisons."""

import pytest
from pydantic import ValidationError
from simjecture_monitor.reward import ContinuationOutcome, RewardWeights, paired_reward, utility


def outcome(action="defer", **changes):
    values = dict(
        record_id=action,
        replicate_id="paired-replicate",
        action=action,
        common_prefix_sha256="a" * 64,
        observation_sha256="b" * 64,
        worker_config_sha256="c" * 64,
        criteria_sha256="d" * 64,
        continuation_budget_seconds=650,
        verified_quality=1,
        quality_receipt_sha256="e" * 64,
        capable_agent_starts=1,
        elapsed_seconds=400,
        required_feedback_misses=0,
        duplicate_wakeups=0,
    )
    values.update(changes)
    return ContinuationOutcome(**values)


def test_extra_judge_work_without_benefit_has_negative_reward():
    result = paired_reward(outcome("request_repair_judge", capable_agent_starts=3), outcome())
    assert result["eligible"]
    assert result["reward"] == pytest.approx(-0.04)


def test_preemptive_intervention_can_earn_reward_from_measured_time_saved():
    result = paired_reward(
        outcome("request_worker_help", elapsed_seconds=100, capable_agent_starts=2), outcome()
    )
    assert result["reward"] > 0


def test_no_waiting_branch_does_not_become_an_invented_zero_baseline():
    result = paired_reward(outcome("wake_director"), None)
    assert not result["eligible"]
    assert result["reward"] is None
    assert "missing_wait_continuation" in result["reasons"]


@pytest.mark.parametrize(
    "field",
    [
        "common_prefix_sha256",
        "observation_sha256",
        "worker_config_sha256",
        "criteria_sha256",
    ],
)
def test_unrelated_contexts_cannot_be_used_as_counterfactuals(field):
    result = paired_reward(outcome("wake_director", **{field: "f" * 64}), outcome())
    assert not result["eligible"]
    assert "mismatched_" + field in result["reasons"]


def test_unknown_feedback_is_unmeasured_and_not_silently_zero():
    result = paired_reward(outcome("wake_director", required_feedback_misses=None), outcome())
    assert not result["eligible"]
    assert result["reward"] is None


def test_verified_native_worker_failure_remains_a_negative_outcome():
    result = paired_reward(outcome("wake_director", verified_quality=0), outcome())
    assert result["eligible"]
    assert result["reward"] == pytest.approx(-1)


def test_duplicate_dispatches_and_feedback_are_separate_components():
    before = utility(outcome(), RewardWeights())
    after = utility(outcome(duplicate_wakeups=2, required_feedback_misses=1), RewardWeights())
    assert after["total"] - before["total"] == pytest.approx(-0.09)
    assert after["components"]["verified_quality"] == before["components"]["verified_quality"]


def test_overruns_continue_increasing_cost_instead_of_saturating():
    weights = RewardWeights()
    assert (
        utility(outcome(elapsed_seconds=1300), weights)["total"]
        < utility(outcome(elapsed_seconds=650), weights)["total"]
    )


def test_nonfinite_measurement_is_rejected():
    with pytest.raises(ValidationError):
        outcome(elapsed_seconds=float("nan"))
