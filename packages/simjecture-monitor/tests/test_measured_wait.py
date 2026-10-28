"""Measured controls cannot become fabricated baseline returns or policy samples."""

import copy
import hashlib
import json

import pytest
from simjecture_monitor.events import digest
from simjecture_monitor.measured_wait import wait_controlled_advantages
from simjecture_monitor.reward import ContinuationOutcome, RewardWeights, utility


def outcome(name, action, **changes):
    values = dict(
        record_id=name,
        replicate_id="public-state",
        action=action,
        common_prefix_sha256="a" * 64,
        observation_sha256="b" * 64,
        worker_config_sha256="c" * 64,
        downstream_policy_sha256="d" * 64,
        criteria_sha256="e" * 64,
        continuation_budget_seconds=650,
        verified_quality=1.0,
        quality_receipt_sha256=digest({"verified_quality": 1.0}),
        capable_agent_starts=1,
        elapsed_seconds=100,
        required_feedback_misses=0,
        duplicate_wakeups=0,
    )
    return ContinuationOutcome(**(values | changes))


def save(root, name, value):
    raw = json.dumps(value).encode()
    (root / name).write_bytes(raw)
    return dict(path=name, sha256=hashlib.sha256(raw).hexdigest())


def receipt(measured, *, control=False):
    value = dict(
        source_kind="executed_wait_continuation" if control else "executed_worker_continuation",
        status="completed",
        verification_sha256=measured.quality_receipt_sha256,
        outcome=measured.model_dump(),
        solver_outcomes_confirmed=True,
        utility=utility(measured, RewardWeights())["total"],
    )
    if not control:
        value.update(
            prompt_sha256="f" * 64,
            sampled_answers={"route": measured.action},
            admission=dict(action=measured.action, invalid_penalty=0.0, overhead_seconds=0.0),
        )
    return value


@pytest.fixture
def dataset(tmp_path):
    waits = [
        save(tmp_path, f"wait-{i}.json", receipt(outcome(f"control-{i}", "defer"), control=True))
        for i in range(2)
    ]
    rows = []
    for i, action in enumerate(["request_worker_help", "wake_director"]):
        name = f"sample-{i}"
        measured = outcome(name, action, capable_agent_starts=2 + i)
        rows.append(
            dict(
                id=name,
                split="train",
                return_group="public-state",
                host_checkpoint_id="opaque-prefix",
                state="Actual public input",
                questions=[],
                targets={"route": dict(label=action)},
                behavior=dict(prompt_sha256="f" * 64, sampled_answers={"route": action}),
                outcome_receipt=save(tmp_path, name + ".json", receipt(measured)),
                wait_outcome_receipts=copy.deepcopy(waits),
            )
        )
    return rows


def test_every_intervention_can_be_worse_than_waiting(dataset, tmp_path):
    advantages, audit = wait_controlled_advantages(dataset, tmp_path)
    assert advantages == pytest.approx({"sample-0": -0.02, "sample-1": -0.04})
    assert audit["public-state"]["wait_records"] == ["control-0", "control-1"]
    assert set(advantages) == {row["id"] for row in dataset}


def test_verified_worker_failure_is_negative_evidence(dataset, tmp_path):
    path = dataset[0]["outcome_receipt"]["path"]
    measured = outcome("sample-0", "request_worker_help", verified_quality=0.0)
    dataset[0]["outcome_receipt"] = save(tmp_path, path, receipt(measured))
    result, _ = wait_controlled_advantages(dataset, tmp_path)
    assert result["sample-0"] == pytest.approx(-1)


@pytest.mark.parametrize(
    "field",
    [
        "common_prefix_sha256",
        "observation_sha256",
        "worker_config_sha256",
        "downstream_policy_sha256",
        "criteria_sha256",
        "continuation_budget_seconds",
        "replicate_id",
    ],
)
def test_unrelated_wait_cannot_supply_an_action_baseline(dataset, tmp_path, field):
    value = receipt(
        outcome(
            "control-0",
            "defer",
            **{field: 600 if field == "continuation_budget_seconds" else "0" * 64},
        ),
        control=True,
    )
    replacement = save(tmp_path, "wait-0.json", value)
    for row in dataset:
        row["wait_outcome_receipts"][0] = replacement
    with pytest.raises(ValueError, match="Incomparable wait"):
        wait_controlled_advantages(dataset, tmp_path)


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("one", "at least two"),
        ("duplicate", "distinct"),
        ("different", "share its wait"),
        ("sample_as_control", "assigned kind"),
    ],
)
def test_explicit_independent_controls_are_mandatory(dataset, tmp_path, mutation, match):
    if mutation == "one":
        for row in dataset:
            row["wait_outcome_receipts"] = row["wait_outcome_receipts"][:1]
    elif mutation == "duplicate":
        for row in dataset:
            row["wait_outcome_receipts"][1] = row["wait_outcome_receipts"][0]
    elif mutation == "different":
        dataset[1]["wait_outcome_receipts"][1] = dataset[1]["wait_outcome_receipts"][0]
    else:
        for row in dataset:
            row["wait_outcome_receipts"][0] = dataset[0]["outcome_receipt"]
    with pytest.raises(ValueError, match=match):
        wait_controlled_advantages(dataset, tmp_path)


@pytest.mark.parametrize(
    "mutation,match",
    [
        ({"solver_outcomes_confirmed": False}, "Unconfirmed solver"),
        ({"utility": 1000}, "Utility does not reproduce"),
        ({"utility": float("nan")}, "Utility does not reproduce"),
        ({"verification_sha256": "0" * 64}, "verification identity"),
        ({"status": "failed"}, "completed executed"),
    ],
)
def test_unusable_baselines_never_become_rewards(dataset, tmp_path, mutation, match):
    value = json.loads((tmp_path / "wait-0.json").read_text()) | mutation
    replacement = save(tmp_path, "wait-0.json", value)
    for row in dataset:
        row["wait_outcome_receipts"][0] = replacement
    with pytest.raises(ValueError, match=match):
        wait_controlled_advantages(dataset, tmp_path)


def test_changed_receipt_and_test_examples_are_rejected(dataset, tmp_path):
    dataset[0]["split"] = "test"
    with pytest.raises(ValueError, match="training rows"):
        wait_controlled_advantages(dataset, tmp_path)
    dataset[0]["split"] = "train"
    (tmp_path / "wait-0.json").write_text("{}")
    with pytest.raises(ValueError, match="receipt changed"):
        wait_controlled_advantages(dataset, tmp_path)






