"""Independently measure absolute electric-field peaks from saved WarpX arrays."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import numpy as np
    import yt

    yt.funcs.mylog.setLevel(40)
    rows = []
    for receipt in sorted(args.work.glob("runs/*/receipt.json")):
        r = json.loads(receipt.read_text())
        if r["status"] != "succeeded":
            continue
        dataset = yt.load(str(receipt.parent / f"plot{r['steps']:06d}"))
        fields = dataset.covering_grid(
            level=0, left_edge=dataset.domain_left_edge, dims=dataset.domain_dimensions
        )
        actual = fields[("mesh", "Ez")].to_ndarray()
        rows.append(
            dict(
                name=receipt.parent.name,
                peak_electric_field_V_per_m=float(np.max(np.abs(actual))),
                receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
            )
        )
    args.output.write_text(
        json.dumps(
            dict(
                rows=rows,
                scope=(
                    "Saved field arrays in the declared WarpX SI convention; "
                    "independent of worker conversion settings"
                ),
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
