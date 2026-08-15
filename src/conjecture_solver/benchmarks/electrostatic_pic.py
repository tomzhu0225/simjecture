"""Independent one-dimensional electrostatic particle-in-cell benchmark.

The solver uses cloud-in-cell deposition/interpolation, a spectral periodic
Poisson solve, leapfrog integration, and quiet-start velocity beams. It is an
independent numerical check of the analytic dispersion-relation benchmark.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal

import numpy as np
from pydantic import Field, model_validator
from scipy.optimize import brentq
from scipy.special import ndtr, ndtri

from ..models import (
    DomainSpec,
    EvidenceContract,
    ExperimentSpec,
    HypothesisNode,
    HypothesisOrigin,
    MatchedPairFormalPredicate,
    ObservableSpec,
    PropositionClass,
    StrictModel,
)
from .kinetic_sufficiency import (
    DistributionMoments,
    GaussianMixture,
    moments,
)


class PICDistribution(StrEnum):
    MAXWELLIAN = "maxwellian"
    SYMMETRIC_TWO_STREAM = "symmetric_two_stream"


class PICNumericalConfig(StrictModel):
    """Distribution-independent PIC discretization and validity contract."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    wavenumber: float = Field(default=0.5, gt=0)
    grid_cells: int = Field(default=64, ge=32)
    velocity_beams: int = Field(default=256, ge=64)
    particles_per_beam: int = Field(default=64, ge=32)
    time_step: float = Field(default=0.05, gt=0)
    final_time: float = Field(default=20.0, gt=0)
    diagnostic_interval: float = Field(default=0.5, gt=0)
    perturbation_amplitude: float = Field(default=0.01, gt=0, lt=0.1)
    seed: int = Field(default=7, ge=0)
    early_window: tuple[float, float] = (0.0, 4.0)
    late_window: tuple[float, float] = (14.0, 18.0)
    damped_ratio_threshold: float = Field(default=0.75, gt=0, lt=1)
    unstable_ratio_threshold: float = Field(default=1.5, gt=1)
    maximum_relative_energy_drift: float = Field(default=1e-3, gt=0)
    maximum_gauss_residual: float = Field(default=1e-10, gt=0)

    @model_validator(mode="after")
    def validate_discretization(self) -> PICNumericalConfig:
        if abs(self.wavenumber - 0.5) > 1e-12:
            raise ValueError("PIC benchmark version 1 is preregistered at k=0.5")
        if self.grid_cells & (self.grid_cells - 1):
            raise ValueError("grid_cells must be a power of two")
        if self.velocity_beams % 2:
            raise ValueError("velocity_beams must be even")
        steps = self.final_time / self.time_step
        stride = self.diagnostic_interval / self.time_step
        if abs(steps - round(steps)) > 1e-10:
            raise ValueError("final_time must contain an integer number of steps")
        if abs(stride - round(stride)) > 1e-10:
            raise ValueError("diagnostic_interval must contain an integer number of steps")
        early_start, early_end = self.early_window
        late_start, late_end = self.late_window
        if not 0 <= early_start < early_end < late_start < late_end <= self.final_time:
            raise ValueError("diagnostic windows must be ordered inside the simulated time")
        return self


class PICConfig(PICNumericalConfig):
    """Legacy fixed-pair benchmark configuration."""

    stream_drift: float = Field(default=0.9, gt=0, lt=1)


DEFAULT_PIC_CONFIG = PICConfig()
DEFAULT_PIC_NUMERICAL_CONFIG = PICNumericalConfig()


class PICTrace(StrictModel):
    times: tuple[float, ...]
    fundamental_mode_amplitudes: tuple[float, ...]
    total_energies: tuple[float, ...]
    gauss_residuals: tuple[float, ...]

    @model_validator(mode="after")
    def equal_trace_lengths(self) -> PICTrace:
        lengths = {
            len(self.times),
            len(self.fundamental_mode_amplitudes),
            len(self.total_energies),
            len(self.gauss_residuals),
        }
        if len(lengths) != 1 or not self.times:
            raise ValueError("PIC diagnostic traces must be non-empty and aligned")
        return self


class PICCaseResult(StrictModel):
    distribution: PICDistribution
    config: PICConfig
    particle_count: int = Field(ge=1)
    initial_moments: DistributionMoments
    early_rms_amplitude: float = Field(gt=0)
    late_rms_amplitude: float = Field(gt=0)
    amplitude_ratio: float = Field(gt=0)
    effective_growth_rate: float
    classification: Literal["damped", "unstable", "ambiguous"]
    relative_energy_drift: float = Field(ge=0)
    maximum_gauss_residual: float = Field(ge=0)
    validity_passed: bool
    trace: PICTrace


class PICMixtureCaseResult(StrictModel):
    """PIC result for an explicitly supplied Gaussian mixture."""

    name: str
    distribution: GaussianMixture
    config: PICNumericalConfig
    particle_count: int = Field(ge=1)
    initial_moments: DistributionMoments
    early_rms_amplitude: float = Field(gt=0)
    late_rms_amplitude: float = Field(gt=0)
    amplitude_ratio: float = Field(gt=0)
    effective_growth_rate: float
    classification: Literal["damped", "unstable", "ambiguous"]
    relative_energy_drift: float = Field(ge=0)
    maximum_gauss_residual: float = Field(ge=0)
    validity_passed: bool
    trace: PICTrace


class PICSufficiencyResult(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    hypothesis: HypothesisNode
    observable: ObservableSpec
    maxwellian: PICCaseResult
    two_stream: PICCaseResult
    moments_match: bool
    hypothesis_falsified: bool


def build_pic_problem() -> tuple[HypothesisNode, ObservableSpec]:
    domain = DomainSpec(
        id="domain_electrostatic_1d_pic_k05",
        description=(
            "Small-amplitude periodic 1D electrostatic PIC approximations of normalized "
            "electron distributions with immobile ions at k=0.5"
        ),
        model_family="electrostatic_1d_pic_vlasov_poisson",
        assumptions=(
            "electron plasma frequency equals one",
            "immobile uniform neutralizing ion background",
            "periodic single-mode domain",
            "quiet-start Gaussian velocity beams",
        ),
        fixed_parameters={
            "wavenumber": 0.5,
            "perturbation_amplitude": 0.01,
            "stream_drift": 0.9,
        },
    )
    observable = ObservableSpec(
        id="observable_pic_effective_mode_growth",
        name="PIC effective fundamental-mode envelope growth rate",
        semantic_kind="effective_fundamental_growth_rate",
        mathematical_definition="log(late_mode_rms / early_mode_rms) / time_separation",
        estimator="quiet-start electrostatic PIC Fourier-mode diagnostic",
        units="electron_plasma_frequency",
        tolerance=0.02,
    )
    coordinates = ("density", "mean_velocity", "variance")
    hypothesis = HypothesisNode(
        id="hypothesis_pic_low_moments_sufficient_for_stability",
        statement=(
            "Density, mean velocity, and variance are sufficient to determine the "
            "effective fundamental-mode growth rate in the declared PIC family."
        ),
        machine_predicate=(
            "equal(n, mean_v, variance) implies abs(gamma_left-gamma_right) <= 0.02"
        ),
        formal_predicate=MatchedPairFormalPredicate(
            matched_coordinates=coordinates,
            outcome_observable_id=observable.id,
            maximum_outcome_difference=observable.tolerance,
        ),
        proposition_class=PropositionClass.PREDICTIVE_SUFFICIENCY,
        domain=domain,
        coordinates=coordinates,
        evidence_contract=EvidenceContract(
            primary_observable_id=observable.id,
            falsifying_witness=(
                "a matched-moment pair with PIC effective growth rates separated by "
                "more than 0.02 and opposite stability classifications"
            ),
            primary_tolerance=observable.tolerance,
        ),
        origin=HypothesisOrigin.HUMAN,
    )
    return hypothesis, observable


def build_pic_experiment(config: PICConfig = DEFAULT_PIC_CONFIG) -> ExperimentSpec:
    hypothesis, _ = build_pic_problem()
    return ExperimentSpec(
        id="experiment_electrostatic_pic_sufficiency_v1",
        hypothesis_ids=(hypothesis.id,),
        action_type="kinetic_sufficiency",
        physical_parameters={
            "wavenumber": config.wavenumber,
            "perturbation_amplitude": config.perturbation_amplitude,
            "stream_drift": config.stream_drift,
        },
        numerical_parameters={
            "grid_cells": config.grid_cells,
            "velocity_beams": config.velocity_beams,
            "particles_per_beam": config.particles_per_beam,
            "time_step": config.time_step,
            "final_time": config.final_time,
            "diagnostic_interval": config.diagnostic_interval,
            "seed": config.seed,
        },
        required_diagnostics=(
            "dominant_linear_mode",
            "distribution_moments",
            "energy_conservation",
            "gauss_residual",
        ),
        predictions={
            "hypothesis_holds": "matched distributions have equal effective growth rate",
            "falsifying_witness": (
                "matched distributions have separated rates and opposite stability classes"
            ),
        },
        falsification_condition=(
            "both PIC cases pass validity gates, moments match, classifications are opposite, "
            "and effective rates differ by more than 0.02"
        ),
    )


def _velocity_beams(
    distribution: PICDistribution,
    config: PICConfig,
) -> np.ndarray:
    half = config.velocity_beams // 2
    probabilities = (np.arange(half, dtype=float) + 0.5) / half
    thermal = ndtri(probabilities)
    thermal = (thermal - np.mean(thermal)) / np.std(thermal)
    if distribution is PICDistribution.MAXWELLIAN:
        return np.tile(thermal, 2)
    component_sigma = np.sqrt(1.0 - config.stream_drift**2)
    return np.concatenate(
        (
            -config.stream_drift + component_sigma * thermal,
            config.stream_drift + component_sigma * thermal,
        )
    )


def _mixture_velocity_beams(
    distribution: GaussianMixture,
    velocity_beams: int,
) -> np.ndarray:
    """Deterministic inverse-CDF beams, rescaled to exact discrete moments."""

    probabilities = (np.arange(velocity_beams, dtype=float) + 0.5) / velocity_beams
    lower = min(component.drift - 10.0 * component.sigma for component in distribution.components)
    upper = max(component.drift + 10.0 * component.sigma for component in distribution.components)

    def cdf(value: float) -> float:
        return float(
            sum(
                component.weight
                * ndtr((value - component.drift) / component.sigma)
                for component in distribution.components
            )
        )

    beams = np.asarray(
        [
            brentq(lambda value, target=target: cdf(value) - target, lower, upper)
            for target in probabilities
        ]
    )
    target = moments(distribution)
    beams = (beams - np.mean(beams)) / np.std(beams)
    beams = beams * np.sqrt(target.variance) + target.mean_velocity
    return beams


def _quiet_start_from_beams(
    beams: np.ndarray,
    config: PICNumericalConfig,
) -> tuple[np.ndarray, np.ndarray]:
    if beams.shape != (config.velocity_beams,):
        raise ValueError("velocity beam count does not match the PIC configuration")
    length = 2.0 * np.pi / config.wavenumber
    rng = np.random.default_rng(config.seed)
    offsets = rng.random(config.velocity_beams)
    base = np.arange(config.particles_per_beam, dtype=float)
    unperturbed = (
        (base[None, :] + 0.5 + offsets[:, None]) % config.particles_per_beam
    ) * (length / config.particles_per_beam)
    positions = (
        unperturbed
        - config.perturbation_amplitude
        / config.wavenumber
        * np.sin(config.wavenumber * unperturbed)
    ) % length
    velocities = np.repeat(beams, config.particles_per_beam)
    return positions.ravel(), velocities


def _deposit_and_field(
    positions: np.ndarray,
    config: PICNumericalConfig,
) -> tuple[np.ndarray, np.ndarray, float]:
    length = 2.0 * np.pi / config.wavenumber
    cell_width = length / config.grid_cells
    coordinate = positions / cell_width
    left = np.floor(coordinate).astype(np.int64) % config.grid_cells
    fraction = coordinate - left
    density = (
        np.bincount(left, weights=1.0 - fraction, minlength=config.grid_cells)
        + np.bincount(
            (left + 1) % config.grid_cells,
            weights=fraction,
            minlength=config.grid_cells,
        )
    ) * (config.grid_cells / positions.size)
    charge_density = 1.0 - density
    charge_modes = np.fft.fft(charge_density) / config.grid_cells
    wave_numbers = 2.0 * np.pi * np.fft.fftfreq(config.grid_cells, d=cell_width)
    field_modes = np.zeros(config.grid_cells, dtype=complex)
    nonzero = wave_numbers != 0
    field_modes[nonzero] = charge_modes[nonzero] / (1j * wave_numbers[nonzero])
    electric_field = np.fft.ifft(field_modes * config.grid_cells).real
    gauss_residual = float(
        np.max(np.abs(1j * wave_numbers[nonzero] * field_modes[nonzero] - charge_modes[nonzero]))
    )
    return electric_field, field_modes, gauss_residual


def _interpolate_field(
    electric_field: np.ndarray,
    positions: np.ndarray,
    config: PICNumericalConfig,
) -> np.ndarray:
    length = 2.0 * np.pi / config.wavenumber
    cell_width = length / config.grid_cells
    coordinate = positions / cell_width
    left = np.floor(coordinate).astype(np.int64) % config.grid_cells
    fraction = coordinate - left
    return (
        electric_field[left] * (1.0 - fraction)
        + electric_field[(left + 1) % config.grid_cells] * fraction
    )


def _window_rms(times: np.ndarray, amplitudes: np.ndarray, window: tuple[float, float]) -> float:
    selected = (times >= window[0]) & (times <= window[1])
    if not np.any(selected):
        raise ValueError("diagnostic window contains no samples")
    return float(np.sqrt(np.mean(amplitudes[selected] ** 2)))


@lru_cache(maxsize=32)
def run_pic_case(
    distribution: PICDistribution,
    config: PICConfig = DEFAULT_PIC_CONFIG,
) -> PICCaseResult:
    beams = _velocity_beams(distribution, config)
    positions, initial_velocities = _quiet_start_from_beams(beams, config)
    result = _run_pic_dynamics(positions, initial_velocities, config)
    return PICCaseResult(
        distribution=distribution,
        config=config,
        **result,
    )


def _run_pic_dynamics(
    positions: np.ndarray,
    initial_velocities: np.ndarray,
    config: PICNumericalConfig,
) -> dict[str, object]:
    initial_moments = DistributionMoments(
        density=1.0,
        mean_velocity=float(np.mean(initial_velocities)),
        variance=float(np.var(initial_velocities)),
    )
    electric_field, field_modes, gauss_residual = _deposit_and_field(positions, config)
    velocities_half = initial_velocities - 0.5 * config.time_step * _interpolate_field(
        electric_field,
        positions,
        config,
    )

    step_count = round(config.final_time / config.time_step)
    diagnostic_stride = round(config.diagnostic_interval / config.time_step)
    times: list[float] = []
    amplitudes: list[float] = []
    energies: list[float] = []
    gauss_residuals: list[float] = []
    length = 2.0 * np.pi / config.wavenumber

    for step in range(step_count + 1):
        if step % diagnostic_stride == 0:
            integer_velocity = velocities_half + 0.5 * config.time_step * _interpolate_field(
                electric_field,
                positions,
                config,
            )
            times.append(step * config.time_step)
            amplitudes.append(float(abs(field_modes[1])))
            energies.append(
                float(
                    0.5 * np.mean(integer_velocity**2)
                    + 0.5 * np.mean(electric_field**2)
                )
            )
            gauss_residuals.append(gauss_residual)
        if step == step_count:
            break
        positions = (positions + config.time_step * velocities_half) % length
        electric_field, field_modes, gauss_residual = _deposit_and_field(positions, config)
        velocities_half -= config.time_step * _interpolate_field(
            electric_field,
            positions,
            config,
        )

    time_array = np.asarray(times)
    amplitude_array = np.asarray(amplitudes)
    energy_array = np.asarray(energies)
    early_rms = _window_rms(time_array, amplitude_array, config.early_window)
    late_rms = _window_rms(time_array, amplitude_array, config.late_window)
    ratio = late_rms / early_rms
    time_separation = (
        sum(config.late_window) / 2.0 - sum(config.early_window) / 2.0
    )
    effective_growth_rate = float(np.log(ratio) / time_separation)
    if ratio < config.damped_ratio_threshold:
        classification: Literal["damped", "unstable", "ambiguous"] = "damped"
    elif ratio > config.unstable_ratio_threshold:
        classification = "unstable"
    else:
        classification = "ambiguous"
    relative_energy_drift = float(
        (np.max(energy_array) - np.min(energy_array)) / energy_array[0]
    )
    finite = all(
        np.all(np.isfinite(values))
        for values in (positions, velocities_half, amplitude_array, energy_array)
    )
    maximum_gauss_residual = max(gauss_residuals)
    validity_passed = (
        finite
        and relative_energy_drift <= config.maximum_relative_energy_drift
        and maximum_gauss_residual <= config.maximum_gauss_residual
    )
    return {
        "particle_count": positions.size,
        "initial_moments": initial_moments,
        "early_rms_amplitude": early_rms,
        "late_rms_amplitude": late_rms,
        "amplitude_ratio": ratio,
        "effective_growth_rate": effective_growth_rate,
        "classification": classification,
        "relative_energy_drift": relative_energy_drift,
        "maximum_gauss_residual": maximum_gauss_residual,
        "validity_passed": validity_passed,
        "trace": PICTrace(
            times=tuple(times),
            fundamental_mode_amplitudes=tuple(amplitudes),
            total_energies=tuple(energies),
            gauss_residuals=tuple(gauss_residuals),
        ),
    }


@lru_cache(maxsize=32)
def run_pic_mixture_case(
    name: str,
    distribution: GaussianMixture,
    config: PICNumericalConfig = DEFAULT_PIC_NUMERICAL_CONFIG,
) -> PICMixtureCaseResult:
    """Run the independent PIC instrument for a frozen mixture candidate."""

    beams = _mixture_velocity_beams(distribution, config.velocity_beams)
    positions, initial_velocities = _quiet_start_from_beams(beams, config)
    result = _run_pic_dynamics(positions, initial_velocities, config)
    return PICMixtureCaseResult(
        name=name,
        distribution=distribution,
        config=config,
        **result,
    )


def run_pic_sufficiency_benchmark(
    config: PICConfig = DEFAULT_PIC_CONFIG,
) -> PICSufficiencyResult:
    maxwellian = run_pic_case(PICDistribution.MAXWELLIAN, config)
    two_stream = run_pic_case(PICDistribution.SYMMETRIC_TWO_STREAM, config)
    hypothesis, observable = build_pic_problem()
    left = maxwellian.initial_moments
    right = two_stream.initial_moments
    moments_match = all(
        abs(getattr(left, name) - getattr(right, name)) <= 1e-12
        for name in ("density", "mean_velocity", "variance")
    )
    separated = (
        abs(maxwellian.effective_growth_rate - two_stream.effective_growth_rate)
        > hypothesis.evidence_contract.primary_tolerance
    )
    hypothesis_falsified = (
        moments_match
        and maxwellian.validity_passed
        and two_stream.validity_passed
        and maxwellian.classification == "damped"
        and two_stream.classification == "unstable"
        and separated
    )
    return PICSufficiencyResult(
        hypothesis=hypothesis,
        observable=observable,
        maxwellian=maxwellian,
        two_stream=two_stream,
        moments_match=moments_match,
        hypothesis_falsified=hypothesis_falsified,
    )
