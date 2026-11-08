"""Transparent NumPy Euler reference and exact rational witness search."""

import json
import platform
import time
from fractions import Fraction as Q
from pathlib import Path

import numpy as np


def pressure(u, gamma=2):
    return (gamma - 1) * (u[..., 4] - np.sum(u[..., 1:4] ** 2, axis=-1) / (2 * u[..., 0]))


def flux(u, axis, gamma=2):
    p = pressure(u, gamma)
    v = u[..., axis + 1] / u[..., 0]
    f = u * v[..., None]
    f[..., axis + 1] += p
    f[..., 4] += p * v
    speed = abs(v) + np.sqrt(gamma * p / u[..., 0])
    return f, speed


def step(u, dt, dx):
    new = u.copy()
    for axis in range(3):
        f, speed = flux(u, axis)
        right = np.roll(u, -1, axis=axis)
        a = np.maximum(speed, np.roll(speed, -1, axis=axis))
        face = (f + np.roll(f, -1, axis=axis) - a[..., None] * (right - u)) / 2
        new -= dt / dx * (face - np.roll(face, 1, axis=axis))
    return new


def smooth_case(n, final_time=0.1):
    xyz = np.meshgrid(*([(np.arange(n) + 0.5) / n] * 3), indexing="ij")
    phase = sum(xyz)
    velocity = np.array([0.5, 0.2, -0.1])
    # Exact volume average of a sinusoidal contact wave over each Cartesian cell.
    amplitude = 0.1 * np.sinc(1 / n) ** 3
    rho = 1 + amplitude * np.sin(2 * np.pi * phase)
    u = np.empty((n, n, n, 5))
    u[..., 0] = rho
    u[..., 1:4] = rho[..., None] * velocity
    u[..., 4] = 1 + 0.5 * rho * np.sum(velocity**2)
    initial = u.sum(axis=(0, 1, 2)) / n**3
    t = 0
    count = 0
    started = time.perf_counter()
    while t < final_time:
        dt = min(final_time - t, 0.3 / (n * sum(flux(u, a)[1].max() for a in range(3))))
        u = step(u, dt, 1 / n)
        t += dt
        count += 1
    exact = 1 + amplitude * np.sin(2 * np.pi * (phase - sum(velocity) * t))
    return dict(
        n=n,
        steps=count,
        time=t,
        wall_seconds=time.perf_counter() - started,
        density_l1=float(np.mean(abs(u[..., 0] - exact))),
        min_density=float(u[..., 0].min()),
        min_pressure=float(pressure(u).min()),
        conservation_drift=(u.sum(axis=(0, 1, 2)) / n**3 - initial).tolist(),
    )


def exact_flux(u):
    rho, mom, energy = u
    p = energy - mom * mom / (2 * rho)  # gamma = 2
    return (mom, mom * mom / rho + p, (energy + p) * mom / rho)


def rational_step(states, ratio):
    # a = 1 is EXACT for these zero-velocity initial states: gamma*p/rho = 1.
    faces = []
    for left, right in zip(states, states[1:] + states[:1], strict=True):
        faces.append(
            tuple(
                (f + g - (right_value - left_value)) / 2
                for f, g, left_value, right_value in zip(
                    exact_flux(left), exact_flux(right), left, right, strict=True
                )
            )
        )
    return [
        tuple(x - ratio * (f - g) for x, f, g in zip(u, faces[i], faces[i - 1], strict=True))
        for i, u in enumerate(states)
    ]


def counterexample():
    attempts = []
    for peak in [Q(2), Q(4), Q(8)]:
        states = [(rho, Q(0), rho / 2) for rho in [Q(1), Q(1), peak]]
        for ratio in [Q(1, 4), Q(1, 2), Q(1), Q(2), Q(4)]:
            after = rational_step(states, ratio)
            attempts.append(
                dict(peak=str(peak), dt_dx=str(ratio), min_density=str(min(s[0] for s in after)))
            )
            if any(s[0] < 0 for s in after):
                assert all(s[0] > 0 and s[2] > 0 and 2 * s[2] / s[0] == 1 for s in states)
                assert all(sum(s[k] for s in states) == sum(s[k] for s in after) for k in range(3))
                return dict(
                    gamma="2",
                    wave_speed="1",
                    dt_dx=str(ratio),
                    before=[[str(x) for x in s] for s in states],
                    after=[[str(x) for x in s] for s in after],
                    attempts=attempts,
                    scope="1D periodic three-cell compressible Euler Rusanov step; exact rationals",
                )
    raise AssertionError("No witness in the declared finite search")


def main():
    cases = [smooth_case(n) for n in [8, 16, 32]]
    constant = np.zeros((3, 4, 5, 5))
    constant[..., 0] = 1
    constant[..., 4] = 1
    assert np.array_equal(step(constant, 0.01, 0.2), constant)
    assert all(c["min_density"] > 0 and c["min_pressure"] > 0 for c in cases)
    assert all(max(abs(x) for x in c["conservation_drift"]) < 1e-11 for c in cases)
    assert cases[2]["density_l1"] < cases[1]["density_l1"] < cases[0]["density_l1"]
    witness = counterexample()
    # Broken two-cell update: the right cell receives a different shared flux.
    broken = dict(
        initial=["1", "1"], transfers=["1/4", "1/2"], after=["3/4", "3/2"], total_change="1/4"
    )
    assert Q(3, 4) + Q(3, 2) - 2 == Q(1, 4)
    result = dict(
        scope="Exploratory reference calculations, not a performance or optimality claim",
        numpy=np.__version__,
        python=platform.python_version(),
        host=platform.platform(),
        smooth_periodic_3d=cases,
        constant_state_preserved=True,
        exact_counterexample=witness,
        broken_shared_flux=broken,
    )
    Path("numerics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
