"""Replot the published, sanitized 2026-10-04 campaign audit (requires matplotlib)."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def main():
    assets = Path(__file__).resolve().parents[1] / "docs/research/assets"
    data = json.loads((assets / "adaptive-campaign-audit-20261004.json").read_text())
    parent, seed = data["native_data"][:2]
    comparison = data["radiation_window_comparison"]
    reference = data["seeded_kinetic_reference"]["line_kinetic_J"]
    window = data["seeded_window"]["window_ns"]
    excess = comparison["seeded_on_own_window_J"] - reference
    heat = seed["operator_budget"]["stages"]["diffusion"]["windows"]
    window_key = ":".join(str(t) for t in window)
    blue, purple, red, grey = "#2563eb", "#9333ea", "#dc2626", "#475569"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout="constrained")
    ax = axes[0, 0]
    for record, label, color in [(parent, "Unperturbed", blue), (seed, "m=1,n=1 seed", purple)]:
        curve = record["radiation"]["curve"]
        ax.plot([r[0] for r in curve], [r[1] / 1e9 for r in curve], color=color, label=label)
    ax.axvspan(*window, color=purple, alpha=0.08, label="Seeded FWHM window")
    ax.set(xlim=(0, 40), xlabel="Physical time (ns)", ylabel="Escaped power (GW)")
    ax.set_title("A. Two complete, unresolved 3D trajectories", loc="left")
    ax.legend(fontsize=9)
    ax = axes[0, 1]
    samples = data["kinetic_samples"]
    for key, label, color in [
        ("load_kinetic_J", "Seeded load tracer", purple),
        ("box_kinetic_J", "Seeded whole box", grey),
    ]:
        ax.plot(
            [r["time_ns"] for r in samples], [r[key] for r in samples], label=label, color=color
        )
    ax.axvspan(0, 10, color=blue, alpha=0.08, label="Declared K reference interval")
    ax.axhline(
        reference, linestyle="--", color=blue, label=f"Sampled K reference: {reference:.1f} J"
    )
    ax.set(xlim=(0, 40), xlabel="Physical time (ns)", ylabel="Kinetic energy (J)")
    ax.set_title("B. Reference interval excludes the later K maximum", loc="left")
    ax.legend(fontsize=9)
    ax = axes[1, 0]
    values = [
        comparison["parent_own_window_J"],
        comparison["seeded_on_parent_window_J"],
        comparison["seeded_on_own_window_J"],
    ]
    bars = ax.bar(
        ["Parent\nparent window", "Seed\nparent window", "Seed\nown window"],
        values,
        color=[blue, purple, purple],
    )
    ax.bar_label(bars, labels=[f"{v:.1f} J" for v in values], padding=4)
    ax.set(ylim=(0, 2050), ylabel="Escaped radiation (J)")
    ax.set_title("C. Common window: +0.71%; own windows: +3.34%", loc="left")
    ax = axes[1, 1]
    values = [excess, excess * 0.1, heat[window_key]["internal_erg"], heat["0:40"]["internal_erg"]]
    bars = ax.bar(
        [
            "Apparent\nexcess",
            "Candidate\n10% threshold",
            "Diffusion heat\nin window",
            "Diffusion heat\nfull trajectory",
        ],
        values,
        color=[grey, red, purple, blue],
    )
    ax.bar_label(bars, labels=[f"{v:.1f} J" for v in values], padding=4)
    ax.set(ylim=(0, 1420), ylabel="Energy (J)")
    ax.set_title("D. Heat bookkeeping does not identify reconnection", loc="left")
    fig.suptitle("Al Z-pinch audit · exploratory observations, no accepted 10% bound", fontsize=15)
    fig.savefig(assets / "adaptive-campaign-science-20261004.png", dpi=170)
    fig.savefig(assets / "adaptive-campaign-science-20261004.pdf")
    plt.close(fig)

    fig, (timeline, tokens) = plt.subplots(
        2, 1, figsize=(13, 8), layout="constrained", gridspec_kw={"height_ratios": [1.4, 1]}
    )
    campaign = data["campaign"]
    start, stopped = campaign["started_at"], campaign["elapsed_h"]
    rows = [r for r in data["timeline"] if r["seconds"] > 300]
    labels = [
        "Unperturbed 48x48x24",
        "Cell noise 80x80x40 (cancelled)",
        "Coherent seed 48x48x24",
        "Spatial pilot 128x128x24 (analysis failed)",
    ]
    for y, row in enumerate(rows):
        left = (row["created_at"] - start) / 3600
        width = (row["finished_at"] - row["created_at"]) / 3600
        color = blue if row["status"] == "succeeded" else red if row["status"] == "failed" else grey
        timeline.barh(y, width, left=left, height=0.55, color=color)
        timeline.text(left + width + 0.04, y, f"{row['sim_ns']:.3g} ns", va="center", fontsize=9)
    for review in data["review_attempts"]:
        left = (review["start_at"] - start) / 3600
        width = (review["end_at"] - review["start_at"]) / 3600
        timeline.barh(
            4,
            width,
            left=left,
            height=0.4,
            color=purple if review["decision_record_present"] else "#d97706",
        )
    timeline.axvspan(stopped, 12, color=red, alpha=0.08)
    timeline.axvline(stopped, color=red, linestyle="--")
    timeline.text(stopped + 0.15, 1.8, f"Harness stopped\n{12 - stopped:.2f} h unused", color=red)
    timeline.set(
        yticks=range(5),
        yticklabels=labels + ["Director calls (overlap jobs)"],
        xlim=(0, 12),
        xlabel="Wall hours from campaign start",
    )
    timeline.invert_yaxis()
    timeline.set_title(
        "A. Submission-to-result intervals and independent review attempts", loc="left"
    )
    roles = data["usage_by_role"]
    names = list(roles)
    uncached = [roles[k]["uncached"] / 1e6 for k in names]
    cached = [roles[k]["cached"] / 1e6 for k in names]
    tokens.barh(names, uncached, color=red, label="Reported uncached input")
    tokens.barh(names, cached, left=uncached, color=blue, label="Reported cached input")
    for y, name in enumerate(names):
        row = roles[name]
        tokens.text(
            row["input"] / 1e6 + 0.3,
            y,
            f"{row['input'] / 1e6:.2f}M total; {row['uncached'] / 1e6:.2f}M uncached",
            va="center",
            fontsize=9,
        )
    tokens.set(xlim=(0, 44), xlabel="Reported input tokens (millions)")
    tokens.invert_yaxis()
    tokens.legend(loc="lower right", fontsize=9)
    tokens.set_title(
        "B. Director: 25% of input, 64% of uncached input · incomplete native counters", loc="left"
    )
    fig.suptitle(
        "Campaign cost audit · time categories overlap; token counters are not billing", fontsize=15
    )
    fig.savefig(assets / "adaptive-campaign-cost-20261004.png", dpi=170)
    fig.savefig(assets / "adaptive-campaign-cost-20261004.pdf")
    plt.close(fig)


if __name__ == "__main__":
    main()
