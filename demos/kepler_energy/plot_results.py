"""Make the documentation figure from retained arrays, without rerunning a solver."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def plot():
    root = HERE / "record"
    selected = {}
    for receipt in (root / "experiments").glob("*.json"):
        record = json.loads(receipt.read_text())
        workspace = root / "experiments" / record["id"] / "workspace"
        if not (workspace / "trajectories.npz").exists():
            continue
        with np.load(workspace / "trajectories.npz", allow_pickle=False) as arrays:
            for n in (256, 2048):
                key = f"e0_n{n}"
                if key + "_t" in arrays:
                    selected[n] = {
                        suffix: arrays[key + suffix].copy()
                        for suffix in ("_t", "_q_kdk", "_q_exact", "_rel_energy")
                    }
    assert set(selected) == {256, 2048}
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.8))
    fig.subplots_adjust(left=0.09, right=0.98, bottom=0.23, top=0.86, wspace=0.3)
    for n, color, label in [
        (256, "#6658d9", "Original test · 256 steps / orbit"),
        (2048, "#16877a", "Fresh repair test · 2,048 steps / orbit"),
    ]:
        data = selected[n]
        time = data["_t"] / (2 * np.pi)
        energy = np.maximum.accumulate(np.abs(data["_rel_energy"]))
        position = np.linalg.norm(data["_q_kdk"] - data["_q_exact"], axis=1)
        axes[0].semilogy(time, np.maximum(energy, 1e-16), color=color, lw=1.35, label=label)
        axes[1].plot(time, position, color=color, lw=2)
    axes[0].axhline(0.001, color="#bd4b4b", ls="--", lw=1.5)
    axes[0].text(0.4, 0.001 * 1.8, "Energy criterion: 0.001", color="#9f3636", fontsize=10)
    axes[0].set(
        title="Energy stays within the criterion",
        ylabel="Maximum relative energy error so far",
        ylim=(1e-13, 1e-2),
    )
    axes[1].axhline(0.01, color="#bd4b4b", ls="--", lw=1.5)
    axes[1].text(0.4, 0.0107, "Position criterion: 0.01a", color="#9f3636", fontsize=10)
    axes[1].set(
        title="Position error exceeds the bound", ylabel="Position error / a", ylim=(0, 0.029)
    )
    fig.legend(
        *axes[0].get_legend_handles_labels(),
        loc="lower center",
        bbox_to_anchor=(0.54, 0.01),
        ncol=2,
        frameon=False,
        fontsize=9.5,
    )
    for ax in axes:
        ax.set(xlabel="Time / orbital period", xlim=(0, 20))
        ax.grid(alpha=0.15)
    output = HERE.parents[1] / "docs/_static/demos"
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        fig.savefig(output / f"kepler-energy.{suffix}", dpi=180, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    plot()
