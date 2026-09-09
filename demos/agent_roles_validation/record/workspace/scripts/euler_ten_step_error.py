#!/usr/bin/env python3
"""Ten-step explicit Euler for y'=-y versus exp(-1) in binary64."""
from __future__ import annotations

import json
import math
from pathlib import Path

OUT = Path("artifacts/euler_ten_step_error.json")
N_STEPS = 10
X0 = 1.0
MULTIPLIER = 0.9
THRESHOLD = 0.001


def main() -> None:
    x = float(X0)
    trajectory = [x]
    for _ in range(N_STEPS):
        x = MULTIPLIER * x
        trajectory.append(x)
    reference = math.exp(-1.0)
    abs_error = abs(x - reference)
    error_at_most_threshold = bool(abs_error <= THRESHOLD)
    payload = {
        "metrics": {
            "n_steps": N_STEPS,
            "x0": X0,
            "multiplier": MULTIPLIER,
            "x10": x,
            "reference_exp_m1": reference,
            "abs_error": abs_error,
            "threshold": THRESHOLD,
            "error_at_most_threshold": error_at_most_threshold,
        },
        "method": "explicit Euler x_{n+1} = 0.9 * x_n in IEEE-754 binary64 Python float",
        "trajectory": trajectory,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "abs_error": abs_error,
                "error_at_most_threshold": error_at_most_threshold,
            }
        )
    )


if __name__ == "__main__":
    main()