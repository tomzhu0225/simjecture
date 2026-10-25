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
            "Descriptive exploratory comparison; two repeats per family, "
            "no population significance claim"
        ),
        live_groups=audit["groups"],
        live_family_groups=[
            dict(
                family=family,
                arm=arm,
                count=len(subset),
                verified=sum(r["verified_complete"] for r in subset),
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
            axis.text(i, -1.15, f"{g['native_starts']} native starts", ha="center", fontsize=8)
        axis.set_ylim(0, 9.2)
        axis.set_yticks(range(0, 9, 2))
        axis.set_title(title)
        axis.set_ylabel("Independently verified complete workflows")
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.15)
        axis.set_axisbelow(True)
    fig.suptitle("Frozen monitoring policies on real-worker WarpX workflows", fontsize=13)
    fig.savefig(output / "verified-workflows.png", dpi=200, bbox_inches="tight")
    fig.savefig(output / "verified-workflows.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    replay = json.loads(args.replay.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    result = summarize(audit, replay)
    put(args.output / "comparison.json", result)
    figure(audit, args.output)
    print(
        json.dumps(dict(live_groups=result["live_groups"], replay_groups=result["replay_groups"]))
    )


if __name__ == "__main__":
    main()
