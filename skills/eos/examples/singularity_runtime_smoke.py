"""Permanently non-evidentiary health check for a local Singularity-EOS capability.

Evaluates IdealGas at one state through the operator query driver or the Python
module. This is an interface check, not a scientific result.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

SUMMARY_NAME = "singularity_eos_capability_smoke.json"
RHO = 1.0
TEMPERATURE = 1.0
GM1 = 2.0 / 3.0
CV = 1.0


def _load_via_query(query: Path, output: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(query),
            "IdealGas",
            f"{RHO:.17g}",
            f"{TEMPERATURE:.17g}",
            f"{GM1:.17g}",
            f"{CV:.17g}",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "query failed"
        raise RuntimeError(detail)
    return json.loads(output.read_text())


def _load_via_module() -> dict[str, Any]:
    from singularity_eos import IdealGas

    eos = IdealGas(GM1, CV)
    pressure = float(eos.PressureFromDensityTemperature(RHO, TEMPERATURE))
    energy = float(eos.InternalEnergyFromDensityTemperature(RHO, TEMPERATURE))
    heat_capacity = float(eos.SpecificHeatFromDensityTemperature(RHO, TEMPERATURE))
    return {
        "schema_version": "0.1.0",
        "package": "singularity-eos",
        "model": "IdealGas",
        "units": "cgs",
        "density": RHO,
        "temperature": TEMPERATURE,
        "pressure": pressure,
        "specific_internal_energy": energy,
        "specific_heat": heat_capacity,
    }


def main() -> int:
    workspace = Path.cwd().resolve()
    summary_path = workspace / SUMMARY_NAME
    query_output = workspace / "singularity_query.json"
    checks = {
        "environment_valid": False,
        "evaluation_completed": False,
        "pressure_finite": False,
        "ideal_gas_pressure_matches_formula": False,
    }
    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "kind": "singularity_eos_capability_smoke",
        "scientific_status": "permanently_non_evidentiary",
        "checks": checks,
        "elapsed_seconds": 0.0,
        "error": None,
        "interface": None,
        "result": None,
    }
    start = time.monotonic()
    try:
        query_value = os.environ.get("SINGULARITY_EOS_QUERY", "").strip()
        if query_value:
            query = Path(query_value).expanduser()
            if not query.is_file() or not os.access(query, os.X_OK):
                raise ValueError("SINGULARITY_EOS_QUERY is not an executable file")
            checks["environment_valid"] = True
            result = _load_via_query(query, query_output)
            payload["interface"] = "query"
        else:
            checks["environment_valid"] = True
            result = _load_via_module()
            payload["interface"] = "python_module"
        payload["result"] = result
        checks["evaluation_completed"] = True
        pressure = float(result["pressure"])
        checks["pressure_finite"] = math.isfinite(pressure) and pressure > 0.0
        expected = GM1 * RHO * CV * TEMPERATURE
        checks["ideal_gas_pressure_matches_formula"] = math.isclose(
            pressure,
            expected,
            rel_tol=1.0e-8,
            abs_tol=1.0e-12,
        )
    except (
        ImportError,
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
