from __future__ import annotations

import numpy as np
import pytest

from conjecture_solver.warpx_analysis import (
    fit_windowed_effective_growth,
    periodic_centered_gauss_assessment,
    relative_range,
    weighted_velocity_moments,
)


@pytest.mark.parametrize("growth_rate", [-0.15, 0.27])
def test_preregistered_windows_recover_synthetic_effective_growth(growth_rate: float) -> None:
    times = np.linspace(0.0, 20.0, 401)
    phase = np.exp(0.7j)
    mode = phase * np.exp(growth_rate * times)
    fit = fit_windowed_effective_growth(
        times,
        mode,
        early_window=(0.0, 4.0),
        late_window=(14.0, 18.0),
        minimum_samples=80,
    )
    assert fit.effective_growth_rate == pytest.approx(growth_rate)
    assert fit.amplitude_ratio == pytest.approx(np.exp(14.0 * growth_rate))
    assert fit.early_sample_count == 81
    assert fit.late_sample_count == 81


def test_windowed_growth_rejects_nonfinite_input() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        fit_windowed_effective_growth(
            np.array([0.0, 1.0, 2.0]),
            np.array([1.0, np.nan, 1.0]),
            early_window=(0.0, 0.5),
            late_window=(1.0, 2.0),
            minimum_samples=1,
        )


def test_centered_periodic_gauss_assessment_recovers_discrete_identity() -> None:
    cells = 64
    length = 2.0 * np.pi
    spacing = length / cells
    coordinate = (np.arange(cells) + 0.5) * spacing
    field = np.sin(coordinate)
    divergence = (np.roll(field, -1) - np.roll(field, 1)) / (2.0 * spacing)
    permittivity = 3.0
    assessment = periodic_centered_gauss_assessment(
        field,
        permittivity * divergence,
        cell_size=spacing,
        vacuum_permittivity=permittivity,
    )
    assert assessment.relative_residual < 1.0e-14
    assert assessment.relative_charge_imbalance < 1.0e-14


def test_weighted_relativistic_moments_and_energy_range() -> None:
    light_speed = 10.0
    velocities = np.array([-2.0, 1.0, 3.0])
    masses = np.array([2.0, 2.0, 2.0])
    proper = velocities / np.sqrt(1.0 - (velocities / light_speed) ** 2)
    weights = np.array([1.0, 2.0, 1.0])
    moments = weighted_velocity_moments(
        masses * proper,
        masses,
        weights,
        speed_of_light=light_speed,
    )
    expected_mean = float(np.average(velocities, weights=weights))
    expected_variance = float(np.average((velocities - expected_mean) ** 2, weights=weights))
    assert moments.total_weight == 4.0
    assert moments.mean_velocity == pytest.approx(expected_mean)
    assert moments.variance == pytest.approx(expected_variance)
    assert relative_range(np.array([10.0, 10.1, 9.9])) == pytest.approx(0.02)
