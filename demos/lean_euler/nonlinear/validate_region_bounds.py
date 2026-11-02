"""Test compact-region hypotheses and retain an invariant-region negative control.

Finite floating-point probes do not prove trajectory bounds over the family.
The compression control is a separate test, not a replacement physical target.
"""

import argparse
import hashlib
import json
from pathlib import Path

import entropy_candidate as ec
import finite_volume as fv
import numpy as np
from validate_entropy_candidate import conserved


def region_values(u):
    rho, pressure = u[..., 0], fv.pressure(u)
    return dict(
        min_density=float(rho.min()),
        max_density=float(rho.max()),
        min_pressure=float(pressure.min()),
        max_energy=float(u[..., 4].max()),
        minimum_region_margin=float(
            min(rho.min() - 0.25, 4 - rho.max(), 4 - u[..., 4].max(), pressure.min() - 0.25)
        ),
    )


def random_region(rng, count):
    rho, pressure = rng.uniform(0.25, 4, count), rng.uniform(0.25, 3.9, count)
    direction = rng.normal(size=(count, 3))
    direction /= np.linalg.norm(direction, axis=-1)[:, None]
    speed = np.sqrt(2 * (4 - pressure) * rng.uniform(0, 1, count) / rho)
    return conserved(rho, pressure, speed[:, None] * direction)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20261106)
    left, right = random_region(rng, 4096), random_region(rng, 4096)
    assert region_values(left)["minimum_region_margin"] >= -1e-12
    assert region_values(right)["minimum_region_margin"] >= -1e-12
    consistency_ratios = []
    for scale in [1, 1e-8]:
        partner = left + scale * (right - left)
        gap = np.linalg.norm(partner - left, axis=-1)
        for d in range(3):
            flux = ec.entropy_conservative_flux(left, partner, d)
            for state in [left, partner]:
                physical = fv.physical_flux(
                    state, fv.pressure(state), state[..., 1:4] / state[..., 0, None], d
                )
                ratio = np.linalg.norm(flux - physical, axis=-1) / gap
                consistency_ratios.append(float(ratio.max()))
                assert np.all(ratio <= 300_000_000)

    compression = np.zeros((3, 3, 3, 5))
    compression[..., 0], compression[..., 4] = 1, 4
    compression[..., 1] = np.array([1, 0, -1])[:, None, None]
    before = region_values(compression)
    assert before["minimum_region_margin"] == 0
    prepared = ec._prepare(compression)
    proposal = 0.3 / prepared.speeds.sum()
    result = ec._step_prepared(compression, 1, proposal, prepared)
    after = region_values(result.field)
    expected_increment = 1 / (2 * float(ec.logarithmic_mean(1 / 7, 1 / 8))) + 56 / 15
    assert abs(prepared.increment[1, 0, 0, 4] - expected_increment) < 1e-12
    assert result.rejected == 0 and result.entropy_margin >= 0
    assert after["max_energy"] > 4 and after["min_density"] > 0 and after["min_pressure"] > 0
    drift = float(np.max(np.abs(result.field.mean((0, 1, 2)) - compression.mean((0, 1, 2)))))
    assert drift < 1e-11

    cases = [
        (16, float(a), float(delta))
        for a in np.linspace(0.5, 1, 5)
        for delta in np.linspace(-0.05, 0.05, 5)
    ]
    cases += [(n, a, delta) for n in [32, 64] for a, delta in [(0.5, -0.05), (0.75, 0), (1, 0.05)]]
    rows = []
    for n, amplitude, delta in cases:
        field = fv.cell_averages(n, amplitude, delta)
        dx, time, steps = 2 * np.pi / n, 0.0, 0
        extrema = region_values(field)
        while time < 0.25:
            old = ec._prepare(field)
            dt = min(0.25 - time, 0.3 * dx / old.speeds.sum())
            update = ec._step_prepared(field, dx, dt, old)
            field, time, steps = update.field, time + update.dt, steps + 1
            current = region_values(field)
            for key, value in current.items():
                extrema[key] = (
                    max(extrema[key], value) if key.startswith("max_") else min(extrema[key], value)
                )
        assert extrema["minimum_region_margin"] >= 0
        row = dict(n=n, A=amplitude, delta=delta, steps=steps, final_time=time, **extrema)
        rows.append(row)
        print(json.dumps(row), flush=True)
    here = Path(__file__).resolve().parent
    report = dict(
        scope=(
            "Numerical diagnostics for proved compact-region flux consistency and an exact "
            "region-escape control. Finite trajectory samples do not prove invariance, "
            "uniform timestep/cost, continuum accuracy or optimality for the Taylor-Green family."
        ),
        random_pairs=4096,
        near_pair_scales=[1, 1e-8],
        proved_flux_bound=300_000_000,
        maximum_observed_flux_consistency_ratio=max(consistency_ratios),
        compression_control=dict(
            shape=[3, 3, 3],
            before=before,
            after=after,
            ratio=result.dt,
            rejected=result.rejected,
            center_energy_increment=expected_increment,
            entropy_margin=result.entropy_margin,
            conservation_error=drift,
        ),
        family_rows=rows,
        sources={
            name: hashlib.sha256((here / name).read_bytes()).hexdigest()
            for name in [
                "validate_region_bounds.py",
                "validate_entropy_candidate.py",
                "entropy_candidate.py",
                "finite_volume.py",
                "contract.json",
            ]
        },
    )
    (args.output / "region-validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
