#!/usr/bin/env python3
"""Render the recorded Gray--Scott contract evidence without rerunning it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DEMO_DIRECTORY = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEMO_DIRECTORY / "record" / "workspace",
        help="recorded workspace containing root_pattern_results.json and fields",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_DIRECTORY / "gray-scott-result.png",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = args.workspace.resolve()
    result = json.loads((workspace / "root_pattern_results.json").read_text())

    fields: dict[str, np.ndarray] = {}
    for scale in ("1", "10"):
        archive = np.load(workspace / f"root_s{scale}_dt0p05.npz")
        fields[scale] = np.asarray(archive["u"], dtype=float)
        if fields[scale].shape != (result["N"], result["N"]):
            raise ValueError(f"unexpected field shape for scale {scale}")
        if not np.isfinite(fields[scale]).all():
            raise ValueError(f"non-finite recorded field for scale {scale}")

    vmin = min(float(field.min()) for field in fields.values())
    vmax = max(float(field.max()) for field in fields.values())
    extent = (0.0, float(result["L"]), 0.0, float(result["L"]))
    figure, axes = plt.subplots(
        1,
        3,
        figsize=(13.2, 4.4),
        gridspec_kw={"width_ratios": (1.0, 1.0, 1.2)},
        constrained_layout=True,
    )

    image = None
    for axis, scale in zip(axes[:2], ("1", "10"), strict=True):
        pattern = float(result["dt_0p05"][scale]["P_final"])
        image = axis.imshow(
            fields[scale],
            origin="lower",
            extent=extent,
            cmap="viridis",
            vmin=vmin,
            vmax=vmax,
            interpolation="nearest",
        )
        diffusion = "(1, 1/3)" if scale == "1" else "(10, 10/3)"
        outcome = "persistent pattern" if scale == "1" else "homogeneous decay"
        axis.set_title(rf"$(D_u,D_v)={diffusion}$" + f"\n{outcome}; P={pattern:.3e}")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
    assert image is not None
    figure.colorbar(image, ax=axes[:2], shrink=0.86, label=r"$u(x,y,t=1000)$")

    colors = {"1": "#2878b5", "10": "#c82423"}
    for dt_key, line_style in (("dt_0p05", "-"), ("dt_0p025", "--")):
        dt_label = dt_key.removeprefix("dt_").replace("p", ".")
        for scale in ("1", "10"):
            records = np.asarray(result[dt_key][scale]["records"], dtype=float)
            measure = np.maximum(records[:, 1], np.finfo(float).tiny)
            axes[2].semilogy(
                records[:, 0],
                measure,
                color=colors[scale],
                linestyle=line_style,
                marker="o",
                markersize=3.5,
                label=rf"$s={scale}$, $\Delta t={dt_label}$",
            )
    axes[2].axhline(1.0e-3, color="#555555", linewidth=0.9, linestyle=":")
    axes[2].set_xlabel("time")
    axes[2].set_ylabel(r"pattern measure $P$")
    axes[2].set_title("Prospective decision observable")
    axes[2].grid(alpha=0.25, which="both")
    axes[2].legend(fontsize=8, loc="best")

    figure.suptitle(
        "Recorded Gray–Scott evidence: fixed ratio, different absolute diffusion scale",
        fontsize=13,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.output, dpi=180)
    plt.close(figure)
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
