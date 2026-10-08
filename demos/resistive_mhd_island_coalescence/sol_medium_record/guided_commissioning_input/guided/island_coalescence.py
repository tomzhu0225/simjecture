"""Run and diagnose the operator-supplied FLASH island-coalescence application.

This program is guided commissioning material. Its outputs are permanently
non-evidentiary context; a campaign must collect fresh evidence prospectively.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import h5py
import numpy as np

_WORKSPACE_MARKER = ".simjecture-flash-guided-output"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _named_values(dataset: h5py.Dataset) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for row in dataset[()]:
        name = row["name"].decode().strip().casefold()
        value = row["value"]
        if isinstance(value, bytes):
            value = value.decode().strip()
        elif hasattr(value, "item"):
            value = value.item()
        values[name] = value
    return values


def _center_flux(bx: np.ndarray, by: np.ndarray) -> tuple[float, float]:
    ny, nx = bx.shape
    dx = 1.0 / nx
    dy = 1.0 / ny
    x = -0.5 + (np.arange(nx) + 0.5) * dx
    y = -0.5 + (np.arange(ny) + 0.5) * dy

    from_left = np.cumsum(by, axis=1) * dx - 0.5 * by * dx
    near_x = np.argsort(np.abs(x))[:2]
    along_y = from_left[:, near_x].mean(axis=1)
    fit_y = np.argsort(np.abs(y))[:8]
    design_y = np.column_stack((np.ones(8), y[fit_y] ** 2, y[fit_y] ** 4))
    flux_from_by = float(np.linalg.lstsq(design_y, along_y[fit_y], rcond=None)[0][0])

    from_bottom = np.cumsum(-bx, axis=0) * dy - 0.5 * (-bx) * dy
    near_y = np.argsort(np.abs(y))[:2]
    along_x = from_bottom[near_y, :].mean(axis=0)
    fit_x = np.argsort(np.abs(x))[:8]
    design_x = np.column_stack((np.ones(8), x[fit_x] ** 2, x[fit_x] ** 4))
    flux_from_bx = float(np.linalg.lstsq(design_x, along_x[fit_x], rcond=None)[0][0])
    return flux_from_by, flux_from_bx


def _crossing(times: np.ndarray, values: np.ndarray, target: float) -> float | None:
    indices = np.flatnonzero(values >= target)
    if not len(indices):
        return None
    index = int(indices[0])
    if index == 0:
        return float(times[0])
    dv = values[index] - values[index - 1]
    if dv <= 0:
        return None
    fraction = (target - values[index - 1]) / dv
    return float(times[index - 1] + fraction * (times[index] - times[index - 1]))


def _parameters(args: argparse.Namespace) -> str:
    return f'''run_comment = "Guided FLASH island-coalescence anchor"
log_file = "flash_run.log"
basenm = "flash_run_"

UnitSystem = "none"
geometry = "cartesian"
xmin = -0.5
xmax = 0.5
ymin = -0.5
ymax = 0.5

xl_boundary_type = "reflecting"
xr_boundary_type = "reflecting"
yl_boundary_type = "reflecting"
yr_boundary_type = "reflecting"

sim_alpha = {args.alpha:.17g}
sim_temperature = 3.0
sim_pressureOffset = 6.0

gamma = 1.6666666666666667
eosModeInit = "dens_pres"
eos_singleSpeciesA = 1.0
eos_singleSpeciesZ = 1.0
smlrho = 1.0e-12
smallp = 1.0e-12
smallt = 1.0e-12

useHydro = .true.
order = 2
slopeLimiter = "mc"
LimitedSlopeBeta = 1.0
charLimiting = .true.
use_avisc = .false.
use_flattening = .false.
use_steepening = .false.
use_upwindTVD = .false.
RiemannSolver = "HLLD"
entropy = .false.
shockDetect = .false.

killdivb = .true.
E_modification = .true.
E_upwind = .false.
energyFix = .true.
ForceHydroLimit = .false.

useDiffuse = .true.
useDiffuseTherm = .false.
useDiffuseSpecies = .false.
useDiffuseComputeDtTherm = .false.
useDiffuseComputeDtVisc = .false.
useDiffuseComputeDtSpecies = .false.
useDiffuseComputeDtMagnetic = .true.
dt_diff_factor = 0.8
useMagneticResistivity = .true.
resistivitySolver = "explicit"
resistivityForm = "parallel"
resistivity = {args.eta:.17g}

restart = .false.
nend = 10000
tmax = {args.tmax:.17g}
dr_shortenLastStepBeforeTMax = .true.
cfl = 0.4
dtinit = 1.0e-6
dtmin = 1.0e-14
dtmax = 1.0e-2
tstep_change_factor = 1.2

plotFileNumber = 0
checkpointFileNumber = 0
plotFileIntervalTime = {args.plot_interval:.17g}
checkpointFileIntervalTime = 1000.0
plot_var_1 = "dens"
plot_var_2 = "pres"
plot_var_3 = "velx"
plot_var_4 = "vely"
plot_var_5 = "magx"
plot_var_6 = "magy"
plot_var_7 = "magp"
plot_var_8 = "divb"

iGridSize = {args.nx}
jGridSize = {args.ny}
kGridSize = 1
iProcs = {args.iprocs}
jProcs = {args.jprocs}
kProcs = 1
'''


def _contained_path(raw: str, *, label: str) -> Path:
    requested = Path(raw)
    if requested.is_absolute():
        raise ValueError(f"{label} must be relative to the workspace")
    workspace = Path.cwd().resolve()
    resolved = (workspace / requested).resolve()
    if resolved == workspace or not resolved.is_relative_to(workspace):
        raise ValueError(f"{label} must be a contained workspace child")
    return resolved


def _analyze(output: Path, args: argparse.Namespace) -> dict[str, Any]:
    files = sorted(output.glob("flash_run_hdf5_plt_cnt_*"))
    if len(files) < 2:
        raise RuntimeError("FLASH produced fewer than two regular plot files")

    rows: list[dict[str, float]] = []
    initial_runtime: dict[str, Any] = {}
    initial_logical: dict[str, Any] = {}
    initial_string: dict[str, Any] = {}
    initial_integer: dict[str, Any] = {}
    state_finite = True
    state_positive = True
    max_divergence = 0.0
    max_boundary_fraction = 0.0
    for path in files:
        with h5py.File(path, "r") as handle:
            required = {"dens", "pres", "velx", "vely", "magx", "magy", "divb"}
            missing = required.difference(handle.keys())
            if missing:
                raise RuntimeError(f"{path.name} lacks datasets: {sorted(missing)}")
            real_scalars = _named_values(handle["real scalars"])
            if not initial_runtime:
                initial_runtime = _named_values(handle["real runtime parameters"])
                initial_logical = _named_values(handle["logical runtime parameters"])
                initial_string = _named_values(handle["string runtime parameters"])
                initial_integer = _named_values(handle["integer scalars"])
            fields = {
                name: np.asarray(handle[name][0, 0], dtype=float)
                for name in required
            }
            state_finite = state_finite and all(
                np.isfinite(field).all() for field in fields.values()
            )
            state_positive = state_positive and bool(
                np.min(fields["dens"]) > 0 and np.min(fields["pres"]) > 0
            )
            bx = fields["magx"]
            by = fields["magy"]
            flux_by, flux_bx = _center_flux(bx, by)
            bmax = max(float(np.max(np.abs(bx))), float(np.max(np.abs(by))), 1.0e-300)
            boundary_normal = max(
                float(np.max(np.abs(bx[:, [0, -1]]))),
                float(np.max(np.abs(by[[0, -1], :]))),
            )
            max_boundary_fraction = max(max_boundary_fraction, boundary_normal / bmax)
            divergence = float(np.max(np.abs(fields["divb"])))
            max_divergence = max(max_divergence, divergence)
            rows.append(
                {
                    "time": float(real_scalars["time"]),
                    "flux_from_by": flux_by,
                    "flux_from_bx": flux_bx,
                    "max_abs_divb": divergence,
                    "max_abs_velocity": max(
                        float(np.max(np.abs(fields["velx"]))),
                        float(np.max(np.abs(fields["vely"]))),
                    ),
                }
            )

    times = np.asarray([row["time"] for row in rows])
    flux_by = np.asarray([row["flux_from_by"] for row in rows])
    flux_bx = np.asarray([row["flux_from_bx"] for row in rows])
    flux_by -= flux_by[0]
    flux_bx -= flux_bx[0]
    for row, value_by, value_bx in zip(rows, flux_by, flux_bx, strict=True):
        row["reconnected_flux_from_by"] = float(value_by)
        row["reconnected_flux_from_bx"] = float(value_bx)

    low_time = _crossing(times, flux_by, args.flux_low)
    high_time = _crossing(times, flux_by, args.flux_high)
    reconnection_time = (
        high_time - low_time
        if low_time is not None and high_time is not None and high_time > low_time
        else None
    )
    rate = (
        (args.flux_high - args.flux_low) / reconnection_time
        if reconnection_time is not None
        else None
    )
    path_mismatch = float(np.max(np.abs(flux_by - flux_bx)))
    sheet_cells = (1.0 / args.alpha) / (1.0 / args.ny)
    realized_eta = float(initial_runtime.get("resistivity", math.nan))
    realized_resistive_path = (
        bool(initial_logical.get("usediffuse", False))
        and bool(initial_logical.get("usemagneticresistivity", False))
        and str(initial_string.get("resistivitysolver", "")).casefold() == "explicit"
    )
    realized_grid = (
        int(initial_integer.get("nxb", -1)) == args.nx
        and int(initial_integer.get("nyb", -1)) == args.ny
        and int(initial_integer.get("dimensionality", -1)) == 2
    )
    checks = {
        "completed": True,
        "representation": realized_grid and state_finite and state_positive,
        "physics_controls": realized_resistive_path
        and math.isclose(realized_eta, args.eta, rel_tol=1.0e-12),
        "boundaries": max_boundary_fraction < 0.05,
        "diagnostics": bool(np.all(np.diff(times) > 0)) and path_mismatch < 5.0e-4,
        "numerical_regime": sheet_cells >= 4.0 and max_divergence < 1.0e-9,
        "flux_window_reached": reconnection_time is not None,
        "scientific_evidence_eligible": False,
    }
    return {
        "schema_version": "0.1.0",
        "kind": "guided_flash_island_coalescence_anchor",
        "scientific_status": "permanently_non_evidentiary",
        "checks": checks,
        "metrics": {
            "l_over_eta_nominal": 1.0 / args.eta,
            "flux_low": args.flux_low,
            "flux_high": args.flux_high,
            "flux_low_crossing_time": low_time,
            "flux_high_crossing_time": high_time,
            "reconnection_time": reconnection_time,
            "normalized_flux_slope": rate,
            "flux_path_max_abs_mismatch": path_mismatch,
            "max_abs_divb": max_divergence,
            "max_boundary_normal_fraction": max_boundary_fraction,
            "initial_sheet_cells": sheet_cells,
            "plot_file_count": len(files),
        },
        "realized": {
            "eta": realized_eta,
            "resistivity_solver": initial_string.get("resistivitysolver"),
            "use_diffuse": bool(initial_logical.get("usediffuse", False)),
            "use_magnetic_resistivity": bool(
                initial_logical.get("usemagneticresistivity", False)
            ),
            "nx": args.nx,
            "ny": args.ny,
            "alpha": args.alpha,
            "tmax": args.tmax,
            "mpi_ranks": args.ranks,
        },
        "timeseries": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eta", type=float, required=True)
    parser.add_argument("--nx", type=int, default=128)
    parser.add_argument("--ny", type=int, default=128)
    parser.add_argument("--alpha", type=float, default=20.0)
    parser.add_argument("--tmax", type=float, default=1.2)
    parser.add_argument("--plot-interval", type=float, default=0.05)
    parser.add_argument("--flux-low", type=float, default=0.01)
    parser.add_argument("--flux-high", type=float, default=0.05)
    parser.add_argument("--ranks", type=int, default=4)
    parser.add_argument("--iprocs", type=int, default=2)
    parser.add_argument("--jprocs", type=int, default=2)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not 0 < args.eta < 1 or args.alpha <= 0 or args.tmax <= 0:
        raise ValueError("eta, alpha, and tmax must define a positive bounded run")
    if args.nx < 32 or args.ny < 32 or args.nx % 2 or args.ny % 2:
        raise ValueError("nx and ny must be even and at least 32")
    if args.ranks != args.iprocs * args.jprocs:
        raise ValueError("ranks must equal iprocs*jprocs")
    if not 0 <= args.flux_low < args.flux_high:
        raise ValueError("flux thresholds must be ordered and nonnegative")

    executable = Path(os.environ["FLASH_EXECUTABLE"]).resolve()
    launcher = Path(os.environ["FLASH_MPI_LAUNCHER"]).resolve()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise FileNotFoundError("FLASH_EXECUTABLE is unavailable")
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise FileNotFoundError("FLASH_MPI_LAUNCHER is unavailable")

    output = _contained_path(args.output, label="output")
    summary = _contained_path(args.summary, label="summary")
    if output.exists():
        if not args.overwrite:
            raise FileExistsError(f"output exists: {output}")
        marker = output / _WORKSPACE_MARKER
        if output.is_symlink() or not marker.is_file():
            raise ValueError("refusing to replace an unmarked output directory")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / _WORKSPACE_MARKER).write_text(
        "Owned by the Simjecture guided FLASH controller.\n"
    )
    parfile = output / "flash.par"
    parfile.write_text(_parameters(args))
    command = (
        str(launcher),
        "-np",
        str(args.ranks),
        str(executable),
        "-par_file",
        parfile.name,
    )
    with (output / "launcher_stdout.txt").open("wb") as stdout, (
        output / "launcher_stderr.txt"
    ).open("wb") as stderr:
        completed = subprocess.run(
            command,
            cwd=output,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"FLASH exited with status {completed.returncode}")

    payload = _analyze(output, args)
    payload["provenance"] = {
        "command": list(command),
        "flash_executable_sha256": _sha256(executable),
        "parameter_file_sha256": _sha256(parfile),
    }
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"checks": payload["checks"], "metrics": payload["metrics"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
