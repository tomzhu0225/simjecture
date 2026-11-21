"""Durable mid-turn direct steering and follow-up queuing for interactive agents.

Supports three Codex-style modes while a turn or swarm worker is active:
- ``steer``: deliver directly at the next model/tool boundary (or immediately via CLI resume)
- ``interrupt``: signal immediate interruption of an in-flight tool/turn and pivot right away
- ``queue``: hold as a sequential follow-up that runs automatically after the current turn
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import signal
import time
import uuid
from pathlib import Path
from typing import Any

from ..mvp_launch import ProcessIdentity, process_identity_matches
from ..research_service import put

STEERING_MODES = frozenset({"steer", "interrupt", "queue"})
MAX_STEER_CHARS = 8000
MAX_TURN_STEERS = 64
MAX_QUEUED_STEERS = 32


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return {} if default is None else default


def _is_alive(record: dict[str, Any] | None) -> bool:
    try:
        return bool(record) and process_identity_matches(ProcessIdentity.model_validate(record))
    except ValueError:
        return False


@contextlib.contextmanager
def _lock_file(directory: Path, name: str = ".steering.lock"):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / name).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _validate_message(message: Any) -> str:
    if not isinstance(message, str) or not message.strip() or len(message) > MAX_STEER_CHARS:
        raise ValueError(f"Provide a steering message between 1 and {MAX_STEER_CHARS} characters")
    return message.strip()


def _validate_mode(mode: Any) -> str:
    value = "steer" if mode is None else str(mode).strip().lower()
    if value not in STEERING_MODES:
        raise ValueError("Steering mode must be steer, interrupt, or queue")
    return value


def _validate_key(request_key: Any) -> str | None:
    if request_key is None or request_key == "":
        return None
    if not isinstance(request_key, str) or len(request_key) > 120:
        raise ValueError("Invalid steering request identifier")
    return request_key


def _emit_turn_event(turn_dir: Path, kind: str, **fields: Any) -> None:
    events_path = turn_dir / "events.jsonl"
    if not events_path.parent.is_dir():
        return
    with events_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"type": kind, "time": time.time(), **fields}) + "\n")


def _signal_interrupt(turn_dir: Path) -> bool:
    """Ask a live builtin agent process to immediately wake up for an interrupt steer."""
    record = _load_json(turn_dir / "process.json")
    if not _is_alive(record):
        return False
    pid = record.get("pid")
    if not isinstance(pid, int) or pid <= 1:
        return False
    if hasattr(signal, "SIGUSR1"):
        with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
            os.kill(pid, signal.SIGUSR1)
            return True
    return False


def _steering_path(turn_dir: Path) -> Path:
    return turn_dir / "steering.json"


def _queue_path(project_dir: Path) -> Path:
    return project_dir / "steering_queue.json"


def list_turn_steering(turn_dir: Path) -> list[dict[str, Any]]:
    data = _load_json(_steering_path(turn_dir), {"items": []})
    items = data.get("items") if isinstance(data, dict) else []
    return list(items) if isinstance(items, list) else []


def list_queued_steering(project_dir: Path) -> list[dict[str, Any]]:
    data = _load_json(_queue_path(project_dir), {"items": []})
    items = data.get("items") if isinstance(data, dict) else []
    return [item for item in items if isinstance(item, dict) and item.get("status") == "queued"]


def project_steering_state(project_dir: Path, active_turn: str | None) -> dict[str, Any]:
    active_items: list[dict[str, Any]] = []
    if active_turn and re.fullmatch(r"[0-9]+", active_turn):
        active_items = list_turn_steering(project_dir / "turns" / active_turn)
    queued = list_queued_steering(project_dir)
    return {
        "active_turn": active_turn,
        "active": active_items,
        "queued": queued,
        "pending_count": sum(1 for item in active_items if item.get("status") == "pending"),
        "queued_count": len(queued),
    }


def submit_steering(
    project_dir: Path,
    turn_name: str,
    message: str,
    *,
    mode: str = "steer",
    request_key: str | None = None,
) -> dict[str, Any]:
    """Record a steering directive for an active turn or append to the project queue."""
    cleaned = _validate_message(message)
    validated_mode = _validate_mode(mode)
    validated_key = _validate_key(request_key)
    if validated_mode == "queue":
        with _lock_file(project_dir):
            data = _load_json(_queue_path(project_dir), {"items": []})
            items = data.get("items", []) if isinstance(data, dict) else []
            for existing in items:
                if validated_key and existing.get("request_key") == validated_key:
                    if existing.get("message") != cleaned:
                        raise ValueError("Steering request identifier already used differently")
                    return existing
            active_queued = [item for item in items if item.get("status") == "queued"]
            if len(active_queued) >= MAX_QUEUED_STEERS:
                raise ValueError(f"At most {MAX_QUEUED_STEERS} queued follow-ups are supported")
            record = {
                "id": "steer_" + uuid.uuid4().hex[:16],
                "turn": turn_name,
                "mode": "queue",
                "message": cleaned,
                "status": "queued",
                "created_at": time.time(),
                "delivered_at": None,
                "applied_at": None,
                "request_key": validated_key,
            }
            items.append(record)
            put(_queue_path(project_dir), {"items": items[-64:]})
            return record

    if not turn_name or not re.fullmatch(r"[0-9]+", turn_name):
        raise ValueError("No active turn to steer")
    turn_dir = project_dir / "turns" / turn_name
    if not turn_dir.is_dir():
        raise ValueError("Active turn directory not found")
    with _lock_file(turn_dir):
        data = _load_json(_steering_path(turn_dir), {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        for existing in items:
            if validated_key and existing.get("request_key") == validated_key:
                if existing.get("message") != cleaned:
                    raise ValueError("Steering request identifier already used differently")
                return existing
        if len(items) >= MAX_TURN_STEERS:
            raise ValueError(f"At most {MAX_TURN_STEERS} direct steers are supported per turn")
        record = {
            "id": "steer_" + uuid.uuid4().hex[:16],
            "turn": turn_name,
            "mode": validated_mode,
            "message": cleaned,
            "status": "pending",
            "created_at": time.time(),
            "delivered_at": None,
            "applied_at": None,
            "request_key": validated_key,
        }
        items.append(record)
        put(_steering_path(turn_dir), {"items": items})
        _emit_turn_event(
            turn_dir,
            "steer",
            id=record["id"],
            mode=validated_mode,
            message=cleaned,
            status="pending",
        )
    if validated_mode == "interrupt":
        _signal_interrupt(turn_dir)
    return record


def submit_worker_steering(
    worker_root: Path,
    message: str,
    *,
    sender: str = "user",
    mode: str = "steer",
) -> dict[str, Any]:
    """Deliver a live steering message to an isolated subagent/swarm worker."""
    cleaned = _validate_message(message)
    validated_mode = "interrupt" if mode == "interrupt" else "steer"
    with _lock_file(worker_root):
        data = _load_json(_steering_path(worker_root), {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        record = {
            "id": "wsteer_" + uuid.uuid4().hex[:14],
            "sender": str(sender)[:80],
            "mode": validated_mode,
            "message": cleaned,
            "status": "pending",
            "created_at": time.time(),
            "applied_at": None,
        }
        items.append(record)
        put(_steering_path(worker_root), {"items": items[-MAX_TURN_STEERS:]})
    if validated_mode == "interrupt":
        _signal_interrupt(worker_root)
    return record


def has_pending_steering(turn_dir: Path | None, *, interrupt_only: bool = False) -> bool:
    if turn_dir is None:
        return False
    path = _steering_path(turn_dir)
    if not path.is_file():
        return False
    data = _load_json(path, {"items": []})
    for item in data.get("items", []) if isinstance(data, dict) else []:
        if item.get("status") != "pending":
            continue
        if interrupt_only and item.get("mode") != "interrupt":
            continue
        return True
    return False


def consume_pending_steering(turn_dir: Path | None) -> list[dict[str, Any]]:
    """Atomically claim all pending steering items for ``turn_dir`` and mark them applied."""
    if turn_dir is None or not _steering_path(turn_dir).is_file():
        return []
    claimed: list[dict[str, Any]] = []
    now = time.time()
    with _lock_file(turn_dir):
        data = _load_json(_steering_path(turn_dir), {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        changed = False
        for item in items:
            if item.get("status") == "pending":
                item["status"] = "applied"
                item["delivered_at"] = now
                item["applied_at"] = now
                claimed.append(dict(item))
                changed = True
        if changed:
            put(_steering_path(turn_dir), {"items": items})
            for record in claimed:
                _emit_turn_event(
                    turn_dir,
                    "steer_applied",
                    id=record["id"],
                    mode=record.get("mode", "steer"),
                    message=record["message"],
                )
    return claimed


def cancel_steering(project_dir: Path, steer_id: str, active_turn: str | None = None) -> dict:
    """Cancel a queued follow-up or pending undelivered steer."""
    if not isinstance(steer_id, str) or not steer_id.strip():
        raise ValueError("Specify a steering item ID")
    with _lock_file(project_dir):
        data = _load_json(_queue_path(project_dir), {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        for item in items:
            if item.get("id") == steer_id and item.get("status") == "queued":
                item["status"] = "cancelled"
                put(_queue_path(project_dir), {"items": items})
                return {"cancelled": steer_id, "message": "Queued follow-up removed"}
    if active_turn and re.fullmatch(r"[0-9]+", active_turn):
        turn_dir = project_dir / "turns" / active_turn
        with _lock_file(turn_dir):
            data = _load_json(_steering_path(turn_dir), {"items": []})
            items = data.get("items", []) if isinstance(data, dict) else []
            for item in items:
                if item.get("id") == steer_id and item.get("status") == "pending":
                    item["status"] = "cancelled"
                    put(_steering_path(turn_dir), {"items": items})
                    return {"cancelled": steer_id, "message": "Pending steer cancelled"}
    raise ValueError("Steering item not found or already applied")


def promote_steering(
    project_dir: Path,
    steer_id: str,
    turn_name: str,
    *,
    mode: str = "steer",
) -> dict[str, Any]:
    """Promote a queued follow-up immediately into active mid-turn steering."""
    validated_mode = "interrupt" if mode == "interrupt" else "steer"
    message = None
    with _lock_file(project_dir):
        data = _load_json(_queue_path(project_dir), {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        for item in items:
            if item.get("id") == steer_id and item.get("status") == "queued":
                item["status"] = "promoted"
                message = item.get("message")
                put(_queue_path(project_dir), {"items": items})
                break
    if not message:
        raise ValueError("Queued follow-up not found")
    return submit_steering(project_dir, turn_name, message, mode=validated_mode)


def pop_next_queued(project_dir: Path) -> dict[str, Any] | None:
    """Atomically dequeue the oldest queued follow-up for automatic dispatch."""
    with _lock_file(project_dir):
        data = _load_json(_queue_path(project_dir), {"items": []})
        items = data.get("items", []) if isinstance(data, dict) else []
        for item in items:
            if item.get("status") == "queued":
                item["status"] = "dispatched"
                item["delivered_at"] = time.time()
                put(_queue_path(project_dir), {"items": items})
                return dict(item)
    return None


def format_steering_injection(records: list[dict[str, Any]]) -> str:
    """Render consumed steering records as a high-priority user directive."""
    urgent = any(item.get("mode") == "interrupt" for item in records)
    header = (
        "URGENT DIRECT USER STEERING (previous step interrupted — pivot immediately and "
        "acknowledge this instruction):"
        if urgent
        else "DIRECT USER STEERING (adapt your current work immediately and respond directly "
        "to this instruction):"
    )
    body = "\n\n".join(
        str(item.get("message", "")).strip() for item in records if item.get("message")
    )
    return f"{header}\n\n{body}"
