"""Durable DeepSeek Harness process adapter for a Simjecture campaign.

The browser and supervisor continue to launch a small, inspectable Python
process.  That process verifies the stored launch contract, supplies only path
and budget metadata to DSH, and keeps the DSH session log inside the campaign.
Scientific authority remains in :mod:`conjecture_solver.campaign_kernel`.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .mvp_control import (
    begin_or_resume_clock,
    elapsed_from_clock,
    finalize_clock,
    pause_at_boundary,
)
from .mvp_launch import DSH_SESSION_ID_PATTERN, ResumeError, load_launch_request

DSH_PROFILE = "simjecture"
DSH_SESSION_DIRECTORY = Path("operator_input") / "dsh_sessions"
DSH_ACTIVITY_FILE = Path("operator_input") / "dsh_activity.jsonl"
DSH_STATE_FILE = Path("operator_input") / "dsh_state.json"
DSH_CONTROL_FILE = Path("operator_input") / "control.json"

INITIAL_TASK = (
    "Operate the durable Simjecture campaign exposed through the typed "
    "mcp__simjecture__ tools. Begin by reading snapshot, then autonomously "
    "commission the available methods, test the root hypothesis, register and "
    "evaluate falsifiable subhypotheses, and preserve every scientific conclusion "
    "through prospective evidence contracts. Continue until the current evidence "
    "supports a defensible stopping point or a durable budget prevents further work."
)
RESUME_TASK = (
    "Resume the same durable Simjecture campaign. Before any mutation, call "
    "mcp__simjecture__snapshot and reconcile its authoritative claims, jobs, "
    "receipts, and remaining budgets with this DSH session. Then continue the "
    "autonomous falsification loop until a defensible stopping point or durable "
    "budget boundary is reached."
)


class DshEngineError(RuntimeError):
    """The configured DSH runtime cannot safely start this campaign."""


class _TerminationRequested(BaseException):
    """Turn a process SIGTERM into a recoverable campaign boundary."""

    def __init__(self, signum: int) -> None:
        super().__init__(signum)
        self.signum = signum


@contextmanager
def _finalizable_sigterm() -> Any:
    """Raise on SIGTERM when installed from a main-thread CLI invocation."""

    installed = False
    previous: Any = None

    def terminate(signum: int, _frame: Any) -> None:
        raise _TerminationRequested(signum)

    try:
        previous = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, terminate)
        installed = True
    except (AttributeError, OSError, ValueError):
        pass
    try:
        yield
    finally:
        if installed:
            signal.signal(signal.SIGTERM, previous)


def run_dsh_campaign(
    output_directory: str | Path,
    *,
    session_id: str,
    resume: bool = False,
    executable: str = "dsh",
    profile: str = DSH_PROFILE,
) -> int:
    """Run or resume one stable DSH session against a stored launch contract."""

    root = Path(output_directory).expanduser().resolve()
    request = load_launch_request(root)
    if request is None:
        raise DshEngineError("DSH launch requires operator_input/launch.json")
    if request.engine != "dsh":
        raise DshEngineError("stored launch contract does not select the DSH engine")
    if request.dsh_session_id != session_id:
        raise DshEngineError("DSH session identity does not match the launch contract")
    _validate_session_id(session_id)

    resolved_executable = shutil.which(executable)
    if resolved_executable is None:
        raise DshEngineError(
            "DeepSeek Harness executable 'dsh' was not found on PATH; install the "
            "pinned Simjecture DSH profile before launching a DSH campaign"
        )

    operator = root / "operator_input"
    session_root = root / DSH_SESSION_DIRECTORY
    activity_file = root / DSH_ACTIVITY_FILE
    state_file = root / DSH_STATE_FILE
    control_file = root / DSH_CONTROL_FILE
    for path in (operator, session_root):
        _require_contained_directory(root, path)
    if activity_file.is_symlink():
        raise DshEngineError(f"DSH file must not be a symlink: {activity_file}")
    activity_file.touch(mode=0o600, exist_ok=True)
    _require_contained_file(root, activity_file)

    environment = _dsh_environment(
        request=request,
        root=root,
        session_id=session_id,
        session_root=session_root,
        activity_file=activity_file,
        state_file=state_file,
        control_file=control_file,
        resume=resume,
    )
    task = RESUME_TASK if resume else INITIAL_TASK
    argv = [resolved_executable, "--profile", profile, task]
    clock = begin_or_resume_clock(root)
    remaining_wall_seconds = max(
        0.0,
        request.max_wall_seconds - elapsed_from_clock(clock),
    )
    _write_state(
        state_file,
        {
            "status": "launching",
            "engine": "dsh",
            "session_id": session_id,
            "resume_requested": resume,
            "updated_at": _utc_now(),
        },
    )

    if remaining_wall_seconds <= 0:
        _write_state(
            state_file,
            {
                "status": "budget_exhausted",
                "engine": "dsh",
                "session_id": session_id,
                "reason": "campaign wall-clock budget exhausted before DSH launch",
                "updated_at": _utc_now(),
            },
        )
        finalize_clock(root)
        return 124

    try:
        with _finalizable_sigterm():
            completed = subprocess.run(
                argv,
                cwd=root,
                env=environment,
                check=False,
                timeout=remaining_wall_seconds,
            )
    except subprocess.TimeoutExpired:
        _write_state(
            state_file,
            {
                "status": "budget_exhausted",
                "engine": "dsh",
                "session_id": session_id,
                "reason": "campaign wall-clock budget exhausted during DSH execution",
                "updated_at": _utc_now(),
            },
        )
        finalize_clock(root)
        return 124
    except _TerminationRequested as termination:
        signal_name = signal.Signals(termination.signum).name
        _write_state(
            state_file,
            {
                "status": "cancelled",
                "engine": "dsh",
                "session_id": session_id,
                "reason": f"received {signal_name} during DSH execution",
                "updated_at": _utc_now(),
            },
        )
        finalize_clock(root)
        return 128 + termination.signum
    except KeyboardInterrupt:
        _write_state(
            state_file,
            {
                "status": "cancelled",
                "engine": "dsh",
                "session_id": session_id,
                "updated_at": _utc_now(),
            },
        )
        finalize_clock(root)
        return 130

    state = _read_state(state_file)
    if state.get("status") == "paused":
        pause_at_boundary(root, iterations=_operation_count(root))
        return 0
    if completed.returncode != 0 and state.get("status") not in {"failed", "paused"}:
        _write_state(
            state_file,
            {
                "status": "failed",
                "engine": "dsh",
                "session_id": session_id,
                "returncode": completed.returncode,
                "updated_at": _utc_now(),
            },
        )
    # Bank this invocation's active harness time even when DSH ends normally.
    # A later resume starts a new session interval from the accumulated value;
    # calendar time between invocations is therefore never charged.
    finalize_clock(root)
    return int(completed.returncode)


def _dsh_environment(
    *,
    request: Any,
    root: Path,
    session_id: str,
    session_root: Path,
    activity_file: Path,
    state_file: Path,
    control_file: Path,
    resume: bool,
) -> dict[str, str]:
    environment = dict(os.environ)
    # Preserve the launcher path instead of resolving its final interpreter.
    # Virtual environments commonly expose ``python`` as a symlink; resolving
    # it would discard the environment's ``bin`` directory, which is exactly
    # where the companion ``simjecture-mcp`` console script is installed.
    executable_directory = str(Path(sys.executable).absolute().parent)
    current_path = environment.get("PATH", "")
    environment["PATH"] = (
        executable_directory
        if not current_path
        else os.pathsep.join((executable_directory, current_path))
    )
    environment.update(
        {
            "SIMJECTURE_WORKSPACE": str(root),
            "SIMJECTURE_CAMPAIGN": "",
            "SIMJECTURE_HYPOTHESIS_FILE": str(root / "operator_input" / "hypothesis.txt"),
            "SIMJECTURE_CAPABILITIES": request.capability_directory or "",
            "SIMJECTURE_SKILLS": request.skills_directory or "",
            "SIMJECTURE_MCP_MAX_OUTPUT_CHARS": str(request.max_tool_output_chars),
            "SIMJECTURE_MCP_TIMEOUT_SECONDS": _format_number(request.max_command_seconds),
            "SIMJECTURE_DSH_SESSION_ID": session_id,
            "SIMJECTURE_DSH_SESSION_ROOT": str(session_root),
            "SIMJECTURE_DSH_ACTIVITY_FILE": str(activity_file),
            "SIMJECTURE_DSH_STATE_FILE": str(state_file),
            "SIMJECTURE_DSH_CONTROL_FILE": str(control_file),
            "SIMJECTURE_DSH_RESUME": "1" if resume else "0",
        }
    )
    return environment


def _validate_session_id(session_id: str) -> None:
    import re

    if not re.fullmatch(DSH_SESSION_ID_PATTERN, session_id):
        raise DshEngineError("invalid DSH session identity")


def _require_contained_directory(root: Path, path: Path) -> None:
    if path.is_symlink():
        raise DshEngineError(f"DSH directory must not be a symlink: {path}")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_dir():
        raise DshEngineError(f"DSH directory escapes the campaign: {path}")


def _require_contained_file(root: Path, path: Path) -> None:
    if path.is_symlink():
        raise DshEngineError(f"DSH file must not be a symlink: {path}")
    resolved = path.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise DshEngineError(f"DSH file escapes the campaign: {path}")


def _write_state(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _read_state(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _operation_count(root: Path) -> int:
    path = root / "action_journal.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 0
    operations = payload.get("operations") if isinstance(payload, dict) else None
    return len(operations) if isinstance(operations, dict) else 0


def _format_number(value: float) -> str:
    return format(value, ".15g")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def run_from_cli(args: Any) -> int:
    """CLI adapter kept separate so importing the main parser does not import DSH."""

    try:
        return run_dsh_campaign(
            args.output,
            session_id=args.session_id,
            resume=args.resume,
        )
    except (DshEngineError, ResumeError, OSError, ValueError) as error:
        print(f"simjecture DSH engine: {error}", file=sys.stderr)
        return 2


__all__ = [
    "DSH_ACTIVITY_FILE",
    "DSH_PROFILE",
    "DSH_SESSION_DIRECTORY",
    "DSH_STATE_FILE",
    "DshEngineError",
    "run_dsh_campaign",
    "run_from_cli",
]
