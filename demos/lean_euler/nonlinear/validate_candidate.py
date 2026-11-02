"""Independent quadrature, admissibility and conservation checks for the candidate."""

import argparse
import hashlib
import json
from pathlib import Path

import finite_volume as fv
import numpy as np


def point_state(x, y, z, amplitude, delta):
    rho = 1 + delta * np.sin(x) * np.sin(y) * np.sin(z)
    vx = amplitude * np.sin(x) * np.cos(y) * np.cos(z)
    vy = -amplitude * np.cos(x) * np.sin(y) * np.cos(z)
    p = 1 + amplitude**2 / 16 * (np.cos(2 * x) + np.cos(2 * y)) * (np.cos(2 * z) + 2)
    return np.array([rho, rho * vx, rho * vy, 0.0, p + rho * (vx * vx + vy * vy) / 2])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    nodes, weights = np.polynomial.legendre.leggauss(8)
    quadrature_error = 0.0
    for n in [8, 15]:
        avg = fv.cell_averages(n, 0.9, -0.04)
        h = 2 * np.pi / n
        for index in [(0, 1, 2), (n - 1, n - 2, n - 3)]:
            center = (np.array(index) + 0.5) * h
            integral = np.zeros(5)
            for i, a in enumerate(nodes):
                for j, b in enumerate(nodes):
                    for k, c in enumerate(nodes):
                        xyz = center + np.array([a, b, c]) * h / 2
                        integral += (
                            weights[i] * weights[j] * weights[k] / 8 * point_state(*xyz, 0.9, -0.04)
                        )
            quadrature_error = max(quadrature_error, float(np.max(np.abs(integral - avg[index]))))
    assert quadrature_error < 2e-12

    rng = np.random.default_rng(20261102)
    rho = 10 ** rng.uniform(-2, 1, (6, 7, 8))
    p = 10 ** rng.uniform(-2, 1, rho.shape)
    v = rng.uniform(-3, 3, (*rho.shape, 3))
    u = np.empty((*rho.shape, 5))
    u[..., 0], u[..., 1:4] = rho, rho[..., None] * v
    u[..., 4] = p + 0.5 * rho * np.sum(v * v, axis=-1)
    pp, vv, a = fv.primitives(u)
    minimum_split_pressure = float("inf")
    for d in range(3):
        f = fv.physical_flux(u, pp, vv, d)
        for sign in [-1, 1]:
            split = u + sign / a[d] * f
            minimum_split_pressure = min(minimum_split_pressure, float(fv.pressure(split).min()))
            assert split[..., 0].min() > 0 and fv.pressure(split).min() > 0
    updated = fv.step(u, 1 / a.sum())
    fv.primitives(updated)
    conservation_error = float(np.max(np.abs(updated.mean((0, 1, 2)) - u.mean((0, 1, 2)))))
    assert conservation_error < 1e-11

    unsafe = np.array([[[[1.0, 10.0, 0.0, 0.0, 1.0]]]])
    assert fv.pressure(unsafe).item() == -49
    rows = []
    for A, delta in [(0.5, -0.05), (0.75, 0), (1.0, 0.05)]:
        for n in [16, 32]:
            original = fv.cell_averages(n, A, delta)
            result = fv.solve(n, A, delta)
            drift = float(np.max(np.abs(result.field.mean((0, 1, 2)) - original.mean((0, 1, 2)))))
            assert drift < 1e-11
            rows.append(
                dict(
                    n=n,
                    A=A,
                    delta=delta,
                    steps=result.steps,
                    cell_updates=result.cell_updates,
                    final_time=result.time,
                    conservation_error=drift,
                    min_density=float(result.field[..., 0].min()),
                    min_pressure=float(fv.pressure(result.field).min()),
                    vertical_velocity_max=float(
                        np.max(np.abs(result.field[..., 3] / result.field[..., 0]))
                    ),
                )
            )
    here = Path(__file__).resolve().parent
    report = dict(
        scope=(
            "Candidate initialization/admissibility/conservation checks; "
            "no continuum accuracy or optimality certificate"
        ),
        cell_average_quadrature_max_error=quadrature_error,
        random_state_split_min_pressure=minimum_split_pressure,
        random_state_update_conservation_error=conservation_error,
        unsafe_flux_splitting_pressure=-49,
        rows=rows,
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in ["finite_volume.py", "validate_candidate.py", "contract.json"]
        },
    )
    (args.output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
