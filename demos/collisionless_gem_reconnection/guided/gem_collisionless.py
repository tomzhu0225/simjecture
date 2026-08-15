#!/usr/bin/env python3
# ruff: noqa: ISC004 - adjacent literals keep the dependency-free SVG readable
"""Known-runnable, fully kinetic 2D collisionless Harris-sheet anchor.

This program is an operator-supplied starting point for a guided autonomous
campaign.  Its output is not, by itself, evidence for the campaign hypothesis.
The setup follows the geometry and normalized controls of the GEM challenge,
while using dimensional SI values and a reduced ion/electron mass ratio so an
anchor and subsequent parameter studies are reachable on one local GPU.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from pywarpx import picmi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nx", type=int, default=256)
    parser.add_argument("--ppc-per-population", type=int, default=16)
    parser.add_argument("--duration-omegaci", type=float, default=10.0)
    parser.add_argument("--diagnostic-count", type=int, default=20)
    parser.add_argument("--mass-ratio", type=float, default=25.0)
    parser.add_argument("--density-m3", type=float, default=1.0e24)
    parser.add_argument("--background-fraction", type=float, default=0.2)
    parser.add_argument("--va-reference-over-c", type=float, default=0.04)
    parser.add_argument("--ion-electron-temperature-ratio", type=float, default=5.0)
    parser.add_argument("--box-lx-di", type=float, default=25.6)
    parser.add_argument("--box-lz-di", type=float, default=12.8)
    parser.add_argument("--sheet-half-width-di", type=float, default=0.5)
    parser.add_argument("--perturbation-fraction", type=float, default=0.1)
    parser.add_argument("--guide-field-fraction", type=float, default=0.0)
    parser.add_argument("--max-grid-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20260814)
    parser.add_argument("--output", default="guided/anchor_run")
    parser.add_argument("--summary", default="guided/gem_anchor_validation.json")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verbose", type=int, default=0)
    return parser.parse_args()


def contained_target(raw: str, *, label: str) -> Path:
    requested = Path(raw)
    if requested.is_absolute() or ".." in requested.parts:
        raise ValueError(f"{label} must be a contained workspace-relative path")
    resolved = (Path.cwd() / requested).resolve()
    root = Path.cwd().resolve()
    if not resolved.is_relative_to(root) or resolved == root:
        raise ValueError(f"{label} escapes or aliases the workspace root")
    return resolved


def positive_inputs(args: argparse.Namespace) -> None:
    positive = {
        "nx": args.nx,
        "ppc-per-population": args.ppc_per_population,
        "duration-omegaci": args.duration_omegaci,
        "diagnostic-count": args.diagnostic_count,
        "mass-ratio": args.mass_ratio,
        "density-m3": args.density_m3,
        "background-fraction": args.background_fraction,
        "va-reference-over-c": args.va_reference_over_c,
        "ion-electron-temperature-ratio": args.ion_electron_temperature_ratio,
        "box-lx-di": args.box_lx_di,
        "box-lz-di": args.box_lz_di,
        "sheet-half-width-di": args.sheet_half_width_di,
        "max-grid-size": args.max_grid_size,
    }
    nonpositive = [name for name, value in positive.items() if value <= 0]
    if nonpositive:
        raise ValueError(f"positive parameters required: {nonpositive}")
    if args.nx % 2:
        raise ValueError("nx must be even")
    if not 0.0 < args.background_fraction < 1.0:
        raise ValueError("background-fraction must be between zero and one")
    if not 0.0 < args.va_reference_over_c < 0.1:
        raise ValueError("anchor requires a nonrelativistic reference Alfven speed")
    if not 0.0 <= args.perturbation_fraction <= 0.2:
        raise ValueError("perturbation-fraction must be between zero and 0.2")


def proper_velocity(velocity: float, c: float) -> float:
    beta = velocity / c
    if abs(beta) >= 1.0:
        raise ValueError("requested drift is relativistically invalid")
    return velocity / math.sqrt(1.0 - beta * beta)


def patch_means(array: np.ndarray) -> tuple[float, float]:
    """Return the edge X-line and central O-line means for a 2D mesh."""

    rows, columns = array.shape
    z_half = max(1, rows // 128)
    x_half = max(1, columns // 128)
    z_center = rows // 2
    x_center = columns // 2
    z_slice = slice(max(0, z_center - z_half), min(rows, z_center + z_half + 1))
    o_slice = slice(
        max(0, x_center - x_half), min(columns, x_center + x_half + 1)
    )
    edge_width = max(1, 2 * x_half + 1)
    o_value = float(np.mean(array[z_slice, o_slice]))
    x_values = np.concatenate(
        (array[z_slice, :edge_width].ravel(), array[z_slice, -edge_width:].ravel())
    )
    return float(np.mean(x_values)), o_value


def read_field_history(
    field_files: list[Path],
    *,
    lx: float,
    lz: float,
    sheet_half_width: float,
    b0: float,
    di: float,
    omega_ci: float,
    va_upstream: float,
) -> tuple[list[dict[str, float]], dict[str, np.ndarray]]:
    import openpmd_api as io

    history: list[dict[str, float]] = []
    final_fields: dict[str, np.ndarray] = {}
    for path in field_files:
        series = io.Series(str(path), io.Access.read_only)
        for iteration_index in series.iterations:
            iteration = series.iterations[iteration_index]
            requested: dict[str, object] = {}
            units: dict[str, float] = {}
            for record_name, component, key in (
                ("E", "y", "Ey"),
                ("B", "x", "Bx"),
                ("B", "y", "By"),
                ("B", "z", "Bz"),
                ("j", "y", "Jy"),
            ):
                component_record = iteration.meshes[record_name][component]
                requested[key] = component_record.load_chunk()
                units[key] = float(component_record.unit_SI)
            series.flush()
            fields = {
                key: np.asarray(value).copy() * units[key]
                for key, value in requested.items()
            }
            if any(array.ndim != 2 for array in fields.values()):
                raise RuntimeError("expected two-dimensional openPMD field records")
            if any(not np.all(np.isfinite(array)) for array in fields.values()):
                raise RuntimeError("non-finite openPMD field record")

            ey_x, ey_o = patch_means(fields["Ey"])
            bz_mid = fields["Bz"][fields["Bz"].shape[0] // 2, :]
            dx_bz = lx / max(1, bz_mid.size - 1)
            midpoint = bz_mid.size // 2
            flux_x_to_o = float(np.trapezoid(bz_mid[: midpoint + 1], dx=dx_bz))

            bx = fields["Bx"]
            z_scale = max(1, bx.shape[0] - 1)
            upper = round((0.5 + 3.0 * sheet_half_width / lz) * z_scale)
            lower = round((0.5 - 3.0 * sheet_half_width / lz) * z_scale)
            upper = min(max(0, upper), bx.shape[0] - 1)
            lower = min(max(0, lower), bx.shape[0] - 1)
            b_up_observed = 0.5 * (
                float(np.mean(np.abs(bx[upper, :])))
                + float(np.mean(np.abs(bx[lower, :])))
            )

            by = fields["By"]
            z_sign = np.sign(
                np.linspace(-0.5 * lz, 0.5 * lz, by.shape[0], endpoint=True)
            )[:, None]
            x_sign = np.sign(
                np.linspace(-0.5 * lx, 0.5 * lx, by.shape[1], endpoint=True)
            )[None, :]
            quadrupole = float(np.mean(by * z_sign * x_sign) / b0)
            time_s = float(iteration.time * iteration.time_unit_SI)
            history.append(
                {
                    "iteration": int(iteration_index),
                    "time_s": time_s,
                    "time_omegaci": time_s * omega_ci,
                    "flux_x_to_o_Wb_per_m": flux_x_to_o,
                    "flux_x_to_o_over_B0_di": flux_x_to_o / (b0 * di),
                    "rate_from_electric_field_upstream_norm": (
                        (ey_x - ey_o) / (b0 * va_upstream)
                    ),
                    "rate_from_electric_field_reference_norm": (
                        (ey_x - ey_o) / (b0 * (omega_ci * di))
                    ),
                    "ey_xline_V_m": ey_x,
                    "ey_oline_V_m": ey_o,
                    "b_up_observed_over_B0": b_up_observed / b0,
                    "hall_quadrupole_projection_over_B0": quadrupole,
                    "max_abs_B_over_B0": max(
                        float(np.max(np.abs(fields["Bx"]))),
                        float(np.max(np.abs(fields["By"]))),
                        float(np.max(np.abs(fields["Bz"]))),
                    )
                    / b0,
                    "max_abs_Jy_A_m2": float(np.max(np.abs(fields["Jy"]))),
                }
            )
            final_fields = fields
        series.close()

    history.sort(key=lambda item: (item["time_s"], item["iteration"]))
    unique: dict[int, dict[str, float]] = {}
    for item in history:
        unique[int(item["iteration"])] = item
    history = [unique[index] for index in sorted(unique)]
    if len(history) >= 2:
        times = np.asarray([item["time_s"] for item in history])
        flux = np.asarray([item["flux_x_to_o_Wb_per_m"] for item in history])
        derivative = np.gradient(flux, times) / (b0 * va_upstream)
        for item, value in zip(history, derivative, strict=True):
            item["rate_from_flux_derivative_upstream_norm"] = float(value)
    return history, final_fields


def make_figure(
    output: Path,
    history: list[dict[str, float]],
    final_fields: dict[str, np.ndarray],
    *,
    b0: float,
    lx_di: float,
    lz_di: float,
) -> Path:
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as error:
        if error.name != "PIL":
            raise
        return make_svg_figure(
            output,
            history,
            final_fields,
            b0=b0,
            lx_di=lx_di,
            lz_di=lz_di,
        )

    times = [item["time_omegaci"] for item in history]
    electric_rates = [
        item["rate_from_electric_field_upstream_norm"] for item in history
    ]
    flux_rates = [
        item.get("rate_from_flux_derivative_upstream_norm", math.nan)
        for item in history
    ]
    fluxes = [item["flux_x_to_o_over_B0_di"] for item in history]
    extent = [-0.5 * lx_di, 0.5 * lx_di, -0.5 * lz_di, 0.5 * lz_di]
    figure, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    axes[0, 0].plot(times, electric_rates, "o-", label=r"$(E_X-E_O)/(B_0V_{A,up})$")
    axes[0, 0].plot(times, flux_rates, ".--", label="flux derivative")
    axes[0, 0].axhline(0.1, color="black", lw=1, alpha=0.5)
    axes[0, 0].set(xlabel=r"$t\Omega_{ci}$", ylabel="normalized rate")
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(alpha=0.25)
    axes[0, 1].plot(times, fluxes, "o-")
    axes[0, 1].set(
        xlabel=r"$t\Omega_{ci}$", ylabel=r"$(A_O-A_X)/(B_0d_i)$"
    )
    axes[0, 1].grid(alpha=0.25)
    for axis, key, title in (
        (axes[1, 0], "By", r"$B_y/B_0$ (Hall quadrupole)"),
        (axes[1, 1], "Jy", r"$J_y$ [A m$^{-2}$]"),
    ):
        values = final_fields[key] / b0 if key == "By" else final_fields[key]
        limit = float(np.quantile(np.abs(values), 0.995))
        limit = max(limit, np.finfo(float).eps)
        image = axis.imshow(
            values,
            origin="lower",
            extent=extent,
            aspect="auto",
            cmap="RdBu_r",
            vmin=-limit,
            vmax=limit,
        )
        axis.set(xlabel=r"$x/d_i$", ylabel=r"$z/d_i$", title=title)
        figure.colorbar(image, ax=axis, shrink=0.85)
    path = output / "diagnostic_overview.png"
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def make_svg_figure(
    output: Path,
    history: list[dict[str, float]],
    final_fields: dict[str, np.ndarray],
    *,
    b0: float,
    lx_di: float,
    lz_di: float,
) -> Path:
    """Dependency-free vector fallback when the capability lacks Pillow."""

    width, height = 1100, 760
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:sans-serif;fill:#222}.axis{stroke:#222;stroke-width:1}'
        '.grid{stroke:#bbb;stroke-width:1;stroke-dasharray:4 4}</style>',
        '<text x="550" y="25" text-anchor="middle" font-size="18">'
        "Fully kinetic collisionless guided anchor</text>",
    ]

    def polyline_panel(
        x0: float,
        y0: float,
        panel_width: float,
        panel_height: float,
        x_values: list[float],
        series: list[tuple[list[float], str]],
        title: str,
        y_label: str,
    ) -> None:
        finite_y = [
            value
            for values, _color in series
            for value in values
            if math.isfinite(value)
        ]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(finite_y), max(finite_y)
        if x_max == x_min:
            x_max = x_min + 1.0
        if y_max == y_min:
            y_max = y_min + 1.0
        padding = 0.08 * (y_max - y_min)
        y_min -= padding
        y_max += padding

        def project_x(value: float) -> float:
            return x0 + (value - x_min) / (x_max - x_min) * panel_width

        def project_y(value: float) -> float:
            return y0 + panel_height - (value - y_min) / (y_max - y_min) * panel_height

        pieces.extend(
            [
                f'<line class="axis" x1="{x0}" y1="{y0 + panel_height}" '
                f'x2="{x0 + panel_width}" y2="{y0 + panel_height}"/>',
                f'<line class="axis" x1="{x0}" y1="{y0}" x2="{x0}" '
                f'y2="{y0 + panel_height}"/>',
                f'<text x="{x0 + panel_width / 2}" y="{y0 - 10}" '
                f'text-anchor="middle" font-size="15">{title}</text>',
                f'<text x="{x0 + panel_width / 2}" y="{y0 + panel_height + 35}" '
                'text-anchor="middle" font-size="13">t Omega_ci</text>',
                f'<text x="{x0 - 38}" y="{y0 + panel_height / 2}" '
                f'text-anchor="middle" font-size="13" transform="rotate(-90 '
                f'{x0 - 38} {y0 + panel_height / 2})">{y_label}</text>',
                f'<text x="{x0}" y="{y0 + panel_height + 17}" font-size="11">'
                f"{x_min:.3g}</text>",
                f'<text x="{x0 + panel_width}" y="{y0 + panel_height + 17}" '
                f'text-anchor="end" font-size="11">{x_max:.3g}</text>',
                f'<text x="{x0 - 5}" y="{y0 + panel_height}" text-anchor="end" '
                f'font-size="11">{y_min:.3g}</text>',
                f'<text x="{x0 - 5}" y="{y0 + 10}" text-anchor="end" '
                f'font-size="11">{y_max:.3g}</text>',
            ]
        )
        for values, color in series:
            points = " ".join(
                f"{project_x(x_value):.2f},{project_y(y_value):.2f}"
                for x_value, y_value in zip(x_values, values, strict=True)
                if math.isfinite(y_value)
            )
            pieces.append(
                f'<polyline points="{points}" fill="none" stroke="{color}" '
                'stroke-width="2"/>'
            )

    times = [item["time_omegaci"] for item in history]
    electric_rates = [
        item["rate_from_electric_field_upstream_norm"] for item in history
    ]
    flux_rates = [
        item.get("rate_from_flux_derivative_upstream_norm", math.nan)
        for item in history
    ]
    fluxes = [item["flux_x_to_o_over_B0_di"] for item in history]
    polyline_panel(
        75,
        65,
        440,
        245,
        times,
        [(electric_rates, "#1f77b4"), (flux_rates, "#d62728")],
        "Normalized reconnection-rate diagnostics",
        "rate",
    )
    polyline_panel(
        625,
        65,
        400,
        245,
        times,
        [(fluxes, "#2ca02c")],
        "Reconnected flux",
        "(A_O-A_X)/(B0 di)",
    )

    def heatmap(
        values: np.ndarray,
        x0: float,
        y0: float,
        panel_width: float,
        panel_height: float,
        title: str,
    ) -> None:
        row_stride = max(1, math.ceil(values.shape[0] / 48))
        column_stride = max(1, math.ceil(values.shape[1] / 96))
        sampled = values[::row_stride, ::column_stride]
        limit = float(np.quantile(np.abs(sampled), 0.995))
        limit = max(limit, np.finfo(float).eps)
        cell_width = panel_width / sampled.shape[1]
        cell_height = panel_height / sampled.shape[0]
        for row in range(sampled.shape[0]):
            for column in range(sampled.shape[1]):
                normalized = float(np.clip(sampled[row, column] / limit, -1.0, 1.0))
                if normalized >= 0.0:
                    red = 220
                    green = blue = round(240 * (1.0 - normalized))
                else:
                    blue = 220
                    red = green = round(240 * (1.0 + normalized))
                pieces.append(
                    f'<rect x="{x0 + column * cell_width:.2f}" '
                    f'y="{y0 + (sampled.shape[0] - row - 1) * cell_height:.2f}" '
                    f'width="{cell_width + 0.1:.2f}" height="{cell_height + 0.1:.2f}" '
                    f'fill="rgb({red},{green},{blue})"/>'
                )
        pieces.extend(
            [
                f'<rect x="{x0}" y="{y0}" width="{panel_width}" '
                f'height="{panel_height}" fill="none" class="axis"/>',
                f'<text x="{x0 + panel_width / 2}" y="{y0 - 10}" '
                f'text-anchor="middle" font-size="15">{title}</text>',
                f'<text x="{x0 + panel_width / 2}" y="{y0 + panel_height + 30}" '
                f'text-anchor="middle" font-size="13">x/di (-{lx_di / 2:g} to '
                f'{lx_di / 2:g})</text>',
                f'<text x="{x0 - 32}" y="{y0 + panel_height / 2}" '
                f'text-anchor="middle" font-size="13" transform="rotate(-90 '
                f'{x0 - 32} {y0 + panel_height / 2})">z/di (-{lz_di / 2:g} to '
                f'{lz_di / 2:g})</text>',
            ]
        )

    heatmap(final_fields["By"] / b0, 75, 405, 440, 250, "Final By/B0")
    heatmap(final_fields["Jy"], 625, 405, 400, 250, "Final Jy [A/m2]")
    pieces.append(
        '<text x="550" y="735" text-anchor="middle" font-size="12">'
        "Blue/red are symmetric about zero; limits are the 99.5th absolute percentiles."
        "</text>"
    )
    pieces.append("</svg>")
    path = output / "diagnostic_overview.svg"
    path.write_text("\n".join(pieces) + "\n")
    return path


def main() -> int:
    args = parse_args()
    positive_inputs(args)
    output = contained_target(args.output, label="output")
    summary_path = contained_target(args.summary, label="summary")
    if output.exists():
        if not args.overwrite:
            raise ValueError("output exists; pass --overwrite to replace this exact target")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    c = 299_792_458.0
    eps0 = 8.854_187_812_8e-12
    mu0 = 1.256_637_062_12e-6
    qe = 1.602_176_634e-19
    me = 9.109_383_701_5e-31
    mi = args.mass_ratio * me
    n_sheet = args.density_m3
    n_background = args.background_fraction * n_sheet
    omega_pe = math.sqrt(n_sheet * qe * qe / (eps0 * me))
    omega_pi = math.sqrt(n_sheet * qe * qe / (eps0 * mi))
    di = c / omega_pi
    de = c / omega_pe
    va_reference = args.va_reference_over_c * c
    b0 = va_reference * math.sqrt(mu0 * n_sheet * (mi + me))
    omega_ci = qe * b0 / mi
    omega_ce = qe * b0 / me
    va_upstream = b0 / math.sqrt(mu0 * n_background * (mi + me))
    total_temperature_j = b0 * b0 / (2.0 * mu0 * n_sheet)
    te_j = total_temperature_j / (1.0 + args.ion_electron_temperature_ratio)
    ti_j = total_temperature_j - te_j
    te_ev = te_j / qe
    ti_ev = ti_j / qe
    vte = math.sqrt(te_j / me)
    vti = math.sqrt(ti_j / mi)
    sheet_half_width = args.sheet_half_width_di * di
    ion_drift = 2.0 * ti_j / (qe * b0 * sheet_half_width)
    electron_drift = -2.0 * te_j / (qe * b0 * sheet_half_width)
    lx = args.box_lx_di * di
    lz = args.box_lz_di * di
    dx = lx / args.nx
    nz_float = lz / dx
    nz = round(nz_float)
    if nz % 2:
        nz += 1
    dz = lz / nz
    dt_cfl = 1.0 / (c * math.sqrt(dx**-2 + dz**-2))
    dt = 0.9 * dt_cfl
    nsteps = max(1, math.ceil(args.duration_omegaci / (dt * omega_ci)))
    diagnostic_period = max(1, nsteps // args.diagnostic_count)
    kx = 2.0 * math.pi / lx
    kz = math.pi / lz
    perturbation_potential = args.perturbation_fraction * b0 / kx
    guide_field = args.guide_field_fraction * b0
    density_expression = f"({n_sheet})/cosh(z/({sheet_half_width}))**2"

    populations: list[picmi.Species] = []
    population_specs = (
        ("sheet_electrons", me, -qe, density_expression, electron_drift, vte),
        ("sheet_ions", mi, qe, density_expression, ion_drift, vti),
        ("background_electrons", me, -qe, str(n_background), 0.0, vte),
        ("background_ions", mi, qe, str(n_background), 0.0, vti),
    )
    for name, mass, charge, density, drift, thermal_speed in population_specs:
        distribution = picmi.AnalyticDistribution(
            density_expression=density,
            momentum_expressions=["0.0", str(proper_velocity(drift, c)), "0.0"],
            warpx_momentum_spread_expressions=[str(thermal_speed)] * 3,
        )
        populations.append(
            picmi.Species(
                name=name,
                mass=mass,
                charge=charge,
                particle_shape="linear",
                initial_distribution=distribution,
            )
        )

    grid = picmi.Cartesian2DGrid(
        number_of_cells=[args.nx, nz],
        lower_bound=[-0.5 * lx, -0.5 * lz],
        upper_bound=[0.5 * lx, 0.5 * lz],
        lower_boundary_conditions=["periodic", "dirichlet"],
        upper_boundary_conditions=["periodic", "dirichlet"],
        lower_boundary_conditions_particles=["periodic", "reflecting"],
        upper_boundary_conditions_particles=["periodic", "reflecting"],
        warpx_max_grid_size=args.max_grid_size,
        warpx_blocking_factor=8,
    )
    solver = picmi.ElectromagneticSolver(grid=grid, method="Yee")
    simulation = picmi.Simulation(
        solver=solver,
        time_step_size=dt,
        max_steps=nsteps,
        particle_shape="linear",
        verbose=args.verbose,
        warpx_evolve_scheme=picmi.ExplicitEvolveScheme(),
        warpx_current_deposition_algo="esirkepov",
        warpx_random_seed=args.seed,
        warpx_serialize_initial_conditions=True,
        warpx_amrex_the_arena_init_size=256 * 1024 * 1024,
        warpx_used_inputs_file=str(output / "warpx_used_inputs"),
    )
    for population in populations:
        simulation.add_species(
            population,
            layout=picmi.PseudoRandomLayout(
                grid=grid,
                n_macroparticles_per_cell=args.ppc_per_population,
            ),
        )
    simulation.add_applied_field(
        picmi.AnalyticInitialField(
            Ex_expression="0.0",
            Ey_expression="0.0",
            Ez_expression="0.0",
            Bx_expression=(
                f"({b0})*tanh(z/({sheet_half_width}))"
                f"+({perturbation_potential * kz})*cos(({kx})*x)*sin(({kz})*z)"
            ),
            By_expression=str(guide_field),
            Bz_expression=(
                f"(-{perturbation_potential * kx})*sin(({kx})*x)*cos(({kz})*z)"
            ),
            warpx_do_initial_div_cleaning=False,
        )
    )
    simulation.add_diagnostic(
        picmi.FieldDiagnostic(
            name="fields",
            grid=grid,
            period=diagnostic_period,
            data_list=["E", "B", "J", "rho"],
            write_dir=str(output),
            warpx_format="openpmd",
            warpx_openpmd_backend="h5",
            warpx_openpmd_encoding="f",
        )
    )
    simulation.add_diagnostic(
        picmi.ReducedDiagnostic(
            diag_type="FieldEnergy",
            name="field_energy",
            period=diagnostic_period,
            path=str(output / "reduced") + "/",
        )
    )
    simulation.add_diagnostic(
        picmi.ReducedDiagnostic(
            diag_type="ParticleEnergy",
            name="particle_energy",
            period=diagnostic_period,
            path=str(output / "reduced") + "/",
        )
    )

    started = time.monotonic()
    simulation.step()
    elapsed = time.monotonic() - started

    field_files = sorted((output / "fields").glob("*.h5"))
    history, final_fields = read_field_history(
        field_files,
        lx=lx,
        lz=lz,
        sheet_half_width=sheet_half_width,
        b0=b0,
        di=di,
        omega_ci=omega_ci,
        va_upstream=va_upstream,
    )
    if not history or not final_fields:
        raise RuntimeError("no readable openPMD field history was produced")
    np.savez_compressed(output / "final_fields.npz", **final_fields)
    figure_path = make_figure(
        output,
        history,
        final_fields,
        b0=b0,
        lx_di=args.box_lx_di,
        lz_di=args.box_lz_di,
    )

    from amrex import space2d as amrex

    used_inputs = (output / "warpx_used_inputs").read_text(errors="replace")
    current_required = b0 / (mu0 * sheet_half_width)
    current_from_drifts = qe * n_sheet * (ion_drift - electron_drift)
    pressure_required = b0 * b0 / (2.0 * mu0)
    pressure_from_particles = n_sheet * (te_j + ti_j)
    all_rates = np.asarray(
        [item["rate_from_electric_field_upstream_norm"] for item in history]
    )
    late_rates = all_rates[max(0, all_rates.size // 2) :]
    nominal_collision_frequency = (
        2.91e-6
        * (n_background * 1.0e-6)
        * 10.0
        / max(te_ev, 1.0) ** 1.5
    )
    all_finite = all(
        math.isfinite(value)
        for item in history
        for value in item.values()
        if isinstance(value, (float, int))
    )
    summary = {
        "schema_version": "0.1.0",
        "scope": "operator-validated guided commissioning anchor",
        "scientific_evidence_eligible": False,
        "references": [
            {
                "name": "GEM magnetic reconnection challenge",
                "doi": "10.1029/1999JA900449",
                "url": "https://doi.org/10.1029/1999JA900449",
            },
            {
                "name": "Review of the 0.1 reconnection rate problem",
                "doi": "10.1017/S0022377817000666",
                "url": "https://doi.org/10.1017/S0022377817000666",
            },
        ],
        "argv": sys.argv[1:],
        "runtime": {
            "elapsed_wall_seconds": elapsed,
            "gpu_enabled": bool(amrex.Config.have_gpu),
            "gpu_backend": str(amrex.Config.gpu_backend),
            "openpmd_file_count": len(field_files),
        },
        "inputs": {
            "geometry": "2D x-z, three velocity components",
            "fully_kinetic_populations": [item.name for item in populations],
            "collision_operator": None,
            "field_solver": "explicit Yee electromagnetic",
            "current_deposition": "Esirkepov",
            "grid_cells": [args.nx, nz],
            "ppc_per_population": args.ppc_per_population,
            "nominal_total_macroparticles": (
                args.nx * nz * args.ppc_per_population * len(populations)
            ),
            "n_sheet_m3": n_sheet,
            "n_sheet_cm3": n_sheet * 1.0e-6,
            "background_fraction": args.background_fraction,
            "mass_ratio": args.mass_ratio,
            "temperature_ratio_Ti_Te": args.ion_electron_temperature_ratio,
            "temperature_electron_eV": te_ev,
            "temperature_ion_eV": ti_ev,
            "B0_T": b0,
            "guide_field_fraction": args.guide_field_fraction,
            "perturbation_fraction": args.perturbation_fraction,
            "box_Lx_di": args.box_lx_di,
            "box_Lz_di": args.box_lz_di,
            "sheet_half_width_di": args.sheet_half_width_di,
            "duration_omegaci": nsteps * dt * omega_ci,
            "steps": nsteps,
            "diagnostic_period_steps": diagnostic_period,
            "seed": args.seed,
            "field_boundaries": ["x periodic", "z conducting/dirichlet"],
            "particle_boundaries": ["x periodic", "z reflecting"],
        },
        "derived": {
            "di_m": di,
            "de_m": de,
            "dx_m": dx,
            "dz_m": dz,
            "dt_s": dt,
            "dt_over_multidimensional_cfl": dt / dt_cfl,
            "dx_over_de": dx / de,
            "dz_over_de": dz / de,
            "sheet_half_width_cells": sheet_half_width / max(dx, dz),
            "dt_omega_pe": dt * omega_pe,
            "dt_omega_ce": dt * omega_ce,
            "dt_omega_ci": dt * omega_ci,
            "va_reference_over_c": va_reference / c,
            "va_upstream_over_c": va_upstream / c,
            "electron_thermal_speed_over_c": vte / c,
            "ion_thermal_speed_over_c": vti / c,
            "electron_drift_over_c": electron_drift / c,
            "ion_drift_over_c": ion_drift / c,
            "nominal_nu_ei_over_omega_ci_if_enabled": (
                nominal_collision_frequency / omega_ci
            ),
            "ampere_balance_relative_error": abs(
                current_from_drifts / current_required - 1.0
            ),
            "pressure_balance_relative_error": abs(
                pressure_from_particles / pressure_required - 1.0
            ),
        },
        "checks": {
            "representation": {
                "fully_kinetic_electrons_and_ions": len(populations) == 4,
                "two_spatial_three_velocity_dimensions": True,
                "reduced_mass_ratio_declared": args.mass_ratio == 25.0,
            },
            "physics_controls": {
                "collisionless_no_collision_operator": "collision_names" not in used_inputs,
                "no_imposed_reconnection_electric_field": True,
                "harris_pressure_balance": abs(
                    pressure_from_particles / pressure_required - 1.0
                )
                < 1.0e-12,
                "harris_ampere_drift_balance": abs(
                    current_from_drifts / current_required - 1.0
                )
                < 1.0e-12,
                "stationary_background_populations": True,
                "dimensionless_perturbation_declared": True,
            },
            "boundaries": {
                "x_fields_periodic": "boundary.field_lo = periodic pec" in used_inputs,
                "x_particles_periodic": "boundary.particle_lo = periodic reflecting" in used_inputs,
                "z_fields_conducting": "boundary.field_hi = periodic pec" in used_inputs,
                "z_particles_reflecting": "boundary.particle_hi = periodic reflecting" in used_inputs,
                "perturbation_normal_field_zero_at_z_walls": abs(
                    math.cos(kz * 0.5 * lz)
                )
                < 1.0e-14,
            },
            "diagnostics": {
                "openpmd_hdf5_files_nonempty": bool(field_files)
                and all(path.stat().st_size > 0 for path in field_files),
                "multiple_field_times_readable": len(history) >= 3,
                "all_reported_values_finite": all_finite,
                "rate_and_flux_diagnostics_present": all(
                    "rate_from_electric_field_upstream_norm" in item
                    and "flux_x_to_o_over_B0_di" in item
                    for item in history
                ),
                "diagnostic_figure_written": figure_path.is_file(),
            },
            "numerical_regime": {
                "cuda_backend_realized": bool(amrex.Config.have_gpu)
                and str(amrex.Config.gpu_backend).upper() == "CUDA",
                "explicit_multidimensional_cfl_satisfied": dt < dt_cfl,
                "electron_plasma_period_resolved": dt * omega_pe < 0.7,
                "electron_gyroperiod_resolved": dt * omega_ce < 0.2,
                "electron_skin_depth_resolved": max(dx, dz) <= de,
                "sheet_half_width_at_least_four_cells": (
                    sheet_half_width / max(dx, dz) >= 4.0
                ),
                "nonrelativistic_characteristic_speeds": max(
                    va_upstream,
                    vte,
                    vti,
                    abs(electron_drift),
                    abs(ion_drift),
                )
                < 0.2 * c,
            },
        },
        "observations": {
            "history": history,
            "late_half_rate_median_upstream_norm": float(np.median(late_rates)),
            "late_half_rate_abs_median_upstream_norm": float(
                np.median(np.abs(late_rates))
            ),
            "late_half_rate_10_90_percentile_upstream_norm": [
                float(np.quantile(late_rates, 0.1)),
                float(np.quantile(late_rates, 0.9)),
            ],
            "flux_change_over_B0_di": (
                history[-1]["flux_x_to_o_over_B0_di"]
                - history[0]["flux_x_to_o_over_B0_di"]
            ),
            "final_hall_quadrupole_projection_over_B0": history[-1][
                "hall_quadrupole_projection_over_B0"
            ],
        },
        "limitations": [
            "This is a guided commissioning anchor, not campaign evidence.",
            "The ion/electron mass ratio is reduced to 25.",
            "One seed and one parameter point cannot establish a plateau or boundary.",
            "Resolution and particle-count convergence remain for the autonomous campaign.",
            "The nominal Coulomb-frequency estimate is contextual; no collision operator is enabled.",
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    leaves: list[bool] = []
    for category in summary["checks"].values():
        leaves.extend(bool(value) for value in category.values())
    print(
        json.dumps(
            {
                "summary": str(summary_path.relative_to(Path.cwd())),
                "output": str(output.relative_to(Path.cwd())),
                "checks_passed": sum(leaves),
                "checks_total": len(leaves),
                "elapsed_wall_seconds": elapsed,
                "history_points": len(history),
                "late_half_rate_abs_median_upstream_norm": summary["observations"][
                    "late_half_rate_abs_median_upstream_norm"
                ],
            },
            sort_keys=True,
        )
    )
    return int(not all(leaves))


if __name__ == "__main__":
    raise SystemExit(main())
