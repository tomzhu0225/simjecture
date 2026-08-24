#!/usr/bin/env python3
"""Strict openPMD reader helpers for WarpX 2D XZ mesh diagnostics.

The pinned WarpX build stores native axes in the order declared by each mesh
record (normally ``["z", "x"]``), not in the physical-component order.  These
helpers normalize every returned array to the explicit convention ``(z, x)``
and derive coordinates from record metadata plus component staggering.

This file contains no scientific estimator.  Materialize or import it from a
campaign analyzer, then define the observable and acceptance rule separately.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

TARGET_AXES = ("z", "x")


def _native_axis_metadata(record: Any, component: Any) -> dict[str, Any]:
    labels = tuple(str(label).lower() for label in record.axis_labels)
    shape = tuple(int(value) for value in component.shape)
    spacing = tuple(float(value) for value in record.grid_spacing)
    offset = tuple(float(value) for value in record.grid_global_offset)
    position = tuple(float(value) for value in component.position)
    if len(labels) != 2 or set(labels) != set(TARGET_AXES):
        raise ValueError(f"expected exactly the XZ axes, got {labels!r}")
    if any(len(values) != len(labels) for values in (shape, spacing, offset, position)):
        raise ValueError("openPMD axis metadata lengths do not match")
    if any(size < 1 for size in shape) or any(
        not math.isfinite(value) for values in (spacing, offset, position) for value in values
    ):
        raise ValueError("openPMD axis metadata is non-finite or empty")
    if any(value <= 0.0 for value in spacing):
        raise ValueError("openPMD grid spacing must be positive")
    grid_unit_si = float(record.grid_unit_SI)
    component_unit_si = float(component.unit_SI)
    if not math.isfinite(grid_unit_si) or grid_unit_si <= 0.0:
        raise ValueError("openPMD grid_unit_SI must be positive and finite")
    if not math.isfinite(component_unit_si):
        raise ValueError("openPMD component unit_SI must be finite")
    return {
        "labels": labels,
        "shape": shape,
        "spacing": spacing,
        "offset": offset,
        "position": position,
        "grid_unit_si": grid_unit_si,
        "component_unit_si": component_unit_si,
    }


def normalize_xz_array(array: Any, native_axis_labels: Sequence[str]) -> np.ndarray:
    """Return a copied 2D array in the unambiguous order ``(z, x)``."""

    labels = tuple(str(label).lower() for label in native_axis_labels)
    values = np.asarray(array)
    if values.ndim != 2 or len(labels) != 2 or set(labels) != set(TARGET_AXES):
        raise ValueError("a 2D array with exactly the XZ axis labels is required")
    axes = tuple(labels.index(label) for label in TARGET_AXES)
    return np.transpose(values, axes=axes).copy()


def component_coordinates_xz(record: Any, component: Any) -> dict[str, np.ndarray]:
    """Derive SI cell/component coordinates, keyed by physical axis label."""

    meta = _native_axis_metadata(record, component)
    coordinates: dict[str, np.ndarray] = {}
    for index, label in enumerate(meta["labels"]):
        coordinate = (
            meta["offset"][index]
            + meta["spacing"][index]
            * (np.arange(meta["shape"][index], dtype=float) + meta["position"][index])
        ) * meta["grid_unit_si"]
        if coordinate.size > 1 and not np.all(np.diff(coordinate) > 0.0):
            raise ValueError(f"openPMD {label}-coordinates are not strictly increasing")
        coordinates[label] = coordinate
    return {"z": coordinates["z"], "x": coordinates["x"]}


def read_xz_components(
    path: str | Path,
    components: Mapping[str, tuple[str, str]],
) -> dict[str, Any]:
    """Read selected components from a single-iteration openPMD file.

    ``components`` maps a caller name to ``(mesh_record, component)``; for
    example ``{"Bx": ("B", "x"), "Ey": ("E", "y")}``. Arrays are copied and
    converted to SI before the series closes. Each component retains its own
    coordinates because staggered records need not be collocated.
    """

    import openpmd_api as io  # capability-only dependency

    source = Path(path)
    series = io.Series(str(source), io.Access.read_only)
    try:
        indices = list(series.iterations)
        if len(indices) != 1:
            raise ValueError(
                f"expected one openPMD iteration in {source}, found {len(indices)}"
            )
        iteration_index = indices[0]
        iteration = series.iterations[iteration_index]
        pending: dict[str, tuple[Any, Any, Any, dict[str, Any]]] = {}
        for name, selector in components.items():
            if len(selector) != 2:
                raise ValueError(f"component selector {name!r} must be (record, component)")
            record = iteration.meshes[selector[0]]
            component = record[selector[1]]
            meta = _native_axis_metadata(record, component)
            pending[name] = (record, component, component.load_chunk(), meta)
        series.flush()

        realized: dict[str, Any] = {}
        for name, (record, component, chunk, meta) in pending.items():
            native = np.asarray(chunk)
            if tuple(native.shape) != meta["shape"]:
                raise ValueError(
                    f"component {name!r} shape {native.shape} does not match metadata "
                    f"{meta['shape']}"
                )
            array_si = normalize_xz_array(native, meta["labels"]) * meta[
                "component_unit_si"
            ]
            coordinates = component_coordinates_xz(record, component)
            if array_si.shape != (coordinates["z"].size, coordinates["x"].size):
                raise ValueError(f"component {name!r} did not normalize to (z, x)")
            realized[name] = {
                "array": array_si,
                "z_m": coordinates["z"],
                "x_m": coordinates["x"],
                "native_axis_labels": meta["labels"],
                "native_position": meta["position"],
                "unit_si": meta["component_unit_si"],
            }
        return {
            "iteration": int(iteration_index),
            "time_s": float(iteration.time) * float(iteration.time_unit_SI),
            "components": realized,
        }
    finally:
        series.close()


def periodic_domain(coordinates: Sequence[float]) -> tuple[float, float]:
    """Infer the lower face and period of a uniformly spaced cell-center grid."""

    x = np.asarray(coordinates, dtype=float)
    if x.ndim != 1 or x.size < 2 or not np.all(np.isfinite(x)):
        raise ValueError("periodic coordinates must be a finite 1D array")
    differences = np.diff(x)
    if not np.all(differences > 0.0) or not np.allclose(
        differences, differences[0], rtol=1.0e-10, atol=0.0
    ):
        raise ValueError("periodic coordinates must be strictly increasing and uniform")
    spacing = float(differences[0])
    return float(x[0] - 0.5 * spacing), float(spacing * x.size)


def wrap_periodic(value: float, lower: float, period: float) -> float:
    """Map a coordinate into the half-open interval ``[lower, lower+period)``."""

    if not all(math.isfinite(item) for item in (value, lower, period)) or period <= 0.0:
        raise ValueError("periodic wrapping requires finite values and a positive period")
    return float(lower + ((value - lower) % period))


def periodic_distance(first: float, second: float, period: float) -> float:
    """Return the shortest unsigned distance on a periodic line."""

    if not math.isfinite(period) or period <= 0.0:
        raise ValueError("period must be positive and finite")
    delta = abs(float(first) - float(second)) % period
    return float(min(delta, period - delta))


def periodic_linear_zero_crossings(
    values: Sequence[float],
    coordinates: Sequence[float],
) -> np.ndarray:
    """Locate sign-changing roots, including the wrapped final/first pair.

    The wrapped pair is interpolated after adding one period to the first cell
    coordinate and only then mapped back into the physical domain. Taking its
    ordinary midpoint would incorrectly fold a boundary root onto the center.
    """

    y = np.asarray(values, dtype=float)
    x = np.asarray(coordinates, dtype=float)
    if y.ndim != 1 or y.shape != x.shape or not np.all(np.isfinite(y)):
        raise ValueError("periodic crossing inputs must be equal finite 1D arrays")
    lower, period = periodic_domain(x)
    roots: list[float] = []
    for index in range(x.size):
        following = (index + 1) % x.size
        y0, y1 = float(y[index]), float(y[following])
        x0 = float(x[index])
        x1 = float(x[following]) + (period if following == 0 else 0.0)
        if y0 == 0.0:
            root = x0
        elif y1 == 0.0:
            root = x1
        elif y0 * y1 < 0.0:
            root = x0 - y0 * (x1 - x0) / (y1 - y0)
        else:
            continue
        wrapped = wrap_periodic(root, lower, period)
        if not any(periodic_distance(wrapped, old, period) <= 1.0e-12 * period for old in roots):
            roots.append(wrapped)
    return np.asarray(sorted(roots), dtype=float)


def periodic_linear_interpolate(
    values: Sequence[float],
    coordinates: Sequence[float],
    query: float,
) -> float:
    """Linearly interpolate cell-centered data without a boundary discontinuity."""

    y = np.asarray(values, dtype=float)
    x = np.asarray(coordinates, dtype=float)
    if y.ndim != 1 or y.shape != x.shape or not np.all(np.isfinite(y)):
        raise ValueError("periodic interpolation inputs must be equal finite 1D arrays")
    lower, period = periodic_domain(x)
    q = wrap_periodic(float(query), lower, period)
    extended_x = np.concatenate(([x[-1] - period], x, [x[0] + period]))
    extended_y = np.concatenate(([y[-1]], y, [y[0]]))
    return float(np.interp(q, extended_x, extended_y))

