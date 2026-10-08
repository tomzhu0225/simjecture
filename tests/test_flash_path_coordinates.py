"""Independent analytic controls for the post-run FLASH coordinate diagnosis."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture(params=["demos/resistive_mhd_island_coalescence", "skills/flash-mhd/examples"])
def paths(request):
    spec = importlib.util.spec_from_file_location(
        "coordinate_paths", Path(__file__).parents[1] / request.param / "coordinate_paths.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("nx,ny,y_origin", [(96, 96, -0.5), (48, 64, -0.4), (48, 64, 1.0)])
def test_asymmetric_field_recovers_same_physical_row_average(paths, nx, ny, y_origin):
    # Small A at the middle of the first two grids makes a half-cell error
    # material even when a loose test on an O(1) potential would overlook it.
    dx, dy = 1.6 / nx, (1.0 if ny == 96 else 0.8) / ny
    x = -0.7 + (np.arange(nx) + 0.5) * dx
    y = y_origin + (np.arange(ny) + 0.5) * dy
    xx, yy = np.meshgrid(x, y)
    observed = paths.midline_paths(2 * xx * yy, -(yy**2 + 0.005), dx=dx, dy=dy)
    coefficient = np.mean(y[ny // 2 - 1 : ny // 2 + 1] ** 2) + 0.005
    expected = (x - x[0]) * coefficient
    for key in ["from_bx", "from_by"]:
        np.testing.assert_allclose(observed[key] - observed[key][0], expected, rtol=0, atol=2e-13)
    assert observed["relative_mismatch"] < 1e-10


def test_constant_potential_has_no_relative_scale(paths):
    zeros = np.zeros((8, 8))
    result = paths.midline_paths(zeros, zeros, dx=0.1, dy=0.2)
    assert result["maximum_absolute_difference"] == 0
    assert result["relative_mismatch"] is None
