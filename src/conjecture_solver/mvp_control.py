"""Operator control channel and run clock for MVP campaigns.

These files live under operator_input/ and are not scientific evidence. The
runner consults them only at action boundaries. They never use SIGSTOP.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from .models import StrictModel

CONTROL_RELATIVE = Path("operator_input") / "control.json"
CLOCK_RELATIVE = Path("operator_input") / "run_clock.json"
PAUSE_STATE_RELATIVE = Path("operator_input") / "pause_state.json"


class ControlCommand(StrEnum):
    NONE = "none"
    PAUSE = "pause"
    CANCEL = "cancel"


class CampaignPaused(Exception):
    """Raised when the runner honors an action-boundary pause.

    No terminal report is written. Repeating the original contract resumes.
    """

    def __init__(self, run_directory: str | Path, *, iterations: int) -> None:
        self.run_directory = Path(run_directory)
        self.iterations = iterations
        super().__init__(
            f"campaign paused at an action boundary after {iterations} iteration(s)"
        )


class OperatorControl(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    command: ControlCommand = ControlCommand.NONE
    requested_at: datetime | None = None
    source: str = "operator"


class RunClock(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    started_at: datetime
    session_started_at: datetime
    last_tick_at: datetime
    accumulated_active_seconds: float = Field(default=0.0, ge=0)
    state: Literal["running", "paused", "finished"] = "running"


class PauseState(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    paused_at: datetime
    iterations: int = Field(ge=0)
    reason: str = "operator requested pause at the next action boundary"


def utc_now() -> datetime:
    return datetime.now(UTC)


def read_control(run_directory: str | Path) -> OperatorControl:
    path = Path(run_directory) / CONTROL_RELATIVE
    payload = _read_json(path)
    if payload is None:
        return OperatorControl()
    try:
        return OperatorControl.model_validate(payload)
    except Exception:
        return OperatorControl()


def write_control(
    run_directory: str | Path,
    command: ControlCommand,
    *,
    source: str = "operator",
    now: datetime | None = None,
) -> OperatorControl:
    control = OperatorControl(
        command=command,
        requested_at=now or utc_now(),
        source=source,
    )
    _write_json(Path(run_directory) / CONTROL_RELATIVE, control.model_dump(mode="json"))
    return control


def clear_control(run_directory: str | Path, *, source: str = "runner") -> None:
    write_control(run_directory, ControlCommand.NONE, source=source)


def poll_control(run_directory: str | Path) -> ControlCommand:
    return read_control(run_directory).command


def read_clock(run_directory: str | Path) -> RunClock | None:
    payload = _read_json(Path(run_directory) / CLOCK_RELATIVE)
    if payload is None:
        return None
    try:
        return RunClock.model_validate(payload)
    except Exception:
        return None


def read_pause_state(run_directory: str | Path) -> PauseState | None:
    payload = _read_json(Path(run_directory) / PAUSE_STATE_RELATIVE)
    if payload is None:
        return None
    try:
        return PauseState.model_validate(payload)
    except Exception:
        return None


def begin_or_resume_clock(
    run_directory: str | Path,
    *,
    now: datetime | None = None,
) -> RunClock:
    """Start or continue the operator clock and clear a prior pause request."""

    moment = now or utc_now()
    existing = read_clock(run_directory)
    if existing is None:
        clock = RunClock(
            started_at=moment,
            session_started_at=moment,
            last_tick_at=moment,
            accumulated_active_seconds=0.0,
            state="running",
        )
    else:
        orphan = 0.0
        if existing.state == "running":
            orphan = max(
                0.0,
                (existing.last_tick_at - existing.session_started_at).total_seconds(),
            )
        clock = RunClock(
            started_at=existing.started_at,
            session_started_at=moment,
            last_tick_at=moment,
            accumulated_active_seconds=existing.accumulated_active_seconds + orphan,
            state="running",
        )
    _write_clock(run_directory, clock)
    clear_control(run_directory, source="runner")
    pause_path = Path(run_directory) / PAUSE_STATE_RELATIVE
    if pause_path.exists():
        pause_path.unlink()
    return clock


def tick_clock(run_directory: str | Path, *, now: datetime | None = None) -> RunClock:
    moment = now or utc_now()
    clock = read_clock(run_directory)
    if clock is None:
        return begin_or_resume_clock(run_directory, now=moment)
    if clock.state != "running":
        return clock
    updated = clock.model_copy(update={"last_tick_at": moment})
    _write_clock(run_directory, updated)
    return updated


def pause_at_boundary(
    run_directory: str | Path,
    *,
    iterations: int,
    now: datetime | None = None,
) -> PauseState:
    moment = now or utc_now()
    clock = read_clock(run_directory)
    if clock is not None and clock.state == "running":
        session = max(0.0, (moment - clock.session_started_at).total_seconds())
        paused_clock = RunClock(
            started_at=clock.started_at,
            session_started_at=clock.session_started_at,
            last_tick_at=moment,
            accumulated_active_seconds=clock.accumulated_active_seconds + session,
            state="paused",
        )
        _write_clock(run_directory, paused_clock)
    state = PauseState(paused_at=moment, iterations=iterations)
    _write_json(Path(run_directory) / PAUSE_STATE_RELATIVE, state.model_dump(mode="json"))
    clear_control(run_directory, source="runner")
    return state


def finalize_clock(run_directory: str | Path, *, now: datetime | None = None) -> RunClock | None:
    moment = now or utc_now()
    clock = read_clock(run_directory)
    if clock is None:
        return None
    extra = 0.0
    if clock.state == "running":
        extra = max(0.0, (moment - clock.session_started_at).total_seconds())
    finished = RunClock(
        started_at=clock.started_at,
        session_started_at=clock.session_started_at,
        last_tick_at=moment,
        accumulated_active_seconds=clock.accumulated_active_seconds + extra,
        state="finished",
    )
    _write_clock(run_directory, finished)
    return finished


def elapsed_from_clock(clock: RunClock, *, now: datetime | None = None) -> float:
    moment = now or utc_now()
    if clock.state == "running":
        session = max(0.0, (moment - clock.session_started_at).total_seconds())
        return clock.accumulated_active_seconds + session
    return clock.accumulated_active_seconds


def parse_usage_payload(usage: Any) -> dict[str, int]:
    """Normalize provider usage objects without treating them as scientific status."""

    empty = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
    }
    if not isinstance(usage, dict):
        return empty
    prompt = _as_int(usage.get("prompt_tokens"))
    if prompt is None:
        prompt = _as_int(usage.get("input_tokens")) or 0
    completion = _as_int(usage.get("completion_tokens"))
    if completion is None:
        completion = _as_int(usage.get("output_tokens")) or 0
    total = _as_int(usage.get("total_tokens"))
    if total is None:
        total = prompt + completion
    cached = 0
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        cached = _as_int(details.get("cached_tokens")) or 0
    cached = (
        _as_int(usage.get("prompt_cache_hit_tokens"))
        or _as_int(usage.get("cached_tokens"))
        or cached
    )
    reasoning = 0
    out_details = usage.get("completion_tokens_details")
    if isinstance(out_details, dict):
        reasoning = _as_int(out_details.get("reasoning_tokens")) or 0
    return {
        "prompt_tokens": max(0, prompt),
        "completion_tokens": max(0, completion),
        "total_tokens": max(0, total),
        "cached_tokens": max(0, cached),
        "reasoning_tokens": max(0, reasoning),
    }


def format_token_counts(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    turns: int,
    missing_turns: int = 0,
    cached_tokens: int = 0,
) -> str:
    parts = [
        f"tokens: {_comma(prompt_tokens)} in / {_comma(completion_tokens)} out / "
        f"{_comma(total_tokens)} total"
    ]
    extras: list[str] = [f"{turns} turn" + ("s" if turns != 1 else "")]
    if missing_turns:
        extras.append(f"{missing_turns} without usage")
    if cached_tokens:
        extras.append(f"{_comma(cached_tokens)} cached")
    parts.append("(" + ", ".join(extras) + ")")
    return " ".join(parts)


def _comma(value: int) -> str:
    return f"{value:,}"


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_clock(run_directory: str | Path, clock: RunClock) -> None:
    _write_json(Path(run_directory) / CLOCK_RELATIVE, clock.model_dump(mode="json"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)
