"""Export fixed descriptive summaries and a standalone exploratory figure."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from simjecture_monitor.events import put


def summarize(audit, replay):
    rows = audit["rows"]
    replay_rows = [r for r in replay if not r.get("missing") and not r.get("error")]
    grouped = []
    healthy = {"progressing_work", "announced_quiet", "publication_retry", "recovered_history"}
    for family in sorted({r["family"] for r in rows}):
        selected = [r for r in replay_rows if r["job"]["family"] == family]
        grouped.append(
            dict(
                family=family,
                healthy=family in healthy,
                packets=len(selected),
                with_published_discrepancy=sum(
                    bool(r["descriptive_evidence_tags"]) for r in selected
                ),
                choices={
                    policy: dict(Counter(r[policy]["choice"] for r in selected))
                    for policy in ["operational_rules", "rules", "model", "hybrid"]
                },
                model_rules_disagreement=sum(
                    r["model"]["choice"] != r["rules"]["choice"] for r in selected
                ),
            )
        )
    return dict(
        scope=(
            "Descriptive exploratory comparison; assignment counts follow the cohort design, "
            "no population significance claim"
        ),
        live_groups=audit["groups"],
        replay_assigned=len(replay),
        cost_scope=audit["cost_scope"],
        balanced_cost_groups=audit["balanced_cost_groups"],
        live_family_groups=[
            dict(
                family=family,
                arm=arm,
                count=len(subset),
                verified=sum(r["verified_complete"] for r in subset),
                whole_workflow_verified=sum(r["whole_workflow_verified"] for r in subset),
                completion_censored=[r["completion_censored"] for r in subset],
                times=[r["elapsed_seconds"] for r in subset],
                native_starts=[r["native_starts"] for r in subset],
                alerts=[r["accepted_actions"] for r in subset],
                fallback=[r["fallback_count"] for r in subset],
            )
            for family in sorted({r["family"] for r in rows})
            for arm in ["observe", "rules", "model", "hybrid"]
            if (subset := [r for r in rows if r["family"] == family and r["arm"] == arm])
        ],
        replay_groups=grouped,
        replay_missing=[
            {k: v for k, v in r.items() if k != "packet"} for r in replay if r.get("missing")
        ],
        replay_errors=[r for r in replay if r.get("error")],
        replay_observation_omissions=[r for r in replay_rows if r.get("observation_omissions")],
        same_input_disagreements=[
            dict(
                family=r["job"]["family"],
                seed=r["job"]["seed"],
                offset=r["target_offset_seconds"],
                packet_sha256=r["packet_sha256"],
                rules=r["rules"]["choice"],
                model=r["model"]["choice"],
                evidence_tags=r["descriptive_evidence_tags"],
            )
            for r in replay_rows
            if r["model"]["choice"] != r["rules"]["choice"]
        ],
    )


def figure(audit, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    arms = ["observe", "rules", "model", "hybrid"]
    labels = ["No watcher", "Rules", "4B model", "Hybrid"]
    colors = ["#64748b", "#c98224", "#286cb5", "#5b8b55"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), constrained_layout=True)
    for axis, subset, title in zip(
        axes, ["healthy", "problem"], ["Healthy workflows", "Problem workflows"], strict=True
    ):
        groups = {g["arm"]: g for g in audit["groups"] if g["subset"] == subset}
        counts = [groups[a]["verified"] for a in arms]
        axis.bar(labels, counts, color=colors, width=0.65)
        for i, a in enumerate(arms):
            g = groups[a]
            axis.text(
                i,
                g["verified"] + 0.18,
                f"{g['verified']}/{g['assigned']}",
                ha="center",
                fontsize=11,
            )
            detail = f"{g['native_starts']} native starts"
            if any(r["completion_censored"] for r in audit["rows"]):
                detail += f"\n{g['completion_censored']} censored returns"
            axis.text(
                i,
                -0.15,
                detail,
                ha="center",
                va="top",
                fontsize=8,
                transform=axis.get_xaxis_transform(),
            )
        maximum = max((g["assigned"] for g in groups.values()), default=0)
        axis.set_ylim(0, max(maximum + 1.2, 2))
        axis.set_yticks(range(0, maximum + 1, 2 if maximum >= 8 else 1))
        axis.set_title(title)
        axis.set_ylabel("Verified scientific reports and pipelines")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.15)
        axis.set_axisbelow(True)
    fig.suptitle("Frozen monitoring policies on real-worker WarpX workflows", fontsize=13)
    fig.savefig(output / "verified-workflows.png", dpi=200, bbox_inches="tight")
    fig.savefig(output / "verified-workflows.pdf", bbox_inches="tight")
    plt.close(fig)

    from statistics import median

    from matplotlib.lines import Line2D

    families = sorted({r["family"] for r in audit["rows"]})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.8), constrained_layout=True)
    for axis, metric, ylabel in zip(
        axes,
        ["elapsed_seconds", "native_starts"],
        ["Whole trajectory time (seconds)", "Native role starts per trajectory"],
        strict=True,
    ):
        for i, arm in enumerate(arms):
            selected = [r for r in audit["rows"] if r["arm"] == arm]
            values = []
            for row in selected:
                value = row.get(metric)
                if value is None:
                    continue
                if row["balanced_cost_eligible"]:
                    values.append(value)
                offset = (families.index(row["family"]) - (len(families) - 1) / 2) * 0.055
                offset += (row.get("repeat", 0) - 0.5) * 0.025
                marker = "o" if row["healthy"] else "^"
                axis.scatter(
                    i + offset,
                    value,
                    marker=marker,
                    facecolors=colors[i] if row["balanced_cost_eligible"] else "none",
                    edgecolors=colors[i],
                    alpha=0.8,
                    s=30,
                )
                if row["completion_censored"]:
                    axis.annotate(
                        "",
                        (i + offset, value + (30 if metric == "elapsed_seconds" else 0.7)),
                        (i + offset, value),
                        arrowprops=dict(arrowstyle="->", color="black"),
                    )
                if not row["verified_complete"]:
                    axis.scatter(i + offset, value, marker="x", color="black", s=60)
            if values:
                axis.plot([i - 0.25, i + 0.25], [median(values)] * 2, color="black", linewidth=2)
        axis.set_xticks(range(4), labels)
        axis.set_ylabel(ylabel)
        axis.set_xlim(-0.5, 3.5)
        axis.set_ylim(bottom=0)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.15)
        axis.set_axisbelow(True)
    axes[1].set_yticks(range(0, 11, 2))
    censored = any(r["completion_censored"] for r in audit["rows"])
    legend = [
        Line2D([], [], color="gray", marker="o", linestyle="", label="Healthy case"),
        Line2D([], [], color="gray", marker="^", linestyle="", label="Problem case"),
    ]
    if any(not r["verified_complete"] for r in audit["rows"]):
        legend.append(
            Line2D([], [], color="black", marker="x", linestyle="", label="Incomplete output")
        )
    if censored:
        legend.extend(
            [
                Line2D(
                    [],
                    [],
                    color="gray",
                    marker="o",
                    markerfacecolor="none",
                    linestyle="",
                    label="Configuration omitted from median",
                ),
                Line2D(
                    [],
                    [],
                    color="black",
                    marker=r"$\uparrow$",
                    linestyle="",
                    label="Censored cost (lower bound)",
                ),
            ]
        )
    legend.append(
        Line2D(
            [],
            [],
            color="black",
            linewidth=2,
            label="Balanced eligible median" if censored else "Median",
        )
    )
    fig.legend(handles=legend, loc="outside lower center", ncol=3, frameon=False, fontsize=8)
    fig.suptitle(
        "Recorded costs; premature collector stops are censored"
        if censored
        else "Recorded workflow costs; all assignments retained",
        fontsize=13,
    )
    fig.savefig(output / "workflow-costs.png", dpi=200, bbox_inches="tight")
    fig.savefig(output / "workflow-costs.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--replay", type=Path, help="Optional replay belonging to this cohort")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    replay = json.loads(args.replay.read_text()) if args.replay else []
    args.output.mkdir(parents=True, exist_ok=True)
    result = summarize(audit, replay)
    put(args.output / "comparison.json", result)
    figure(audit, args.output)
    print(
        json.dumps(dict(live_groups=result["live_groups"], replay_groups=result["replay_groups"]))
    )


if __name__ == "__main__":
    main()
