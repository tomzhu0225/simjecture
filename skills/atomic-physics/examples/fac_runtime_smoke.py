"""Permanently non-evidentiary FAC execution and table-format health check."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import time
from pathlib import Path


def main():
    started = time.monotonic()
    checks = {
        key: False
        for key in (
            "executables_present",
            "process_completed",
            "return_code_zero",
            "tables_readable",
            "lyman_alpha_limit",
        )
    }
    result = {
        "schema_version": "0.1.0",
        "kind": "fac_capability_smoke",
        "scientific_status": "permanently_non_evidentiary",
        "checks": checks,
        "error": None,
    }
    try:
        executables = [Path(os.environ[name]) for name in ("FAC_SFAC", "FAC_SCRM", "FAC_SPOL")]
        checks["executables_present"] = all(
            p.is_file() and os.access(p, os.X_OK) for p in executables
        )
        if not checks["executables_present"]:
            raise ValueError("FAC executable is missing")
        helper = runpy.run_path(os.environ["FAC_LTE_HELPER"])
        directory = Path("fac_smoke")
        directory.mkdir(exist_ok=True)
        for name in ("h.en.b", "h.tr.b", "h.en", "h.tr"):
            (directory / name).unlink(missing_ok=True)
        (directory / "input.sf").write_text(
            "SetAtom('H')\nConfig('ground', '1s1')\nConfig('upper', '2p1')\n"
            "ConfigEnergy(0)\nOptimizeRadial(['ground'])\nConfigEnergy(1)\n"
            "Structure('h.en.b', ['ground', 'upper'])\nMemENTable('h.en.b')\n"
            "PrintTable('h.en.b', 'h.en', 1)\n"
            "TransitionTable('h.tr.b', ['ground'], ['upper'], -1)\n"
            "PrintTable('h.tr.b', 'h.tr', 1)\n"
        )
        with (
            (directory / "stdout.log").open("w") as stdout,
            (directory / "stderr.log").open("w") as stderr,
        ):
            process = subprocess.run(
                [str(executables[0]), "input.sf"],
                cwd=directory,
                stdout=stdout,
                stderr=stderr,
                timeout=90,
                check=False,
            )
        checks["process_completed"] = True
        checks["return_code_zero"] = process.returncode == 0
        levels = helper["read_levels"](directory / "h.en")
        blocks = list(helper["transition_blocks"](directory / "h.tr"))
        checks["tables_readable"] = len(levels["index"]) == 3 and len(blocks) == 1
        block = blocks[0]
        oscillator_sum = float(sum(block["gf"] / block["lower_weight"]))
        energy = float(sum(block["energy_eV"] * block["gf"]) / sum(block["gf"]))
        result.update(
            {
                "energy_eV": energy,
                "oscillator_strength_sum": oscillator_sum,
                "sfac_sha256": helper["sha256"](executables[0]),
            }
        )
        # Loose hydrogenic limit checks detect column and unit mistakes.
        checks["lyman_alpha_limit"] = (
            abs(energy / 10.2 - 1) < 0.02 and abs(oscillator_sum / 0.4162 - 1) < 0.02
        )
    except (OSError, ValueError, KeyError, ImportError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)
    checks["completed"] = all(checks.values())
    result["elapsed_seconds"] = time.monotonic() - started
    Path("fac_capability_smoke.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return 0 if checks["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
