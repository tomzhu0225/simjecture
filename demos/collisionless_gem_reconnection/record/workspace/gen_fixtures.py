#!/usr/bin/env python3
"""Generate deterministic synthetic fixtures for analyzer instrument commissioning.

The fixtures implement the exact guided summary structure (including the
five-aspect checks object), the pinned single-level reduced-energy header
schema, and known linear flux slopes, so commissioning checks can assert the
analyzer's estimator math, grouping, energy gating, bootstrap, and decision
booleans before scientific use.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

C = 299_792_458.0
DI = 2.6570466307910177e-05
DT_S = 5.6403491027952336e-15
DT_OMEGACI = 0.002595996918334016
VA_OVER_C = 0.08944271909999159
OMEGA_CI = DT_OMEGACI / DT_S
ALPHA = DI * OMEGA_CI / (VA_OVER_C * C)
T_DURATION = 12.001293753458157
N_POINTS = 26
N_STEPS = 4623
FLUX0 = 0.8178430491920198
MU_T1 = 0.1500
MU_T20 = 0.0500

TIMES = np.linspace(0.0, T_DURATION, N_POINTS)
STEPS = np.linspace(0, N_STEPS, N_POINTS).round().astype(int)

ROOT = Path("fixtures/inp")

CHECKS = {
    "representation": {
        "fully_kinetic_electrons_and_ions": True,
        "two_spatial_three_velocity_dimensions": True,
        "reduced_mass_ratio_declared": True,
    },
    "physics_controls": {
        "collisionless_no_collision_operator": True,
        "no_imposed_reconnection_electric_field": True,
        "harris_pressure_balance": True,
        "harris_ampere_drift_balance": True,
        "stationary_background_populations": True,
        "dimensionless_perturbation_declared": True,
    },
    "boundaries": {
        "x_fields_periodic": True,
        "x_particles_periodic": True,
        "z_fields_conducting": True,
        "z_particles_reflecting": True,
        "perturbation_normal_field_zero_at_z_walls": True,
    },
    "diagnostics": {
        "openpmd_hdf5_files_nonempty": True,
        "multiple_field_times_readable": True,
        "all_reported_values_finite": True,
        "rate_and_flux_diagnostics_present": True,
        "diagnostic_figure_written": True,
    },
    "numerical_regime": {
        "cuda_backend_realized": True,
        "explicit_multidimensional_cfl_satisfied": True,
        "electron_plasma_period_resolved": True,
        "electron_gyroperiod_resolved": True,
        "electron_skin_depth_resolved": True,
        "sheet_half_width_at_least_four_cells": True,
        "nonrelativistic_characteristic_speeds": True,
    },
}


def flux_series(mu: float) -> np.ndarray:
    slope = mu / ALPHA
    return FLUX0 + slope * TIMES


def write_summary(path: Path, endpoint: float, fidelity: int, seed: int, mu: float) -> None:
    history = [
        {
            "time_omegaci": float(time),
            "flux_x_to_o_over_B0_di": float(flux),
            "rate_from_flux_derivative_upstream_norm": mu,
        }
        for time, flux in zip(TIMES, flux_series(mu), strict=True)
    ]
    summary = {
        "inputs": {
            "temperature_ratio_Ti_Te": endpoint,
            "ppc_per_population": fidelity,
            "seed": seed,
            "mass_ratio": 25.0,
            "duration_omegaci": T_DURATION,
            "steps": N_STEPS,
        },
        "derived": {
            "di_m": DI,
            "dt_s": DT_S,
            "dt_omega_ci": DT_OMEGACI,
            "va_upstream_over_c": VA_OVER_C,
        },
        "checks": CHECKS,
        "observations": {"history": history},
    }
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


def write_energy_files(dirpath: Path) -> dict[str, float]:
    dirpath.mkdir(parents=True, exist_ok=True)
    field_rows: list[list[float]] = []
    particle_rows: list[list[float]] = []
    fraction = np.linspace(0.0, 1.0, N_POINTS)
    field_total = 5.0e6 * (1.0 - 1.0e-5 * fraction)
    particle_total = 5.0e9 * (1.0 + 1.0e-8 * fraction)
    for step, time, ft, pt in zip(
        STEPS, TIMES, field_total, particle_total, strict=True
    ):
        field_rows.append([float(step), float(time), float(ft), 0.6 * ft, 0.3 * ft, 0.1 * ft])
        particle_rows.append(
            [float(step), float(time), float(pt), 0.4 * pt, 0.4 * pt, 0.1 * pt, 0.1 * pt]
        )
    field_path = dirpath / "field_energy.txt"
    particle_path = dirpath / "particle_energy.txt"
    with field_path.open("w") as handle:
        handle.write(
            "# [0]step() [1]time(s) [2]total_lev0(J) [3]Ex_lev0(J) [4]Ey_lev0(J) [5]Ez_lev0(J)\n"
        )
        for row in field_rows:
            handle.write(" ".join(format(value, ".17g") for value in row) + "\n")
    with particle_path.open("w") as handle:
        handle.write(
            "# [0]step() [1]time(s) [2]total(J) [3]sheet_electrons(J) "
            "[4]sheet_ions(J) [5]background_electrons(J) [6]background_ions(J)\n"
        )
        for row in particle_rows:
            handle.write(" ".join(format(value, ".17g") for value in row) + "\n")
    combined0 = float(field_total[0] + particle_total[0])
    combined1 = float(field_total[-1] + particle_total[-1])
    return {"combined_relative_drift": (combined1 - combined0) / abs(combined0)}


def main() -> int:
    seeds = [20260902, 20260903, 20260904]
    runs: list[dict[str, object]] = []
    for endpoint, mu in ((1.0, MU_T1), (20.0, MU_T20)):
        for fidelity in (8, 16):
            for seed in seeds:
                label = f"p{fidelity}_t{int(endpoint)}_s{seed}"
                summary_path = ROOT / f"{label}_summary.json"
                reduced = ROOT / label / "reduced"
                drift = write_energy_files(reduced)
                write_summary(summary_path, endpoint, fidelity, seed, mu)
                runs.append(
                    {
                        "label": label,
                        "summary": str(summary_path),
                        "field_energy": str(reduced / "field_energy.txt"),
                        "particle_energy": str(reduced / "particle_energy.txt"),
                        "expected_mu": mu,
                        "combined_relative_drift": drift["combined_relative_drift"],
                    }
                )
    manifest = {
        "schema_version": "analyzer_commissioning_fixture_0.1",
        "runs": runs,
        "alpha_used": ALPHA,
        "timeline": {
            "times": [float(value) for value in TIMES],
            "duration_omegaci": T_DURATION,
            "window_min": 6.0,
            "window_max": 12.0,
        },
    }
    (Path("fixtures/commission_manifest.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "alpha": ALPHA,
                "run_count": len(runs),
                "drift_range": sorted({r["combined_relative_drift"] for r in runs}),
                "expected_R": MU_T1 / MU_T20,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())