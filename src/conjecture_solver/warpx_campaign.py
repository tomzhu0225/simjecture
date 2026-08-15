"""Portable, self-verifying export for a qualified WarpX campaign."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .benchmarks.kinetic_sufficiency import build_problem
from .ledger import SQLiteEventLedger
from .models import Claim, ClaimDisposition, HypothesisNode, RunEvidence, StrictModel
from .orchestration import MultiActionCampaignReport, OrchestrationDisposition
from .search import BlindedSearchReport
from .warpx_confirmation import (
    QualifiedWarpXInstrument,
    WarpXConfirmationDisposition,
    WarpXConfirmationReport,
)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class QualifiedWarpXCampaignPackage(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    campaign_id: str = Field(min_length=1)
    hypothesis: HypothesisNode
    instrument: QualifiedWarpXInstrument
    search_report: BlindedSearchReport
    confirmation_report: WarpXConfirmationReport
    evidence: tuple[RunEvidence, ...] = ()
    claim: Claim
    campaign_report: MultiActionCampaignReport
    provenance_event_hashes: tuple[str, ...] = Field(min_length=1)
    generated_at: datetime
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def scientific_records_are_consistent(self) -> QualifiedWarpXCampaignPackage:
        if self.campaign_report.campaign_id != self.campaign_id:
            raise ValueError("campaign package contains a report for another campaign")
        if self.campaign_report.disposition is not OrchestrationDisposition.COMPLETED:
            raise ValueError("only a completed campaign can be exported")
        if self.instrument.qualification_hash != self.confirmation_report.design.qualification_hash:
            raise ValueError("confirmation does not use the packaged qualified instrument")
        if (
            self.search_report.confirmation_candidate
            != self.confirmation_report.design.physical.candidate
        ):
            raise ValueError("confirmation candidate differs from the frozen search winner")
        if self.claim.hypothesis_id != self.hypothesis.id:
            raise ValueError("claim refers to another hypothesis")
        evidence_ids = {item.id for item in self.evidence}
        if self.claim.disposition is ClaimDisposition.REFUTED_WITHIN_MODEL:
            if self.confirmation_report.disposition is not WarpXConfirmationDisposition.CONFIRMED:
                raise ValueError("an unconfirmed matrix cannot support a refutation claim")
            if not evidence_ids or set(self.claim.evidence_ids) != evidence_ids:
                raise ValueError("refutation claim must name every packaged confirmation evidence")
            if not all(item.eligible for item in self.evidence):
                raise ValueError("refutation claim cannot cite ineligible evidence")
        return self

    def calculated_hash(self) -> str:
        content = self.model_dump(mode="json", exclude={"package_hash"})
        return hashlib.sha256(_canonical_json(content).encode()).hexdigest()

    def verify_hash(self) -> bool:
        return self.package_hash == self.calculated_hash()

    @classmethod
    def create(cls, **values: object) -> QualifiedWarpXCampaignPackage:
        unhashed = cls.model_construct(package_hash="0" * 64, **values)
        return cls.model_validate(
            {
                **unhashed.model_dump(mode="json", exclude={"package_hash"}),
                "package_hash": unhashed.calculated_hash(),
            }
        )

    def write(self, output_directory: str | Path) -> Path:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        path = output / "qualified_warpx_campaign_package.json"
        temporary = output / ".qualified_warpx_campaign_package.json.tmp"
        temporary.write_text(self.model_dump_json(indent=2) + "\n")
        os.replace(temporary, path)
        return path

    @classmethod
    def read_verified(cls, path: str | Path) -> QualifiedWarpXCampaignPackage:
        package = cls.model_validate_json(Path(path).read_text())
        if not package.verify_hash():
            raise ValueError("qualified WarpX campaign package hash does not match its contents")
        return package


def build_qualified_warpx_campaign_package(
    *,
    campaign_id: str,
    ledger: SQLiteEventLedger,
    instrument: QualifiedWarpXInstrument,
    campaign_report: MultiActionCampaignReport,
) -> QualifiedWarpXCampaignPackage:
    if campaign_report.campaign_id != campaign_id:
        raise ValueError("campaign report targets a different campaign")
    discovery_state = next(
        state
        for state in campaign_report.action_states
        if "search_report" in (state.execution.output if state.execution else {})
    )
    confirmation_state = next(
        state
        for state in campaign_report.action_states
        if "confirmation_report" in (state.execution.output if state.execution else {})
        and "qualification_hash" in (state.execution.output if state.execution else {})
    )
    assert discovery_state.execution is not None
    assert confirmation_state.execution is not None
    output = confirmation_state.execution.output
    search_report = BlindedSearchReport.model_validate(
        discovery_state.execution.output["search_report"]
    )
    confirmation_report = WarpXConfirmationReport.model_validate(output["confirmation_report"])
    evidence = tuple(RunEvidence.model_validate(item) for item in output["evidence"])
    claim = Claim.model_validate(output["claim"])
    events = ledger.load(campaign_id)
    completed = next(
        event for event in reversed(events) if event.event_type == "multi_action_campaign_completed"
    )
    hypothesis, _ = build_problem()
    return QualifiedWarpXCampaignPackage.create(
        campaign_id=campaign_id,
        hypothesis=hypothesis,
        instrument=instrument,
        search_report=search_report,
        confirmation_report=confirmation_report,
        evidence=evidence,
        claim=claim,
        campaign_report=campaign_report,
        provenance_event_hashes=tuple(event.event_hash for event in events),
        generated_at=datetime.fromisoformat(completed.created_at),
    )
