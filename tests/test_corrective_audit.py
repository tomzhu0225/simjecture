from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from conjecture_solver.corrective_audit import (
    CORRECTIVE_AUDIT_FILE,
    append_corrective_audit,
    load_corrective_audits,
)


def test_corrective_audit_is_hash_chained_and_does_not_rewrite_artifacts(
    tmp_path: Path,
) -> None:
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    report = campaign / "mvp_report.json"
    ledger = campaign / "hypothesis_ledger.json"
    report.write_text('{"status":"completed"}\n')
    ledger.write_text('{"claims":[]}\n')
    original_report = report.read_bytes()
    original_ledger = ledger.read_bytes()

    first = append_corrective_audit(
        campaign,
        reviewer="operator-review",
        finding="The terminal record was incorrectly interpreted as scientific support.",
        corrected_interpretation=(
            "The run is instrument-limited because the registered claim was not tested."
        ),
        artifacts=("mvp_report.json", "hypothesis_ledger.json"),
        recorded_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    second = append_corrective_audit(
        campaign,
        reviewer="operator-review",
        finding="The follow-up confirms that no scientific support should be inferred.",
        corrected_interpretation=(
            "Preserve the historical result only as an auditable failed test attempt."
        ),
        artifacts=("mvp_report.json",),
        recorded_at=datetime(2026, 8, 27, tzinfo=UTC),
    )

    loaded = load_corrective_audits(campaign)
    assert loaded.records == (first, second)
    assert second.previous_record_sha256 == first.record_sha256
    assert report.read_bytes() == original_report
    assert ledger.read_bytes() == original_ledger


def test_corrective_audit_detects_tampering(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    campaign.mkdir()
    (campaign / "mvp_report.json").write_text('{"status":"completed"}\n')
    append_corrective_audit(
        campaign,
        reviewer="operator-review",
        finding="A material semantic mismatch was identified in this campaign record.",
        corrected_interpretation="The original conclusion must not be treated as support.",
        artifacts=("mvp_report.json",),
    )
    path = campaign / CORRECTIVE_AUDIT_FILE
    payload = json.loads(path.read_text())
    payload["records"][0]["finding"] = "A silently changed finding that breaks the digest."
    path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="digest does not match"):
        load_corrective_audits(campaign)


def test_corrective_audit_rejects_paths_outside_campaign(tmp_path: Path) -> None:
    campaign = tmp_path / "campaign"
    campaign.mkdir()

    with pytest.raises(ValueError, match="must stay inside"):
        append_corrective_audit(
            campaign,
            reviewer="operator-review",
            finding="A material semantic mismatch was identified in this campaign record.",
            corrected_interpretation="The original conclusion must not be treated as support.",
            artifacts=("../outside.json",),
        )
