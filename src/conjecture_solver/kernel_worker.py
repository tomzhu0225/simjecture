"""One-shot process entry point for durable CampaignKernel actions.

The durable job supervisor launches this module as the detached, restart-safe
process boundary.  The worker opens the campaign from its immutable
manifest/operator input, parses exactly one typed action, and executes it
through :meth:`CampaignKernel.execute_operation`; the kernel then creates the same
Bubblewrap child used by synchronous MVP execution.  It never accepts a shell
string and it emits one bounded JSON receipt on stdout for the job supervisor
log.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from .campaign_jobs import (
    KERNEL_WORKER_SCHEMA_VERSION,
    CampaignJobRequest,
    CampaignJobState,
    CampaignJobSupervisorRecord,
    CampaignLockBusyError,
    kernel_worker_request_sha256,
    kernel_worker_result_path,
)
from .campaign_kernel import CampaignKernel
from .mvp_agent import parse_mvp_action
from .mvp_launch import read_process_identity


def _open_campaign_after_handshake(
    campaign_root: Path,
    *,
    timeout_seconds: float = 30.0,
) -> CampaignKernel:
    """Wait for the spawning supervisor to release its short writer lock."""

    deadline = time.monotonic() + max(0.1, timeout_seconds)
    while True:
        try:
            return CampaignKernel.open(workspace=campaign_root)
        except CampaignLockBusyError:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "campaign writer lock remained held after worker handshake"
                ) from None
            time.sleep(0.01)


def _action_result_succeeded(result: Any) -> bool:
    """Interpret existing synchronous execution receipts for async lifecycle."""

    if not isinstance(result, dict):
        return True
    execution = result.get("execution_result")
    if isinstance(execution, dict) and not _action_result_succeeded(execution):
        return False
    return not (
        result.get("timed_out") is True
        or result.get("workspace_exceeded") is True
        or (
            isinstance(result.get("returncode"), int)
            and result["returncode"] != 0
        )
    )


def _load_worker_request(
    request_path: str | Path,
    *,
    campaign: str | Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    """Load and authenticate one host-written worker request."""

    raw_path = Path(request_path).expanduser()
    if raw_path.is_symlink():
        raise ValueError("kernel worker request must not be a symlink")
    path = raw_path.resolve()
    if not path.is_file():
        raise ValueError("kernel worker request is not a regular file")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("kernel worker request must be a JSON object")
    if payload.get("schema_version") != KERNEL_WORKER_SCHEMA_VERSION:
        raise ValueError("kernel worker request has an unsupported schema version")
    recorded_digest = payload.get("worker_request_sha256")
    if (
        not isinstance(recorded_digest, str)
        or len(recorded_digest) != 64
        or recorded_digest != kernel_worker_request_sha256(payload)
    ):
        raise ValueError("kernel worker request digest does not match")
    root = campaign or payload.get("campaign")
    if root is None:
        raise ValueError("kernel worker request is missing campaign")
    campaign_root = Path(root).expanduser().resolve()
    if not path.is_relative_to(campaign_root / "kernel_jobs"):
        raise ValueError("kernel worker request is outside campaign kernel_jobs")
    return path, campaign_root, payload


def _await_worker_handshake(
    handshake_path: str | Path,
    *,
    request_path: Path,
    campaign_root: Path,
    timeout_seconds: float = 30.0,
) -> str:
    """Wait until the supervisor's identity and running state are durable."""

    raw = Path(handshake_path).expanduser()
    if raw.is_symlink():
        raise ValueError("kernel worker handshake must not be a symlink")
    path = raw.resolve()
    kernel_jobs = (campaign_root / "kernel_jobs").resolve()
    if not path.is_relative_to(kernel_jobs):
        raise ValueError("kernel worker handshake is outside campaign kernel_jobs")
    deadline = time.monotonic() + max(0.1, float(timeout_seconds))
    while time.monotonic() < deadline:
        if path.is_file() and not path.is_symlink():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict):
                return _validate_worker_handshake(
                    payload,
                    handshake_path=path,
                    request_path=request_path,
                    campaign_root=campaign_root,
                )
        time.sleep(0.01)
    raise TimeoutError("kernel worker supervisor handshake was not durable")


def _validate_worker_handshake(
    payload: dict[str, Any],
    *,
    handshake_path: Path,
    request_path: Path,
    campaign_root: Path,
) -> str:
    if payload.get("schema_version") != KERNEL_WORKER_SCHEMA_VERSION:
        raise ValueError("kernel worker handshake has an unsupported schema version")
    job_id = payload.get("job_id")
    operation_id = payload.get("operation_id")
    if not isinstance(job_id, str) or not isinstance(operation_id, str):
        raise ValueError("kernel worker handshake is missing job identity")
    recorded_request = Path(str(payload.get("request_path", ""))).expanduser()
    if recorded_request.is_symlink() or recorded_request.resolve() != request_path.resolve():
        raise ValueError("kernel worker handshake request path does not match")
    if payload.get("request_sha256") is None or payload.get("worker_request_sha256") is None:
        raise ValueError("kernel worker handshake is missing request identity")
    # CampaignJobSupervisor receives ``campaign/jobs`` as its root and keeps
    # per-job records below its own ``jobs/`` child.
    job_dir = (campaign_root / "jobs" / "jobs" / job_id).resolve()
    state_path = job_dir / "state.json"
    supervisor_path = job_dir / "supervisor.json"
    if not job_dir.is_relative_to(campaign_root) or any(
        path.is_symlink() for path in (state_path, supervisor_path)
    ):
        raise ValueError("kernel worker handshake job paths are unsafe")
    if not state_path.is_file() or not supervisor_path.is_file():
        raise ValueError("kernel worker supervisor records are not durable")
    state = CampaignJobState.model_validate_json(state_path.read_text(encoding="utf-8"))
    supervisor = CampaignJobSupervisorRecord.model_validate_json(
        supervisor_path.read_text(encoding="utf-8")
    )
    supervisor_request_path = job_dir / "request.json"
    if supervisor_request_path.is_symlink() or not supervisor_request_path.is_file():
        raise ValueError("kernel worker supervisor request is not durable")
    request = CampaignJobRequest.model_validate_json(
        supervisor_request_path.read_text(encoding="utf-8")
    )
    try:
        worker_payload = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("kernel worker request is not valid JSON") from error
    if not isinstance(worker_payload, dict):
        raise ValueError("kernel worker request is not an object")
    if (
        state.job_id != job_id
        or state.operation_id != operation_id
        or state.status.value != "running"
        or payload.get("state_status") != "running"
        or state.pid != os.getpid()
        or supervisor.job_id != job_id
        or supervisor.operation_id != operation_id
        or supervisor.identity.run_directory != str(job_dir)
        or request.operation_id != operation_id
        or request.request_sha256 != payload.get("request_sha256")
        or worker_payload.get("operation_id") != operation_id
        or worker_payload.get("worker_request_sha256")
        != payload.get("worker_request_sha256")
        or kernel_worker_request_sha256(worker_payload)
        != payload.get("worker_request_sha256")
        or tuple(request.argv) != tuple(supervisor.identity.argv)
    ):
        raise ValueError("kernel worker supervisor handshake identity mismatch")
    identity = supervisor.identity
    if identity.pid != os.getpid() or identity.starttime == "unavailable":
        raise ValueError("kernel worker supervisor PID identity is unverifiable")
    actual = read_process_identity(os.getpid(), identity.argv, run_directory=job_dir)
    if (
        actual is None
        or actual.starttime != identity.starttime
        or actual.argv != identity.argv
    ):
        raise ValueError("kernel worker process identity does not match supervisor receipt")
    # The handshake itself must remain inside kernel_jobs and paired with the
    # request name; this rejects a copied gate from another campaign.
    if handshake_path.parent != request_path.parent:
        raise ValueError("kernel worker handshake is not paired with its request")
    return job_id


def execute_worker_request(
    request_path: str | Path,
    *,
    campaign: str | Path | None = None,
    handshake: str | Path | None = None,
) -> dict[str, Any]:
    """Read and execute one durable typed action request."""

    path, campaign_root, payload = _load_worker_request(
        request_path,
        campaign=campaign,
    )
    job_id = None
    if handshake is not None:
        job_id = _await_worker_handshake(
            handshake,
            request_path=path,
            campaign_root=campaign_root,
        )
    action_payload = payload.get("action")
    if not isinstance(action_payload, dict):
        raise ValueError("kernel worker request is missing an action object")
    action = parse_mvp_action(json.dumps(action_payload, separators=(",", ":")))
    timeout_seconds = payload.get("timeout_seconds")
    if timeout_seconds is not None and (
        isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float))
    ):
        raise ValueError("kernel worker timeout_seconds must be numeric or null")
    kernel = _open_campaign_after_handshake(campaign_root)
    operation_id = payload.get("operation_id")
    if not isinstance(operation_id, str) or not operation_id:
        raise ValueError("kernel worker request is missing operation_id")
    result = kernel.execute_operation(
        operation_id,
        action,
        timeout_seconds=(float(timeout_seconds) if timeout_seconds is not None else None),
        _job_id=job_id,
        _defer_provenance=True,
    )
    return {
        "ok": _action_result_succeeded(result),
        "action_executed": True,
        "schema_version": KERNEL_WORKER_SCHEMA_VERSION,
        "worker_request_sha256": payload["worker_request_sha256"],
        "operation_id": payload.get("operation_id"),
        "action": action.action.value,
        "result": result,
    }


def _persist_worker_receipt(
    request_path: str | Path,
    receipt: dict[str, Any],
    *,
    campaign: str | Path | None = None,
) -> Path:
    """Atomically persist a receipt next to its authenticated request."""

    path, _campaign_root, payload = _load_worker_request(
        request_path,
        campaign=campaign,
    )
    action_payload = payload.get("action")
    action_name = action_payload.get("action") if isinstance(action_payload, dict) else None
    durable = {
        **receipt,
        "schema_version": KERNEL_WORKER_SCHEMA_VERSION,
        "worker_request_sha256": payload["worker_request_sha256"],
        "operation_id": payload.get("operation_id"),
        "action": action_name,
    }
    if durable.get("ok") is True and durable.get("action_executed") is not True:
        raise ValueError("a successful worker receipt must record action execution")
    target = kernel_worker_result_path(path)
    temporary = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    encoded = json.dumps(
        durable,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        default=str,
    ) + "\n"
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute one durable campaign action")
    parser.add_argument("--request", required=True)
    parser.add_argument("--campaign")
    parser.add_argument("--handshake")
    args = parser.parse_args(argv)
    try:
        result = execute_worker_request(
            args.request,
            campaign=args.campaign,
            handshake=args.handshake,
        )
    except Exception as error:
        result = {
            "ok": False,
            "action_executed": False,
            "error": f"{type(error).__name__}: {error}",
        }
    try:
        _persist_worker_receipt(args.request, result, campaign=args.campaign)
    except Exception as receipt_error:
        result = {
            **result,
            "ok": False,
            "receipt_error": f"{type(receipt_error).__name__}: {receipt_error}",
        }
        print(json.dumps(result, sort_keys=True), flush=True)
        return 1
    print(json.dumps(result, sort_keys=True, default=str), flush=True)
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":  # pragma: no cover - exercised through subprocesses
    sys.exit(main())
