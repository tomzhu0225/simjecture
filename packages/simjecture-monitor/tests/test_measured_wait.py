"""Measured controls cannot become fabricated baseline returns or policy samples."""

import copy
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from simjecture_monitor.events import digest
from simjecture_monitor.measured_wait import wait_controlled_advantages
from simjecture_monitor.reward import ContinuationOutcome, RewardWeights, utility


def collector():
    scripts = Path(__file__).parents[1] / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(
            "controlled_returns_test", scripts / "collect_controlled_returns.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts))


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


def test_independent_controls_are_frozen_for_every_group(dataset):
    module = collector()
    proposals = [
        {
            key: value
            for key, value in row.items()
            if key not in {"outcome_receipt", "wait_outcome_receipts"}
        }
        for row in dataset
    ]
    second = [
        row
        | dict(
            id="another-" + row["id"],
            return_group="other-state",
            host_checkpoint_id="other-prefix",
            state="Another public state",
        )
        for row in proposals
    ]
    blocks = module.assignments(proposals + second, repeats=2, seed=111)
    assert blocks == module.assignments(proposals + second, repeats=2, seed=111)
    assert len(blocks) == 2
    assert len({trial["id"] for block in blocks for trial in block["trials"]}) == 8
    for block in blocks:
        assert [t["kind"] for t in block["trials"]].count("wait") == 2
        assert [t["kind"] for t in block["trials"]].count("sampled") == 2
        assert all(not t["id"].startswith("wait-") for t in block["trials"])
    with pytest.raises(ValueError, match="unexecuted"):
        module.assignments(dataset, repeats=2, seed=111)


def test_wait_collector_checks_actual_transport_receipts(tmp_path):
    module = collector()
    measured = outcome("opaque-control", "defer")
    (tmp_path / "OUTCOME.json").write_text(measured.model_dump_json())
    (tmp_path / "CONTINUATION.json").write_text(
        json.dumps(dict(stage="completed", quality={"verified_quality": 1.0}))
    )
    folder = tmp_path / "research/runs/control"
    folder.mkdir(parents=True)
    (folder / "receipt.json").write_text(
        json.dumps(dict(status="unknown", transport_status="failed"))
    )
    with pytest.raises(ValueError, match="Unconfirmed solver"):
        module.wait_receipt(tmp_path)
    (folder / "receipt.json").write_text(json.dumps(dict(status="succeeded")))
    record = module.wait_receipt(tmp_path)
    assert record["source_kind"] == "executed_wait_continuation"
    assert "sampled_answers" not in record


@pytest.mark.parametrize("failure", [None, "sample-0", "no_capacity"])
def test_collection_preserves_all_assignments_and_only_exports_a_complete_cohort(
    dataset, tmp_path, monkeypatch, failure
):
    """Exercise the CLI orchestration with a fake child, never a model or solver."""
    module = collector()
    samples, prefixes, root = [tmp_path / name for name in ["samples", "prefixes", "cohort"]]
    samples.mkdir()
    checkpoint = prefixes / "opaque-prefix"
    checkpoint.mkdir(parents=True)
    for name in ["checkpoint.json", "observation.json"]:
        (checkpoint / name).write_text("{}")
    for row in dataset:
        proposal = {
            key: value
            for key, value in row.items()
            if key not in {"outcome_receipt", "wait_outcome_receipts"}
        }
        save(samples, row["id"] + ".json", proposal)
    save(samples, "manifest.json", dict(records=[row["id"] for row in dataset]))
    planned = module.plan(
        SimpleNamespace(samples=samples, prefixes=prefixes, root=root, repetitions=2, seed=123)
    )
    budget = tmp_path / "budget.json"
    save(
        tmp_path,
        budget.name,
        dict(
            starts=[],
            maximum_starts=0 if failure == "no_capacity" else 100,
            maximum_per_continuation=12,
            deadline=time.time() + 10000,
        ),
    )
    interpreter = tmp_path / "venv-python"
    interpreter.symlink_to(sys.executable)
    invoked = []

    class FakeProcess:
        def __init__(self, command, **kwargs):
            self.pid = os.getpid()
            destination = Path(command[command.index("--root") + 1])
            name = destination.name
            invoked.append(name)
            assert command[command.index("--python") + 1] == str(interpreter)
            assert kwargs["env"]["SIMJECTURE_CONTINUATION"] == name
            self.code = 1 if failure == name else 0
            if self.code:
                return
            destination.mkdir(parents=True)
            if "--sample" in command:
                proposal = json.loads(Path(command[command.index("--sample") + 1]).read_text())
                measured = outcome(
                    name, proposal["targets"]["route"]["label"], capable_agent_starts=2
                )
                target = Path(command[command.index("--receipts") + 1])
                proposal["outcome_receipt"] = save(target, name + "-reward.json", receipt(measured))
                save(target, name + "-training.json", proposal)
            else:
                measured = outcome(name, "defer")
                (destination / "OUTCOME.json").write_text(measured.model_dump_json())
                save(
                    destination,
                    "CONTINUATION.json",
                    dict(stage="completed", quality={"verified_quality": 1.0}),
                )
                physical = destination / "research/runs/control"
                physical.mkdir(parents=True)
                save(physical, "receipt.json", dict(status="succeeded"))

        def wait(self, *, timeout):
            return self.code

    monkeypatch.setattr(module.subprocess, "Popen", FakeProcess)
    result = module.execute(
        SimpleNamespace(
            root=root,
            budget=budget,
            backend=tmp_path / "backend.json",
            wrapper=tmp_path / "native-wrapper",
            python=interpreter,
            plasma_assets=tmp_path / "plasma",
            parallel=2,
        )
    )
    if failure == "no_capacity":
        assert invoked == []
        assert result["unstarted_groups"] == ["public-state"]
        assert result["blocks"] == []
    else:
        assert sorted(invoked) == sorted(t["id"] for t in planned["blocks"][0]["trials"])
        assert len(result["blocks"][0]["results"]) == 4
    assert result["eligible"] is (failure is None)
    assert (root / "receipts/train.jsonl").exists() is (failure is None)
    if failure is None:
        rows = [
            json.loads(line) for line in (root / "receipts/train.jsonl").read_text().splitlines()
        ]
        assert len(rows) == 2
        assert len(rows[0]["wait_outcome_receipts"]) == 2
        assert all(
            value < 0 for value in wait_controlled_advantages(rows, root / "receipts")[0].values()
        )
    with pytest.raises(ValueError, match="already attempted"):
        module.execute(SimpleNamespace(root=root))
