"""Safe subprocess construction for operator-launched MVP campaigns.

The launcher materializes operator inputs as files and never builds a shell
string. Hypothesis text stays out of argv except as a path to those files.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel
from .mvp_control import ControlCommand, write_control

OPERATOR_INPUT_DIR = "operator_input"
CONTROLLER_LOG_NAME = "controller.log"
LAUNCH_RECORD_NAME = "launch.json"
SUPERVISOR_RECORD_NAME = "supervisor.json"
HYPOTHESIS_FILE_NAME = "hypothesis.txt"
INSTRUCTION_FILE_NAME = "instruction.txt"
GUIDED_COMMISSIONING_DIR_NAME = "guided_commissioning"
RUN_LOCK_NAME = "runner.lock"
CAMPAIGN_ID_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$"
DSH_SESSION_ID_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$"
ReasoningEngine = Literal["native", "dsh"]


class MVPLaunchRequest(StrictModel):
    hypothesis: str = Field(min_length=1)
    instruction: str | None = None
    campaign_id: str = Field(pattern=CAMPAIGN_ID_PATTERN)
    output_directory: str
    max_wall_seconds: float = Field(default=21_600.0, gt=0)
    max_command_seconds: float = Field(default=600.0, gt=0)
    max_workspace_mb: int = Field(default=512, ge=1)
    max_file_mb: int = Field(default=64, ge=1)
    max_memory_mb: int = Field(default=4096, ge=1)
    max_iterations: int | None = Field(default=None, ge=1)
    max_tool_output_chars: int = Field(default=30_000, ge=1)
    command_heartbeat_seconds: float = Field(default=30.0, gt=0)
    literature_search_timeout_seconds: float = Field(default=20.0, gt=0)
    recent_full_turns: int = Field(default=8, ge=1)
    max_model_retries: int = Field(default=3, ge=0)
    model_failover_after: int = Field(default=2, ge=1)
    ledger: str | None = None
    guided_commission: str | None = None
    skills_directory: str | None = None
    capability_directory: str | None = None
    use_glm: bool = False
    reason: str | None = None
    engine: ReasoningEngine = "native"
    dsh_session_id: str | None = Field(default=None, pattern=DSH_SESSION_ID_PATTERN)
    executable: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_route(self) -> MVPLaunchRequest:
        if self.use_glm and not (self.reason and self.reason.strip()):
            raise ValueError("use_glm requires a non-empty reason")
        if self.engine == "native" and self.dsh_session_id is not None:
            raise ValueError("dsh_session_id requires engine='dsh'")
        return self


class MVPLaunchPlan(StrictModel):
    request: MVPLaunchRequest
    output_directory: str
    hypothesis_file: str
    instruction_file: str | None = None
    guided_commission_file: str | None = None
    launch_record: str
    controller_log: str
    argv: tuple[str, ...]
    engine: ReasoningEngine = "native"
    dsh_session_id: str | None = None


class ProcessIdentity(StrictModel):
    pid: int = Field(ge=1)
    starttime: str
    argv: tuple[str, ...]
    launched_at: str
    run_directory: str | None = None


class LaunchConflictError(ValueError):
    """An output directory already contains a different launch contract."""


class RunAlreadyActiveError(RuntimeError):
    """A runner already owns the output-directory lock."""


def default_mvp_executable() -> tuple[str, ...]:
    return (sys.executable, "-m", "conjecture_solver")


def validate_campaign_id(value: str) -> str:
    import re

    candidate = value.strip()
    if not re.fullmatch(CAMPAIGN_ID_PATTERN, candidate):
        raise ValueError(
            "campaign id must start with a letter and use only letters, digits, "
            "'_', '.', or '-'"
        )
    return candidate


def materialize_operator_input(
    request: MVPLaunchRequest,
    *,
    create_output: bool = True,
    resume: bool = False,
) -> MVPLaunchPlan:
    output = Path(request.output_directory).expanduser().resolve()
    if create_output:
        output.mkdir(parents=True, exist_ok=True)
    if not output.is_dir():
        raise NotADirectoryError(f"output path is not a directory: {output}")
    if output_lock_is_held(output):
        raise RunAlreadyActiveError(
            f"another runner owns the output directory: {output}"
        )
    operator = _secure_operator_directory(output, create=True)
    hypothesis_file = operator / HYPOTHESIS_FILE_NAME
    hypothesis_text = request.hypothesis
    instruction_file: Path | None = None
    instruction_text: str | None = None
    if request.instruction and request.instruction.strip():
        instruction_file = operator / INSTRUCTION_FILE_NAME
        instruction_text = request.instruction

    guided_package = None
    guided_file: Path | None = None
    guided_sha256: str | None = None
    if request.guided_commission:
        from .mvp_guidance import MVPGuidedCommissioningPackage

        guided_package = MVPGuidedCommissioningPackage.read(request.guided_commission)
        guided_file = operator / GUIDED_COMMISSIONING_DIR_NAME / "manifest.json"
        guided_sha256 = guided_package.package_sha256

    normalized = request.model_copy(
        update={
            "output_directory": str(output),
            "instruction": instruction_text,
            "ledger": _normalized_optional_path(request.ledger),
            "guided_commission": str(guided_file) if guided_file else None,
            "skills_directory": _normalized_optional_path(request.skills_directory),
            "capability_directory": _normalized_optional_path(
                request.capability_directory
            ),
            "dsh_session_id": (
                request.dsh_session_id
                or (_default_dsh_session_id(request) if request.engine == "dsh" else None)
            ),
        }
    )
    argv = build_launch_argv(
        normalized,
        hypothesis_file=hypothesis_file,
        instruction_file=instruction_file,
        resume=resume,
    )
    launch_record = operator / LAUNCH_RECORD_NAME
    blocked = _automatic_resume_blockers(normalized, output)
    record: dict[str, Any] = {
        "schema_version": "0.3.0",
        "campaign_id": normalized.campaign_id,
        "hypothesis_file": hypothesis_file.name,
        "hypothesis_sha256": _sha256_text(hypothesis_text),
        "instruction_file": instruction_file.name if instruction_file else None,
        "instruction_sha256": (
            _sha256_text(instruction_text) if instruction_text is not None else None
        ),
        "guided_commission": (
            f"{GUIDED_COMMISSIONING_DIR_NAME}/manifest.json" if guided_file else None
        ),
        "guided_commission_sha256": guided_sha256,
        "output_directory": str(output),
        "max_wall_seconds": normalized.max_wall_seconds,
        "max_command_seconds": normalized.max_command_seconds,
        "max_workspace_mb": normalized.max_workspace_mb,
        "max_file_mb": normalized.max_file_mb,
        "max_memory_mb": normalized.max_memory_mb,
        "max_iterations": normalized.max_iterations,
        "max_tool_output_chars": normalized.max_tool_output_chars,
        "command_heartbeat_seconds": normalized.command_heartbeat_seconds,
        "literature_search_timeout_seconds": (
            normalized.literature_search_timeout_seconds
        ),
        "recent_full_turns": normalized.recent_full_turns,
        "max_model_retries": normalized.max_model_retries,
        "model_failover_after": normalized.model_failover_after,
        "ledger": _recorded_path(normalized.ledger, output),
        "skills_directory": _recorded_path(normalized.skills_directory, output),
        "capability_directory": _recorded_path(
            normalized.capability_directory, output
        ),
        "use_glm": normalized.use_glm,
        "reason": normalized.reason,
        "engine": normalized.engine,
        "dsh_session_id": normalized.dsh_session_id,
        "automatic_resume_blockers": blocked,
        "argv": list(argv),
        "written_at": datetime.now(UTC).isoformat(),
    }
    existing = _load_secure_json(launch_record, root=output)
    if existing is not None:
        _assert_launch_record_matches(
            existing,
            desired=record,
            output=output,
            hypothesis_text=hypothesis_text,
            instruction_text=instruction_text,
        )
        if existing.get("schema_version") in {"0.2.0", "0.3.0"}:
            return MVPLaunchPlan(
                request=normalized,
                output_directory=str(output),
                hypothesis_file=str(hypothesis_file),
                instruction_file=str(instruction_file) if instruction_file else None,
                guided_commission_file=str(guided_file) if guided_file else None,
                launch_record=str(launch_record),
                controller_log=str(output / CONTROLLER_LOG_NAME),
                argv=argv,
                engine=normalized.engine,
                dsh_session_id=normalized.dsh_session_id,
            )
    else:
        _assert_unrecorded_output_is_compatible(
            output,
            operator=operator,
            request=normalized,
            hypothesis_text=hypothesis_text,
            instruction_text=instruction_text,
            guided_commission_sha256=guided_sha256,
        )

    _atomic_write_text(hypothesis_file, hypothesis_text)
    if instruction_file is not None and instruction_text is not None:
        _atomic_write_text(instruction_file, instruction_text)
    if guided_package is not None and guided_file is not None:
        _materialize_guided_package(guided_package, guided_file)
    _atomic_write_text(launch_record, json.dumps(record, indent=2, sort_keys=True) + "\n")
    return MVPLaunchPlan(
        request=normalized,
        output_directory=str(output),
        hypothesis_file=str(hypothesis_file),
        instruction_file=str(instruction_file) if instruction_file else None,
        guided_commission_file=str(guided_file) if guided_file else None,
        launch_record=str(launch_record),
        controller_log=str(output / CONTROLLER_LOG_NAME),
        argv=argv,
        engine=normalized.engine,
        dsh_session_id=normalized.dsh_session_id,
    )


def build_launch_argv(
    request: MVPLaunchRequest,
    *,
    hypothesis_file: Path,
    instruction_file: Path | None,
    resume: bool = False,
) -> tuple[str, ...]:
    """Build the reviewed native or DSH supervisor command without inline science text."""

    if request.engine == "dsh":
        return build_dsh_argv(request, resume=resume)
    return build_mvp_argv(
        request,
        hypothesis_file=hypothesis_file,
        instruction_file=instruction_file,
    )


def build_dsh_argv(
    request: MVPLaunchRequest,
    *,
    resume: bool = False,
) -> tuple[str, ...]:
    """Build the stable Python supervisor command for one DSH session."""

    if request.engine != "dsh" or request.dsh_session_id is None:
        raise ValueError("a DSH launch requires a durable dsh_session_id")
    executable = request.executable or default_mvp_executable()
    argv = [
        *executable,
        "dsh-run",
        "--output",
        str(Path(request.output_directory).expanduser().resolve()),
        "--session-id",
        request.dsh_session_id,
    ]
    if resume:
        argv.append("--resume")
    if any("\x00" in item for item in argv):
        raise ValueError("command arguments cannot contain NUL bytes")
    return tuple(argv)


def build_mvp_argv(
    request: MVPLaunchRequest,
    *,
    hypothesis_file: Path,
    instruction_file: Path | None,
) -> tuple[str, ...]:
    executable = request.executable or default_mvp_executable()
    argv = [
        *executable,
        "mvp",
        "--hypothesis-file",
        str(hypothesis_file),
        "--campaign-id",
        request.campaign_id,
        "--output",
        str(Path(request.output_directory).expanduser().resolve()),
        "--max-wall-seconds",
        _format_number(request.max_wall_seconds),
        "--max-command-seconds",
        _format_number(request.max_command_seconds),
        "--max-workspace-mb",
        str(request.max_workspace_mb),
        "--max-file-mb",
        str(request.max_file_mb),
        "--max-memory-mb",
        str(request.max_memory_mb),
        "--max-tool-output-chars",
        str(request.max_tool_output_chars),
        "--command-heartbeat-seconds",
        _format_number(request.command_heartbeat_seconds),
        "--literature-search-timeout-seconds",
        _format_number(request.literature_search_timeout_seconds),
        "--recent-full-turns",
        str(request.recent_full_turns),
        "--max-model-retries",
        str(request.max_model_retries),
        "--model-failover-after",
        str(request.model_failover_after),
    ]
    if instruction_file is not None:
        argv.extend(["--instruction-file", str(instruction_file)])
    if request.max_iterations is not None:
        argv.extend(["--max-iterations", str(request.max_iterations)])
    if request.ledger:
        argv.extend(["--ledger", request.ledger])
    if request.guided_commission:
        argv.extend(["--guided-commission", request.guided_commission])
    if request.skills_directory:
        argv.extend(["--skills-directory", request.skills_directory])
    if request.capability_directory:
        argv.extend(["--capability-directory", request.capability_directory])
    if request.use_glm:
        argv.append("--use-glm")
    if request.reason:
        argv.extend(["--reason", request.reason])
    if any("\x00" in item for item in argv):
        raise ValueError("command arguments cannot contain NUL bytes")
    return tuple(argv)


def read_process_identity(
    pid: int,
    argv: Sequence[str] = (),
    *,
    run_directory: str | Path | None = None,
) -> ProcessIdentity | None:
    stat_path = Path(f"/proc/{pid}/stat")
    if not stat_path.is_file():
        return None
    try:
        stat_text = stat_path.read_text()
    except OSError:
        return None
    starttime = _starttime_from_stat(stat_text)
    if starttime is None:
        return None
    actual_argv = _read_process_argv(pid)
    if actual_argv is None and argv:
        actual_argv = tuple(argv)
    if actual_argv is None:
        return None
    return ProcessIdentity(
        pid=pid,
        starttime=starttime,
        argv=actual_argv,
        launched_at=datetime.now(UTC).isoformat(),
        run_directory=(
            str(Path(run_directory).expanduser().resolve())
            if run_directory is not None
            else None
        ),
    )


def process_identity_matches(expected: ProcessIdentity) -> bool:
    current = read_process_identity(expected.pid)
    if current is None:
        return False
    if current.starttime != expected.starttime or current.argv != expected.argv:
        return False
    state = _state_from_stat_path(expected.pid)
    return state not in {None, "Z", "X"}


def write_supervisor_record(output_directory: str | Path, identity: ProcessIdentity) -> Path:
    root = Path(output_directory).expanduser().resolve()
    operator = _secure_operator_directory(root, create=True)
    path = operator / SUPERVISOR_RECORD_NAME
    bound = identity.model_copy(update={"run_directory": str(root)})
    payload = {
        "schema_version": "0.2.0",
        "pid": bound.pid,
        "starttime": bound.starttime,
        "argv": list(bound.argv),
        "launched_at": bound.launched_at,
        "run_directory": bound.run_directory,
    }
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def load_supervisor_record(output_directory: str | Path) -> ProcessIdentity | None:
    root = Path(output_directory).expanduser().resolve()
    try:
        operator = _secure_operator_directory(root, create=False)
    except (FileNotFoundError, ValueError):
        return None
    path = operator / SUPERVISOR_RECORD_NAME
    payload = _load_secure_json(path, root=root)
    if payload is None or payload.get("schema_version") != "0.2.0":
        return None
    pid = payload.get("pid")
    starttime = payload.get("starttime")
    argv = payload.get("argv")
    launched_at = payload.get("launched_at")
    run_directory = payload.get("run_directory")
    if not isinstance(pid, int) or pid < 1:
        return None
    if not isinstance(starttime, str) or not isinstance(launched_at, str):
        return None
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        return None
    if not isinstance(run_directory, str):
        return None
    try:
        recorded_root = Path(run_directory).expanduser().resolve()
    except OSError:
        return None
    if recorded_root != root or not _argv_targets_run(tuple(argv), root):
        return None
    identity = ProcessIdentity(
        pid=pid,
        starttime=starttime,
        argv=tuple(argv),
        launched_at=launched_at,
        run_directory=str(root),
    )
    return identity if process_identity_matches(identity) else None


class ManagedCampaign:
    """A runner subprocess started by this operator interface."""

    def __init__(
        self,
        plan: MVPLaunchPlan,
        process: subprocess.Popen[bytes],
        identity: ProcessIdentity,
        log_handle: IO[bytes],
    ) -> None:
        self.plan = plan
        self.process = process
        self.identity = identity
        self.log_handle = log_handle

    def poll(self) -> int | None:
        return self.process.poll()

    def is_alive(self) -> bool:
        if self.process.poll() is not None:
            return False
        return process_identity_matches(self.identity)

    def cancel(
        self,
        *,
        wait_interrupt_seconds: float = 20.0,
        wait_terminate_seconds: float = 10.0,
        sleep: Any = time.sleep,
    ) -> str:
        result = request_graceful_cancel(
            self.identity,
            wait_interrupt_seconds=wait_interrupt_seconds,
            wait_terminate_seconds=wait_terminate_seconds,
            sleep=sleep,
        )
        with suppress(Exception):
            self.process.poll()
        return result

    def close(self) -> None:
        with suppress(OSError):
            self.log_handle.close()


def start_managed_campaign(
    plan: MVPLaunchPlan,
    *,
    popen: Any = subprocess.Popen,
) -> ManagedCampaign:
    log_path = Path(plan.controller_log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("ab", buffering=0)
    try:
        process = popen(
            list(plan.argv),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception:
        log_handle.close()
        raise
    identity = read_process_identity(
        process.pid,
        plan.argv,
        run_directory=plan.output_directory,
    )
    if identity is None:
        identity = ProcessIdentity(
            pid=process.pid,
            starttime="unavailable",
            argv=plan.argv,
            launched_at=datetime.now(UTC).isoformat(),
            run_directory=plan.output_directory,
        )
    write_supervisor_record(plan.output_directory, identity)
    return ManagedCampaign(
        plan=plan,
        process=process,
        identity=identity,
        log_handle=log_handle,
    )


class ResumeError(ValueError):
    """A campaign cannot be resumed from the stored operator launch record."""


def persist_operator_launch(
    *,
    hypothesis: str,
    instruction: str | None,
    campaign_id: str,
    output_directory: str | Path,
    max_wall_seconds: float,
    max_command_seconds: float,
    max_workspace_mb: int,
    max_file_mb: int,
    max_memory_mb: int,
    max_iterations: int | None = None,
    max_tool_output_chars: int = 30_000,
    command_heartbeat_seconds: float = 30.0,
    literature_search_timeout_seconds: float = 20.0,
    recent_full_turns: int = 8,
    max_model_retries: int = 3,
    model_failover_after: int = 2,
    ledger: str | None = None,
    guided_commission: str | None = None,
    skills_directory: str | None = None,
    capability_directory: str | None = None,
    use_glm: bool = False,
    reason: str | None = None,
) -> MVPLaunchPlan:
    """Write the complete structured launch contract for safe later resume."""

    return materialize_operator_input(
        MVPLaunchRequest(
            hypothesis=hypothesis,
            instruction=instruction,
            campaign_id=validate_campaign_id(campaign_id),
            output_directory=str(output_directory),
            max_wall_seconds=max_wall_seconds,
            max_command_seconds=max_command_seconds,
            max_workspace_mb=max_workspace_mb,
            max_file_mb=max_file_mb,
            max_memory_mb=max_memory_mb,
            max_iterations=max_iterations,
            max_tool_output_chars=max_tool_output_chars,
            command_heartbeat_seconds=command_heartbeat_seconds,
            literature_search_timeout_seconds=literature_search_timeout_seconds,
            recent_full_turns=recent_full_turns,
            max_model_retries=max_model_retries,
            model_failover_after=model_failover_after,
            ledger=ledger,
            guided_commission=guided_commission,
            skills_directory=skills_directory,
            capability_directory=capability_directory,
            use_glm=use_glm,
            reason=reason,
        )
    )


def load_launch_request(run_directory: str | Path) -> MVPLaunchRequest | None:
    root = Path(run_directory).expanduser().resolve()
    try:
        operator = _secure_operator_directory(root, create=False)
    except (FileNotFoundError, ValueError):
        return None
    path = operator / LAUNCH_RECORD_NAME
    payload = _load_secure_json(path, root=root)
    if payload is None:
        return None
    schema_version = payload.get("schema_version")
    if schema_version == "0.1.0":
        raise ResumeError(
            "legacy launch record does not contain the complete MVP contract; "
            "repeat the reviewed original command"
        )
    if schema_version not in {"0.2.0", "0.3.0"}:
        raise ResumeError(f"unsupported launch record schema: {schema_version!r}")
    blockers = payload.get("automatic_resume_blockers") or []
    if not isinstance(blockers, list) or not all(
        isinstance(item, str) for item in blockers
    ):
        raise ResumeError("launch record has invalid automatic_resume_blockers")
    if blockers:
        raise ResumeError(
            "automatic resume is disabled for this non-self-contained contract: "
            + "; ".join(blockers)
            + ". Repeat the reviewed original command instead."
        )
    hypothesis_name = payload.get("hypothesis_file") or HYPOTHESIS_FILE_NAME
    if hypothesis_name != HYPOTHESIS_FILE_NAME:
        raise ResumeError("launch record hypothesis_file must be hypothesis.txt")
    hypothesis_path = _contained_regular_file(
        root,
        operator / HYPOTHESIS_FILE_NAME,
        description="stored hypothesis",
    )
    try:
        hypothesis = hypothesis_path.read_text()
    except OSError:
        raise ResumeError("stored hypothesis could not be read") from None
    expected_hypothesis_hash = payload.get("hypothesis_sha256")
    if expected_hypothesis_hash != _sha256_text(hypothesis):
        raise ResumeError("stored hypothesis identity does not match launch.json")
    instruction = None
    instruction_name = payload.get("instruction_file")
    if instruction_name is not None:
        if instruction_name != INSTRUCTION_FILE_NAME:
            raise ResumeError("launch record instruction_file must be instruction.txt")
        instruction_path = _contained_regular_file(
            root,
            operator / INSTRUCTION_FILE_NAME,
            description="stored instruction",
        )
        instruction = instruction_path.read_text()
        if payload.get("instruction_sha256") != _sha256_text(instruction):
            raise ResumeError("stored instruction identity does not match launch.json")

    guided_commission = None
    guided_name = payload.get("guided_commission")
    if guided_name is not None:
        expected = f"{GUIDED_COMMISSIONING_DIR_NAME}/manifest.json"
        if guided_name != expected:
            raise ResumeError("guided commissioning path is not self-contained")
        guided_path = _contained_regular_file(
            root,
            operator / GUIDED_COMMISSIONING_DIR_NAME / "manifest.json",
            description="guided commissioning manifest",
        )
        from .mvp_guidance import MVPGuidedCommissioningPackage

        package = MVPGuidedCommissioningPackage.read(guided_path)
        if payload.get("guided_commission_sha256") != package.package_sha256:
            raise ResumeError("guided commissioning identity does not match launch.json")
        guided_commission = str(guided_path)

    try:
        request = MVPLaunchRequest(
            hypothesis=hypothesis,
            instruction=instruction,
            campaign_id=str(payload.get("campaign_id") or root.name),
            output_directory=str(root),
            max_wall_seconds=float(payload.get("max_wall_seconds", 21_600.0)),
            max_command_seconds=float(payload.get("max_command_seconds", 600.0)),
            max_workspace_mb=int(payload.get("max_workspace_mb", 512)),
            max_file_mb=int(payload.get("max_file_mb", 64)),
            max_memory_mb=int(payload.get("max_memory_mb", 4096)),
            max_iterations=(
                int(payload["max_iterations"])
                if payload.get("max_iterations") is not None
                else None
            ),
            max_tool_output_chars=int(payload.get("max_tool_output_chars", 30_000)),
            command_heartbeat_seconds=float(
                payload.get("command_heartbeat_seconds", 30.0)
            ),
            literature_search_timeout_seconds=float(
                payload.get("literature_search_timeout_seconds", 20.0)
            ),
            recent_full_turns=int(payload.get("recent_full_turns", 12)),
            max_model_retries=int(payload.get("max_model_retries", 3)),
            model_failover_after=int(payload.get("model_failover_after", 2)),
            ledger=_load_recorded_path(payload.get("ledger"), root, "ledger"),
            guided_commission=guided_commission,
            skills_directory=_load_recorded_path(
                payload.get("skills_directory"), root, "skills directory"
            ),
            capability_directory=_load_recorded_path(
                payload.get("capability_directory"), root, "capability directory"
            ),
            use_glm=payload.get("use_glm") is True,
            reason=(
                str(payload["reason"])
                if isinstance(payload.get("reason"), str)
                else None
            ),
            engine=(
                str(payload.get("engine") or "native")
                if schema_version == "0.3.0"
                else "native"
            ),
            dsh_session_id=(
                str(payload["dsh_session_id"])
                if schema_version == "0.3.0"
                and isinstance(payload.get("dsh_session_id"), str)
                else None
            ),
        )
    except ResumeError:
        raise
    except Exception as error:
        raise ResumeError(f"stored launch contract is invalid: {error}") from error
    return request


def request_verified_pause(
    run_directory: str | Path,
    *,
    source: str = "operator",
) -> str:
    """Ask a verified live runner to pause after the current action."""

    record = load_supervisor_record(run_directory)
    if record is None or not process_identity_matches(record):
        return "no verified running process; nothing to pause"
    write_control(run_directory, ControlCommand.PAUSE, source=source)
    return "pause requested at the next action boundary"


def prepare_resume(run_directory: str | Path) -> MVPLaunchPlan:
    root = Path(run_directory).expanduser().resolve()
    if not root.is_dir():
        raise ResumeError(f"run directory does not exist: {root}")
    if (root / "mvp_report.json").is_file():
        raise ResumeError(
            "a terminal report exists; repeating the original mvp command replays it"
        )
    if output_lock_is_held(root):
        raise ResumeError("a runner already owns this output directory; attach instead")
    record = load_supervisor_record(root)
    if record is not None and process_identity_matches(record):
        raise ResumeError(f"process still running (pid={record.pid}); attach instead")
    request = load_launch_request(root)
    if request is None:
        raise ResumeError(
            "no operator_input/launch.json; repeat the original mvp command to resume"
        )
    return materialize_operator_input(request, resume=True)


def request_graceful_cancel(
    identity: ProcessIdentity,
    *,
    wait_interrupt_seconds: float = 20.0,
    wait_terminate_seconds: float = 10.0,
    sleep: Any = time.sleep,
) -> str:
    """Cancel a verified campaign tree, then its supervisor process.

    Detached kernel workers are deliberately restart-safe, so killing only the
    campaign supervisor can otherwise leave a simulation consuming CPU/GPU.
    When ``run_directory`` identifies a campaign, verified non-terminal jobs
    are cancelled before the supervisor and reconciled once more after it
    exits. Never signals an unverified PID. Does not use SIGKILL or SIGSTOP.
    """

    if not process_identity_matches(identity):
        return "process identity does not match; no signal sent"
    _cancel_active_campaign_jobs(
        identity,
        wait_interrupt_seconds=wait_interrupt_seconds,
        wait_terminate_seconds=wait_terminate_seconds,
        sleep=sleep,
    )
    if not _signal_verified(identity, signal.SIGINT):
        result = "process already exited"
    elif _wait_for_exit(identity, wait_interrupt_seconds, sleep=sleep):
        result = "interrupted"
    elif not process_identity_matches(identity):
        result = "process identity changed after interrupt; no further signal sent"
    elif not _signal_verified(identity, signal.SIGTERM):
        result = "interrupted"
    elif _wait_for_exit(identity, wait_terminate_seconds, sleep=sleep):
        result = "terminated"
    else:
        result = "cancel requested; process still running"
    # Close the small race in which a worker handshake became durable between
    # the first job scan and the supervisor signal.
    _cancel_active_campaign_jobs(
        identity,
        wait_interrupt_seconds=wait_interrupt_seconds,
        wait_terminate_seconds=wait_terminate_seconds,
        sleep=sleep,
    )
    return result


def _cancel_active_campaign_jobs(
    identity: ProcessIdentity,
    *,
    wait_interrupt_seconds: float,
    wait_terminate_seconds: float,
    sleep: Any,
) -> tuple[str, ...]:
    """Cancel verified durable jobs below ``identity.run_directory``.

    This is intentionally a best-effort companion to supervisor cancellation:
    malformed or absent job state must never prevent signalling the already
    verified campaign PID. Individual job cancellation still performs its own
    PID/start-time/argv verification immediately before every signal.
    """

    if identity.run_directory is None:
        return ()
    try:
        root = Path(identity.run_directory).expanduser().resolve()
    except OSError:
        return ()
    jobs_root = root / "jobs"
    if not (jobs_root / "jobs").is_dir():
        return ()
    try:
        # Local import avoids the module-level cycle: campaign_jobs reuses this
        # verified signal primitive for each detached worker.
        from .campaign_jobs import CampaignJobSupervisor

        supervisor = CampaignJobSupervisor(jobs_root)
        outcomes: list[str] = []
        for state in supervisor.jobs():
            if state.status.terminal:
                continue
            cancelled = supervisor.cancel(
                state.job_id,
                wait_interrupt_seconds=min(max(0.0, wait_interrupt_seconds), 5.0),
                wait_terminate_seconds=min(max(0.0, wait_terminate_seconds), 2.0),
                sleep=sleep,
            )
            outcomes.append(f"{state.operation_id}:{cancelled.status.value}")
        return tuple(outcomes)
    except Exception:  # noqa: BLE001 - parent cancellation must still proceed
        return ()


def _signal_verified(identity: ProcessIdentity, sig: signal.Signals) -> bool:
    if not process_identity_matches(identity):
        return False
    try:
        group = os.getpgid(identity.pid)
        if group == identity.pid:
            os.killpg(group, sig)
        else:
            os.kill(identity.pid, sig)
    except ProcessLookupError:
        return False
    return True


def _wait_for_exit(
    identity: ProcessIdentity,
    timeout_seconds: float,
    *,
    sleep: Any,
) -> bool:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while time.monotonic() < deadline:
        if not process_identity_matches(identity):
            return True
        sleep(0.05)
    return not process_identity_matches(identity)


class MVPOutputLock:
    """Non-blocking exclusive ownership of one durable run directory."""

    def __init__(self, run_directory: str | Path) -> None:
        self.root = Path(run_directory).expanduser().resolve()
        self._fd: int | None = None

    def __enter__(self) -> MVPOutputLock:
        self.root.mkdir(parents=True, exist_ok=True)
        operator = _secure_operator_directory(self.root, create=True)
        path = operator / RUN_LOCK_NAME
        flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags, 0o600)
        except OSError as error:
            raise RunAlreadyActiveError(
                f"cannot safely open the run lock: {path}: {error}"
            ) from error
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            os.close(fd)
            raise RunAlreadyActiveError(
                f"another runner owns the output directory: {self.root}"
            ) from error
        self._fd = fd
        os.ftruncate(fd, 0)
        os.write(fd, f"pid={os.getpid()}\n".encode())
        os.fsync(fd)
        return self

    def __exit__(self, *_args: object) -> None:
        if self._fd is None:
            return
        with suppress(OSError):
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        with suppress(OSError):
            os.close(self._fd)
        self._fd = None


def output_lock_is_held(run_directory: str | Path) -> bool:
    """Return true when another process owns the durable runner lock."""

    root = Path(run_directory).expanduser().resolve()
    try:
        operator = _secure_operator_directory(root, create=False)
    except FileNotFoundError:
        return False
    except ValueError:
        return True
    path = operator / RUN_LOCK_NAME
    if path.is_symlink():
        return True
    if not path.exists():
        return False
    flags = os.O_RDWR | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        return True
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def _secure_operator_directory(root: Path, *, create: bool) -> Path:
    if not root.is_dir():
        raise FileNotFoundError(f"run directory does not exist: {root}")
    operator = root / OPERATOR_INPUT_DIR
    if operator.is_symlink():
        raise ValueError("operator_input must not be a symlink")
    if not operator.exists():
        if not create:
            raise FileNotFoundError(operator)
        operator.mkdir(mode=0o700)
    if not operator.is_dir() or operator.resolve() != operator:
        raise ValueError("operator_input must be a contained regular directory")
    return operator


def _contained_regular_file(root: Path, path: Path, *, description: str) -> Path:
    if path.is_symlink():
        raise ResumeError(f"{description} must not be a symlink")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, FileNotFoundError) as error:
        raise ResumeError(f"{description} is missing or unreadable") from error
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ResumeError(f"{description} must be a regular file inside the run")
    return resolved


def _load_secure_json(path: Path, *, root: Path) -> dict[str, Any] | None:
    if not path.exists() or path.is_symlink():
        return None
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            return None
        payload = json.loads(resolved.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _normalized_optional_path(value: str | None) -> str | None:
    return str(Path(value).expanduser().resolve()) if value else None


def _recorded_path(value: str | None, output: Path) -> str | None:
    if value is None:
        return None
    resolved = Path(value).expanduser().resolve()
    if resolved.is_relative_to(output):
        return resolved.relative_to(output).as_posix()
    return str(resolved)


def _load_recorded_path(value: Any, root: Path, description: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ResumeError(f"stored {description} path is invalid")
    candidate = Path(value)
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if not resolved.is_relative_to(root):
        raise ResumeError(f"stored {description} path escapes the run directory")
    return str(resolved)


def _automatic_resume_blockers(
    request: MVPLaunchRequest,
    output: Path,
) -> list[str]:
    blockers: list[str] = []
    for label, value in (
        ("ledger", request.ledger),
        ("skills directory", request.skills_directory),
        ("capability directory", request.capability_directory),
    ):
        if value is not None and not Path(value).resolve().is_relative_to(output):
            blockers.append(f"{label} is outside the run directory")
    if request.executable and tuple(request.executable) != default_mvp_executable():
        blockers.append("custom executable is not replayed from an artifact")
    return blockers


_CONTRACT_KEYS = frozenset(
    {
        "campaign_id",
        "hypothesis_file",
        "hypothesis_sha256",
        "instruction_file",
        "instruction_sha256",
        "guided_commission",
        "guided_commission_sha256",
        "max_wall_seconds",
        "max_command_seconds",
        "max_workspace_mb",
        "max_file_mb",
        "max_memory_mb",
        "max_iterations",
        "max_tool_output_chars",
        "command_heartbeat_seconds",
        "literature_search_timeout_seconds",
        "recent_full_turns",
        "max_model_retries",
        "model_failover_after",
        "ledger",
        "skills_directory",
        "capability_directory",
        "use_glm",
        "reason",
        "engine",
        "dsh_session_id",
        "automatic_resume_blockers",
    }
)

_V2_CONTRACT_KEYS = _CONTRACT_KEYS - {"engine", "dsh_session_id"}


def _assert_launch_record_matches(
    existing: dict[str, Any],
    *,
    desired: dict[str, Any],
    output: Path,
    hypothesis_text: str,
    instruction_text: str | None,
) -> None:
    schema = existing.get("schema_version")
    if schema == "0.3.0":
        differences = sorted(
            key for key in _CONTRACT_KEYS if existing.get(key) != desired.get(key)
        )
        if differences:
            raise LaunchConflictError(
                "output directory already contains a different launch contract "
                f"({', '.join(differences)})"
            )
    elif schema == "0.2.0":
        differences = sorted(
            key for key in _V2_CONTRACT_KEYS if existing.get(key) != desired.get(key)
        )
        if desired.get("engine") != "native":
            differences.append("engine")
        if differences:
            raise LaunchConflictError(
                "output directory already contains a different launch contract "
                f"({', '.join(differences)})"
            )
    elif schema == "0.1.0":
        legacy_keys = {
            "campaign_id",
            "hypothesis_file",
            "instruction_file",
            "max_wall_seconds",
            "max_command_seconds",
            "max_workspace_mb",
            "max_file_mb",
            "max_memory_mb",
            "max_iterations",
        }
        differences = sorted(
            key for key in legacy_keys if existing.get(key) != desired.get(key)
        )
        advanced_defaults = all(
            desired.get(key) == value
            for key, value in {
                "max_tool_output_chars": 30_000,
                "command_heartbeat_seconds": 30.0,
                "literature_search_timeout_seconds": 20.0,
                "recent_full_turns": 12,
                "max_model_retries": 3,
                "model_failover_after": 2,
                "ledger": None,
                "guided_commission": None,
                "skills_directory": None,
                "capability_directory": None,
                "use_glm": False,
                "reason": None,
            }.items()
        )
        if differences or not advanced_defaults:
            raise LaunchConflictError(
                "legacy launch record does not match the requested contract"
            )
    else:
        raise LaunchConflictError(f"unsupported existing launch schema: {schema!r}")

    operator = _secure_operator_directory(output, create=False)
    hypothesis_path = _contained_regular_file(
        output,
        operator / HYPOTHESIS_FILE_NAME,
        description="stored hypothesis",
    )
    if hypothesis_path.read_text() != hypothesis_text:
        raise LaunchConflictError("stored hypothesis differs from the requested contract")
    instruction_path = operator / INSTRUCTION_FILE_NAME
    if instruction_text is None:
        if instruction_path.exists() or instruction_path.is_symlink():
            raise LaunchConflictError("stored instruction differs from the requested contract")
    else:
        contained = _contained_regular_file(
            output,
            instruction_path,
            description="stored instruction",
        )
        if contained.read_text() != instruction_text:
            raise LaunchConflictError("stored instruction differs from the requested contract")
    guided_manifest = operator / GUIDED_COMMISSIONING_DIR_NAME / "manifest.json"
    expected_guided_sha = desired.get("guided_commission_sha256")
    if expected_guided_sha is None:
        if guided_manifest.exists() or guided_manifest.is_symlink():
            raise LaunchConflictError(
                "unexpected guided commissioning in output directory"
            )
    else:
        contained_guided = _contained_regular_file(
            output,
            guided_manifest,
            description="guided commissioning manifest",
        )
        from .mvp_guidance import MVPGuidedCommissioningPackage

        package = MVPGuidedCommissioningPackage.read(contained_guided)
        if package.package_sha256 != expected_guided_sha:
            raise LaunchConflictError(
                "guided commissioning differs from the requested contract"
            )


def _assert_unrecorded_output_is_compatible(
    output: Path,
    *,
    operator: Path,
    request: MVPLaunchRequest,
    hypothesis_text: str,
    instruction_text: str | None,
    guided_commission_sha256: str | None,
) -> None:
    launch_path = operator / LAUNCH_RECORD_NAME
    if launch_path.exists() or launch_path.is_symlink():
        raise LaunchConflictError("existing launch.json is malformed or unsafe")
    hypothesis_path = operator / HYPOTHESIS_FILE_NAME
    if hypothesis_path.exists() or hypothesis_path.is_symlink():
        contained = _contained_regular_file(
            output,
            hypothesis_path,
            description="stored hypothesis",
        )
        if contained.read_text() != hypothesis_text:
            raise LaunchConflictError("stored hypothesis differs from the requested contract")
    instruction_path = operator / INSTRUCTION_FILE_NAME
    if instruction_path.exists() or instruction_path.is_symlink():
        if instruction_text is None:
            raise LaunchConflictError("unexpected stored instruction in output directory")
        contained = _contained_regular_file(
            output,
            instruction_path,
            description="stored instruction",
        )
        if contained.read_text() != instruction_text:
            raise LaunchConflictError("stored instruction differs from the requested contract")

    manifest_path = output / "mvp_manifest.json"
    manifest = _load_secure_json(manifest_path, root=output)
    if manifest_path.exists() and manifest is None:
        raise LaunchConflictError("existing MVP manifest is malformed or unsafe")
    if manifest is not None:
        if manifest.get("hypothesis") != request.hypothesis or manifest.get(
            "campaign_instruction"
        ) != request.instruction:
            raise LaunchConflictError("MVP manifest belongs to a different hypothesis")
        config = manifest.get("config")
        expected_config = {
            "max_iterations": request.max_iterations,
            "max_wall_seconds": request.max_wall_seconds,
            "max_command_seconds": request.max_command_seconds,
            "max_workspace_bytes": request.max_workspace_mb * 1024 * 1024,
            "max_file_bytes": request.max_file_mb * 1024 * 1024,
            "max_memory_bytes": request.max_memory_mb * 1024 * 1024,
            "max_tool_output_chars": request.max_tool_output_chars,
            "command_heartbeat_seconds": request.command_heartbeat_seconds,
            "recent_full_turns": request.recent_full_turns,
            "max_model_retries": request.max_model_retries,
            "model_failover_after": request.model_failover_after,
        }
        if not isinstance(config, dict) or any(
            config.get(key) != value for key, value in expected_config.items()
        ):
            raise LaunchConflictError("MVP manifest has a different resource contract")
        existing_guided = manifest.get("guided_commissioning")
        existing_guided_sha = (
            existing_guided.get("package_sha256")
            if isinstance(existing_guided, dict) and existing_guided
            else None
        )
        if existing_guided_sha != guided_commission_sha256:
            raise LaunchConflictError(
                "MVP manifest has different guided commissioning"
            )
        from .mvp_skills import (
            MVPCapabilityRegistry,
            MVPSkillCatalog,
            discover_builtin_mvp_resources,
        )

        skills, capabilities = discover_builtin_mvp_resources()
        if request.skills_directory:
            skills = MVPSkillCatalog.discover(request.skills_directory)
        if request.capability_directory:
            capabilities = MVPCapabilityRegistry.discover(
                request.capability_directory
            )
        if manifest.get("skill_hashes") != skills.hashes or manifest.get(
            "capability_hashes"
        ) != capabilities.hashes:
            raise LaunchConflictError(
                "MVP manifest has different skill or capability identities"
            )
        return

    allowed_operator = {
        path.name
        for path in (hypothesis_path, instruction_path)
        if path.exists()
    }
    unexpected_operator = {
        path.name for path in operator.iterdir() if path.name not in allowed_operator
    }
    declared_top_level: set[str] = set()
    for value in (
        request.ledger,
        request.skills_directory,
        request.capability_directory,
    ):
        if value is None:
            continue
        resolved = Path(value).resolve()
        if resolved.is_relative_to(output) and resolved != output:
            declared_top_level.add(resolved.relative_to(output).parts[0])
    unexpected_output = {
        path.name
        for path in output.iterdir()
        if path != operator and path.name not in declared_top_level
    }
    if unexpected_operator or unexpected_output:
        raise LaunchConflictError(
            "refusing to initialize a non-empty directory without an MVP manifest"
        )


def _materialize_guided_package(package: Any, manifest_path: Path) -> None:
    if package.manifest_path == manifest_path:
        package.assert_identity()
        return
    destination = manifest_path.parent
    if destination.is_symlink():
        raise LaunchConflictError("guided commissioning destination must not be a symlink")
    if destination.exists() and any(destination.iterdir()):
        raise LaunchConflictError("guided commissioning destination is not empty")
    destination.mkdir(parents=True, exist_ok=True)
    _atomic_write_bytes(manifest_path, package.manifest_path.read_bytes())
    for record in package.file_records:
        target = destination / record.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.resolve().is_relative_to(destination.resolve()) is False:
            raise LaunchConflictError("guided commissioning file escapes its destination")
        _atomic_write_bytes(target, package.read_file(record.path))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _default_dsh_session_id(request: MVPLaunchRequest) -> str:
    identity = "\0".join(
        (
            request.campaign_id,
            str(Path(request.output_directory).expanduser().resolve()),
            _sha256_text(request.hypothesis),
        )
    )
    return f"simjecture-{hashlib.sha256(identity.encode()).hexdigest()[:24]}"


def _read_process_argv(pid: int) -> tuple[str, ...] | None:
    path = Path(f"/proc/{pid}/cmdline")
    try:
        encoded = path.read_bytes()
    except OSError:
        return None
    parts = encoded.rstrip(b"\0").split(b"\0") if encoded else []
    if not parts:
        return None
    return tuple(part.decode(errors="surrogateescape") for part in parts)


def _argv_targets_run(argv: tuple[str, ...], root: Path) -> bool:
    command = next((item for item in ("mvp", "dsh-run") if item in argv), None)
    if command is None:
        return False
    command_index = argv.index(command)
    prefix = argv[:command_index]
    module_entry = any(
        item == "-m" and index + 1 < len(prefix) and prefix[index + 1] == "conjecture_solver"
        for index, item in enumerate(prefix)
    )
    console_entry = any(
        Path(item).name in {"acs", "conjecture-solver", "simjecture"}
        for item in prefix
    )
    if not module_entry and not console_entry:
        return False
    output_value: str | None = None
    for index, item in enumerate(argv):
        if item == "--output" and index + 1 < len(argv):
            output_value = argv[index + 1]
            break
        if item.startswith("--output="):
            output_value = item.split("=", 1)[1]
            break
    if not output_value:
        return False
    try:
        return Path(output_value).expanduser().resolve() == root
    except OSError:
        return False


def _stat_fields(stat_text: str) -> list[str] | None:
    close = stat_text.rfind(")")
    if close < 0:
        return None
    return stat_text[close + 2 :].split()


def _starttime_from_stat(stat_text: str) -> str | None:
    fields = _stat_fields(stat_text)
    if fields is None or len(fields) < 20:
        return None
    return fields[19]


def _state_from_stat_path(pid: int) -> str | None:
    path = Path(f"/proc/{pid}/stat")
    if not path.is_file():
        return None
    try:
        fields = _stat_fields(path.read_text())
    except OSError:
        return None
    if not fields:
        return None
    return fields[0]


def _atomic_write_bytes(path: Path, encoded: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with suppress(FileNotFoundError):
            temporary.unlink()


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode())


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return repr(value)
