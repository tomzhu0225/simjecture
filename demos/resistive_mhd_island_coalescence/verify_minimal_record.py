"""Verify the one-hour minimal-run audit extract, without a solver or model call."""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path


def verify():
    root = Path(__file__).resolve().parent / "minimal_record"
    manifest = json.loads((root / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Record path escapes archive: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Record hash mismatch: {name}")
    records = [json.loads(p.read_text()) for p in (root / "experiments").glob("*.json")]
    assert dict(collections.Counter(r["status"] for r in records)) == manifest["experiments"]
    for record in records:
        workspace = root / "experiments" / record["id"] / "workspace"
        for name, digest in record["binding"]["inputs"].items():
            path = workspace / name
            if path.is_file():
                assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        for name, artifact in record.get("artifacts", {}).items():
            path = workspace / name
            if path.is_file():
                assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    report = json.loads((root / "research_report.json").read_text())
    assert report["completed"] is False
    assert not any(r.get("verdict", {}).get("decision") == "approved" for r in report["reviews"])
    methods = [json.loads(p.read_text()) for p in (root / "methods").glob("*.json")]
    return {
        "verified_files": len(manifest["files"]),
        "experiment_statuses": manifest["experiments"],
        "method_decisions": dict(
            collections.Counter(m.get("verdict", {}).get("decision") for m in methods)
        ),
        "completed": False,
        "scientific_outcome": manifest["scientific_outcome"],
        "scope": (
            "Integrity and recorded disposition only; omitted bulk histories prevent "
            "complete numerical replay from this extract."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
