#!/usr/bin/env python3
"""Ten-step explicit Euler versus exp(-1) with a Leibniz series error enclosure."""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from math import factorial
from pathlib import Path

OUT = Path("artifacts/euler_bound_002_prospective.json")
N_STEPS = 10
X0 = 1.0
MULTIPLIER = 0.9
THRESHOLD = 0.02
SERIES_LAST = 24


def exp_m1_series_enclosure(n_last: int) -> tuple[Fraction, Fraction]:
    partial = Fraction(0)
    for k in range(n_last + 1):
        partial += Fraction((-1) ** k, factorial(k))
    next_term = Fraction((-1) ** (n_last + 1), factorial(n_last + 1))
    a = partial
    b = partial + next_term
    return (a, b) if a <= b else (b, a)


def outward_float_lower(q: Fraction) -> float:
    f = float(q)
    if not math.isfinite(f):
        return f
    fq = Fraction(*f.as_integer_ratio())
    if fq > q:
        f = math.nextafter(f, float("-inf"))
    return f


def outward_float_upper(q: Fraction) -> float:
    f = float(q)
    if not math.isfinite(f):
        return f
    fq = Fraction(*f.as_integer_ratio())
    if fq < q:
        f = math.nextafter(f, float("inf"))
    return f


def abs_error_enclosure(
    x: Fraction, e_lo: Fraction, e_hi: Fraction
) -> tuple[Fraction, Fraction]:
    if x < e_lo:
        return (e_lo - x, e_hi - x)
    if x > e_hi:
        return (x - e_hi, x - e_lo)
    return (Fraction(0), max(x - e_lo, e_hi - x))


def verify_binary64(trajectory: list[float], multiplier: float) -> bool:
    mant_dig = int(sys.float_info.mant_dig)
    radix = int(sys.float_info.radix)
    eps = float(sys.float_info.epsilon)
    halfway = 1.0 + 0.5 * eps
    next_up = 1.0 + eps
    round_ok = halfway == 1.0 and next_up == math.nextafter(1.0, 2.0)
    half = 1.0
    for _ in range(10):
        half = 0.5 * half
    dyadic_ok = half == 2.0**-10
    sequential_ok = len(trajectory) == N_STEPS + 1 and trajectory[0] == X0
    for i in range(N_STEPS):
        if trajectory[i + 1] != multiplier * trajectory[i]:
            sequential_ok = False
            break
    return mant_dig == 53 and radix == 2 and round_ok and dyadic_ok and sequential_ok


def main() -> None:
    x = float(X0)
    trajectory = [x]
    for _ in range(N_STEPS):
        x = MULTIPLIER * x
        trajectory.append(x)
    binary64_verified = verify_binary64(trajectory, MULTIPLIER)
    reference = math.exp(-1.0)
    abs_error = abs(x - reference)

    e_lo, e_hi = exp_m1_series_enclosure(SERIES_LAST)
    x_frac = Fraction(*x.as_integer_ratio())
    err_lo, err_hi = abs_error_enclosure(x_frac, e_lo, e_hi)
    error_lower = outward_float_lower(err_lo)
    error_upper = outward_float_upper(err_hi)
    interval_width = error_upper - error_lower
    wholly_above_threshold = error_lower > THRESHOLD
    wholly_at_or_below_threshold = error_upper <= THRESHOLD

    payload = {
        "enclosure_method": (
            "exp(-1) is enclosed by consecutive alternating Taylor partial "
            "sums S_24 and S_25 (Leibniz next-term remainder 1/25!). The "
            "observed x10 is converted to an exact rational via "
            "as_integer_ratio. Absolute-error endpoints are outward-rounded "
            "to binary64. math.exp(-1) is a commissioned library reference, "
            "not the enclosure source."
        ),
        "metrics": {
            "abs_error": abs_error,
            "binary64_verified": binary64_verified,
            "error_lower": error_lower,
            "error_upper": error_upper,
            "float_mant_dig": int(sys.float_info.mant_dig),
            "float_radix": int(sys.float_info.radix),
            "interval_width": interval_width,
            "multiplier": MULTIPLIER,
            "n_steps": N_STEPS,
            "reference_exp_m1": reference,
            "series_last_index": SERIES_LAST,
            "threshold": THRESHOLD,
            "wholly_above_threshold": wholly_above_threshold,
            "wholly_at_or_below_threshold": wholly_at_or_below_threshold,
            "x0": X0,
            "x10": x,
        },
        "series_enclosure": {
            "exp_m1_hi": str(e_hi),
            "exp_m1_lo": str(e_lo),
            "error_hi_rational": str(err_hi),
            "error_lo_rational": str(err_lo),
        },
        "trajectory": trajectory,
        "trajectory_hex": [value.hex() for value in trajectory],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "abs_error": abs_error,
                "binary64_verified": binary64_verified,
                "error_lower": error_lower,
                "error_upper": error_upper,
                "wholly_above_threshold": wholly_above_threshold,
                "wholly_at_or_below_threshold": wholly_at_or_below_threshold,
            }
        )
    )


if __name__ == "__main__":
    main()