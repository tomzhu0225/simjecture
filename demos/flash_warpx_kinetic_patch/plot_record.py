"""Editorial plot from preserved exploratory measurements; no new model call."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE / "record/experiments/exp_a8a1458ce67d49c2307145de/workspace/analysis.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "figures/pressure-controls")
    args = parser.parse_args()
    data = json.loads(ANALYSIS.read_text())["cases"]
    cases = [
        ("fine", "Fine patch · 576²", "#176B87", "-"),
        ("bigfine", "Larger patch · 864²", "#C65B2B", "--"),
        ("timestep", "Half timestep · 576²", "#7056AB", "-."),
    ]
    with plt.rc_context({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False}):
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharey=True)
        for axis, species in zip(axes, ["ions", "electrons"], strict=True):
            axis.axvspan(0.3, 0.8, color="#edf2f4", zorder=0)
            for key, label, color, style in cases:
                row = data[key]["species"][species]
                axis.plot(row["times"], row["area_means"], color=color, ls=style, lw=2, label=label)
            axis.axhline(0.20, color="#465261", ls=":", lw=1.5)
            axis.text(0.015, 0.203, "Hypothesis threshold 0.20", color="#465261", fontsize=9)
            axis.set(
                xlim=(0, 0.8),
                ylim=(0, 0.222),
                xlabel=r"$t\Omega_{ci,\mathrm{ref}}$",
                title=species.capitalize(),
            )
            axis.grid(axis="y", alpha=0.2)
        axes[0].set_ylabel("Area-averaged local pressure departure")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.025), ncol=3, frameon=False
        )
        fig.suptitle(
            "A FLASH current sheet followed with kinetic WarpX patches", y=0.98, fontsize=15
        )
        fig.text(
            0.5,
            0.912,
            "Exploratory controls · shaded measurement window · no accepted scientific verdict",
            ha="center",
            color="#465261",
            fontsize=10,
        )
        fig.subplots_adjust(left=0.09, right=0.98, bottom=0.21, top=0.81, wspace=0.12)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        for suffix in [".png", ".pdf"]:
            fig.savefig(args.output.with_suffix(suffix), dpi=180, facecolor="white")
        plt.close(fig)


if __name__ == "__main__":
    main()
