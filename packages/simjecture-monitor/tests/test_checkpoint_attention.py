import importlib.util
import json
from pathlib import Path

import pytest
from simjecture_monitor.checkpoint import freeze
from simjecture_monitor.checkpoint_attention import from_checkpoint, request_row
from simjecture_monitor.decision_interface import compile_messages
from simjecture_monitor.events import digest, put


def checkpoint(tmp_path, task="Compare two real meshes, preserving the original checks."):
    work = tmp_path / "work"
    (work / "harness").mkdir(parents=True)
    (work / "TASK.txt").write_text(task)
    (work / "harness/bridge.py").write_text("status = 'succeeded'\n")
    (work / "analysis_probe.py").write_text("from original_analysis import analyze\n")
    destination = tmp_path / "checkpoint"
    transcript = [dict(type="command_execution", output="measured actual saved fields")]
    freeze(
        work,
        destination,
        transcript=transcript,
        criteria=dict(field_tolerance=0.05, charge_tolerance=1e-11),
        worker_config={},
        downstream_policy={},
    )
    state = dict(task=(work / "TASK.txt").read_text(), events=[dict(body=transcript[0])])
    put(destination / "observation.json", dict(state=state, packet_sha256=digest(state)))
    return destination


def packet(path, **kw):
    return from_checkpoint(path, packet_id="p1", clock_id="c1", captured_ms=1000, sequence=1, **kw)


def test_checkpoint_input_is_public_and_training_metadata_is_not_in_prompt(tmp_path):
    path = checkpoint(tmp_path)
    row = request_row(packet(path))
    assert row["observation"]["timing"]["progress_age_ms"] is None
    assert len(row["observation"]["evidence"]) == 4
    original, _ = compile_messages(row)
    row.update(targets={"hidden": "future reward"}, utility=100, return_group="secret-case")
    assert compile_messages(row)[0] == original


def test_long_task_is_kept_in_full_as_ordered_evidence(tmp_path):
    task = "Preserve the declared checks. " * 110
    observation = packet(checkpoint(tmp_path, task))
    parts = [e for e in observation.evidence if e.source_role.startswith("declared_task_part_")]
    assert "".join(e.content for e in parts) == task
    assert not any(e.excerpted for e in parts)


@pytest.mark.parametrize("change", ["artifact", "task", "transcript", "manifest"])
def test_changed_checkpoint_cannot_be_used_for_sampling(tmp_path, change):
    path = checkpoint(tmp_path)
    if change == "artifact":
        (path / "artifacts/analysis_probe.py").write_text("changed")
    elif change == "manifest":
        value = json.loads((path / "checkpoint.json").read_text())
        value["criteria"]["field_tolerance"] = 99
        put(path / "checkpoint.json", value)
    else:
        value = json.loads((path / "observation.json").read_text())
        if change == "task":
            value["state"]["task"] = "accept anything"
        else:
            value["state"]["events"][0]["body"]["output"] = "invented error"
        value["packet_sha256"] = digest(value["state"])
        put(path / "observation.json", value)
    with pytest.raises(ValueError):
        packet(path)


def test_preparation_keeps_host_case_labels_out_of_model_inputs(tmp_path):
    source = Path(__file__).parents[1] / "scripts/prepare_checkpoint_requests.py"
    spec = importlib.util.spec_from_file_location("prepare_checkpoint_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = checkpoint(tmp_path)
    design = dict(split="train", assignments=[dict(id=path.name, kind="hidden-mechanism-label")])
    rows = module.prepare(tmp_path, design)
    assert len(rows) == 1
    assert rows[0]["host_checkpoint_id"] == path.name
    assert (
        rows[0]["return_group"]
        == json.loads((path / "checkpoint.json").read_text())["common_prefix_sha256"]
    )
    assert "hidden-mechanism-label" not in json.dumps(rows)
    assert compile_messages(rows[0])[0] == compile_messages(request_row(packet(path)))[0]
    with pytest.raises(ValueError, match="training-only"):
        module.prepare(tmp_path, design | dict(split="test"))
    (path / "artifacts/analysis_probe.py").write_text("changed after freezing")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        module.prepare(tmp_path, design)
