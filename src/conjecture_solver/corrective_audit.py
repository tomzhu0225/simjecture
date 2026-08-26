"""Append-only corrective annotations for immutable campaign artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, model_validator

from .campaign_jobs import CampaignInterprocessLock
from .models import StrictModel, utc_now

CORRECTIVE_AUDIT_FILE = "corrective_audits.json"


class CorrectiveArtifactIdentity(StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)


class CorrectiveAuditRecord(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    record_id: str = Field(pattern=r"^audit_[a-f0-9]{32}$")
    reviewer: str = Field(min_length=1, max_length=200)
    finding: str = Field(min_length=16)
    corrected_interpretation: str = Field(min_length=16)
    artifacts: tuple[CorrectiveArtifactIdentity, ...] = Field(min_length=1)
    previous_record_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    recorded_at: datetime
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    def calculated_sha256(self) -> str:
        payload = self.model_dump(mode="json", exclude={"record_sha256"})
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    @model_validator(mode="after")
    def digest_matches_record(self) -> CorrectiveAuditRecord:
        if self.record_sha256 != self.calculated_sha256():
            raise ValueError("corrective audit record digest does not match its content")
        return self


class CorrectiveAuditLedger(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    records: tuple[CorrectiveAuditRecord, ...] = ()

    @model_validator(mode="after")
    def hash_chain_is_contiguous(self) -> CorrectiveAuditLedger:
        previous: str | None = None
        seen: set[str] = set()
        for record in self.records:
            if record.record_id in seen:
                raise ValueError("corrective audit record IDs must be unique")
            if record.previous_record_sha256 != previous:
                raise ValueError("corrective audit hash chain is not contiguous")
            seen.add(record.record_id)
            previous = record.record_sha256
        return self


def _artifact_identity(root: Path, relative: str) -> CorrectiveArtifactIdentity:
    normalized = PurePosixPath(relative)
    if normalized.is_absolute() or relative in {"", "."} or ".." in normalized.parts:
        raise ValueError("corrective audit artifact paths must stay inside the campaign")
    path = root / normalized
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"corrective audit artifact is not a regular file: {relative}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return CorrectiveArtifactIdentity(
        path=normalized.as_posix(),
        sha256=digest.hexdigest(),
        bytes=size,
    )


def load_corrective_audits(campaign: str | Path) -> CorrectiveAuditLedger:
    root = Path(campaign).expanduser().resolve()
    path = root / CORRECTIVE_AUDIT_FILE
    if not path.exists():
        return CorrectiveAuditLedger()
    if path.is_symlink() or not path.is_file():
        raise ValueError("corrective audit ledger must be a regular file")
    return CorrectiveAuditLedger.model_validate_json(path.read_text(encoding="utf-8"))


def append_corrective_audit(
    campaign: str | Path,
    *,
    reviewer: str,
    finding: str,
    corrected_interpretation: str,
    artifacts: tuple[str, ...],
    recorded_at: datetime | None = None,
) -> CorrectiveAuditRecord:
    """Append a hash-chained annotation without rewriting scientific records."""

    root = Path(campaign).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"campaign directory does not exist: {root}")
    with CampaignInterprocessLock(root):
        ledger = load_corrective_audits(root)
        identities = tuple(_artifact_identity(root, path) for path in artifacts)
        previous = ledger.records[-1].record_sha256 if ledger.records else None
        values: dict[str, Any] = {
            "record_id": f"audit_{uuid4().hex}",
            "reviewer": reviewer,
            "finding": finding,
            "corrected_interpretation": corrected_interpretation,
            "artifacts": identities,
            "previous_record_sha256": previous,
            "recorded_at": recorded_at or utc_now(),
        }
        unsigned = CorrectiveAuditRecord.model_construct(
            **values,
            record_sha256="0" * 64,
        )
        values["record_sha256"] = unsigned.calculated_sha256()
        record = CorrectiveAuditRecord.model_validate(values)
        updated = CorrectiveAuditLedger(records=(*ledger.records, record))
        path = root / CORRECTIVE_AUDIT_FILE
        temporary = root / f".{CORRECTIVE_AUDIT_FILE}.tmp"
        temporary.write_text(updated.model_dump_json(indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        return record
