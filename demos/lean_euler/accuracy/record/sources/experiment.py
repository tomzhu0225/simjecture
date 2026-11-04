"""Stage 1: preserve the fixed 3D Rusanov update while caching thermodynamics."""

import argparse
import hashlib
import importlib.util
import json
import platform
import random
import statistics
import time
from pathlib import Path

import numpy as np

# The original reference is an explicit lab input, frozen alongside this source.
spec = importlib.util.spec_from_file_location("reference_euler", Path("euler.py"))
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def cached_step(u, dt, dx):
    p = reference.pressure(u)
    sound = np.sqrt(2 * p / u[..., 0])
    new = u.copy()
    for axis in range(3):
        v = u[..., axis + 1] / u[..., 0]
        f = u * v[..., None]
        f[..., axis + 1] += p
        f[..., 4] += p * v
        speed = abs(v) + sound
        a = np.maximum(speed, np.roll(speed, -1, axis=axis))
        right = np.roll(u, -1, axis=axis)
        face = (f + np.roll(f, -1, axis=axis) - a[..., None] * (right - u)) / 2
        new -= dt / dx * (face - np.roll(face, 1, axis=axis))
    return new


def state(n, seed, kind):
    rng = np.random.default_rng(seed)
    xyz = np.meshgrid(*([(np.arange(n) + 0.5) / n] * 3), indexing="ij")
    if kind == "random":
        rho = rng.uniform(0.5, 2, (n, n, n))
        velocity = rng.uniform(-1, 1, (n, n, n, 3))
        p = rng.uniform(0.5, 2, (n, n, n))
    elif kind == "blast":
        rho = np.ones((n, n, n))
        velocity = np.zeros((n, n, n, 3))
        radius2 = sum((x - 0.5) ** 2 for x in xyz)
        p = np.where(radius2 < 0.15**2, 10.0, 0.1)
    elif kind == "coupled":
        x, y, z = xyz
        rho = 1 + 0.1 * np.sin(2 * np.pi * x) * np.cos(2 * np.pi * y) * np.sin(2 * np.pi * z)
        velocity = np.stack(
            [0.3 * np.sin(2 * np.pi * y), 0.2 * np.sin(2 * np.pi * z), 0.1 * np.sin(2 * np.pi * x)],
            axis=-1,
        )
        p = 1 + 0.1 * np.cos(2 * np.pi * (x + y + z))
    else:
        raise ValueError(kind)
    u = np.empty((n, n, n, 5))
    u[..., 0] = rho
    u[..., 1:4] = rho[..., None] * velocity
    u[..., 4] = p + 0.5 * rho * np.sum(velocity**2, axis=-1)
    return u


def timestep(u, dx):
    return 0.2 / (sum(reference.flux(u, a)[1].max() for a in range(3)) / dx)


def check_case(n, seed, kind, steps):
    initial = state(n, seed, kind)
    baseline = initial.copy()
    candidate = initial.copy()
    elapsed = 0
    bitwise_equal = True
    max_difference = 0
    initial_total = initial.sum(axis=(0, 1, 2)) / n**3
    for _ in range(steps):
        dt = timestep(baseline, 1 / n)
        baseline = reference.step(baseline, dt, 1 / n)
        candidate = cached_step(candidate, dt, 1 / n)
        elapsed += dt
        bitwise_equal &= np.array_equal(baseline, candidate)
        max_difference = max(max_difference, float(np.max(abs(baseline - candidate))))
        assert np.all(np.isfinite(candidate))
        assert candidate[..., 0].min() > 0 and reference.pressure(candidate).min() > 0
    drift = candidate.sum(axis=(0, 1, 2)) / n**3 - initial_total
    assert max_difference < 1e-12
    assert np.max(abs(drift)) < 1e-11
    return dict(
        n=n,
        kind=kind,
        seed=seed,
        steps=steps,
        time=elapsed,
        bitwise_equal=bool(bitwise_equal),
        max_difference=max_difference,
        min_density=float(candidate[..., 0].min()),
        min_pressure=float(reference.pressure(candidate).min()),
        conserved_total_drift=drift.tolist(),
    )


def timing(n, repeats=11):
    u = state(n, 20261101, "coupled")
    dt = timestep(u, 1 / n)
    kernels = {"reference": reference.step, "cached": cached_step}
    samples = {name: [] for name in kernels}
    for kernel in kernels.values():
        kernel(u, dt, 1 / n)
    order_rng = random.Random(n)
    for _ in range(repeats):
        names = list(kernels)
        order_rng.shuffle(names)
        for name in names:
            start = time.perf_counter()
            result = kernels[name](u, dt, 1 / n)
            samples[name].append(time.perf_counter() - start)
            assert result.shape == u.shape
    medians = {name: statistics.median(values) for name, values in samples.items()}
    return dict(
        n=n,
        cells=n**3,
        trials_seconds=samples,
        median_seconds=medians,
        reference_over_cached=medians["reference"] / medians["cached"],
        pressure_cell_evaluations={"reference": 3 * n**3, "cached": n**3},
        sound_speed_cell_evaluations={"reference": 3 * n**3, "cached": n**3},
        timestep_selection_timed=False,
        timing_scope="entire one-step kernel including cache creation and output allocation",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="optimization.json")
    args = parser.parse_args()
    checks = [
        check_case(n, seed, kind, steps)
        for n, seed, kind, steps in [
            (8, 1, "random", 8),
            (12, 2, "random", 8),
            (16, 3, "coupled", 20),
            (24, 4, "blast", 20),
        ]
    ]
    results = dict(
        stage="1: fixed-discretization implementation experiment; optimality unproved",
        contract=dict(
            equations="3D ideal-gas compressible Euler, gamma=2",
            grid="uniform periodic Cartesian cells; five conservative variables",
            scheme="first-order shared-face Rusanov plus forward Euler",
            allowed_change="reuse old-state pressure and sound speed across axes",
            required_output="same discrete update for same inputs and timestep",
            cost="one-step CPU wall time, plus instrumentable thermodynamic evaluations",
        ),
        equivalence_checks=checks,
        timings=[timing(n) for n in [16, 32, 48, 64]],
        environment=dict(
            python=platform.python_version(), numpy=np.__version__, platform=platform.platform()
        ),
        source_sha256={
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ["experiment.py", "euler.py"]
        },
        claim_status=dict(
            tested_update_equivalence="empirical",
            thermodynamic_reuse="by code inspection",
            general_positivity="open",
            pde_accuracy="not assessed in nonlinear cases",
            implementation_optimality="open",
            solver_optimality_at_fixed_error="open",
        ),
        limitations=[
            "Four exploratory nonlinear 3D trajectories are not a convergence proof",
            "The blast check tests execution and admissibility, not a validated shock solution",
            "A speedup over one baseline is not an optimality lower bound",
            "Timing excludes timestep selection and is not time-to-solution at fixed error",
        ],
    )
    Path(args.output).write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({"checks": checks, "timings": results["timings"]}, indent=2))


if __name__ == "__main__":
    main()
