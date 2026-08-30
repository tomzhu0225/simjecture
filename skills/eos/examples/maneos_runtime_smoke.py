"""Permanently non-evidentiary health check for a local M-ANEOS capability.

Copies the operator-prepared ANEOS input and runs the query driver at one
density-temperature point. This is an interface check, not a material
qualification.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

SUMMARY_NAME = "maneos_capability_smoke.json"
RHO = 1.0
TEMPERATURE_EV = 1.0


def main() -> int:
    workspace = Path.cwd().resolve()
    summary_path = workspace / SUMMARY_NAME
    result_path = workspace / "maneos_query.json"
    checks = {
        "environment_valid": False,
        "executable_present": False,
        "input_present": False,
        "input_copied": False,
        "process_completed": False,
        "return_code_zero": False,
        "pressure_finite": False,
    }
    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "kind": "maneos_capability_smoke",
        "scientific_status": "permanently_non_evidentiary",
        "checks": checks,
        "command": [],
        "elapsed_seconds": 0.0,
        "error": None,
        "return_code": None,
        "result": None,
    }
    start = time.monotonic()
    try:
        query = Path(os.environ.get("MANEOS_QUERY", "")).expanduser()
        source_input = Path(os.environ.get("MANEOS_PREFLIGHT_INPUT", "")).expanduser()
        if not os.environ.get("MANEOS_QUERY") or not os.environ.get(
            "MANEOS_PREFLIGHT_INPUT"
        ):
            raise ValueError("MANEOS_QUERY and MANEOS_PREFLIGHT_INPUT must be set")
        checks["environment_valid"] = True
        checks["executable_present"] = query.is_file() and os.access(query, os.X_OK)
        checks["input_present"] = source_input.is_file()
        if not checks["executable_present"] or not checks["input_present"]:
            raise ValueError("the configured query driver or ANEOS input is unavailable")
        destination = workspace / "ANEOS.INPUT"
        shutil.copyfile(source_input, destination)
        checks["input_copied"] = destination.is_file() and destination.stat().st_size > 0
        command = [
            str(query),
            f"{RHO:.17g}",
            f"{TEMPERATURE_EV:.17g}",
            str(result_path),
        ]
        payload["command"] = command
        completed = subprocess.run(
            command,
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
        )
        payload["return_code"] = completed.returncode
        checks["process_completed"] = True
        checks["return_code_zero"] = completed.returncode == 0
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip() or completed.stdout.strip() or "query failed"
            )
        result = json.loads(result_path.read_text())
        payload["result"] = result
        pressure = float(result["pressure"])
        checks["pressure_finite"] = math.isfinite(pressure) and pressure > 0.0
    except (
        OSError,
        ValueError,
        RuntimeError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        payload["error"] = str(exc)

    checks["completed"] = all(checks.values())
    payload["elapsed_seconds"] = time.monotonic() - start
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if checks["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
