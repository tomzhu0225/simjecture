"""Framework-independent application layer for the local Simjecture web UI."""

from __future__ import annotations

import hashlib
import mimetypes
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from ..mvp_launch import (
    MVPLaunchRequest,
    ResumeError,
    load_supervisor_record,
    materialize_operator_input,
    output_lock_is_held,
    prepare_resume,
    process_identity_matches,
    request_graceful_cancel,
    request_verified_pause,
    start_managed_campaign,
    validate_campaign_id,
)
from ..mvp_monitor import (
    MVPRunMonitor,
    RunPhase,
    contained_path,
    discover_recent_runs,
    format_age,
    format_bytes,
    format_duration,
    list_contained_artifacts,
    load_json_object,
)
from ..presentation import build_hypothesis_tree, build_validation_tree

API_SCHEMA_VERSION = "0.2.0"
MAX_CAMPAIGNS = 100
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
VISIBLE_RECORDS = frozenset(
    {
        "artifact_provenance.json",
        "claim_summary.md",
        "controller.log",
        "hypothesis_ledger.json",
        "mvp_manifest.json",
        "mvp_report.json",
    }
)
IMAGE_SUFFIXES = frozenset({".apng", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"})
TEXT_SUFFIXES = frozenset(
    {".csv", ".json", ".jsonl", ".log", ".md", ".py", ".txt", ".yaml", ".yml"}
)


class WebApplicationError(RuntimeError):
    """A safe operator-facing error returned by the local API."""

    def __init__(self, message: str, *, status: int = 400) -> None:
        self.status = status
        super().__init__(message)


@dataclass(frozen=True)
class ArtifactResource:
    path: Path
    content_type: str
    size: int


class CampaignRegistry:
    """Resolve opaque browser identifiers to explicitly discovered run roots."""

    def __init__(
        self,
        *,
        initial_run: str | Path | None,
        scan_roots: tuple[str | Path, ...],
    ) -> None:
        self.scan_roots = tuple(Path(item).expanduser().resolve() for item in scan_roots)
        self._paths: dict[str, Path] = {}
        self.initial_token: str | None = None
        if initial_run is not None:
            path = Path(initial_run).expanduser().resolve()
            if not path.is_dir():
                raise FileNotFoundError(f"run directory does not exist: {path}")
            self.initial_token = self.register(path)
        self.refresh()

    @staticmethod
    def token_for(path: Path) -> str:
        return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:20]

    def register(self, path: str | Path) -> str:
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_dir():
            raise FileNotFoundError(f"run directory does not exist: {resolved}")
        token = self.token_for(resolved)
        previous = self._paths.get(token)
        if previous is not None and previous != resolved:
            raise RuntimeError("campaign identifier collision")
        self._paths[token] = resolved
        return token

    def refresh(self) -> None:
        for recent in discover_recent_runs(self.scan_roots, limit=MAX_CAMPAIGNS):
            try:
                self.register(recent.run_directory)
            except OSError:
                continue

    def resolve(self, token: str) -> Path:
        try:
            return self._paths[token]
        except KeyError as error:
            raise WebApplicationError("unknown campaign", status=404) from error

    def items(self) -> tuple[tuple[str, Path], ...]:
        return tuple(self._paths.items())


class SimjectureWebApplication:
    """Project campaigns and execute the small set of reviewed operator controls."""

    def __init__(
        self,
        *,
        initial_run: str | Path | None = None,
        scan_roots: tuple[str | Path, ...] = (),
        runs_root: str | Path = "artifacts",
        allow_mutations: bool = True,
    ) -> None:
        roots = scan_roots or (Path.cwd() / "artifacts", Path.cwd() / "demos")
        self.registry = CampaignRegistry(initial_run=initial_run, scan_roots=roots)
        self.runs_root = Path(runs_root).expanduser().resolve()
        self.allow_mutations = allow_mutations
        self._monitors: dict[str, MVPRunMonitor] = {}
        self._lock = threading.RLock()

    @property
    def initial_campaign(self) -> str | None:
        if self.registry.initial_token is not None:
            return self.registry.initial_token
        campaigns = self.campaigns()
        return str(campaigns[0]["id"]) if campaigns else None

    def bootstrap(self) -> dict[str, Any]:
        campaigns = self.campaigns()
        selected = self.registry.initial_token
        if selected is None and campaigns:
            selected = str(campaigns[0]["id"])
        return {
            "schema_version": API_SCHEMA_VERSION,
            "product": "Simjecture",
            "allow_mutations": self.allow_mutations,
            "selected_campaign": selected,
            "campaigns": campaigns,
        }

    def campaigns(self) -> list[dict[str, Any]]:
        with self._lock:
            self.registry.refresh()
            cards: list[dict[str, Any]] = []
            for token, path in self.registry.items():
                try:
                    snapshot = self._monitor(token, path).snapshot()
                except (OSError, ValueError):
                    continue
                stamp = _latest_campaign_mtime(path)
                live = _is_live(path)
                cards.append(
                    {
                        "id": token,
                        "campaign_id": snapshot.identity.campaign_id or path.name,
                        "display_name": _campaign_display_name(snapshot, path),
                        "path": _display_path(path),
                        "phase": snapshot.phase.value,
                        "phase_label": snapshot.phase_label,
                        "execution_status": _execution_status(snapshot.phase, live),
                        "hypothesis": snapshot.identity.hypothesis,
                        "modified_at": stamp.isoformat() if stamp else None,
                    }
                )
            cards.sort(key=lambda item: item["modified_at"] or "", reverse=True)
            return cards

    def campaign_snapshot(self, token: str) -> dict[str, Any]:
        with self._lock:
            root = self.registry.resolve(token)
            snapshot = self._monitor(token, root).snapshot()
            live = _is_live(root)
            raw_claims = _raw_claims(root)
            claim_details = _claim_details(raw_claims, root=root)
            scientific_rows = build_hypothesis_tree(snapshot.claims)
            scientific_ids = {row.claim.id for row in scientific_rows}
            scientific_nodes = [
                {
                    **row.claim.model_dump(mode="json"),
                    "depth": row.depth,
                    "orphaned": row.orphaned,
                }
                for row in scientific_rows
            ]
            scientific_edges = [
                {
                    "source": row.claim.parent_id,
                    "target": row.claim.id,
                    "relation": row.claim.relation,
                }
                for row in scientific_rows
                if row.claim.parent_id in scientific_ids
            ]
            supporting_rows_by_owner = {
                claim_id: build_validation_tree(snapshot.claims, claim_id)
                for claim_id in scientific_ids
            }
            claim_graph_nodes = [
                {**node, "owner_id": node["id"]}
                for node in scientific_nodes
            ]
            claim_graph_edges = list(scientific_edges)
            for owner_id, rows in supporting_rows_by_owner.items():
                supporting_ids = {row.claim.id for row in rows}
                for row in rows:
                    claim_graph_nodes.append(
                        {
                            **row.claim.model_dump(mode="json"),
                            "depth": row.depth,
                            "orphaned": row.orphaned,
                            "owner_id": owner_id,
                        }
                    )
                    source = (
                        row.claim.parent_id
                        if row.claim.parent_id in supporting_ids
                        else owner_id
                    )
                    claim_graph_edges.append(
                        {
                            "source": source,
                            "target": row.claim.id,
                            "relation": row.claim.relation,
                        }
                    )
            commissioning = _commissioning_projection(
                claim_graph_nodes,
                claim_details=claim_details,
                guided=_guided_commissioning_projection(root),
            )
            artifacts = _artifact_index(root, raw_claims=raw_claims)
            controls = _control_capabilities(root, phase=snapshot.phase, live=live)
            if not self.allow_mutations:
                controls = {
                    "can_pause": False,
                    "can_resume": False,
                    "can_cancel": False,
                    "read_only_reason": "this web session is read-only",
                }
            revision = _revision(snapshot, root=root, live=live)
            payload = snapshot.model_dump(mode="json")
            payload["identity"]["run_directory"] = _display_path(root)
            payload["execution_status"] = _execution_status(snapshot.phase, live)
            payload["process_live"] = live
            return {
                "schema_version": API_SCHEMA_VERSION,
                "campaign": token,
                "display_name": _campaign_display_name(snapshot, root),
                "revision": revision,
                "snapshot": payload,
                "claim_graph": {"nodes": claim_graph_nodes, "edges": claim_graph_edges},
                "claim_details": claim_details,
                "commissioning": commissioning,
                "executions": _execution_projection(snapshot),
                "artifacts": artifacts,
                "controls": controls,
                "formatted": {
                    "elapsed": format_duration(snapshot.elapsed_wall_seconds),
                    "workspace": format_bytes(snapshot.workspace_bytes),
                    "heartbeat_age": (
                        format_age(snapshot.latest_heartbeat.age_seconds)
                        if snapshot.latest_heartbeat
                        else None
                    ),
                },
            }

    def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_mutations()
        hypothesis = _required_text(payload, "hypothesis", maximum=20_000)
        instruction = _optional_text(payload, "instruction", maximum=20_000)
        supplied_id = _optional_text(payload, "campaign_id", maximum=128)
        try:
            campaign_id = validate_campaign_id(supplied_id or _default_campaign_id())
            request = MVPLaunchRequest(
                hypothesis=hypothesis,
                instruction=instruction,
                campaign_id=campaign_id,
                output_directory=str(self.runs_root / campaign_id),
                max_wall_seconds=_bounded_float(payload, "max_wall_seconds", 21_600, 1, 604_800),
                max_command_seconds=_bounded_float(payload, "max_command_seconds", 600, 1, 86_400),
                max_workspace_mb=_bounded_int(payload, "max_workspace_mb", 512, 1, 1_048_576),
                max_memory_mb=_bounded_int(payload, "max_memory_mb", 4096, 1, 1_048_576),
            )
        except ValueError as error:
            raise WebApplicationError(str(error), status=400) from error
        try:
            plan = materialize_operator_input(request)
            campaign = start_managed_campaign(plan)
        except Exception as error:
            raise WebApplicationError(str(error), status=409) from error
        campaign.close()
        with self._lock:
            token = self.registry.register(plan.output_directory)
            self._monitors[token] = MVPRunMonitor(plan.output_directory)
        return {
            "campaign": token,
            "campaign_id": campaign_id,
            "pid": campaign.identity.pid,
            "message": "campaign launched",
        }

    def execution(self, token: str, iteration: int) -> dict[str, Any]:
        """Return one bounded execution detail without bloating the live snapshot."""

        if iteration < 1:
            raise WebApplicationError("invalid execution iteration", status=400)
        with self._lock:
            root = self.registry.resolve(token)
            snapshot = self._monitor(token, root).snapshot()
            execution = next(
                (item for item in snapshot.executions if item.iteration == iteration),
                None,
            )
            if execution is None:
                raise WebApplicationError("execution not found", status=404)
            payload = execution.model_dump(mode="json")
            payload["label"] = _execution_label(
                execution.action_name,
                execution.capability,
            )
            return {
                "schema_version": API_SCHEMA_VERSION,
                "campaign": token,
                "execution": payload,
            }

    def control(self, token: str, action: str) -> dict[str, Any]:
        self._require_mutations()
        root = self.registry.resolve(token)
        if action == "pause":
            message = request_verified_pause(root, source="web")
            if not message.startswith("pause requested"):
                raise WebApplicationError(message, status=409)
            return {"message": message}
        if action == "resume":
            try:
                plan = prepare_resume(root)
                campaign = start_managed_campaign(plan)
            except ResumeError as error:
                raise WebApplicationError(str(error), status=409) from error
            except Exception as error:
                raise WebApplicationError(str(error), status=500) from error
            campaign.close()
            return {
                "message": "campaign resumed",
                "pid": campaign.identity.pid,
            }
        if action == "cancel":
            identity = load_supervisor_record(root)
            if identity is None or not process_identity_matches(identity):
                raise WebApplicationError(
                    "no verified running process; no signal sent",
                    status=409,
                )
            message = request_graceful_cancel(identity)
            return {"message": message}
        raise WebApplicationError("unknown control action", status=404)

    def artifact(self, token: str, relative_path: str) -> ArtifactResource:
        root = self.registry.resolve(token)
        normalized = PurePosixPath(relative_path)
        if (
            normalized.is_absolute()
            or ".." in normalized.parts
            or not normalized.parts
            or "\x00" in relative_path
        ):
            raise WebApplicationError("invalid artifact path", status=400)
        requested = root.joinpath(*normalized.parts)
        _reject_symlink_path(root, requested)
        path = contained_path(root, normalized)
        if path is None or not path.is_file():
            raise WebApplicationError("artifact not found", status=404)
        try:
            size = path.stat().st_size
        except OSError as error:
            raise WebApplicationError("artifact could not be read", status=404) from error
        if size > MAX_ARTIFACT_BYTES:
            raise WebApplicationError("artifact is too large for browser delivery", status=413)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix.lower() in TEXT_SUFFIXES and content_type == "application/octet-stream":
            content_type = "text/plain; charset=utf-8"
        return ArtifactResource(path=path, content_type=content_type, size=size)

    def _monitor(self, token: str, path: Path) -> MVPRunMonitor:
        monitor = self._monitors.get(token)
        if monitor is None:
            monitor = MVPRunMonitor(path)
            self._monitors[token] = monitor
        return monitor

    def _require_mutations(self) -> None:
        if not self.allow_mutations:
            raise WebApplicationError("this web session is read-only", status=403)


def _raw_claims(root: Path) -> list[dict[str, Any]]:
    ledger = load_json_object(root / "hypothesis_ledger.json")
    if ledger and isinstance(ledger.get("claims"), list):
        return [item for item in ledger["claims"] if isinstance(item, dict)]
    report = load_json_object(root / "mvp_report.json")
    if report and isinstance(report.get("claim_ledger"), dict):
        claims = report["claim_ledger"].get("claims")
        if isinstance(claims, list):
            return [item for item in claims if isinstance(item, dict)]
    return []


def _claim_details(raw_claims: list[dict[str, Any]], *, root: Path) -> dict[str, Any]:
    details: dict[str, Any] = {}
    for raw in raw_claims:
        claim_id = raw.get("id")
        if not isinstance(claim_id, str) or not claim_id:
            continue
        evidence = []
        for entry in raw.get("evidence") or []:
            if not isinstance(entry, dict):
                continue
            enriched = dict(entry)
            path = entry.get("path")
            if isinstance(path, str):
                enriched["artifact_path"] = _resolve_evidence_path(root, path)
            evidence.append(enriched)
        details[claim_id] = {
            "id": claim_id,
            "statement": str(raw.get("statement") or ""),
            "kind": raw.get("kind"),
            "relation": raw.get("relation"),
            "parent_id": raw.get("parent_id"),
            "status": str(raw.get("status") or "open"),
            "rationale": raw.get("rationale"),
            "closed_reason": raw.get("closed_reason"),
            "created_iteration": raw.get("created_iteration"),
            "updated_iteration": raw.get("updated_iteration"),
            "evidence_contracts": [
                item for item in raw.get("evidence_contracts") or [] if isinstance(item, dict)
            ],
            "evidence": evidence,
        }
    return details


def _guided_commissioning_projection(root: Path) -> dict[str, Any]:
    payload = load_json_object(root / "guided_commissioning.json")
    if not payload:
        return {"available": False}
    limitations = payload.get("limitations")
    return {
        "available": bool(payload.get("available", True)),
        "name": payload.get("name"),
        "description": payload.get("description"),
        "policy": payload.get("policy"),
        "capability": payload.get("capability"),
        "program_path": payload.get("program_path"),
        "operator_validation": payload.get("operator_validation"),
        "limitations": (
            [str(item) for item in limitations if isinstance(item, str)]
            if isinstance(limitations, list)
            else []
        ),
        "package_sha256": payload.get("package_sha256"),
    }


def _commissioning_projection(
    claim_nodes: list[dict[str, Any]],
    *,
    claim_details: dict[str, Any],
    guided: dict[str, Any],
) -> dict[str, Any]:
    """Project capability commissioning without inventing a fifth claim kind."""

    scientific = [node for node in claim_nodes if node.get("kind") == "scientific"]
    instrument_by_parent: dict[str, list[dict[str, Any]]] = {}
    for node in claim_nodes:
        if node.get("kind") == "instrument" and node.get("relation") == "instrument_of":
            parent_id = node.get("parent_id")
            if isinstance(parent_id, str):
                instrument_by_parent.setdefault(parent_id, []).append(node)

    candidates: list[tuple[dict[str, Any], list[dict[str, Any]], int]] = []
    for node in scientific:
        details = claim_details.get(str(node.get("id")), {})
        binding_count = _execution_binding_count(details.get("evidence_contracts"))
        instruments = instrument_by_parent.get(str(node.get("id")), [])
        if instruments or binding_count:
            candidates.append((node, instruments, binding_count))

    if guided.get("available") and not candidates and scientific:
        root = next((node for node in scientific if node.get("id") == "claim_root"), scientific[0])
        candidates.append((root, [], 0))

    guided_owner = next(
        (str(node.get("id")) for node, instruments, _count in candidates if instruments),
        str(candidates[0][0].get("id")) if candidates else None,
    )
    stages = []
    for node, instruments, binding_count in candidates:
        scientific_id = str(node.get("id"))
        statuses = [str(item.get("status") or "open") for item in instruments]
        stages.append(
            {
                "id": f"stage_commissioning_{scientific_id}",
                "node_type": "stage",
                "stage": "commissioning",
                "kind": "stage",
                "scientific_claim_id": scientific_id,
                "owner_id": scientific_id,
                "claim_ids": [str(item["id"]) for item in instruments],
                "binding_count": binding_count,
                "guided_available": bool(guided.get("available"))
                and scientific_id == guided_owner,
                "status": _commissioning_status(statuses, binding_count=binding_count),
            }
        )
    return {"guided": guided, "stages": stages}


def _execution_binding_count(contracts: Any) -> int:
    if not isinstance(contracts, list):
        return 0
    identities: set[tuple[str, str]] = set()
    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        bindings = [contract.get("execution_binding")]
        additional = contract.get("additional_execution_bindings")
        if isinstance(additional, list):
            bindings.extend(additional)
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            capability = binding.get("capability")
            program = binding.get("program_path")
            if isinstance(capability, str) and isinstance(program, str):
                identities.add((capability, program))
    return len(identities)


def _commissioning_status(statuses: list[str], *, binding_count: int) -> str:
    if any(status == "open" for status in statuses):
        return "open"
    if statuses and all(status == "supported" for status in statuses):
        return "supported"
    for status in ("instrument_limited", "unresolved", "weakened", "falsified"):
        if status in statuses:
            return status
    return "open" if binding_count else "available"


def _resolve_evidence_path(root: Path, value: str) -> str | None:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or "\x00" in value:
        return None
    candidates = (relative, PurePosixPath("workspace") / relative)
    for candidate in candidates:
        try:
            path = contained_path(root, candidate)
        except (OSError, ValueError):
            continue
        if path is not None and path.is_file():
            return candidate.as_posix()
    return None


def _artifact_index(root: Path, *, raw_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claimed_by: dict[str, list[str]] = {}
    for claim in raw_claims:
        claim_id = claim.get("id")
        if not isinstance(claim_id, str):
            continue
        for evidence in claim.get("evidence") or []:
            if not isinstance(evidence, dict) or not isinstance(evidence.get("path"), str):
                continue
            path = _resolve_evidence_path(root, evidence["path"])
            if path:
                claimed_by.setdefault(path, []).append(claim_id)
    results: list[dict[str, Any]] = []
    for artifact in list_contained_artifacts(root, max_entries=600):
        relative = artifact.relative_path
        if artifact.kind != "file":
            continue
        if not (relative.startswith("workspace/") or relative in VISIBLE_RECORDS):
            continue
        if "/__pycache__/" in relative or "/." in relative:
            continue
        suffix = Path(relative).suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            preview = "image"
        elif suffix in TEXT_SUFFIXES and artifact.bytes <= 2 * 1024 * 1024:
            preview = "text"
        else:
            preview = "download"
        results.append(
            {
                "path": relative,
                "name": Path(relative).name,
                "bytes": artifact.bytes,
                "size_label": format_bytes(artifact.bytes),
                "preview": preview,
                "category": "workspace" if relative.startswith("workspace/") else "record",
                "claimed_by": sorted(set(claimed_by.get(relative, []))),
            }
        )
    results.sort(
        key=lambda item: (
            0 if item["claimed_by"] else 1,
            0 if item["preview"] == "image" else 1,
            item["path"],
        )
    )
    return results


def _execution_projection(snapshot: Any) -> dict[str, Any]:
    """Project bounded compute history as selectable runs, never fake progress."""

    ordered = []
    for execution in snapshot.executions:
        item = execution.model_dump(mode="json")
        console_excerpt = item.pop("console_excerpt")
        item["console_available"] = bool(console_excerpt)
        item["label"] = _execution_label(
            execution.action_name,
            execution.capability,
        )
        ordered.append(item)
    status_counts: dict[str, int] = {}
    for item in ordered:
        status = str(item["status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "items": ordered,
        "total": snapshot.execution_total,
        "visible": len(ordered),
        "truncated": snapshot.execution_total > len(ordered),
        "status_counts": status_counts,
        "active_id": next(
            (item["id"] for item in ordered if item["status"] == "running"),
            ordered[0]["id"] if ordered else None,
        ),
        "progress_semantics": "state_and_heartbeat",
    }


def _execution_label(action_name: str, capability: str | None) -> str:
    if capability:
        return capability
    if action_name == "run_python":
        return "Python calculation"
    if action_name == "author_and_run_capability":
        return "Authored capability run"
    return "Capability run"


def _control_capabilities(root: Path, *, phase: RunPhase, live: bool) -> dict[str, Any]:
    terminal = (root / "mvp_report.json").is_file()
    launch = (root / "operator_input" / "launch.json").is_file()
    return {
        "can_pause": live and phase is not RunPhase.PAUSED,
        "can_resume": not live and not terminal and launch,
        "can_cancel": live,
        "read_only_reason": None,
    }


def _execution_status(phase: RunPhase, live: bool) -> str:
    if live:
        return "running"
    if phase is RunPhase.PAUSED:
        return "paused"
    if phase in {
        RunPhase.COMPLETED,
        RunPhase.CANCELLED,
        RunPhase.PROVIDER_FAILED,
        RunPhase.BUDGET_EXHAUSTED,
    }:
        return "terminal"
    return "inactive"


def _is_live(root: Path) -> bool:
    identity = load_supervisor_record(root)
    if identity and process_identity_matches(identity):
        return True
    # Direct ``simjecture mvp`` runs do not have a web/TUI supervisor record,
    # but they hold the same verified output lock for their entire lifetime.
    return output_lock_is_held(root)


def _revision(snapshot: Any, *, root: Path, live: bool) -> str:
    pieces = [
        str(snapshot.transcript_cursor.inode),
        str(snapshot.transcript_cursor.offset),
        snapshot.phase.value,
        str(live),
    ]
    for name in ("hypothesis_ledger.json", "mvp_report.json", "operator_input/control.json"):
        try:
            pieces.append(str((root / name).stat().st_mtime_ns))
        except OSError:
            pieces.append("-")
    return hashlib.sha256("|".join(pieces).encode()).hexdigest()[:20]


def _latest_campaign_mtime(root: Path) -> datetime | None:
    newest: int | None = None
    for name in (
        "mvp_report.json",
        "hypothesis_ledger.json",
        "transcript.jsonl",
        "mvp_manifest.json",
        "operator_input/launch.json",
    ):
        try:
            stamp = (root / name).stat().st_mtime_ns
        except OSError:
            continue
        newest = stamp if newest is None else max(newest, stamp)
    if newest is None:
        return None
    return datetime.fromtimestamp(newest / 1_000_000_000, UTC)


def _campaign_display_name(snapshot: Any, root: Path) -> str:
    campaign_id = snapshot.identity.campaign_id or root.name
    if root.name == "record" and not (root / "operator_input" / "launch.json").is_file():
        return root.parent.name.replace("_", " ")
    return str(campaign_id)


def _display_path(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return path.name
    return relative.as_posix() or "."


def _reject_symlink_path(root: Path, requested: Path) -> None:
    current = requested
    while current != root:
        if current.is_symlink():
            raise WebApplicationError("symbolic-link artifacts are not served", status=403)
        if root not in current.parents:
            raise WebApplicationError("invalid artifact path", status=400)
        current = current.parent


def _required_text(payload: dict[str, Any], key: str, *, maximum: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WebApplicationError(f"{key} is required")
    if len(value) > maximum:
        raise WebApplicationError(f"{key} exceeds {maximum} characters")
    return value.strip()


def _optional_text(payload: dict[str, Any], key: str, *, maximum: int) -> str | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise WebApplicationError(f"{key} must be text")
    if len(value) > maximum:
        raise WebApplicationError(f"{key} exceeds {maximum} characters")
    stripped = value.strip()
    return stripped or None


def _bounded_float(
    payload: dict[str, Any], key: str, default: float, minimum: float, maximum: float
) -> float:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WebApplicationError(f"{key} must be a number")
    converted = float(value)
    if not minimum <= converted <= maximum:
        raise WebApplicationError(f"{key} must be between {minimum:g} and {maximum:g}")
    return converted


def _bounded_int(
    payload: dict[str, Any], key: str, default: int, minimum: int, maximum: int
) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise WebApplicationError(f"{key} must be an integer")
    if not minimum <= value <= maximum:
        raise WebApplicationError(f"{key} must be between {minimum} and {maximum}")
    return value


def _default_campaign_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return f"campaign-{timestamp}-{uuid.uuid4().hex[:6]}"


__all__ = [
    "API_SCHEMA_VERSION",
    "ArtifactResource",
    "SimjectureWebApplication",
    "WebApplicationError",
]
