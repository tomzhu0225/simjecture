"""Small durable supervisor for local simulation jobs.

The MVP runner has a durable campaign transcript, but a simulation action also
needs a restart-safe process boundary.  This module keeps that boundary small:
one request, state, result, and verified supervisor record per job, plus an
operation-id index for idempotent submission.  A generic unreceipted process
remains ``outcome_unknown`` and is never rerun automatically; the campaign
kernel may promote that state only after validating its own authenticated
worker receipt.

Commands are executed directly as an argv tuple; no shell string is built.
Cancellation reuses the PID/start-time/argv verification and signal policy from
``mvp_launch``.  A stale or mismatched identity is therefore observable but
never signalled.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

try:  # pragma: no cover - exercised on POSIX in production/tests
    import fcntl
except ImportError:  # pragma: no cover - retained for importability on Windows
    fcntl = None  # type: ignore[assignment]

from pydantic import Field, model_validator

from .models import StrictModel, utc_now
from .mvp_launch import (
    ProcessIdentity,
    process_identity_matches,
    read_process_identity,
    request_graceful_cancel,
)

JOB_SCHEMA_VERSION = "0.1.0"
KERNEL_WORKER_SCHEMA_VERSION = "0.1.0"
REQUEST_FILE = "request.json"
STATE_FILE = "state.json"
RESULT_FILE = "result.json"
SUPERVISOR_FILE = "supervisor.json"
OPERATION_INDEX_FILE = "operation_index.json"
CAMPAIGN_LOCK_FILE = ".campaign-write.lock"


def kernel_worker_request_sha256(payload: Mapping[str, Any]) -> str:
    """Hash the immutable worker payload without its self-describing digest."""

    identity = dict(payload)
    identity.pop("worker_request_sha256", None)
    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def kernel_worker_result_path(request_path: str | Path) -> Path:
    """Return the durable receipt path paired with a kernel worker request."""

    path = Path(request_path)
    return path.with_suffix(".result.json")


class CampaignJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OUTCOME_UNKNOWN = "outcome_unknown"

    @property
    def terminal(self) -> bool:
        return self in {
            self.SUCCEEDED,
            self.FAILED,
            self.CANCELLED,
            self.OUTCOME_UNKNOWN,
        }


class CampaignJobRequest(StrictModel):
    """Immutable request identity persisted before a process is started."""

    schema_version: Literal["0.1.0"] = JOB_SCHEMA_VERSION
    operation_id: str = Field(min_length=1, max_length=256)
    argv: tuple[str, ...] = ()
    # ``command`` is accepted as a readable synonym for callers that model a
    # simulation action rather than a subprocess.  It is normalized into argv.
    command: tuple[str, ...] | None = None
    cwd: str | None = None
    env: dict[str, str] | None = None
    timeout_seconds: float = Field(default=600.0, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_command(self) -> CampaignJobRequest:
        if "\x00" in self.operation_id:
            raise ValueError("campaign job operation_id cannot contain NUL bytes")
        if not self.argv and self.command is None:
            raise ValueError("campaign job request requires a non-empty argv")
        if self.argv and self.command is not None and self.argv != self.command:
            raise ValueError("argv and command must match when both are supplied")
        selected = self.argv or self.command
        assert selected is not None
        if not all(isinstance(item, str) and item for item in selected):
            raise ValueError("campaign job argv entries must be non-empty strings")
        if any("\x00" in item for item in selected):
            raise ValueError("campaign job argv cannot contain NUL bytes")
        if self.cwd is not None:
            cwd = Path(self.cwd).expanduser().resolve()
            if not cwd.is_dir():
                raise ValueError(f"campaign job cwd is not a directory: {cwd}")
        if self.env is not None and any(
            not isinstance(key, str)
            or not key
            or "\x00" in key
            or not isinstance(value, str)
            or "\x00" in value
            for key, value in self.env.items()
        ):
            raise ValueError("campaign job environment contains an invalid entry")
        # ``StrictModel`` is frozen, but Pydantic's top-level ``__init__`` path
        # does not honor a validator returning a replacement instance.  Set the
        # two normalized fields explicitly so both constructor and JSON replay
        # follow the same identity without emitting a validator warning.
        object.__setattr__(self, "argv", tuple(selected))
        object.__setattr__(self, "command", None)
        return self

    @property
    def request_sha256(self) -> str:
        payload = self.model_dump(mode="json", exclude={"schema_version"})
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class CampaignJobState(StrictModel):
    """Durable lifecycle projection for one simulation job."""

    schema_version: Literal["0.1.0"] = JOB_SCHEMA_VERSION
    job_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: CampaignJobStatus
    created_at: datetime
    updated_at: datetime
    pid: int | None = Field(default=None, ge=1)
    cancellation_requested_at: datetime | None = None
    reconciliation_note: str | None = None


class CampaignJobResult(StrictModel):
    """Receipt written only when an outcome is known (or explicitly unknown)."""

    schema_version: Literal["0.1.0"] = JOB_SCHEMA_VERSION
    job_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    status: CampaignJobStatus
    outcome: CampaignJobStatus | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    started_at: datetime | None = None
    finished_at: datetime
    detail: str | None = None


class CampaignJobSupervisorRecord(StrictModel):
    """Verified process binding persisted separately from lifecycle state."""

    schema_version: Literal["0.1.0"] = JOB_SCHEMA_VERSION
    job_id: str = Field(min_length=1)
    operation_id: str = Field(min_length=1)
    identity: ProcessIdentity
    stdout_path: str = Field(min_length=1)
    stderr_path: str = Field(min_length=1)
    written_at: datetime


class JobConflictError(ValueError):
    """An operation id was reused for a different immutable request."""


class UnknownJobError(KeyError):
    """No durable job exists for the supplied id."""


class CampaignLockBusyError(RuntimeError):
    """Another process currently owns the campaign mutation lock."""


class CampaignInterprocessLock:
    """Advisory writer lock scoped to one campaign output directory.

    The lock lives beside the campaign's durable indexes rather than below
    ``jobs/``. Kernel action execution, journal updates, and worker spawn
    handshakes therefore share one writer boundary. Callers hold the context
    for the complete mutation.
    """

    def __init__(self, campaign_root: str | Path) -> None:
        self.root = Path(campaign_root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / CAMPAIGN_LOCK_FILE
        self._fd: int | None = None

    def acquire(self) -> CampaignInterprocessLock:
        if self._fd is not None:
            return self
        if fcntl is None:
            raise RuntimeError(
                "CampaignInterprocessLock requires a POSIX file-lock backend"
            )
        if self.path.is_symlink():
            raise ValueError("campaign writer lock must not be a symlink")
        fd = os.open(
            self.path,
            os.O_RDWR
            | os.O_CREAT
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as error:
            with suppress(OSError):
                os.close(fd)
            if isinstance(error, BlockingIOError) or getattr(error, "errno", None) in {
                11,
                13,
            }:
                raise CampaignLockBusyError(
                    f"campaign writer lock is held: {self.path}"
                ) from None
            raise
        self._fd = fd
        return self

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            if fcntl is not None:
                with suppress(OSError):
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            with suppress(OSError):
                os.close(fd)

    def __enter__(self) -> CampaignInterprocessLock:
        return self.acquire()

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.release()


class CampaignJobSupervisor:
    """Restart-safe local process supervisor.

    ``start`` is idempotent by ``operation_id``.  Reopening a supervisor from
    the same root only reads durable records; it never starts a process for an
    existing request.  A custom ``popen`` is accepted for deterministic tests
    and embedding, but production callers use ``subprocess.Popen``.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        popen: Any = subprocess.Popen,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs_root = self.root / "jobs"
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self.popen = popen
        self._processes: dict[str, Any] = {}
        self._streams: dict[str, tuple[Any, Any]] = {}
        self._operations = self._load_operation_index()

    # ---- public lifecycle -------------------------------------------------

    def start(
        self,
        request: CampaignJobRequest | Mapping[str, Any] | None = None,
        *,
        operation_id: str | None = None,
        argv: Sequence[str] | None = None,
        command: Sequence[str] | None = None,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_seconds: float = 600.0,
        metadata: Mapping[str, Any] | None = None,
    ) -> CampaignJobState:
        """Create or replay a job, starting at most one process.

        Callers may pass a typed request or convenient keyword fields.  A
        repeated operation id with byte-identical request fields returns its
        existing durable state; a different request raises ``JobConflictError``.
        """

        normalized = self._coerce_request(
            request,
            operation_id=operation_id,
            argv=argv,
            command=command,
            cwd=cwd,
            env=env,
            timeout_seconds=timeout_seconds,
            metadata=metadata,
        )
        existing_job_id = self._operations.get(normalized.operation_id)
        if existing_job_id is None:
            # Recover the idempotency key if a supervisor crashed after the
            # per-job request was durable but before operation_index.json was
            # replaced.  This scan never starts a discovered job.
            existing_job_id = self._find_operation_job(normalized.operation_id)
            if existing_job_id is not None:
                self._operations[normalized.operation_id] = existing_job_id
                self._persist_operation_index()
        if existing_job_id is not None:
            existing_request = self._load_request(existing_job_id)
            if existing_request.request_sha256 != normalized.request_sha256:
                raise JobConflictError(
                    f"operation_id {normalized.operation_id!r} already names a "
                    "different request"
                )
            return self.status(existing_job_id)

        job_id = "job_" + normalized.request_sha256[:32]
        job_dir = self._job_dir(job_id)
        if job_dir.exists():
            # A deterministic id collision is extraordinarily unlikely, but a
            # malformed leftover must not be silently reused.
            existing_request = self._load_request(job_id)
            if existing_request.request_sha256 != normalized.request_sha256:
                raise JobConflictError(f"job id collision for {job_id}")
            self._operations[normalized.operation_id] = job_id
            self._persist_operation_index()
            return self.status(job_id)

        job_dir.mkdir(parents=True, exist_ok=False)
        created = utc_now()
        self._write_request(job_id, normalized)
        state = CampaignJobState(
            job_id=job_id,
            operation_id=normalized.operation_id,
            request_sha256=normalized.request_sha256,
            status=CampaignJobStatus.QUEUED,
            created_at=created,
            updated_at=created,
        )
        self._write_state(state)
        self._operations[normalized.operation_id] = job_id
        self._persist_operation_index()

        stdout_path = job_dir / "stdout.log"
        stderr_path = job_dir / "stderr.log"
        stdout_handle = stdout_path.open("ab", buffering=0)
        stderr_handle = stderr_path.open("ab", buffering=0)
        try:
            popen_kwargs: dict[str, Any] = {
                "stdout": stdout_handle,
                "stderr": stderr_handle,
                "start_new_session": True,
            }
            if normalized.cwd is not None:
                popen_kwargs["cwd"] = str(Path(normalized.cwd).expanduser().resolve())
            if normalized.env is not None:
                popen_kwargs["env"] = dict(normalized.env)
            process = self.popen(list(normalized.argv), **popen_kwargs)
        except Exception as error:
            stdout_handle.close()
            stderr_handle.close()
            self._write_result(
                CampaignJobResult(
                    job_id=job_id,
                    operation_id=normalized.operation_id,
                    status=CampaignJobStatus.FAILED,
                    outcome=CampaignJobStatus.FAILED,
                    started_at=created,
                    finished_at=utc_now(),
                    detail=f"process start failed: {type(error).__name__}: {error}",
                )
            )
            self._write_state(
                state.model_copy(
                    update={
                        "status": CampaignJobStatus.FAILED,
                        "updated_at": utc_now(),
                        "reconciliation_note": "process failed before supervisor receipt",
                    }
                )
            )
            return self.status(job_id)

        identity = read_process_identity(
            process.pid,
            normalized.argv,
            run_directory=job_dir,
        )
        if identity is None:
            # Keep a durable binding even on platforms without /proc.  It is
            # intentionally unverified, so status/cancel will not signal it.
            identity = ProcessIdentity(
                pid=process.pid,
                starttime="unavailable",
                argv=tuple(normalized.argv),
                launched_at=utc_now().isoformat(),
                run_directory=str(job_dir),
            )
        supervisor = CampaignJobSupervisorRecord(
            job_id=job_id,
            operation_id=normalized.operation_id,
            identity=identity,
            stdout_path=stdout_path.name,
            stderr_path=stderr_path.name,
            written_at=utc_now(),
        )
        self._write_supervisor(supervisor)
        self._processes[job_id] = process
        self._streams[job_id] = (stdout_handle, stderr_handle)
        running = state.model_copy(
            update={
                "status": CampaignJobStatus.RUNNING,
                "updated_at": utc_now(),
                "pid": process.pid,
            }
        )
        self._write_state(running)
        return running

    def status(self, job_id: str) -> CampaignJobState:
        """Return and reconcile one durable job state."""

        state = self._load_state(job_id)
        if state.status.terminal:
            return state
        supervisor = self._load_supervisor(job_id)
        if supervisor is None:
            return self._mark_unknown(state, "missing supervisor receipt")

        process = self._processes.get(job_id)
        if process is not None:
            returncode = self._poll(process)
            if returncode is not None:
                # Only receipt a result for a process owned by this supervisor
                # instance.  A restarted supervisor has no such receipt and
                # intentionally takes the unknown path below.
                # ``Popen.poll`` is a receipt held by this supervisor instance;
                # process_identity_matches naturally becomes false after the
                # child is reaped.  A reopened supervisor has no process handle
                # and therefore takes the explicit outcome_unknown path below.
                return self._receipt_process_result(
                    state,
                    supervisor,
                    returncode,
                )
            if state.status not in {
                CampaignJobStatus.RUNNING,
                CampaignJobStatus.CANCEL_REQUESTED,
            }:
                state = state.model_copy(
                    update={"status": CampaignJobStatus.RUNNING, "updated_at": utc_now()}
                )
                self._write_state(state)
            return state

        verified = process_identity_matches(supervisor.identity)
        if not verified:
            return self._mark_unknown(
                state,
                "process identity is absent, dead, or no longer matches pid/starttime/argv",
            )
        if state.status not in {
            CampaignJobStatus.RUNNING,
            CampaignJobStatus.CANCEL_REQUESTED,
        }:
            state = state.model_copy(
                update={"status": CampaignJobStatus.RUNNING, "updated_at": utc_now()}
            )
            self._write_state(state)
        return state

    def cancel(
        self,
        job_id: str,
        *,
        wait_interrupt_seconds: float = 20.0,
        wait_terminate_seconds: float = 10.0,
        sleep: Any = time.sleep,
    ) -> CampaignJobState:
        """Request cancellation only after verifying process identity."""

        state = self._load_state(job_id)
        if state.status.terminal:
            return state
        supervisor = self._load_supervisor(job_id)
        if supervisor is None or not process_identity_matches(supervisor.identity):
            return self._mark_unknown(
                state,
                "cancel refused: process identity does not match; no signal sent",
            )
        requested = state.model_copy(
            update={
                "status": CampaignJobStatus.CANCEL_REQUESTED,
                "updated_at": utc_now(),
                "cancellation_requested_at": utc_now(),
            }
        )
        self._write_state(requested)
        # request_graceful_cancel performs its own check immediately before
        # each signal and will not signal a reused PID.
        detail = request_graceful_cancel(
            supervisor.identity,
            wait_interrupt_seconds=wait_interrupt_seconds,
            wait_terminate_seconds=wait_terminate_seconds,
            sleep=sleep,
        )
        if detail in {"interrupted", "terminated"}:
            # A fresh supervisor has no Popen object to reap, but the signal
            # helper verified the durable pid/starttime/argv identity before
            # signalling and observed that exact identity disappear. Persist
            # that known administrative outcome instead of degrading it to an
            # unactionable unknown state after an MCP restart.
            return self._receipt_verified_cancellation(
                requested,
                supervisor,
                detail=detail,
            )
        current = self.status(job_id)
        if current.status in {CampaignJobStatus.RUNNING, CampaignJobStatus.CANCEL_REQUESTED}:
            current = current.model_copy(
                update={"status": CampaignJobStatus.CANCEL_REQUESTED, "reconciliation_note": detail}
            )
            self._write_state(current)
        return current

    def reopen(self) -> CampaignJobSupervisor:
        """Return a fresh read-only process view over the same durable root."""

        return type(self)(self.root, popen=self.popen)

    def jobs(self) -> tuple[CampaignJobState, ...]:
        """List durable jobs without starting or rerunning any process."""

        states: list[CampaignJobState] = []
        for path in sorted(self.jobs_root.glob(f"*/{STATE_FILE}")):
            with suppress(ValueError, OSError):
                states.append(CampaignJobState.model_validate_json(path.read_text()))
        return tuple(states)

    # Front-end naming aliases mirror CampaignKernel/MCP without creating a
    # second lifecycle implementation.
    start_job = start
    job_status = status
    cancel_job = cancel
    reconcile = status

    # ---- durable record helpers ------------------------------------------

    def request_record(self, job_id: str) -> CampaignJobRequest:
        return self._load_request(job_id)

    def result_record(self, job_id: str) -> CampaignJobResult | None:
        path = self._job_dir(job_id) / RESULT_FILE
        if path.is_symlink() or not path.is_file():
            return None
        return CampaignJobResult.model_validate_json(path.read_text())

    def supervisor_record(self, job_id: str) -> CampaignJobSupervisorRecord | None:
        return self._load_supervisor(job_id)

    def accept_external_result(
        self,
        job_id: str,
        *,
        returncode: int,
        detail: str,
        receipt_text: str = "",
    ) -> CampaignJobState:
        """Promote an unknown process outcome using a validated worker receipt.

        The scientific kernel validates the receipt against its immutable
        worker-request digest before calling this method.  Restricting the
        transition to ``outcome_unknown`` prevents an external receipt from
        replacing a normal supervisor-owned result.
        """

        state = self._load_state(job_id)
        if state.status != CampaignJobStatus.OUTCOME_UNKNOWN:
            raise ValueError(
                "an external result can only reconcile an outcome_unknown job"
            )
        supervisor = self._load_supervisor(job_id)
        stdout = ""
        stderr = ""
        if supervisor is not None:
            job_dir = self._job_dir(job_id)
            stdout = self._read_log(job_dir / supervisor.stdout_path)
            stderr = self._read_log(job_dir / supervisor.stderr_path)
        if receipt_text and receipt_text not in stdout:
            stdout = f"{stdout.rstrip()}\n{receipt_text}\n" if stdout else receipt_text + "\n"
        status = (
            CampaignJobStatus.CANCELLED
            if state.cancellation_requested_at is not None
            else CampaignJobStatus.SUCCEEDED
            if returncode == 0
            else CampaignJobStatus.FAILED
        )
        finished = utc_now()
        self._write_result(
            CampaignJobResult(
                job_id=state.job_id,
                operation_id=state.operation_id,
                status=status,
                outcome=status,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                started_at=state.created_at,
                finished_at=finished,
                detail=detail,
            )
        )
        updated = state.model_copy(
            update={
                "status": status,
                "updated_at": finished,
                "reconciliation_note": detail,
            }
        )
        self._write_state(updated)
        return updated

    def reject_unverified_success(self, job_id: str, *, detail: str) -> CampaignJobState:
        """Downgrade a process-level success lacking a valid worker receipt.

        A zero process return code is not by itself proof that the typed
        scientific action completed.  The kernel calls this narrow transition
        only for its own worker jobs after receipt authentication fails.
        """

        state = self._load_state(job_id)
        if state.status != CampaignJobStatus.SUCCEEDED:
            return state
        previous = self.result_record(job_id)
        finished = utc_now()
        self._write_result(
            CampaignJobResult(
                job_id=state.job_id,
                operation_id=state.operation_id,
                status=CampaignJobStatus.OUTCOME_UNKNOWN,
                outcome=CampaignJobStatus.OUTCOME_UNKNOWN,
                returncode=previous.returncode if previous is not None else None,
                stdout=previous.stdout if previous is not None else "",
                stderr=previous.stderr if previous is not None else "",
                timed_out=previous.timed_out if previous is not None else False,
                started_at=(previous.started_at if previous is not None else state.created_at),
                finished_at=finished,
                detail=detail,
            )
        )
        updated = state.model_copy(
            update={
                "status": CampaignJobStatus.OUTCOME_UNKNOWN,
                "updated_at": finished,
                "reconciliation_note": detail,
            }
        )
        self._write_state(updated)
        return updated

    def _coerce_request(
        self,
        request: CampaignJobRequest | Mapping[str, Any] | None,
        *,
        operation_id: str | None,
        argv: Sequence[str] | None,
        command: Sequence[str] | None,
        cwd: str | Path | None,
        env: Mapping[str, str] | None,
        timeout_seconds: float,
        metadata: Mapping[str, Any] | None,
    ) -> CampaignJobRequest:
        if request is not None:
            if any(
                value is not None
                for value in (operation_id, argv, command, cwd, env, metadata)
            ):
                raise TypeError("request cannot be combined with request keyword fields")
            return (
                request
                if isinstance(request, CampaignJobRequest)
                else CampaignJobRequest.model_validate(request)
            )
        if operation_id is None:
            raise TypeError("operation_id is required when request is omitted")
        selected = tuple(argv or command or ())
        return CampaignJobRequest(
            operation_id=operation_id,
            argv=selected,
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
            timeout_seconds=timeout_seconds,
            metadata=dict(metadata or {}),
        )

    def _job_dir(self, job_id: str) -> Path:
        if not job_id or "/" in job_id or "\\" in job_id or job_id in {".", ".."}:
            raise ValueError("invalid campaign job id")
        return self.jobs_root / job_id

    def _load_operation_index(self) -> dict[str, str]:
        path = self.root / OPERATION_INDEX_FILE
        if not path.is_file():
            return {}
        payload = json.loads(path.read_text())
        if payload.get("schema_version") != JOB_SCHEMA_VERSION:
            raise ValueError("invalid campaign job operation index schema")
        operations = payload.get("operations")
        if not isinstance(operations, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in operations.items()
        ):
            raise ValueError("invalid campaign job operation index")
        return dict(operations)

    def _find_operation_job(self, operation_id: str) -> str | None:
        for request_path in sorted(self.jobs_root.glob(f"*/{REQUEST_FILE}")):
            if request_path.is_symlink():
                continue
            with suppress(OSError, ValueError):
                request = CampaignJobRequest.model_validate_json(request_path.read_text())
                if request.operation_id == operation_id:
                    return request_path.parent.name
        return None

    def _persist_operation_index(self) -> None:
        self._atomic_write(
            self.root / OPERATION_INDEX_FILE,
            {"schema_version": JOB_SCHEMA_VERSION, "operations": self._operations},
        )

    def _load_request(self, job_id: str) -> CampaignJobRequest:
        path = self._job_dir(job_id) / REQUEST_FILE
        if path.is_symlink() or not path.is_file():
            raise UnknownJobError(job_id)
        return CampaignJobRequest.model_validate_json(path.read_text())

    def _load_state(self, job_id: str) -> CampaignJobState:
        path = self._job_dir(job_id) / STATE_FILE
        if path.is_symlink() or not path.is_file():
            raise UnknownJobError(job_id)
        return CampaignJobState.model_validate_json(path.read_text())

    def _load_supervisor(self, job_id: str) -> CampaignJobSupervisorRecord | None:
        path = self._job_dir(job_id) / SUPERVISOR_FILE
        if path.is_symlink() or not path.is_file():
            return None
        with suppress(OSError, ValueError):
            record = CampaignJobSupervisorRecord.model_validate_json(path.read_text())
            request = self._load_request(job_id)
            identity = record.identity
            # The supervisor receipt is trusted only when its immutable job and
            # command identity agree with the request it is meant to supervise.
            # In particular, a crafted receipt cannot turn this job into a
            # handle for an unrelated process.
            job_dir = self._job_dir(job_id)
            stdout_path = Path(record.stdout_path)
            stderr_path = Path(record.stderr_path)
            if not stdout_path.is_absolute():
                stdout_path = (job_dir / stdout_path).resolve()
            if not stderr_path.is_absolute():
                stderr_path = (job_dir / stderr_path).resolve()
            if (
                record.job_id != job_id
                or record.operation_id != request.operation_id
                or identity.argv != request.argv
                or identity.run_directory != str(job_dir)
                or not stdout_path.is_relative_to(job_dir)
                or not stderr_path.is_relative_to(job_dir)
            ):
                return None
            return record
        return None

    def _write_request(self, job_id: str, request: CampaignJobRequest) -> None:
        self._atomic_write(self._job_dir(job_id) / REQUEST_FILE, request.model_dump(mode="json"))

    def _write_state(self, state: CampaignJobState) -> None:
        self._atomic_write(self._job_dir(state.job_id) / STATE_FILE, state.model_dump(mode="json"))

    def _write_supervisor(self, supervisor: CampaignJobSupervisorRecord) -> None:
        self._atomic_write(
            self._job_dir(supervisor.job_id) / SUPERVISOR_FILE,
            supervisor.model_dump(mode="json"),
        )

    def _write_result(self, result: CampaignJobResult) -> None:
        self._atomic_write(
            self._job_dir(result.job_id) / RESULT_FILE,
            result.model_dump(mode="json"),
        )

    @staticmethod
    def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
        encoded = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
        with temporary.open("w") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    def _mark_unknown(self, state: CampaignJobState, note: str) -> CampaignJobState:
        if state.status.terminal and state.status != CampaignJobStatus.OUTCOME_UNKNOWN:
            return state
        updated = state.model_copy(
            update={
                "status": CampaignJobStatus.OUTCOME_UNKNOWN,
                "updated_at": utc_now(),
                "reconciliation_note": note,
            }
        )
        self._write_state(updated)
        if self.result_record(state.job_id) is None:
            self._write_result(
                CampaignJobResult(
                    job_id=state.job_id,
                    operation_id=state.operation_id,
                    status=CampaignJobStatus.OUTCOME_UNKNOWN,
                    outcome=CampaignJobStatus.OUTCOME_UNKNOWN,
                    started_at=state.created_at,
                    finished_at=utc_now(),
                    detail=note,
                )
            )
        return updated

    def _receipt_process_result(
        self,
        state: CampaignJobState,
        supervisor: CampaignJobSupervisorRecord,
        returncode: int,
    ) -> CampaignJobState:
        handles = self._streams.pop(state.job_id, ())
        for handle in handles:
            with suppress(OSError):
                handle.close()
        stdout = self._read_log(self._job_dir(state.job_id) / supervisor.stdout_path)
        stderr = self._read_log(self._job_dir(state.job_id) / supervisor.stderr_path)
        status = (
            CampaignJobStatus.CANCELLED
            if state.cancellation_requested_at is not None
            else CampaignJobStatus.SUCCEEDED
            if returncode == 0
            else CampaignJobStatus.FAILED
        )
        result = CampaignJobResult(
            job_id=state.job_id,
            operation_id=state.operation_id,
            status=status,
            outcome=status,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            started_at=state.created_at,
            finished_at=utc_now(),
        )
        self._write_result(result)
        updated = state.model_copy(
            update={"status": status, "updated_at": result.finished_at}
        )
        self._write_state(updated)
        return updated

    def _receipt_verified_cancellation(
        self,
        state: CampaignJobState,
        supervisor: CampaignJobSupervisorRecord,
        *,
        detail: str,
    ) -> CampaignJobState:
        """Receipt a verified signal-and-death cancellation without Popen."""

        process = self._processes.pop(state.job_id, None)
        returncode = None
        if process is not None:
            with suppress(Exception):
                returncode = process.wait(timeout=0)
        handles = self._streams.pop(state.job_id, ())
        for handle in handles:
            with suppress(OSError):
                handle.close()
        job_dir = self._job_dir(state.job_id)
        finished = utc_now()
        self._write_result(
            CampaignJobResult(
                job_id=state.job_id,
                operation_id=state.operation_id,
                status=CampaignJobStatus.CANCELLED,
                outcome=CampaignJobStatus.CANCELLED,
                returncode=returncode,
                stdout=self._read_log(job_dir / supervisor.stdout_path),
                stderr=self._read_log(job_dir / supervisor.stderr_path),
                started_at=state.created_at,
                finished_at=finished,
                detail=f"verified cancellation: {detail}",
            )
        )
        updated = state.model_copy(
            update={
                "status": CampaignJobStatus.CANCELLED,
                "updated_at": finished,
                "reconciliation_note": f"verified cancellation: {detail}",
            }
        )
        self._write_state(updated)
        return updated

    @staticmethod
    def _poll(process: Any) -> int | None:
        with suppress(Exception):
            return process.poll()
        return None

    @staticmethod
    def _read_log(path: Path) -> str:
        with suppress(OSError):
            return path.read_text(errors="replace")
        return ""


# Compatibility aliases make the small supervisor easy to discover from
# front-ends that call it a store or a job manager.
CampaignJobStore = CampaignJobSupervisor
JobSupervisor = CampaignJobSupervisor
