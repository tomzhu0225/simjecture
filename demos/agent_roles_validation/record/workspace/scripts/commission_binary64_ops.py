#!/usr/bin/env python3
"""Commission binary64 multiply and exp against independent known references."""
from __future__ import annotations

import json
import math
import struct
import sys
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 80

OUT = Path("artifacts/commission_binary64_ops.json")


def ulp_distance(a: float, b: float) -> int:
    if math.isnan(a) or math.isnan(b) or math.isinf(a) or math.isinf(b):
        return 10**9
    ia = struct.unpack("<Q", struct.pack("<d", a))[0]
    ib = struct.unpack("<Q", struct.pack("<d", b))[0]
    if ia >= 0x8000000000000000:
        ia = 0xFFFFFFFFFFFFFFFF - ia
    if ib >= 0x8000000000000000:
        ib = 0xFFFFFFFFFFFFFFFF - ib
    return abs(ia - ib)


def ten_multiplies(factor: float, start: float = 1.0) -> float:
    x = start
    for _ in range(10):
        x = factor * x
    return x


def main() -> None:
    mant_dig = int(sys.float_info.mant_dig)
    radix = int(sys.float_info.radix)
    half_pow10 = ten_multiplies(0.5, 1.0)
    half_expected = 2.0 ** -10
    half_pow10_error = abs(half_pow10 - half_expected)
    two_pow10 = ten_multiplies(2.0, 1.0)
    two_pow10_error = abs(two_pow10 - 1024.0)
    exp0 = math.exp(0.0)
    exp0_error = abs(exp0 - 1.0)

    dec_exp_m1 = Decimal(-1).exp()
    ref_exp_m1 = float(dec_exp_m1)
    lib_exp_m1 = math.exp(-1.0)
    exp_m1_ulps = ulp_distance(lib_exp_m1, ref_exp_m1)

    commissioning_passed = (
        mant_dig == 53
        and radix == 2
        and half_pow10_error == 0.0
        and two_pow10_error == 0.0
        and exp0_error == 0.0
        and exp_m1_ulps <= 1
    )

    payload = {
        "metrics": {
            "float_mant_dig": mant_dig,
            "float_radix": radix,
            "half_pow10": half_pow10,
            "half_pow10_error": half_pow10_error,
            "two_pow10": two_pow10,
            "two_pow10_error": two_pow10_error,
            "exp0": exp0,
            "exp0_error": exp0_error,
            "lib_exp_m1": lib_exp_m1,
            "decimal_ref_exp_m1": ref_exp_m1,
            "exp_m1_ulps": exp_m1_ulps,
            "commissioning_passed": commissioning_passed,
        },
        "reference": {
            "half_expected": half_expected,
            "two_expected": 1024.0,
            "exp0_expected": 1.0,
            "decimal_exp_m1_text": format(dec_exp_m1, ".50f"),
            "source": (
                "Independent of the Euler claim: exact binary64 dyadic products "
                "0.5**10 and 2**10, math.exp(0)==1, and Decimal(-1).exp() as an "
                "independent e^{-1} reference."
            ),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"wrote": str(OUT), "commissioning_passed": commissioning_passed}))


if __name__ == "__main__":
    main()