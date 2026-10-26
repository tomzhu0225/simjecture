import importlib.util
from pathlib import Path

import pytest
from simjecture_monitor.checkpoint_attention import request_row
from test_checkpoint_attention import checkpoint, packet


def module(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "checkpoint_execution_test", scripts / "execute_checkpoint_decision.py"
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    clock = [10.0]
    monkeypatch.setattr(loaded.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        loaded.time, "sleep", lambda duration: clock.__setitem__(0, clock[0] + duration)
    )
    return loaded


def sample(path, route, *, basis="source", evidence="e0"):
    row = request_row(packet(path))
    row["behavior"] = dict(
        sampled_answers=dict(
            route=route,
            question_ref="none",
            basis=basis,
            evidence_primary=evidence,
            evidence_secondary="none",
        )
    )
    return row


def test_source_attention_requires_two_fresh_bound_checkpoint_reads(tmp_path, monkeypatch):
    loaded = module(monkeypatch)
    path = checkpoint(tmp_path)
    result = loaded.admission(path, sample(path, "director"))
    assert result["action"] == "wake_director"
    assert result["invalid_penalty"] == 0
    assert [r["admission"]["disposition"] for r in result["reads"]] == ["pending", "admitted"]
    first, second = [r["submitted"] for r in result["reads"]]
    assert second["packet_id"] != first["packet_id"]
    assert second["captured_ms"] - first["captured_ms"] >= 5000
    assert second["evidence"] == first["evidence"]


@pytest.mark.parametrize(
    "route,basis,evidence,penalty",
    [
        ("observe", "unspecified", "none", 0),
        ("recheck", "missing", "none", 0),
        ("lookup", "missing", "e0", 0.05),
        ("director", "unspecified", "none", 0.05),
        ("worker_help", "silence", "e0", 0.05),
    ],
)
def test_invalid_attention_cannot_get_the_same_reward_as_legitimate_abstention(
    tmp_path, monkeypatch, route, basis, evidence, penalty
):
    loaded = module(monkeypatch)
    path = checkpoint(tmp_path)
    result = loaded.admission(path, sample(path, route, basis=basis, evidence=evidence))
    assert result["action"] == "defer"
    assert result["invalid_penalty"] == penalty


def test_changed_model_input_is_not_executed(tmp_path, monkeypatch):
    loaded = module(monkeypatch)
    path = checkpoint(tmp_path)
    row = sample(path, "director")
    row["state"] += " substituted evidence"
    with pytest.raises(ValueError, match="changed after"):
        loaded.admission(path, row)


@pytest.mark.parametrize(
    "status,transport,eligible",
    [
        ("succeeded", None, True),
        ("failed", None, True),
        ("timeout", None, True),
        ("unknown", "failed", False),
        ("queued", None, False),
        ("running", None, False),
        ("succeeded", "failed", False),
    ],
)
def test_actual_solver_failures_remain_rewards_but_unconfirmed_transfers_do_not(
    tmp_path, monkeypatch, status, transport, eligible
):
    import json

    loaded = module(monkeypatch)
    folder = tmp_path / "research/runs/control"
    folder.mkdir(parents=True)
    (folder / "receipt.json").write_text(
        json.dumps(dict(status=status, transport_status=transport))
    )
    if eligible:
        loaded.require_confirmed_solver_outcomes(tmp_path)
    else:
        with pytest.raises(ValueError, match="ineligible for training"):
            loaded.require_confirmed_solver_outcomes(tmp_path)


def test_missing_physics_cannot_be_treated_as_a_measured_failure(tmp_path, monkeypatch):
    loaded = module(monkeypatch)
    with pytest.raises(ValueError, match="No physical execution"):
        loaded.require_confirmed_solver_outcomes(tmp_path)
