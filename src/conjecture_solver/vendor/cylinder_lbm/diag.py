"""Plot force histories from one or more validate_re100/domain_sweep cases."""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="+", help="case directory names")
    parser.add_argument("--results", type=Path, default=Path("results"),
                        help="parent directory containing the cases")
    parser.add_argument("--out", type=Path, default=Path("force_diagnostic.png"))
    args = parser.parse_args()
    fig, axes = plt.subplots(len(args.cases), 2,
                             figsize=(13, 3.2 * len(args.cases)), squeeze=False)
    for row, name in enumerate(args.cases):
        path = args.results / name / "forces.npz"
        if not path.is_file():
            parser.error(f"missing force history: {path}")
        with np.load(path) as data:
            cl, cd = data["cl"].astype(float), data["cd"].astype(float)
            u, nd = float(data["u"]), int(data["nd"])
        time_star = (np.arange(len(cl)) + 1) * u / nd
        axes[row, 0].plot(time_star, cl, lw=.5)
        axes[row, 0].set(title=f"{name}: lift history", xlabel="tU/D", ylabel="Cl")
        recent = time_star >= time_star[-1] - 25
        axes[row, 1].plot(time_star[recent], cl[recent], label="Cl")
        axes[row, 1].plot(time_star[recent],
                          10 * (cd[recent] - cd[recent].mean()),
                          label="10 × (Cd − mean Cd)")
        axes[row, 1].set(title=f"{name}: final 25 D/U", xlabel="tU/D")
        axes[row, 1].legend(fontsize=8)
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=150)
    plt.close(fig)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
