"""Bounded, verified JSON retrieval for tool-free methods/progress reviewers."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .evidence_paths import evidence_value
from .research_audit import strict_json
from .research_receipts import InventorySelection, selected_inventory
from .review_assets import freeze_file, read_asset


class AssetSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    json_path: str | None = None
    offset: int = Field(default=0, ge=0)
    max_bytes: int = Field(default=16384, ge=1, le=65536)


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experiment: str | None = Field(default=None, pattern=r"^exp_[A-Za-z0-9_-]+$", max_length=100)
    output: str | None = Field(default=None, max_length=256)
    path: str | None = Field(default=None, max_length=1024)
    inventory: InventorySelection | None = None
    asset: AssetSelection | None = None

    @model_validator(mode="after")
    def separate_inventory_and_output(self):
        if self.asset is not None:
            if self.inventory is not None or self.output is not None or self.path is not None:
                raise ValueError("Request an asset page or an experiment output, not both")
            return self
        if self.experiment is None:
            raise ValueError("Choose an experiment output or recorded review asset")
        if self.inventory is not None and (self.output is not None or self.path is not None):
            raise ValueError("Request an inventory excerpt or an output value, not both")
        return self


def fetch_evidence(service, requests):
    results = []
    for request in requests:
        result = dict(request=request, authority="recorded_artifact_not_scientific_approval")
        try:
            if request.get("asset") is not None:
                selection = AssetSelection.model_validate(request["asset"]).model_dump()
                result["asset"] = read_asset(service.root, selection.pop("sha256"), **selection)
                results.append(result)
                continue
            record = service._read("experiments", request["experiment"])
            result.update(execution=record["status"], stage=record.get("stage"))
            if request.get("inventory") is not None:
                result["inventory"] = selected_inventory(service, record, request["inventory"])
                results.append(result)
                continue
            output = request.get("output")
            if output is None:
                result["outputs"] = {
                    name: record.get("artifacts", {}).get(name)
                    for name in record.get("outputs", [])[:16]
                }
                result["missing_outputs"] = record.get("missing_outputs", [])[:16]
            else:
                if output not in record.get("outputs", []):
                    raise ValueError("Not a declared output of this experiment")
                meta = record.get("artifacts", {}).get(output)
                workspace = service.root / "experiments" / request["experiment"] / "workspace"
                file = workspace / output
                if (
                    not meta
                    or not file.is_file()
                    or file.is_symlink()
                    or not file.resolve().is_relative_to(workspace.resolve())
                    or file.suffix != ".json"
                ):
                    raise ValueError("Request a recorded JSON output")
                payload = file.read_bytes()
                if hashlib.sha256(payload).hexdigest() != meta["sha256"]:
                    raise ValueError("Recorded output has changed; retrieval rejected")
                document = strict_json(payload.decode())
                value = (
                    evidence_value(document, request["path"]) if request.get("path") else document
                )
                result["sha256"] = meta["sha256"]
                if len(json.dumps(value, ensure_ascii=False).encode()) > 12000:
                    result["available_keys"] = list(value)[:24] if isinstance(value, dict) else None
                    reference = freeze_file(service.root, file, expected_sha256=meta["sha256"])
                    result["reference"] = reference
                    result["asset"] = read_asset(
                        service.root, reference["sha256"], json_path=request.get("path")
                    )
                    result["note"] = (
                        "Excerpt only; request further asset pages or a narrower JSON path"
                    )
                else:
                    result["value"] = value
        except (ValueError, KeyError, OSError) as error:
            result["error"] = str(error)[:350]
        results.append(result)
    return results
