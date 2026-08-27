#!/usr/bin/env python3
"""Generate the FLASH demo figures from recorded outputs.

The guided anchor is deliberately non-evidentiary.  This script therefore
never invents a field or diagnostic: the first three figures are read from
the HDF5 plot files produced by ``guided/island_coalescence.py`` and the
scaling figure is read from the explicitly labelled local campaign audit
extract.

Run from the repository root after the guided anchor has completed::

    uv run python demos/resistive_mhd_island_coalescence/plot_results.py

The anchor output is ignored by Git, so a fresh checkout must run the guided
command before this script can make the field figures.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

ROOT = Path(__file__).resolve().parent
DEFAULT_ANCHOR = ROOT / "guided" / "anchor_run"
DEFAULT_SUMMARY = ROOT / "guided" / "anchor_validation.json"
DEFAULT_AUDIT = ROOT / "campaign_audit.json"
FIGURES = ROOT / "figures"


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


def _current_density(bx: np.ndarray, by: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Return J_z = dB_y/dx - dB_x/dy using the analysis convention."""

    return np.gradient(by, dx, axis=1) - np.gradient(bx, dy, axis=0)


def _flux_function(bx: np.ndarray, by: np.ndarray, dx: float) -> np.ndarray:
    """Construct a gauge-shifted 2-D flux function for field-line contours."""

    psi = np.cumsum(by, axis=1) * dx - 0.5 * by * dx
    return psi - float(np.mean(psi))


def _load_anchor(anchor_dir: Path, summary_path: Path) -> dict[str, Any]:
    files = sorted(anchor_dir.glob("flash_run_hdf5_plt_cnt_*"))
    if len(files) < 2:
        raise SystemExit(
            f"expected at least two FLASH plot files in {anchor_dir}; run the guided anchor first"
        )

    frames: list[dict[str, Any]] = []
    for path in files:
        with h5py.File(path, "r") as handle:
            required = {"dens", "pres", "velx", "vely", "magx", "magy", "divb"}
            missing = required.difference(handle.keys())
            if missing:
                raise SystemExit(f"{path.name} lacks datasets: {sorted(missing)}")
            runtime = _named_values(handle["real scalars"])
            time = float(runtime["time"])
            fields = {name: np.asarray(handle[name][0, 0], dtype=float) for name in required}
        ny, nx = fields["magx"].shape
        dx = 1.0 / nx
        dy = 1.0 / ny
        fields.update(
            {
                "path": path,
                "time": time,
                "jz": _current_density(fields["magx"], fields["magy"], dx, dy),
                "psi": _flux_function(fields["magx"], fields["magy"], dx),
            }
        )
        frames.append(fields)

    summary = json.loads(summary_path.read_text())
    realized = summary.get("realized", {})
    metrics = summary.get("metrics", {})
    rows = summary.get("timeseries", [])
    if not rows:
        raise SystemExit(f"summary has no timeseries rows: {summary_path}")
    ny, nx = frames[0]["magx"].shape
    x = -0.5 + (np.arange(nx) + 0.5) / nx
    y = -0.5 + (np.arange(ny) + 0.5) / ny
    return {
        "frames": frames,
        "times": np.asarray([frame["time"] for frame in frames], dtype=float),
        "x": x,
        "y": y,
        "nx": nx,
        "ny": ny,
        "summary": summary,
        "realized": realized,
        "metrics": metrics,
        "rows": rows,
    }


def _nearest(data: dict[str, Any], target: float) -> int:
    return int(np.argmin(np.abs(data["times"] - target)))


def _field_limits(data: dict[str, Any]) -> tuple[float, float, float, float]:
    j_values = np.concatenate([np.abs(frame["jz"]).ravel() for frame in data["frames"]])
    j_limit = max(float(np.percentile(j_values, 99.5)), 1.0)
    rho_values = np.concatenate([frame["dens"].ravel() for frame in data["frames"]])
    rho_limits = (float(np.min(rho_values)), float(np.max(rho_values)))
    vx_values = np.concatenate([np.abs(frame["velx"]).ravel() for frame in data["frames"]])
    vx_limit = max(float(np.percentile(vx_values, 99.5)), 1.0e-3)
    return j_limit, rho_limits[0], max(rho_limits[1], rho_limits[0] + 1.0e-12), vx_limit


def _stream(ax: Any, data: dict[str, Any], frame: dict[str, Any], *, color: str) -> None:
    step = max(1, data["nx"] // 32)
    ax.streamplot(
        data["x"][::step],
        data["y"][::step],
        frame["magx"][::step, ::step],
        frame["magy"][::step, ::step],
        density=0.85,
        color=color,
        linewidth=0.35,
        arrowsize=0.45,
    )


def _save(fig: Any, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_evolution(data: dict[str, Any]) -> None:
    targets = [0.0, 0.35, 0.70, float(data["times"][-1])]
    indices = [_nearest(data, target) for target in targets]
    j_limit, _, _, _ = _field_limits(data)
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 9.4), constrained_layout=True)
    image = None
    for ax, index in zip(axes.flat, indices, strict=True):
        frame = data["frames"][index]
        image = ax.pcolormesh(
            data["x"],
            data["y"],
            frame["jz"],
            shading="auto",
            cmap="coolwarm",
            norm=TwoSlopeNorm(vmin=-j_limit, vcenter=0.0, vmax=j_limit),
        )
        levels = np.linspace(float(frame["psi"].min()), float(frame["psi"].max()), 15)
        ax.contour(
            data["x"], data["y"], frame["psi"], levels=levels, colors="#00d4e8", linewidths=0.45
        )
        _stream(ax, data, frame, color="white")
        ax.set_aspect("equal")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title(f"t = {frame['time']:.3f}")
    assert image is not None
    fig.colorbar(image, ax=axes.ravel().tolist(), shrink=0.86, label=r"$J_z$")
    eta = float(data["realized"].get("eta", np.nan))
    s_eta = 1.0 / eta if eta > 0 else float("nan")
    title = (
        "FLASH resistive-MHD island coalescence: actual guided anchor "
        f"($S_\\eta={s_eta:.0f}$, {data['nx']}²)\n"
        "HDF5 output from the operator-validated, permanently non-evidentiary anchor"
    )
    fig.suptitle(
        title,
        fontsize=14,
    )
    _save(fig, "island_coalescence_evolution.png")


def _plot_layer(data: dict[str, Any]) -> None:
    index = _nearest(data, 0.70)
    frame = data["frames"][index]
    j_limit, rho_min, rho_max, vx_limit = _field_limits(data)
    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.7))

    current = axes[0].pcolormesh(
        data["x"],
        data["y"],
        frame["jz"],
        shading="auto",
        cmap="coolwarm",
        norm=TwoSlopeNorm(vmin=-j_limit, vcenter=0.0, vmax=j_limit),
    )
    levels = np.linspace(float(frame["psi"].min()), float(frame["psi"].max()), 15)
    axes[0].contour(
        data["x"], data["y"], frame["psi"], levels=levels, colors="#00d4e8", linewidths=0.45
    )
    axes[0].set_title(r"Current density $J_z$ and magnetic flux")
    fig.colorbar(current, ax=axes[0], label=r"$J_z$")

    density = axes[1].pcolormesh(
        data["x"],
        data["y"],
        frame["dens"],
        shading="auto",
        cmap="viridis",
        vmin=rho_min,
        vmax=rho_max,
    )
    axes[1].contour(
        data["x"], data["y"], frame["pres"], levels=12, colors="white", linewidths=0.4, alpha=0.8
    )
    axes[1].set_title(r"Density $\rho$ (pressure contours)")
    fig.colorbar(density, ax=axes[1], label=r"$\rho$")

    velocity = axes[2].pcolormesh(
        data["x"],
        data["y"],
        frame["velx"],
        shading="auto",
        cmap="coolwarm",
        norm=TwoSlopeNorm(vmin=-vx_limit, vcenter=0.0, vmax=vx_limit),
    )
    step = max(1, data["nx"] // 32)
    axes[2].streamplot(
        data["x"][::step],
        data["y"][::step],
        frame["velx"][::step, ::step],
        frame["vely"][::step, ::step],
        density=0.85,
        color="black",
        linewidth=0.35,
        arrowsize=0.45,
    )
    axes[2].set_title(r"Outflow $v_x$ and velocity streamlines")
    fig.colorbar(velocity, ax=axes[2], label=r"$v_x$")

    for ax in axes:
        ax.set_aspect("equal")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    flux = (
        data["rows"][index]["reconnected_flux_from_by"]
        if index < len(data["rows"])
        else float("nan")
    )
    title = (
        "Reconnection-layer diagnostics at actual "
        f"$t={frame['time']:.4f}$ ($S_\\eta=1000$, {data['nx']}²; "
        f"$\\psi_{{rec}}={flux:.4f}$)"
    )
    fig.suptitle(
        title,
        fontsize=13,
    )
    fig.tight_layout(rect=(0.01, 0.075, 0.99, 0.91))
    fig.text(
        0.5,
        0.005,
        "Fields and streamlines are read directly from the guided FLASH HDF5 state; "
        "this is not campaign evidence.",
        ha="center",
        fontsize=9,
    )
    _save(fig, "reconnection_layer_physics.png")


def _plot_profiles(data: dict[str, Any]) -> None:
    index = _nearest(data, 0.70)
    frame = data["frames"][index]
    x0 = int(np.argmin(np.abs(data["x"])))
    y0 = int(np.argmin(np.abs(data["y"])))
    rows = data["rows"]
    times = np.asarray([row["time"] for row in rows], dtype=float)
    psi_rec = np.asarray([row["reconnected_flux_from_by"] for row in rows], dtype=float)
    divb = np.asarray([row["max_abs_divb"] for row in rows], dtype=float)
    metrics = data["metrics"]

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.5))
    ax = axes[0]
    (line_bx,) = ax.plot(data["y"], frame["magx"][:, x0], color="#1769aa", lw=1.8, label=r"$B_x$")
    ax.set_xlabel("y at x ≈ 0")
    ax.set_ylabel(r"$B_x$", color="#1769aa")
    ax.tick_params(axis="y", colors="#1769aa")
    ax2 = ax.twinx()
    (line_jz,) = ax2.plot(data["y"], frame["jz"][:, x0], color="#c62828", lw=1.5, label=r"$J_z$")
    ax2.set_ylabel(r"$J_z$", color="#c62828")
    ax2.tick_params(axis="y", colors="#c62828")
    ax.set_title("Normal cut through the sheet")
    ax.grid(alpha=0.25)
    ax.legend([line_bx, line_jz], [r"$B_x$", r"$J_z$"], loc="best", frameon=False)

    ax = axes[1]
    (line_vx,) = ax.plot(data["x"], frame["velx"][y0, :], color="#2e7d32", lw=1.8, label=r"$v_x$")
    ax.set_xlabel("x at y ≈ 0")
    ax.set_ylabel(r"$v_x$", color="#2e7d32")
    ax.tick_params(axis="y", colors="#2e7d32")
    ax2 = ax.twinx()
    (line_rho,) = ax2.plot(
        data["x"], frame["dens"][y0, :], color="#7b1fa2", lw=1.5, label=r"$\rho$"
    )
    ax2.set_ylabel(r"$\rho$", color="#7b1fa2")
    ax2.tick_params(axis="y", colors="#7b1fa2")
    ax.set_title("Outflow cut through the X-point")
    ax.grid(alpha=0.25)
    ax.legend([line_vx, line_rho], [r"$v_x$", r"$\rho$"], loc="best", frameon=False)

    ax = axes[2]
    ax.plot(times, psi_rec, color="#1769aa", lw=2.0, label=r"$\psi_{rec}$")
    ax.axhspan(0.01, 0.05, color="#90caf9", alpha=0.25, label="analysis window")
    low = metrics.get("flux_low_crossing_time")
    high = metrics.get("flux_high_crossing_time")
    if low is not None and high is not None:
        ax.axvline(float(low), color="#1565c0", ls="--", lw=0.9)
        ax.axvline(float(high), color="#1565c0", ls="--", lw=0.9)
    ax.set_xlabel("simulation time")
    ax.set_ylabel(r"reconnected flux $\psi_{rec}$")
    ax.set_title("Flux window and divergence check")
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", frameon=False)
    ax2 = ax.twinx()
    positive_divb = np.maximum(divb, np.finfo(float).tiny)
    ax2.semilogy(
        times,
        positive_divb,
        color="#c62828",
        lw=1.2,
        alpha=0.8,
        label=r"$\max|\nabla\cdot B|$",
    )
    ax2.set_ylabel(r"$\max|\nabla\cdot B|$")
    ax2.legend(loc="lower right", frameon=False)

    title = (
        "Actual guided-anchor profiles "
        f"($S_\\eta=1000$, explicit resistivity, {data['nx']}²; "
        f"snapshot t={frame['time']:.4f})"
    )
    fig.suptitle(title, fontsize=13)
    fig.tight_layout(rect=(0.01, 0.075, 0.99, 0.91))
    fig.text(
        0.5,
        0.005,
        "The anchor reaches the declared flux window; its record remains "
        "permanently non-evidentiary.",
        ha="center",
        fontsize=9,
    )
    _save(fig, "reconnection_microphysics_profiles.png")


def _plot_scaling(audit_path: Path) -> None:
    audit = json.loads(audit_path.read_text())
    root = audit["root"]
    refinement = audit["root_refinement"]
    repair = audit["repair"]
    root_points = root["points"]
    repair_points = repair["points"]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.3), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    root_s = np.asarray([point["S_eta"] for point in root_points], dtype=float)
    root_r = np.asarray([point["R"] for point in root_points], dtype=float)
    ax.loglog(root_s, root_r, "o", color="#1565c0", ms=6, label="root campaign (base)")
    refinement_point = refinement["point"]
    ax.loglog(
        [refinement_point["S_eta"]],
        [refinement_point["R"]],
        "^",
        color="#ef6c00",
        ms=7,
        label="512² refinement",
    )
    repair_s = np.asarray([point["S_eta"] for point in repair_points], dtype=float)
    repair_r = np.asarray([point["R"] for point in repair_points], dtype=float)
    ax.loglog(repair_s, repair_r, "s", color="#2e7d32", ms=5.5, label="repair audit extract")
    grid = np.geomspace(200.0, 4500.0, 200)

    def fit_line(fit: dict[str, Any]) -> np.ndarray:
        return 10.0 ** (float(fit["intercept"]) + float(fit["p_hat"]) * np.log10(grid))

    ax.loglog(
        grid,
        fit_line(root["fit"]),
        color="#1565c0",
        lw=1.4,
        label=rf"root fit $p={root['fit']['p_hat']:.4f}$",
    )
    ax.loglog(
        grid,
        fit_line(repair["fit"]),
        color="#2e7d32",
        lw=1.4,
        ls="--",
        label=rf"repair fit $p={repair['fit']['p_hat']:.4f}$",
    )
    reference = root_r[root_s.tolist().index(1000.0)] * (grid / 1000.0) ** (-0.5)
    ax.loglog(grid, reference, color="#c62828", ls=":", lw=1.4, label=r"reference slope $p=-1/2$")
    ax.set_xlabel(r"nominal inverse resistivity $S_\eta=1/\eta$")
    ax.set_ylabel(r"normalized rate $R$")
    ax.set_title("Scaling data and fitted slopes")
    ax.grid(which="both", alpha=0.22)
    ax.legend(fontsize=8.2, frameon=False, loc="best")

    ax = axes[1]
    intervals = [
        ("root target", root["target_interval"], "#bdbdbd"),
        ("root 95% CI", root["fit"]["ci_95"], "#1565c0"),
        ("repair target", repair["target_interval"], "#bdbdbd"),
        ("repair 95% CI", repair["fit"]["ci_95"], "#2e7d32"),
    ]
    y_positions = np.arange(len(intervals))[::-1]
    for y_position, (label, interval, color) in zip(y_positions, intervals, strict=True):
        lo, hi = map(float, interval)
        ax.plot(
            [lo, hi],
            [y_position, y_position],
            color=color,
            lw=7 if "target" in label else 3.5,
            solid_capstyle="butt",
        )
        if "CI" in label:
            ax.plot([(lo + hi) / 2], [y_position], "o", color=color, ms=6)
        ax.text(-0.625, y_position, label, va="center", ha="left", fontsize=9)
    ax.axvline(-0.40, color="#c62828", ls="--", lw=1.1)
    ax.axvline(-0.38, color="#6a1b9a", ls="--", lw=1.1)
    ax.set_yticks([])
    ax.set_xlim(-0.63, -0.35)
    ax.set_ylim(-0.7, len(intervals) - 0.3)
    ax.set_xlabel(r"power-law exponent $p$")
    ax.set_title("Adjudication intervals")
    ax.grid(axis="x", alpha=0.22)
    ax.text(
        -0.40, 3.65, "root boundary", color="#c62828", rotation=90, ha="right", va="top", fontsize=8
    )
    ax.text(
        -0.38,
        3.65,
        "repair boundary",
        color="#6a1b9a",
        rotation=90,
        ha="right",
        va="top",
        fontsize=8,
    )

    fig.suptitle("Campaign audit extract: root falsified; repair branch still open", fontsize=14)
    fig.tight_layout(rect=(0.01, 0.09, 0.99, 0.92))
    fig.text(
        0.5,
        0.005,
        "The repair fit is shown for audit transparency only: its analyzer lineage "
        "was not closure-eligible, so no repair support/falsification verdict was recorded.",
        ha="center",
        fontsize=8.8,
    )
    _save(fig, "scaling_law_discovery.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor-dir", type=Path, default=DEFAULT_ANCHOR)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--campaign-audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()
    data = _load_anchor(args.anchor_dir, args.summary)
    _plot_evolution(data)
    _plot_layer(data)
    _plot_profiles(data)
    _plot_scaling(args.campaign_audit)
    print(f"wrote figures to {FIGURES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
