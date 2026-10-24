import json

import pytest
from simjecture_monitor.checkpoint import freeze, restore
from simjecture_monitor.ledger import IncidentLedger


def test_checkpoint_detects_changed_files_and_manifest(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "data").write_text("actual plot-derived diagnostics")
    checkpoint = tmp_path / "checkpoint"
    manifest = freeze(
        work,
        checkpoint,
        transcript=[{"output": "saved"}],
        criteria={"charge": 1e-11},
        worker_config={"model": "worker"},
        downstream_policy={"automatic": "observe"},
    )
    assert restore(checkpoint, tmp_path / "branch") == manifest
    (checkpoint / "artifacts/data").write_text("changed")
    with pytest.raises(ValueError, match="artifact hash"):
        restore(checkpoint, tmp_path / "other")
    (checkpoint / "artifacts/data").write_text("actual plot-derived diagnostics")
    manifest["criteria"]["charge"] = 1
    (checkpoint / "checkpoint.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest hash"):
        restore(checkpoint, tmp_path / "other")


def test_checkpoint_rejects_symlinks(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    (work / "link").symlink_to("/etc/hostname")
    with pytest.raises(ValueError, match="symbolic"):
        freeze(
            work,
            tmp_path / "checkpoint",
            transcript=[],
            criteria={},
            worker_config={},
            downstream_policy={},
        )


def test_incident_reopen_and_idempotent_execution_receipt(tmp_path):
    ledger = IncidentLedger(tmp_path / "ledger.json")
    incident = ledger.observe("adapter", "completion mismatch", {"trace": "one"}, now=1)
    same = ledger.observe("adapter", "completion mismatch", {"trace": "two"}, now=2)
    assert same["id"] == incident["id"] and same["generation"] == 1
    with pytest.raises(ValueError, match="execution receipt"):
        ledger.dispatch(incident["id"], "wake_director", execution_receipt=None)
    first = ledger.dispatch(incident["id"], "wake_director", execution_receipt={"pid": 1})
    assert ledger.dispatch(incident["id"], "wake_director", execution_receipt={"pid": 1}) == first
    ledger.resolve(incident["id"], {"checks": "passed"}, now=3)
    ledger = IncidentLedger(ledger.path)
    reopened = ledger.observe("adapter", "completion mismatch", {"trace": "three"}, now=4)
    assert reopened["generation"] == 2 and reopened["status"] == "active"
    assert len(ledger.data["dispatches"]) == 1


def test_feedback_requires_content_identity_and_actual_delivery(tmp_path):
    ledger = IncidentLedger(tmp_path / "ledger.json")
    row = ledger.feedback(
        "repair", {"applied": True}, required=True, reason="Protected repair applied"
    )
    ack = dict(
        id="repair",
        result_sha256=row["result_sha256"],
        disposition="used",
        explanation="Reran the previously blocked operation and checked its diagnostics.",
    )
    path = tmp_path / "ACK.json"
    path.write_text(json.dumps([ack]))
    assert ledger.acknowledge(path) == []
    ledger.deliver(tmp_path)
    ack["result_sha256"] = "bad"
    path.write_text(json.dumps([ack]))
    assert ledger.acknowledge(path) == []
    ack["result_sha256"] = row["result_sha256"]
    path.write_text(json.dumps([ack]))
    assert ledger.acknowledge(path) == ["repair"]
    assert ledger.measurements()["required_feedback_misses"] == 0
    with pytest.raises(ValueError, match="cannot change"):
        ledger.feedback("repair", {"applied": False}, required=True, reason="Changed")
