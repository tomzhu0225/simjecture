"""Host-owned semantic review gates, separate from model-owned evidence contracts.

Legacy campaigns remain readable. New persistent supervisors require this gate;
workers can propose contracts but cannot approve them through scientific tools.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .evidence_paths import evidence_path_parts


class ReviewVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approved|rejected)$")
    rationale: str = Field(min_length=16)
    evidence_gaps: list[str]
    next_test: str | None = Field(
        default=None,
        description=(
            "Suggested follow-up action; required changes belong in evidence_gaps "
            "and require rejection."
        ),
    )

    @model_validator(mode="after")
    def coherent(self):
        if self.decision == "approved" and self.evidence_gaps:
            raise ValueError("Approval cannot retain required design or evidence gaps")
        if self.decision == "rejected" and not self.evidence_gaps:
            raise ValueError("Rejection must identify evidence gaps")
        return self


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class ScientificReviews:
    def __init__(self, host):
        self.host = host
        self.path = Path(host.output) / "scientific_reviews.json"

    def packet(self, claim_id: str, stage: str) -> dict[str, Any]:
        if stage not in {"contract", "qualification"}:
            raise ValueError("Unknown scientific review stage")
        claim = self.host.claim_store.ledger.by_id()[claim_id]
        if not claim.evidence_contracts:
            raise ValueError("Review requires a proposed contract")
        contract = claim.evidence_contracts[-1]
        body = dict(
            stage=stage,
            claim_id=claim.id,
            claim_kind=claim.kind.value,
            original_hypothesis=self.host.hypothesis,
            statement=claim.statement,
            parent_id=claim.parent_id,
            relation=claim.relation.value,
            contract=contract.model_dump(mode="json"),
            sources=[],
        )
        protocol = Path(self.host.output) / "operator_input" / "scientific_protocol.txt"
        if protocol.exists():
            body["operator_protocol"] = protocol.read_text()
        bindings = [contract.execution_binding] if contract.execution_binding else []
        bindings += list(contract.additional_execution_bindings)
        for binding in bindings:
            source = self.host.sandbox._path(binding.program_path).read_text()
            if not isinstance(source, str) or len(source.encode()) > 131072:
                raise ValueError("Review requires a complete source file of at most 128 KiB")
            observed = hashlib.sha256(source.encode()).hexdigest()
            if observed != binding.program_sha256:
                raise ValueError("Review source differs from contract program hash")
            body["sources"].append(dict(path=binding.program_path, sha256=observed, source=source))
        # Include parent semantics, so a repair/instrument cannot redefine the target.
        if claim.parent_id:
            parent = self.host.claim_store.ledger.by_id()[claim.parent_id]
            body["parent_statement"] = parent.statement
        metadata_fields = {
            "stage",
            "returncode",
            "return_code",
            "return_code_zero",
            "plot_count",
            "evidentiary",
            "reached_horizon",
            "completed",
            "execution_succeeded",
            "scientific_evidence_eligible",
        }
        aspects = {}
        for check in contract.validation_checks:
            if check.aspect is not None:
                aspects.setdefault(check.aspect.value, []).append(check.json_path)
        body["deterministic_issues"] = [
            f"{aspect} is checked only with execution metadata, not physical validation"
            for aspect, paths in aspects.items()
            if aspect != "interface"
            and all(
                next((key for key in reversed(evidence_path_parts(path)) if not key.isdigit()), "")
                in metadata_fields
                for path in paths
            )
        ]
        if stage == "qualification":
            if claim.kind.value not in {"instrument", "diagnostic", "control"}:
                raise ValueError("Scientific claims require scientific adjudication")
            evidence = [e for e in claim.evidence if e.contract_version == contract.version]
            if not evidence:
                raise ValueError("Qualification review requires linked prospective evidence")
            body["evidence"] = []
            for item in evidence:
                document = self.host.sandbox.read_json_artifact(item.path)
                meta = self.host.sandbox.artifact_metadata(item.path)
                if meta["sha256"] != item.provenance.sha256:
                    raise ValueError("Qualification evidence changed after linking")
                body["evidence"].append(
                    dict(record=item.model_dump(mode="json"), document=document)
                )
        if len(json.dumps(body).encode()) > 1_000_000:
            raise ValueError("Review packet exceeds 1 MB; provide concise auditable evidence")
        return body

    def decision(self, packet):
        records = json.loads(self.path.read_text()) if self.path.exists() else {}
        return records.get(digest(packet))

    def require(self, claim_id: str, stage: str):
        packet = self.packet(claim_id, stage)
        record = self.decision(packet)
        if not record or record["verdict"]["decision"] != "approved":
            raise ValueError(
                f"Independent {stage} review required for {claim_id}; "
                "request host review; workbench development may continue"
            )

    def record(self, packet, verdict, *, reviewer, transcript_sha256):
        """Host-only commit; exact current packet must still match the frozen case."""
        verdict = ReviewVerdict.model_validate(verdict)
        current = self.packet(packet["claim_id"], packet["stage"])
        if verdict.decision == "approved" and current["deterministic_issues"]:
            raise ValueError(
                "Cannot approve metadata-only qualification: "
                + "; ".join(current["deterministic_issues"])
            )
        if digest(current) != digest(packet):
            raise ValueError("Scientific review case changed while judge was running")
        if not reviewer or len(transcript_sha256) != 64:
            raise ValueError("Review requires reviewer and transcript identity")
        records = json.loads(self.path.read_text()) if self.path.exists() else {}
        key = digest(packet)
        record = dict(
            packet_sha256=key,
            claim_id=packet["claim_id"],
            stage=packet["stage"],
            verdict=verdict.model_dump(),
            reviewer=reviewer,
            transcript_sha256=transcript_sha256,
        )
        if key in records and records[key] != record:
            raise ValueError("Review record is immutable; revise the case for a new review")
        records[key] = record
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w") as stream:
            stream.write(json.dumps(records, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        return record

    def guard(self, action):
        kind = getattr(action.action, "value", action.action)
        claim_id = getattr(action, "claim_id", None) or getattr(action, "active_claim_id", None)
        if not claim_id and kind in {"run_python", "run_capability"}:
            claim_id = "claim_root"
        if not claim_id:
            return
        claim = self.host.claim_store.ledger.by_id().get(claim_id)
        if claim is None:
            return
        stage = getattr(getattr(action, "stage", None), "value", None)
        if (
            kind == "run_capability"
            and stage != "workbench"
            or kind == "run_python"
            and claim.evidence_contracts
            or kind == "link_claim_evidence"
            and action.observation_sufficient
        ):
            self.require(claim_id, "contract")
        elif kind == "close_claim" and getattr(action.status, "value", None) == "supported":
            self.require(claim_id, "contract")
            if claim.kind.value != "scientific":
                self.require(claim_id, "qualification")
