"""Read-only projection of durable natural-language MVP run artifacts.

The monitor never writes to a run directory. Claim ledgers and terminal reports
remain authoritative; model prose is only used to name the current typed action.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, TextIO

from pydantic import Field

from .models import StrictModel
from .mvp_agent import (
    MVPAgentAction,
    MVPAuthorAndRunCapabilityAction,
    MVPCloseClaimAction,
    MVPFinishAction,
    MVPLinkClaimEvidenceAction,
    MVPListFilesAction,
    MVPListSkillsAction,
    MVPLoopStage,
    MVPLoopState,
    MVPMaterializeSkillResourceAction,
    MVPReadFileAction,
    MVPReadSkillAction,
    MVPRegisterClaimAction,
    MVPRegisterEvidenceContractAction,
    MVPRequestAdjudicationAction,
    MVPResearchRole,
    MVPRunCapabilityAction,
    MVPRunPythonAction,
    MVPSearchLiteratureAction,
    MVPWriteFileAction,
    parse_mvp_action,
)
from .mvp_control import (
    ControlCommand,
    elapsed_from_clock,
    format_token_counts,
    parse_usage_payload,
    read_clock,
    read_control,
    read_pause_state,
)

TERMINAL_REPORT_STATUSES = frozenset(
    {"completed", "cancelled", "provider_failed", "budget_exhausted"}
)
OPERATOR_INPUT_DIR = "operator_input"
DEFAULT_RECENT_EVENT_LIMIT = 40
_MAX_RETAINED_EVENTS = 80
_MAX_CONSOLE_EXCERPT_CHARS = 12_000
_MAX_PROJECTED_EXECUTIONS = 100
_EXECUTION_ACTION_NAMES = frozenset(
    {"run_python", "run_capability", "author_and_run_capability"}
)


class RunPhase(StrEnum):
    """Operator-facing phase derived from durable artifacts, not process liveness."""

    INITIALIZED = "initialized"
    INCOMPLETE = "incomplete"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PROVIDER_FAILED = "provider_failed"
    BUDGET_EXHAUSTED = "budget_exhausted"


class TranscriptCursor(StrictModel):
    """Byte-oriented resume point for an append-only transcript."""

    inode: int | None = None
    offset: int = Field(default=0, ge=0)
    size: int = Field(default=0, ge=0)
    mtime_ns: int | None = None


class RunIdentity(StrictModel):
    run_directory: str
    campaign_id: str | None = None
    hypothesis: str | None = None
    campaign_instruction: str | None = None
    manifest_schema_version: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    skill_hashes: dict[str, str] = Field(default_factory=dict)
    capability_hashes: dict[str, str] = Field(default_factory=dict)


class ClaimSummary(StrictModel):
    id: str
    status: str
    kind: str | None = None
    relation: str | None = None
    parent_id: str | None = None
    statement: str = ""
    evidence_count: int = Field(default=0, ge=0)
    contract_count: int = Field(default=0, ge=0)
    closed_reason: str | None = None
    active: bool = False


class CurrentAction(StrictModel):
    iteration: int = Field(ge=1)
    action_name: str | None = None
    description: str
    pending: bool
    capability: str | None = None
    stage: str | None = None
    active_claim_id: str | None = None
    path: str | None = None
    model: str | None = None
    route: str | None = None
    research_note: str | None = None
    argv: tuple[str, ...] = ()


class HeartbeatObservation(StrictModel):
    iteration: int = Field(ge=1)
    elapsed_wall_seconds: float | None = None
    stdout_bytes: int | None = None
    stderr_bytes: int | None = None
    workspace_bytes: int | None = None
    observed_at: datetime | None = None
    age_seconds: float | None = None


class HumanizedEvent(StrictModel):
    sequence: int = Field(default=0, ge=0)
    kind: str
    iteration: int | None = None
    summary: str
    action_name: str | None = None
    research_note: str | None = None
    model: str | None = None
    route: str | None = None
    research_role: str | None = None
    outcome: str | None = None
    capability: str | None = None
    stage: str | None = None
    active_claim_id: str | None = None
    argv: tuple[str, ...] = ()
    console_excerpt: str | None = None
    returncode: int | None = None
    timed_out: bool | None = None
    elapsed_wall_seconds: float | None = None
    stdout_bytes: int | None = None
    stderr_bytes: int | None = None
    workspace_bytes: int | None = None


class ComputeExecutionSummary(StrictModel):
    id: str
    iteration: int = Field(ge=1)
    action_name: str
    description: str
    status: str
    capability: str | None = None
    stage: str | None = None
    active_claim_id: str | None = None
    argv: tuple[str, ...] = ()
    model: str | None = None
    route: str | None = None
    research_note: str | None = None
    console_excerpt: str | None = None
    returncode: int | None = None
    timed_out: bool | None = None
    elapsed_wall_seconds: float | None = None
    stdout_bytes: int | None = None
    stderr_bytes: int | None = None
    workspace_bytes: int | None = None


class ModelTokenUsage(StrictModel):
    model: str
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    turns: int = Field(default=0, ge=0)


class TokenUsageSummary(StrictModel):
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cached_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    turns: int = Field(default=0, ge=0)
    turns_missing_usage: int = Field(default=0, ge=0)
    by_model: tuple[ModelTokenUsage, ...] = ()
    label: str = "tokens: 0 in / 0 out / 0 total (0 turns)"


class TerminalReportSummary(StrictModel):
    status: str
    final_answer: str
    iterations: int = Field(ge=0)
    elapsed_wall_seconds: float = Field(ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    open_claim_ids: tuple[str, ...] = ()
    closed_claim_ids: tuple[str, ...] = ()
    finish_claim_notes: tuple[str, ...] = ()
    workspace_artifact_count: int = Field(default=0, ge=0)


class ArtifactPaths(StrictModel):
    run_directory: str
    manifest: str | None = None
    transcript: str | None = None
    report: str | None = None
    claim_ledger: str | None = None
    claim_summary: str | None = None
    loop_state: str | None = None
    adjudications: str | None = None
    artifact_provenance: str | None = None
    workspace: str | None = None
    controller_log: str | None = None
    operator_input: str | None = None


class ContainedArtifact(StrictModel):
    relative_path: str
    bytes: int = Field(ge=0)
    kind: str


class RecentRun(StrictModel):
    run_directory: str
    campaign_id: str | None = None
    phase: RunPhase
    hypothesis: str | None = None
    modified_at: datetime | None = None


class MVPRunSnapshot(StrictModel):
    phase: RunPhase
    phase_label: str
    identity: RunIdentity
    configured_wall_seconds: float | None = None
    elapsed_wall_seconds: float | None = None
    elapsed_is_estimate: bool = False
    iterations: int = Field(default=0, ge=0)
    action_counts: dict[str, int] = Field(default_factory=dict)
    claims: tuple[ClaimSummary, ...] = ()
    open_claim_ids: tuple[str, ...] = ()
    closed_claim_ids: tuple[str, ...] = ()
    current_action: CurrentAction | None = None
    loop_state: MVPLoopState
    latest_heartbeat: HeartbeatObservation | None = None
    recent_events: tuple[HumanizedEvent, ...] = ()
    execution_total: int = Field(default=0, ge=0)
    executions: tuple[ComputeExecutionSummary, ...] = ()
    report: TerminalReportSummary | None = None
    artifacts: ArtifactPaths
    workspace_bytes: int = Field(default=0, ge=0)
    last_model: str | None = None
    last_capability: str | None = None
    token_usage: TokenUsageSummary = Field(default_factory=TokenUsageSummary)
    pending_control: str | None = None
    warnings: tuple[str, ...] = ()
    transcript_cursor: TranscriptCursor = Field(default_factory=TranscriptCursor)


@dataclass
class _UsageState:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    usage_turns: int = 0
    missing_usage_turns: int = 0
    model_usage: dict[str, dict[str, int]] = field(default_factory=dict)

    def reset(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.cached_tokens = 0
        self.reasoning_tokens = 0
        self.usage_turns = 0
        self.missing_usage_turns = 0
        self.model_usage.clear()


@dataclass
class _TranscriptState:
    assistant: dict[int, dict[str, Any]] = field(default_factory=dict)
    tools: dict[int, dict[str, Any]] = field(default_factory=dict)
    last_heartbeat: dict[str, Any] | None = None
    last_heartbeat_observed_at: datetime | None = None
    events: list[HumanizedEvent] = field(default_factory=list)
    action_counts: Counter[str] = field(default_factory=Counter)
    last_model: str | None = None
    last_route: str | None = None
    last_capability: str | None = None
    parse_warnings: list[str] = field(default_factory=list)
    usage: _UsageState = field(default_factory=_UsageState)
    next_event_sequence: int = 0

    def reset(self) -> None:
        self.assistant.clear()
        self.tools.clear()
        self.last_heartbeat = None
        self.last_heartbeat_observed_at = None
        self.events.clear()
        self.action_counts.clear()
        self.last_model = None
        self.last_route = None
        self.last_capability = None
        self.parse_warnings.clear()
        self.usage.reset()
        self.next_event_sequence = 0


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "--:--:--"
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_bytes(size: int | None) -> str:
    if size is None:
        return "unknown"
    value = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)} B"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{size} B"


def format_age(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds < 1:
        return "just now"
    if seconds < 60:
        return f"{int(seconds)} s ago"
    if seconds < 3600:
        return f"{int(seconds // 60)} min ago"
    return f"{int(seconds // 3600)} h ago"


def claim_status_marker(status: str) -> str:
    markers = {
        "open": "●",
        "supported": "✓",
        "weakened": "~",
        "falsified": "×",
        "superseded": "▸",
        "unresolved": "?",
        "instrument_limited": "!",
    }
    return markers.get(status, "·")


def phase_label(phase: RunPhase) -> str:
    if phase is RunPhase.INCOMPLETE:
        return "incomplete (no terminal report)"
    if phase is RunPhase.INITIALIZED:
        return "initialized"
    if phase is RunPhase.PAUSED:
        return "paused (action boundary)"
    return phase.value


def humanize_action(action: MVPAgentAction) -> str:
    """Describe a typed action without treating research notes as scientific status."""

    if isinstance(action, MVPSearchLiteratureAction):
        return f"Searching literature for {action.query!r}"
    if isinstance(action, MVPWriteFileAction):
        return f"Writing {action.path}"
    if isinstance(action, MVPReadFileAction):
        return f"Reading {action.path}"
    if isinstance(action, MVPListFilesAction):
        return f"Listing {action.path}"
    if isinstance(action, MVPRunPythonAction):
        command = _short_argv(action.argv)
        if action.active_claim_id:
            return f"Running Python {command} for {action.active_claim_id}"
        return f"Running Python {command}"
    if isinstance(action, MVPListSkillsAction):
        return "Listing installed skills and capabilities"
    if isinstance(action, MVPReadSkillAction):
        if action.path:
            return f"Reading skill {action.skill} ({action.path})"
        return f"Reading skill {action.skill}"
    if isinstance(action, MVPMaterializeSkillResourceAction):
        return f"Materializing {action.skill}:{action.source_path} → {action.destination_path}"
    if isinstance(action, MVPRunCapabilityAction):
        claim = f", claim={action.active_claim_id}" if action.active_claim_id else ""
        return f"Running capability {action.capability} (stage={action.stage.value}{claim})"
    if isinstance(action, MVPAuthorAndRunCapabilityAction):
        claim = f", claim={action.active_claim_id}" if action.active_claim_id else ""
        return (
            f"Authoring and running {action.path} on {action.capability} "
            f"(stage={action.stage.value}{claim})"
        )
    if isinstance(action, MVPRegisterClaimAction):
        return f"Registering {action.claim_id} ({action.kind.value})"
    if isinstance(action, MVPRegisterEvidenceContractAction):
        return f"Registering evidence contract for {action.claim_id}"
    if isinstance(action, MVPLinkClaimEvidenceAction):
        return f"Linking evidence {action.path} to {action.claim_id}"
    if isinstance(action, MVPCloseClaimAction):
        return f"Closing {action.claim_id} as {action.status.value}"
    if isinstance(action, MVPRequestAdjudicationAction):
        return f"Requesting independent adjudication for {action.claim_id}"
    if isinstance(action, MVPFinishAction):
        return "Finishing the campaign"
    if action.action.value == "list_claims":
        return "Listing claims"
    return f"Performing {action.action.value}"


def action_details(action: MVPAgentAction) -> dict[str, Any]:
    details: dict[str, Any] = {"action_name": action.action.value}
    if isinstance(
        action,
        (MVPRunCapabilityAction, MVPAuthorAndRunCapabilityAction),
    ):
        details["capability"] = action.capability
        details["stage"] = action.stage.value
        details["active_claim_id"] = action.active_claim_id
        details["argv"] = action.argv
        if isinstance(action, MVPAuthorAndRunCapabilityAction):
            details["path"] = action.path
    elif isinstance(action, MVPRunPythonAction):
        details["argv"] = action.argv
        details["active_claim_id"] = action.active_claim_id
    elif isinstance(
        action,
        (MVPWriteFileAction, MVPReadFileAction, MVPListFilesAction, MVPReadSkillAction),
    ):
        details["path"] = action.path
    elif isinstance(action, MVPMaterializeSkillResourceAction):
        details["path"] = action.destination_path
    elif isinstance(
        action,
        (
            MVPRegisterClaimAction,
            MVPRegisterEvidenceContractAction,
            MVPLinkClaimEvidenceAction,
            MVPCloseClaimAction,
            MVPRequestAdjudicationAction,
        ),
    ):
        details["active_claim_id"] = action.claim_id
        if isinstance(action, MVPLinkClaimEvidenceAction):
            details["path"] = action.path
    return details


def read_new_transcript_records(
    path: Path,
    cursor: TranscriptCursor,
) -> tuple[list[dict[str, Any]], TranscriptCursor, tuple[str, ...]]:
    """Read newly completed JSONL records without consuming a partial last line."""

    if not path.exists() or not path.is_file():
        return [], TranscriptCursor(), ()
    stat = path.stat()
    inode = getattr(stat, "st_ino", None)
    reset = False
    if cursor.inode is not None and inode != cursor.inode:
        reset = True
    if stat.st_size < cursor.offset:
        reset = True
    start = 0 if reset else cursor.offset
    with path.open("rb") as stream:
        stream.seek(start)
        chunk = stream.read()
    newline_at = chunk.rfind(b"\n")
    if newline_at < 0:
        return (
            [],
            TranscriptCursor(
                inode=inode,
                offset=start,
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            ),
            (),
        )
    complete = chunk[: newline_at + 1]
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    for raw_line in complete.split(b"\n"):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            warnings.append(f"skipped malformed transcript line: {error}")
            continue
        if isinstance(payload, dict):
            records.append(payload)
        else:
            warnings.append("skipped non-object transcript line")
    return (
        records,
        TranscriptCursor(
            inode=inode,
            offset=start + len(complete),
            size=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
        ),
        tuple(warnings),
    )


def load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def directory_bytes(root: Path) -> int:
    if not root.is_dir():
        return 0
    resolved = root.resolve()
    total = 0
    for dirpath, dirnames, filenames in os.walk(resolved, followlinks=False):
        current = Path(dirpath)
        try:
            if not current.resolve().is_relative_to(resolved):
                dirnames.clear()
                continue
        except OSError:
            dirnames.clear()
            continue
        for name in filenames:
            path = current / name
            if path.is_symlink():
                continue
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


def contained_path(root: Path, relative: str | Path) -> Path | None:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    if not candidate.is_relative_to(resolved_root):
        return None
    return candidate


def list_contained_artifacts(
    run_directory: Path,
    *,
    max_entries: int = 200,
) -> tuple[ContainedArtifact, ...]:
    root = Path(run_directory).resolve()
    if not root.is_dir():
        return ()
    entries: list[ContainedArtifact] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        try:
            if not current.resolve().is_relative_to(root):
                dirnames.clear()
                continue
        except OSError:
            dirnames.clear()
            continue
        dirnames.sort()
        for name in sorted(filenames):
            path = current / name
            if path.is_symlink():
                kind = "symlink"
                size = 0
            elif path.is_file():
                kind = "file"
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
            else:
                continue
            relative = path.relative_to(root).as_posix()
            entries.append(
                ContainedArtifact(relative_path=relative, bytes=size, kind=kind)
            )
            if len(entries) >= max_entries:
                return tuple(entries)
    return tuple(entries)


def discover_recent_runs(
    roots: Iterable[str | Path] | None = None,
    *,
    limit: int = 20,
) -> tuple[RecentRun, ...]:
    search_roots = [Path(item).expanduser() for item in roots] if roots else _default_run_roots()
    found: dict[str, RecentRun] = {}
    for search_root in search_roots:
        if not search_root.is_dir():
            continue
        for manifest in _candidate_manifests(search_root):
            run_dir = manifest.parent
            key = str(run_dir)
            if key in found:
                continue
            try:
                snapshot = load_run_snapshot(run_dir)
            except OSError:
                continue
            found[key] = RecentRun(
                run_directory=snapshot.identity.run_directory,
                campaign_id=snapshot.identity.campaign_id,
                phase=snapshot.phase,
                hypothesis=snapshot.identity.hypothesis,
                modified_at=_latest_mtime(run_dir),
            )
    ordered = sorted(
        found.values(),
        key=lambda item: item.modified_at or datetime.fromtimestamp(0, UTC),
        reverse=True,
    )
    return tuple(ordered[:limit])


def _default_run_roots() -> list[Path]:
    cwd = Path.cwd()
    return [cwd, cwd / "artifacts"]


def _candidate_manifests(root: Path) -> list[Path]:
    if (root / "mvp_manifest.json").is_file():
        return [root / "mvp_manifest.json"]
    matches: list[Path] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return []
    for child in children:
        if not child.is_dir() or child.name.startswith("."):
            continue
        manifest = child / "mvp_manifest.json"
        if manifest.is_file():
            matches.append(manifest)
            continue
        try:
            grandchildren = list(child.iterdir())
        except OSError:
            continue
        for grandchild in grandchildren:
            nested = grandchild / "mvp_manifest.json"
            if grandchild.is_dir() and nested.is_file():
                matches.append(nested)
    return matches


def _latest_mtime(run_directory: Path) -> datetime | None:
    newest: int | None = None
    for name in ("mvp_report.json", "transcript.jsonl", "mvp_manifest.json"):
        path = run_directory / name
        if not path.exists():
            continue
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            continue
        newest = stamp if newest is None else max(newest, stamp)
    if newest is None:
        return None
    return datetime.fromtimestamp(newest / 1_000_000_000, UTC)


def _short_argv(argv: tuple[str, ...] | list[str], *, limit: int = 72) -> str:
    text = " ".join(str(item) for item in argv)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text or "(no arguments)"


def _existing_path(path: Path) -> str | None:
    return str(path) if path.exists() else None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _iteration_of(record: dict[str, Any]) -> int | None:
    value = record.get("iteration")
    return value if isinstance(value, int) and value >= 1 else None


def _action_from_assistant(record: dict[str, Any]) -> MVPAgentAction | None:
    content = record.get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    try:
        return parse_mvp_action(content)
    except ValueError:
        return None


def _tool_payload(record: dict[str, Any]) -> dict[str, Any] | None:
    content = record.get("content")
    if not isinstance(content, str):
        return None
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    tool = payload.get("tool_result")
    return tool if isinstance(tool, dict) else None


def _console_excerpt(tool: dict[str, Any] | None) -> str | None:
    """Return a bounded, operator-facing excerpt from a command result."""

    if tool is None:
        return None
    result = tool.get("result")
    if not isinstance(result, dict):
        return None
    execution = result.get("execution_result")
    sources = [execution, result] if isinstance(execution, dict) else [result]
    lines: list[str] = []
    primary = sources[0]
    for key in ("returncode", "timed_out", "wall_seconds", "workspace_bytes"):
        if key in primary:
            lines.append(f"{key}: {primary[key]}")
    for source in sources:
        for stream in ("stdout", "stderr"):
            value = source.get(stream)
            if not isinstance(value, str):
                value = source.get(f"{stream}_head")
            if not isinstance(value, str) or not value:
                continue
            if lines:
                lines.append("")
            lines.append(f"[{stream}]")
            lines.append(value)
    if not lines:
        return None
    excerpt = "\n".join(lines)
    if len(excerpt) <= _MAX_CONSOLE_EXCERPT_CHARS:
        return excerpt
    omitted = len(excerpt) - _MAX_CONSOLE_EXCERPT_CHARS
    return f"{excerpt[:_MAX_CONSOLE_EXCERPT_CHARS]}\n… {omitted} characters omitted"


def _execution_metrics(tool: dict[str, Any] | None) -> dict[str, Any]:
    if tool is None or not isinstance(tool.get("result"), dict):
        return {}
    result = tool["result"]
    nested = result.get("execution_result")
    execution = nested if isinstance(nested, dict) else result
    metrics: dict[str, Any] = {}
    if isinstance(execution.get("returncode"), int):
        metrics["returncode"] = execution["returncode"]
    if isinstance(execution.get("timed_out"), bool):
        metrics["timed_out"] = execution["timed_out"]
    elapsed = _as_float(execution.get("wall_seconds"))
    if elapsed is not None:
        metrics["elapsed_wall_seconds"] = elapsed
    workspace = _as_int(execution.get("workspace_bytes"))
    if workspace is not None:
        metrics["workspace_bytes"] = workspace
    for stream in ("stdout", "stderr"):
        value = execution.get(stream)
        if isinstance(value, str):
            metrics[f"{stream}_bytes"] = len(value.encode())
    return metrics


def _execution_outcome(tool: dict[str, Any] | None, metrics: dict[str, Any]) -> str:
    if tool is None:
        return "incomplete"
    if tool.get("ok") is not True:
        return "failed"
    if metrics.get("returncode") not in (None, 0) or metrics.get("timed_out") is True:
        return "failed"
    return "succeeded"


class MVPRunMonitor:
    """Incrementally project a run directory into an operator-facing snapshot."""

    def __init__(self, run_directory: str | Path) -> None:
        self.root = Path(run_directory).expanduser().resolve()
        self._cursor = TranscriptCursor()
        self._dsh_cursor = TranscriptCursor()
        self._state = _TranscriptState()
        self._dsh_usage = _UsageState()
        self._dsh_model: str | None = None
        self._sidecar_cache: dict[str, tuple[int | None, dict[str, Any] | None]] = {}

    def snapshot(self, *, now: datetime | None = None) -> MVPRunSnapshot:
        observed_at = now or utc_now()
        warnings: list[str] = []
        if not self.root.exists():
            raise FileNotFoundError(f"run directory does not exist: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"run path is not a directory: {self.root}")
        warnings.extend(self._ingest_transcript(observed_at=observed_at))
        warnings.extend(self._ingest_dsh_activity())
        manifest = self._read_sidecar("mvp_manifest.json")
        report = self._read_sidecar("mvp_report.json")
        ledger = self._read_sidecar("hypothesis_ledger.json")
        loop_payload = self._read_sidecar("loop_state.json")
        launch = self._read_sidecar(f"{OPERATOR_INPUT_DIR}/launch.json")
        dsh_state = self._read_sidecar(f"{OPERATOR_INPUT_DIR}/dsh_state.json")
        if (self.root / "mvp_manifest.json").exists() and manifest is None:
            warnings.append("mvp_manifest.json exists but could not be parsed")
        if (self.root / "mvp_report.json").exists() and report is None:
            warnings.append("mvp_report.json exists but could not be parsed")
        if (self.root / "hypothesis_ledger.json").exists() and ledger is None:
            warnings.append("hypothesis_ledger.json exists but could not be parsed")
        identity = self._identity(manifest, report, ledger, launch)
        phase = self._phase(report, dsh_state=dsh_state)
        current = None if report is not None else self._current_action()
        claims = self._claims(ledger, report, current)
        model_iterations = len(self._state.assistant) or self._dsh_usage.usage_turns
        loop_state = self._loop_state(
            loop_payload,
            phase=phase,
            claims=claims,
            current=current,
            iterations=model_iterations,
            observed_at=observed_at,
        )
        heartbeat = self._heartbeat(observed_at)
        terminal = self._terminal_report(report)
        configured = None
        if isinstance(identity.config.get("max_wall_seconds"), (int, float)):
            configured = float(identity.config["max_wall_seconds"])
        elapsed, elapsed_is_estimate = self._elapsed(
            report=report,
            configured=configured,
            heartbeat=heartbeat,
            observed_at=observed_at,
        )
        workspace_size = 0
        if heartbeat is not None and heartbeat.workspace_bytes is not None:
            workspace_size = heartbeat.workspace_bytes
        else:
            workspace_size = directory_bytes(self.root / "workspace")
        open_ids = tuple(claim.id for claim in claims if claim.status == "open")
        closed_ids = tuple(claim.id for claim in claims if claim.status != "open")
        if terminal is not None:
            if terminal.open_claim_ids:
                open_ids = terminal.open_claim_ids
            if terminal.closed_claim_ids:
                closed_ids = terminal.closed_claim_ids
        warnings.extend(self._state.parse_warnings[-8:])
        control = read_control(self.root)
        pending = control.command.value if control.command is not ControlCommand.NONE else None
        return MVPRunSnapshot(
            phase=phase,
            phase_label=phase_label(phase),
            identity=identity,
            configured_wall_seconds=configured,
            elapsed_wall_seconds=elapsed,
            elapsed_is_estimate=elapsed_is_estimate,
            iterations=model_iterations,
            action_counts=dict(self._state.action_counts),
            claims=claims,
            open_claim_ids=open_ids,
            closed_claim_ids=closed_ids,
            current_action=current,
            loop_state=loop_state,
            latest_heartbeat=heartbeat,
            recent_events=tuple(self._state.events[-DEFAULT_RECENT_EVENT_LIMIT:]),
            execution_total=sum(
                self._state.action_counts.get(name, 0)
                for name in _EXECUTION_ACTION_NAMES
            ),
            executions=self._executions(current=current, heartbeat=heartbeat),
            report=terminal,
            artifacts=self._artifact_paths(),
            workspace_bytes=workspace_size,
            last_model=self._state.last_model or self._dsh_model,
            last_capability=self._state.last_capability,
            token_usage=self._token_usage(),
            pending_control=pending,
            warnings=tuple(dict.fromkeys(warnings)),
            transcript_cursor=self._cursor,
        )

    @staticmethod
    def _loop_state(
        payload: dict[str, Any] | None,
        *,
        phase: RunPhase,
        claims: tuple[ClaimSummary, ...],
        current: CurrentAction | None,
        iterations: int,
        observed_at: datetime,
    ) -> MVPLoopState:
        cycle = 1 + sum(claim.relation == "repairs" for claim in claims)
        active_claim_id = current.active_claim_id if current is not None else None
        if phase in {
            RunPhase.COMPLETED,
            RunPhase.CANCELLED,
            RunPhase.PROVIDER_FAILED,
            RunPhase.BUDGET_EXHAUSTED,
        }:
            completed = phase is RunPhase.COMPLETED
            if active_claim_id is None:
                open_scientific = [
                    claim
                    for claim in claims
                    if claim.kind == "scientific" and claim.status == "open"
                ]
                if open_scientific:
                    active_claim_id = open_scientific[-1].id
            return MVPLoopState(
                stage=(MVPLoopStage.COMPLETE if completed else MVPLoopStage.STOPPED),
                role=MVPResearchRole.JUDGE,
                cycle=cycle,
                active_claim_id=active_claim_id,
                status="completed" if completed else "stopped",
                iteration=iterations,
                detail=(
                    "Campaign completed with a bounded conclusion."
                    if completed
                    else f"Campaign stopped: {phase.value.replace('_', ' ')}."
                ),
                updated_at=observed_at,
            )
        if payload is not None:
            try:
                return MVPLoopState.model_validate(payload)
            except ValueError:
                pass
        if current is not None and current.action_name == "request_adjudication":
            return MVPLoopState(
                stage=MVPLoopStage.ADJUDICATION,
                role=MVPResearchRole.JUDGE,
                cycle=cycle,
                active_claim_id=active_claim_id,
                iteration=iterations,
                detail="Independent judge is reviewing the evidence package.",
                updated_at=observed_at,
            )
        if active_claim_id is not None:
            active = next((claim for claim in claims if claim.id == active_claim_id), None)
            if active is not None and active.kind == "instrument":
                return MVPLoopState(
                    stage=MVPLoopStage.COMMISSIONING,
                    role=MVPResearchRole.FALSIFIER,
                    cycle=cycle,
                    active_claim_id=active_claim_id,
                    iteration=iterations,
                    detail="Commissioning the experimental pipeline.",
                    updated_at=observed_at,
                )
        repair_parents = {claim.parent_id for claim in claims if claim.relation == "repairs"}
        falsified_frontier = [
            claim
            for claim in claims
            if claim.kind == "scientific"
            and claim.status == "falsified"
            and claim.id not in repair_parents
        ]
        if falsified_frontier:
            target = falsified_frontier[-1]
            return MVPLoopState(
                stage=MVPLoopStage.REPAIR,
                role=MVPResearchRole.SCIENTIST,
                cycle=cycle,
                active_claim_id=target.id,
                iteration=iterations,
                detail="Forming a minimal claim that accommodates the counterexample.",
                updated_at=observed_at,
            )
        open_scientific = [
            claim
            for claim in claims
            if claim.kind == "scientific" and claim.status == "open"
        ]
        if open_scientific:
            target = open_scientific[-1]
            return MVPLoopState(
                stage=MVPLoopStage.FALSIFICATION,
                role=MVPResearchRole.FALSIFIER,
                cycle=cycle,
                active_claim_id=target.id,
                iteration=iterations,
                detail="Searching for a counterexample under a prospective contract.",
                updated_at=observed_at,
            )
        return MVPLoopState(
            stage=MVPLoopStage.FALSIFICATION,
            role=MVPResearchRole.FALSIFIER,
            cycle=cycle,
            active_claim_id=active_claim_id or "claim_root",
            iteration=iterations,
            detail="Searching for a counterexample under a prospective contract.",
            updated_at=observed_at,
        )

    def _ingest_transcript(self, *, observed_at: datetime) -> list[str]:
        transcript = self.root / "transcript.jsonl"
        previous = self._cursor
        records, cursor, warnings = read_new_transcript_records(transcript, previous)
        if previous.inode is not None and (
            cursor.inode != previous.inode or cursor.offset < previous.offset
        ):
            self._state.reset()
        self._cursor = cursor
        recorded_fallback = observed_at
        try:
            recorded_fallback = datetime.fromtimestamp(transcript.stat().st_mtime, UTC)
        except OSError:
            recorded_fallback = observed_at
        for record in records:
            self._ingest_record(record, observed_at=recorded_fallback)
        return list(warnings)

    def _ingest_dsh_activity(self) -> list[str]:
        """Incrementally add provider usage from DSH's bounded event projection.

        DSH model turns live in its event-sourced session rather than the legacy
        Simjecture transcript.  The activity file contains only public event
        metadata and usage counters, so consuming it here neither exposes nor
        reconstructs private reasoning.  Independent-judge usage remains in the
        scientific transcript and is combined at presentation time.
        """

        activity = self.root / OPERATOR_INPUT_DIR / "dsh_activity.jsonl"
        if activity.is_symlink():
            return ["DSH activity: ignored symbolic-link activity file"]
        previous = self._dsh_cursor
        records, cursor, warnings = read_new_transcript_records(activity, previous)
        if previous.inode is not None and (
            cursor.inode != previous.inode or cursor.offset < previous.offset
        ):
            self._dsh_usage.reset()
            self._dsh_model = None
        self._dsh_cursor = cursor
        for record in records:
            if record.get("kind") == "route" and isinstance(record.get("model"), str):
                self._dsh_model = record["model"]
            if isinstance(record.get("usage"), dict):
                self._accumulate_usage(
                    record,
                    target=self._dsh_usage,
                    fallback_model=self._dsh_model,
                    count_turn=(
                        record.get("kind") == "model"
                        and record.get("status") == "responded"
                    ),
                )
        return [f"DSH activity: {warning}" for warning in warnings]

    def _ingest_record(self, record: dict[str, Any], *, observed_at: datetime) -> None:
        kind = str(record.get("kind") or "unknown")
        iteration = _iteration_of(record)
        if kind == "assistant":
            if iteration is None:
                return
            self._state.assistant[iteration] = record
            if isinstance(record.get("model"), str):
                self._state.last_model = record["model"]
            if isinstance(record.get("route"), str):
                self._state.last_route = record["route"]
            action = _action_from_assistant(record)
            action_name = action.action.value if action is not None else None
            self._accumulate_usage(record)
            details: dict[str, Any] = {}
            if action is not None:
                self._state.action_counts[action.action.value] += 1
                details = action_details(action)
                if details.get("capability"):
                    self._state.last_capability = str(details["capability"])
                summary = humanize_action(action)
            else:
                summary = "Model turn recorded; no typed action parsed"
                self._state.parse_warnings.append(
                    f"assistant iteration {iteration} has no typed action"
                )
            self._push_event(
                HumanizedEvent(
                    kind="assistant",
                    iteration=iteration,
                    summary=summary,
                    action_name=action_name,
                    research_note=action.research_note if action is not None else None,
                    model=record.get("model") if isinstance(record.get("model"), str) else None,
                    route=record.get("route") if isinstance(record.get("route"), str) else None,
                    research_role=(
                        record.get("research_role")
                        if isinstance(record.get("research_role"), str)
                        else None
                    ),
                    outcome="pending",
                    capability=details.get("capability"),
                    stage=details.get("stage"),
                    active_claim_id=details.get("active_claim_id"),
                    argv=tuple(str(item) for item in details.get("argv") or ()),
                )
            )
            return
        if kind == "adjudication":
            model = record.get("model") if isinstance(record.get("model"), str) else None
            if model is not None:
                self._state.last_model = model
            self._accumulate_usage(record)
            decision = str(record.get("decision") or "recorded")
            claim_id = str(record.get("claim_id") or "unknown claim")
            self._push_event(
                HumanizedEvent(
                    kind="adjudication",
                    iteration=iteration,
                    summary=(f"Independent judge found the evidence {decision} for {claim_id}"),
                    action_name="request_adjudication",
                    model=model,
                    route=(record.get("route") if isinstance(record.get("route"), str) else None),
                    research_role=MVPResearchRole.JUDGE.value,
                    outcome=decision,
                    active_claim_id=(claim_id if claim_id.startswith("claim_") else None),
                )
            )
            return
        if kind == "tool":
            if iteration is not None:
                self._state.tools[iteration] = record
            payload = _tool_payload(record)
            action = None
            details: dict[str, Any] = {}
            if iteration in self._state.assistant:
                action = _action_from_assistant(self._state.assistant[iteration])
                if action is not None:
                    details = action_details(action)
            execution_metrics = _execution_metrics(payload)
            if payload is None:
                summary = f"Tool result recorded for iteration {iteration or '?'}"
                outcome = "unknown"
            elif payload.get("ok") is True:
                summary = (
                    f"Completed {humanize_action(action)}"
                    if action is not None
                    else f"Completed action at iteration {iteration}"
                )
                outcome = _execution_outcome(payload, execution_metrics)
            else:
                error = str(payload.get("error") or "unknown error")
                summary = f"Action failed: {error}"
                outcome = "failed"
            self._push_event(
                HumanizedEvent(
                    kind="tool",
                    iteration=iteration,
                    summary=summary,
                    action_name=action.action.value if action is not None else None,
                    research_role=(
                        self._state.assistant.get(iteration, {}).get("research_role")
                        if iteration is not None
                        else None
                    ),
                    outcome=outcome,
                    capability=details.get("capability"),
                    stage=details.get("stage"),
                    active_claim_id=details.get("active_claim_id"),
                    argv=tuple(str(item) for item in details.get("argv") or ()),
                    console_excerpt=_console_excerpt(payload),
                    **execution_metrics,
                )
            )
            return
        if kind == "tool_heartbeat":
            self._state.last_heartbeat = record
            recorded_at = _parse_datetime(record.get("recorded_at"))
            self._state.last_heartbeat_observed_at = recorded_at or observed_at
            elapsed = _as_float(record.get("elapsed_wall_seconds"))
            workspace = _as_int(record.get("workspace_bytes"))
            parts = ["Command heartbeat"]
            if elapsed is not None:
                parts.append(f"elapsed {format_duration(elapsed)}")
            if workspace is not None:
                parts.append(f"workspace {format_bytes(workspace)}")
            action = None
            details: dict[str, Any] = {}
            if iteration in self._state.assistant:
                action = _action_from_assistant(self._state.assistant[iteration])
                if action is not None:
                    details = action_details(action)
            self._push_event(
                HumanizedEvent(
                    kind="tool_heartbeat",
                    iteration=iteration,
                    summary=", ".join(parts),
                    action_name=action.action.value if action is not None else None,
                    outcome="running",
                    capability=details.get("capability"),
                    stage=details.get("stage"),
                    active_claim_id=details.get("active_claim_id"),
                    argv=tuple(str(item) for item in details.get("argv") or ()),
                )
            )
            return
        if kind == "control":
            event = str(record.get("event") or "control event")
            action_name = record.get("action") if isinstance(record.get("action"), str) else None
            if event == "campaign_cancelled":
                summary = "Campaign cancelled"
            elif event == "campaign_paused":
                summary = "Paused at the next action boundary"
            elif event == "interrupted_action_recovered":
                summary = (
                    f"Recovered interrupted {action_name}"
                    if action_name
                    else "Recovered interrupted action"
                )
            elif event == "model_completion_retry":
                attempt = record.get("attempt")
                summary = f"Retrying model completion (attempt {attempt})"
            else:
                summary = event.replace("_", " ")
            self._push_event(
                HumanizedEvent(
                    kind="control",
                    iteration=iteration,
                    summary=summary,
                    action_name=action_name,
                )
            )

    def _push_event(self, event: HumanizedEvent) -> None:
        self._state.next_event_sequence += 1
        self._state.events.append(
            event.model_copy(update={"sequence": self._state.next_event_sequence})
        )
        if len(self._state.events) > _MAX_RETAINED_EVENTS:
            self._state.events = self._state.events[-_MAX_RETAINED_EVENTS:]

    def _read_sidecar(self, relative: str) -> dict[str, Any] | None:
        path = self.root / relative
        if not path.is_file():
            self._sidecar_cache.pop(relative, None)
            return None
        try:
            mtime_ns = path.stat().st_mtime_ns
        except OSError:
            return None
        cached = self._sidecar_cache.get(relative)
        if cached is not None and cached[0] == mtime_ns:
            return cached[1]
        payload = load_json_object(path)
        self._sidecar_cache[relative] = (mtime_ns, payload)
        return payload

    def _identity(
        self,
        manifest: dict[str, Any] | None,
        report: dict[str, Any] | None,
        ledger: dict[str, Any] | None,
        launch: dict[str, Any] | None,
    ) -> RunIdentity:
        hypothesis = None
        instruction = None
        config: dict[str, Any] = {}
        schema_version = None
        skill_hashes: dict[str, str] = {}
        capability_hashes: dict[str, str] = {}
        campaign_id = None
        if launch and isinstance(launch.get("campaign_id"), str):
            campaign_id = launch["campaign_id"]
        if campaign_id is None:
            campaign_id = self.root.name
        source = manifest or {}
        if source:
            if isinstance(source.get("hypothesis"), str):
                hypothesis = source["hypothesis"]
            if source.get("campaign_instruction") is None or isinstance(
                source.get("campaign_instruction"), str
            ):
                instruction = source.get("campaign_instruction")
            if isinstance(source.get("schema_version"), str):
                schema_version = source["schema_version"]
            if isinstance(source.get("config"), dict):
                config = source["config"]
            if isinstance(source.get("skill_hashes"), dict):
                skill_hashes = {
                    str(key): str(value) for key, value in source["skill_hashes"].items()
                }
            if isinstance(source.get("capability_hashes"), dict):
                capability_hashes = {
                    str(key): str(value)
                    for key, value in source["capability_hashes"].items()
                }
        if report:
            if hypothesis is None and isinstance(report.get("hypothesis"), str):
                hypothesis = report["hypothesis"]
            if instruction is None and (
                report.get("campaign_instruction") is None
                or isinstance(report.get("campaign_instruction"), str)
            ):
                instruction = report.get("campaign_instruction")
        if ledger and hypothesis is None and isinstance(ledger.get("root_hypothesis"), str):
            hypothesis = ledger["root_hypothesis"]
        operator_hypothesis = self.root / OPERATOR_INPUT_DIR / "hypothesis.txt"
        if hypothesis is None and operator_hypothesis.is_file():
            try:
                text = operator_hypothesis.read_text().strip()
            except OSError:
                text = ""
            if text:
                hypothesis = text
        return RunIdentity(
            run_directory=str(self.root),
            campaign_id=campaign_id,
            hypothesis=hypothesis,
            campaign_instruction=instruction,
            manifest_schema_version=schema_version,
            config=config,
            skill_hashes=skill_hashes,
            capability_hashes=capability_hashes,
        )

    def _phase(
        self,
        report: dict[str, Any] | None,
        *,
        dsh_state: dict[str, Any] | None = None,
    ) -> RunPhase:
        if report is not None:
            status = report.get("status")
            if status == "completed":
                return RunPhase.COMPLETED
            if status == "cancelled":
                return RunPhase.CANCELLED
            if status == "provider_failed":
                return RunPhase.PROVIDER_FAILED
            if status == "budget_exhausted":
                return RunPhase.BUDGET_EXHAUSTED
            # An unrecognized report is still a terminal document, not "running".
            return RunPhase.INCOMPLETE
        dsh_status = dsh_state.get("status") if dsh_state is not None else None
        if dsh_status == "cancelled":
            return RunPhase.CANCELLED
        if dsh_status == "budget_exhausted":
            return RunPhase.BUDGET_EXHAUSTED
        if dsh_status == "failed":
            return RunPhase.PROVIDER_FAILED
        if dsh_status == "paused":
            return RunPhase.PAUSED
        pause = read_pause_state(self.root)
        clock = read_clock(self.root)
        if pause is not None or (clock is not None and clock.state == "paused"):
            return RunPhase.PAUSED
        if self._state.assistant or self._state.tools or self._state.events:
            return RunPhase.INCOMPLETE
        transcript = self.root / "transcript.jsonl"
        if transcript.is_file():
            try:
                if transcript.stat().st_size > 0:
                    return RunPhase.INCOMPLETE
            except OSError:
                return RunPhase.INCOMPLETE
        if (self.root / "mvp_manifest.json").is_file():
            return RunPhase.INITIALIZED
        return RunPhase.INCOMPLETE

    def _current_action(self) -> CurrentAction | None:
        pending_iterations = [
            iteration
            for iteration in self._state.assistant
            if iteration not in self._state.tools
        ]
        if not pending_iterations:
            return None
        iteration = max(pending_iterations)
        record = self._state.assistant[iteration]
        action = _action_from_assistant(record)
        details = action_details(action) if action is not None else {}
        description = (
            humanize_action(action)
            if action is not None
            else "Model turn recorded; waiting for a tool result"
        )
        argv = details.get("argv") or ()
        return CurrentAction(
            iteration=iteration,
            action_name=details.get("action_name")
            if action is not None
            else None,
            description=description,
            pending=True,
            capability=details.get("capability"),
            stage=details.get("stage"),
            active_claim_id=details.get("active_claim_id"),
            path=details.get("path"),
            model=record.get("model") if isinstance(record.get("model"), str) else None,
            route=record.get("route") if isinstance(record.get("route"), str) else None,
            research_note=action.research_note if action is not None else None,
            argv=tuple(str(item) for item in argv),
        )

    def _executions(
        self,
        *,
        current: CurrentAction | None,
        heartbeat: HeartbeatObservation | None,
    ) -> tuple[ComputeExecutionSummary, ...]:
        rows: list[ComputeExecutionSummary] = []
        for iteration in sorted(self._state.assistant, reverse=True):
            record = self._state.assistant[iteration]
            action = _action_from_assistant(record)
            if action is None or action.action.value not in _EXECUTION_ACTION_NAMES:
                continue
            details = action_details(action)
            tool = (
                _tool_payload(self._state.tools[iteration])
                if iteration in self._state.tools
                else None
            )
            metrics = _execution_metrics(tool)
            status = _execution_outcome(tool, metrics)
            if current is not None and current.iteration == iteration:
                status = "running"
            if heartbeat is not None and heartbeat.iteration == iteration and status == "running":
                if heartbeat.elapsed_wall_seconds is not None:
                    metrics["elapsed_wall_seconds"] = heartbeat.elapsed_wall_seconds
                if heartbeat.stdout_bytes is not None:
                    metrics["stdout_bytes"] = heartbeat.stdout_bytes
                if heartbeat.stderr_bytes is not None:
                    metrics["stderr_bytes"] = heartbeat.stderr_bytes
                if heartbeat.workspace_bytes is not None:
                    metrics["workspace_bytes"] = heartbeat.workspace_bytes
            rows.append(
                ComputeExecutionSummary(
                    id=f"iteration-{iteration}",
                    iteration=iteration,
                    action_name=action.action.value,
                    description=humanize_action(action),
                    status=status,
                    capability=details.get("capability"),
                    stage=details.get("stage"),
                    active_claim_id=details.get("active_claim_id"),
                    argv=tuple(str(item) for item in details.get("argv") or ()),
                    model=record.get("model")
                    if isinstance(record.get("model"), str)
                    else None,
                    route=record.get("route")
                    if isinstance(record.get("route"), str)
                    else None,
                    research_note=action.research_note,
                    console_excerpt=_console_excerpt(tool),
                    **metrics,
                )
            )
            if len(rows) >= _MAX_PROJECTED_EXECUTIONS:
                break
        return tuple(rows)

    def _claims(
        self,
        ledger: dict[str, Any] | None,
        report: dict[str, Any] | None,
        current: CurrentAction | None,
    ) -> tuple[ClaimSummary, ...]:
        payload = None
        if ledger and isinstance(ledger.get("claims"), list):
            payload = ledger["claims"]
        elif report and isinstance(report.get("claim_ledger"), dict):
            claims = report["claim_ledger"].get("claims")
            if isinstance(claims, list):
                payload = claims
        if not payload:
            return ()
        active_id = current.active_claim_id if current is not None else None
        summaries: list[ClaimSummary] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            claim_id = item.get("id")
            if not isinstance(claim_id, str) or not claim_id:
                continue
            evidence = item.get("evidence") or []
            contracts = item.get("evidence_contracts") or []
            summaries.append(
                ClaimSummary(
                    id=claim_id,
                    status=str(item.get("status") or "open"),
                    kind=str(item["kind"]) if isinstance(item.get("kind"), str) else None,
                    relation=(
                        str(item["relation"])
                        if isinstance(item.get("relation"), str)
                        else None
                    ),
                    parent_id=(
                        str(item["parent_id"])
                        if isinstance(item.get("parent_id"), str)
                        else None
                    ),
                    statement=str(item.get("statement") or ""),
                    evidence_count=len(evidence) if isinstance(evidence, list) else 0,
                    contract_count=len(contracts) if isinstance(contracts, list) else 0,
                    closed_reason=(
                        str(item["closed_reason"])
                        if isinstance(item.get("closed_reason"), str)
                        else None
                    ),
                    active=claim_id == active_id,
                )
            )
        return tuple(summaries)

    def _heartbeat(self, observed_at: datetime) -> HeartbeatObservation | None:
        record = self._state.last_heartbeat
        if not record:
            return None
        iteration = _iteration_of(record)
        if iteration is None:
            return None
        seen_at = self._state.last_heartbeat_observed_at
        age = None
        if seen_at is not None:
            age = max(0.0, (observed_at - seen_at).total_seconds())
        return HeartbeatObservation(
            iteration=iteration,
            elapsed_wall_seconds=_as_float(record.get("elapsed_wall_seconds")),
            stdout_bytes=_as_int(record.get("stdout_bytes")),
            stderr_bytes=_as_int(record.get("stderr_bytes")),
            workspace_bytes=_as_int(record.get("workspace_bytes")),
            observed_at=seen_at,
            age_seconds=age,
        )

    def _terminal_report(
        self, report: dict[str, Any] | None
    ) -> TerminalReportSummary | None:
        if not report:
            return None
        status = report.get("status")
        if not isinstance(status, str):
            return None
        artifacts = report.get("workspace_artifacts")
        artifact_count = len(artifacts) if isinstance(artifacts, dict) else 0
        open_ids = tuple(
            str(item) for item in report.get("open_claim_ids") or [] if item
        )
        closed_ids = tuple(
            str(item) for item in report.get("closed_claim_ids") or [] if item
        )
        notes = tuple(
            str(item) for item in report.get("finish_claim_notes") or [] if item
        )
        return TerminalReportSummary(
            status=status,
            final_answer=str(report.get("final_answer") or ""),
            iterations=max(0, _as_int(report.get("iterations")) or 0),
            elapsed_wall_seconds=max(0.0, _as_float(report.get("elapsed_wall_seconds")) or 0.0),
            started_at=_parse_datetime(report.get("started_at")),
            finished_at=_parse_datetime(report.get("finished_at")),
            open_claim_ids=open_ids,
            closed_claim_ids=closed_ids,
            finish_claim_notes=notes,
            workspace_artifact_count=artifact_count,
        )

    def _elapsed(
        self,
        *,
        report: dict[str, Any] | None,
        configured: float | None,
        heartbeat: HeartbeatObservation | None,
        observed_at: datetime,
    ) -> tuple[float | None, bool]:
        clock = read_clock(self.root)
        if clock is not None:
            return elapsed_from_clock(clock, now=observed_at), False
        if report is not None:
            value = _as_float(report.get("elapsed_wall_seconds"))
            if value is not None:
                return max(0.0, value), False
        started = None
        if report is not None:
            started = _parse_datetime(report.get("started_at"))
        if started is None:
            started = _latest_mtime(self.root)
            if started is None:
                return None, False
            return max(0.0, (observed_at - started).total_seconds()), True
        elapsed = max(0.0, (observed_at - started).total_seconds())
        if configured is not None:
            elapsed = min(elapsed, configured)
        if heartbeat is not None and heartbeat.elapsed_wall_seconds is not None:
            # Heartbeat is command-local; keep directory estimate for campaign clock.
            return elapsed, True
        return elapsed, True

    def _accumulate_usage(
        self,
        record: dict[str, Any],
        *,
        target: _UsageState | None = None,
        fallback_model: str | None = None,
        count_turn: bool = True,
    ) -> None:
        selected = target or self._state.usage
        usage = parse_usage_payload(record.get("usage"))
        has_usage = any(
            usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        )
        if not has_usage:
            selected.missing_usage_turns += 1
            return
        if count_turn:
            selected.usage_turns += 1
        selected.prompt_tokens += usage["prompt_tokens"]
        selected.completion_tokens += usage["completion_tokens"]
        selected.total_tokens += usage["total_tokens"]
        selected.cached_tokens += usage["cached_tokens"]
        selected.reasoning_tokens += usage["reasoning_tokens"]
        model = (
            record.get("model")
            if isinstance(record.get("model"), str)
            else fallback_model or "unknown"
        )
        bucket = selected.model_usage.setdefault(
            model,
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "turns": 0},
        )
        bucket["prompt_tokens"] += usage["prompt_tokens"]
        bucket["completion_tokens"] += usage["completion_tokens"]
        bucket["total_tokens"] += usage["total_tokens"]
        if count_turn:
            bucket["turns"] += 1

    def _token_usage(self) -> TokenUsageSummary:
        sources = (self._state.usage, self._dsh_usage)
        model_totals: dict[str, dict[str, int]] = {}
        for source in sources:
            for name, values in source.model_usage.items():
                bucket = model_totals.setdefault(
                    name,
                    {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "turns": 0,
                    },
                )
                for key in bucket:
                    bucket[key] += values[key]
        by_model = tuple(
            ModelTokenUsage(
                model=name,
                prompt_tokens=values["prompt_tokens"],
                completion_tokens=values["completion_tokens"],
                total_tokens=values["total_tokens"],
                turns=values["turns"],
            )
            for name, values in sorted(model_totals.items())
        )
        prompt_tokens = sum(source.prompt_tokens for source in sources)
        completion_tokens = sum(source.completion_tokens for source in sources)
        total_tokens = sum(source.total_tokens for source in sources)
        cached_tokens = sum(source.cached_tokens for source in sources)
        reasoning_tokens = sum(source.reasoning_tokens for source in sources)
        turns = sum(source.usage_turns for source in sources)
        missing_turns = sum(source.missing_usage_turns for source in sources)
        return TokenUsageSummary(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            turns=turns,
            turns_missing_usage=missing_turns,
            by_model=by_model,
            label=format_token_counts(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                turns=turns,
                missing_turns=missing_turns,
                cached_tokens=cached_tokens,
            ),
        )

    def _artifact_paths(self) -> ArtifactPaths:
        return ArtifactPaths(
            run_directory=str(self.root),
            manifest=_existing_path(self.root / "mvp_manifest.json"),
            transcript=_existing_path(self.root / "transcript.jsonl"),
            report=_existing_path(self.root / "mvp_report.json"),
            claim_ledger=_existing_path(self.root / "hypothesis_ledger.json"),
            claim_summary=_existing_path(self.root / "claim_summary.md"),
            loop_state=_existing_path(self.root / "loop_state.json"),
            adjudications=_existing_path(self.root / "adjudications.json"),
            artifact_provenance=_existing_path(self.root / "artifact_provenance.json"),
            workspace=_existing_path(self.root / "workspace"),
            controller_log=_existing_path(self.root / "controller.log"),
            operator_input=_existing_path(self.root / OPERATOR_INPUT_DIR),
        )


def load_run_snapshot(
    run_directory: str | Path,
    *,
    now: datetime | None = None,
) -> MVPRunSnapshot:
    return MVPRunMonitor(run_directory).snapshot(now=now)


def format_human_status(snapshot: MVPRunSnapshot) -> str:
    identity = snapshot.identity
    campaign = identity.campaign_id or Path(identity.run_directory).name
    lines = [
        f"Campaign: {campaign}       {snapshot.phase_label}",
        f"directory: {identity.run_directory}",
    ]
    elapsed = format_duration(snapshot.elapsed_wall_seconds)
    budget = format_duration(snapshot.configured_wall_seconds)
    estimate = " ~" if snapshot.elapsed_is_estimate else " "
    heartbeat = "heartbeat --"
    if snapshot.latest_heartbeat is not None:
        heartbeat = f"heartbeat {format_age(snapshot.latest_heartbeat.age_seconds)}"
    lines.append(f"elapsed{estimate}{elapsed} / {budget}     {heartbeat}")
    model = snapshot.last_model
    if snapshot.current_action is not None and snapshot.current_action.model:
        model = snapshot.current_action.model
    capability = snapshot.last_capability
    if snapshot.current_action and snapshot.current_action.capability:
        capability = snapshot.current_action.capability
    lines.append(
        f"model: {model or '-'}                 capability: {capability or '-'}"
    )
    lines.append(f"iterations: {snapshot.iterations}")
    lines.append(snapshot.token_usage.label)
    loop = snapshot.loop_state
    lines.append(
        "loop: "
        f"cycle {loop.cycle} · {loop.stage.value} · role {loop.role.value}"
        + (f" · {loop.active_claim_id}" if loop.active_claim_id else "")
    )
    if snapshot.pending_control:
        lines.append(f"pending control: {snapshot.pending_control} at next action boundary")
    lines.append("")
    lines.append("Root hypothesis")
    hypothesis = (identity.hypothesis or "(not yet recorded)").strip()
    for raw in hypothesis.splitlines() or ["(not yet recorded)"]:
        lines.append(f"  {raw}")
    if identity.campaign_instruction:
        lines.append("")
        lines.append("Operational instruction")
        for raw in identity.campaign_instruction.strip().splitlines():
            lines.append(f"  {raw}")
    lines.append("")
    lines.append("Claims")
    if not snapshot.claims:
        lines.append("  (no claims recorded)")
    for claim in snapshot.claims:
        marker = claim_status_marker(claim.status)
        active = "   current" if claim.active else ""
        lines.append(
            f"  {marker} {claim.id:<28} {claim.status:<18} evidence {claim.evidence_count}{active}"
        )
    lines.append("")
    lines.append("Current action")
    if snapshot.current_action is None:
        if snapshot.phase in {
            RunPhase.COMPLETED,
            RunPhase.CANCELLED,
            RunPhase.PROVIDER_FAILED,
            RunPhase.BUDGET_EXHAUSTED,
        }:
            if snapshot.report is not None:
                lines.append("  (campaign has a terminal report)")
            else:
                lines.append(
                    "  (campaign stopped at an engine boundary; no scientific report was written)"
                )
        elif snapshot.phase is RunPhase.PAUSED:
            lines.append("  (paused at an action boundary; resume to continue)")
        else:
            lines.append("  (no pending action)")
    else:
        action = snapshot.current_action
        lines.append(f"  {action.description}")
        details: list[str] = [f"iteration={action.iteration}"]
        if action.stage:
            details.append(f"stage={action.stage}")
        if snapshot.latest_heartbeat and snapshot.latest_heartbeat.elapsed_wall_seconds is not None:
            details.append(
                f"elapsed={int(snapshot.latest_heartbeat.elapsed_wall_seconds)} s"
            )
        details.append(f"workspace={format_bytes(snapshot.workspace_bytes)}")
        lines.append("  " + ", ".join(details))
    lines.append("")
    lines.append("Recent activity")
    events = snapshot.recent_events[-8:]
    if not events:
        lines.append("  (no transcript events yet)")
    for event in events:
        lines.append(f"  {event.summary}")
    if snapshot.report is not None:
        lines.append("")
        lines.append(f"Terminal report: {snapshot.report.status}")
        answer = snapshot.report.final_answer.strip()
        if answer:
            lines.append("Final answer")
            preview = answer if len(answer) <= 1200 else answer[:1197] + "..."
            for raw in preview.splitlines():
                lines.append(f"  {raw}")
        if snapshot.report.finish_claim_notes:
            lines.append("Finish notes")
            for note in snapshot.report.finish_claim_notes:
                lines.append(f"  {note}")
    if snapshot.warnings:
        lines.append("")
        lines.append("Warnings")
        for warning in snapshot.warnings:
            lines.append(f"  {warning}")
    return "\n".join(lines) + "\n"


def watch_run(
    run_directory: str | Path,
    *,
    jsonl: bool = False,
    poll_seconds: float = 0.5,
    output: TextIO | None = None,
    sleep: Callable[[float], None] = time.sleep,
    should_stop: Callable[[], bool] | None = None,
    now: Callable[[], datetime] = utc_now,
) -> int:
    """Follow durable records until a terminal report appears.

    Interrupting this viewer does not cancel the scientific campaign.
    """

    stream = output if output is not None else sys.stdout
    monitor = MVPRunMonitor(run_directory)
    last_event_sequence = 0
    last_cursor = TranscriptCursor()
    last_signature: tuple[Any, ...] | None = None
    try:
        while True:
            snapshot = monitor.snapshot(now=now())
            cursor = snapshot.transcript_cursor
            if last_cursor.inode is not None and (
                cursor.inode != last_cursor.inode or cursor.offset < last_cursor.offset
            ):
                last_event_sequence = 0
            last_cursor = cursor
            events = snapshot.recent_events
            new_events = tuple(
                event for event in events if event.sequence > last_event_sequence
            )
            if events:
                last_event_sequence = max(
                    last_event_sequence,
                    max(event.sequence for event in events),
                )
            signature = (
                snapshot.phase,
                snapshot.iterations,
                snapshot.current_action.description if snapshot.current_action else None,
                snapshot.latest_heartbeat.age_seconds if snapshot.latest_heartbeat else None,
                len(snapshot.claims),
                snapshot.report.status if snapshot.report else None,
                snapshot.loop_state.stage,
                snapshot.loop_state.role,
                snapshot.loop_state.cycle,
            )
            if jsonl:
                stream.write(snapshot.model_dump_json() + "\n")
                stream.flush()
            elif signature != last_signature or new_events:
                if last_signature is None:
                    stream.write(format_human_status(snapshot))
                else:
                    for event in new_events:
                        stream.write(f"  {event.summary}\n")
                    if signature[0] != last_signature[0] or snapshot.report is not None:
                        stream.write(format_human_status(snapshot))
                stream.flush()
                last_signature = signature
            if snapshot.phase in {
                RunPhase.COMPLETED,
                RunPhase.CANCELLED,
                RunPhase.PROVIDER_FAILED,
                RunPhase.BUDGET_EXHAUSTED,
                RunPhase.PAUSED,
            }:
                return 0
            if should_stop is not None and should_stop():
                return 0
            sleep(max(0.05, poll_seconds))
    except KeyboardInterrupt:
        if not jsonl:
            stream.write("watch stopped; the campaign was not cancelled\n")
            stream.flush()
        return 0


def installed_capability_descriptors(
    project_root: str | Path | None = None,
) -> tuple[dict[str, Any], ...]:
    """Return generic descriptors of currently installed capabilities."""

    from .mvp_skills import discover_builtin_mvp_resources

    _skills, capabilities = discover_builtin_mvp_resources(project_root)
    descriptors: list[dict[str, Any]] = []
    for item in capabilities.descriptors():
        descriptors.append(
            {
                "name": item.get("name"),
                "version": item.get("version"),
                "description": item.get("description"),
                "skill": item.get("skill"),
                "runtime": item.get("runtime"),
            }
        )
    return tuple(descriptors)
