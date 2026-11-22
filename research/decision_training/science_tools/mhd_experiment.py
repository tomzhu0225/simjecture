"""A parameterized, real conservative ideal-MHD evolution on a remote CPU.

Only measured quantities are published. Analytic target values and reward
calculations are absent from the student's numerical observation document.
"""

import contextlib
import io
import json
import time
from pathlib import Path

import numpy as np
from mhd_core import simulate

PUBLIC_FIELDS = (
    "polarization", "n", "cfl", "angle_deg", "beta", "amplitude", "seed",
    "initial_phase", "dt", "steps", "end_time", "periods", "measured_speed",
    "amplitude_ratio", "phase_fit_max_residual", "conserved_residuals",
    "max_conservation_residual", "min_density", "min_pressure",
    "density_max_deviation", "divB_max", "floor_corrections", "source_corrections",
)


def main():
    config = json.loads(Path("experiment.json").read_bytes())
    arrays, measurements = {}, []
    started = time.time()
    error = None
    try:
        for index, nx in enumerate(config["nx"]):
            label = "run_" + str(index)
            with contextlib.redirect_stdout(io.StringIO()):
                values = simulate(
                    nx, config["cfl"], config["angle_deg"], config["beta"],
                    config["amplitude"], config["periods"], label, arrays,
                )
            public = {key: values[key] for key in PUBLIC_FIELDS}
            modes = arrays[label + "_mode"]
            phases = np.unwrap(np.angle(modes[0] + 1j * modes[1]))
            public["max_sample_phase_increment"] = float(np.max(np.abs(np.diff(phases))))
            public["phase_sample_count"] = len(phases)
            public["initial_total_energy"] = float(arrays[label + "_initial"][4].mean())
            public["final_total_energy"] = float(arrays[label + "_final"][4].mean())
            measurements.append(public)
            np.savez_compressed("raw.npz", **arrays)
            Path("observations.json").write_text(json.dumps(dict(
                measurements=measurements, complete=False, wall_seconds=time.time() - started,
            ), allow_nan=False))
    except Exception as failure:
        error = type(failure).__name__ + ": " + str(failure)
    result = dict(
        measurements=measurements, complete=error is None, error=error,
        wall_seconds=time.time() - started, boundary="periodic", units="rho0=B0=mu0=L=1; gamma=5/3",
        numerical_method="conservative 1D3V ideal MHD; unlimited MUSCL, LLF, SSPRK2; no floors",
        scope="smooth 1D periodic waves; no multidimensional divergence-control or kinetic claim",
    )
    Path("observations.json").write_text(json.dumps(result, allow_nan=False, indent=2))
    print(json.dumps(result, allow_nan=False))
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
