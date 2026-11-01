"""Characteristic reconstruction for the frozen affine-shear Euler family.

The Lean theorem uses exact real arithmetic. This NumPy implementation is a
local floating-point demonstration, not an extracted or verified executable.
"""

from collections.abc import Callable
from dataclasses import dataclass
from math import ceil

import numpy as np

Array = np.ndarray


def flow(t: float, a: Array) -> Array:
    x = np.empty_like(a, dtype=float)
    x[..., 0] = a[..., 0] + t * a[..., 1]
    x[..., 1] = a[..., 1] + t * a[..., 2]
    x[..., 2] = a[..., 2] + t
    return x


def inverse_flow(t: float, x: Array) -> Array:
    a = np.empty_like(x, dtype=float)
    a[..., 0] = x[..., 0] - t * x[..., 1] + t * t * x[..., 2] - t**3
    a[..., 1] = x[..., 1] - t * x[..., 2] + t * t
    a[..., 2] = x[..., 2] - t
    return a


def velocity(t: float, x: Array) -> Array:
    v = np.empty_like(x, dtype=float)
    v[..., 0] = x[..., 1] - t * x[..., 2] + t * t
    v[..., 1] = x[..., 2] - t
    v[..., 2] = 1.0
    return v


def conserved(rho: Array, v: Array) -> Array:
    u = np.empty((*rho.shape, 5))
    u[..., 0] = rho
    u[..., 1:4] = rho[..., None] * v
    u[..., 4] = 1.0 + 0.5 * rho * np.sum(v * v, axis=-1)
    return u


def exact_state(rho0: Callable[[Array], Array], t: float, x: Array) -> Array:
    return conserved(rho0(inverse_flow(t, x)), velocity(t, x))


def euler_flux(u: Array, d: int) -> Array:
    rho, m, energy = u[..., 0], u[..., 1:4], u[..., 4]
    p = energy - 0.5 * np.sum(m * m, axis=-1) / rho
    vd = m[..., d] / rho
    f = np.empty_like(u)
    f[..., 0] = m[..., d]
    f[..., 1:4] = m * vd[..., None]
    f[..., d + 1] += p
    f[..., 4] = (energy + p) * vd
    return f


def modeled_work(n: int) -> int:
    """Lean RAM model including tolerance selection; not NumPy FLOPs."""
    return 19 * n**3 + 4 * n**2 + 4 * n + 12


@dataclass
class Reconstruction:
    data: Array
    lipschitz: float
    tolerance: float
    query_count: int

    @property
    def n(self) -> int:
        return self.data.shape[0]

    @property
    def exact_real_error_bound(self) -> float:
        return 3 * self.lipschitz / (4 * self.n)

    def evaluate(self, t: float, x: Array) -> Array:
        a = inverse_flow(t, np.asarray(x, dtype=float))
        # The theorem covers the moving cube. A small tolerance only absorbs
        # floating-point inversion error at its boundary.
        if np.any(a < -1e-12) or np.any(a > 1 + 1e-12):
            raise ValueError("Evaluation point is outside the moving material cube")
        i = np.minimum(np.floor(self.n * np.clip(a, 0, 1)).astype(np.int64), self.n - 1)
        rho = self.data[i[..., 0], i[..., 1], i[..., 2]]
        return conserved(rho, velocity(t, np.asarray(x, dtype=float)))


def solve(rho0: Callable[[Array], Array], lipschitz: float, tolerance: float) -> Reconstruction:
    if not np.isfinite(lipschitz) or lipschitz <= 0 or not np.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Positive finite Lipschitz and tolerance parameters are required")
    n = max(1, ceil(3 * lipschitz / (4 * tolerance)))
    c = (np.arange(n, dtype=float) + 0.5) / n
    coordinates = np.stack(np.meshgrid(c, c, c, indexing="ij"), axis=-1)
    data = np.asarray(rho0(coordinates), dtype=float)
    if data.shape != (n, n, n) or not np.all(np.isfinite(data)):
        raise ValueError("Density oracle must return one finite value per point")
    if np.min(data) < 1 or np.max(data) > 2:
        raise ValueError("Sampled density is outside the frozen [1,2] class")
    # Samples cannot establish the global C1/Lipschitz premise. The caller must
    # supply a valid class member; the demonstration uses an analytic one.
    return Reconstruction(data.copy(), lipschitz, tolerance, n**3)


def demonstration_density(a: Array) -> Array:
    # 1.4 <= rho <= 1.6. Sum of absolute partial derivatives <= 0.6*pi < 2,
    # hence Lipschitz constant <= 2 for the coordinate maximum norm.
    return 1.5 + 0.1 * np.prod(np.sin(2 * np.pi * a), axis=-1)
