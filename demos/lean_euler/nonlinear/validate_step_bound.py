"""Numerical diagnostics for the proved exact-real, state-dependent retry bound.

Floating-point evaluation of a proved formula is not a validated enclosure.
This diagnostic does not change the candidate's timesteps or claim accuracy.
"""

import argparse
import hashlib
import json
from pathlib import Path

import entropy_candidate as ec
import finite_volume as fv
import numpy as np
from validate_entropy_candidate import conserved


def bound_quantities(u, increment):
    rho, p, _, _ = ec.state_fields(u)
    k, kr = increment, increment[..., 0]
    quadratic = 2 * rho * p
    first = (
        2 * kr * u[..., 4] + 2 * rho * k[..., 4] - 2 * np.sum(u[..., 1:4] * k[..., 1:4], axis=-1)
    )
    second = 2 * kr * k[..., 4] - np.sum(k[..., 1:4] ** 2, axis=-1)
    rate = np.abs(kr) / rho + (np.abs(first) + np.abs(second)) / quadratic
    radius = float(1 / (2 * (1 + np.max(rate))))
    first_bound = np.abs(first) + 2 * np.abs(second)
    curvature = (
        6 * kr**2 / rho
        + 4 * np.abs(kr) * first_bound / quadratic
        + 6 * rho * np.abs(second) / quadratic
        + 6 * rho * (first_bound / quadratic) ** 2
    )
    assert radius > 0 and np.all(np.isfinite(curvature)) and np.min(curvature) >= 0
    return radius, curvature, quadratic, first, second


def numerical_cap(u, prepared):
    radius, curvature, *_ = bound_quantities(u, prepared.increment)
    budget, dissipation = float(curvature.mean()), prepared.dissipation
    if dissipation == 0:
        return radius, budget, None
    assert dissipation > 0
    return radius, budget, min(radius, dissipation / (budget + dissipation))


def numerical_retry_bound(proposal_ratio, cap):
    if cap is None:
        return 0
    # Integer ceil-log2 avoids a second floating-point logarithm near powers of 2.
    ceiling = int(np.ceil(proposal_ratio / cap))
    return max(0, (ceiling - 1).bit_length())


def complex_directional_hessian(u, k):
    """Complex-step derivative of the entropy gradient, independent of the bound."""
    z = u.astype(complex) + 1e-30j * k
    rho = z[..., 0]
    velocity = z[..., 1:4] / rho[..., None]
    p = z[..., 4] - np.sum(z[..., 1:4] ** 2, axis=-1) / (2 * rho)
    gradient = np.empty_like(z)
    gradient[..., 0] = (
        2 - np.log(p) + 2 * np.log(rho) - rho * np.sum(velocity**2, axis=-1) / (2 * p)
    )
    gradient[..., 1:4] = z[..., 1:4] / p[..., None]
    gradient[..., 4] = -rho / p
    return np.sum(gradient.imag * k, axis=-1) / 1e-30


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20261105)
    rho = 10 ** rng.uniform(-1, 1, 2048)
    pressure = 10 ** rng.uniform(-1, 1, 2048)
    velocity = rng.uniform(-2, 2, (2048, 3))
    u = conserved(rho, pressure, velocity)
    k = rng.normal(size=u.shape) * rng.uniform(0.01, 2, (2048, 1))
    radius, curvature, q, first, second = bound_quantities(u, k)
    hessian_error = 0.0
    smallest_margin = np.inf
    smallest_density_ratio, smallest_quadratic_ratio = np.inf, np.inf
    for fraction in [0, 0.1, 0.5, 0.9, 1]:
        ratio = fraction * radius
        trial = u + ratio * k
        qt = 2 * trial[..., 0] * fv.pressure(trial)
        qpoly = q + ratio * first + ratio**2 * second
        assert np.max(np.abs(qt - qpoly) / (1 + np.abs(qpoly))) < 5e-13
        ft = first + 2 * ratio * second
        explicit = (
            3 * k[..., 0] ** 2 / trial[..., 0]
            - 2 * k[..., 0] * ft / qt
            - 2 * trial[..., 0] * second / qt
            + trial[..., 0] * (ft / qt) ** 2
        )
        independent = complex_directional_hessian(trial, k)
        hessian_error = max(
            hessian_error,
            float(np.max(np.abs(explicit - independent) / (1 + np.abs(independent)))),
        )
        smallest_margin = min(
            smallest_margin, float(np.min((curvature - independent) / (1 + curvature)))
        )
        smallest_density_ratio = min(smallest_density_ratio, float(np.min(trial[..., 0] / rho)))
        smallest_quadratic_ratio = min(smallest_quadratic_ratio, float(np.min(qt / q)))
    assert hessian_error < 1e-10
    assert smallest_margin >= 0
    assert smallest_density_ratio >= 0.5 and smallest_quadratic_ratio >= 0.5

    # Exercise a nonzero retry bound and the zero-dissipation branch.
    initial = fv.cell_averages(8, 1, 0.05)
    prepared = ec._prepare(initial)
    dx = 2 * np.pi / 8
    _, _, control_cap = numerical_cap(initial, prepared)
    control_ratio = 10 / prepared.speeds.sum()
    predicted = numerical_retry_bound(control_ratio, control_cap)
    actual = ec._step_prepared(initial, dx, control_ratio * dx, prepared)
    assert 0 < actual.rejected <= predicted
    assert actual.dt / dx >= min(control_ratio, control_cap / 2)
    constant = np.broadcast_to(np.array([1.0, 0.2, -0.3, 0.4, 1.5]), (4, 4, 4, 5)).copy()
    zero = ec._prepare(constant)
    _, _, zero_cap = numerical_cap(constant, zero)
    assert zero.dissipation == 0 and zero_cap is None
    assert numerical_retry_bound(100, zero_cap) == 0

    rows = []
    for amplitude, delta in [(0.5, -0.05), (0.75, 0), (1.0, 0.05)]:
        for n in [16, 32, 64]:
            field = fv.cell_averages(n, amplitude, delta)
            dx, time, steps = 2 * np.pi / n, 0.0, 0
            max_retries, max_actual, max_ratio = 0, 0, 0.0
            min_cap, min_radius, min_acceptance_slack = np.inf, np.inf, np.inf
            while time < 0.25:
                prepared = ec._prepare(field)
                proposal = min(0.25 - time, 0.3 * dx / prepared.speeds.sum())
                radius, budget, cap = numerical_cap(field, prepared)
                retries = numerical_retry_bound(proposal / dx, cap)
                result = ec._step_prepared(field, dx, proposal, prepared)
                assert result.rejected <= retries
                if cap is not None:
                    assert result.dt / dx >= min(proposal / dx, cap / 2)
                    min_cap = min(min_cap, cap)
                    max_ratio = max(max_ratio, (proposal / dx) / cap)
                    min_acceptance_slack = min(
                        min_acceptance_slack,
                        prepared.dissipation - (proposal / dx) * budget,
                    )
                max_retries = max(max_retries, retries)
                max_actual = max(max_actual, result.rejected)
                min_radius = min(min_radius, radius)
                field, time, steps = result.field, time + result.dt, steps + 1
            row = dict(
                A=amplitude,
                delta=delta,
                n=n,
                final_time=time,
                steps=steps,
                max_predicted_halvings=max_retries,
                max_actual_halvings=max_actual,
                max_proposal_over_cap=max_ratio,
                min_cap=min_cap,
                min_radius=min_radius,
                min_entropy_budget_slack=min_acceptance_slack,
            )
            rows.append(row)
            print(json.dumps(row), flush=True)
    here = Path(__file__).resolve().parent
    report = dict(
        scope=(
            "Float diagnostics of explicit exact-real state-dependent bounds. No certified "
            "rounding enclosure, uniform family/trajectory estimate, continuum accuracy or "
            "total-work optimality. The solver does not execute this diagnostic bound."
        ),
        random_states=2048,
        hessian_complex_step_max_scaled_error=hessian_error,
        minimum_scaled_curvature_margin=smallest_margin,
        minimum_density_ratio=smallest_density_ratio,
        minimum_quadratic_ratio=smallest_quadratic_ratio,
        excessive_proposal_control=dict(
            proposal_ratio=float(control_ratio),
            cap=float(control_cap),
            predicted_halvings=predicted,
            actual_halvings=actual.rejected,
        ),
        zero_dissipation_predicted_halvings=0,
        rows=rows,
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in [
                "validate_step_bound.py",
                "validate_entropy_candidate.py",
                "entropy_candidate.py",
                "finite_volume.py",
                "contract.json",
            ]
        },
    )
    (args.output / "step-bound-validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
