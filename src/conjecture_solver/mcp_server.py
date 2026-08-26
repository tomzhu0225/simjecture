"""MCP/DSH bridge for the model-independent Simjecture campaign kernel.

The bridge is intentionally a thin adapter.  It owns no scientific state and
does not import the optional MCP SDK or :mod:`campaign_kernel` at module import
time.  This lets schema tests and kernel fakes run in the base installation,
while ``simjecture-mcp`` remains a normal stdio MCP server when the ``dsh``
extra is installed.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import importlib
import inspect
import json
import math
import os
import sys
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any, Protocol, TypeVar

from .mcp_schemas import (
    TOOL_SCHEMAS,
    tool_definitions,
    validate_tool_arguments,
)

MAX_DEFAULT_OUTPUT_CHARS = 30_000
MAX_OUTPUT_CHARS = 1_000_000
MAX_RESULT_DEPTH = 12
MAX_RESULT_ITEMS = 500
MAX_RESULT_STRING_CHARS = 16_384
DEFAULT_CLAIM_PAGE_SIZE = 24
MAX_CLAIM_PAGE_SIZE = 100
MAX_ROLE_CLAIMS = 1
MAX_FULL_CLAIMS = 8
MAX_ROLE_CONTRACTS = 2
MAX_ROLE_EVIDENCE = 8
MAX_ROLE_NOTE_CHARS = 400
MAX_ROLE_VALIDATION_RESULTS = 8
MAX_CLAIM_SUMMARY_STATEMENT_CHARS = 512
MAX_SNAPSHOT_HYPOTHESIS_CHARS = 2_048
MAX_SNAPSHOT_INSTRUCTION_CHARS = 8_192
MAX_SNAPSHOT_CLAIM_STATEMENT_CHARS = 256
MAX_SNAPSHOT_REPAIR_TEXT_CHARS = 256
MAX_SNAPSHOT_ARTIFACTS = 8
MAX_SNAPSHOT_JOBS = 8
MAX_SNAPSHOT_LITERATURE_SOURCES = 3
_T = TypeVar("_T")
_UNSET = object()


class CampaignKernelProtocol(Protocol):
    """The intentionally frozen subset consumed by this bridge."""

    @classmethod
    def open(cls, *args: Any, **kwargs: Any) -> Any: ...

    def snapshot(self) -> Any: ...

    def perform(self, action: Any, *, iteration: int = 0) -> Any: ...

    def execute_operation(
        self,
        operation_id: str,
        action: Any,
        *,
        timeout_seconds: float | None = None,
    ) -> Any: ...

    def start_job(self, request: Any) -> Any: ...

    def job_status(self, job_id: str) -> Any: ...

    def cancel_job(self, job_id: str) -> Any: ...

    def prepare_adjudication(self, operation_id: str, **kwargs: Any) -> Any: ...

    def record_adjudication(self, operation_id: str, **kwargs: Any) -> Any: ...

    def finalize_campaign(self, operation_id: str, **kwargs: Any) -> Any: ...


class MCPBridgeError(RuntimeError):
    """Base error raised for bridge setup/dispatch failures."""


class MCPInputError(ValueError):
    """Raised before a malformed tool call reaches the campaign kernel."""


MAX_HYPOTHESIS_CHARS = 16_384


def _read_hypothesis_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise MCPBridgeError(f"cannot read hypothesis file {path}: {error}") from error
    hypothesis = text.strip()
    if not hypothesis:
        raise MCPBridgeError(f"hypothesis file is empty: {path}")
    if len(text) > MAX_HYPOTHESIS_CHARS:
        raise MCPBridgeError(
            f"hypothesis file exceeds the {MAX_HYPOTHESIS_CHARS}-character limit: {path}"
        )
    # StrictModel canonicalizes operator hypotheses this way before writing
    # launch/manifest records.  Apply the same rule at the host boundary so a
    # normal POSIX text file's trailing newline does not change root identity
    # across an MCP restart.
    return hypothesis


@dataclasses.dataclass(frozen=True, slots=True)
class BridgeConfig:
    """Host-controlled configuration for one bridge process."""

    workspace: Path = dataclasses.field(default_factory=Path.cwd)
    campaign: str | None = None
    hypothesis_file: Path | None = None
    capabilities: Path | None = None
    skills: Path | None = None
    max_output_chars: int = MAX_DEFAULT_OUTPUT_CHARS
    default_timeout_seconds: float = 600.0

    def __post_init__(self) -> None:
        workspace = Path(self.workspace).expanduser().resolve()
        object.__setattr__(self, "workspace", workspace)
        if self.hypothesis_file is not None:
            object.__setattr__(
                self,
                "hypothesis_file",
                Path(self.hypothesis_file).expanduser().resolve(),
            )
        if self.capabilities is not None:
            object.__setattr__(
                self,
                "capabilities",
                Path(self.capabilities).expanduser().resolve(),
            )
        if self.skills is not None:
            object.__setattr__(self, "skills", Path(self.skills).expanduser().resolve())
        if not 1_024 <= self.max_output_chars <= MAX_OUTPUT_CHARS:
            raise ValueError(f"max_output_chars must lie in [1024, {MAX_OUTPUT_CHARS}]")
        if not math.isfinite(self.default_timeout_seconds) or self.default_timeout_seconds <= 0:
            raise ValueError("default_timeout_seconds must be finite and positive")

    @classmethod
    def from_environment(cls) -> BridgeConfig:
        """Resolve explicit ``SIMJECTURE_*`` settings without importing DSH."""

        workspace = Path(os.environ.get("SIMJECTURE_WORKSPACE", os.getcwd()))
        campaign = (
            os.environ.get("SIMJECTURE_CAMPAIGN")
            or os.environ.get("SIMJECTURE_CAMPAIGN_ID")
            or None
        )
        hypothesis_file = os.environ.get("SIMJECTURE_HYPOTHESIS_FILE") or None
        capabilities = os.environ.get("SIMJECTURE_CAPABILITIES") or None
        skills = os.environ.get("SIMJECTURE_SKILLS") or None
        try:
            max_output_chars = int(
                os.environ.get(
                    "SIMJECTURE_MCP_MAX_OUTPUT_CHARS",
                    str(MAX_DEFAULT_OUTPUT_CHARS),
                )
            )
        except ValueError as error:
            raise ValueError("SIMJECTURE_MCP_MAX_OUTPUT_CHARS must be an integer") from error
        try:
            default_timeout = float(os.environ.get("SIMJECTURE_MCP_TIMEOUT_SECONDS", "600"))
        except ValueError as error:
            raise ValueError("SIMJECTURE_MCP_TIMEOUT_SECONDS must be numeric") from error
        return cls(
            workspace=workspace,
            campaign=campaign,
            hypothesis_file=Path(hypothesis_file) if hypothesis_file else None,
            capabilities=Path(capabilities) if capabilities else None,
            skills=Path(skills) if skills else None,
            max_output_chars=max_output_chars,
            default_timeout_seconds=default_timeout,
        )


def _jsonable(value: Any, *, depth: int = 0) -> Any:
    """Convert Pydantic/dataclass/enum values into strict JSON values."""

    if depth > MAX_RESULT_DEPTH:
        return "... result depth truncated ..."
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item, depth=depth + 1)
            for key, item in list(value.items())[:MAX_RESULT_ITEMS]
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item, depth=depth + 1) for item in list(value)[:MAX_RESULT_ITEMS]]
    if isinstance(value, bytes):
        return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _jsonable(model_dump(mode="json"), depth=depth + 1)
        except TypeError:
            return _jsonable(model_dump(), depth=depth + 1)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _jsonable(dataclasses.asdict(value), depth=depth + 1)
    enum_value = getattr(value, "value", None)
    if enum_value is not None and enum_value is not value:
        return _jsonable(enum_value, depth=depth + 1)
    return str(value)


def _compact_json(value: Any) -> str:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        default=str,
    )


def _bound_result(value: Any, maximum: int) -> Any:
    """Return JSON-safe output whose encoded size is bounded.

    The normal path preserves the kernel result shape.  If a pathological
    result still exceeds the configured budget, a deterministic digest and a
    head/tail preview preserve enough information for an operator to locate the
    full durable receipt without flooding DSH's context window.
    """

    converted = _jsonable(value)
    encoded = _compact_json(converted)
    if len(encoded) <= maximum:
        return converted
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    preview_chars = max(0, maximum - 180)
    while True:
        head = preview_chars // 2
        tail = preview_chars - head
        preview = encoded[:head]
        if preview_chars < len(encoded):
            preview += "..."
        if tail:
            preview += encoded[-tail:]
        bounded = {
            "truncated": True,
            "sha256": digest,
            "bytes": len(encoded.encode()),
            "preview": preview,
        }
        overflow = len(_compact_json(bounded)) - maximum
        if overflow <= 0:
            return bounded
        if preview_chars == 0:  # pragma: no cover - BridgeConfig has a 1 KiB floor
            bounded.pop("preview")
            return bounded
        preview_chars = max(0, preview_chars - max(1, overflow))


def _clip_text(value: Any, maximum: int) -> tuple[str, bool, str]:
    text = "" if value is None else str(value)
    truncated = len(text) > maximum
    return (
        text[:maximum] + "..." if truncated else text,
        truncated,
        hashlib.sha256(text.encode()).hexdigest(),
    )


def _snapshot_repair(repair: Any) -> dict[str, Any] | None:
    if not isinstance(repair, Mapping):
        return None
    projected: dict[str, Any] = {
        "counterexample_paths": list(repair.get("counterexample_paths", []))[-8:]
        if isinstance(repair.get("counterexample_paths"), list)
        else [],
    }
    for key in ("accommodation", "semantic_change", "falsification_condition"):
        text, truncated, digest = _clip_text(
            repair.get(key),
            MAX_SNAPSHOT_REPAIR_TEXT_CHARS,
        )
        projected[key] = text
        projected[f"{key}_truncated"] = truncated
        projected[f"{key}_sha256"] = digest
    return projected


def _snapshot_claim_ledger(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    raw_claims = value.get("claims")
    claims = raw_claims if isinstance(raw_claims, list) else []
    projected = []
    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        statement, truncated, digest = _clip_text(
            claim.get("statement"),
            MAX_SNAPSHOT_CLAIM_STATEMENT_CHARS,
        )
        projected.append(
            {
                "id": claim.get("id"),
                "kind": claim.get("kind"),
                "relation": claim.get("relation"),
                "parent_id": claim.get("parent_id"),
                "status": claim.get("status"),
                "statement": statement,
                "statement_truncated": truncated,
                "statement_sha256": digest,
                "repair": _snapshot_repair(claim.get("repair")),
                "evidence_contract_count": claim.get("evidence_contract_count", 0),
                "evidence_count": claim.get("evidence_count", 0),
                "decisive_contract_version": claim.get("decisive_contract_version"),
            }
        )
    return {
        "schema_version": value.get("schema_version"),
        "claim_count": value.get("claim_count", len(projected)),
        "open_count": value.get("open_count"),
        "claims": projected,
    }


def _snapshot_guided_commissioning(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    description, description_truncated, description_sha256 = _clip_text(
        value.get("description"),
        512,
    )
    validation, validation_truncated, validation_sha256 = _clip_text(
        value.get("operator_validation"),
        512,
    )
    files = value.get("files")
    return {
        "available": value.get("available"),
        "schema_version": value.get("schema_version"),
        "name": value.get("name"),
        "description": description,
        "description_truncated": description_truncated,
        "description_sha256": description_sha256,
        "capability": value.get("capability"),
        "program_path": value.get("program_path"),
        "validation_summary_path": value.get("validation_summary_path"),
        "operator_validation": validation,
        "operator_validation_truncated": validation_truncated,
        "operator_validation_sha256": validation_sha256,
        "file_count": len(files) if isinstance(files, list) else 0,
        "files": [
            {
                "path": item.get("path"),
                "bytes": item.get("bytes"),
                "sha256": item.get("sha256"),
            }
            for item in (files or [])
            if isinstance(item, Mapping)
        ],
        "package_sha256": value.get("package_sha256"),
    }


def _snapshot_artifacts(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    raw_artifacts = value.get("artifacts")
    items = list(raw_artifacts.items()) if isinstance(raw_artifacts, Mapping) else []
    selected = items[-MAX_SNAPSHOT_ARTIFACTS:]
    return {
        "schema_version": value.get("schema_version"),
        "artifact_count": value.get("artifact_count", len(items)),
        "artifacts_truncated": value.get("artifacts_truncated") is True
        or len(items) > len(selected),
        "artifacts": {
            str(path): {
                "bytes": record.get("bytes"),
                "active_claim_id": record.get("active_claim_id"),
                "evidence_candidate": record.get("evidence_candidate"),
                "evidence_eligible": record.get("evidence_eligible"),
                "execution_succeeded": record.get("execution_succeeded"),
                "execution_stage": record.get("execution_stage"),
                "capability": record.get("capability"),
                "program_path": record.get("program_path"),
                "program_sha256": record.get("program_sha256"),
                "operation_id": record.get("operation_id"),
                "job_id": record.get("job_id"),
                "job_status": record.get("job_status"),
            }
            for path, record in selected
            if isinstance(record, Mapping)
        },
    }


def _snapshot_literature_search(search: Any) -> dict[str, Any] | None:
    if not isinstance(search, Mapping):
        return None
    query, query_truncated, query_sha256 = _clip_text(search.get("query"), 256)
    purpose, purpose_truncated, purpose_sha256 = _clip_text(search.get("purpose"), 384)
    sources = search.get("sources")
    sources = sources if isinstance(sources, list) else []
    selected_sources = sources[:MAX_SNAPSHOT_LITERATURE_SOURCES]
    return {
        "id": search.get("id"),
        "query": query,
        "query_truncated": query_truncated,
        "query_sha256": query_sha256,
        "purpose": purpose,
        "purpose_truncated": purpose_truncated,
        "purpose_sha256": purpose_sha256,
        "status": search.get("status"),
        "provider_status": search.get("provider_status"),
        "errors": search.get("errors"),
        "searched_at": search.get("searched_at"),
        "scientific_evidence_eligible": search.get("scientific_evidence_eligible"),
        "source_count": search.get("source_count", len(sources)),
        "sources_truncated": len(sources) > len(selected_sources),
        "sources": [
            {
                "id": source.get("id"),
                "kind": source.get("kind"),
                "provider": source.get("provider"),
                "title": _clip_text(source.get("title"), 160)[0],
                "publication_year": source.get("publication_year"),
                "doi": source.get("doi"),
                "url": source.get("url"),
            }
            for source in selected_sources
            if isinstance(source, Mapping)
        ],
    }


def _snapshot_jobs(value: Any) -> tuple[list[dict[str, Any]], bool]:
    jobs = value if isinstance(value, list) else []
    active_statuses = {"queued", "running", "cancel_requested", "outcome_unknown"}
    active = [
        job for job in jobs if isinstance(job, Mapping) and job.get("status") in active_statuses
    ]
    terminal_slots = max(0, MAX_SNAPSHOT_JOBS - len(active))
    terminal = [job for job in jobs if isinstance(job, Mapping) and job not in active]
    selected = active + (terminal[-terminal_slots:] if terminal_slots else [])
    return (
        [
            {
                "job_id": job.get("job_id"),
                "operation_id": job.get("operation_id"),
                "status": job.get("status"),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
                "cancellation_requested_at": job.get("cancellation_requested_at"),
            }
            for job in selected
        ],
        len(jobs) > len(selected),
    )


def _project_snapshot(value: Any, query: Mapping[str, Any]) -> Any:
    """Return a stable campaign overview without duplicating bulky receipts."""

    if not isinstance(value, Mapping):
        raise MCPBridgeError("CampaignKernel returned an invalid snapshot")
    view = query.get("view", "summary")
    if view == "full" or "hypothesis" not in value:
        return value
    manifest = value.get("manifest")
    manifest = manifest if isinstance(manifest, Mapping) else {}
    instruction = manifest.get("campaign_instruction")
    if view == "instruction":
        text, truncated, digest = _clip_text(instruction, MAX_RESULT_STRING_CHARS)
        return {
            "view": "instruction",
            "campaign_instruction": text,
            "campaign_instruction_truncated": truncated,
            "campaign_instruction_sha256": digest,
        }

    hypothesis, hypothesis_truncated, hypothesis_sha256 = _clip_text(
        value.get("hypothesis"),
        MAX_SNAPSHOT_HYPOTHESIS_CHARS,
    )
    instruction_text, instruction_truncated, instruction_sha256 = _clip_text(
        instruction,
        MAX_SNAPSHOT_INSTRUCTION_CHARS,
    )
    raw_searches = value.get("literature_searches")
    searches = raw_searches if isinstance(raw_searches, list) else []
    projected_searches = [
        projected
        for search in searches
        if (projected := _snapshot_literature_search(search)) is not None
    ]
    jobs, jobs_projected_truncated = _snapshot_jobs(value.get("jobs"))
    return {
        "view": "summary",
        "hypothesis": hypothesis,
        "hypothesis_truncated": hypothesis_truncated,
        "hypothesis_sha256": hypothesis_sha256,
        "manifest": {
            "schema_version": manifest.get("schema_version"),
            "campaign_instruction": instruction_text,
            "campaign_instruction_truncated": instruction_truncated,
            "campaign_instruction_sha256": instruction_sha256,
            "config": manifest.get("config"),
            "guided_commissioning": _snapshot_guided_commissioning(
                manifest.get("guided_commissioning")
            ),
            "claim_ledger_schema_version": manifest.get("claim_ledger_schema_version"),
            "literature_search": manifest.get("literature_search"),
            "system_prompt_profile": manifest.get("system_prompt_profile"),
            "system_prompt_sha256": manifest.get("system_prompt_sha256"),
        },
        "claim_ledger": _snapshot_claim_ledger(value.get("claim_ledger")),
        "skill_hashes": value.get("skill_hashes"),
        "capability_hashes": value.get("capability_hashes"),
        "artifact_provenance": _snapshot_artifacts(value.get("artifact_provenance")),
        "literature_search_count": value.get("literature_search_count", len(searches)),
        "literature_searches_truncated": value.get("literature_searches_truncated") is True,
        "literature_searches": projected_searches,
        "job_count": value.get("job_count"),
        "jobs_truncated": value.get("jobs_truncated") is True or jobs_projected_truncated,
        "jobs": jobs,
        "budget": value.get("budget"),
    }


def _claim_summary(claim: Mapping[str, Any]) -> dict[str, Any]:
    contracts = claim.get("evidence_contracts")
    evidence = claim.get("evidence")
    statement = str(claim.get("statement", ""))
    statement_truncated = len(statement) > MAX_CLAIM_SUMMARY_STATEMENT_CHARS
    return {
        "id": claim.get("id"),
        "statement": (
            statement[:MAX_CLAIM_SUMMARY_STATEMENT_CHARS] + "..."
            if statement_truncated
            else statement
        ),
        "statement_truncated": statement_truncated,
        "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
        "kind": claim.get("kind"),
        "relation": claim.get("relation"),
        "parent_id": claim.get("parent_id"),
        "status": claim.get("status"),
        "evidence_contract_count": len(contracts) if isinstance(contracts, list) else 0,
        "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
        "decisive_contract_version": claim.get("decisive_contract_version"),
        "updated_iteration": claim.get("updated_iteration"),
    }


def _tail_with_decisive_contract(
    contracts: list[Any],
    decisive_version: Any,
    *,
    maximum: int = MAX_ROLE_CONTRACTS,
) -> tuple[list[Any], bool]:
    """Keep the active contract tail and any older decisive contract."""

    if len(contracts) <= maximum:
        return contracts, False
    selected = list(contracts[-maximum:])
    if isinstance(decisive_version, int) and not isinstance(decisive_version, bool):
        decisive = next(
            (
                contract
                for contract in contracts
                if isinstance(contract, Mapping) and contract.get("version") == decisive_version
            ),
            None,
        )
        if decisive is not None and decisive not in selected:
            selected[0] = decisive
    return selected, True


def _clip_role_text(value: Any, maximum: int = MAX_ROLE_NOTE_CHARS) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= maximum:
        return text
    return text[:maximum] + "..."


def _evidence_execution_failed(evidence: Mapping[str, Any]) -> bool:
    provenance = evidence.get("provenance")
    if not isinstance(provenance, Mapping):
        provenance = {}
    return bool(
        evidence.get("validation_passed") is False
        or provenance.get("execution_succeeded") is False
        or provenance.get("execution_timed_out") is True
        or provenance.get("execution_workspace_exceeded") is True
        or provenance.get("job_status") in {"failed", "cancelled", "outcome_unknown"}
    )


def _select_role_evidence(
    evidence: list[Mapping[str, Any]],
    *,
    decisive_contract_version: Any,
    maximum: int = MAX_ROLE_EVIDENCE,
) -> tuple[list[Mapping[str, Any]], dict[str, int]]:
    """Select a bounded, chronologically ordered and outcome-balanced view."""

    categories = {
        "decisive": [
            index
            for index, item in enumerate(evidence)
            if decisive_contract_version is not None
            and item.get("contract_version") == decisive_contract_version
            and item.get("observation_sufficient") is True
        ],
        "sufficient": [
            index
            for index, item in enumerate(evidence)
            if item.get("observation_sufficient") is True
        ],
        "non_sufficient": [
            index
            for index, item in enumerate(evidence)
            if item.get("observation_sufficient") is not True
        ],
        "failed": [
            index for index, item in enumerate(evidence) if _evidence_execution_failed(item)
        ],
    }
    selected: set[int] = set()
    # Preserve the newest representative of every semantically important
    # category before filling the remaining budget from the chronological tail.
    for name in ("decisive", "sufficient", "failed", "non_sufficient"):
        if len(selected) >= maximum:
            break
        if categories[name]:
            selected.add(categories[name][-1])
    if evidence and len(selected) < maximum:
        selected.add(len(evidence) - 1)
    for index in range(len(evidence) - 1, -1, -1):
        if len(selected) >= maximum:
            break
        selected.add(index)

    selected_indices = sorted(selected)
    selected_evidence = [evidence[index] for index in selected_indices]
    counts: dict[str, int] = {
        "selected": len(selected_indices),
        "omitted": len(evidence) - len(selected_indices),
    }
    for name, indices in categories.items():
        retained = sum(index in selected for index in indices)
        counts[f"{name}_omitted"] = len(indices) - retained
    return selected_evidence, counts


def _compact_validation_results(
    value: Any,
    *,
    maximum: int = MAX_ROLE_VALIDATION_RESULTS,
) -> dict[str, Any]:
    raw = [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []
    failed = [index for index, item in enumerate(raw) if item.get("passed") is False]
    selected: set[int] = set(failed[-maximum:]) if maximum else set()
    for index in range(len(raw) - 1, -1, -1):
        if len(selected) >= maximum:
            break
        selected.add(index)
    projected = []
    for index in sorted(selected):
        item = raw[index]
        projected.append(
            {
                key: (_clip_role_text(item.get(key)) if key == "error" else item.get(key))
                for key in (
                    "aspect",
                    "json_path",
                    "expected_value",
                    "actual_value",
                    "passed",
                    "error",
                )
                if key in item
            }
        )
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str)
    return {
        "validation_results": projected,
        "validation_result_count": len(raw),
        "validation_results_omitted_count": len(raw) - len(projected),
        "validation_results_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def _role_evidence(
    evidence: Mapping[str, Any],
    *,
    maximum_validation_results: int = MAX_ROLE_VALIDATION_RESULTS,
) -> dict[str, Any]:
    provenance = evidence.get("provenance")
    if isinstance(provenance, Mapping):
        provenance = {
            key: provenance.get(key)
            for key in (
                "sha256",
                "bytes",
                "tracked",
                "evidence_eligible",
                "execution_succeeded",
                "execution_returncode",
                "execution_timed_out",
                "execution_workspace_exceeded",
                "execution_stage",
                "capability",
                "command_argv",
                "program_path",
                "program_sha256",
                "operation_id",
                "job_id",
                "job_status",
                "generated_iteration",
            )
            if key in provenance
        }
    else:
        provenance = None
    projected = {
        "path": evidence.get("path"),
        "note": _clip_role_text(evidence.get("note")),
        "contract_version": evidence.get("contract_version"),
        "observation_sufficient": evidence.get("observation_sufficient"),
        "observation_note": _clip_role_text(evidence.get("observation_note")),
        "commissioning_claim_id": evidence.get("commissioning_claim_id"),
        "validation_passed": evidence.get("validation_passed"),
        "iteration": evidence.get("iteration"),
        "provenance": provenance,
    }
    projected.update(
        _compact_validation_results(
            evidence.get("validation_results"),
            maximum=maximum_validation_results,
        )
    )
    return projected


def _claim_role_view(
    claim: Mapping[str, Any],
    *,
    maximum_contracts: int = MAX_ROLE_CONTRACTS,
    maximum_evidence: int = MAX_ROLE_EVIDENCE,
    maximum_validation_results: int = MAX_ROLE_VALIDATION_RESULTS,
) -> dict[str, Any]:
    raw_contracts = claim.get("evidence_contracts")
    contracts = list(raw_contracts) if isinstance(raw_contracts, list) else []
    selected_contracts, contracts_truncated = _tail_with_decisive_contract(
        contracts,
        claim.get("decisive_contract_version"),
        maximum=maximum_contracts,
    )
    raw_evidence = claim.get("evidence")
    evidence = (
        [item for item in raw_evidence if isinstance(item, Mapping)]
        if isinstance(raw_evidence, list)
        else []
    )
    selected_evidence, evidence_selection = _select_role_evidence(
        evidence,
        decisive_contract_version=claim.get("decisive_contract_version"),
        maximum=maximum_evidence,
    )
    return {
        "id": claim.get("id"),
        "statement": claim.get("statement"),
        "kind": claim.get("kind"),
        "relation": claim.get("relation"),
        "parent_id": claim.get("parent_id"),
        "status": claim.get("status"),
        "rationale": claim.get("rationale"),
        "repair": claim.get("repair"),
        "closed_reason": claim.get("closed_reason"),
        "decisive_contract_version": claim.get("decisive_contract_version"),
        "created_iteration": claim.get("created_iteration"),
        "updated_iteration": claim.get("updated_iteration"),
        "evidence_contract_count": len(contracts),
        "evidence_contracts_truncated": contracts_truncated,
        "evidence_contracts": selected_contracts,
        "evidence_count": len(evidence),
        "evidence_truncated": evidence_selection["omitted"] > 0,
        "evidence_omitted_count": evidence_selection["omitted"],
        "evidence_selection_omissions": {
            key.removesuffix("_omitted"): value
            for key, value in evidence_selection.items()
            if key.endswith("_omitted") and key != "omitted"
        },
        "evidence": [
            _role_evidence(
                item,
                maximum_validation_results=maximum_validation_results,
            )
            for item in selected_evidence
            if isinstance(item, Mapping)
        ],
    }


def _project_claims(
    value: Any,
    query: Mapping[str, Any],
    *,
    maximum_output_chars: int | None = None,
) -> dict[str, Any]:
    """Project a growing ledger before it crosses the bounded MCP surface."""

    if not isinstance(value, Mapping) or not isinstance(value.get("claims"), list):
        raise MCPBridgeError("CampaignKernel returned an invalid claim ledger")
    raw_claims = [item for item in value["claims"] if isinstance(item, Mapping)]
    view = query.get("view", "summary")
    claim_ids = query.get("claim_ids")
    parent_id = query.get("parent_id")
    offset = query.get("offset", 0)
    default_limit = (
        MAX_ROLE_CLAIMS
        if view == "role"
        else MAX_FULL_CLAIMS
        if view == "full"
        else DEFAULT_CLAIM_PAGE_SIZE
    )
    limit = query.get("limit", default_limit)

    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise MCPInputError("claims.offset must be a non-negative integer")
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
        or limit > MAX_CLAIM_PAGE_SIZE
    ):
        raise MCPInputError(f"claims.limit must lie in [1, {MAX_CLAIM_PAGE_SIZE}]")
    if view in {"role", "full"}:
        if not isinstance(claim_ids, list) or not claim_ids:
            raise MCPInputError(f"claims view={view} requires explicit claim_ids")
        maximum_ids = MAX_ROLE_CLAIMS if view == "role" else MAX_FULL_CLAIMS
        if len(claim_ids) > maximum_ids:
            raise MCPInputError(f"claims view={view} accepts at most {maximum_ids} claim_ids")
    if isinstance(claim_ids, list) and len(claim_ids) > MAX_CLAIM_PAGE_SIZE:
        raise MCPInputError(f"claims accepts at most {MAX_CLAIM_PAGE_SIZE} claim_ids per request")

    requested_ids: list[str] | None = None
    if isinstance(claim_ids, list):
        requested_ids = []
        for claim_id in claim_ids:
            folded = str(claim_id).casefold()
            if folded and folded not in requested_ids:
                requested_ids.append(folded)
    folded_parent = parent_id.casefold() if isinstance(parent_id, str) else None
    matching = [
        claim
        for claim in raw_claims
        if (requested_ids is None or str(claim.get("id", "")).casefold() in requested_ids)
        and (folded_parent is None or str(claim.get("parent_id", "")).casefold() == folded_parent)
    ]
    page = matching[offset : offset + limit]
    available_ids = {str(claim.get("id", "")).casefold() for claim in raw_claims}
    ledger = value.get("claim_ledger")
    ledger = ledger if isinstance(ledger, Mapping) else {}

    def result_with(projected: list[Any]) -> dict[str, Any]:
        return {
            "view": view,
            "claim_ledger": {
                "schema_version": ledger.get("schema_version"),
                "claim_count": len(raw_claims),
                "open_count": sum(claim.get("status") == "open" for claim in raw_claims),
            },
            "matching_claim_count": len(matching),
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(page) < len(matching),
            "missing_claim_ids": (
                []
                if requested_ids is None
                else [claim_id for claim_id in requested_ids if claim_id not in available_ids]
            ),
            "claims": projected,
        }

    if view == "summary":
        return result_with([_claim_summary(claim) for claim in page])
    if view != "role":
        return result_with(list(page))

    # A role projection is a control-plane object, not a bulky archival view.
    # It must retain its shape so DSH can continue a fresh role even after a
    # claim has accumulated many failed observations. First retain the active
    # contract (and an older decisive contract when applicable), then reduce
    # repeated per-evidence validation detail until the configured wire budget
    # is met. Counts and hashes still expose every omitted record.
    validation_limits = (MAX_ROLE_VALIDATION_RESULTS, 4, 2, 1, 0)
    last_result: dict[str, Any] | None = None
    for evidence_limit in range(MAX_ROLE_EVIDENCE, 0, -1):
        for validation_limit in validation_limits:
            candidate = result_with(
                [
                    _claim_role_view(
                        claim,
                        maximum_evidence=evidence_limit,
                        maximum_validation_results=validation_limit,
                    )
                    for claim in page
                ]
            )
            last_result = candidate
            if (
                maximum_output_chars is None
                or len(_compact_json(candidate)) <= maximum_output_chars
            ):
                return candidate
    return last_result if last_result is not None else result_with([])


def _maybe_await(value: _T | Awaitable[_T]) -> Awaitable[_T] | _T:
    return value


async def _await_result(value: _T | Awaitable[_T]) -> _T:
    if inspect.isawaitable(value):
        return await value
    return value


def _signature_parameters(
    function: Callable[..., Any],
) -> tuple[dict[str, inspect.Parameter], bool]:
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return {}, True
    parameters = dict(signature.parameters)
    has_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    return parameters, has_kwargs


def _filtered_kwargs(function: Callable[..., Any], candidates: Mapping[str, Any]) -> dict[str, Any]:
    parameters, has_kwargs = _signature_parameters(function)
    if has_kwargs:
        return dict(candidates)
    return {key: value for key, value in candidates.items() if key in parameters}


class CampaignMCPBridge:
    """Expose one campaign kernel through explicit scientific MCP tools."""

    def __init__(
        self,
        kernel: CampaignKernelProtocol | Any | None = None,
        *,
        config: BridgeConfig | None = None,
        kernel_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config or BridgeConfig.from_environment()
        self._kernel = kernel
        self._kernel_factory = kernel_factory
        self._opening: Awaitable[Any] | None = None
        self._startup_snapshot: Any = _UNSET
        self._lifetime_lock: Any | None = None

    @property
    def kernel_loaded(self) -> bool:
        return self._kernel is not None

    @classmethod
    def from_environment(
        cls,
        *,
        kernel: CampaignKernelProtocol | Any | None = None,
        kernel_factory: Callable[..., Any] | None = None,
    ) -> CampaignMCPBridge:
        return cls(
            kernel,
            config=BridgeConfig.from_environment(),
            kernel_factory=kernel_factory,
        )

    async def _ensure_kernel(self) -> Any:
        if self._kernel is not None:
            return self._kernel
        if self._opening is not None:
            self._kernel = await self._opening
            self._opening = None
            return self._kernel
        self._opening = self._open_kernel()
        try:
            self._kernel = await self._opening
            return self._kernel
        finally:
            self._opening = None

    async def startup(self) -> Any:
        """Open the campaign and validate its first snapshot before MCP I/O.

        DSH treats a successful MCP handshake as permission to start a
        scientific session.  Opening a kernel lazily from the first tool call
        would therefore let a broken campaign appear healthy until after the
        model had already started planning.  The stdio entry point calls this
        method before creating the transport; direct embedders can call it as
        an explicit readiness check as well.
        """

        if self._startup_snapshot is not _UNSET:
            return self._startup_snapshot
        try:
            self._acquire_lifetime_lock()
            await self._ensure_kernel()
            snapshot = await self._kernel_method("snapshot")
            bounded = _bound_result(snapshot, self.config.max_output_chars)
        except MCPBridgeError:
            self.shutdown()
            raise
        except Exception as error:
            self.shutdown()
            raise MCPBridgeError(f"CampaignKernel startup/open/snapshot failed: {error}") from error
        self._startup_snapshot = bounded
        return bounded

    def _acquire_lifetime_lock(self) -> None:
        """Own the campaign for the complete root MCP process lifetime.

        The short campaign writer flock serializes durable commits, but it
        cannot make two long-lived hosts' in-memory ledgers coherent.  The
        existing runner lock is therefore also the supervisor lease shared by
        the legacy CLI runner and a root MCP bridge.  Detached kernel workers
        do not construct this bridge and remain deliberately exempt.
        """

        if self._lifetime_lock is not None:
            return
        from .mvp_launch import MVPOutputLock, RunAlreadyActiveError

        target = self._campaign_candidates()[0]
        lock = MVPOutputLock(target)
        try:
            lock.__enter__()
        except RunAlreadyActiveError as error:
            raise MCPBridgeError(
                f"cannot attach MCP bridge to an active campaign: {target}: {error}"
            ) from error
        self._lifetime_lock = lock

    def shutdown(self) -> None:
        """Release the root campaign ownership lease, if held."""

        lock, self._lifetime_lock = self._lifetime_lock, None
        if lock is not None:
            lock.__exit__(None, None, None)

    def _campaign_candidates(self) -> tuple[Path, ...]:
        candidates: list[Path] = []
        if self.config.campaign:
            campaign = Path(self.config.campaign).expanduser()
            if campaign.is_absolute():
                target = campaign.resolve()
            else:
                direct = self.config.workspace / campaign
                grouped = self.config.workspace / "campaigns" / campaign
                target = (direct if direct.exists() or not grouped.exists() else grouped).resolve()
            candidates.append(target)
        else:
            candidates.append(self.config.workspace)
        unique: list[Path] = []
        for candidate in candidates:
            resolved = candidate.expanduser().resolve()
            if resolved not in unique:
                unique.append(resolved)
        return tuple(unique)

    @staticmethod
    def _launch_hypothesis(candidate: Path) -> str | None:
        """Read and verify the operator launch contract when one exists."""

        launch_path = candidate / "operator_input" / "launch.json"
        if not launch_path.is_file():
            return None
        try:
            payload = json.loads(launch_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise MCPBridgeError(
                f"cannot validate operator launch record {launch_path}: {error}"
            ) from error
        if not isinstance(payload, Mapping):
            raise MCPBridgeError(f"operator launch record is not an object: {launch_path}")
        hypothesis_name = payload.get("hypothesis_file", "hypothesis.txt")
        if hypothesis_name != "hypothesis.txt":
            raise MCPBridgeError("operator launch record must use operator_input/hypothesis.txt")
        hypothesis_path = candidate / "operator_input" / "hypothesis.txt"
        try:
            hypothesis = hypothesis_path.read_text(encoding="utf-8")
        except OSError as error:
            raise MCPBridgeError(
                f"cannot read operator hypothesis {hypothesis_path}: {error}"
            ) from error
        expected_hash = payload.get("hypothesis_sha256")
        actual_hash = hashlib.sha256(hypothesis.encode()).hexdigest()
        if expected_hash != actual_hash:
            raise MCPBridgeError(
                "operator launch record hypothesis identity does not match "
                "operator_input/hypothesis.txt"
            )
        canonical = hypothesis.strip()
        if not canonical:
            raise MCPBridgeError(f"operator hypothesis is empty: {hypothesis_path}")
        return canonical

    def _host_hypothesis(self) -> str | None:
        """Read a host-owned hypothesis and protect an existing root identity."""

        requested = (
            _read_hypothesis_file(self.config.hypothesis_file)
            if self.config.hypothesis_file is not None
            else None
        )
        existing: str | None = None
        for candidate in self._campaign_candidates():
            launch_hypothesis = self._launch_hypothesis(candidate)
            if launch_hypothesis is not None:
                if existing is not None and launch_hypothesis != existing:
                    raise MCPBridgeError(
                        "operator launch and MVP manifest contain different root hypotheses"
                    )
                existing = launch_hypothesis
            manifest_path = candidate / "mvp_manifest.json"
            if not manifest_path.is_file():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise MCPBridgeError(
                    f"cannot validate existing campaign manifest {manifest_path}: {error}"
                ) from error
            value = manifest.get("hypothesis")
            if not isinstance(value, str) or not value.strip():
                raise MCPBridgeError(
                    f"existing campaign manifest has no valid hypothesis: {manifest_path}"
                )
            if existing is not None and value != existing:
                raise MCPBridgeError(
                    "operator launch and MVP manifest contain different root hypotheses"
                )
            existing = value
        if existing is not None and requested is not None and requested != existing:
            raise MCPBridgeError(
                "SIMJECTURE_HYPOTHESIS_FILE does not exactly match the existing "
                "campaign root hypothesis"
            )
        return existing or requested

    async def _open_kernel(self) -> Any:
        hypothesis = self._host_hypothesis()
        if self._kernel_factory is not None:
            factory = self._kernel_factory
            candidates = {
                "config": self.config,
                "workspace": self.config.workspace,
                "root": self.config.workspace,
                "campaign": self.config.campaign,
                "campaign_id": self.config.campaign,
                "hypothesis": hypothesis,
            }
            kwargs = _filtered_kwargs(factory, candidates)
            parameters, has_kwargs = _signature_parameters(factory)
            if parameters or has_kwargs:
                result = factory(**kwargs)
            else:
                result = factory(self.config.workspace)
            return await _await_result(result)

        try:
            module = importlib.import_module("conjecture_solver.campaign_kernel")
            kernel_type = module.CampaignKernel
        except (ImportError, AttributeError) as error:
            raise MCPBridgeError(
                "CampaignKernel is unavailable; install the campaign runtime or "
                "pass a kernel fake to CampaignMCPBridge"
            ) from error
        opener = getattr(kernel_type, "open", None)
        if opener is None:
            raise MCPBridgeError(
                "CampaignKernel.open(...) is required by the MCP bridge; "
                "the installed kernel is an older host adapter"
            )
        candidates = {
            "config": self.config,
            "workspace": self.config.workspace,
            "root": self.config.workspace,
            "project_root": self.config.workspace,
            "campaign": self.config.campaign,
            "campaign_id": self.config.campaign,
            "hypothesis": hypothesis,
            "output": self.config.campaign,
            "output_dir": self.config.campaign,
            "capabilities": self.config.capabilities,
            "capabilities_root": self.config.capabilities,
            "skills": self.config.skills,
            "skills_root": self.config.skills,
        }
        kwargs = _filtered_kwargs(opener, candidates)
        try:
            result = opener(**kwargs)
        except TypeError as error:
            # A small compatibility fallback handles early fakes whose open
            # method accepted only a positional workspace path.  Do not retry
            # when the signature clearly accepted named arguments: in that case
            # a TypeError is an actual kernel setup error.
            parameters, has_kwargs = _signature_parameters(opener)
            if parameters and not has_kwargs and kwargs:
                raise error
            result = opener(self.config.workspace)
        return await _await_result(result)

    async def _kernel_method(self, name: str, *args: Any, **kwargs: Any) -> Any:
        kernel = await self._ensure_kernel()
        method = getattr(kernel, name, None)
        if method is None or not callable(method):
            raise MCPBridgeError(f"CampaignKernel does not implement {name}(...)")
        return await _await_result(method(*args, **kwargs))

    async def _execute_action(
        self,
        action_name: str,
        payload: Mapping[str, Any],
    ) -> Any:
        action = dict(payload)
        # Iteration is host-controlled. It is never accepted from MCP input.
        action["action"] = action_name
        action.setdefault("research_note", f"DSH MCP tool: {action_name}")
        kernel = await self._ensure_kernel()
        method = getattr(kernel, "execute", None) or getattr(kernel, "perform", None)
        if method is None or not callable(method):
            raise MCPBridgeError("CampaignKernel does not implement execute(...)")
        parameters, has_kwargs = _signature_parameters(method)
        kwargs: dict[str, Any] = {}
        if has_kwargs or "iteration" in parameters:
            kwargs["iteration"] = 0
        if has_kwargs or "timeout_seconds" in parameters:
            # The action endpoint is synchronous in early kernels; this bound
            # keeps direct file/claim actions from accidentally running forever.
            kwargs["timeout_seconds"] = self.config.default_timeout_seconds
        # Never retry an action after entering the kernel.  A TypeError or
        # ValueError can be raised after a mutating action has already begun;
        # treating it as an old-signature signal would execute the mutation a
        # second time.  CampaignKernel v0.2 owns mapping-to-action validation,
        # so one MCP call always crosses this boundary exactly once.
        return await _await_result(method(action, **kwargs))

    async def _execute_mutation(
        self,
        operation_id: str,
        action_name: str,
        payload: Mapping[str, Any],
    ) -> Any:
        """Dispatch a durable mutation through the kernel's idempotent seam."""

        action = dict(payload)
        action.pop("operation_id", None)
        action.setdefault("research_note", f"DSH MCP tool: {action_name}")
        method = await self._ensure_kernel()
        execute_operation = getattr(method, "execute_operation", None)
        if not callable(execute_operation):
            raise MCPBridgeError(
                "CampaignKernel does not implement the required "
                "execute_operation(...) idempotency boundary"
            )
        return await _await_result(
            execute_operation(
                operation_id,
                {**action, "action": action_name},
                timeout_seconds=self.config.default_timeout_seconds,
            )
        )

    async def _job(self, request: Mapping[str, Any]) -> Any:
        kernel = await self._ensure_kernel()
        method = getattr(kernel, "start_job", None)
        if method is None or not callable(method):
            raise MCPBridgeError("CampaignKernel does not implement start_job(...)")
        return await _await_result(method(dict(request)))

    async def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        """Validate, dispatch, and bound one scientific MCP tool call."""

        if name not in TOOL_SCHEMAS:
            raise MCPInputError(f"unknown scientific MCP tool {name!r}")
        try:
            validated = validate_tool_arguments(
                name,
                {} if arguments is None else arguments,
            )
        except ValueError as error:
            raise MCPInputError(str(error)) from error

        if name == "snapshot":
            snapshot = await self._kernel_method("snapshot")
            result = _project_snapshot(snapshot, validated)
        elif name == "claims":
            # Projection arguments belong to this wire adapter, not to the
            # model-independent CampaignKernel action.  Retrieve once, then
            # select before the generic output bound can collapse the ledger
            # into an unusable digest/preview record.
            ledger = await self._execute_action("list_claims", {})
            result = _project_claims(
                ledger,
                validated,
                maximum_output_chars=self.config.max_output_chars,
            )
        elif name in {
            "register_claim",
            "register_evidence_contract",
            "link_claim_evidence",
            "close_claim",
        }:
            result = await self._execute_mutation(
                validated["operation_id"],
                name,
                validated,
            )
        elif name == "list_skills":
            result = await self._execute_action("list_skills", validated)
        elif name == "read_skill":
            result = await self._execute_action("read_skill", validated)
        elif name == "materialize_skill":
            result = await self._execute_mutation(
                validated["operation_id"],
                "materialize_skill_resource",
                validated,
            )
        elif name == "search_literature":
            result = await self._execute_mutation(
                validated["operation_id"],
                "search_literature",
                validated,
            )
        elif name == "read_workspace_file":
            result = await self._execute_action(
                "read_file",
                {**validated, "path": validated["path"]},
            )
        elif name == "write_workspace_file":
            result = await self._execute_mutation(
                validated["operation_id"],
                "write_file",
                validated,
            )
        elif name == "list_workspace_files":
            payload = dict(validated)
            payload.setdefault("path", ".")
            result = await self._execute_action("list_files", payload)
        elif name in {
            "run_python",
            "run_workbench_capability",
            "run_evidence_capability",
        }:
            payload = dict(validated)
            research_note = payload.pop("research_note", None)
            timeout = payload.pop("timeout_seconds", self.config.default_timeout_seconds)
            operation_id = payload.pop("operation_id")
            if name == "run_python":
                request = {
                    "operation_id": operation_id,
                    "kind": "python",
                    "argv": list(payload["argv"]),
                    "active_claim_id": payload.get("active_claim_id"),
                    "timeout_seconds": timeout,
                }
            else:
                request = {
                    "operation_id": operation_id,
                    "kind": "capability",
                    "capability": payload["capability"],
                    "argv": list(payload["argv"]),
                    "stage": "evidence" if name == "run_evidence_capability" else "workbench",
                    "active_claim_id": payload.get("active_claim_id"),
                    "timeout_seconds": timeout,
                }
            if research_note is not None:
                request["research_note"] = research_note
            result = await self._job(request)
        elif name == "job_status":
            kernel = await self._ensure_kernel()
            reporter = getattr(kernel, "job_report", None)
            if validated.get("report", True) and callable(reporter):
                result = await _await_result(reporter(validated["job_id"]))
            else:
                result = await self._kernel_method("job_status", validated["job_id"])
        elif name == "cancel_job":
            result = await self._execute_mutation(
                validated["operation_id"],
                "cancel_job",
                validated,
            )
        elif name == "prepare_adjudication":
            payload = dict(validated)
            operation_id = payload.pop("operation_id")
            kernel = await self._ensure_kernel()
            method = getattr(kernel, "prepare_adjudication", None)
            if not callable(method):
                raise MCPBridgeError("CampaignKernel does not implement prepare_adjudication(...)")
            result = await _await_result(method(operation_id, **payload))
        elif name == "record_adjudication":
            payload = dict(validated)
            operation_id = payload.pop("operation_id")
            kernel = await self._ensure_kernel()
            method = getattr(kernel, "record_adjudication", None)
            if not callable(method):
                raise MCPBridgeError("CampaignKernel does not implement record_adjudication(...)")
            result = await _await_result(method(operation_id, **payload))
        elif name == "finalize_campaign":
            payload = dict(validated)
            operation_id = payload.pop("operation_id")
            kernel = await self._ensure_kernel()
            method = getattr(kernel, "finalize_campaign", None)
            if not callable(method):
                raise MCPBridgeError("CampaignKernel does not implement finalize_campaign(...)")
            result = await _await_result(method(operation_id, **payload))
        else:  # pragma: no cover - guarded by TOOL_SCHEMAS above
            raise MCPInputError(f"unhandled scientific MCP tool {name!r}")
        return _bound_result(result, self.config.max_output_chars)

    async def list_tools(self) -> tuple[dict[str, Any], ...]:
        return tool_definitions()


# Short aliases make the integration straightforward for callers without
# committing them to the longer class name.
MCPBridge = CampaignMCPBridge
MCPServerBridge = CampaignMCPBridge


def _model(cls: Any, **values: Any) -> Any:
    """Instantiate SDK models across legacy camelCase and v2 aliases."""

    try:
        return cls(**values)
    except (TypeError, ValueError):
        translated = dict(values)
        translations = {
            "inputSchema": "input_schema",
            "structuredContent": "structured_content",
            "isError": "is_error",
        }
        for old, new in translations.items():
            if old in translated:
                translated[new] = translated.pop(old)
        return cls(**translated)


def _sdk_tool(types_module: Any, definition: Mapping[str, Any]) -> Any:
    return _model(
        types_module.Tool,
        name=definition["name"],
        description=definition["description"],
        inputSchema=definition["inputSchema"],
    )


def _sdk_text(types_module: Any, text: str) -> Any:
    return _model(types_module.TextContent, type="text", text=text)


def _sdk_result(types_module: Any, result: Any, *, error: bool = False) -> Any:
    text = _compact_json(result)
    # The MCP structured-content field is an object in both the legacy and v2
    # SDK models.  Preserve the complete JSON value in text content while
    # wrapping scalar/list results for clients that validate that field.
    structured = result if isinstance(result, Mapping) else {"value": result}
    return _model(
        types_module.CallToolResult,
        content=[_sdk_text(types_module, text)],
        structuredContent=structured,
        isError=error,
    )


def _mcp_error_payload(error: Exception, *, tool: str) -> dict[str, Any]:
    """Return a bounded stable error envelope for retry-aware MCP clients."""

    from .campaign_jobs import CampaignLockBusyError

    if isinstance(error, CampaignLockBusyError):
        code = "campaign_writer_busy"
    elif isinstance(error, MCPInputError):
        code = "invalid_tool_arguments"
    elif isinstance(error, MCPBridgeError):
        code = "mcp_bridge_error"
    else:
        code = "scientific_tool_failed"
    return {
        "error": {
            "code": code,
            "message": str(error)[:2_000],
        },
        "tool": tool,
    }


def create_mcp_server(bridge: CampaignMCPBridge | None = None) -> Any:
    """Construct an official Python MCP SDK server lazily.

    The low-level server is used instead of generated FastMCP signatures so the
    exact DSH-compatible input schemas survive discovery unchanged.
    """

    try:
        from mcp import types as mcp_types

        try:
            # MCP SDK v2 keeps the low-level server in this explicit module;
            # older initialize-era releases re-export the same class from
            # ``mcp.server``.
            from mcp.server.lowlevel import Server
        except ImportError:
            from mcp.server import Server
    except ImportError as error:  # pragma: no cover - depends on optional extra
        raise MCPBridgeError(
            "the MCP SDK is optional; install simjecture[dsh] to run simjecture-mcp"
        ) from error

    active_bridge = bridge or CampaignMCPBridge.from_environment()
    definitions = tuple(tool_definitions())

    async def list_handler(*args: Any, **kwargs: Any) -> Any:
        tools = [_sdk_tool(mcp_types, definition) for definition in definitions]
        result_type = getattr(mcp_types, "ListToolsResult", None)
        if result_type is None:
            return tools
        return _model(result_type, tools=tools)

    async def call_handler(*args: Any, **kwargs: Any) -> Any:
        # v2 calls receive (ctx, CallToolRequestParams); legacy decorator calls
        # receive (name, arguments).  Supporting both here also makes a real
        # initialize/list/call handshake test useful across SDK revisions.
        request = next(
            (
                item
                for item in (*args, *kwargs.values())
                if hasattr(item, "name") and hasattr(item, "arguments")
            ),
            None,
        )
        if request is not None:
            name = str(request.name)
            arguments = request.arguments or {}
        elif args:
            name = str(args[0])
            arguments = args[1] if len(args) > 1 and args[1] is not None else {}
        else:
            name = str(kwargs.get("name"))
            arguments = kwargs.get("arguments") or {}
        try:
            result = await active_bridge.call_tool(name, arguments)
            return _sdk_result(mcp_types, result)
        except Exception as error:
            return _sdk_result(
                mcp_types,
                _mcp_error_payload(error, tool=name),
                error=True,
            )

    # v2's low-level Server accepts constructor callbacks.  Legacy SDKs expose
    # the same callbacks as decorators, so fall back without importing private
    # SDK internals.
    try:
        return Server(
            "simjecture-mcp",
            version="0.2.0",
            instructions=(
                "Scientific campaign tools only. Use the explicit Simjecture "
                "tools; generic shell and finish tools are intentionally absent."
            ),
            on_list_tools=list_handler,
            on_call_tool=call_handler,
        )
    except TypeError:
        server = Server("simjecture-mcp")

        @server.list_tools()
        async def _legacy_list_tools() -> list[Any]:
            return [_sdk_tool(mcp_types, definition) for definition in definitions]

        @server.call_tool()
        async def _legacy_call_tool(name: str, arguments: dict[str, Any]) -> Any:
            return await call_handler(name, arguments)

        return server


# Natural factory alias used by small host integrations.
create_server = create_mcp_server


async def run_stdio(
    bridge: CampaignMCPBridge | None = None,
    *,
    server: Any | None = None,
) -> None:
    """Run one bridge over the official SDK's stdio transport."""

    active_bridge = bridge
    if active_bridge is None and server is None:
        active_bridge = CampaignMCPBridge.from_environment()
    try:
        if active_bridge is not None:
            # Fail before opening stdin/stdout or advertising MCP capabilities.
            # A DSH profile can then use failOnStartupError as its hard campaign
            # readiness gate.
            await active_bridge.startup()
        if server is None:
            server = create_mcp_server(active_bridge)
        try:
            from mcp.server.stdio import stdio_server
        except ImportError as error:  # pragma: no cover - optional dependency
            raise MCPBridgeError("the installed MCP SDK does not provide stdio_server") from error
        async with stdio_server() as (read_stream, write_stream):
            options = server.create_initialization_options()
            await server.run(read_stream, write_stream, options)
    finally:
        if active_bridge is not None:
            active_bridge.shutdown()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="simjecture-mcp",
        description="Expose one Simjecture CampaignKernel over MCP stdio.",
    )
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--campaign", default=None)
    parser.add_argument("--hypothesis-file", type=Path, default=None)
    parser.add_argument("--max-output-chars", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    """CLI entry point installed as ``simjecture-mcp``."""

    args = _arguments()
    config = BridgeConfig.from_environment()
    if (
        args.workspace is not None
        or args.campaign is not None
        or args.hypothesis_file is not None
        or args.max_output_chars is not None
    ):
        config = dataclasses.replace(
            config,
            workspace=args.workspace or config.workspace,
            campaign=args.campaign if args.campaign is not None else config.campaign,
            hypothesis_file=(
                args.hypothesis_file if args.hypothesis_file is not None else config.hypothesis_file
            ),
            max_output_chars=args.max_output_chars
            if args.max_output_chars is not None
            else config.max_output_chars,
        )
    bridge = CampaignMCPBridge(config=config)
    try:
        asyncio.run(run_stdio(bridge))
    except MCPBridgeError as error:
        print(f"simjecture-mcp: {error}", file=sys.stderr)
        raise SystemExit(2) from error


__all__ = [
    "BridgeConfig",
    "CampaignKernelProtocol",
    "CampaignMCPBridge",
    "MCPBridge",
    "MCPBridgeError",
    "MCPInputError",
    "MCPServerBridge",
    "create_mcp_server",
    "create_server",
    "main",
    "run_stdio",
]


if __name__ == "__main__":  # pragma: no cover - exercised by stdio clients
    main()
