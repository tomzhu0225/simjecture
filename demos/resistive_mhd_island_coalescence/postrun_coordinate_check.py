"""Diagnose the recorded minimal run's half-cell path error; no model calls.

Default: an independently specified analytic field. --study additionally reads
retained raw FLASH archives from an original study directory. It performs no new
simulation, changes no archived receipt and creates no accepted claim verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

import numpy as np
from coordinate_paths import midline_paths

HERE = Path(__file__).resolve().parent
CASES = [
    "exp_c82be7437f3086601d26cdc7",
    "exp_9782e73d183bd77e86261640",
    "exp_9e3db9fe2b479941a809ebd9",
    "exp_e7019f81e0a9d3630488f26e",
    "exp_bed50fd68869aa9e6441647b",
]


def original_paths(bx, by):
    # The mathematical operations in the archived az_midline_paths function,
    # preserved here to avoid importing its plotting/HDF5 dependencies for the
    # no-key analytic control. The original source remains in minimal_record.
    ny, nx = bx.shape
    dx = dy = 1 / nx
    mid = ny // 2
    by_middle = 0.5 * (by[mid - 1] + by[mid])
    bottom = -np.r_[0.0, np.cumsum(0.5 * (by[0, :-1] + by[0, 1:]) * dx)]
    vertical = bottom + np.sum(bx[:mid], axis=0) * dy
    horizontal = vertical[0] - np.r_[0.0, np.cumsum(0.5 * (by_middle[:-1] + by_middle[1:]) * dx)]
    return float(
        np.max(np.abs(vertical - horizontal)) / max(np.ptp(vertical), np.ptp(horizontal), 1e-300)
    )


def analytic_check(n=96):
    x = -0.5 + (np.arange(n) + 0.5) / n
    xx, yy = np.meshgrid(x, x)
    bx, by = 2 * xx * yy, -(yy**2 + 0.005)
    fixed = midline_paths(bx, by, dx=1 / n, dy=1 / n)
    # A_z=x*(y^2+eps); average its two center-row values, subtract the gauge.
    expected = x * (0.005 + 0.25 / n**2)
    expected -= expected[0]
    np.testing.assert_allclose(fixed["from_bx"] - fixed["from_bx"][0], expected, rtol=0, atol=2e-14)
    np.testing.assert_allclose(fixed["from_by"] - fixed["from_by"][0], expected, rtol=0, atol=2e-14)
    return {
        "potential": "A_z=x*(y^2+0.005)",
        "grid": [n, n],
        "original_relative_mismatch": original_paths(bx, by),
        "coordinate_consistent_relative_mismatch": fixed["relative_mismatch"],
        "independent_reference": (
            "Exact average of the two central analytic A_z rows, with a common gauge."
        ),
    }


def check_study(study):
    import importlib.util

    import h5py

    archived = (
        HERE / "minimal_record/experiments/exp_524cf7f12140e1f2e5cc0115/workspace/analysis.py"
    )
    spec = importlib.util.spec_from_file_location("retained_analysis", archived)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    results = []
    for identifier in CASES:
        record = json.loads((study / "experiments" / (identifier + ".json")).read_text())
        workspace = study / "experiments" / identifier / "workspace"
        archive = next(workspace.rglob("raw.tar.gz"))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        assert record["artifacts"][str(archive.relative_to(workspace))]["sha256"] == digest
        states = []
        with tarfile.open(archive) as tf:
            for member in tf:
                if "hdf5_plt_cnt_" not in member.name:
                    continue
                with h5py.File(io.BytesIO(tf.extractfile(member).read())) as f:
                    tm = next(
                        float(r["value"])
                        for r in f["real scalars"]
                        if r["name"].decode().strip() == "time"
                    )
                    states.append(
                        (tm, f["magx"][0, 0].astype(float), f["magy"][0, 0].astype(float))
                    )
        states.sort(key=lambda s: s[0])
        zero = old.flux_from_by(states[0][2])
        original, corrected = [], []
        for _, bx, by in states:
            if 0.01 <= old.flux_from_by(by) - zero <= 0.05:
                original.append(old.az_midline_paths(bx, by)[2])
                np.testing.assert_allclose(original_paths(bx, by), original[-1], rtol=1e-14)
                corrected.append(
                    midline_paths(bx, by, dx=1 / bx.shape[1], dy=1 / bx.shape[0])[
                        "relative_mismatch"
                    ]
                )
        results.append(
            {
                "experiment": identifier,
                "nx": states[0][1].shape[1],
                "original_max_relative_mismatch": max(original),
                "coordinate_consistent_max_relative_mismatch": max(corrected),
                "window_states": len(corrected),
                "archive_sha256": digest,
            }
        )
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study", type=Path, help="Original local study with retained raw archives")
    p.add_argument("--output", type=Path, help="New JSON report; never overwrites an existing file")
    args = p.parse_args()
    report = {
        "scope": (
            "Post-run operator diagnosis, separate from the original agent record. "
            "No new simulation or accepted scaling verdict."
        ),
        "analytic_control": analytic_check(),
        "source_sha256": {
            f.name: hashlib.sha256(f.read_bytes()).hexdigest()
            for f in [Path(__file__).resolve(), HERE / "coordinate_paths.py"]
        },
    }
    if args.study:
        report["recorded_cases"] = check_study(args.study)
    if args.output:
        with args.output.open("x") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
