"""Permanently non-evidentiary health check for a local Optab capability.

Copies the operator-prepared input tree, launches Optab, and reads back HDF5.
This checks process wiring only; it does not validate an opacity model.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

SUMMARY_NAME = "optab_capability_smoke.json"
STDOUT_NAME = "optab_capability_smoke.stdout.log"
STDERR_NAME = "optab_capability_smoke.stderr.log"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_path(variable: str) -> Path:
    value = os.environ.get(variable, "")
    if not value:
        raise ValueError(f"{variable} is not set")
    return Path(value).expanduser().resolve()


def _copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=False)


def _inspect_hdf5(paths: list[Path]) -> tuple[list[dict[str, Any]], str | None]:
    try:
        h5py = importlib.import_module("h5py")
    except ImportError as exc:
        return [], f"h5py is unavailable: {exc}"
    records: list[dict[str, Any]] = []
    try:
        for path in paths:
            if not h5py.is_hdf5(path):
                continue
            with h5py.File(path, "r") as handle:
                keys = sorted(str(key) for key in handle)
                records.append(
                    {
                        "path": str(path.relative_to(Path.cwd())),
                        "size_bytes": path.stat().st_size,
                        "root_keys": keys,
                        "root_key_count": len(keys),
                    }
                )
    except (OSError, ValueError) as exc:
        return records, f"HDF5 readback failed: {exc}"
    return records, None


def main() -> int:
    workspace = Path.cwd().resolve()
    summary_path = workspace / SUMMARY_NAME
    stdout_path = workspace / STDOUT_NAME
    stderr_path = workspace / STDERR_NAME
    checks = {
        "environment_valid": False,
        "executable_present": False,
        "mpi_launcher_present": False,
        "input_present": False,
        "input_copied": False,
        "process_completed": False,
        "return_code_zero": False,
        "hdf5_output_created": False,
        "hdf5_output_readable": False,
    }
    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "kind": "optab_capability_smoke",
        "scientific_status": "permanently_non_evidentiary",
        "checks": checks,
        "command": [],
        "elapsed_seconds": 0.0,
        "error": None,
        "return_code": None,
        "timed_out": False,
        "hdf5_outputs": [],
    }
    start = time.monotonic()
    try:
        executable = _required_path("OPTAB_EXECUTABLE")
        launcher = _required_path("OPTAB_MPI_LAUNCHER")
        source_input = _required_path("OPTAB_PREFLIGHT_INPUT")
        ranks = int(os.environ["OPTAB_MPI_RANKS"])
        timeout = float(os.environ.get("OPTAB_PREFLIGHT_TIMEOUT_SECONDS", "120"))
        if ranks < 1:
            raise ValueError("OPTAB_MPI_RANKS must be positive")
        if timeout <= 0:
            raise ValueError("OPTAB_PREFLIGHT_TIMEOUT_SECONDS must be positive")
        checks["environment_valid"] = True
        checks["executable_present"] = executable.is_file() and os.access(
            executable, os.X_OK
        )
        checks["mpi_launcher_present"] = launcher.is_file() and os.access(
            launcher, os.X_OK
        )
        checks["input_present"] = source_input.is_dir()
        payload["executable_sha256"] = (
            _sha256(executable) if checks["executable_present"] else None
        )
        if not all(
            checks[name]
            for name in ("executable_present", "mpi_launcher_present", "input_present")
        ):
            raise ValueError(
                "the configured executable, launcher, or preflight input is unavailable"
            )
        _copy_tree(source_input, workspace / "input")
        (workspace / "output").mkdir(exist_ok=True)
        checks["input_copied"] = (workspace / "input").is_dir()
        command = [str(launcher), "-np", str(ranks), str(executable)]
        payload["command"] = command
        try:
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                completed = subprocess.run(
                    command,
                    cwd=workspace,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=timeout,
                    check=False,
                )
            payload["return_code"] = completed.returncode
            checks["process_completed"] = True
            checks["return_code_zero"] = completed.returncode == 0
        except subprocess.TimeoutExpired:
            payload["timed_out"] = True
            payload["error"] = "Optab runtime smoke exceeded its timeout"
        hdf5_paths = sorted((workspace / "output").rglob("*"))
        hdf5_outputs, hdf5_error = _inspect_hdf5(
            [path for path in hdf5_paths if path.is_file()]
        )
        payload["hdf5_outputs"] = hdf5_outputs
        checks["hdf5_output_created"] = bool(hdf5_outputs)
        checks["hdf5_output_readable"] = bool(hdf5_outputs) and hdf5_error is None
        if hdf5_error and payload["error"] is None:
            payload["error"] = hdf5_error
    except (KeyError, OSError, ValueError) as exc:
        payload["error"] = str(exc)

    checks["completed"] = all(checks.values())
    payload["elapsed_seconds"] = time.monotonic() - start
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if checks["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
