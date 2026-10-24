"""Plot individual exploratory live trajectories; no confidence intervals implied."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    rows = json.loads(args.audit.read_text())["rows"]
    figure, axes = plt.subplots(1, 2, figsize=(9, 4), layout="constrained")
    policies = ["observe", "rules", "model"]
    colors = {"adapter": "#c95c35", "healthy": "#237a8a"}
    for ax, metric, title in zip(
        axes,
        ["elapsed_seconds", "parked_seconds"],
        ["Full task time (s)", "Worker parked (s)"],
        strict=True,
    ):
        for condition, offset in [("adapter", -0.10), ("healthy", 0.10)]:
            for index, policy in enumerate(policies):
                selected = sorted(
                    [r[metric] for r in rows if r["case"] == condition and r["policy"] == policy]
                )
                ax.scatter(
                    [index + offset - 0.025, index + offset + 0.025],
                    selected,
                    s=50,
                    color=colors[condition],
                    edgecolors="white",
                    linewidths=0.5,
                    label=("Adapter fault" if condition == "adapter" else "Healthy")
                    if index == 0
                    else None,
                    zorder=3,
                )
        ax.set_xticks(range(3), ["Observe only", "Rules", "4B model"])
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", alpha=0.18)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(frameon=False, loc="upper right")
    figure.suptitle("Background attention during real WarpX tasks", fontsize=13)
    figure.supxlabel(
        "Two runs per condition; all 12 numeric reports independently verified.\n"
        "Known injected fault; unchanged base weights; rules were faster.",
        fontsize=9,
    )
    figure.savefig(args.output, dpi=170, facecolor="white")
    plt.close(figure)


if __name__ == "__main__":
    main()
