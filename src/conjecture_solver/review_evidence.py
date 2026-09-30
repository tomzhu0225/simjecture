"""Bounded, verified JSON retrieval for tool-free methods/progress reviewers."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field

from .evidence_paths import evidence_value
from .research_audit import strict_json


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    experiment: str = Field(pattern=r"^exp_[A-Za-z0-9_-]+$", max_length=100)
    output: str | None = Field(default=None, max_length=256)
    path: str | None = Field(default=None, max_length=1024)


def fetch_evidence(service, requests):
    results = []
    for request in requests:
        result = dict(request=request, authority="recorded_artifact_not_scientific_approval")
        try:
            record = service._read("experiments", request["experiment"])
            result.update(execution=record["status"], stage=record.get("stage"))
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
                    or file.stat().st_size > 262144
                ):
                    raise ValueError("Request a recorded JSON output of at most 256 KiB")
                with file.open("rb") as stream:
                    payload = stream.read(262145)
                if len(payload) > 262144:
                    raise ValueError("Recorded JSON exceeds 256 KiB")
                if hashlib.sha256(payload).hexdigest() != meta["sha256"]:
                    raise ValueError("Recorded output has changed; retrieval rejected")
                document = strict_json(payload.decode())
                value = (
                    evidence_value(document, request["path"]) if request.get("path") else document
                )
                result["sha256"] = meta["sha256"]
                if len(json.dumps(value, ensure_ascii=False).encode()) > 12000:
                    result["available_keys"] = list(value)[:24] if isinstance(value, dict) else None
                    raise ValueError(
                        "Value exceeds review excerpt budget; request a narrower JSON path"
                    )
                result["value"] = value
        except (ValueError, KeyError, OSError) as error:
            result["error"] = str(error)[:350]
        results.append(result)
    return results
