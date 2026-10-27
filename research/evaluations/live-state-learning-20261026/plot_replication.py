"""Plot the completed registered comparison without changing its analysis."""

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text())
    analysis = evidence["analysis"]
    primary = analysis["primary_all_attempts"]
    assert primary["complete_design"] and primary["started"] == primary["planned"] == 64
    assert primary["audit_violations"] == []
    records = {(r["block"], r["arm"]): r for r in evidence["records"]}
    main_effect = primary["continued_sft_minus_baseline"]["base"]["restricted_completion_seconds"]
    sensitivity = analysis["clean_block_sensitivity"]["continued_sft_minus_baseline"]["base"][
        "restricted_completion_seconds"
    ]
    excluded = set(analysis["excluded_blocks"])
    groups = defaultdict(list)
    for pair in main_effect["paired_differences"]:
        groups[pair["family"]].append(pair)
    assert len(groups) == 8 and all(len(v) == 2 for v in groups.values())
    assert (
        abs(
            statistics.mean(statistics.mean(p["difference"] for p in v) for v in groups.values())
            - main_effect["difference"]
        )
        < 1e-6
    )
    labels = {
        "publication_retry": "Expected publication retry",
        "announced_quiet": "Announced quiet period",
        "progressing_work": "Healthy progress",
        "update_cycle": "Unstable update cycle",
        "unit_conversion": "Unit conversion",
        "source_binding": "Protected source selection",
        "artifact_consumer": "Artifact consumption",
        "recovered_history": "Recovered historical warning",
    }
    order = sorted(
        groups, key=lambda family: statistics.mean(p["difference"] for p in groups[family])
    )
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), gridspec_kw={"height_ratios": [1, 3]})
    fig.suptitle(
        "Conjecture 1: repeated scientific-workflow comparison", fontsize=16, x=0.51, y=0.98
    )
    fig.text(
        0.51,
        0.946,
        "64 assigned workflows · 8 engineered mechanisms · "
        "frozen SFT adapter versus pretrained base",
        ha="center",
        fontsize=10,
    )
    ax = axes[0]
    for y, (_name, effect, color) in enumerate(
        [
            ("All attempts", main_effect, "#245b94"),
            ("Infrastructure-block sensitivity", sensitivity, "#637685"),
        ]
    ):
        mean, interval = effect["difference"], effect["interval"]
        assert effect["confidence"] == 0.95
        ax.errorbar(
            mean,
            y,
            xerr=[[mean - interval[0]], [interval[1] - mean]],
            fmt="o",
            color=color,
            capsize=5,
            markersize=7,
            linewidth=2,
        )
        ax.annotate(
            f"{mean:+.1f} s  [{interval[0]:+.1f}, {interval[1]:+.1f}]",
            xy=(mean, y),
            xytext=(0, -19),
            textcoords="offset points",
            ha="center",
            fontsize=10,
        )
    ax.set_yticks([0, 1], ["All attempts", "Infrastructure-block sensitivity"])
    ax.set_ylim(1.65, -0.6)
    ax.set_title(
        "Registered family-weighted effects and descriptive 95% intervals", loc="left", fontsize=11
    )
    ax.axvline(0, color="#555555", linestyle="--", linewidth=1)
    ax.grid(axis="x", color="#eeeeee")
    ax.set_xlabel("SFT minus base restricted completion time (seconds)")
    ax = axes[1]
    used = set()
    for y, family in enumerate(order):
        values = groups[family]
        ax.plot([p["difference"] for p in values], [y, y], color="#d6dce2", linewidth=2, zorder=1)
        for index, pair in enumerate(sorted(values, key=lambda p: p["repeat"])):
            success = all(
                records[(pair["block"], arm)]["whole_workflow_verified"]
                for arm in ["base", "continued_sft"]
            )
            if pair["block"] in excluded:
                color, marker, label = (
                    "#c47b13",
                    "x",
                    "Block excluded in infrastructure sensitivity",
                )
            elif not success:
                color, marker, label = "#b74040", "s", "At least one workflow failed completion"
            else:
                color, marker, label = "#245b94", "o", "Both workflows verified"
            ax.scatter(
                pair["difference"],
                y + (-0.06 if index == 0 else 0.06),
                c=color,
                marker=marker,
                s=53,
                zorder=3,
                label=label if label not in used else None,
            )
            used.add(label)
        mean = statistics.mean(p["difference"] for p in values)
        ax.scatter(mean, y, marker="|", c="#111111", s=220, zorder=4)
    ax.set_yticks(range(len(order)), [labels.get(v, v) for v in order])
    ax.set_ylim(len(order) - 0.4, -0.6)
    ax.axvline(0, color="#555555", linestyle="--", linewidth=1)
    ax.grid(axis="x", color="#eeeeee")
    ax.set_xlabel("Individual paired differences (seconds): negative favors SFT")
    ax.set_title(
        "Two independent executions per mechanism; black ticks show family means",
        loc="left",
        fontsize=11,
    )
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False, fontsize=9)
    fig.text(
        0.02,
        0.024,
        "Verified times are capped at 650 s; unsuccessful workflows receive 650 s.\n"
        "Orange markers identify entire excluded blocks, including otherwise verified pairs. "
        "These are known mechanisms, not unseen-task generalization.",
        fontsize=9,
    )
    fig.subplots_adjust(left=0.29, right=0.97, top=0.89, bottom=0.23, hspace=0.57)
    args.output.mkdir(parents=True, exist_ok=False)
    for extension in ["png", "pdf"]:
        fig.savefig(args.output / ("replication-effects." + extension), dpi=180)
    plt.close(fig)
    print(
        json.dumps(
            {"source": str(args.evidence), "output": str(args.output), "pairs": 16, "families": 8}
        )
    )


if __name__ == "__main__":
    main()
