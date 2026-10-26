"""Control panels shared by the fresh v0.7.0 plasma figures."""

import json
from pathlib import Path

import numpy as np
from matplotlib.ticker import NullFormatter

ROOT = Path(__file__).resolve().parents[2]
NAVY, TEAL, ORANGE, GRAY = "#18334A", "#087F8C", "#D97835", "#657787"


def read(name):
    demo = {"island": "resistive_mhd_island_coalescence", "coupled": "flash_warpx_kinetic_patch"}[
        name
    ]
    return json.loads(
        (ROOT / "demos" / demo / "fresh_v070_visual_data" / f"benchmark_{name}.json").read_text()
    )


def panel(ax, title):
    ax.set_title(title, loc="left", fontweight="bold", pad=10)
    ax.grid(axis="y", color="#DDE5EB", linewidth=0.55)
    ax.set_axisbelow(True)


def draw_island_scaling(ax, title="FLASH island coalescence"):
    island = read("island")
    rows = sorted(
        [r for r in island["cases"] if r["key"].startswith("pilot-")], key=lambda x: x["S"]
    )
    ax.plot(
        [r["S"] for r in rows],
        [r["rate"] for r in rows],
        color=GRAY,
        marker="s",
        ms=4,
        lw=0.8,
        label=r"Exploratory $128^2$",
    )
    contrast = island["accepted_contrast"]
    production = contrast["cases"]
    ax.errorbar(
        [r["S_eta"] for r in production],
        [r["rate"] for r in production],
        yerr=[r["rate"] * r["relative_uncertainty"] for r in production],
        color=TEAL,
        marker="o",
        ms=5,
        lw=1,
        capsize=3,
        label=r"Fresh production $384^2$",
    )
    # A fixed -1/2 reference, normalized to the lowest-S exploratory case.
    # Its normalization is stated in the caption; it is not a fitted slope.
    anchor = rows[0]
    reference_S = np.geomspace(rows[0]["S"], rows[-1]["S"], 200)
    reference_R = anchor["rate"] * (reference_S / anchor["S"]) ** (-0.5)
    ax.plot(
        reference_S,
        reference_R,
        color=ORANGE,
        ls="--",
        lw=1.3,
        label=r"Original $p=-1/2$ reference",
        zorder=1,
    )
    ax.set(
        xscale="log",
        yscale="log",
        xlabel=r"Inverse-resistivity control $S_\eta=1/\eta$",
        ylabel="Flux-window rate R",
        xlim=(210, 4800),
        ylim=(0.018, 0.12),
    )
    ax.set_xticks([250, 1000, 4000], labels=["250", "1,000", "4,000"])
    ax.set_yticks([0.03, 0.05, 0.09], labels=["0.03", "0.05", "0.09"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(frameon=False, loc="lower left", fontsize=8)
    inset = ax.inset_axes([0.43, 0.72, 0.55, 0.20])
    lo, hi = contrast["root_band"]
    inset.axvspan(lo, hi, color="#D6DEE3", zorder=0)
    p = contrast["p_eff"]
    pmin, pmax = contrast["numerical_interval"]
    inset.errorbar(
        p, 0, xerr=[[p - pmin], [pmax - p]], fmt="o", color=TEAL, markersize=4, capsize=3, lw=1
    )
    inset.set(xlim=(-0.59, -0.29), ylim=(-1, 1), yticks=[], xticks=[-0.55, -0.45, -0.35])
    inset.set_title(r"$1000\rightarrow2000$ contrast", fontsize=8, pad=3)
    inset.set_xlabel(r"$p_{\rm eff}$", fontsize=8.5, labelpad=1)
    inset.tick_params(axis="x", labelsize=7.8, length=2, pad=2)
    panel(ax, title)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
        inset.spines[side].set_visible(False)


def draw_pressure_controls(ax, title="FLASH → WarpX controls"):
    coupled = read("coupled")
    names = ["base", "particles", "fine", "timestep", "bigfine", "fine32"]
    labels = [
        "Coarse, 16 PPC",
        "Coarse, 32 PPC",
        "Fine, 16 PPC",
        "Half timestep",
        "Larger domain",
        "Fine, 32 PPC",
    ]
    if "display_controls" in coupled:
        names = [row["case"] for row in coupled["display_controls"]]
        labels = [row["label"] for row in coupled["display_controls"]]
    threshold = float(coupled.get("threshold", 0.2))
    maximum = max(
        coupled["cases"][n]["species"][sp]["area_time_mean"]
        + coupled["cases"][n].get("uncertainty_upper_allowance", {}).get(sp, 0)
        for n in names
        for sp in ["ions", "electrons"]
    )
    y = np.arange(len(names))
    # A small offset keeps the nearly coincident larger-domain pair distinguishable.
    for species, offset, color, marker, label in [
        ("ions", -0.055, TEAL, "o", "Ions"),
        ("electrons", 0.055, ORANGE, "D", "Electrons"),
    ]:
        values = [coupled["cases"][n]["species"][species]["area_time_mean"] for n in names]
        for index, name in enumerate(names):
            allowance = coupled["cases"][name].get("uncertainty_upper_allowance", {}).get(species)
            if allowance is not None:
                ax.errorbar(
                    values[index],
                    y[index] + offset,
                    xerr=[[0], [allowance]],
                    fmt="none",
                    ecolor=color,
                    elinewidth=0.85,
                    capsize=2,
                    zorder=2,
                )
        ax.scatter(values, y + offset, c=color, s=25, marker=marker, label=label, zorder=3)
    ax.axvline(threshold, ls="--", c=NAVY, lw=0.8)
    ax.text(threshold * 0.99, len(names) - 0.48, "Claim threshold", ha="right", fontsize=7.5)
    ax.set(
        xlim=(0, max(threshold, maximum) * 1.075),
        ylim=(-0.7, len(names) + 0.1),
        xlabel=r"Mean pressure departure $\langle A_s\rangle$",
    )
    ax.set_yticks(y, labels=labels)
    ax.tick_params(axis="y", length=0)
    ax.set_xticks([0, 0.05, 0.1, 0.15, 0.2])
    ax.grid(axis="x", color="#DDE5EB", lw=0.55)
    ax.legend(frameon=False, loc="lower right", fontsize=7.6)
    panel(ax, title)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
