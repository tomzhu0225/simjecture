"""Audit the exact model-visible view, not discarded context or guessed failures."""

import importlib.util
from pathlib import Path

import pytest
from simjecture_monitor.events import digest


def audit_module():
    source = Path(__file__).parents[1] / "scripts/audit_reward_data.py"
    spec = importlib.util.spec_from_file_location("reward_audit", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record():
    state = dict(
        events=[
            dict(id="old", body=dict(text="/trials/harness-71/private/path")),
            dict(id="current", body=dict(text="Control is progressing")),
        ]
    )
    visible = dict(events=state["events"][1:])
    return dict(
        packet=dict(state=state, packet_sha256=digest(state)),
        model_view=dict(included_event_ids=["current"], state_sha256=digest(visible)),
    )


def test_discarded_case_path_is_not_reported_as_visible():
    value = record()
    view = audit_module().observed_view(value)
    assert view == dict(events=[dict(id="current", body=dict(text="Control is progressing"))])
    assert "harness-71" not in str(view)
    assert len(value["packet"]["state"]["events"]) == 2


def test_tampered_or_incomplete_visibility_receipts_are_rejected():
    value = record()
    value["model_view"]["included_event_ids"] = ["unrecorded"]
    with pytest.raises(ValueError, match="invalid event"):
        audit_module().observed_view(value)
    value = record()
    value["model_view"]["state_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="does not match"):
        audit_module().observed_view(value)


def test_code_mentioning_a_failure_is_not_a_measured_status_mismatch():
    module = audit_module()
    body = dict(type="command_execution", aggregated_output='print("reported_status: running")')
    view = dict(events=[dict(body=body)])
    assert not module.visible_status_mismatch(view)
    body["aggregated_output"] = (
        '{"reported_status":"running","process_receipt_status":"succeeded","returncode":0}'
    )
    assert module.visible_status_mismatch(view)
