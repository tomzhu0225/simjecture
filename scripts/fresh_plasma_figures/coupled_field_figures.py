#!/usr/bin/env python3
"""Render one coupling-case figure with fields, pressure maps and controls.

Uses only data/coupled_fields.npz and data/coupled_fields.json (plus verification
against data/benchmark_coupled.json). No solver launches or model calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle
from matplotlib.ticker import FormatStrFormatter, MaxNLocator

from .controls import draw_pressure_controls

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "demos/flash_warpx_kinetic_patch/fresh_v070_visual_data"
OUT = ROOT / "docs/_static/demos"
NAVY = "#18334A"


def pressure_tiles(arrays, meta, coupled):
    """Integrate local departures over the recorded decision window."""
    measurement = meta.get("measurement", {})
    lower, upper = measurement.get("window", [0.3, 0.8])
    bins = int(measurement.get("bins_per_axis", 4))
    reference = measurement.get("reference_case", "fine32")
    times = arrays["times"]
    if not (
        lower < upper and times[0] <= lower and times[-1] >= upper and np.all(np.diff(times) > 0)
    ):
        raise ValueError("Recorded times do not cover the decision window monotonically")
    target = np.r_[lower, times[(times > lower) & (times < upper)], upper]
    tiles = {}
    for sp in ("ions", "electrons"):
        departure = arrays[f"{sp}_departure"]
        if departure.shape != (len(times), bins * bins):
            raise ValueError(f"{sp} pressure-map shape disagrees with recorded bins")
        vals = np.stack(
            [np.interp(target, times, departure[:, i]) for i in range(bins * bins)],
            axis=1,
        )
        field = np.trapezoid(vals, target, axis=0) / (upper - lower)
        expected = coupled["cases"][reference]["species"][sp]["area_time_mean"]
        if not np.isclose(float(field.mean()), expected, rtol=0, atol=1e-7):
            raise ValueError(f"{sp} pressure-map mean disagrees with benchmark_coupled.json")
        tiles[sp] = field.reshape(bins, bins)
    return tiles


def load_and_check():
    meta = json.loads((DATA / "coupled_fields.json").read_text())
    npz_path = DATA / meta["frozen_data_file"]
    if hashlib.sha256(npz_path.read_bytes()).hexdigest() != meta["frozen_data_sha256"]:
        raise ValueError("Frozen coupled_fields.npz hash mismatch")
    with np.load(npz_path, allow_pickle=False) as archive:
        arrays = {key: archive[key].astype(float) for key in archive.files}
    for key, arr in arrays.items():
        if not np.isfinite(arr).all():
            raise ValueError(f"Non-finite values in {key}")
    coupled = json.loads((DATA / "benchmark_coupled.json").read_text())
    return arrays, meta, pressure_tiles(arrays, meta, coupled)


def render():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.8,
            "axes.titlesize": 9.0,
            "xtick.labelsize": 7.8,
            "ytick.labelsize": 7.8,
            "axes.edgecolor": NAVY,
            "axes.labelcolor": NAVY,
            "text.color": NAVY,
            "xtick.color": NAVY,
            "ytick.color": NAVY,
            "axes.linewidth": 0.6,
            "pdf.fonttype": 42,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    a, meta, tiles = load_and_check()
    measurement = meta.get("measurement", {})
    roi = np.asarray(measurement.get("bounds_code", [[-0.04, 0.04], [-0.015, 0.015]]))
    bins = tiles["ions"].shape[0]
    patch_bounds = np.asarray(meta["patch"]["bounds_xz_m"]) / meta["patch"]["scales"]["length_m"]
    larger_bounds = np.asarray(
        meta.get("display", {}).get("larger_patch_bounds_code", [[-0.45, 0.45], [-0.45, 0.45]])
    )
    threshold = float(measurement.get("threshold", 0.20))
    pressure_max = max(threshold, max(float(v.max()) for v in tiles.values()))
    roi_width, roi_height = roi[:, 1] - roi[:, 0]
    x = a["macro_x"]
    z = a["macro_z"]
    bx, bz = a["macro_bx"], a["macro_bz"]
    dx = float(x[1] - x[0])
    dz = float(z[1] - z[0])
    macro_extent = (x[0] - dx / 2, x[-1] + dx / 2, z[0] - dz / 2, z[-1] + dz / 2)
    zoom = max(0.075, float(np.abs(roi).max()) * 1.875)
    source_grid = rf"{len(x)}^2" if len(x) == len(z) else rf"{len(x)}\times{len(z)}"
    jy = np.gradient(bx, dz, axis=0, edge_order=2) - np.gradient(bz, dx, axis=1, edge_order=2)
    j_limit = float(np.abs(jy).max())
    j_norm = TwoSlopeNorm(vmin=-j_limit, vcenter=0.0, vmax=j_limit)

    b0 = float(meta["patch"]["scales"]["magnetic_T"])
    by = a["final_by"] / b0
    by_limit = float(np.abs(by).max())
    by_norm = TwoSlopeNorm(vmin=-by_limit, vcenter=0.0, vmax=by_limit)

    fig = plt.figure(figsize=(7.4, 6.2))

    # Top row: three square field panels (a), (b), (c) with horizontal colorbars below
    y_top, h_top, w_top = 0.65, 0.29, 0.245
    ax_a = fig.add_axes([0.065, y_top, w_top, h_top])
    ax_b = fig.add_axes([0.398, y_top, w_top, h_top])
    ax_c = fig.add_axes([0.725, y_top, w_top, h_top])

    cax_j = fig.add_axes([0.135, 0.555, 0.440, 0.013])
    cax_b = fig.add_axes([0.735, 0.555, 0.225, 0.013])

    for ax, extent, title, tag in [
        (ax_a, macro_extent, rf"FLASH source (${source_grid}$)", "(a)"),
        (ax_b, (-zoom, zoom, -zoom, zoom), "Measurement region", "(b)"),
    ]:
        im_j = ax.imshow(
            jy,
            extent=macro_extent,
            origin="lower",
            interpolation="none",
            cmap="RdBu_r",
            norm=j_norm,
            rasterized=True,
        )
        ax.streamplot(
            x,
            z,
            bx,
            bz,
            color="#42556a",
            density=0.68,
            linewidth=0.48,
            arrowsize=0.42,
            broken_streamlines=False,
        )
        ax.add_patch(Rectangle(roi[:, 0], roi_width, roi_height, fill=False, ec="#ffe95d", lw=1.6))
        ax.set(xlim=extent[:2], ylim=extent[2:], xlabel=r"$X/L_0$", ylabel=r"$Z/L_0$")
        ax.set_title(title, pad=5)
        ax.set_aspect("equal")
        ax.tick_params(length=2.6, pad=2.0)
        ax.xaxis.set_major_formatter(FormatStrFormatter("%g"))
        ax.yaxis.set_major_formatter(FormatStrFormatter("%g"))
        ax.text(
            0.04,
            0.94,
            tag,
            transform=ax.transAxes,
            va="top",
            color=NAVY,
            weight="bold",
            fontsize=8.8,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 1.3},
        )

    ax_a.set_xticks([-0.5, 0.0, 0.5])
    ax_a.set_yticks([-0.5, 0.0, 0.5])
    ax_b.set_xticks([-0.05, 0.0, 0.05])
    ax_b.set_yticks([-0.05, 0.0, 0.05])
    ax_b.set_ylabel(r"$Z/L_0$", labelpad=1)

    for bounds, style in [(patch_bounds, "-"), (larger_bounds, "--")]:
        ax_a.add_patch(
            Rectangle(
                bounds[:, 0],
                *(bounds[:, 1] - bounds[:, 0]),
                fill=False,
                ec="#ff9f38",
                lw=1.35,
                ls=style,
            )
        )
    ax_a.text(
        float(patch_bounds[0].mean()),
        patch_bounds[1, 0] + 0.04,
        "Standard PIC",
        color=NAVY,
        fontsize=8.0,
        ha="center",
        va="bottom",
        bbox={"fc": "white", "ec": "none", "alpha": 0.84, "pad": 1.0},
    )
    ax_a.text(
        float(larger_bounds[0].mean()),
        larger_bounds[1, 0] + 0.02,
        "Larger-patch control",
        color=NAVY,
        fontsize=8.0,
        ha="center",
        va="bottom",
        bbox={"fc": "white", "ec": "none", "alpha": 0.84, "pad": 1.0},
    )

    for vx in np.linspace(*roi[0], bins + 1):
        ax_b.plot([vx, vx], roi[1], color="#ffe95d", lw=0.65)
    for vz in np.linspace(*roi[1], bins + 1):
        ax_b.plot(roi[0], [vz, vz], color="#ffe95d", lw=0.65)

    im_b = ax_c.imshow(
        by,
        origin="lower",
        extent=patch_bounds.ravel(),
        interpolation="none",
        cmap="RdBu_r",
        norm=by_norm,
        rasterized=True,
    )
    ax_c.add_patch(Rectangle(roi[:, 0], roi_width, roi_height, fill=False, ec="#ffe95d", lw=1.6))
    ax_c.set(
        xlim=patch_bounds[0],
        ylim=patch_bounds[1],
        xticks=np.linspace(*patch_bounds[0], 3),
        yticks=np.linspace(*patch_bounds[1], 3),
        xlabel=r"$X/L_0$",
        ylabel=r"$Z/L_0$",
    )
    ax_c.set_ylabel(r"$Z/L_0$", labelpad=1)
    ax_c.set_title(r"Kinetic $B_y$", pad=5)
    ax_c.set_aspect("equal")
    ax_c.tick_params(length=2.6, pad=2.0)
    ax_c.xaxis.set_major_formatter(FormatStrFormatter("%g"))
    ax_c.yaxis.set_major_formatter(FormatStrFormatter("%g"))
    ax_c.text(
        0.04,
        0.94,
        "(c)",
        transform=ax_c.transAxes,
        va="top",
        color=NAVY,
        weight="bold",
        fontsize=8.8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 1.3},
    )

    def field_ticks(limit):
        ticks = MaxNLocator(nbins=5, symmetric=True).tick_values(-limit, limit)
        return ticks[np.abs(ticks) <= limit]

    cb_j = fig.colorbar(im_j, cax=cax_j, orientation="horizontal", ticks=field_ticks(j_limit))
    cb_j.set_label(r"Normalized FLASH out-of-plane current $j_y$", labelpad=2, fontsize=8.2)
    cb_j.ax.tick_params(length=2.2, pad=2.0, labelsize=7.5)
    cb_j.outline.set_linewidth(0.5)

    cb_b = fig.colorbar(im_b, cax=cax_b, orientation="horizontal", ticks=field_ticks(by_limit))
    cb_b.set_label(r"WarpX $B_y/B_0$", labelpad=2, fontsize=8.2)
    cb_b.ax.tick_params(length=2.2, pad=2.0, labelsize=7.5)
    cb_b.outline.set_linewidth(0.5)

    # Local maps share a column and scale; the adjacent panel tests the controls.
    ax_d = fig.add_axes([0.075, 0.29, 0.31, 0.14])
    ax_e = fig.add_axes([0.075, 0.10, 0.31, 0.14])
    cax_p = fig.add_axes([0.43, 0.10, 0.012, 0.33])
    ax_f = fig.add_axes([0.68, 0.10, 0.29, 0.33])

    di_code = float(meta["patch"]["scales"]["ion_skin_depth_code"])
    p_extent = roi.ravel() / di_code
    for _idx, (ax, sp, tag) in enumerate(
        [
            (ax_d, "ions", "(d)"),
            (ax_e, "electrons", "(e)"),
        ]
    ):
        grid = tiles[sp]
        im_p = ax.imshow(
            grid,
            extent=p_extent,
            origin="lower",
            vmin=0.0,
            vmax=pressure_max,
            cmap="viridis",
            interpolation="nearest",
            aspect="equal",
        )
        mean_val = float(grid.mean())
        sp_label = "Ions" if sp == "ions" else "Electrons"
        ax.set_title(rf"{tag} {sp_label} ($\langle A_{sp[0]}\rangle = {mean_val:.4f}$)", pad=5)
        ax.set(xlabel=r"$X/d_{i,\mathrm{ref}}$")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5, steps=[1, 2, 5, 10]))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=3))
        ax.set_ylabel(r"$Z/d_{i,\mathrm{ref}}$", labelpad=2)
        ax.tick_params(length=2.6, pad=2.0)
        for row_idx in range(bins):
            for col_idx in range(bins):
                ax.text(
                    (col_idx + 0.5) / bins,
                    (row_idx + 0.5) / bins,
                    f"{grid[row_idx, col_idx]:.3f}",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=8.2,
                    weight="bold",
                )
    ax_d.set_xlabel("")
    ax_d.tick_params(axis="x", labelbottom=False)

    cb_p = fig.colorbar(
        im_p, cax=cax_p, orientation="vertical", ticks=np.linspace(0, pressure_max, 5)
    )
    cb_p.set_label(r"$A_s$", labelpad=4, fontsize=8.8)
    cb_p.ax.tick_params(length=2.2, pad=2.0, labelsize=7.5)
    cb_p.outline.set_linewidth(0.5)
    draw_pressure_controls(ax_f, title="(f) Numerical controls")
    ax_f.set_title("(f) Numerical controls", loc="left", fontweight="bold", fontsize=9, pad=10)

    OUT.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(
            OUT / f"fresh-v070-coupled-fields.{ext}", dpi=400, bbox_inches="tight", pad_inches=0.08
        )
    plt.close(fig)
    print(
        json.dumps(
            {
                "figure": "docs/_static/demos/fresh-v070-coupled-fields.pdf",
                "source_experiment": meta["source_experiment"],
                "kinetic_experiment": meta["kinetic_experiment"],
                "jy_range": [-j_limit, j_limit],
                "by_range": [-by_limit, by_limit],
                "ion_mean": float(tiles["ions"].mean()),
                "electron_mean": float(tiles["electrons"].mean()),
                "color_clipping": False,
                "bundle_hash_valid": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    render()
