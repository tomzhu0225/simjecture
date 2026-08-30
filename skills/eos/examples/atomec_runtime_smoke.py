"""Permanently non-evidentiary health check for a local atoMEC capability.

This script imports atoMEC and evaluates a cheap helium ion-sphere state. It
checks process wiring only; it does not validate a physical model or scientific
result.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

SUMMARY_NAME = "atomec_capability_smoke.json"


def main() -> int:
    workspace = Path.cwd().resolve()
    summary_path = workspace / SUMMARY_NAME
    checks = {
        "import_succeeded": False,
        "energy_finite": False,
        "mean_ionization_in_range": False,
    }
    payload: dict[str, Any] = {
        "schema_version": "0.1.0",
        "kind": "atomec_capability_smoke",
        "scientific_status": "permanently_non_evidentiary",
        "checks": checks,
        "elapsed_seconds": 0.0,
        "error": None,
        "free_energy_ha": None,
        "mean_ionization": None,
    }
    start = time.monotonic()
    try:
        from atoMEC import Atom, config, models

        config.numcores = 0
        checks["import_succeeded"] = True
        atom = Atom("He", radius=3.0, temp=0.01, write_info=False)
        model = models.ISModel(atom, bc="neumann", write_info=False)
        output = model.CalcEnergy(
            nmax=2,
            lmax=2,
            grid_params={"ngrid": 400},
            verbosity=0,
            write_info=False,
            write_density=False,
            write_potential=False,
            write_eigs_occs=False,
            write_dos=False,
        )
        energy = float(output["energy"].F_tot)
        ionization = float(output["density"].MIS[0])
        payload["free_energy_ha"] = energy
        payload["mean_ionization"] = ionization
        checks["energy_finite"] = math.isfinite(energy)
        checks["mean_ionization_in_range"] = math.isfinite(ionization) and (
            0.0 <= ionization <= 2.0 + 1.0e-6
        )
    except (
        ImportError,
        OSError,
        ValueError,
        RuntimeError,
        AttributeError,
        KeyError,
        TypeError,
    ) as exc:
        payload["error"] = str(exc)

    checks["completed"] = all(checks.values())
    payload["elapsed_seconds"] = time.monotonic() - start
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if checks["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
