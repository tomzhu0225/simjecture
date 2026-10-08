"""A portable audit must detect tampering even when its export manifest is updated."""

import hashlib
import json

import pytest

from scripts.verify_research_audit import verify


@pytest.fixture
def audit(tmp_path):
    root = tmp_path / "record"
    root.mkdir()
    contents = {
        "research.json": {},
        "research_report.json": {"completed": False, "reviews": []},
        "experiments/exp_example.json": {
            "id": "exp_example",
            "status": "succeeded",
            "binding": {"inputs": {}},
            "artifacts": {"result.json": {"sha256": hashlib.sha256(b"{}\n").hexdigest()}},
        },
    }
    for name, value in contents.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
    result = root / "experiments/exp_example/workspace/result.json"
    result.parent.mkdir(parents=True)
    result.write_bytes(b"{}\n")
    manifest = {
        "files": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*")
            if p.is_file()
        },
        "experiments": {"succeeded": 1},
        "recorded_completed": False,
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    assert verify(root)["completed"] is False
    return root, manifest


def test_modified_artifact_cannot_be_resealed_by_export_manifest(audit):
    root, manifest = audit
    name = "experiments/exp_example/workspace/result.json"
    (root / name).write_bytes(b'{"fabricated": true}\n')
    manifest["files"][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="differs from receipt"):
        verify(root)


def test_export_cannot_claim_completion_absent_from_report(audit):
    root, manifest = audit
    manifest["recorded_completed"] = True
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Completion disposition"):
        verify(root)


def test_export_manifest_cannot_reach_outside_record(audit):
    root, manifest = audit
    (root.parent / "outside").write_bytes(b"outside")
    manifest["files"]["../outside"] = hashlib.sha256(b"outside").hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="escapes"):
        verify(root)
