"""Independent quadrature diagnostics for exact initial means and entropy excess.

The universal bounds are Lean theorems. These quadrature differences are
numerical diagnostics, not certified integration errors or future PDE errors.
"""

import argparse
import hashlib
import json
from pathlib import Path

import entropy_candidate as ec
import finite_volume as fv
import numpy as np


def quadrature(order):
    z, w = np.polynomial.legendre.leggauss(order)
    axis, weights = np.pi * (z + 1), w / 2
    points = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
    weights3 = weights[:, None, None] * weights[None, :, None] * weights[None, None, :]
    return points, weights3


def point_initial(points, amplitude, delta):
    """Direct physical formulas, independent of the analytic cell-average code."""
    sx, sy, sz = np.moveaxis(np.sin(points), -1, 0)
    cx, cy, cz = np.moveaxis(np.cos(points), -1, 0)
    c2x, c2y, c2z = np.moveaxis(np.cos(2 * points), -1, 0)
    density = 1 + delta * sx * sy * sz
    pressure = 1 + amplitude**2 / 16 * (c2x + c2y) * (c2z + 2)
    velocity = np.stack(
        [amplitude * sx * cy * cz, -amplitude * cx * sy * cz, np.zeros_like(sx)], axis=-1
    )
    state = np.empty((*density.shape, 5))
    state[..., 0], state[..., 1:4] = density, density[..., None] * velocity
    state[..., 4] = pressure + 0.5 * density * np.sum(velocity**2, axis=-1)
    return state, pressure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rules = {order: quadrature(order) for order in [24, 48]}
    rows = []
    for amplitude in np.linspace(0.5, 1, 5):
        for delta in np.linspace(-0.05, 0.05, 5):
            entropies = []
            for order, (points, weights) in rules.items():
                state, p = point_initial(points, amplitude, delta)
                rho = state[..., 0]
                entropy = ec.entropy(state)
                entropies.append(float(np.sum(weights * entropy)))
                if order == 48:
                    mean = np.sum(weights[..., None] * state, axis=(0, 1, 2))
                    expected = np.array([1, 0, 0, 0, 1 + amplitude**2 / 8])
                    excess = entropies[-1] - float(ec.entropy(expected))
                    lower = -rho * (p - 1) + 2 * (rho - 1)
                    row = dict(
                        A=float(amplitude),
                        delta=float(delta),
                        mean_state=mean.tolist(),
                        mean_max_error=float(np.max(np.abs(mean - expected))),
                        density_pressure_moment=float(np.sum(weights * rho * (p - 1))),
                        pressure_formula_error=float(np.max(np.abs(fv.pressure(state) - p))),
                        minimum_pointwise_entropy_slack=float(np.min(entropy - lower)),
                        entropy_quadrature=entropies[-1],
                        entropy_excess_quadrature=excess,
                        excess_above_uniform_bound=excess - 1 / 33,
                        log_mean_energy=float(np.log1p(amplitude**2 / 8)),
                    )
            row["entropy_quadrature_difference_24_48"] = abs(entropies[-1] - entropies[0])
            assert row["mean_max_error"] < 2e-12
            assert abs(row["density_pressure_moment"]) < 2e-12
            assert row["pressure_formula_error"] < 2e-14
            assert row["minimum_pointwise_entropy_slack"] >= -2e-14
            assert row["entropy_quadrature"] >= 0
            assert row["excess_above_uniform_bound"] > 0
            assert row["log_mean_energy"] >= 1 / 33
            assert row["entropy_quadrature_difference_24_48"] < 1e-9
            rows.append(row)
    here = Path(__file__).resolve().parent
    record = dict(
        scope="Initial-field quadrature only; no certified integration or evolved-solution error",
        quadrature_orders=list(rules),
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in [
                "validate_initial_excess.py",
                "finite_volume.py",
                "entropy_candidate.py",
                "contract.json",
            ]
        },
        uniform_proved_excess_lower_bound=1 / 33,
        small_error_threshold_for_half_excess=1 / 21120,
        rows=rows,
    )
    (args.output / "initial-excess-validation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"status": "passed", "parameter_cases": len(rows)}))


if __name__ == "__main__":
    main()
