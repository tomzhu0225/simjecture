"""Continuous periodic trilinear reconstruction of cell-centered conserved data.

Each query uses eight neighboring cells, including periodic seam cells. The
exact-real hat reconstruction is formalized in HatReconstruction.lean; this
NumPy implementation is not a verified floating-point extraction.
"""

from itertools import product

import numpy as np


def reconstruct(field, points, side=2 * np.pi):
    """Return five conserved components at points with final dimension three."""
    field, points = np.asarray(field, dtype=float), np.asarray(points, dtype=float)
    if field.ndim != 4 or field.shape[-1] != 5:
        raise ValueError("Expected a cubic n by n by n grid of five conserved fields")
    n = field.shape[0]
    if n < 1 or field.shape[:3] != (n, n, n):
        raise ValueError("Expected a nonempty cubic grid")
    if points.ndim < 1 or points.shape[-1] != 3 or not np.all(np.isfinite(points)):
        raise ValueError("Expected finite query points with final dimension three")
    if not np.isfinite(side) or side <= 0:
        raise ValueError("Expected a positive finite domain side")
    scaled = np.remainder(points, side) * (n / side) - 0.5
    lower = np.floor(scaled).astype(np.int64)
    fraction = scaled - lower
    result = np.zeros((*points.shape[:-1], 5))
    for corner in product((0, 1), repeat=3):
        corner = np.asarray(corner)
        index = (lower + corner) % n
        weight = np.prod(np.where(corner, fraction, 1 - fraction), axis=-1)
        result += weight[..., None] * field[index[..., 0], index[..., 1], index[..., 2]]
    return result
