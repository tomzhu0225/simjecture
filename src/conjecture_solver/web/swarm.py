"""Coordinated multi-agent swarm orchestration with DAG stages and shared message board.

Swarm workers run in isolated ``simulations/<id>/workspace/`` folders with frozen inputs,
validated ``HELPER_RESULT.json`` handoffs, SHA-256 deliverables, live mid-turn steering,
and an append-only shared board (``board.jsonl``). All swarm outputs remain tagged as
``exploration`` until explicitly reviewed through Simjecture's evidence gates.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..mvp_launch import ProcessIdentity, process_identity_matches, read_process_identity
from ..research_helpers import output_path, relative_path
from ..research_service import put
from .jobs import TERMINAL, cancel, list_jobs, read, resolve, selected_inputs, snapshot
from .steering import submit_worker_steering
from .subagents import SubagentTaskSpec, import_subagent_outputs, launch_subagent, subagent_snapshot

SWARM_STRATEGIES = frozenset(
    {"parallel_explore", "divide_and_conquer", "adversarial_verify", "custom"}
)
SWARM_ROLES = frozenset(
    {
        "coordinator",
        "explorer",
        "analyst",
        "solver",
        "verifier",
        "falsifier",
        "critic",
        "synthesizer",
        "worker",
    }
)
MAX_SWARM_MEMBERS = 8
MAX_CONCURRENT_WORKERS = 4
MAX_BOARD_MESSAGE_CHARS = 8000


class SwarmMemberSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=80)
    role: str = Field(default="worker", min_length=2, max_length=40)
    task: str = Field(min_length=8, max_length=8000)
    completion_criteria: str = Field(min_length=8, max_length=4000)
    outputs: list[str] = Field(min_length=1, max_length=16)
    input_files: list[str] | None = None
    depends_on: list[str] = Field(default_factory=list, max_length=8)
    timeout_seconds: float = Field(default=600, ge=5, le=7200, allow_inf_nan=False)
    backend: str | None = Field(default=None, max_length=30)
    model: str | None = Field(default=None, max_length=200)
    reasoning_effort: str | None = Field(default=None, max_length=20)


class SwarmSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(default="Research swarm", min_length=2, max_length=140)
    objective: str = Field(default="", max_length=8000)
    strategy: str = Field(default="parallel_explore", max_length=40)
    members: list[SwarmMemberSpec] = Field(min_length=1, max_length=MAX_SWARM_MEMBERS)
    max_concurrent: int = Field(default=MAX_CONCURRENT_WORKERS, ge=1, le=MAX_CONCURRENT_WORKERS)
    wait: bool = False


def _is_alive(record: dict[str, Any] | None) -> bool:
    try:
        return bool(record) and process_identity_matches(ProcessIdentity.model_validate(record))
    except ValueError:
        return False


def _slug(value: str, fallback: str = "swarm") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:48]
    return cleaned or fallback


def _validate_swarm_spec(payload: dict[str, Any]) -> tuple[SwarmSpec, dict[str, int]]:
    spec = SwarmSpec.model_validate(payload)
    if spec.strategy not in SWARM_STRATEGIES:
        raise ValueError(f"Unsupported swarm strategy: {spec.strategy}")
    names: list[str] = []
    seen_lower: set[str] = set()
    for member in spec.members:
        key = member.name.lower()
        if key in seen_lower:
            raise ValueError(f"Duplicate swarm member name: {member.name}")
        seen_lower.add(key)
        names.append(member.name)
        cleaned_outputs = [str(output_path(item)) for item in member.outputs]
        if len(set(cleaned_outputs)) != len(cleaned_outputs):
            raise ValueError(f"Member {member.name!r} outputs must be distinct relative paths")
        member.outputs = cleaned_outputs
    name_set = set(names)
    indegree = {name: 0 for name in names}
    children: dict[str, list[str]] = {name: [] for name in names}
    for member in spec.members:
        if len(set(member.depends_on)) != len(member.depends_on):
            raise ValueError(f"Member {member.name!r} lists duplicate dependencies")
        for dep in member.depends_on:
            if dep == member.name:
                raise ValueError(f"Member {member.name!r} cannot depend on itself")
            if dep not in name_set:
                raise ValueError(f"Member {member.name!r} depends on unknown member {dep!r}")
            children[dep].append(member.name)
            indegree[member.name] += 1
    queue = deque(name for name, deg in indegree.items() if deg == 0)
    stages: dict[str, int] = {name: 0 for name in queue}
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for nxt in children[current]:
            stages[nxt] = max(stages.get(nxt, 0), stages[current] + 1)
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if visited != len(names):
        raise ValueError("Swarm member dependencies contain a cycle")
    return spec, stages


def _swarm_root(project_dir: Path, swarm_id: str) -> Path:
    if not re.fullmatch(r"swarm-[a-z0-9-]{1,100}", swarm_id or ""):
        raise ValueError("Unknown swarm")
    root = project_dir / "swarms" / swarm_id
    if root.is_symlink() or not (root / "swarm.json").is_file():
        raise ValueError("Unknown swarm")
    return root


@contextlib.contextmanager
def _swarm_lock(swarm_dir: Path):
    swarm_dir.mkdir(parents=True, exist_ok=True)
    with (swarm_dir / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def read_board(swarm_dir: Path, *, limit: int = 120) -> list[dict[str, Any]]:
    path = swarm_dir / "board.jsonl"
    if not path.is_file() or path.is_symlink():
        return []
    messages: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    messages.append(item)
            except ValueError:
                continue
    return messages[-limit:]


def append_board(
    swarm_dir: Path,
    *,
    sender: str,
    sender_role: str,
    content: str,
    recipient: str = "all",
    kind: str = "finding",
    attachments: list[str] | None = None,
) -> dict[str, Any]:
    text_body = str(content or "").strip()
    if not text_body or len(text_body) > MAX_BOARD_MESSAGE_CHARS:
        raise ValueError(f"Board message must be 1 to {MAX_BOARD_MESSAGE_CHARS} characters")
    entry = {
        "id": "msg_" + uuid.uuid4().hex[:14],
        "timestamp": time.time(),
        "sender": str(sender)[:80],
        "sender_role": str(sender_role)[:40],
        "recipient": str(recipient or "all")[:80],
        "kind": str(kind or "finding")[:32],
        "content": text_body,
        "attachments": [str(a)[:240] for a in (attachments or [])[:16]],
    }
    with _swarm_lock(swarm_dir), (swarm_dir / "board.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _collect_upstream_artifacts(
    project_dir: Path, member_map: dict[str, dict[str, Any]], depends_on: list[str]
) -> list[tuple[Path, Path]]:
    """Collect validated upstream deliverables into ``inputs/upstream/<member>/...``."""
    staged: list[tuple[Path, Path]] = []
    for dep_name in depends_on:
        dep = member_map.get(dep_name)
        if not dep or not dep.get("job_id"):
            continue
        dep_root = resolve(project_dir, dep["job_id"])
        req = read(dep_root / "request.json")
        handoff = read(dep_root / "subagent_result.json")
        if not req or not handoff:
            continue
        work = Path(req["work_directory"]).resolve()
        dep_slug = _slug(dep_name, "upstream")
        for rel_name in handoff.get("artifacts", {}):
            source = work / relative_path(rel_name)
            if source.is_symlink() or not source.resolve().is_relative_to(work):
                continue
            if source.is_file():
                staged.append((source, Path("upstream") / dep_slug / relative_path(rel_name)))
    return staged


def _member_task_spec(
    member: dict[str, Any],
    swarm: dict[str, Any],
    *,
    upstream_summary: str = "",
) -> SubagentTaskSpec:
    role = member.get("role", "worker")
    task_text = member["task"]
    header_parts = [f"Swarm: {swarm['title']} (strategy: {swarm['strategy']}, role: {role})."]
    if swarm.get("objective"):
        header_parts.append(f"Shared objective: {swarm['objective']}")
    if upstream_summary:
        header_parts.append(f"Upstream handoffs (files in inputs/upstream/):\n{upstream_summary}")
    full_task = "\n".join(header_parts) + "\n\nAssigned task:\n" + task_text
    return SubagentTaskSpec(
        name=member["name"],
        task=full_task[:8000],
        completion_criteria=member["completion_criteria"],
        outputs=member["outputs"],
        input_files=member.get("input_files"),
        timeout_seconds=member.get("timeout_seconds", 600),
    )


def _member_connection(workspace, project_dir: Path, member: dict[str, Any], swarm_id: str) -> Path:
    project = read(project_dir / "project.json")
    override = dict(project)
    if member.get("backend") or member.get("model") or member.get("reasoning_effort"):
        base = dict(project.get("agent") or workspace.default_agent())
        if member.get("backend"):
            base["backend"] = member["backend"]
        if member.get("model"):
            base["model"] = member["model"]
        if member.get("reasoning_effort") is not None:
            base["reasoning_effort"] = member["reasoning_effort"]
        override["agent"] = base
    config = workspace.project_connection(override)
    conn = (
        workspace.root
        / "turn-connections"
        / f"{project_dir.name}-{swarm_id}-{uuid.uuid4().hex[:10]}.json"
    )
    from .workspace import private_json

    private_json(conn, config)
    return conn


def _launch_member_job(
    workspace,
    project_dir: Path,
    swarm_dir: Path,
    swarm: dict[str, Any],
    member: dict[str, Any],
    *,
    upstream_artifacts: list[tuple[Path, Path]] | None = None,
    upstream_summary: str = "",
) -> dict[str, Any]:
    spec = _member_task_spec(member, swarm, upstream_summary=upstream_summary)
    selected = selected_inputs(project_dir, spec.input_files)
    conn_path = _member_connection(workspace, project_dir, member, swarm["id"])
    try:
        job = launch_subagent(
            project_dir,
            spec,
            conn_path,
            selected=selected,
            extra_metadata={
                "swarm_id": swarm["id"],
                "swarm_dir": str(swarm_dir),
                "swarm_role": member.get("role", "worker"),
                "swarm_member": member["name"],
                "swarm_stage": member.get("stage", 0),
                "depends_on": member.get("depends_on", []),
                "model": member.get("model") or "",
                "backend": member.get("backend") or "",
            },
            upstream_artifacts=upstream_artifacts,
        )
    except Exception:
        conn_path.unlink(missing_ok=True)
        raise
    return job


def launch_swarm(workspace, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Validate, persist, and launch a coordinated multi-agent swarm with DAG controller."""
    spec, stages = _validate_swarm_spec(payload)
    project_dir = workspace.directory(project_id).resolve()
    project = read(project_dir / "project.json")
    # Pre-validate project & per-member inputs and connections before mutating disk.
    for member in spec.members:
        selected_inputs(project_dir, member.input_files)
        override = dict(project)
        if member.backend or member.model or member.reasoning_effort is not None:
            base = dict(project.get("agent") or workspace.default_agent())
            if member.backend:
                base["backend"] = member.backend
            if member.model:
                base["model"] = member.model
            if member.reasoning_effort is not None:
                base["reasoning_effort"] = member.reasoning_effort
            override["agent"] = base
        workspace.project_connection(override)

    swarms_root = project_dir / "swarms"
    swarms_root.mkdir(exist_ok=True)
    slug = _slug(spec.title, "swarm")
    with (swarms_root / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        number = len(list(swarms_root.glob("*/swarm.json"))) + 1
        swarm_id = f"swarm-{number:03d}-{slug}"
        while (swarms_root / swarm_id).exists():
            number += 1
            swarm_id = f"swarm-{number:03d}-{slug}"
        swarm_dir = swarms_root / swarm_id
        swarm_dir.mkdir(parents=True)
        members = [
            {
                "name": m.name,
                "slug": _slug(m.name, f"member-{idx + 1}"),
                "role": m.role,
                "task": m.task,
                "completion_criteria": m.completion_criteria,
                "outputs": m.outputs,
                "input_files": m.input_files,
                "depends_on": m.depends_on,
                "stage": stages[m.name],
                "timeout_seconds": m.timeout_seconds,
                "backend": m.backend,
                "model": m.model,
                "reasoning_effort": m.reasoning_effort,
                "job_id": None,
                "status": "waiting_deps" if m.depends_on else "queued",
                "history": [],
            }
            for idx, m in enumerate(spec.members)
        ]
        swarm_record = {
            "id": swarm_id,
            "project_id": project_id,
            "workspace_root": str(workspace.root),
            "title": spec.title,
            "objective": spec.objective,
            "strategy": spec.strategy,
            "max_concurrent": spec.max_concurrent,
            "status": "running",
            "created_at": time.time(),
            "updated_at": time.time(),
            "finished_at": None,
            "source_turn": project.get("active_turn"),
            "scientific_status": "exploration",
            "members": members,
        }
        put(swarm_dir / "swarm.json", swarm_record)
    brief_lines = [f"Swarm '{spec.title}' launched ({spec.strategy}, {len(members)} agents)."]
    if spec.objective:
        brief_lines.append(f"Objective: {spec.objective}")
    for m in members:
        deps = f" [after {', '.join(m['depends_on'])}]" if m["depends_on"] else ""
        brief_lines.append(f"- @{m['name']} ({m['role']}){deps}: {m['task'].splitlines()[0][:140]}")
    append_board(
        swarm_dir,
        sender="Coordinator",
        sender_role="coordinator",
        recipient="all",
        kind="brief",
        content="\n".join(brief_lines),
    )
    _start_controller(project_dir, swarm_dir)
    if spec.wait:
        deadline = time.monotonic() + sum(m["timeout_seconds"] for m in members) + 30
        while time.monotonic() < deadline:
            snap = swarm_snapshot(project_dir, swarm_id, include_board=False, include_files=False)
            terminal_swarm = {"completed", "partial", "failed", "cancelled"}
            if snap["status"] in terminal_swarm and not snap["live"]:
                break
            time.sleep(0.25)
    return swarm_snapshot(project_dir, swarm_id, include_board=True, include_files=True)


def _start_controller(project_dir: Path, swarm_dir: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    cmd = [sys.executable, "-m", "conjecture_solver.web.swarm", "--run", str(swarm_dir)]
    with (swarm_dir / "controller.log").open("ab") as log:
        process = subprocess.Popen(
            cmd,
            env=env,
            cwd=project_dir,
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    identity = read_process_identity(process.pid, cmd, run_directory=swarm_dir)
    if identity:
        put(swarm_dir / "process.json", identity.model_dump(mode="json"))
    threading.Thread(target=process.wait, daemon=True).start()


def _refresh_member_state(
    project_dir: Path, member: dict[str, Any], *, include_files: bool = True
) -> dict[str, Any]:
    job_id = member.get("job_id")
    enriched = dict(member)
    if not job_id:
        enriched["live"] = False
        enriched["elapsed_seconds"] = 0
        enriched["deliverables"] = []
        return enriched
    try:
        job = snapshot(project_dir, job_id, include_files=include_files, summary=not include_files)
    except ValueError:
        enriched["live"] = False
        return enriched
    enriched["status"] = job["status"]
    enriched["live"] = bool(job.get("live"))
    enriched["elapsed_seconds"] = job.get("elapsed_seconds", 0)
    enriched["created_at"] = job.get("created_at")
    enriched["error"] = job.get("error")
    if include_files:
        enriched["output"] = job.get("output", "")
        enriched["files"] = job.get("files", [])
        handoff = job.get("subagent_result") or {}
        enriched["handoff"] = handoff
        enriched["deliverables"] = [
            {"name": name, "bytes": info.get("bytes", 0), "sha256": info.get("sha256", "")}
            for name, info in (handoff.get("artifacts") or {}).items()
        ]
    else:
        job_root = resolve(project_dir, job_id)
        handoff = read(job_root / "subagent_result.json")
        if handoff:
            enriched["handoff"] = {
                "status": handoff.get("status"),
                "summary": handoff.get("summary", ""),
                "checks": handoff.get("checks", []),
                "unresolved": handoff.get("unresolved", []),
            }
            enriched["deliverables"] = [
                {"name": name, "bytes": info.get("bytes", 0), "sha256": info.get("sha256", "")}
                for name, info in (handoff.get("artifacts") or {}).items()
            ]
        else:
            enriched["deliverables"] = []
    return enriched


def _aggregate_status(members: list[dict[str, Any]], controller_live: bool, saved: str) -> str:
    statuses = [m.get("status", "queued") for m in members]
    if any(m.get("live") for m in members) or controller_live:
        return "running"
    if saved == "cancelled" or (statuses and all(s == "cancelled" for s in statuses)):
        return "cancelled"
    if statuses and all(s == "succeeded" for s in statuses):
        return "completed"
    if any(s == "succeeded" for s in statuses) and any(
        s in {"failed", "cancelled", "timed_out", "interrupted", "skipped"} for s in statuses
    ):
        return "partial"
    if any(s in {"failed", "timed_out", "interrupted"} for s in statuses):
        return "failed"
    return saved


def swarm_snapshot(
    project_dir: Path,
    swarm_id: str,
    *,
    include_board: bool = True,
    include_files: bool = True,
) -> dict[str, Any]:
    swarm_dir = _swarm_root(project_dir, swarm_id)
    record = read(swarm_dir / "swarm.json")
    controller_live = _is_alive(read(swarm_dir / "process.json"))
    members = [
        _refresh_member_state(project_dir, m, include_files=include_files)
        for m in record.get("members", [])
    ]
    status = _aggregate_status(members, controller_live, record.get("status", "running"))
    counts = {
        "total": len(members),
        "active": sum(1 for m in members if m.get("status") in {"queued", "running"}),
        "waiting": sum(1 for m in members if m.get("status") == "waiting_deps"),
        "succeeded": sum(1 for m in members if m.get("status") == "succeeded"),
        "failed": sum(
            1 for m in members if m.get("status") in {"failed", "timed_out", "interrupted"}
        ),
        "cancelled": sum(1 for m in members if m.get("status") in {"cancelled", "skipped"}),
    }
    now = time.time()
    finished_at = record.get("finished_at")
    result = {
        "id": record["id"],
        "title": record.get("title", "Research swarm"),
        "objective": record.get("objective", ""),
        "strategy": record.get("strategy", "parallel_explore"),
        "status": status,
        "live": controller_live or any(m.get("live") for m in members),
        "created_at": record.get("created_at", now),
        "finished_at": finished_at,
        "elapsed_seconds": max(
            0, (finished_at or now) - record.get("created_at", now)
        ),
        "source_turn": record.get("source_turn"),
        "scientific_status": "exploration",
        "counts": counts,
        "members": members,
    }
    if include_board:
        result["board"] = read_board(swarm_dir)
    return result


def list_swarms(project_dir: Path) -> list[dict[str, Any]]:
    """List durable swarms plus standalone legacy subagent batches for the Swarm GUI."""
    swarms: list[dict[str, Any]] = []
    owned_jobs: set[str] = set()
    swarms_root = project_dir / "swarms"
    if swarms_root.is_dir():
        for path in sorted(swarms_root.glob("*/swarm.json")):
            if path.is_symlink() or path.parent.is_symlink():
                continue
            try:
                snap = swarm_snapshot(
                    project_dir, path.parent.name, include_board=False, include_files=False
                )
            except (ValueError, OSError):
                continue
            for member in snap.get("members", []):
                if member.get("job_id"):
                    owned_jobs.add(member["job_id"])
            swarms.append(snap)
    # Surface legacy run_subagents batches gracefully as read-only swarm summaries.
    standalone = [
        job
        for job in list_jobs(project_dir, summary=True)
        if job.get("subagent") and job["id"] not in owned_jobs
    ]
    if standalone:
        by_turn: dict[str, list[dict[str, Any]]] = {}
        for job in standalone:
            by_turn.setdefault(str(job.get("source_turn") or "batch"), []).append(job)
        for turn_key, jobs in by_turn.items():
            members = [
                {
                    "name": j["name"],
                    "slug": _slug(j["name"], "worker"),
                    "role": "worker",
                    "stage": 0,
                    "depends_on": [],
                    "job_id": j["id"],
                    "status": j["status"],
                    "live": bool(j.get("live")),
                    "elapsed_seconds": j.get("elapsed_seconds", 0),
                    "deliverables": [],
                }
                for j in jobs
            ]
            live = any(m["live"] for m in members)
            swarms.append(
                {
                    "id": f"legacy-{turn_key}",
                    "legacy": True,
                    "title": f"Subagents ({len(members)})",
                    "objective": "",
                    "strategy": "parallel_explore",
                    "status": _aggregate_status(members, live, "running" if live else "completed"),
                    "live": live,
                    "created_at": min((j.get("created_at", 0) for j in jobs), default=0),
                    "elapsed_seconds": max((j.get("elapsed_seconds", 0) for j in jobs), default=0),
                    "counts": {
                        "total": len(members),
                        "active": sum(
                            1 for m in members if m["status"] in {"queued", "running"}
                        ),
                        "waiting": 0,
                        "succeeded": sum(1 for m in members if m["status"] == "succeeded"),
                        "failed": sum(
                            1
                            for m in members
                            if m["status"] in {"failed", "timed_out", "interrupted"}
                        ),
                        "cancelled": sum(1 for m in members if m["status"] == "cancelled"),
                    },
                    "members": members,
                }
            )
    swarms.sort(key=lambda item: item.get("created_at", 0), reverse=True)
    return swarms


def post_board_message(
    project_dir: Path,
    swarm_id: str,
    *,
    sender: str,
    sender_role: str,
    content: str,
    recipient: str = "all",
    kind: str = "steering",
    mode: str = "steer",
    steer_live: bool = True,
) -> dict[str, Any]:
    """Post a message to the swarm board and steer matching live workers immediately."""
    swarm_dir = _swarm_root(project_dir, swarm_id)
    record = read(swarm_dir / "swarm.json")
    entry = append_board(
        swarm_dir,
        sender=sender,
        sender_role=sender_role,
        recipient=recipient,
        kind=kind,
        content=content,
    )
    steered: list[str] = []
    if steer_live and kind in {"steering", "message", "brief"}:
        target = (recipient or "all").strip()
        for member in record.get("members", []):
            job_id = member.get("job_id")
            if not job_id:
                continue
            if target != "all" and target.lower() not in {
                member["name"].lower(),
                member.get("slug", "").lower(),
                job_id.lower(),
            }:
                continue
            try:
                job = snapshot(project_dir, job_id, summary=True)
            except ValueError:
                continue
            if job.get("live"):
                submit_worker_steering(
                    resolve(project_dir, job_id),
                    f"[{sender} -> @{target}]: {content}",
                    sender=sender,
                    mode=mode,
                )
                steered.append(member["name"])
    return {"message": entry, "steered_workers": steered}


def control_swarm(
    workspace,
    project_id: str,
    swarm_id: str,
    action: str,
    *,
    worker_id: str | None = None,
    worker_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Perform lifecycle actions on a swarm or individual worker."""
    project_dir = workspace.directory(project_id).resolve()
    swarm_dir = _swarm_root(project_dir, swarm_id)
    if action == "stop_swarm":
        put(swarm_dir / "control.json", {"command": "cancel", "at": time.time()})
        record = read(swarm_dir / "swarm.json")
        for member in record.get("members", []):
            if member.get("job_id"):
                with contextlib.suppress(ValueError, OSError):
                    cancel(project_dir, member["job_id"])
        append_board(
            swarm_dir,
            sender="Operator",
            sender_role="coordinator",
            recipient="all",
            kind="alert",
            content="Swarm stop requested; cancelling active workers.",
        )
        return swarm_snapshot(project_dir, swarm_id)

    if action == "stop_worker":
        if not worker_id:
            raise ValueError("Choose a swarm worker to stop")
        record = read(swarm_dir / "swarm.json")
        member = next(
            (m for m in record.get("members", []) if worker_id in {m.get("job_id"), m["name"]}),
            None,
        )
        if not member or not member.get("job_id"):
            raise ValueError("Swarm worker is not currently running")
        cancel(project_dir, member["job_id"])
        append_board(
            swarm_dir,
            sender="Operator",
            sender_role="coordinator",
            recipient=member["name"],
            kind="alert",
            content=f"Stop requested for @{member['name']}.",
        )
        return swarm_snapshot(project_dir, swarm_id)

    if action == "retry_worker":
        if not worker_id:
            raise ValueError("Choose a swarm worker to retry")
        with _swarm_lock(swarm_dir):
            record = read(swarm_dir / "swarm.json")
            member = next(
                (
                    m
                    for m in record.get("members", [])
                    if worker_id in {m.get("job_id"), m["name"]}
                ),
                None,
            )
            if not member:
                raise ValueError("Swarm worker not found")
            if member.get("job_id"):
                current = snapshot(project_dir, member["job_id"], summary=True)
                if current.get("live"):
                    raise ValueError("Stop the running worker before retrying it")
                member.setdefault("history", []).append(member["job_id"])
            member_map = {m["name"]: m for m in record.get("members", [])}
            upstream = _collect_upstream_artifacts(project_dir, member_map, member["depends_on"])
            job = _launch_member_job(
                workspace, project_dir, swarm_dir, record, member, upstream_artifacts=upstream
            )
            member["job_id"] = job["id"]
            member["status"] = job["status"]
            record["status"] = "running"
            record["finished_at"] = None
            record["updated_at"] = time.time()
            put(swarm_dir / "swarm.json", record)
            if not _is_alive(read(swarm_dir / "process.json")):
                (swarm_dir / "control.json").unlink(missing_ok=True)
                _start_controller(project_dir, swarm_dir)
        append_board(
            swarm_dir,
            sender="Operator",
            sender_role="coordinator",
            recipient=member["name"],
            kind="brief",
            content=f"Retried @{member['name']} as {job['id']}.",
        )
        return swarm_snapshot(project_dir, swarm_id)

    if action == "add_worker":
        if not isinstance(worker_spec, dict):
            raise ValueError("Provide a worker specification")
        with _swarm_lock(swarm_dir):
            record = read(swarm_dir / "swarm.json")
            members = record.get("members", [])
            if len(members) >= MAX_SWARM_MEMBERS:
                raise ValueError(f"A swarm supports at most {MAX_SWARM_MEMBERS} agents")
            member_spec = SwarmMemberSpec.model_validate(worker_spec)
            member_spec.outputs = [str(output_path(o)) for o in member_spec.outputs]
            if any(m["name"].lower() == member_spec.name.lower() for m in members):
                raise ValueError(f"Duplicate swarm member name: {member_spec.name}")
            known_names = {m["name"]: m for m in members}
            for dep in member_spec.depends_on:
                if dep not in known_names:
                    raise ValueError(f"Unknown upstream member: {dep}")
            stage = max(
                (known_names[d].get("stage", 0) + 1 for d in member_spec.depends_on), default=0
            )
            selected_inputs(project_dir, member_spec.input_files)
            entry = {
                "name": member_spec.name,
                "slug": _slug(member_spec.name, f"member-{len(members) + 1}"),
                "role": member_spec.role,
                "task": member_spec.task,
                "completion_criteria": member_spec.completion_criteria,
                "outputs": member_spec.outputs,
                "input_files": member_spec.input_files,
                "depends_on": member_spec.depends_on,
                "stage": stage,
                "timeout_seconds": member_spec.timeout_seconds,
                "backend": member_spec.backend,
                "model": member_spec.model,
                "reasoning_effort": member_spec.reasoning_effort,
                "job_id": None,
                "status": "waiting_deps" if member_spec.depends_on else "queued",
                "history": [],
            }
            members.append(entry)
            record["status"] = "running"
            record["finished_at"] = None
            record["updated_at"] = time.time()
            put(swarm_dir / "swarm.json", record)
            if not _is_alive(read(swarm_dir / "process.json")):
                (swarm_dir / "control.json").unlink(missing_ok=True)
                _start_controller(project_dir, swarm_dir)
        append_board(
            swarm_dir,
            sender="Coordinator",
            sender_role="coordinator",
            recipient=member_spec.name,
            kind="brief",
            content=f"Added @{member_spec.name} ({member_spec.role}): {member_spec.task[:200]}",
        )
        return swarm_snapshot(project_dir, swarm_id)

    raise ValueError("Unsupported swarm control action")


def import_swarm_deliverables(
    project_dir: Path,
    swarm_id: str,
    worker_id: str,
    files: list[str] | None = None,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Import validated SHA-256 deliverables from a swarm worker into conversation files."""
    if not swarm_id.startswith("legacy-"):
        swarm_dir = _swarm_root(project_dir, swarm_id)
        record = read(swarm_dir / "swarm.json")
        member = next(
            (m for m in record.get("members", []) if worker_id in {m.get("job_id"), m["name"]}),
            None,
        )
        if not member or not member.get("job_id"):
            raise ValueError("Choose a swarm worker with a completed run")
        job_id = member["job_id"]
        receipts = import_subagent_outputs(project_dir, job_id, files, overwrite=overwrite)
        if receipts:
            names = ", ".join(r["artifact"] for r in receipts)
            append_board(
                swarm_dir,
                sender="Operator",
                sender_role="coordinator",
                recipient=member["name"],
                kind="handoff",
                content=f"Imported validated deliverables from @{member['name']}: {names}",
                attachments=[r["artifact"] for r in receipts],
            )
        return {
            "imported": receipts,
            "worker": subagent_snapshot(project_dir, job_id),
            "swarm": swarm_snapshot(project_dir, swarm_id),
        }
    receipts = import_subagent_outputs(project_dir, worker_id, files, overwrite=overwrite)
    return {"imported": receipts, "worker": subagent_snapshot(project_dir, worker_id)}


def _upstream_handoff_summary(
    project_dir: Path, member_map: dict[str, dict[str, Any]], depends_on: list[str]
) -> str:
    lines: list[str] = []
    for dep_name in depends_on:
        dep = member_map.get(dep_name)
        if not dep or not dep.get("job_id"):
            continue
        handoff = read(resolve(project_dir, dep["job_id"]) / "subagent_result.json")
        summary = handoff.get("summary") or f"Status: {dep.get('status')}"
        artifacts = list((handoff.get("artifacts") or {}).keys())
        lines.append(f"- {dep_name} ({dep.get('role', 'worker')}): {summary} | files={artifacts}")
    return "\n".join(lines)


def run_swarm_controller(swarm_dir: Path) -> int:
    """Durable DAG scheduler for one multi-agent swarm."""
    swarm_dir = Path(swarm_dir).resolve()
    identity = read_process_identity(os.getpid(), run_directory=swarm_dir)
    if identity:
        put(swarm_dir / "process.json", identity.model_dump(mode="json"))
    stopped = False

    def handle_stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    announced_terminal: set[str] = set()
    from .workspace import Workspace

    while True:
        record = read(swarm_dir / "swarm.json")
        if not record:
            return 1
        project_dir = swarm_dir.parent.parent
        workspace = Workspace(record["workspace_root"])
        cancelled = stopped or read(swarm_dir / "control.json").get("command") == "cancel"
        members = record.get("members", [])
        member_map = {m["name"]: m for m in members}
        changed = False
        active_live = 0

        for m in members:
            job_id = m.get("job_id")
            if not job_id:
                continue
            try:
                job = snapshot(project_dir, job_id, summary=True)
            except ValueError:
                continue
            if job["status"] != m.get("status"):
                m["status"] = job["status"]
                changed = True
            if job.get("live"):
                active_live += 1
                if cancelled:
                    with contextlib.suppress(ValueError, OSError):
                        cancel(project_dir, job_id)
            elif job["status"] in TERMINAL and job_id not in announced_terminal:
                announced_terminal.add(job_id)
                handoff = read(resolve(project_dir, job_id) / "subagent_result.json")
                summary = handoff.get("summary") or f"Finished with status: {job['status']}"
                artifacts = list((handoff.get("artifacts") or {}).keys())
                append_board(
                    swarm_dir,
                    sender=m["name"],
                    sender_role=m.get("role", "worker"),
                    recipient="all",
                    kind="handoff" if job["status"] == "succeeded" else "alert",
                    content=summary,
                    attachments=artifacts,
                )

        if cancelled:
            for m in members:
                if not m.get("job_id") and m.get("status") in {"queued", "waiting_deps"}:
                    m["status"] = "cancelled"
                    changed = True
        else:
            max_conc = int(record.get("max_concurrent") or MAX_CONCURRENT_WORKERS)
            for m in members:
                if m.get("job_id") or m.get("status") not in {"queued", "waiting_deps"}:
                    continue
                deps = [member_map[d] for d in m.get("depends_on", []) if d in member_map]
                failed_states = {"failed", "cancelled", "timed_out", "interrupted", "skipped"}
                if any(d.get("status") in failed_states for d in deps):
                    m["status"] = "skipped"
                    changed = True
                    append_board(
                        swarm_dir,
                        sender="Coordinator",
                        sender_role="coordinator",
                        recipient=m["name"],
                        kind="alert",
                        content=(
                            f"Skipped @{m['name']} because an upstream dependency did not succeed."
                        ),
                    )
                    continue
                deps_ready = all(d.get("status") == "succeeded" and d.get("job_id") for d in deps)
                if not deps_ready:
                    continue
                if active_live >= max_conc:
                    continue
                upstream = _collect_upstream_artifacts(project_dir, member_map, m["depends_on"])
                up_summary = _upstream_handoff_summary(project_dir, member_map, m["depends_on"])
                try:
                    job = _launch_member_job(
                        workspace,
                        project_dir,
                        swarm_dir,
                        record,
                        m,
                        upstream_artifacts=upstream,
                        upstream_summary=up_summary,
                    )
                    m["job_id"] = job["id"]
                    m["status"] = job["status"]
                    active_live += 1
                    changed = True
                except Exception as error:
                    m["status"] = "failed"
                    m["error"] = str(error)
                    changed = True
                    append_board(
                        swarm_dir,
                        sender="Coordinator",
                        sender_role="coordinator",
                        recipient=m["name"],
                        kind="alert",
                        content=f"Could not launch @{m['name']}: {error}",
                    )

        pending = any(m.get("status") in {"queued", "waiting_deps", "running"} for m in members)
        if changed:
            with _swarm_lock(swarm_dir):
                fresh = read(swarm_dir / "swarm.json")
                by_name = {m["name"]: m for m in members}
                merged = [by_name.get(m["name"], m) for m in fresh.get("members", [])]
                fresh["members"] = merged
                fresh["updated_at"] = time.time()
                put(swarm_dir / "swarm.json", fresh)
                pending = any(
                    m.get("status") in {"queued", "waiting_deps", "running"} for m in merged
                )
        if not pending and active_live == 0:
            with _swarm_lock(swarm_dir):
                fresh = read(swarm_dir / "swarm.json")
                merged = fresh.get("members", members)
                if any(m.get("status") in {"queued", "waiting_deps", "running"} for m in merged):
                    continue
                final_status = _aggregate_status(
                    merged, False, "cancelled" if cancelled else "completed"
                )
                fresh["status"] = final_status
                fresh["finished_at"] = time.time()
                fresh["updated_at"] = time.time()
                put(swarm_dir / "swarm.json", fresh)
                proc_path = swarm_dir / "process.json"
                if read(proc_path).get("pid") == os.getpid():
                    proc_path.unlink(missing_ok=True)
            return 0 if final_status == "completed" else 1
        time.sleep(0.25)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    return run_swarm_controller(args.run)


if __name__ == "__main__":
    raise SystemExit(main())
