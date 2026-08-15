"""Pure numerical estimators used by the WarpX openPMD postprocessor."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class WindowedGrowth:
    effective_growth_rate: float
    early_rms_amplitude: float
    late_rms_amplitude: float
    amplitude_ratio: float
    early_sample_count: int
    late_sample_count: int
    initial_amplitude: float
    final_amplitude: float


@dataclass(frozen=True)
class WeightedMoments:
    total_weight: float
    mean_velocity: float
    variance: float


@dataclass(frozen=True)
class GaussAssessment:
    relative_residual: float
    relative_charge_imbalance: float


def fit_windowed_effective_growth(
    times_omega_pe: np.ndarray,
    complex_mode: np.ndarray,
    *,
    early_window: tuple[float, float],
    late_window: tuple[float, float],
    minimum_samples: int,
) -> WindowedGrowth:
    """Measure preregistered early/late RMS change of a spatial Fourier mode.

    The two-window estimator intentionally matches the independent quiet-start
    PIC benchmark.  It does not fit a late stochastic resurgence after a
    damped signal has reached the finite-particle noise floor.
    """

    times = np.asarray(times_omega_pe, dtype=float)
    mode = np.asarray(complex_mode, dtype=complex)
    if times.ndim != 1 or mode.ndim != 1 or len(times) != len(mode):
        raise ValueError("mode times and values must be equal-length one-dimensional arrays")
    if len(times) < minimum_samples or not np.all(np.diff(times) > 0):
        raise ValueError("mode series is too short or is not strictly increasing")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(mode)):
        raise ValueError("mode series contains non-finite values")
    early_start, early_end = early_window
    late_start, late_end = late_window
    if not 0 <= early_start < early_end < late_start < late_end <= times[-1] + 1.0e-10:
        raise ValueError("growth windows must be ordered inside the diagnostic trace")
    tolerance = 1.0e-10 * max(1.0, abs(late_end))
    early_selected = (times >= early_start - tolerance) & (times <= early_end + tolerance)
    late_selected = (times >= late_start - tolerance) & (times <= late_end + tolerance)
    early_count = int(np.count_nonzero(early_selected))
    late_count = int(np.count_nonzero(late_selected))
    if min(early_count, late_count) < minimum_samples:
        raise ValueError("a growth window contains too few diagnostic samples")
    amplitudes = np.abs(mode)
    early_rms = float(np.sqrt(np.mean(amplitudes[early_selected] ** 2)))
    late_rms = float(np.sqrt(np.mean(amplitudes[late_selected] ** 2)))
    if early_rms <= 0 or late_rms <= 0:
        raise ValueError("growth-window RMS amplitude is zero")
    ratio = late_rms / early_rms
    time_separation = 0.5 * (late_start + late_end - early_start - early_end)
    return WindowedGrowth(
        effective_growth_rate=float(np.log(ratio) / time_separation),
        early_rms_amplitude=early_rms,
        late_rms_amplitude=late_rms,
        amplitude_ratio=ratio,
        early_sample_count=early_count,
        late_sample_count=late_count,
        initial_amplitude=float(abs(mode[0])),
        final_amplitude=float(abs(mode[-1])),
    )


def periodic_centered_gauss_assessment(
    electric_field: np.ndarray,
    charge_density: np.ndarray,
    *,
    cell_size: float,
    vacuum_permittivity: float,
) -> GaussAssessment:
    """Assess the cell-centered periodic finite-difference Gauss law."""

    field = np.asarray(electric_field, dtype=float)
    charge = np.asarray(charge_density, dtype=float)
    if field.ndim != 1 or charge.shape != field.shape or len(field) < 4:
        raise ValueError("Gauss-law arrays must have one equal, nontrivial shape")
    if cell_size <= 0 or vacuum_permittivity <= 0:
        raise ValueError("Gauss-law normalization values must be positive")
    if not np.all(np.isfinite(field)) or not np.all(np.isfinite(charge)):
        raise ValueError("Gauss-law arrays contain non-finite values")
    divergence = (np.roll(field, -1) - np.roll(field, 1)) / (2.0 * cell_size)
    source = charge / vacuum_permittivity
    mean_source = float(np.mean(source))
    centered_source = source - mean_source
    centered_divergence = divergence - float(np.mean(divergence))
    scale = max(
        float(np.sqrt(np.mean(centered_source**2))),
        float(np.sqrt(np.mean(centered_divergence**2))),
    )
    if scale == 0:
        residual = 0.0
        imbalance = 0.0 if mean_source == 0 else float("inf")
    else:
        residual = float(np.sqrt(np.mean((centered_divergence - centered_source) ** 2)) / scale)
        imbalance = abs(mean_source) / scale
    return GaussAssessment(
        relative_residual=residual,
        relative_charge_imbalance=imbalance,
    )


def weighted_velocity_moments(
    momentum: np.ndarray,
    mass: np.ndarray,
    weights: np.ndarray,
    *,
    speed_of_light: float,
) -> WeightedMoments:
    """Convert SI momentum to velocity and compute weighted moments."""

    momentum = np.asarray(momentum, dtype=float)
    mass = np.asarray(mass, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if momentum.shape != mass.shape or momentum.shape != weights.shape or momentum.ndim != 1:
        raise ValueError("particle momentum, mass, and weight arrays must have one equal shape")
    if speed_of_light <= 0 or np.any(mass <= 0) or np.any(weights < 0):
        raise ValueError("particle mass, weight, and light speed are outside their domains")
    if not all(np.all(np.isfinite(values)) for values in (momentum, mass, weights)):
        raise ValueError("particle arrays contain non-finite values")
    total_weight = float(np.sum(weights))
    if total_weight <= 0:
        raise ValueError("particle weights sum to zero")
    proper_velocity = momentum / mass
    velocity = proper_velocity / np.sqrt(1.0 + (proper_velocity / speed_of_light) ** 2)
    mean = float(np.sum(weights * velocity) / total_weight)
    variance = float(np.sum(weights * (velocity - mean) ** 2) / total_weight)
    return WeightedMoments(
        total_weight=total_weight,
        mean_velocity=mean,
        variance=variance,
    )


def relative_range(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        raise ValueError("relative-range input must be a finite one-dimensional series")
    scale = abs(float(values[0]))
    if scale == 0:
        raise ValueError("relative range is undefined for a zero initial value")
    return float((np.max(values) - np.min(values)) / scale)


def diagnostic_manifest_hash(paths: Iterable[Path], *, root: Path) -> str:
    entries: list[dict[str, str | int]] = []
    for path in sorted((Path(path) for path in paths), key=lambda item: str(item)):
        content = path.read_bytes()
        entries.append(
            {
                "path": str(path.relative_to(root)),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
