"""Audit continuous density reconstruction separately from cell-average error."""

import importlib.util
import itertools
import json
import time
from pathlib import Path

import numpy as np

spec = importlib.util.spec_from_file_location("accuracy_study", "study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def reconstruct(rho):
    slopes = []
    for axis in range(3):
        minus = rho - np.roll(rho, 1, axis=axis)
        plus = np.roll(rho, -1, axis=axis) - rho
        slopes.append(study.minmod3(2 * minus, (minus + plus) / 2, 2 * plus))
    return slopes


def error(rho, slopes, t, order):
    n = rho.shape[0]
    x = (np.arange(n) + 0.5) / n
    phase = x[:, None, None] + x[None, :, None] + x[None, None, :] - 0.6 * t
    nodes, weights = np.polynomial.legendre.leggauss(order)
    result = 0.0
    for ix, iy, iz in itertools.product(range(order), repeat=3):
        offsets = np.array([nodes[ix], nodes[iy], nodes[iz]]) / 2
        approx = rho + sum(s * d for s, d in zip(slopes, offsets, strict=True))
        exact = 1 + 0.1 * np.sin(2 * np.pi * (phase + sum(offsets) / n))
        result += weights[ix] * weights[iy] * weights[iz] / 8 * float(abs(approx - exact).mean())
    return result


def main():
    rows = []
    for method, n, eps in [
        ("fused", 16, 0.02),
        ("fused", 32, 0.01),
        ("fused", 64, 0.005),
        ("muscl_rk2", 8, 0.01),
        ("muscl_rk2", 16, 0.005),
    ]:
        u, row = study.solve(n, method, 0.05, 0.3)
        study.assess(u, row, 0.05)
        start = time.perf_counter()
        slopes = reconstruct(u[..., 0])
        reconstruct_time = time.perf_counter() - start
        low = error(u[..., 0], slopes, 0.05, 3)
        high = error(u[..., 0], slopes, 0.05, 5)
        rows.append(
            dict(
                method=method,
                n=n,
                epsilon=eps,
                cell_average_l1=row["density_l1"],
                reconstruction_l1_order3=low,
                reconstruction_l1_order5=high,
                quadrature_order_difference=abs(high - low),
                reconstruction_seconds=reconstruct_time,
                solve_plus_reconstruction_seconds=row["solver_seconds"] + reconstruct_time,
                numerically_meets_reconstructed_target=bool(high <= eps),
            )
        )
    # Exact single-cell means hide the entire wave. This is why the output
    # representation belongs in the accuracy contract, not just a reported norm.
    invisible = study.exact_state(1, 0.05)[..., 0]
    alias = error(invisible, [np.zeros_like(invisible)] * 3, 0.05, 12)
    assert alias > 0.04
    result = dict(
        cases=rows,
        one_cell_projection_negative_control=dict(cell_average_error=0.0, reconstructed_l1=alias),
        scope=(
            "Numerical quadrature audit of a common piecewise-linear density output; "
            "not an interval-certified continuum error bound"
        ),
        timing=(
            "One audit solve per selected case, including reconstruction; "
            "not repeated performance measurements"
        ),
    )
    Path("representation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
