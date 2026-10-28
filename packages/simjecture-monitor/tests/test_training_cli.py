import builtins
import json
import sys

import pytest
from simjecture_monitor import training


def row():
    return dict(
        id="train-1",
        split="train",
        state="A verified local example.",
        questions=dict(
            route=dict(
                type="choice",
                instructions="Choose a route.",
                criteria=dict(observe="Wait", director="Ask director"),
            )
        ),
        targets=dict(route=dict(label="observe")),
    )


def test_data_preflight_never_loads_torch_or_creates_an_adapter(tmp_path, monkeypatch, capsys):
    data = tmp_path / "train.jsonl"
    data.write_text(json.dumps(row()) + "\n")
    output = tmp_path / "adapter"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train",
            "--base",
            "/not-loaded",
            "--data",
            str(data),
            "--output",
            str(output),
            "--validate-only",
        ],
    )
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name in {"torch", "peft", "transformers"}:
            raise AssertionError("Preflight attempted to load GPU/model dependencies")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    training.main()
    result = json.loads(capsys.readouterr().out)
    assert result["stage"] == "data_validated"
    assert not result["model_loaded"] and not result["token_budget_checked"]
    assert not output.exists()


@pytest.mark.parametrize("split", ["test", "dev", "commissioning"])
def test_evaluation_and_commissioning_data_cannot_train(tmp_path, split):
    p = tmp_path / "rows.jsonl"
    p.write_text(json.dumps(row() | dict(split=split)) + "\n")
    with pytest.raises(ValueError, match="cannot enter"):
        training.read_data(p)


def test_preflight_rejects_unknown_target_before_loading_model(tmp_path, monkeypatch):
    data = tmp_path / "train.jsonl"
    value = row()
    value["targets"]["route"]["label"] = "invented"
    data.write_text(json.dumps(value) + "\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train",
            "--base",
            "/not-loaded",
            "--data",
            str(data),
            "--output",
            str(tmp_path / "out"),
            "--validate-only",
        ],
    )
    with pytest.raises(ValueError):
        training.main()
    assert not (tmp_path / "out").exists()
