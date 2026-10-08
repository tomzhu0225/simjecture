"""Render the separately labelled post-run diagnostic correction; no simulation."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

here = Path(__file__).resolve().parent
report = json.loads((here / "postrun_coordinate_check.json").read_text())
cases = report["recorded_cases"]
x = np.arange(len(cases))
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(10.2, 4.7))
fig.subplots_adjust(left=0.1, right=0.98, top=0.84, bottom=0.27)
ax.bar(
    x - 0.18,
    [r["original_max_relative_mismatch"] for r in cases],
    width=0.34,
    color="#c45d67",
    label="Original diagnostic",
)
ax.bar(
    x + 0.18,
    [r["coordinate_consistent_max_relative_mismatch"] for r in cases],
    width=0.34,
    color="#168d81",
    label="Consistent coordinates",
)
ax.set_yscale("log")
ax.set_ylim(1e-8, 1.2)
ax.axhline(0.15, color="#67707b", ls="--", lw=1.3)
ax.text(4.52, 0.15, "Declared cutoff: 0.15", ha="right", va="bottom", fontsize=10, color="#525d69")
ax.set_xticks(
    x, ["Sη=250\n96²", "Sη=250\n120²", "Sη=1000\n128²", "Sη=1000\n160²", "Sη=1000\n256² pilot"]
)
ax.set_ylabel(r"Relative disagreement between $A_z$ paths")
ax.grid(axis="y", alpha=0.18)
ax.set_axisbelow(True)
fig.suptitle("The same FLASH fields passed a consistent coordinate check", fontsize=15, y=0.98)
fig.legend(loc="lower center", bbox_to_anchor=(0.55, 0.03), ncol=2, frameon=False)
fig.text(
    0.1,
    0.9,
    "Post-run operator diagnosis · original campaign records unchanged",
    fontsize=10,
    color="#5d6371",
)
output = here.parents[1] / "docs/_static/demos/island-coordinate-correction"
for suffix in [".png", ".pdf"]:
    fig.savefig(output.with_suffix(suffix), dpi=180)
