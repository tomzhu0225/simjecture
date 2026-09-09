#!/usr/bin/env python3
"""Commission binary64 rounding, sequential multiply vs pow, and exp(-1) series enclosure."""
from __future__ import annotations

import json
import math
import struct
import sys
from decimal import Decimal, getcontext
from fractions import Fraction
from math import factorial
from pathlib import Path

getcontext().prec = 80

OUT = Path("artifacts/commission_series_round_003.json")
SEQ_POW_ULP_TOLERANCE = 16
LIB_EXP_ULP_TOLERANCE = 1
SERIES_LAST = 24
SERIES_WIDTH_LIMIT = Fraction(1, 10**15)


def ulp_distance(a: float, b: float) -> int:
    if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
        return 10**9
    ia = struct.unpack("<Q", struct.pack("<d", a))[0]
    ib = struct.unpack("<Q", struct.pack("<d", b))[0]
    sign_bit = 0x8000000000000000
    if ia >= sign_bit:
        ia = 0xFFFFFFFFFFFFFFFF - ia
    if ib >= sign_bit:
        ib = 0xFFFFFFFFFFFFFFFF - ib
    return abs(ia - ib)


def ten_multiplies(factor: float, start: float = 1.0) -> float:
    x = start
    for _ in range(10):
        x = factor * x
    return x


def exp_m1_series_enclosure(n_last: int) -> tuple[Fraction, Fraction]:
    partial = Fraction(0)
    for k in range(n_last + 1):
        partial += Fraction((-1) ** k, factorial(k))
    next_term = Fraction((-1) ** (n_last + 1), factorial(n_last + 1))
    a = partial
    b = partial + next_term
    return (a, b) if a <= b else (b, a)


def decimal_in_enclosure(d: Decimal, lo: Fraction, hi: Fraction) -> bool:
    q = Fraction(d)
    return lo <= q <= hi


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


def ulps_from_interval(x: float, lo_f: float, hi_f: float) -> int:
    if lo_f <= x <= hi_f:
        return 0
    if x < lo_f:
        return ulp_distance(x, lo_f)
    return ulp_distance(x, hi_f)


def main() -> None:
    mant_dig = int(sys.float_info.mant_dig)
    radix = int(sys.float_info.radix)
    eps = float(sys.float_info.epsilon)

    halfway = 1.0 + 0.5 * eps
    next_up = 1.0 + eps
    round_nearest_even_at_one = halfway == 1.0
    nextafter_matches = next_up == math.nextafter(1.0, 2.0)
    ulp_two = 2.0 * eps
    halfway_two = 2.0 + 0.5 * ulp_two
    round_nearest_even_at_two = halfway_two == 2.0
    round_nearest_verified = (
        round_nearest_even_at_one and nextafter_matches and round_nearest_even_at_two
    )

    half_seq = ten_multiplies(0.5, 1.0)
    two_seq = ten_multiplies(2.0, 1.0)
    half_ok = half_seq == 2.0**-10
    two_ok = two_seq == 1024.0

    factor = 0.9
    seq_09 = ten_multiplies(factor, 1.0)
    pow_09 = math.pow(factor, 10)
    seq_vs_pow_ulps = ulp_distance(seq_09, pow_09)
    seq_vs_pow_within_tolerance = seq_vs_pow_ulps <= SEQ_POW_ULP_TOLERANCE
    seq_pow_bit_identical = seq_09 == pow_09

    exact_nine_tenths_pow10 = Fraction(9, 10) ** 10
    seq_09_frac = Fraction(*seq_09.as_integer_ratio())
    dist_to_nine_tenths = seq_09_frac - exact_nine_tenths_pow10

    lo, hi = exp_m1_series_enclosure(SERIES_LAST)
    series_width = hi - lo
    series_width_ok = series_width <= SERIES_WIDTH_LIMIT

    dec_exp_m1 = Decimal(-1).exp()
    lib_exp_m1 = math.exp(-1.0)
    series_contains_decimal = decimal_in_enclosure(dec_exp_m1, lo, hi)
    lo_f = outward_float_lower(lo)
    hi_f = outward_float_upper(hi)
    lib_exp_ulps_from_series = ulps_from_interval(lib_exp_m1, lo_f, hi_f)
    series_lib_exp_within_1_ulp = lib_exp_ulps_from_series <= LIB_EXP_ULP_TOLERANCE

    exp0 = math.exp(0.0)
    exp0_ok = exp0 == 1.0

    commissioning_passed = (
        mant_dig == 53
        and radix == 2
        and round_nearest_verified
        and half_ok
        and two_ok
        and exp0_ok
        and seq_vs_pow_within_tolerance
        and series_width_ok
        and series_contains_decimal
        and series_lib_exp_within_1_ulp
    )

    payload = {
        "metrics": {
            "commissioning_passed": commissioning_passed,
            "exp0_error": abs(exp0 - 1.0),
            "float_mant_dig": mant_dig,
            "float_radix": radix,
            "half_pow10_error": abs(half_seq - 2.0**-10),
            "lib_exp_ulps_from_series": lib_exp_ulps_from_series,
            "round_nearest_verified": round_nearest_verified,
            "seq_pow_bit_identical": seq_pow_bit_identical,
            "seq_vs_pow_ulp_tolerance": SEQ_POW_ULP_TOLERANCE,
            "seq_vs_pow_ulps": seq_vs_pow_ulps,
            "seq_vs_pow_within_tolerance": seq_vs_pow_within_tolerance,
            "series_contains_decimal": series_contains_decimal,
            "series_last_index": SERIES_LAST,
            "series_lib_exp_within_1_ulp": series_lib_exp_within_1_ulp,
            "series_width": float(series_width),
            "two_pow10_error": abs(two_seq - 1024.0),
        },
        "reference": {
            "decimal_exp_m1_text": format(dec_exp_m1, ".50f"),
            "dist_seq09_minus_nine_tenths_pow10": str(dist_to_nine_tenths),
            "exact_nine_tenths_pow10": str(exact_nine_tenths_pow10),
            "exp0_expected": 1.0,
            "half_expected": 2.0**-10,
            "lib_exp_ulp_tolerance": LIB_EXP_ULP_TOLERANCE,
            "seq_vs_pow_note": (
                "Sequential binary64 multiplication by 0.9 need not be "
                "bit-identical to math.pow; explicit tolerance is 16 ulps."
            ),
            "series_hi_text": str(hi),
            "series_lo_text": str(lo),
            "source": (
                "Independent known references: exact dyadic products 0.5**10 and "
                "2**10; math.exp(0)==1; Decimal(-1).exp() inside the Leibniz "
                "enclosure of exp(-1). Sequential 0.9 multiplies compared to "
                "pow with an explicit 16-ulp binary64 rounding tolerance. "
                "math.exp(-1) compared to the series enclosure with an explicit "
                "1-ulp tolerance."
            ),
            "two_expected": 1024.0,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "commissioning_passed": commissioning_passed,
                "seq_vs_pow_ulps": seq_vs_pow_ulps,
                "seq_pow_bit_identical": seq_pow_bit_identical,
                "lib_exp_ulps_from_series": lib_exp_ulps_from_series,
            }
        )
    )


if __name__ == "__main__":
    main()