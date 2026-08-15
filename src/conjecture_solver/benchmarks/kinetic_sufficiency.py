"""Matched-moment kinetic stability counterexample.

The normalization uses electron plasma frequency equal to one. Ions are an
immobile neutralizing background. For a Gaussian component with weight a,
drift u, and standard deviation sigma, its electrostatic susceptibility is

    a / (k sigma)^2 * [1 + zeta Z(zeta)]

where zeta = (omega - k u) / (sqrt(2) k sigma) and Z is the plasma dispersion
function. The least-damped or fastest-growing root is the primary observable.
"""

from __future__ import annotations

import warnings

import numpy as np
from pydantic import Field, model_validator
from scipy.optimize import root
from scipy.special import wofz

from ..models import (
    DomainSpec,
    EvidenceContract,
    HypothesisNode,
    HypothesisOrigin,
    MatchedPairFormalPredicate,
    ObservableSpec,
    PropositionClass,
    StrictModel,
)
from ..semantics import MatchedObservation, SufficiencyWitness, evaluate_predictive_sufficiency


class GaussianComponent(StrictModel):
    weight: float = Field(gt=0, le=1)
    drift: float
    sigma: float = Field(gt=0)


class GaussianMixture(StrictModel):
    components: tuple[GaussianComponent, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def normalized_weights(self) -> GaussianMixture:
        if abs(sum(component.weight for component in self.components) - 1.0) > 1e-12:
            raise ValueError("component weights must sum to one")
        return self

    def density(self) -> float:
        return sum(component.weight for component in self.components)

    def mean(self) -> float:
        return sum(component.weight * component.drift for component in self.components)

    def second_moment(self) -> float:
        return sum(
            component.weight * (component.sigma**2 + component.drift**2)
            for component in self.components
        )

    def variance(self) -> float:
        return self.second_moment() - self.mean() ** 2


class DistributionMoments(StrictModel):
    density: float
    mean_velocity: float
    variance: float = Field(ge=0)


class LinearMode(StrictModel):
    frequency: float
    growth_rate: float
    dielectric_residual: float = Field(ge=0)


class KineticCaseResult(StrictModel):
    name: str
    distribution: GaussianMixture
    moments: DistributionMoments
    mode: LinearMode
    classification: str


class KineticSufficiencyResult(StrictModel):
    schema_version: str = "0.1.0"
    experiment_id: str = "planted_kinetic_sufficiency_v1"
    hypothesis: HypothesisNode
    observable: ObservableSpec
    wavenumber: float = Field(gt=0)
    maxwellian: KineticCaseResult
    two_stream: KineticCaseResult
    moments_match: bool
    witness: SufficiencyWitness


def plasma_dispersion(zeta: complex) -> complex:
    return 1j * np.sqrt(np.pi) * wofz(zeta)


def dielectric(
    omega: complex,
    wavenumber: float,
    distribution: GaussianMixture,
) -> complex:
    value = 1.0 + 0.0j
    with np.errstate(all="ignore"):
        for component in distribution.components:
            zeta = (omega - wavenumber * component.drift) / (
                np.sqrt(2.0) * wavenumber * component.sigma
            )
            value += component.weight / (wavenumber * component.sigma) ** 2 * (
                1.0 + zeta * plasma_dispersion(zeta)
            )
    return complex(value)


def solve_modes(
    distribution: GaussianMixture,
    *,
    wavenumber: float,
    residual_tolerance: float = 1e-8,
) -> tuple[LinearMode, ...]:
    guesses = (
        complex(real, imaginary)
        for real in np.linspace(-2.0, 2.0, 9)
        for imaginary in np.linspace(-0.8, 0.6, 8)
    )
    modes: list[LinearMode] = []
    for guess in guesses:
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            solution = root(
                lambda pair: (
                    dielectric(
                        complex(float(pair[0]), float(pair[1])),
                        wavenumber,
                        distribution,
                    ).real,
                    dielectric(
                        complex(float(pair[0]), float(pair[1])),
                        wavenumber,
                        distribution,
                    ).imag,
                ),
                (guess.real, guess.imag),
                tol=1e-11,
            )
        if not solution.success or not np.all(np.isfinite(solution.x)):
            continue
        omega = complex(float(solution.x[0]), float(solution.x[1]))
        residual = abs(dielectric(omega, wavenumber, distribution))
        if residual > residual_tolerance or abs(omega) > 10:
            continue
        if any(
            abs(omega - complex(mode.frequency, mode.growth_rate)) < 1e-6 for mode in modes
        ):
            continue
        modes.append(
            LinearMode(
                frequency=omega.real,
                growth_rate=omega.imag,
                dielectric_residual=float(residual),
            )
        )
    if not modes:
        raise RuntimeError("dispersion solver found no validated root")
    return tuple(sorted(modes, key=lambda mode: mode.growth_rate, reverse=True))


def moments(distribution: GaussianMixture) -> DistributionMoments:
    return DistributionMoments(
        density=distribution.density(),
        mean_velocity=distribution.mean(),
        variance=distribution.variance(),
    )


def classify_mode(mode: LinearMode, *, zero_tolerance: float = 1e-6) -> str:
    if mode.growth_rate > zero_tolerance:
        return "unstable"
    if mode.growth_rate < -zero_tolerance:
        return "damped"
    return "neutral"


def build_problem() -> tuple[HypothesisNode, ObservableSpec]:
    domain = DomainSpec(
        id="domain_linear_1d_vlasov_poisson_k05",
        description=(
            "Linear electrostatic perturbations of smooth normalized electron "
            "distributions with immobile ions at k=0.5"
        ),
        model_family="linearized_1d_electrostatic_vlasov_poisson",
        assumptions=(
            "electron plasma frequency equals one",
            "immobile neutralizing ion background",
            "Gaussian-mixture equilibrium distributions",
        ),
        fixed_parameters={"wavenumber": 0.5},
    )
    observable = ObservableSpec(
        id="observable_dominant_growth_rate",
        name="dominant linear growth rate",
        semantic_kind="dominant_linear_growth_rate",
        mathematical_definition="maximum imaginary part among validated dielectric roots",
        estimator="analytic Gaussian-mixture dielectric root solver",
        units="electron_plasma_frequency",
        tolerance=0.02,
    )
    hypothesis = HypothesisNode(
        id="hypothesis_low_moments_sufficient_for_stability",
        statement=(
            "Density, mean velocity, and variance are sufficient to determine "
            "the dominant linear growth rate in the declared distribution family."
        ),
        machine_predicate=(
            "equal(n, mean_v, variance) implies abs(gamma_left-gamma_right) <= 0.02"
        ),
        formal_predicate=MatchedPairFormalPredicate(
            matched_coordinates=("density", "mean_velocity", "variance"),
            outcome_observable_id=observable.id,
            maximum_outcome_difference=observable.tolerance,
        ),
        proposition_class=PropositionClass.PREDICTIVE_SUFFICIENCY,
        domain=domain,
        coordinates=("density", "mean_velocity", "variance"),
        evidence_contract=EvidenceContract(
            primary_observable_id=observable.id,
            falsifying_witness=(
                "a matched pair with equal declared moments and growth rates "
                "separated by more than 0.02"
            ),
            primary_tolerance=observable.tolerance,
        ),
        origin=HypothesisOrigin.HUMAN,
    )
    return hypothesis, observable


def run_kinetic_sufficiency_benchmark(
    *,
    wavenumber: float = 0.5,
) -> KineticSufficiencyResult:
    if abs(wavenumber - 0.5) > 1e-12:
        raise ValueError("version 1 of the planted benchmark is preregistered at k=0.5")

    maxwellian_distribution = GaussianMixture(
        components=(GaussianComponent(weight=1.0, drift=0.0, sigma=1.0),)
    )
    drift = 0.9
    component_sigma = float(np.sqrt(1.0 - drift**2))
    two_stream_distribution = GaussianMixture(
        components=(
            GaussianComponent(weight=0.5, drift=-drift, sigma=component_sigma),
            GaussianComponent(weight=0.5, drift=drift, sigma=component_sigma),
        )
    )

    maxwellian_moments = moments(maxwellian_distribution)
    two_stream_moments = moments(two_stream_distribution)
    maxwellian_mode = solve_modes(
        maxwellian_distribution,
        wavenumber=wavenumber,
    )[0]
    two_stream_mode = solve_modes(
        two_stream_distribution,
        wavenumber=wavenumber,
    )[0]
    hypothesis, observable = build_problem()
    coordinate_names = hypothesis.coordinates
    left_coordinates = {
        coordinate: getattr(maxwellian_moments, coordinate) for coordinate in coordinate_names
    }
    right_coordinates = {
        coordinate: getattr(two_stream_moments, coordinate) for coordinate in coordinate_names
    }
    witness = evaluate_predictive_sufficiency(
        hypothesis,
        MatchedObservation(
            evidence_id="evidence_maxwellian_mode",
            coordinates=left_coordinates,
            outcome=maxwellian_mode.growth_rate,
            outcome_uncertainty=maxwellian_mode.dielectric_residual,
        ),
        MatchedObservation(
            evidence_id="evidence_two_stream_mode",
            coordinates=right_coordinates,
            outcome=two_stream_mode.growth_rate,
            outcome_uncertainty=two_stream_mode.dielectric_residual,
        ),
    )
    moments_match = all(
        abs(left_coordinates[name] - right_coordinates[name]) <= 1e-10
        for name in coordinate_names
    )
    return KineticSufficiencyResult(
        hypothesis=hypothesis,
        observable=observable,
        wavenumber=wavenumber,
        maxwellian=KineticCaseResult(
            name="unit_variance_maxwellian",
            distribution=maxwellian_distribution,
            moments=maxwellian_moments,
            mode=maxwellian_mode,
            classification=classify_mode(maxwellian_mode),
        ),
        two_stream=KineticCaseResult(
            name="matched_moment_symmetric_two_stream",
            distribution=two_stream_distribution,
            moments=two_stream_moments,
            mode=two_stream_mode,
            classification=classify_mode(two_stream_mode),
        ),
        moments_match=moments_match,
        witness=witness,
    )
