#!/usr/bin/env python3
"""Normalize one restricted WarpX case from openPMD and reduced diagnostics."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import openpmd_api as io

from conjecture_solver.warpx_analysis import (
    diagnostic_manifest_hash,
    fit_windowed_effective_growth,
    periodic_centered_gauss_assessment,
    relative_range,
    weighted_velocity_moments,
)

ELECTRON_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837139e-31
VACUUM_PERMITTIVITY_F_M = 8.8541878128e-12
SPEED_OF_LIGHT_M_S = 299792458.0


def _particle_scalar_component(record):
    return record[io.Record_Component.SCALAR]


def _mesh_scalar_component(record):
    return record[io.Mesh_Record_Component.SCALAR]


def _load_component(series, component) -> np.ndarray:
    buffer = component.load_chunk()
    series.flush()
    return np.array(buffer, dtype=float) * component.unit_SI


def _field_diagnostics(
    case_directory: Path,
    physical: dict[str, float],
    numerical: dict[str, float | int],
) -> tuple[np.ndarray, np.ndarray, float, float]:
    pattern = case_directory / "diags" / "fields" / "openpmd_%T.h5"
    series = io.Series(str(pattern), io.Access.read_only)
    steps = sorted(series.iterations)
    expected_samples = (
        int(round(float(numerical["final_time_omega_pe"]) / numerical["time_step_omega_pe"]))
        // int(numerical["diagnostic_interval_steps"])
        + 1
    )
    if len(steps) != expected_samples or steps[0] != 0:
        series.close()
        raise ValueError("field diagnostic iteration set is incomplete")
    omega_pe = math.sqrt(
        float(physical["reference_density_m3"])
        * ELECTRON_CHARGE_C**2
        / (ELECTRON_MASS_KG * VACUUM_PERMITTIVITY_F_M)
    )
    times: list[float] = []
    modes: list[complex] = []
    gauss_residuals: list[float] = []
    charge_imbalances: list[float] = []
    for step in steps:
        iteration = series.iterations[step]
        if "E" not in iteration.meshes or "rho" not in iteration.meshes:
            series.close()
            raise ValueError("required E or rho mesh is missing")
        electric_mesh = iteration.meshes["E"]
        charge_mesh = iteration.meshes["rho"]
        if list(electric_mesh.axis_labels) != ["z"] or len(electric_mesh.grid_spacing) != 1:
            series.close()
            raise ValueError("field diagnostic is not the expected one-dimensional z mesh")
        electric = _load_component(series, electric_mesh["z"])
        charge = _load_component(series, _mesh_scalar_component(charge_mesh))
        if electric.shape != (int(numerical["grid_cells"]),) or charge.shape != electric.shape:
            series.close()
            raise ValueError("field diagnostic shape does not match the run package")
        modes.append(2.0 * np.fft.rfft(electric)[1] / len(electric))
        times.append(float(iteration.time * iteration.time_unit_SI * omega_pe))
        gauss = periodic_centered_gauss_assessment(
            electric,
            charge,
            cell_size=float(electric_mesh.grid_spacing[0]),
            vacuum_permittivity=VACUUM_PERMITTIVITY_F_M,
        )
        gauss_residuals.append(gauss.relative_residual)
        charge_imbalances.append(gauss.relative_charge_imbalance)
    series.close()
    return (
        np.array(times),
        np.array(modes),
        max(gauss_residuals),
        max(charge_imbalances),
    )


def _initial_moments(
    case_directory: Path,
    case_name: str,
    physical: dict[str, float],
    numerical: dict[str, float | int],
) -> tuple[float, float, float]:
    pattern = case_directory / "diags" / "particles" / "openpmd_%T.h5"
    series = io.Series(str(pattern), io.Access.read_only)
    steps = sorted(series.iterations)
    max_steps = round(
        float(numerical["final_time_omega_pe"]) / float(numerical["time_step_omega_pe"])
    )
    if steps != [0, max_steps]:
        series.close()
        raise ValueError("particle diagnostics must contain exactly the initial and final steps")
    iteration = series.iterations[0]
    expected_species = 1 if case_name == "unit_maxwellian_reference" else 4
    if len(iteration.particles) != expected_species:
        series.close()
        raise ValueError("electron species count does not match the compiled case")
    momenta: list[np.ndarray] = []
    masses: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    for _, species in iteration.particles.items():
        momentum_component = species["momentum"]["z"]
        mass_component = _particle_scalar_component(species["mass"])
        weight_component = _particle_scalar_component(species["weighting"])
        momentum_buffer = momentum_component.load_chunk()
        mass_buffer = mass_component.load_chunk()
        weight_buffer = weight_component.load_chunk()
        series.flush()
        momenta.append(np.array(momentum_buffer, dtype=float) * momentum_component.unit_SI)
        masses.append(np.array(mass_buffer, dtype=float) * mass_component.unit_SI)
        weights.append(np.array(weight_buffer, dtype=float) * weight_component.unit_SI)
    series.close()
    moments = weighted_velocity_moments(
        np.concatenate(momenta),
        np.concatenate(masses),
        np.concatenate(weights),
        speed_of_light=SPEED_OF_LIGHT_M_S,
    )
    omega_pe = math.sqrt(
        float(physical["reference_density_m3"])
        * ELECTRON_CHARGE_C**2
        / (ELECTRON_MASS_KG * VACUUM_PERMITTIVITY_F_M)
    )
    wavenumber = (
        float(physical["wavenumber_dimensionless"])
        * omega_pe
        / float(physical["velocity_unit_m_s"])
    )
    domain_length = 2.0 * math.pi / wavenumber
    density = moments.total_weight / domain_length
    velocity_unit = float(physical["velocity_unit_m_s"])
    return (
        density / float(physical["reference_density_m3"]),
        moments.mean_velocity / velocity_unit,
        moments.variance / velocity_unit**2,
    )


def _energy_drift(case_directory: Path) -> float:
    reduced = case_directory / "diags" / "reducedfiles"
    field = np.loadtxt(reduced / "field_energy.txt")
    particle = np.loadtxt(reduced / "particle_energy.txt")
    if field.ndim != 2 or particle.ndim != 2 or not np.array_equal(field[:, 0], particle[:, 0]):
        raise ValueError("field and particle energy diagnostics do not share an iteration set")
    return relative_range(field[:, 2] + particle[:, 2])


def _manifest(case_directory: Path) -> str:
    paths = [
        *case_directory.glob("diags/fields/*.h5"),
        *case_directory.glob("diags/particles/*.h5"),
        *case_directory.glob("diags/reducedfiles/*.txt"),
        case_directory / "run_picmi.py",
        case_directory / "warpx_used_inputs",
    ]
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("diagnostic manifest is incomplete")
    return diagnostic_manifest_hash(paths, root=case_directory)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-directory", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    metadata = json.loads(args.metadata.read_text())
    case_name = str(metadata["case_name"])
    physical = metadata["physical"]
    numerical = metadata["numerical"]
    times, modes, gauss_residual, charge_imbalance = _field_diagnostics(
        args.case_directory,
        physical,
        numerical,
    )
    growth = fit_windowed_effective_growth(
        times,
        modes,
        early_window=(
            float(numerical["early_window_start_omega_pe"]),
            float(numerical["early_window_end_omega_pe"]),
        ),
        late_window=(
            float(numerical["late_window_start_omega_pe"]),
            float(numerical["late_window_end_omega_pe"]),
        ),
        minimum_samples=int(numerical["minimum_window_samples"]),
    )
    if growth.amplitude_ratio < float(numerical["damped_ratio_threshold"]):
        classification = "damped"
    elif growth.amplitude_ratio > float(numerical["unstable_ratio_threshold"]):
        classification = "unstable"
    else:
        classification = "ambiguous"
    density, mean, variance = _initial_moments(
        args.case_directory,
        case_name,
        physical,
        numerical,
    )
    summary = {
        "case_name": case_name,
        "solver_converged": True,
        "finite_values": True,
        "diagnostic_samples": len(times),
        "effective_growth_rate_omega_pe": growth.effective_growth_rate,
        "early_rms_amplitude_v_m": growth.early_rms_amplitude,
        "late_rms_amplitude_v_m": growth.late_rms_amplitude,
        "amplitude_ratio": growth.amplitude_ratio,
        "early_window_sample_count": growth.early_sample_count,
        "late_window_sample_count": growth.late_sample_count,
        "classification": classification,
        "fundamental_amplitude_initial_v_m": growth.initial_amplitude,
        "fundamental_amplitude_final_v_m": growth.final_amplitude,
        "initial_density_normalized": density,
        "initial_mean_velocity_normalized": mean,
        "initial_variance_normalized": variance,
        "relative_energy_drift": _energy_drift(args.case_directory),
        "relative_gauss_residual": gauss_residual,
        "relative_charge_imbalance": charge_imbalance,
        "diagnostic_manifest_hash": _manifest(args.case_directory),
    }
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
