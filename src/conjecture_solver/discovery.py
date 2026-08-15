"""Self-verifying export package for one computational discovery."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field

from .adapters.base import NormalizedResult
from .models import AttemptRecord, Claim, ExperimentSpec, HypothesisNode, RunEvidence, StrictModel


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class DiscoveryPackage(StrictModel):
    """Portable result with a hash over all scientific and provenance fields."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    campaign_id: str
    hypothesis: HypothesisNode
    experiment: ExperimentSpec
    attempt: AttemptRecord
    evidence: RunEvidence
    claim: Claim
    normalized_result: NormalizedResult
    provenance_event_hashes: tuple[str, ...] = Field(min_length=1)
    generated_at: datetime
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    def calculated_hash(self) -> str:
        content = self.model_dump(mode="json", exclude={"package_hash"})
        return hashlib.sha256(_canonical_json(content).encode()).hexdigest()

    def verify_hash(self) -> bool:
        return self.package_hash == self.calculated_hash()

    @classmethod
    def create(cls, **values: object) -> DiscoveryPackage:
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
        path = output / "discovery_package.json"
        temporary = output / ".discovery_package.json.tmp"
        temporary.write_text(self.model_dump_json(indent=2) + "\n")
        os.replace(temporary, path)
        return path

    @classmethod
    def read_verified(cls, path: str | Path) -> DiscoveryPackage:
        package = cls.model_validate_json(Path(path).read_text())
        if not package.verify_hash():
            raise ValueError("discovery package hash does not match its contents")
        return package
