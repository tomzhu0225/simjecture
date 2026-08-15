#!/usr/bin/env python3
"""Render the archived GEM ensemble and representative final fields."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DEMO_DIRECTORY = Path(__file__).resolve().parent
SEEDS = (20260902, 20260903, 20260904)
TEMPERATURE_RATIOS = (1, 20)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--record",
        type=Path,
        default=DEMO_DIRECTORY / "record",
        help="curated autonomous-run record",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEMO_DIRECTORY.parents[1] / "docs" / "_static" / "demos",
    )
    return parser.parse_args()


def run_index(result: dict[str, object]) -> dict[tuple[int, int, int], dict[str, object]]:
    indexed: dict[tuple[int, int, int], dict[str, object]] = {}
    for run in result["runs"]:
        assert isinstance(run, dict)
        key = (
            int(run["ppc_per_population"]),
            int(run["temperature_ratio_Ti_Te"]),
            int(run["seed"]),
        )
        indexed[key] = run
    return indexed


def plot_ensemble(result: dict[str, object], output: Path) -> None:
    indexed = run_index(result)
    colors = {1: "#2878b5", 20: "#d05a3a"}
    seed_colors = ("#2f5597", "#4f9d69", "#b45f06")
    figure, axes = plt.subplots(2, 2, figsize=(13.4, 9.0), constrained_layout=True)

    flux_axis = axes[0, 0]
    for temperature_ratio in TEMPERATURE_RATIOS:
        for index, seed in enumerate(SEEDS):
            run = indexed[(16, temperature_ratio, seed)]
            flux_axis.plot(
                run["time_coordinates_matching"],
                run["flux_coordinates_matching"],
                color=colors[temperature_ratio],
                alpha=0.55 + 0.2 * index,
                linewidth=1.8,
                linestyle="-" if temperature_ratio == 1 else "--",
                label=(
                    rf"$T_i/T_e={temperature_ratio}$"
                    if index == 0
                    else None
                ),
            )
    flux_axis.set_title("16-PPC late-window reconnected flux")
    flux_axis.set_xlabel(r"time $t\Omega_{ci}$")
    flux_axis.set_ylabel(r"$(A_O-A_X)/(B_0d_i)$")
    flux_axis.grid(alpha=0.25)
    flux_axis.legend()

    for axis, ppc in zip((axes[0, 1], axes[1, 0]), (16, 8), strict=True):
        for seed, color in zip(SEEDS, seed_colors, strict=True):
            values = [
                float(indexed[(ppc, temperature_ratio, seed)]["mu_upstream_normalized_rate"])
                for temperature_ratio in TEMPERATURE_RATIOS
            ]
            axis.plot((0, 1), values, "o-", color=color, alpha=0.82, label=str(seed))
        statistics = result["summary_statistics"]
        assert isinstance(statistics, dict)
        means = [
            float(statistics[f"TiTe{temperature_ratio}_ppc{ppc}"]["mean"])
            for temperature_ratio in TEMPERATURE_RATIOS
        ]
        errors = [
            float(statistics[f"TiTe{temperature_ratio}_ppc{ppc}"]["se"])
            for temperature_ratio in TEMPERATURE_RATIOS
        ]
        axis.errorbar(
            (0, 1),
            means,
            yerr=errors,
            fmt="D",
            color="black",
            capsize=5,
            markersize=6,
            linewidth=1.5,
            label="mean ± SE",
            zorder=5,
        )
        axis.set_xticks((0, 1), (r"$T_i/T_e=1$", r"$T_i/T_e=20$"))
        axis.set_ylabel("normalized late-window rate")
        axis.set_title(f"{ppc} PPC per population: paired seeds")
        axis.set_ylim(bottom=0.0)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8, ncols=2)

    ratio_axis = axes[1, 1]
    ratios = result["ratios"]
    assert isinstance(ratios, dict)
    ratio_values = np.asarray(
        [
            float(ratios["R16_mean_TiTe1_over_mean_TiTe20"]),
            float(ratios["R8_mean_TiTe1_over_mean_TiTe20"]),
        ]
    )
    intervals = [
        ratios["bootstrap_R16_95_percent_CI"],
        ratios["bootstrap_R8_95_percent_CI"],
    ]
    lower = np.asarray([float(item["ci_low"]) for item in intervals])
    upper = np.asarray([float(item["ci_high"]) for item in intervals])
    ratio_axis.errorbar(
        (0, 1),
        ratio_values,
        yerr=np.vstack((ratio_values - lower, upper - ratio_values)),
        fmt="o",
        color="#6a3d9a",
        capsize=6,
        markersize=8,
        linewidth=1.8,
    )
    ratio_axis.axhline(1.25, color="#c82423", linestyle="--", label="claim threshold 1.25")
    ratio_axis.axhline(1.0, color="#444444", linestyle=":", label="equal means")
    ratio_axis.set_yscale("log")
    ratio_axis.set_xticks((0, 1), ("16 PPC", "8 PPC"))
    ratio_axis.set_ylabel(r"$\mu_{T_i/T_e=1}/\mu_{T_i/T_e=20}$")
    ratio_axis.set_title("Mean ratios and paired-bootstrap intervals")
    ratio_axis.grid(alpha=0.25, which="both")
    ratio_axis.legend(fontsize=8)

    figure.suptitle(
        "Recorded autonomous GEM ensemble: 12 fresh held-out CUDA runs",
        fontsize=14,
    )
    figure.savefig(output, dpi=180)
    plt.close(figure)


def plot_fields(record: Path, output: Path) -> None:
    workspace = record / "workspace" / "campaign"
    labels = (
        ("run_p16_t1_s20260902", r"$T_i/T_e=1$"),
        ("run_p16_t20_s20260902", r"$T_i/T_e=20$"),
    )
    loaded: list[tuple[str, dict[str, np.ndarray], dict[str, object]]] = []
    for run_name, title in labels:
        field_path = workspace / run_name / "final_fields.npz"
        summary_path = workspace / "summaries" / f"{run_name.removeprefix('run_')}_summary.json"
        with np.load(field_path) as archive:
            fields = {name: np.asarray(archive[name], dtype=float) for name in archive.files}
        if not all(np.isfinite(value).all() for value in fields.values()):
            raise ValueError(f"non-finite representative fields in {field_path}")
        loaded.append((title, fields, json.loads(summary_path.read_text())))

    by_values = [fields["By"] / float(summary["inputs"]["B0_T"]) for _, fields, summary in loaded]
    jy_values = [fields["Jy"] / 1.0e12 for _, fields, _ in loaded]
    by_limit = float(
        np.percentile(np.abs(np.concatenate([value.ravel() for value in by_values])), 99.5)
    )
    jy_limit = float(
        np.percentile(np.abs(np.concatenate([value.ravel() for value in jy_values])), 99.5)
    )

    figure, axes = plt.subplots(2, 2, figsize=(13.0, 7.3), constrained_layout=True)
    for row, ((title, _, summary), by_field, jy_field) in enumerate(
        zip(loaded, by_values, jy_values, strict=True)
    ):
        inputs = summary["inputs"]
        extent = (
            -0.5 * float(inputs["box_Lx_di"]),
            0.5 * float(inputs["box_Lx_di"]),
            -0.5 * float(inputs["box_Lz_di"]),
            0.5 * float(inputs["box_Lz_di"]),
        )
        for column, (field, limit, label) in enumerate(
            (
                (by_field, by_limit, r"$B_y/B_0$"),
                (jy_field, jy_limit, r"$J_y$ [$10^{12}$ A m$^{-2}$]"),
            )
        ):
            axis = axes[row, column]
            image = axis.imshow(
                field,
                origin="lower",
                extent=extent,
                aspect="auto",
                cmap="RdBu_r",
                vmin=-limit,
                vmax=limit,
                interpolation="nearest",
            )
            axis.set_title(f"{title}: {label}")
            axis.set_xlabel(r"$x/d_i$")
            axis.set_ylabel(r"$z/d_i$")
            figure.colorbar(image, ax=axis, shrink=0.88)

    figure.suptitle(
        "Representative final GEM states · 16 PPC · seed 20260902 · "
        r"$t\Omega_{ci}=12$",
        fontsize=14,
    )
    figure.savefig(output, dpi=180)
    plt.close(figure)


def main() -> int:
    args = parse_args()
    record = args.record.resolve()
    output_directory = args.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    result = json.loads(
        (record / "workspace" / "campaign" / "ensemble_result.json").read_text()
    )
    ensemble_output = output_directory / "gem-ensemble-result.png"
    fields_output = output_directory / "gem-reconnection-fields.png"
    plot_ensemble(result, ensemble_output)
    plot_fields(record, fields_output)
    print(ensemble_output)
    print(fields_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
