from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

REPOSITORY = Path(__file__).resolve().parents[1]
RECORD = REPOSITORY / "demos" / "gray_scott_counterexample" / "record"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_gray_scott_record_is_complete_and_hash_bound() -> None:
    report = json.loads((RECORD / "mvp_report.json").read_text())
    assert report["status"] == "completed"
    assert report["iterations"] == 37
    assert report["open_claim_ids"] == []

    workspace = RECORD / "workspace"
    expected = report["workspace_artifacts"]
    actual = {path.name for path in workspace.iterdir() if path.is_file()}
    assert actual == set(expected)
    assert {name: _sha256(workspace / name) for name in expected} == expected


def test_gray_scott_record_contains_the_reported_counterexample() -> None:
    ledger = json.loads((RECORD / "hypothesis_ledger.json").read_text())
    statuses = {claim["id"]: claim["status"] for claim in ledger["claims"]}
    assert statuses == {"claim_root": "falsified", "claim_finite_gs": "supported"}

    result = json.loads((RECORD / "workspace" / "root_pattern_results.json").read_text())
    patterned = result["dt_0p05"]["1"]["P_final"]
    homogeneous = result["dt_0p05"]["10"]["P_final"]
    assert patterned > 1.0e-3
    assert patterned / homogeneous > 1.0e3

    for scale in ("1", "10"):
        archive = np.load(RECORD / "workspace" / f"root_s{scale}_dt0p05.npz")
        assert archive["u"].shape == (128, 128)
        assert np.isfinite(archive["u"]).all()
