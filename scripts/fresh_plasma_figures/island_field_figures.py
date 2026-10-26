#!/usr/bin/env python3
"""Render one island-case figure with retained fields and the scaling test.

The frozen bundle contains actual snapshots of a fresh accepted production
trajectory identified in benchmark_island.json. The source receipt,
original raw archive and selected-array comparison were checked when freezing
the bundle; the self-contained rendering rechecks its hash and metadata.
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
from matplotlib.ticker import FormatStrFormatter

from .controls import draw_island_scaling

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "demos/resistive_mhd_island_coalescence/fresh_v070_visual_data"
OUT = ROOT / "docs/_static/demos"
NAVY = "#18334A"


def load_fields():
    meta = json.loads((DATA / "island_fields.json").read_text())
    path = DATA / meta["frozen_file"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != meta["frozen_sha256"]:
        raise ValueError("Frozen FLASH plotting fields changed")
    with np.load(path, allow_pickle=False) as archive:
        arrays = {key: archive[key].astype(float) for key in archive.files}
    shape = tuple(meta["array_shape"])
    for name in ("dens", "magx", "magy"):
        if arrays[name].shape != shape or not np.isfinite(arrays[name]).all():
            raise ValueError(f"Unexpected or nonfinite field: {name}")
    np.testing.assert_array_equal(arrays["times"], meta["times"])
    n = shape[-1]
    x = -0.5 + (np.arange(n) + 0.5) / n
    np.testing.assert_allclose(arrays["x"], x, rtol=0, atol=2e-8)
    # Regenerate exact cell-center coordinates, avoiding float32 spacing noise.
    arrays["x"] = x
    scaling = json.loads((DATA / "benchmark_island.json").read_text())
    cases = [case for case in scaling["cases"] if case["experiment"] == meta["source_experiment"]]
    if len(cases) != 1 or cases[0]["S"] != meta["S_eta"] or cases[0]["n"] != n:
        raise ValueError("Field trajectory no longer matches the scaling record")
    return arrays, meta


def render():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 9,
            "axes.titlesize": 9.5,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
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
    a, meta = load_fields()
    chosen = meta["figure_bundle_indices"]
    x = a["x"]
    n = len(x)
    current = np.gradient(a["magy"], 1 / n, axis=2, edge_order=2) - np.gradient(
        a["magx"], 1 / n, axis=1, edge_order=2
    )
    density_limits = [float(a["dens"][chosen].min()), float(a["dens"][chosen].max())]
    # A symmetric full range retains extreme currents, with no percentile clip.
    current_limit = float(np.abs(current[chosen]).max())
    norm = TwoSlopeNorm(vmin=-current_limit, vcenter=0, vmax=current_limit)

    fig = plt.figure(figsize=(7.2, 6.6))
    fields_grid = fig.add_gridspec(
        2, 3, left=0.093, right=0.86, bottom=0.47, top=0.96, wspace=0.34, hspace=0.16
    )
    axes = fields_grid.subplots(sharex=True, sharey=True)
    for col, index in enumerate(chosen):
        density_image = axes[0, col].imshow(
            a["dens"][index],
            origin="lower",
            extent=(-0.5, 0.5, -0.5, 0.5),
            interpolation="none",
            cmap="viridis",
            vmin=density_limits[0],
            vmax=density_limits[1],
            rasterized=True,
        )
        axes[0, col].streamplot(
            x,
            x,
            a["magx"][index],
            a["magy"][index],
            color="#F6FCFF",
            density=0.72,
            linewidth=0.50,
            arrowsize=0.42,
            broken_streamlines=False,
        )
        current_image = axes[1, col].imshow(
            current[index],
            origin="lower",
            extent=(-0.5, 0.5, -0.5, 0.5),
            interpolation="none",
            cmap="RdBu_r",
            norm=norm,
            rasterized=True,
        )
        axes[0, col].set_title(rf"$t/\tau_A = {a['times'][index]:.2f}$", pad=7)
        for row in (0, 1):
            ax = axes[row, col]
            ax.set(xlim=(-0.5, 0.5), ylim=(-0.5, 0.5), xticks=[-0.5, 0, 0.5], yticks=[-0.5, 0, 0.5])
            ax.set_aspect("equal")
            ax.tick_params(length=2.8, pad=2.5)
            ax.xaxis.set_major_formatter(FormatStrFormatter("%g"))
            ax.yaxis.set_major_formatter(FormatStrFormatter("%g"))
            ax.text(
                0.035,
                0.94,
                f"({'abcdef'[row * 3 + col]})",
                transform=ax.transAxes,
                va="top",
                color=NAVY,
                weight="bold",
                fontsize=9,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.86, "pad": 1.4},
            )
        axes[1, col].set_xlabel(r"$x/L_0$", labelpad=3)
    axes[0, 0].set_ylabel(r"Density and field lines" + "\n" + r"$y/L_0$")
    axes[1, 0].set_ylabel(r"Out-of-plane current" + "\n" + r"$y/L_0$")

    fig.canvas.draw()
    for row, im, label, ticks in [
        (0, density_image, r"$\rho/\rho_0$", [0.95, 1.00, 1.05, 1.10]),
        (1, current_image, r"$j_z$", [-40, -20, 0, 20, 40]),
    ]:
        position = axes[row, -1].get_position()
        cax = fig.add_axes([0.882, position.y0, 0.020, position.height])
        cb = fig.colorbar(im, cax=cax, ticks=ticks)
        cb.set_label(label, labelpad=5)
        cb.ax.tick_params(length=2.5, pad=3, labelsize=8)
        cb.outline.set_linewidth(0.5)
    scaling = fig.add_axes([0.12, 0.09, 0.80, 0.25])
    draw_island_scaling(scaling, title="(g) Reconnection-rate scaling")
    OUT.mkdir(exist_ok=True)
    for extension in ("pdf", "png"):
        fig.savefig(
            OUT / f"fresh-v070-island-fields.{extension}",
            dpi=400,
            bbox_inches="tight",
            pad_inches=0.08,
        )
    plt.close(fig)
    print(
        json.dumps(
            {
                "figure": "docs/_static/demos/fresh-v070-island-fields.pdf",
                "source_experiment": meta["source_experiment"],
                "times": meta["figure_times"],
                "density_range": density_limits,
                "current_color_range": [-current_limit, current_limit],
                "color_clipping": False,
                "bundle_hash_valid": True,
                "matches_scaling_record": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    render()
