"""Conservative gamma=2 Euler candidate with global directional Rusanov speeds.

This module evolves unknown nonlinear dynamics. The formal admissibility proof
uses exact reals; continuum accuracy and floating-point refinement remain open.
"""

from dataclasses import dataclass

import numpy as np


def pressure(u):
    return u[..., 4] - np.sum(u[..., 1:4] ** 2, axis=-1) / (2 * u[..., 0])


def cell_averages(n, amplitude, delta):
    """Analytic cell averages of the trigonometric initial conservative fields."""
    if n < 1 or not 0.5 <= amplitude <= 1 or not -0.05 <= delta <= 0.05:
        raise ValueError("Use the fixed problem family and a positive grid size")
    x = (np.arange(n) + 0.5) * (2 * np.pi / n)
    s1 = np.sin(x) * np.sinc(1 / n)
    c1 = np.cos(x) * np.sinc(1 / n)
    s2 = np.sin(2 * x) * np.sinc(2 / n)
    c2 = np.cos(2 * x) * np.sinc(2 / n)
    s3 = np.sin(3 * x) * np.sinc(3 / n)
    ss, cc, sc = (1 - c2) / 2, (1 + c2) / 2, s2 / 2
    sss, scc = (3 * s1 - s3) / 4, (s1 + s3) / 4

    def tensor(a, b, c):
        return a[:, None, None] * b[None, :, None] * c[None, None, :]

    u = np.empty((n, n, n, 5))
    u[..., 0] = 1 + delta * tensor(s1, s1, s1)
    u[..., 1] = amplitude * (tensor(s1, c1, c1) + delta * tensor(ss, sc, sc))
    u[..., 2] = -amplitude * (tensor(c1, s1, c1) + delta * tensor(sc, ss, sc))
    u[..., 3] = 0
    pbar = 1 + amplitude**2 / 16 * (c2[:, None, None] + c2[None, :, None]) * (c2[None, None, :] + 2)
    u[..., 4] = pbar + amplitude**2 / 2 * (
        tensor(ss, cc, cc)
        + tensor(cc, ss, cc)
        + delta * (tensor(sss, scc, scc) + tensor(scc, sss, scc))
    )
    return u


def primitives(u):
    p = pressure(u)
    if not np.all(np.isfinite(u)) or np.min(u[..., 0]) <= 0 or np.min(p) <= 0:
        raise ValueError("State is not admissible")
    v = u[..., 1:4] / u[..., 0, None]
    sound = np.sqrt(2 * p / u[..., 0])
    speed = np.max(np.abs(v) + sound[..., None], axis=(0, 1, 2))
    return p, v, speed


def physical_flux(u, p, v, d):
    result = u * v[..., d, None]
    result[..., d + 1] += p
    result[..., 4] += p * v[..., d]
    return result


def _step_prepared(u, ratio, prepared):
    """Internal kernel: prepared quantities must come from this same state."""
    p, v, speeds = prepared
    if ratio < 0 or ratio * speeds.sum() > 1 + 1e-14:
        raise ValueError("CFL condition violated")
    result = u.copy()
    for d in range(3):
        f = physical_flux(u, p, v, d)
        face = 0.5 * (f + np.roll(f, -1, axis=d) - speeds[d] * (np.roll(u, -1, axis=d) - u))
        result -= ratio * (face - np.roll(face, 1, axis=d))
    return result


def step(u, ratio):
    """One conservative update with fresh quantities; ratio = dt/dx."""
    return _step_prepared(u, ratio, primitives(u))


@dataclass
class Result:
    field: np.ndarray
    time: float
    steps: int
    cell_updates: int


def solve(n, amplitude, delta, final_time=0.25, cfl=0.3):
    if not 0 < cfl <= 1 or final_time <= 0:
        raise ValueError("Require 0 < CFL <= 1 and positive final time")
    u = cell_averages(n, amplitude, delta)
    t, count, dx = 0.0, 0, 2 * np.pi / n
    while t < final_time:
        prepared = primitives(u)
        dt = min(final_time - t, cfl * dx / prepared[2].sum())
        if dt <= 0 or t + dt == t:
            raise ArithmeticError("Timestep cannot advance floating-point time")
        u = _step_prepared(u, dt / dx, prepared)
        t += dt
        count += 1
    primitives(u)
    return Result(u, t, count, count * n**3)
