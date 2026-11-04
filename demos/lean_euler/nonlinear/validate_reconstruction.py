"""Independent hat/quadrature checks for the continuous periodic reconstruction.

Quadrature diagnostics do not certify continuum Euler error. The unknown
Taylor-Green evolution remains the research target.
"""

import argparse
import hashlib
import json
from pathlib import Path

import entropy_candidate as ec
import finite_volume as fv
import numpy as np
from reconstruction import reconstruct
from validate_region_bounds import random_region, region_values


def dense_weights(n, points, side=2 * np.pi):
    """Independent three-copy tent formula on the physical cube."""
    s = np.asarray(points)[..., None] * (n / side) - 0.5 - np.arange(n)
    return sum(np.maximum(0, 1 - np.abs(s + shift * n)) for shift in [-1, 0, 1])


def dense_reconstruct(field, points, side=2 * np.pi):
    w = dense_weights(len(field), points, side)
    return np.einsum("pi,pj,pk,ijkc->pc", w[:, 0], w[:, 1], w[:, 2], field)


def quadrature(n, side=2 * np.pi, order=2):
    """Tensor Gauss rule split at every cell center, where hat slopes change."""
    centers = (np.arange(n) + 0.5) * side / n
    edges = np.r_[0, centers, side]
    z, w = np.polynomial.legendre.leggauss(order)
    midpoint = 0.5 * (edges[1:] + edges[:-1])
    halfwidth = 0.5 * np.diff(edges)
    axis = (midpoint[:, None] + halfwidth[:, None] * z).ravel()
    axis_weights = (halfwidth[:, None] * w / side).ravel()
    points = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1).reshape(-1, 3)
    weights = (
        axis_weights[:, None, None] * axis_weights[None, :, None] * axis_weights[None, None, :]
    ).ravel()
    return axis, axis_weights, points, weights


def integrated_checks(field):
    n = len(field)
    axis, axis_weights, points, weights = quadrature(n)
    values = reconstruct(field, points)
    mean_error = float(np.max(np.abs(weights @ values - field.mean((0, 1, 2)))))
    grid_entropy = float(ec.entropy(field).mean())
    sampled_entropy = float(weights @ ec.entropy(values))
    return dict(
        mean_error=mean_error,
        quadrature_total_weight=float(weights.sum()),
        axis_weight_integral_error=float(
            np.max(np.abs(axis_weights @ dense_weights(n, axis) - 1 / n))
        ),
        grid_entropy=grid_entropy,
        quadrature_reconstructed_entropy=sampled_entropy,
        quadrature_entropy_margin=grid_entropy - sampled_entropy,
        reconstruction_region_margin=region_values(values)["minimum_region_margin"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20261108)
    random_rows, family_rows = [], []
    side = 2 * np.pi
    for n in [1, 2, 3, 5]:
        field = random_region(rng, n**3).reshape(n, n, n, 5)
        points = rng.uniform(0, side, size=(4096, 3))
        actual, independent = reconstruct(field, points), dense_reconstruct(field, points)
        center = (np.arange(n) + 0.5) * side / n
        nodes = np.stack(np.meshgrid(center, center, center, indexing="ij"), axis=-1)
        node_error = float(np.max(np.abs(reconstruct(field, nodes) - field)))
        shifted = points + side * rng.integers(-3, 4, size=points.shape)
        periodic_error = float(np.max(np.abs(reconstruct(field, shifted) - actual)))
        seam_error = 0.0
        for d in range(3):
            left, right = points.copy(), points.copy()
            left[:, d], right[:, d] = 0, side
            seam_error = max(
                seam_error,
                float(np.max(np.abs(reconstruct(field, left) - reconstruct(field, right)))),
            )
        ws = dense_weights(n, points)
        row = dict(
            n=n,
            queries=len(points),
            dense_sparse_error=float(np.max(np.abs(actual - independent))),
            node_error=node_error,
            periodic_error=periodic_error,
            seam_error=seam_error,
            min_weight=float(ws.min()),
            weight_sum_error=float(np.max(np.abs(ws.sum(-1) - 1))),
            **integrated_checks(field),
        )
        assert row["dense_sparse_error"] < 3e-13
        assert node_error < 3e-13 and periodic_error < 3e-13 and seam_error == 0
        assert row["min_weight"] >= 0 and row["weight_sum_error"] < 1e-14
        random_rows.append(row)

    # New reconstruction diagnostics on actual nonlinear solves; no exact future
    # field is supplied, so these are not measurements of continuum solution error.
    for n, amplitude, delta in [(16, 0.5, -0.05), (16, 0.75, 0), (16, 1.0, 0.05), (32, 1.0, 0.05)]:
        result = ec.solve(n, amplitude, delta)
        row = dict(
            n=n,
            A=amplitude,
            delta=delta,
            final_time=result.time,
            steps=result.steps,
            rejected_steps=result.rejected_steps,
            **integrated_checks(result.field),
        )
        family_rows.append(row)

    for row in random_rows + family_rows:
        assert row["mean_error"] < 5e-13
        assert abs(row["quadrature_total_weight"] - 1) < 2e-14
        assert row["axis_weight_integral_error"] < 2e-14
        assert row["quadrature_entropy_margin"] >= -2e-14
        assert row["reconstruction_region_margin"] >= 0
    constant = np.broadcast_to(np.array([1.0, 0.2, -0.3, 0.4, 1.5]), (3, 3, 3, 5))
    constant_error = float(np.max(np.abs(reconstruct(constant, points) - constant[0, 0, 0])))
    assert constant_error < 2e-15 and np.min(fv.pressure(reconstruct(constant, points))) > 0
    here = Path(__file__).resolve().parent
    record = dict(
        scope="Continuous-reconstruction diagnostics; no certified continuum-error measurement",
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in [
                "reconstruction.py",
                "validate_reconstruction.py",
                "entropy_candidate.py",
                "finite_volume.py",
                "validate_region_bounds.py",
                "validate_entropy_candidate.py",
                "contract.json",
            ]
        },
        constant_error=constant_error,
        random_rows=random_rows,
        family_rows=family_rows,
    )
    (args.output / "reconstruction-validation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        json.dumps(
            {"status": "passed", "random_grids": len(random_rows), "solves": len(family_rows)}
        )
    )


if __name__ == "__main__":
    main()
