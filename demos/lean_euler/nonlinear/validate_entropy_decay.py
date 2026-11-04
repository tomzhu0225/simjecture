"""Independent periodic-grid identities and accumulated entropy-loss diagnostics.

The exact-real theorem is conditional on the old states remaining in the region.
These finite runs do not establish continuum accuracy or a work lower bound.
"""

import argparse
import hashlib
import json
from pathlib import Path

import entropy_candidate as ec
import finite_volume as fv
import numpy as np
from validate_entropy_candidate import complex_step_gradient
from validate_region_bounds import random_region, region_values


def grid_quantities(u):
    mean = u.mean((0, 1, 2))
    centered = u - mean
    variance = float(np.mean(np.sum(centered**2, axis=-1)))
    edges = sum(
        float(np.mean(np.sum((np.roll(u, -1, axis=d) - u) ** 2, axis=-1))) for d in range(3)
    )
    entropy = float(ec.entropy(u).mean())
    excess = entropy - float(ec.entropy(mean))
    return mean, variance, edges, entropy, excess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20261107)
    pair_errors = []
    poincare_ratios = []
    for n in [1, 2, 3, 4]:
        field = rng.normal(size=(n, n, n, 5))
        values = field.reshape(-1, 5)
        pair_sum = float(np.sum((values[:, None, :] - values[None, :, :]) ** 2))
        variance_sum = float(np.sum((values - values.mean(axis=0)) ** 2))
        predicted = 2 * n**3 * variance_sum
        pair_errors.append(abs(pair_sum - predicted) / (1 + abs(predicted)))
        edges = sum(float(np.sum((np.roll(field, -1, axis=d) - field) ** 2)) for d in range(3))
        assert variance_sum <= 1.5 * n**2 * edges + 1e-12
        if edges > 0:
            poincare_ratios.append(variance_sum / (n**2 * edges))
    assert max(pair_errors) < 2e-14

    constant = np.broadcast_to(np.array([1.0, 0.2, -0.3, 0.4, 1.5]), (4, 4, 4, 5)).copy()
    _, constant_variance, constant_edges, _, constant_excess = grid_quantities(constant)
    assert constant_edges == 0 and constant_variance < 1e-28 and abs(constant_excess) < 1e-14

    left, right = random_region(rng, 4096), random_region(rng, 4096)
    max_gradient = max(float(np.abs(complex_step_gradient(u)).max()) for u in [left, right])
    point_error = np.sum(np.abs(right - left), axis=-1)
    entropy_difference = np.abs(ec.entropy(right) - ec.entropy(left))
    max_point_ratio = float(np.max(entropy_difference / point_error))
    weights = rng.uniform(0.01, 1, len(left))
    weights /= weights.sum()
    component_errors = np.sum(weights[:, None] * np.abs(right - left), axis=0)
    entropy_gap = float(abs(np.sum(weights * (ec.entropy(right) - ec.entropy(left)))))
    assert max_gradient <= 32 and max_point_ratio <= 32
    assert entropy_gap <= 32 * component_errors.sum()
    assert entropy_gap / 160 <= component_errors.max()

    rows = []
    for amplitude, delta in [(0.5, -0.05), (0.75, 0), (1.0, 0.05)]:
        for n in [16, 32, 64]:
            field = fv.cell_averages(n, amplitude, delta)
            initial_mean, _, _, initial_entropy, initial_excess = grid_quantities(field)
            dx, time, steps, ratio_sum = 2 * np.pi / n, 0.0, 0, 0.0
            max_poincare, max_excess_to_edges = 0.0, 0.0
            min_dissipation_to_edges = np.inf
            min_step_loss_factor = np.inf
            min_region_margin = np.inf
            max_mean_drift = 0.0
            while time < 0.25:
                min_region_margin = min(
                    min_region_margin, region_values(field)["minimum_region_margin"]
                )
                prepared = ec._prepare(field)
                _, variance, edges, before, excess = grid_quantities(field)
                assert excess >= -1e-12
                assert variance <= 1.5 * n**2 * edges + 1e-12
                assert excess <= 50_000 * variance + 1e-12
                assert prepared.dissipation >= edges / 100_000
                assert prepared.speeds.min() >= 0.25
                dt = min(0.25 - time, 0.3 * dx / prepared.speeds.sum())
                update = ec._step_prepared(field, dx, dt, prepared)
                ratio = update.dt / dx
                drop = before - update.entropy_after
                assert ratio * excess <= 15_000_000_000 * n**2 * drop
                if edges > 0:
                    max_poincare = max(max_poincare, variance / (n**2 * edges))
                    max_excess_to_edges = max(max_excess_to_edges, excess / (n**2 * edges))
                    min_dissipation_to_edges = min(
                        min_dissipation_to_edges, prepared.dissipation / edges
                    )
                if excess > 0:
                    min_step_loss_factor = min(min_step_loss_factor, n**2 * drop / (ratio * excess))
                field, time = update.field, time + update.dt
                ratio_sum, steps = ratio_sum + ratio, steps + 1
                max_mean_drift = max(
                    max_mean_drift, float(np.max(np.abs(field.mean((0, 1, 2)) - initial_mean)))
                )
            _, _, _, final_entropy, final_excess = grid_quantities(field)
            loss = initial_entropy - final_entropy
            lower_bound = time * final_excess / (30_000_000_000 * np.pi * n)
            assert min_region_margin >= 0 and max_mean_drift < 1e-11
            assert abs(dx * ratio_sum - time) < 1e-13
            assert loss >= lower_bound > 0
            row = dict(
                n=n,
                A=amplitude,
                delta=delta,
                final_time=time,
                steps=steps,
                ratio_sum=ratio_sum,
                mean_conservation_error=max_mean_drift,
                min_region_margin=min_region_margin,
                initial_excess=initial_excess,
                final_excess=final_excess,
                entropy_loss=loss,
                conditional_loss_lower_bound=lower_bound,
                observed_loss_over_bound=loss / lower_bound,
                max_variance_over_n2_edges=max_poincare,
                max_excess_over_n2_edges=max_excess_to_edges,
                min_dissipation_over_edges=min_dissipation_to_edges,
                min_n2_loss_over_ratio_excess=min_step_loss_factor,
            )
            rows.append(row)
            print(json.dumps(row), flush=True)
    here = Path(__file__).resolve().parent
    report = dict(
        scope=(
            "Float checks of a periodic Poincare estimate and a conditional accumulated "
            "entropy-loss theorem for the actual EC+LF trace. Region membership is only "
            "sampled here. Continuous Euler entropy conservation, reconstruction/error "
            "bridges and total-work optimality remain unproved."
        ),
        pair_variance_max_scaled_error=max(pair_errors),
        random_grid_max_poincare_ratio=max(poincare_ratios),
        constant_state_entropy_excess=constant_excess,
        entropy_error_checks=dict(
            random_pairs=len(left),
            max_independent_gradient_component=max_gradient,
            max_pointwise_entropy_over_component_l1=max_point_ratio,
            weighted_entropy_gap=entropy_gap,
            weighted_max_component_l1=float(component_errors.max()),
            entropy_gap_lower_bound=entropy_gap / 160,
        ),
        rows=rows,
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in [
                "validate_entropy_decay.py",
                "validate_region_bounds.py",
                "validate_entropy_candidate.py",
                "entropy_candidate.py",
                "finite_volume.py",
                "contract.json",
            ]
        },
    )
    (args.output / "entropy-decay-validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
