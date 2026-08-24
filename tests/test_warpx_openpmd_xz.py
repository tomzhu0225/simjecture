from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/warpx/examples/openpmd_xz_reader.py"
)


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("warpx_openpmd_xz_reader", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Record:
    axis_labels = ["x", "z"]
    grid_spacing = [2.0, 3.0]
    grid_global_offset = [-4.0, -6.0]
    grid_unit_SI = 10.0


class _Component:
    shape = [3, 2]
    position = [0.25, 0.5]
    unit_SI = 2.0


def test_normalizes_native_axes_and_derives_staggered_coordinates() -> None:
    reader = _module()
    native = np.arange(6).reshape(3, 2)
    normalized = reader.normalize_xz_array(native, ["x", "z"])
    assert normalized.shape == (2, 3)
    assert np.array_equal(normalized, native.T)

    coordinates = reader.component_coordinates_xz(_Record(), _Component())
    assert np.allclose(coordinates["x"], [-35.0, -15.0, 5.0])
    assert np.allclose(coordinates["z"], [-45.0, -15.0])


def test_periodic_crossing_does_not_fold_boundary_onto_center() -> None:
    reader = _module()
    x = np.asarray([-1.5, -0.5, 0.5, 1.5])
    values = np.asarray([1.0, 1.0, -1.0, -1.0])
    roots = reader.periodic_linear_zero_crossings(values, x)
    assert np.allclose(roots, [-2.0, 0.0])
    assert reader.periodic_distance(roots[0], 2.0, 4.0) == pytest.approx(0.0)


def test_periodic_interpolation_uses_wrapped_neighbor_cells() -> None:
    reader = _module()
    x = np.asarray([-1.5, -0.5, 0.5, 1.5])
    values = np.asarray([2.0, 0.0, 0.0, 6.0])
    assert reader.periodic_linear_interpolate(values, x, -2.0) == pytest.approx(4.0)
    assert reader.periodic_linear_interpolate(values, x, 2.0) == pytest.approx(4.0)


def test_rejects_ambiguous_or_nonuniform_axes() -> None:
    reader = _module()
    with pytest.raises(ValueError, match="XZ axis labels"):
        reader.normalize_xz_array(np.zeros((2, 2)), ["x", "y"])
    with pytest.raises(ValueError, match="uniform"):
        reader.periodic_domain([0.0, 1.0, 3.0])

