"""Run matched-time 1D WarpX Langmuir controls and independently check saved fields."""

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import yt
from scipy.constants import c, e, epsilon_0, m_e


def analyze(directory, cells):
    dataset = yt.load(str(directory))
    fields = dataset.covering_grid(
        level=0, left_edge=dataset.domain_left_edge, dims=dataset.domain_dimensions
    )
    physical_time = float(dataset.current_time.to_value())
    z = -20e-6 + 40e-6 / cells * (np.arange(cells) + 0.5)
    k = 4 * np.pi / 40e-6
    omega_p = np.sqrt(4e24 * e**2 / (m_e * epsilon_0))
    exact = 0.01 * m_e * c**2 * k / e * np.sin(omega_p * physical_time) * np.sin(k * z)
    actual = fields[("mesh", "Ez")].to_ndarray()[:, 0, 0]
    field_error = float(np.max(np.abs(actual - exact)) / np.max(np.abs(exact)))
    rho = fields[("boxlib", "rho")].to_ndarray()
    divergence = fields[("boxlib", "divE")].to_ndarray()
    charge_error = float(
        np.max(np.abs(divergence - rho / epsilon_0)) / np.max(np.abs(rho / epsilon_0))
    )
    return {
        "cells": cells,
        "physical_time_s": physical_time,
        "relative_field_error": field_error,
        "relative_charge_residual": charge_error,
        "original_field_tolerance": 0.05,
        "original_charge_tolerance": 1e-11,
        "original_checks_passed": field_error < 0.05 and charge_error < 1e-11,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cells", type=int, nargs="+", default=[64, 128, 256])
    args = parser.parse_args()
    binary, source = args.binary.resolve(), args.input.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    yt.funcs.mylog.setLevel(40)
    results = []
    for cells in args.cells:
        steps = 80 * cells // 128
        if cells % 64 or steps < 1:
            raise ValueError("Use multiples of 64 cells for this matched-time test")
        folder = output / f"n{cells}"
        folder.mkdir(exist_ok=False)
        (folder / "inputs").write_bytes(source.read_bytes())
        command = [
            str(binary),
            "inputs",
            "diagnostics.diags_names=diag1",
            "diag1.file_prefix=langmuir",
            f"diag1.intervals={steps}",
            f"amr.n_cell={cells}",
            f"max_step={steps}",
            "amrex.the_arena_init_size=67108864",
            "warpx.verbose=0",
        ]
        start = time.perf_counter()
        with (folder / "run.log").open("w") as log:
            subprocess.run(
                command,
                cwd=folder,
                env=dict(os.environ, OMP_NUM_THREADS="2"),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=True,
            )
        seconds = time.perf_counter() - start
        result = analyze(folder / f"langmuir{steps:06d}", cells)
        result.update(steps=steps, process_seconds=seconds, command=command)
        results.append(result)
        print(json.dumps(result), flush=True)
    body = {
        "solver": "WarpX 26.10, retained 1D CUDA double-precision executable",
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "scope": (
            "Local matched-time Langmuir grid controls; no claim of general solver qualification"
        ),
        "cases": results,
        "time_spread_seconds": max(r["physical_time_s"] for r in results)
        - min(r["physical_time_s"] for r in results),
    }
    (output / "validation.json").write_text(json.dumps(body, indent=2) + "\n")


if __name__ == "__main__":
    main()
