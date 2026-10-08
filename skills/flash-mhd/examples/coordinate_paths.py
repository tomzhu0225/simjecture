"""Consistent flux-potential paths on a uniform Cartesian, cell-center mesh.

The returned curves represent the average of A_z on the two central cell-center
rows. They are not an exact continuum evaluation at y=0. Gauge and quadrature
origins are the lower-left cell center for both paths. Supports only 2D arrays.
"""

from __future__ import annotations

import numpy as np


def midline_paths(bx, by, *, dx, dy):
    bx, by = np.asarray(bx, dtype=float), np.asarray(by, dtype=float)
    if bx.ndim != 2 or bx.shape != by.shape:
        raise ValueError("Magnetic components need matching 2D (y,x) arrays")
    ny, nx = bx.shape
    if ny < 4 or ny % 2 or nx < 2:
        raise ValueError("Need an even number of rows >=4 and at least two columns")
    if not (
        np.isfinite(bx).all()
        and np.isfinite(by).all()
        and np.isfinite([dx, dy]).all()
        and dx > 0
        and dy > 0
    ):
        raise ValueError("Require finite fields and positive finite cell spacing")
    mid = ny // 2
    bottom = -np.r_[0.0, np.cumsum(0.5 * (by[0, :-1] + by[0, 1:]) * dx)]
    # Integrate from the first cell center to the lower central cell center,
    # then average the potentials on the two central rows. Do not integrate
    # an extra half-cell at the bottom while keeping a cell-center gauge.
    integral = dy * (0.5 * (bx[0] + bx[mid - 1]) + bx[1 : mid - 1].sum(axis=0))
    vertical = bottom + integral + 0.25 * dy * (bx[mid - 1] + bx[mid])
    by_middle = 0.5 * (by[mid - 1] + by[mid])
    horizontal = vertical[0] - np.r_[0.0, np.cumsum(0.5 * (by_middle[:-1] + by_middle[1:]) * dx)]
    absolute = float(np.max(np.abs(vertical - horizontal)))
    scale = float(max(np.ptp(vertical), np.ptp(horizontal)))
    return {
        "from_bx": vertical,
        "from_by": horizontal,
        "maximum_absolute_difference": absolute,
        "potential_range": scale,
        "relative_mismatch": absolute / scale if scale > 0 else None,
    }
