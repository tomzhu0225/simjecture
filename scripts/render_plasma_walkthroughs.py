"""Render field-led demo figures from small, hash-bound plotting bundles.

No solver or model calls. These editorial figures do not change claim dispositions.
Run with the project's NumPy/Matplotlib scientific environment from any directory.
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
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/_static/demos"
INK, BLUE, TEAL, ORANGE = "#192a40", "#2463a5", "#067a78", "#ba691b"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.labelcolor": INK,
        "text.color": INK,
        "axes.titleweight": "bold",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.facecolor": "white",
    }
)


def load(name):
    path = ROOT / "demos" / name / "visual_data"
    meta = json.loads((path / "provenance.json").read_text())
    if hashlib.sha256((path / "fields.npz").read_bytes()).hexdigest() != meta["bundle_sha256"]:
        raise ValueError("Plotting bundle changed")
    with np.load(path / "fields.npz") as z:
        return {k: z[k] for k in z.files}, meta


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for suffix in ["png", "pdf", "svg"]:
        fig.savefig(OUT / f"{name}.{suffix}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def heading(fig, title, subtitle):
    fig.suptitle(title, x=0.065, y=0.985, ha="left", fontsize=20, weight="bold")
    fig.text(0.065, 0.900, subtitle, fontsize=10.5, color="#516277")


def stream(ax, x, z, bx, bz, color="#eff7fc"):
    ax.streamplot(
        x,
        z,
        bx,
        bz,
        color=color,
        density=0.8,
        linewidth=0.55,
        arrowsize=0.55,
        broken_streamlines=False,
    )


def island_fields(a, meta):
    fig, axes = plt.subplots(2, 4, figsize=(14, 8))
    heading(
        fig,
        "Watch the magnetic islands evolve",
        "Fresh FLASH trajectory · Sη = 1000 · 384 × 384 cells · all times and fields normalized",
    )
    x = a["x"].astype(float)
    dx = 1.0 / len(x)
    current = np.gradient(a["magy"], dx, axis=2) - np.gradient(a["magx"], dx, axis=1)
    limit = float(np.quantile(np.abs(current), 0.995))
    lo, hi = float(a["dens"].min()), float(a["dens"].max())
    for j, t in enumerate(a["times"]):
        im = axes[0, j].imshow(
            a["dens"][j],
            origin="lower",
            extent=(-0.5, 0.5, -0.5, 0.5),
            cmap="viridis",
            vmin=lo,
            vmax=hi,
            rasterized=True,
        )
        stream(axes[0, j], x, x, a["magx"][j], a["magy"][j])
        jm = axes[1, j].imshow(
            current[j],
            origin="lower",
            extent=(-0.5, 0.5, -0.5, 0.5),
            cmap="RdBu_r",
            norm=TwoSlopeNorm(0, -limit, limit),
            rasterized=True,
        )
        axes[0, j].set_title(f"t = {t:.3f}", fontsize=12)
        axes[1, j].set_xlabel("x / L₀")
        for ax in axes[:, j]:
            ax.set(xlim=(-0.5, 0.5), ylim=(-0.5, 0.5))
            ax.set_aspect("equal")
            ax.set_xticks([-0.5, 0, 0.5])
            ax.set_yticks([-0.5, 0, 0.5])
        if j == 0:
            axes[0, j].set_ylabel("Density + field lines\ny / L₀")
            axes[1, j].set_ylabel("Out-of-plane current Jz\ny / L₀")
    fig.subplots_adjust(left=0.07, right=0.90, top=0.84, bottom=0.14, wspace=0.18, hspace=0.18)
    fig.colorbar(im, cax=fig.add_axes([0.92, 0.53, 0.014, 0.29]), label="ρ / ρ₀")
    fig.colorbar(
        jm, cax=fig.add_axes([0.92, 0.17, 0.014, 0.29]), label="Jz (code units)", extend="both"
    )
    fig.text(
        0.065,
        0.063,
        "Density shows plasma compression; field lines show magnetic "
        "geometry. The lower row locates the current sheet.",
        fontsize=11,
    )
    fig.text(
        0.065,
        0.026,
        "Source: "
        + meta["source_experiment"]
        + " · shared color scales; current colors clipped at the 99.5th percentile for visibility.",
        fontsize=9,
        color="#516277",
    )
    save(fig, "island-field-walkthrough")


def macro_patch(a, meta):
    fig, axes = plt.subplots(1, 3, figsize=(14, 6.3))
    heading(
        fig,
        "From a fluid current sheet to kinetic particles",
        "Actual FLASH state → mapped initial conditions → WarpX evolution "
        "· one-way transfer, with no kinetic feedback to FLASH",
    )
    x, z = a["macro_x"].astype(float), a["macro_z"].astype(float)
    bx, bz = a["macro_bx"], a["macro_bz"]
    j = np.gradient(bz, x[1] - x[0], axis=1) - np.gradient(bx, z[1] - z[0], axis=0)
    bound = float(np.quantile(abs(j), 0.995))
    for ax, extent, title in [
        (axes[0], (-0.5, 0.5, -0.5, 0.5), "1  FLASH source · 512²"),
        (axes[1], (-0.075, 0.075, -0.075, 0.075), "2  The measurement region"),
    ]:
        im = ax.imshow(
            j,
            extent=(-0.5, 0.5, -0.5, 0.5),
            origin="lower",
            cmap="RdBu_r",
            norm=TwoSlopeNorm(0, -bound, bound),
            rasterized=True,
        )
        stream(ax, x, z, bx, bz, color="#42556a")
        ax.set(xlim=extent[:2], ylim=extent[2:], xlabel="X / L₀", ylabel="Z / L₀")
        ax.set_title(title, fontsize=12)
        ax.add_patch(Rectangle((-0.04, -0.015), 0.08, 0.03, fill=False, ec="#ffe95d", lw=2))
    for half, color, style in [(0.3, "#ffad45", "-"), (0.45, "#ffad45", "--")]:
        axes[0].add_patch(
            Rectangle((-half, -half), 2 * half, 2 * half, fill=False, ec=color, lw=1.8, ls=style)
        )
    axes[0].text(
        -0.45,
        0.40,
        "Larger-patch control",
        color=INK,
        fontsize=9,
        bbox=dict(fc="white", ec="none", alpha=0.8),
    )
    axes[0].text(
        -0.28,
        0.24,
        "Standard PIC domain",
        color=INK,
        fontsize=9,
        bbox=dict(fc="white", ec="none", alpha=0.8),
    )
    axes[1].text(
        0,
        0.022,
        "16 pressure bins",
        color=INK,
        ha="center",
        fontsize=9,
        bbox=dict(fc="white", ec="none", alpha=0.8),
    )
    for vx in np.linspace(-0.04, 0.04, 5):
        axes[1].plot([vx, vx], [-0.015, 0.015], color="#ffe95d", lw=0.7)
    for vz in np.linspace(-0.015, 0.015, 5):
        axes[1].plot([-0.04, 0.04], [vz, vz], color="#ffe95d", lw=0.7)
    b0 = meta["patch"]["scales"]["magnetic_T"]
    by = a["final_by"] / b0
    limit = float(np.max(abs(by)))
    im2 = axes[2].imshow(
        by,
        origin="lower",
        extent=(-0.3, 0.3, -0.3, 0.3),
        cmap="RdBu_r",
        norm=TwoSlopeNorm(0, -limit, limit),
        rasterized=True,
    )
    axes[2].add_patch(Rectangle((-0.04, -0.015), 0.08, 0.03, fill=False, ec="#ffe95d", lw=2))
    axes[2].set(title="3  Kinetic field at the end", xlabel="X / L₀", ylabel="Z / L₀")
    for ax in axes:
        ax.set_aspect("equal")
    fig.subplots_adjust(top=0.81, bottom=0.27, left=0.06, right=0.98, wspace=0.32)
    fig.colorbar(
        im,
        ax=list(axes[:2]),
        fraction=0.025,
        pad=0.02,
        label="FLASH Jz (code units)",
        extend="both",
    )
    fig.colorbar(im2, ax=axes[2], fraction=0.045, pad=0.025, label="WarpX Bᵧ / B₀")
    fig.text(
        0.065,
        0.15,
        "Orange: kinetic domains. Yellow: fixed pressure-measurement "
        "region. The right panel shows an evolved out-of-plane field,",
        fontsize=10.5,
    )
    fig.text(
        0.065,
        0.112,
        "WarpX evolves the mapped state. Initial Bᵧ = 0; final tΩci = "
        + f"{a['times'][-1]:.4f}. Particle physics is collisionless; FLASH "
        f"resistivity is not evolved in PIC.",
        fontsize=10,
    )
    fig.text(
        0.065,
        0.053,
        "FLASH t = "
        + f"{meta['patch']['source_time_code']:.6f}"
        + " · L₀ = 1.107 mm, B₀ = 16.36 T, mi/me = 25 are declared mapping choices.",
        fontsize=9,
        color="#516277",
    )
    save(fig, "coupled-field-handoff")


def pressure_maps(a, meta):
    fig, axes = plt.subplots(1, 3, figsize=(13, 5.5), gridspec_kw={"width_ratios": [1, 1, 1.1]})
    heading(
        fig,
        "Where the pressure departs from isotropy",
        "Fresh WarpX particle-count control · 576² cells · 32 particles "
        "per cell per species · 4 × 4 measurement bins",
    )
    times = a["times"]
    target = np.r_[0.3, times[(times > 0.3) & (times < 0.8)], 0.8]
    means = {}
    for ax, sp in zip(axes[:2], ["ions", "electrons"], strict=True):
        values = np.stack(
            [np.interp(target, times, a[sp + "_departure"][:, i]) for i in range(16)], axis=1
        )
        field = np.trapezoid(values, target, axis=0) / 0.5
        means[sp] = float(field.mean())
        expected = meta["analysis"]["cases"]["fine32"]["species"][sp]["area_time_mean"]
        if not np.isclose(means[sp], expected, rtol=0, atol=1e-7):
            raise ValueError("Rendered pressure map disagrees with the recorded analysis")
        im = ax.imshow(
            field.reshape(4, 4),
            extent=(-0.04 / 0.024, 0.04 / 0.024, -0.015 / 0.024, 0.015 / 0.024),
            origin="lower",
            vmin=0,
            vmax=0.20,
            cmap="viridis",
            interpolation="nearest",
            aspect="equal",
        )
        ax.set_title(sp.capitalize() + f" · mean {field.mean():.4f}", fontsize=12)
        ax.set(xlabel="X / di,ref", ylabel="Z / di,ref")
        for j in range(4):
            for i in range(4):
                ax.text(
                    (i + 0.5) / 4,
                    (j + 0.5) / 4,
                    f"{field.reshape(4, 4)[j, i]:.3f}",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=9,
                )
    axes[2].axis("off")
    axes[2].text(0, 0.95, "What the colors mean", weight="bold", fontsize=13, va="top")
    axes[2].text(
        0,
        0.80,
        "0 = isotropic pressure tensor\n0.20 = hypothesis "
        "threshold\n"
        "\n"
        "Each tile averages the local tensor\n"
        "departure over tΩci = 0.3–0.8.\n"
        "All three velocity components enter.\n"
        "\n"
        "The two means are below 0.20.\n"
        "Controls and uncertainty still matter:\n"
        "a low value alone is not a verdict.\n"
        "\n"
        "Outcome: unresolved.\n"
        "The planned fresh-seed evidence\n"
        "run was deferred for lack of time.",
        fontsize=11,
        va="top",
        linespacing=1.55,
    )
    fig.subplots_adjust(left=0.07, right=0.98, top=0.81, bottom=0.27, wspace=0.42)
    fig.colorbar(
        im,
        cax=fig.add_axes([0.10, 0.18, 0.45, 0.025]),
        orientation="horizontal",
        label="Local pressure-tensor departure A (dimensionless)",
    )
    fig.text(
        0.065,
        0.046,
        "Source: "
        + meta["kinetic_experiment"]
        + " · raw moment arrays, time interpolation and trapezoidal "
        "averaging; no spatial smoothing.",
        fontsize=9,
        color="#516277",
    )
    save(fig, "coupled-pressure-map")


def box(ax, x, y, w, h, title, body, *, color=BLUE, dashed=False):
    rect = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=.012,rounding_size=.015",
        facecolor="#f5f8fc",
        edgecolor=color,
        lw=1.4,
        ls="--" if dashed else "-",
    )
    ax.add_patch(rect)
    ax.text(
        x, y + h * 0.20, title, ha="center", va="center", fontsize=11, weight="bold", color=color
    )
    ax.text(x, y - h * 0.17, body, ha="center", va="center", fontsize=9.5, linespacing=1.4)


def arrow(ax, start, end, color="#9aaabb"):
    ax.add_patch(
        FancyArrowPatch(
            start, end, arrowstyle="-|>", mutation_scale=12, color=color, lw=1.1, zorder=0
        )
    )


def evidence_map(kind, meta):
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    fig.subplots_adjust(left=0.035, right=0.965, top=0.86, bottom=0.075)
    if kind == "island":
        heading(
            fig,
            "The actual island-coalescence evidence map",
            "One original hypothesis · five baseline cases · two refinements · "
            "preserved experiment receipts",
        )
        box(
            ax,
            0.5,
            0.91,
            0.83,
            0.105,
            "QUESTION: one resolved pre-plasmoid scaling branch?",
            "R ∝ Sηᵖ, −0.60 ≤ p ≤ −0.40, over Sη = 250–4000",
        )
        xs = np.linspace(0.09, 0.91, 5)
        for x, S in zip(xs, [250, 500, 1000, 2000, 4000], strict=True):
            row = next(c for c in meta["analysis"]["cases"] if c["S"] == S and c["n"] == 256)
            box(ax, x, 0.66, 0.15, 0.13, f"Sη = {S}", f"256² · completed\nR = {row['rate']:.5f}")
            arrow(ax, (0.5, 0.85), (x, 0.74))
        box(
            ax,
            0.28,
            0.42,
            0.38,
            0.13,
            "MATCHED REFINEMENT",
            "250 and 1000 repeated at 384²\nRate changes: 0.136% and 0.223%",
            color=TEAL,
        )
        box(
            ax,
            0.74,
            0.42,
            0.38,
            0.13,
            "FIVE-POINT FIT",
            "Exploratory final analysis\nEffective exponent p = −0.40785",
            color=BLUE,
        )
        for x in xs:
            arrow(ax, (x, 0.585), (0.74, 0.495))
        for x in [xs[0], xs[2]]:
            arrow(ax, (x, 0.585), (0.28, 0.495), TEAL)
        box(
            ax,
            0.5,
            0.16,
            0.83,
            0.15,
            "UNRESOLVED · no accepted scientific verdict",
            "Two refined points cannot test full-range curvature. High-S "
            "refinement remains missing.\nThe report reviewer timed out; "
            "successful simulations do not equal accepted support.",
            color=ORANGE,
        )
        arrow(ax, (0.28, 0.345), (0.5, 0.25))
        arrow(ax, (0.74, 0.345), (0.5, 0.25))
        note = (
            "Methods: revised once, then approved for evidence collection. "
            "Seven fresh physics trajectories completed; final postprocessing remains exploratory."
        )
    else:
        heading(
            fig,
            "The actual FLASH → WarpX evidence map",
            "A traceable source state, a local kinetic test, and explicit "
            "numerical controls · both solvers really ran",
        )
        box(
            ax,
            0.5,
            0.92,
            0.86,
            0.105,
            "QUESTION: does local pressure stay nearly isotropic?",
            "Both species: area/time-averaged A ≤ 0.20 over the fixed window Δt Ωci = 0.5",
        )
        box(
            ax,
            0.16,
            0.68,
            0.25,
            0.15,
            "FLASH SOURCE",
            "512² MHD state at t = 0.800111\nSource geometry and "
            "current\nHistorical parent trajectory",
            color="#60748b",
        )
        box(
            ax,
            0.50,
            0.68,
            0.25,
            0.15,
            "RECORDED TRANSFER",
            "(X,Y,Z) = (x,−z,y)\nFields, density, pressure, drifts\nDeclared SI mapping",
            color=TEAL,
        )
        box(
            ax,
            0.84,
            0.68,
            0.25,
            0.15,
            "WARPX FOLLOW-UP",
            "576² · 32 particles/cell/species\nFresh full-window control\nAᵢ "
            "= 0.04383, Aₑ = 0.05955",
        )
        arrow(ax, (0.29, 0.68), (0.36, 0.68))
        arrow(ax, (0.63, 0.68), (0.70, 0.68))
        for x, title, body in [
            (0.18, "LARGER PATCH", "864², same cell scale\nBoundary sensitivity"),
            (0.50, "SMALLER TIMESTEP", "Matched 576² cells\nTemporal sensitivity"),
            (0.82, "MATCHED PARTICLE COUNT", "384² ↔ 576² at 32 ppc\nGrid and sampling separated"),
        ]:
            box(ax, x, 0.40, 0.27, 0.13, title, body, color="#60748b" if x < 0.8 else BLUE)
            arrow(ax, (0.84, 0.595), (x, 0.48))
        box(
            ax,
            0.32,
            0.145,
            0.53,
            0.14,
            "UNRESOLVED",
            "Controls support a useful finite measurement.\nNo accepted root "
            "claim; report review timed out.",
            color=ORANGE,
        )
        box(
            ax,
            0.80,
            0.145,
            0.32,
            0.14,
            "NEXT TEST · NOT RUN",
            "Reviewed full-window fresh seed\nDeferred at the compute cutoff",
            color=ORANGE,
            dashed=True,
        )
        for x in [0.18, 0.5, 0.82]:
            arrow(ax, (x, 0.325), (0.32, 0.225))
        arrow(ax, (0.60, 0.145), (0.625, 0.145), ORANGE)
        note = (
            "Gray: historical controls. Blue: fresh commissioning. Teal: "
            "explicit transfer. Dashed: a proposed experiment, "
            "never presented as completed evidence."
        )
    fig.text(0.065, 0.025, note, fontsize=9, color="#516277")
    save(fig, kind + "-evidence-map")


def main():
    a, meta = load("resistive_mhd_island_coalescence")
    island_fields(a, meta)
    evidence_map("island", meta)
    a, meta = load("flash_warpx_kinetic_patch")
    macro_patch(a, meta)
    pressure_maps(a, meta)
    evidence_map("coupled", meta)
    print("Rendered five field/evidence figures in PNG, PDF and SVG:", OUT)


if __name__ == "__main__":
    main()
