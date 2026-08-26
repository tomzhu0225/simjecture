"""Permanently non-evidentiary health check for a local FLASH capability.

The capability supplies a FLASH executable, MPI launcher, rank count, and an
operator-prepared parameter file through environment variables. This script
checks process wiring and HDF5 readback only; it does not validate a physical
model or scientific result.
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

SUMMARY_NAME = "flash_mhd_capability_smoke.json"
PARFILE_NAME = "flash_mhd_capability_smoke.par"
STDOUT_NAME = "flash_mhd_capability_smoke.stdout.log"
STDERR_NAME = "flash_mhd_capability_smoke.stderr.log"


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


def _file_state(root: Path) -> dict[str, tuple[int, int]]:
    excluded = {SUMMARY_NAME, PARFILE_NAME, STDOUT_NAME, STDERR_NAME}
    state: dict[str, tuple[int, int]] = {}
    for path in root.iterdir():
        if not path.is_file() or path.name in excluded:
            continue
        stat = path.stat()
        state[path.name] = (stat.st_size, stat.st_mtime_ns)
    return state


def _fresh_files(root: Path, before: dict[str, tuple[int, int]]) -> list[Path]:
    fresh: list[Path] = []
    excluded = {SUMMARY_NAME, PARFILE_NAME, STDOUT_NAME, STDERR_NAME}
    for path in root.iterdir():
        if not path.is_file() or path.name in excluded:
            continue
        stat = path.stat()
        if before.get(path.name) != (stat.st_size, stat.st_mtime_ns):
            fresh.append(path)
    return sorted(fresh)


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
                        "path": path.name,
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
    copied_parfile = workspace / PARFILE_NAME
    stdout_path = workspace / STDOUT_NAME
    stderr_path = workspace / STDERR_NAME

    checks = {
        "environment_valid": False,
        "executable_present": False,
        "mpi_launcher_present": False,
        "parameter_file_present": False,
        "parameter_file_copied": False,
        "process_completed": False,
        "return_code_zero": False,
        "hdf5_output_created": False,
        "hdf5_output_readable": False,
    }
    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "kind": "flash_mhd_capability_smoke",
        "scientific_status": "permanently_non_evidentiary",
        "checks": checks,
        "command": [],
        "elapsed_seconds": 0.0,
        "error": None,
        "return_code": None,
        "timed_out": False,
        "fresh_files": [],
        "hdf5_outputs": [],
    }

    start = time.monotonic()
    before = _file_state(workspace)
    try:
        executable = _required_path("FLASH_EXECUTABLE")
        launcher = _required_path("FLASH_MPI_LAUNCHER")
        source_parfile = _required_path("FLASH_PREFLIGHT_PARFILE")
        ranks = int(os.environ["FLASH_MPI_RANKS"])
        timeout = float(os.environ.get("FLASH_PREFLIGHT_TIMEOUT_SECONDS", "120"))
        if ranks < 1:
            raise ValueError("FLASH_MPI_RANKS must be positive")
        if timeout <= 0:
            raise ValueError("FLASH_PREFLIGHT_TIMEOUT_SECONDS must be positive")
        checks["environment_valid"] = True

        checks["executable_present"] = executable.is_file() and os.access(
            executable,
            os.X_OK,
        )
        checks["mpi_launcher_present"] = launcher.is_file() and os.access(
            launcher,
            os.X_OK,
        )
        checks["parameter_file_present"] = source_parfile.is_file()
        payload["executable_sha256"] = (
            _sha256(executable) if checks["executable_present"] else None
        )
        payload["source_parameter_sha256"] = (
            _sha256(source_parfile) if checks["parameter_file_present"] else None
        )

        if not all(
            checks[name]
            for name in (
                "executable_present",
                "mpi_launcher_present",
                "parameter_file_present",
            )
        ):
            raise ValueError(
                "the configured executable, launcher, or parameter file is unavailable"
            )

        shutil.copyfile(source_parfile, copied_parfile)
        checks["parameter_file_copied"] = (
            _sha256(copied_parfile) == payload["source_parameter_sha256"]
        )
        command = [
            str(launcher),
            "-np",
            str(ranks),
            str(executable),
            "-par_file",
            copied_parfile.name,
        ]
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
            payload["error"] = "FLASH runtime smoke exceeded its timeout"

        fresh = _fresh_files(workspace, before)
        payload["fresh_files"] = [path.name for path in fresh]
        hdf5_outputs, hdf5_error = _inspect_hdf5(fresh)
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
