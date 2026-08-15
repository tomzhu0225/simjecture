"""Restricted WarpX/PICMI compiler and execution boundary.

The model-facing surface is a small set of validated scalar parameters.  This
module, not a language model, owns the executable PICMI template and the
result-validity rules.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import platform
import subprocess
from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from statistics import median
from typing import Any, Literal

from pydantic import Field, model_validator

from ..models import ExperimentSpec, StrictModel, utc_now
from ..search import SymmetricMixtureCandidate
from .base import (
    CapabilityManifest,
    CostEstimate,
    JobReference,
    JobState,
    JobStatus,
    NormalizedResult,
    RawResult,
    RunPackage,
    ValidationReport,
)

ELECTRON_CHARGE_C = 1.602176634e-19
ELECTRON_MASS_KG = 9.1093837139e-31
VACUUM_PERMITTIVITY_F_M = 8.8541878128e-12
SPEED_OF_LIGHT_M_S = 299792458.0

WARPX_ADAPTER_VERSION = "0.3.0"
WARPX_CONTRACT_VERSION = "warpx_picmi_pair_v1"
WARPX_ACTION = "warpx_kinetic_sufficiency_confirmation"
WARPX_MODEL = "warpx_electrostatic_1d3v_pic"
WARPX_REQUIRED_DIAGNOSTICS = (
    "dominant_linear_mode",
    "distribution_moments",
    "field_energy",
    "gauss_residual",
    "openpmd_electric_field",
    "particle_energy",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _warpx_versions_equivalent(left: str, right: str) -> bool:
    """Treat release spellings such as 26.07 and Python metadata 26.7 as equal."""

    try:
        return tuple(int(part) for part in left.split(".")) == tuple(
            int(part) for part in right.split(".")
        )
    except ValueError:
        return left == right


class WarpXRunnerKind(StrEnum):
    CONTRACT_FIXTURE = "contract_fixture"
    LOCAL_CPU = "local_cpu"
    SITE_SCHEDULER = "site_scheduler"


class WarpXExecutionProfile(StrictModel):
    """Identity and trust status of the process that executes a run package."""

    profile_id: str = Field(min_length=1)
    runner_kind: WarpXRunnerKind
    warpx_version: str = Field(min_length=1)
    openpmd_backend: Literal["h5"] = "h5"
    qualification_hash: str | None = None
    qualified_for_scientific_evidence: bool = False

    @model_validator(mode="after")
    def qualification_is_coherent(self) -> WarpXExecutionProfile:
        if self.runner_kind is WarpXRunnerKind.CONTRACT_FIXTURE:
            if self.qualified_for_scientific_evidence or self.qualification_hash is not None:
                raise ValueError("a contract fixture can never be qualified as scientific evidence")
        elif self.qualified_for_scientific_evidence and self.qualification_hash is None:
            raise ValueError("an evidence-qualified profile requires a qualification hash")
        return self


class WarpXPhysicalConfig(StrictModel):
    reference_density_m3: float = Field(default=1.0e18, ge=1.0e12, le=1.0e25)
    velocity_unit_m_s: float = Field(default=1.0e6, ge=1.0e3, le=2.0e7)
    wavenumber_dimensionless: float = Field(default=0.5, ge=0.1, le=2.0)
    perturbation_amplitude: float = Field(default=0.02, ge=1.0e-7, le=0.05)
    inner_pair_weight: float = Field(default=0.5, gt=0, lt=1)
    inner_drift: float = Field(default=0.95, ge=0, lt=1)
    outer_drift: float = Field(default=0.95, ge=0, lt=1)

    @model_validator(mode="after")
    def candidate_is_safe(self) -> WarpXPhysicalConfig:
        candidate = self.candidate
        if (candidate.outer_drift + 6.0 * candidate.thermal_sigma) * self.velocity_unit_m_s > (
            0.25 * SPEED_OF_LIGHT_M_S
        ):
            raise ValueError("the declared nonrelativistic distribution extends above 0.25 c")
        return self

    @property
    def candidate(self) -> SymmetricMixtureCandidate:
        return SymmetricMixtureCandidate(
            inner_pair_weight=self.inner_pair_weight,
            inner_drift=self.inner_drift,
            outer_drift=self.outer_drift,
        )

    @property
    def plasma_frequency_rad_s(self) -> float:
        return math.sqrt(
            self.reference_density_m3
            * ELECTRON_CHARGE_C**2
            / (ELECTRON_MASS_KG * VACUUM_PERMITTIVITY_F_M)
        )

    @property
    def wavenumber_m_inverse(self) -> float:
        return self.wavenumber_dimensionless * self.plasma_frequency_rad_s / self.velocity_unit_m_s

    @property
    def domain_length_m(self) -> float:
        return 2.0 * math.pi / self.wavenumber_m_inverse


class WarpXNumericalConfig(StrictModel):
    grid_cells: int = Field(default=64, ge=32, le=4096)
    electron_macroparticles_per_cell: int = Field(default=512, ge=16, le=8192)
    ion_macroparticles_per_cell: int = Field(default=16, ge=1, le=1024)
    time_step_omega_pe: float = Field(default=0.05, ge=0.001, le=0.2)
    final_time_omega_pe: float = Field(default=20.0, ge=1.0, le=500.0)
    diagnostic_interval_steps: int = Field(default=2, ge=1, le=10000)
    random_seed: int = Field(default=1, ge=1, le=2_147_483_647)
    poisson_relative_tolerance: float = Field(default=1.0e-10, ge=1.0e-14, le=1.0e-4)
    poisson_max_iterations: int = Field(default=200, ge=10, le=10000)
    minimum_diagnostic_samples: int = Field(default=50, ge=3, le=10000)
    early_window_start_omega_pe: float = Field(default=0.0, ge=0)
    early_window_end_omega_pe: float = Field(default=4.0, gt=0)
    late_window_start_omega_pe: float = Field(default=14.0, gt=0)
    late_window_end_omega_pe: float = Field(default=18.0, gt=0)
    minimum_window_samples: int = Field(default=20, ge=3, le=10000)
    damped_ratio_threshold: float = Field(default=0.75, gt=0, lt=1)
    unstable_ratio_threshold: float = Field(default=1.5, gt=1)
    maximum_relative_energy_drift: float = Field(default=0.01, gt=0, le=1.0)
    maximum_relative_gauss_residual: float = Field(default=0.01, gt=0, le=1.0)
    maximum_relative_charge_imbalance: float = Field(default=0.01, gt=0, le=1.0)
    moment_tolerance: float = Field(default=0.05, gt=0, le=0.5)
    outcome_tolerance_omega_pe: float = Field(default=0.02, gt=0, le=1.0)

    @model_validator(mode="after")
    def discrete_layout_is_valid(self) -> WarpXNumericalConfig:
        if self.grid_cells & (self.grid_cells - 1):
            raise ValueError("grid_cells must be a power of two")
        if self.electron_macroparticles_per_cell % 4:
            raise ValueError("electron_macroparticles_per_cell must be divisible by four")
        steps = self.final_time_omega_pe / self.time_step_omega_pe
        if abs(steps - round(steps)) > 1.0e-10:
            raise ValueError("final_time_omega_pe must contain an integer number of steps")
        if self.max_steps % self.diagnostic_interval_steps:
            raise ValueError("diagnostic_interval_steps must divide the total step count")
        available_samples = self.max_steps // self.diagnostic_interval_steps + 1
        if available_samples < self.minimum_diagnostic_samples:
            raise ValueError("the diagnostic cadence cannot provide the required samples")
        windows = (
            self.early_window_start_omega_pe,
            self.early_window_end_omega_pe,
            self.late_window_start_omega_pe,
            self.late_window_end_omega_pe,
        )
        if not 0 <= windows[0] < windows[1] < windows[2] < windows[3] <= self.final_time_omega_pe:
            raise ValueError("the growth windows must be ordered and inside the run")
        cadence = self.diagnostic_interval_steps * self.time_step_omega_pe
        for start, end in ((windows[0], windows[1]), (windows[2], windows[3])):
            samples = math.floor((end - start) / cadence + 1.0e-10) + 1
            if samples < self.minimum_window_samples:
                raise ValueError("a growth window cannot provide the required samples")
        return self

    @property
    def max_steps(self) -> int:
        return round(self.final_time_omega_pe / self.time_step_omega_pe)


class WarpXCompiledCase(StrictModel):
    case_name: Literal["unit_maxwellian_reference", "symmetric_mixture_candidate"]
    script: str = Field(min_length=1)
    script_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def hash_matches_script(self) -> WarpXCompiledCase:
        if _sha256_text(self.script) != self.script_hash:
            raise ValueError("compiled PICMI script hash does not match its content")
        return self


class WarpXCaseSummary(StrictModel):
    case_name: Literal["unit_maxwellian_reference", "symmetric_mixture_candidate"]
    solver_converged: bool
    finite_values: bool
    diagnostic_samples: int = Field(ge=0)
    effective_growth_rate_omega_pe: float
    early_rms_amplitude_v_m: float = Field(gt=0)
    late_rms_amplitude_v_m: float = Field(gt=0)
    amplitude_ratio: float = Field(gt=0)
    early_window_sample_count: int = Field(ge=0)
    late_window_sample_count: int = Field(ge=0)
    classification: Literal["damped", "ambiguous", "unstable"]
    fundamental_amplitude_initial_v_m: float = Field(ge=0)
    fundamental_amplitude_final_v_m: float = Field(ge=0)
    initial_density_normalized: float = Field(gt=0)
    initial_mean_velocity_normalized: float
    initial_variance_normalized: float = Field(ge=0)
    relative_energy_drift: float = Field(ge=0)
    relative_gauss_residual: float = Field(ge=0)
    relative_charge_imbalance: float = Field(ge=0)
    diagnostic_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class WarpXPairSummary(StrictModel):
    contract_version: Literal["warpx_picmi_pair_v1"] = WARPX_CONTRACT_VERSION
    postprocessor_version: Literal["warpx_openpmd_v2"] = "warpx_openpmd_v2"
    runtime_warpx_version: str = Field(min_length=1)
    reference: WarpXCaseSummary
    candidate: WarpXCaseSummary

    @model_validator(mode="after")
    def cases_have_expected_roles(self) -> WarpXPairSummary:
        if self.reference.case_name != "unit_maxwellian_reference":
            raise ValueError("reference summary has the wrong case name")
        if self.candidate.case_name != "symmetric_mixture_candidate":
            raise ValueError("candidate summary has the wrong case name")
        return self


class WarpXQualificationRecord(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    profile_id: str = Field(min_length=1)
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_warpx_version: str = Field(min_length=1)
    observed_warpx_version: str | None = None
    qualification_kind: Literal["picmi_compile_only"] = "picmi_compile_only"
    compiled_case_hashes: dict[str, str] = Field(default_factory=dict)
    checks: dict[str, bool]
    passed: bool
    scientific_evidence_eligible: Literal[False] = False
    host_architecture: str = Field(default_factory=platform.machine)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def pass_matches_checks(self) -> WarpXQualificationRecord:
        if not self.checks:
            raise ValueError("a qualification record requires at least one check")
        if self.passed != all(self.checks.values()):
            raise ValueError("qualification pass flag must equal the conjunction of checks")
        if self.passed and set(self.compiled_case_hashes) != {
            "unit_maxwellian_reference",
            "symmetric_mixture_candidate",
        }:
            raise ValueError("a passing qualification must compile both cases")
        return self


class WarpXQualifiedScope(StrictModel):
    physical: WarpXPhysicalConfig
    minimum_grid_cells: int = Field(default=64, ge=32)
    minimum_electron_macroparticles_per_cell: int = Field(default=512, ge=16)
    minimum_ion_macroparticles_per_cell: int = Field(default=16, ge=1)
    maximum_time_step_omega_pe: float = Field(default=0.05, gt=0)
    minimum_final_time_omega_pe: float = Field(default=20.0, gt=0)
    maximum_diagnostic_cadence_omega_pe: float = Field(default=0.1, gt=0)
    early_window_start_omega_pe: float = Field(default=0.0, ge=0)
    early_window_end_omega_pe: float = Field(default=4.0, gt=0)
    late_window_start_omega_pe: float = Field(default=14.0, gt=0)
    late_window_end_omega_pe: float = Field(default=18.0, gt=0)
    maximum_damped_ratio_threshold: float = Field(default=0.75, gt=0, lt=1)
    minimum_unstable_ratio_threshold: float = Field(default=1.5, gt=1)
    maximum_poisson_relative_tolerance: float = Field(default=1.0e-10, gt=0)
    minimum_poisson_max_iterations: int = Field(default=200, ge=10)
    minimum_diagnostic_samples: int = Field(default=50, ge=3)
    minimum_window_samples: int = Field(default=20, ge=3)
    maximum_relative_energy_drift: float = Field(default=0.01, gt=0)
    maximum_relative_gauss_residual: float = Field(default=0.01, gt=0)
    maximum_relative_charge_imbalance: float = Field(default=0.01, gt=0)
    maximum_moment_tolerance: float = Field(default=0.05, gt=0)
    minimum_outcome_tolerance_omega_pe: float = Field(default=0.02, gt=0)

    def validation_errors(
        self,
        physical: WarpXPhysicalConfig,
        numerical: WarpXNumericalConfig,
    ) -> tuple[str, ...]:
        errors: list[str] = []
        if physical != self.physical:
            errors.append("physical configuration is outside the qualified scope")
        if numerical.grid_cells < self.minimum_grid_cells:
            errors.append("grid resolution is below the qualified scope")
        if (
            numerical.electron_macroparticles_per_cell
            < self.minimum_electron_macroparticles_per_cell
        ):
            errors.append("electron particle resolution is below the qualified scope")
        if numerical.ion_macroparticles_per_cell < self.minimum_ion_macroparticles_per_cell:
            errors.append("ion particle resolution is below the qualified scope")
        if numerical.time_step_omega_pe > self.maximum_time_step_omega_pe:
            errors.append("time step is above the qualified scope")
        if numerical.final_time_omega_pe < self.minimum_final_time_omega_pe:
            errors.append("run duration is below the qualified scope")
        cadence = numerical.diagnostic_interval_steps * numerical.time_step_omega_pe
        if cadence > self.maximum_diagnostic_cadence_omega_pe:
            errors.append("diagnostic cadence is coarser than the qualified scope")
        configured_windows = (
            numerical.early_window_start_omega_pe,
            numerical.early_window_end_omega_pe,
            numerical.late_window_start_omega_pe,
            numerical.late_window_end_omega_pe,
        )
        qualified_windows = (
            self.early_window_start_omega_pe,
            self.early_window_end_omega_pe,
            self.late_window_start_omega_pe,
            self.late_window_end_omega_pe,
        )
        if any(
            abs(configured - qualified) > 1.0e-12
            for configured, qualified in zip(configured_windows, qualified_windows, strict=True)
        ):
            errors.append("growth windows differ from the qualified scope")
        if numerical.damped_ratio_threshold > self.maximum_damped_ratio_threshold:
            errors.append("damped classification gate is weaker than the qualified scope")
        if numerical.unstable_ratio_threshold < self.minimum_unstable_ratio_threshold:
            errors.append("unstable classification gate is weaker than the qualified scope")
        if numerical.poisson_relative_tolerance > self.maximum_poisson_relative_tolerance:
            errors.append("Poisson tolerance is weaker than the qualified scope")
        if numerical.poisson_max_iterations < self.minimum_poisson_max_iterations:
            errors.append("Poisson iteration limit is below the qualified scope")
        if numerical.minimum_diagnostic_samples < self.minimum_diagnostic_samples:
            errors.append("diagnostic sample gate is weaker than the qualified scope")
        if numerical.minimum_window_samples < self.minimum_window_samples:
            errors.append("window sample gate is weaker than the qualified scope")
        if numerical.maximum_relative_energy_drift > self.maximum_relative_energy_drift:
            errors.append("energy-drift gate is weaker than the qualified scope")
        if numerical.maximum_relative_gauss_residual > self.maximum_relative_gauss_residual:
            errors.append("Gauss-residual gate is weaker than the qualified scope")
        if numerical.maximum_relative_charge_imbalance > self.maximum_relative_charge_imbalance:
            errors.append("charge-imbalance gate is weaker than the qualified scope")
        if numerical.moment_tolerance > self.maximum_moment_tolerance:
            errors.append("moment gate is weaker than the qualified scope")
        if numerical.outcome_tolerance_omega_pe < self.minimum_outcome_tolerance_omega_pe:
            errors.append("outcome-separation gate is weaker than the qualified scope")
        return tuple(errors)


class WarpXCalibrationPoint(StrictModel):
    seed: int = Field(ge=1)
    resolution_id: str = Field(min_length=1)
    grid_cells: int = Field(ge=32)
    electron_macroparticles_per_cell: int = Field(ge=16)
    time_step_omega_pe: float = Field(gt=0)
    run_package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalized_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_profile: WarpXExecutionProfile
    numerical_validity_passed: bool
    reference_growth_rate: float
    candidate_growth_rate: float
    reference_amplitude_ratio: float = Field(gt=0)
    candidate_amplitude_ratio: float = Field(gt=0)
    reference_classification: Literal["damped", "ambiguous", "unstable"]
    candidate_classification: Literal["damped", "ambiguous", "unstable"]
    reference_diagnostic_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_diagnostic_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class WarpXPhysicsQualificationRecord(StrictModel):
    schema_version: Literal["0.2.0"] = "0.2.0"
    qualification_kind: Literal["known_mode_matrix_v2"] = "known_mode_matrix_v2"
    compile_qualification: WarpXQualificationRecord
    calibration_points: tuple[WarpXCalibrationPoint, ...] = Field(min_length=1)
    postprocessor_version: Literal["warpx_openpmd_v2"] = "warpx_openpmd_v2"
    scope: WarpXQualifiedScope
    analytic_reference_growth_rate: float
    analytic_candidate_growth_rate: float
    expected_reference_classification: Literal["damped"] = "damped"
    expected_candidate_classification: Literal["unstable"] = "unstable"
    minimum_seed_count: int = Field(default=4, ge=2)
    minimum_resolution_count: int = Field(default=2, ge=2)
    minimum_effective_rate_separation: float = Field(default=0.1, gt=0)
    maximum_median_rate_shift: float = Field(default=0.03, gt=0)
    median_reference_rates_by_resolution: dict[str, float]
    median_candidate_rates_by_resolution: dict[str, float]
    checks: dict[str, bool]
    passed: bool
    authorizes_scientific_evidence: bool
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def status_is_coherent(self) -> WarpXPhysicsQualificationRecord:
        if not self.checks:
            raise ValueError("physics qualification requires checks")
        if self.passed != all(self.checks.values()):
            raise ValueError("physics qualification pass flag must equal all checks")
        if self.authorizes_scientific_evidence != self.passed:
            raise ValueError("only a passing physics qualification can authorize evidence")
        return self


def warpx_physics_qualification_hash(record: WarpXPhysicsQualificationRecord) -> str:
    def without_timestamps(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: without_timestamps(item) for key, item in value.items() if key != "created_at"
            }
        if isinstance(value, list):
            return [without_timestamps(item) for item in value]
        return value

    return _sha256_text(_canonical_json(without_timestamps(record.model_dump(mode="json"))))


def build_warpx_physics_qualification(
    *,
    compile_qualification: WarpXQualificationRecord,
    calibration_results: Sequence[NormalizedResult],
    scope: WarpXQualifiedScope,
    analytic_reference_growth_rate: float,
    analytic_candidate_growth_rate: float,
    minimum_seed_count: int = 4,
    minimum_resolution_count: int = 2,
    minimum_effective_rate_separation: float = 0.1,
    maximum_median_rate_shift: float = 0.03,
) -> WarpXPhysicsQualificationRecord:
    points: list[WarpXCalibrationPoint] = []
    physical_configs: list[WarpXPhysicalConfig] = []
    numerical_configs: list[WarpXNumericalConfig] = []
    for result in calibration_results:
        diagnostics = result.diagnostics
        pair = WarpXPairSummary.model_validate(diagnostics["pair_summary"])
        profile = WarpXExecutionProfile.model_validate(diagnostics["execution_profile"])
        physical = WarpXPhysicalConfig.model_validate(diagnostics["physical"])
        numerical = WarpXNumericalConfig.model_validate(diagnostics["numerical"])
        resolution_id = (
            f"g{numerical.grid_cells}_ppc{numerical.electron_macroparticles_per_cell}_"
            f"dt{numerical.time_step_omega_pe:g}"
        )
        physical_configs.append(physical)
        numerical_configs.append(numerical)
        points.append(
            WarpXCalibrationPoint(
                seed=numerical.random_seed,
                resolution_id=resolution_id,
                grid_cells=numerical.grid_cells,
                electron_macroparticles_per_cell=(numerical.electron_macroparticles_per_cell),
                time_step_omega_pe=numerical.time_step_omega_pe,
                run_package_hash=str(diagnostics["run_package_hash"]),
                normalized_result_hash=_sha256_text(
                    _canonical_json(result.model_dump(mode="json"))
                ),
                execution_profile=profile,
                numerical_validity_passed=bool(
                    diagnostics["validity_gates"]["numerical_validity_passed"]
                ),
                reference_growth_rate=pair.reference.effective_growth_rate_omega_pe,
                candidate_growth_rate=pair.candidate.effective_growth_rate_omega_pe,
                reference_amplitude_ratio=pair.reference.amplitude_ratio,
                candidate_amplitude_ratio=pair.candidate.amplitude_ratio,
                reference_classification=pair.reference.classification,
                candidate_classification=pair.candidate.classification,
                reference_diagnostic_manifest_hash=(pair.reference.diagnostic_manifest_hash),
                candidate_diagnostic_manifest_hash=(pair.candidate.diagnostic_manifest_hash),
            )
        )

    seed_set = {point.seed for point in points}
    resolution_set = {point.resolution_id for point in points}
    matrix_keys = {(point.seed, point.resolution_id) for point in points}
    matrix_complete = (
        len(seed_set) >= minimum_seed_count
        and len(resolution_set) >= minimum_resolution_count
        and len(matrix_keys) == len(points) == len(seed_set) * len(resolution_set)
        and all(
            {point.seed for point in points if point.resolution_id == resolution_id} == seed_set
            for resolution_id in resolution_set
        )
    )

    def medians(attribute: str) -> dict[str, float]:
        return {
            resolution_id: float(
                median(
                    getattr(point, attribute)
                    for point in points
                    if point.resolution_id == resolution_id
                )
            )
            for resolution_id in sorted(resolution_set)
        }

    reference_medians = medians("reference_growth_rate")
    candidate_medians = medians("candidate_growth_rate")

    def median_range(values: dict[str, float]) -> float:
        return max(values.values()) - min(values.values()) if values else math.inf

    manifest_hashes = {
        digest
        for point in points
        for digest in (
            point.reference_diagnostic_manifest_hash,
            point.candidate_diagnostic_manifest_hash,
        )
    }
    checks = {
        "compile_qualification_passed": compile_qualification.passed,
        "compile_package_is_in_calibration_matrix": (
            compile_qualification.package_hash in {point.run_package_hash for point in points}
        ),
        "calibration_matrix_complete": matrix_complete,
        "calibration_packages_are_unique": (
            len({point.run_package_hash for point in points}) == len(points)
        ),
        "calibration_diagnostics_are_unique": len(manifest_hashes) == 2 * len(points),
        "calibration_profiles_were_unqualified": all(
            not point.execution_profile.qualified_for_scientific_evidence for point in points
        ),
        "calibration_runners_are_not_fixtures": all(
            point.execution_profile.runner_kind is not WarpXRunnerKind.CONTRACT_FIXTURE
            for point in points
        ),
        "calibration_configurations_are_in_scope": all(
            physical == scope.physical and not scope.validation_errors(physical, numerical)
            for physical, numerical in zip(physical_configs, numerical_configs, strict=True)
        ),
        "all_calibration_runs_are_numerically_valid": all(
            point.numerical_validity_passed for point in points
        ),
        "all_reference_cases_match_damped_oracle": all(
            point.reference_classification == "damped" for point in points
        ),
        "all_candidate_cases_match_unstable_oracle": all(
            point.candidate_classification == "unstable" for point in points
        ),
        "all_pairs_exceed_effective_rate_separation": all(
            point.candidate_growth_rate - point.reference_growth_rate
            >= minimum_effective_rate_separation
            for point in points
        ),
        "reference_median_rate_is_resolution_converged": (
            median_range(reference_medians) <= maximum_median_rate_shift
        ),
        "candidate_median_rate_is_resolution_converged": (
            median_range(candidate_medians) <= maximum_median_rate_shift
        ),
    }
    passed = all(checks.values())
    return WarpXPhysicsQualificationRecord(
        compile_qualification=compile_qualification,
        calibration_points=tuple(
            sorted(points, key=lambda point: (point.resolution_id, point.seed))
        ),
        scope=scope,
        analytic_reference_growth_rate=analytic_reference_growth_rate,
        analytic_candidate_growth_rate=analytic_candidate_growth_rate,
        minimum_seed_count=minimum_seed_count,
        minimum_resolution_count=minimum_resolution_count,
        minimum_effective_rate_separation=minimum_effective_rate_separation,
        maximum_median_rate_shift=maximum_median_rate_shift,
        median_reference_rates_by_resolution=reference_medians,
        median_candidate_rates_by_resolution=candidate_medians,
        checks=checks,
        passed=passed,
        authorizes_scientific_evidence=passed,
    )


def qualified_warpx_profile(
    record: WarpXPhysicsQualificationRecord,
    *,
    runner_kind: WarpXRunnerKind = WarpXRunnerKind.LOCAL_CPU,
) -> WarpXExecutionProfile:
    if not record.passed:
        raise ValueError("a failed physics qualification cannot create a profile")
    qualification_hash = warpx_physics_qualification_hash(record)
    return WarpXExecutionProfile(
        profile_id=f"warpx_qualified_{qualification_hash[:16]}",
        runner_kind=runner_kind,
        warpx_version=record.compile_qualification.expected_warpx_version,
        qualification_hash=qualification_hash,
        qualified_for_scientific_evidence=True,
    )


def _distribution_components(
    case_name: str, physical: WarpXPhysicalConfig
) -> tuple[tuple[float, float, float], ...]:
    if case_name == "unit_maxwellian_reference":
        return ((1.0, 0.0, 1.0),)
    candidate = physical.candidate
    return tuple(
        (component.weight, component.drift, component.sigma)
        for component in candidate.distribution().components
    )


def _picmi_script(
    case_name: Literal["unit_maxwellian_reference", "symmetric_mixture_candidate"],
    physical: WarpXPhysicalConfig,
    numerical: WarpXNumericalConfig,
) -> str:
    """Render a fixed PICMI program containing validated numeric literals only."""

    omega_pe = physical.plasma_frequency_rad_s
    dt_s = numerical.time_step_omega_pe / omega_pe
    components = _distribution_components(case_name, physical)
    ppc = numerical.electron_macroparticles_per_cell // len(components)
    component_rows = _canonical_json(
        [
            {
                "density": weight * physical.reference_density_m3,
                "drift": drift * physical.velocity_unit_m_s,
                "sigma": sigma * physical.velocity_unit_m_s,
            }
            for weight, drift, sigma in components
        ]
    )
    return f'''#!/usr/bin/env python3
"""Generated from a typed source specification; edit that specification, not this file."""

import argparse
from pywarpx import picmi

CASE_NAME = {case_name!r}
COMPONENTS = {component_rows}

grid = picmi.Cartesian1DGrid(
    number_of_cells=[{numerical.grid_cells}],
    lower_bound=[0.0],
    upper_bound=[{physical.domain_length_m!r}],
    lower_boundary_conditions=["periodic"],
    upper_boundary_conditions=["periodic"],
    lower_boundary_conditions_particles=["periodic"],
    upper_boundary_conditions_particles=["periodic"],
    warpx_max_grid_size={min(64, numerical.grid_cells)},
)
solver = picmi.ElectrostaticSolver(
    grid=grid,
    required_precision={numerical.poisson_relative_tolerance!r},
    maximum_iterations={numerical.poisson_max_iterations},
)
simulation = picmi.Simulation(
    solver=solver,
    time_step_size={dt_s!r},
    max_steps={numerical.max_steps},
    particle_shape=2,
    verbose=1,
    warpx_random_seed={numerical.random_seed},
    warpx_serialize_initial_conditions=True,
    warpx_used_inputs_file="warpx_used_inputs",
)

electrons = []
for index, component in enumerate(COMPONENTS):
    distribution = picmi.AnalyticDistribution(
        density_expression=(
            f"{{component['density']}}*(1+{physical.perturbation_amplitude!r}*"
            f"cos({physical.wavenumber_m_inverse!r}*z))"
        ),
        directed_velocity=[0.0, 0.0, component["drift"]],
        rms_velocity=[0.0, 0.0, component["sigma"]],
    )
    species = picmi.Species(
        particle_type="electron",
        name=f"electrons_{{index}}",
        initial_distribution=distribution,
    )
    electrons.append(species)
    simulation.add_species(
        species,
        layout=picmi.GriddedLayout(
            grid=grid,
            n_macroparticle_per_cell=[{ppc}],
        ),
    )

ions = picmi.Species(
    particle_type="proton",
    name="immobile_ions",
    initial_distribution=picmi.UniformDistribution(
        density={physical.reference_density_m3!r},
        directed_velocity=[0.0, 0.0, 0.0],
    ),
    warpx_do_not_push=True,
)
simulation.add_species(
    ions,
    layout=picmi.GriddedLayout(
        grid=grid,
        n_macroparticle_per_cell=[{numerical.ion_macroparticles_per_cell}],
    ),
)

simulation.add_diagnostic(
    picmi.FieldDiagnostic(
        name="fields",
        grid=grid,
        period={numerical.diagnostic_interval_steps},
        data_list=["E", "rho"],
        warpx_format="openpmd",
        warpx_openpmd_backend="h5",
    )
)
simulation.add_diagnostic(
    picmi.ParticleDiagnostic(
        name="particles",
        period={numerical.max_steps},
        species=electrons,
        data_list=["weighting", "momentum", "position"],
        warpx_format="openpmd",
        warpx_openpmd_backend="h5",
    )
)
simulation.add_diagnostic(
    picmi.ReducedDiagnostic(diag_type="FieldEnergy", name="field_energy", period=1)
)
simulation.add_diagnostic(
    picmi.ReducedDiagnostic(diag_type="ParticleEnergy", name="particle_energy", period=1)
)

parser = argparse.ArgumentParser()
parser.add_argument("--compile-only", action="store_true")
arguments = parser.parse_args()
if arguments.compile_only:
    simulation.write_input_file(file_name="inputs")
else:
    simulation.step()
'''


def build_warpx_experiment(
    candidate: SymmetricMixtureCandidate | None = None,
    *,
    physical: WarpXPhysicalConfig | None = None,
    numerical: WarpXNumericalConfig | None = None,
    experiment_id: str = "experiment_warpx_moment_sufficiency_v1",
) -> ExperimentSpec:
    chosen = candidate or (
        physical.candidate
        if physical
        else SymmetricMixtureCandidate(inner_pair_weight=0.5, inner_drift=0.95, outer_drift=0.95)
    )
    base_physical = physical or WarpXPhysicalConfig(
        inner_pair_weight=chosen.inner_pair_weight,
        inner_drift=chosen.inner_drift,
        outer_drift=chosen.outer_drift,
    )
    if base_physical.candidate != chosen:
        raise ValueError("candidate and physical configuration disagree")
    numerical = numerical or WarpXNumericalConfig()
    return ExperimentSpec(
        id=experiment_id,
        hypothesis_ids=("hypothesis_low_moments_sufficient_for_stability",),
        action_type=WARPX_ACTION,
        physical_parameters=base_physical.model_dump(mode="json"),
        numerical_parameters=numerical.model_dump(mode="json"),
        required_diagnostics=WARPX_REQUIRED_DIAGNOSTICS,
        predictions={
            "sufficiency": "matched distributions have equal normalized growth rate",
            "counterexample": "matched distributions differ in normalized growth rate",
        },
        falsification_condition=(
            "both cases pass numerical gates and normalized growth rates differ by more than "
            f"{numerical.outcome_tolerance_omega_pe}"
        ),
    )


class SubprocessWarpXScheduler:
    """Durable local runner contract used by qualification and site wrappers.

    The configured command receives ``--package``, ``--result`` and
    ``--work-directory``.  It must write one ``WarpXPairSummary`` JSON object.
    The scheduler is synchronous for now, but job identity and state are stored
    on disk so controller restarts reattach instead of creating a second run.
    """

    def __init__(
        self,
        *,
        work_root: Path,
        command: tuple[str, ...],
        profile: WarpXExecutionProfile,
        timeout_seconds: float = 3600.0,
    ) -> None:
        if not command:
            raise ValueError("runner command cannot be empty")
        self.work_root = Path(work_root).resolve()
        self.command = command
        self.profile = profile
        self.timeout_seconds = timeout_seconds

    def _job_id(self, run: RunPackage, idempotency_key: str) -> str:
        identity = _sha256_text(f"{run.package_hash}:{idempotency_key}")
        return f"warpx-{identity[:20]}"

    def _job_dir(self, job_id: str) -> Path:
        return self.work_root / job_id

    @staticmethod
    def _archive_interrupted_outputs(job_dir: Path) -> None:
        """Preserve partial outputs before replaying a controller-orphaned job."""

        for name in ("execution", "pair_summary.json", "pair_summary.json.tmp"):
            source = job_dir / name
            if not source.exists():
                continue
            ordinal = 1
            while (job_dir / f"interrupted_{ordinal}_{name}").exists():
                ordinal += 1
            source.rename(job_dir / f"interrupted_{ordinal}_{name}")

    def _commit_summary(
        self,
        *,
        job_id: str,
        run: RunPackage,
        summary: WarpXPairSummary,
        raw_path: Path,
        status_path: Path,
    ) -> None:
        result_payload = {
            "experiment_id": run.experiment_id,
            "run_package_hash": run.package_hash,
            "physical": run.payload["physical"],
            "numerical": run.payload["numerical"],
            "execution_profile": self.profile.model_dump(mode="json"),
            "pair_summary": summary.model_dump(mode="json"),
        }
        result_hash = _sha256_text(_canonical_json(result_payload))
        raw = RawResult(
            job_id=job_id,
            payload=result_payload,
            artifact_hashes=(result_hash,),
        )
        raw_path.write_text(raw.model_dump_json(indent=2) + "\n")
        status_path.write_text(
            json.dumps(
                {
                    "state": JobState.COMPLETED.value,
                    "package_hash": run.package_hash,
                    "detail": "runner produced a schema-valid pair summary",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def submit(self, run: RunPackage, *, idempotency_key: str) -> JobReference:
        job_id = self._job_id(run, idempotency_key)
        job_dir = self._job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        status_path = job_dir / "status.json"
        raw_path = job_dir / "raw_result.json"
        result_path = job_dir / "pair_summary.json"
        lock_path = job_dir / "dispatch.lock"
        with lock_path.open("a+") as dispatch_lock:
            # The runner inherits this descriptor. After an accidental
            # controller stop, another controller waits for the still-running
            # child, then commits its completed result or safely replays it.
            fcntl.flock(dispatch_lock.fileno(), fcntl.LOCK_EX)
            if status_path.exists():
                status = json.loads(status_path.read_text())
                if status["package_hash"] != run.package_hash:
                    raise ValueError("stored job has a different run-package hash")
                if status["state"] in {JobState.COMPLETED.value, JobState.FAILED.value}:
                    return JobReference(
                        job_id=job_id,
                        experiment_id=run.experiment_id,
                        idempotency_key=idempotency_key,
                    )
                if result_path.exists():
                    try:
                        orphaned_summary = WarpXPairSummary.model_validate_json(
                            result_path.read_text()
                        )
                    except ValueError:
                        pass
                    else:
                        self._commit_summary(
                            job_id=job_id,
                            run=run,
                            summary=orphaned_summary,
                            raw_path=raw_path,
                            status_path=status_path,
                        )
                        return JobReference(
                            job_id=job_id,
                            experiment_id=run.experiment_id,
                            idempotency_key=idempotency_key,
                        )
                self._archive_interrupted_outputs(job_dir)

            package_path = job_dir / "run_package.json"
            package_path.write_text(run.model_dump_json(indent=2) + "\n")
            status_path.write_text(
                json.dumps(
                    {
                        "state": JobState.RUNNING.value,
                        "package_hash": run.package_hash,
                        "detail": "local subprocess owns the durable dispatch lock",
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            command = (
                *self.command,
                "--package",
                str(package_path),
                "--result",
                str(result_path),
                "--work-directory",
                str(job_dir),
            )
            try:
                completed = subprocess.run(
                    command,
                    cwd=job_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    pass_fds=(dispatch_lock.fileno(),),
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                detail = f"{type(error).__name__}: {error}"
                status_path.write_text(
                    json.dumps(
                        {
                            "state": JobState.FAILED.value,
                            "package_hash": run.package_hash,
                            "detail": detail,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                )
            else:
                if completed.returncode != 0 or not result_path.exists():
                    detail = (
                        f"runner exit={completed.returncode}; stderr={completed.stderr[-4000:]}"
                    )
                    status_path.write_text(
                        json.dumps(
                            {
                                "state": JobState.FAILED.value,
                                "package_hash": run.package_hash,
                                "detail": detail,
                            },
                            indent=2,
                            sort_keys=True,
                        )
                        + "\n"
                    )
                else:
                    try:
                        summary = WarpXPairSummary.model_validate_json(result_path.read_text())
                    except ValueError as error:
                        status_path.write_text(
                            json.dumps(
                                {
                                    "state": JobState.FAILED.value,
                                    "package_hash": run.package_hash,
                                    "detail": f"runner result failed schema validation: {error}",
                                },
                                indent=2,
                                sort_keys=True,
                            )
                            + "\n"
                        )
                    else:
                        self._commit_summary(
                            job_id=job_id,
                            run=run,
                            summary=summary,
                            raw_path=raw_path,
                            status_path=status_path,
                        )
        return JobReference(
            job_id=job_id,
            experiment_id=run.experiment_id,
            idempotency_key=idempotency_key,
        )

    def monitor(self, job: JobReference) -> JobStatus:
        status_path = self._job_dir(job.job_id) / "status.json"
        if not status_path.exists():
            return JobStatus(job_id=job.job_id, state=JobState.UNKNOWN)
        payload = json.loads(status_path.read_text())
        return JobStatus(
            job_id=job.job_id,
            state=JobState(payload["state"]),
            detail=str(payload.get("detail", "")),
        )

    def retrieve(self, job: JobReference) -> RawResult:
        path = self._job_dir(job.job_id) / "raw_result.json"
        if not path.exists():
            raise LookupError(f"WarpX job {job.job_id} has no completed result")
        result = RawResult.model_validate_json(path.read_text())
        if result.job_id != job.job_id or result.payload.get("experiment_id") != job.experiment_id:
            raise ValueError("stored WarpX result identity does not match the job reference")
        return result

    def cancel(self, job: JobReference) -> JobStatus:
        status = self.monitor(job)
        if status.state in {JobState.COMPLETED, JobState.FAILED, JobState.UNKNOWN}:
            return status
        return JobStatus(
            job_id=job.job_id,
            state=JobState.UNKNOWN,
            detail="the synchronous local runner cannot be safely cancelled cross-process",
        )


class WarpXAdapter:
    _PHYSICAL_KEYS = set(WarpXPhysicalConfig.model_fields)
    _NUMERICAL_KEYS = set(WarpXNumericalConfig.model_fields)

    def __init__(
        self,
        scheduler: SubprocessWarpXScheduler,
        *,
        physics_qualification: WarpXPhysicsQualificationRecord | None = None,
    ) -> None:
        self.scheduler = scheduler
        self.physics_qualification = physics_qualification
        if scheduler.profile.qualified_for_scientific_evidence:
            if physics_qualification is None or not physics_qualification.passed:
                raise ValueError("a qualified execution profile requires its passing record")
            if scheduler.profile.qualification_hash != warpx_physics_qualification_hash(
                physics_qualification
            ):
                raise ValueError("execution profile qualification hash does not match its record")
        elif physics_qualification is not None:
            raise ValueError("an unqualified execution profile cannot carry a physics record")

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            adapter_name="warpx_picmi",
            adapter_version=WARPX_ADAPTER_VERSION,
            supported_actions=(WARPX_ACTION,),
            supported_models=(WARPX_MODEL,),
            supported_diagnostics=WARPX_REQUIRED_DIAGNOSTICS,
            supported_coordinates=("density", "mean_velocity", "variance"),
            supported_observable_kinds=("effective_fundamental_growth_rate",),
            supports_checkpoint=True,
            deterministic=False,
        )

    def _configs(
        self, experiment: ExperimentSpec
    ) -> tuple[WarpXPhysicalConfig, WarpXNumericalConfig]:
        return (
            WarpXPhysicalConfig.model_validate(experiment.physical_parameters),
            WarpXNumericalConfig.model_validate(experiment.numerical_parameters),
        )

    def validate(self, experiment: ExperimentSpec) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        if experiment.action_type != WARPX_ACTION:
            errors.append("unsupported action_type")
        unknown_physical = set(experiment.physical_parameters) - self._PHYSICAL_KEYS
        unknown_numerical = set(experiment.numerical_parameters) - self._NUMERICAL_KEYS
        if unknown_physical:
            errors.append(f"unknown physical parameters: {sorted(unknown_physical)}")
        if unknown_numerical:
            errors.append(f"unknown numerical parameters: {sorted(unknown_numerical)}")
        missing = set(WARPX_REQUIRED_DIAGNOSTICS) - set(experiment.required_diagnostics)
        extra = set(experiment.required_diagnostics) - set(WARPX_REQUIRED_DIAGNOSTICS)
        if missing:
            errors.append(f"missing required diagnostics: {sorted(missing)}")
        if extra:
            errors.append(f"unsupported diagnostics: {sorted(extra)}")
        if not errors:
            try:
                physical, numerical = self._configs(experiment)
            except ValueError as error:
                errors.append(f"invalid WarpX configuration: {error}")
            else:
                if self.physics_qualification is not None:
                    errors.extend(
                        self.physics_qualification.scope.validation_errors(
                            physical,
                            numerical,
                        )
                    )
                if numerical.grid_cells * numerical.electron_macroparticles_per_cell > 1e7:
                    warnings.append("the paired run initializes more than ten million electrons")
                cell_size = physical.domain_length_m / numerical.grid_cells
                thermal_crossing = physical.velocity_unit_m_s * (
                    numerical.time_step_omega_pe / physical.plasma_frequency_rad_s
                )
                if thermal_crossing / cell_size > 0.5:
                    warnings.append("thermal particles cross more than half a cell per step")
        return ValidationReport(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))

    def estimate_cost(self, experiment: ExperimentSpec) -> CostEstimate:
        report = self.validate(experiment)
        if not report.valid:
            raise ValueError("; ".join(report.errors))
        _, numerical = self._configs(experiment)
        particles_per_case = numerical.grid_cells * (
            numerical.electron_macroparticles_per_cell + numerical.ion_macroparticles_per_cell
        )
        work = 2 * particles_per_case * numerical.max_steps
        snapshots = 2 * (numerical.max_steps // numerical.diagnostic_interval_steps + 1)
        return CostEstimate(
            compute_units=work / 100_000_000,
            wall_seconds=work / 5_000_000,
            storage_bytes=snapshots * numerical.grid_cells * 512,
        )

    def compile_input(self, experiment: ExperimentSpec) -> RunPackage:
        report = self.validate(experiment)
        if not report.valid:
            raise ValueError("; ".join(report.errors))
        physical, numerical = self._configs(experiment)
        cases = tuple(
            WarpXCompiledCase(
                case_name=case_name,
                script=script.strip(),
                script_hash=_sha256_text(script.strip()),
            )
            for case_name in (
                "unit_maxwellian_reference",
                "symmetric_mixture_candidate",
            )
            for script in (_picmi_script(case_name, physical, numerical),)
        )
        payload = {
            "contract_version": WARPX_CONTRACT_VERSION,
            "compiler": "restricted_picmi_template_v2",
            "expected_warpx_version": self.scheduler.profile.warpx_version,
            "physical": physical.model_dump(mode="json"),
            "numerical": numerical.model_dump(mode="json"),
            "cases": [case.model_dump(mode="json") for case in cases],
        }
        return RunPackage(
            experiment_id=experiment.id,
            adapter_name="warpx_picmi",
            payload=payload,
            package_hash=_sha256_text(_canonical_json(payload)),
        )

    def submit(self, run: RunPackage, *, idempotency_key: str) -> JobReference:
        if run.adapter_name != "warpx_picmi":
            raise ValueError("run package belongs to a different adapter")
        return self.scheduler.submit(run, idempotency_key=idempotency_key)

    def monitor(self, job: JobReference) -> JobStatus:
        return self.scheduler.monitor(job)

    def retrieve(self, job: JobReference) -> RawResult:
        return self.scheduler.retrieve(job)

    def normalize(self, result: RawResult) -> NormalizedResult:
        payload = result.payload
        expected_artifact_hash = _sha256_text(_canonical_json(payload))
        if result.artifact_hashes != (expected_artifact_hash,):
            raise ValueError("WarpX raw-result artifact hash does not match its payload")
        physical = WarpXPhysicalConfig.model_validate(payload["physical"])
        numerical = WarpXNumericalConfig.model_validate(payload["numerical"])
        profile = WarpXExecutionProfile.model_validate(payload["execution_profile"])
        summary = WarpXPairSummary.model_validate(payload["pair_summary"])
        reference = summary.reference
        candidate = summary.candidate

        def expected_classification(case: WarpXCaseSummary) -> str:
            if case.amplitude_ratio < numerical.damped_ratio_threshold:
                return "damped"
            if case.amplitude_ratio > numerical.unstable_ratio_threshold:
                return "unstable"
            return "ambiguous"

        case_gates = {
            case.case_name: {
                "solver_converged": case.solver_converged,
                "finite_values": case.finite_values,
                "diagnostic_samples": (
                    case.diagnostic_samples >= numerical.minimum_diagnostic_samples
                ),
                "energy_drift": (
                    case.relative_energy_drift <= numerical.maximum_relative_energy_drift
                ),
                "gauss_residual": (
                    case.relative_gauss_residual <= numerical.maximum_relative_gauss_residual
                ),
                "charge_imbalance": (
                    case.relative_charge_imbalance <= numerical.maximum_relative_charge_imbalance
                ),
                "early_window_samples": (
                    case.early_window_sample_count >= numerical.minimum_window_samples
                ),
                "late_window_samples": (
                    case.late_window_sample_count >= numerical.minimum_window_samples
                ),
                "classification_consistent": (case.classification == expected_classification(case)),
            }
            for case in (reference, candidate)
        }
        moments_match = all(
            difference <= numerical.moment_tolerance
            for difference in (
                abs(reference.initial_density_normalized - candidate.initial_density_normalized),
                abs(
                    reference.initial_mean_velocity_normalized
                    - candidate.initial_mean_velocity_normalized
                ),
                abs(reference.initial_variance_normalized - candidate.initial_variance_normalized),
                abs(reference.initial_density_normalized - 1.0),
                abs(reference.initial_mean_velocity_normalized),
                abs(reference.initial_variance_normalized - 1.0),
                abs(candidate.initial_density_normalized - 1.0),
                abs(candidate.initial_mean_velocity_normalized),
                abs(candidate.initial_variance_normalized - 1.0),
            )
        )
        runtime_matches = _warpx_versions_equivalent(
            summary.runtime_warpx_version,
            profile.warpx_version,
        )
        numerical_validity = (
            all(all(gates.values()) for gates in case_gates.values())
            and moments_match
            and runtime_matches
        )
        separation = abs(
            candidate.effective_growth_rate_omega_pe - reference.effective_growth_rate_omega_pe
        )
        opposite = {reference.classification, candidate.classification} == {
            "damped",
            "unstable",
        }
        raw_witness = (
            numerical_validity and opposite and separation > numerical.outcome_tolerance_omega_pe
        )
        eligible = numerical_validity and profile.qualified_for_scientific_evidence
        diagnostics = {
            "contract_version": WARPX_CONTRACT_VERSION,
            "run_package_hash": str(payload["run_package_hash"]),
            "physical": physical.model_dump(mode="json"),
            "numerical": numerical.model_dump(mode="json"),
            "execution_profile": profile.model_dump(mode="json"),
            "pair_summary": summary.model_dump(mode="json"),
            "validity_gates": {
                "cases": case_gates,
                "moments_match": moments_match,
                "runtime_version_matches_profile": runtime_matches,
                "numerical_validity_passed": numerical_validity,
            },
            "raw_witness_satisfies_predicate": raw_witness,
            "scientific_evidence_eligible": eligible,
        }
        return NormalizedResult(
            experiment_id=str(payload["experiment_id"]),
            observables={
                "maxwellian_growth_rate": reference.effective_growth_rate_omega_pe,
                "two_stream_growth_rate": candidate.effective_growth_rate_omega_pe,
                "moments_match": moments_match,
                "outcome_separation": separation,
                "numerical_validity_passed": numerical_validity,
                "hypothesis_falsified": eligible and raw_witness,
            },
            diagnostics=diagnostics,
            artifact_hashes=result.artifact_hashes,
        )

    def cancel(self, job: JobReference) -> JobStatus:
        return self.scheduler.cancel(job)


def qualify_warpx_picmi_compiler(
    run: RunPackage,
    *,
    python_executable: Path,
    work_directory: Path,
    profile_id: str = "warpx_cpu_26_07_compile",
) -> WarpXQualificationRecord:
    """Import WarpX and compile both generated PICMI cases without evolving them."""

    expected_version = str(run.payload["expected_warpx_version"])
    python_executable = python_executable.resolve()
    work_directory = work_directory.resolve()
    checks: dict[str, bool] = {}
    compiled: dict[str, str] = {}
    observed_version: str | None = None
    work_directory.mkdir(parents=True, exist_ok=True)
    try:
        version = subprocess.run(
            [
                str(python_executable),
                "-c",
                "import importlib.metadata; print(importlib.metadata.version('pywarpx'))",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        checks["runtime_import"] = False
        checks["runtime_version"] = False
    else:
        observed_version = version.stdout.strip() if version.returncode == 0 else None
        checks["runtime_import"] = version.returncode == 0
        checks["runtime_version"] = bool(observed_version) and _warpx_versions_equivalent(
            observed_version,
            expected_version,
        )

    for case_payload in run.payload["cases"]:
        case = WarpXCompiledCase.model_validate(case_payload)
        case_dir = work_directory / case.case_name
        case_dir.mkdir(parents=True, exist_ok=True)
        script_path = case_dir / "run_picmi.py"
        script_path.write_text(case.script)
        try:
            execution = subprocess.run(
                [str(python_executable), str(script_path), "--compile-only"],
                cwd=case_dir,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            checks[f"compile_{case.case_name}"] = False
            continue
        input_path = case_dir / "inputs"
        success = execution.returncode == 0 and input_path.exists()
        checks[f"compile_{case.case_name}"] = success
        if success:
            compiled[case.case_name] = hashlib.sha256(input_path.read_bytes()).hexdigest()

    return WarpXQualificationRecord(
        profile_id=profile_id,
        package_hash=run.package_hash,
        expected_warpx_version=expected_version,
        observed_warpx_version=observed_version,
        compiled_case_hashes=compiled,
        checks=checks,
        passed=bool(checks) and all(checks.values()),
    )
