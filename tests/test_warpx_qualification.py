from __future__ import annotations

import hashlib
import math

from conjecture_solver.adapters.base import NormalizedResult
from conjecture_solver.adapters.warpx import (
    WarpXCaseSummary,
    WarpXExecutionProfile,
    WarpXNumericalConfig,
    WarpXPairSummary,
    WarpXPhysicalConfig,
    WarpXQualificationRecord,
    WarpXQualifiedScope,
    WarpXRunnerKind,
    build_warpx_physics_qualification,
    qualified_warpx_profile,
)
from conjecture_solver.warpx_confirmation import (
    WarpXConfirmationDisposition,
    build_warpx_confirmation_report,
    default_warpx_confirmation_design,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def case_summary(
    *,
    name: str,
    growth: float,
    manifest_label: str,
) -> WarpXCaseSummary:
    ratio = math.exp(14.0 * growth)
    return WarpXCaseSummary(
        case_name=name,
        solver_converged=True,
        finite_values=True,
        diagnostic_samples=201,
        effective_growth_rate_omega_pe=growth,
        early_rms_amplitude_v_m=1000.0,
        late_rms_amplitude_v_m=1000.0 * ratio,
        amplitude_ratio=ratio,
        early_window_sample_count=41,
        late_window_sample_count=41,
        classification="damped" if growth < 0 else "unstable",
        fundamental_amplitude_initial_v_m=1000.0,
        fundamental_amplitude_final_v_m=1000.0 * ratio,
        initial_density_normalized=1.0,
        initial_mean_velocity_normalized=0.0,
        initial_variance_normalized=1.0,
        relative_energy_drift=1.0e-4,
        relative_gauss_residual=1.0e-8,
        relative_charge_imbalance=1.0e-10,
        diagnostic_manifest_hash=digest(manifest_label),
    )


def normalized_result(
    *,
    seed: int,
    grid_cells: int,
    time_step: float,
    reference_growth: float,
    candidate_growth: float,
    profile: WarpXExecutionProfile,
    label: str,
) -> NormalizedResult:
    numerical = WarpXNumericalConfig(
        grid_cells=grid_cells,
        electron_macroparticles_per_cell=512,
        time_step_omega_pe=time_step,
        diagnostic_interval_steps=2 if time_step == 0.05 else 4,
        random_seed=seed,
    )
    pair = WarpXPairSummary(
        runtime_warpx_version="26.7",
        reference=case_summary(
            name="unit_maxwellian_reference",
            growth=reference_growth,
            manifest_label=f"{label}:reference",
        ),
        candidate=case_summary(
            name="symmetric_mixture_candidate",
            growth=candidate_growth,
            manifest_label=f"{label}:candidate",
        ),
    )
    package_hash = digest(f"{label}:package")
    eligible = profile.qualified_for_scientific_evidence
    return NormalizedResult(
        experiment_id=f"experiment_{label}",
        observables={
            "maxwellian_growth_rate": reference_growth,
            "two_stream_growth_rate": candidate_growth,
            "moments_match": True,
            "outcome_separation": candidate_growth - reference_growth,
            "numerical_validity_passed": True,
            "hypothesis_falsified": eligible,
        },
        diagnostics={
            "run_package_hash": package_hash,
            "physical": WarpXPhysicalConfig().model_dump(mode="json"),
            "numerical": numerical.model_dump(mode="json"),
            "execution_profile": profile.model_dump(mode="json"),
            "pair_summary": pair.model_dump(mode="json"),
            "validity_gates": {"numerical_validity_passed": True},
            "raw_witness_satisfies_predicate": True,
            "scientific_evidence_eligible": eligible,
        },
        artifact_hashes=(digest(f"{label}:artifact"),),
    )


def passing_qualification():
    profile = WarpXExecutionProfile(
        profile_id="real_calibration",
        runner_kind=WarpXRunnerKind.LOCAL_CPU,
        warpx_version="26.07",
    )
    calibration: list[NormalizedResult] = []
    for resolution, grid, step, reference, candidate in (
        ("coarse", 64, 0.05, -0.07, 0.17),
        ("refined", 128, 0.025, -0.08, 0.165),
    ):
        for seed in (1, 7, 19, 101):
            calibration.append(
                normalized_result(
                    seed=seed,
                    grid_cells=grid,
                    time_step=step,
                    reference_growth=reference - seed * 1.0e-5,
                    candidate_growth=candidate + seed * 1.0e-5,
                    profile=profile,
                    label=f"calibration:{resolution}:{seed}",
                )
            )
    compile_record = WarpXQualificationRecord(
        profile_id="real_compile",
        package_hash=str(calibration[0].diagnostics["run_package_hash"]),
        expected_warpx_version="26.07",
        observed_warpx_version="26.7",
        compiled_case_hashes={
            "unit_maxwellian_reference": digest("compiled:reference"),
            "symmetric_mixture_candidate": digest("compiled:candidate"),
        },
        checks={"runtime": True, "both_cases": True},
        passed=True,
    )
    record = build_warpx_physics_qualification(
        compile_qualification=compile_record,
        calibration_results=calibration,
        scope=WarpXQualifiedScope(physical=WarpXPhysicalConfig()),
        analytic_reference_growth_rate=-0.153,
        analytic_candidate_growth_rate=0.271,
    )
    return record


def test_complete_real_profile_matrix_can_qualify() -> None:
    record = passing_qualification()
    assert record.passed
    assert record.authorizes_scientific_evidence
    assert len(record.calibration_points) == 8
    assert all(record.checks.values())
    assert qualified_warpx_profile(record).qualified_for_scientific_evidence


def test_qualified_scope_rejects_weaker_solver_and_evidence_gates() -> None:
    scope = passing_qualification().scope
    weakened = WarpXNumericalConfig(
        poisson_relative_tolerance=1.0e-6,
        poisson_max_iterations=100,
        minimum_diagnostic_samples=10,
        minimum_window_samples=10,
        outcome_tolerance_omega_pe=0.001,
    )
    errors = scope.validation_errors(WarpXPhysicalConfig(), weakened)
    assert len(errors) == 5
    assert any("Poisson tolerance" in error for error in errors)
    assert any("outcome-separation" in error for error in errors)


def test_contract_fixture_matrix_cannot_qualify() -> None:
    record = passing_qualification()
    fixture_profile = WarpXExecutionProfile(
        profile_id="fixture",
        runner_kind=WarpXRunnerKind.CONTRACT_FIXTURE,
        warpx_version="26.07",
    )
    calibration = [
        normalized_result(
            seed=point.seed,
            grid_cells=point.grid_cells,
            time_step=point.time_step_omega_pe,
            reference_growth=point.reference_growth_rate,
            candidate_growth=point.candidate_growth_rate,
            profile=fixture_profile,
            label=f"fixture:{point.resolution_id}:{point.seed}",
        )
        for point in record.calibration_points
    ]
    failed = build_warpx_physics_qualification(
        compile_qualification=record.compile_qualification.model_copy(
            update={"package_hash": calibration[0].diagnostics["run_package_hash"]}
        ),
        calibration_results=calibration,
        scope=record.scope,
        analytic_reference_growth_rate=record.analytic_reference_growth_rate,
        analytic_candidate_growth_rate=record.analytic_candidate_growth_rate,
    )
    assert not failed.passed
    assert not failed.checks["calibration_runners_are_not_fixtures"]


def test_fresh_qualified_matrix_confirms_without_reusing_calibration() -> None:
    qualification = passing_qualification()
    design = default_warpx_confirmation_design(qualification)
    profile = qualified_warpx_profile(qualification)
    results = tuple(
        normalized_result(
            seed=seed,
            grid_cells=resolution.grid_cells,
            time_step=resolution.time_step_omega_pe,
            reference_growth=-0.075 if resolution.id == "coarse" else -0.083,
            candidate_growth=0.172 if resolution.id == "coarse" else 0.166,
            profile=profile,
            label=f"confirmation:{resolution.id}:{seed}",
        )
        for resolution in design.resolutions
        for seed in design.seeds
    )
    report = build_warpx_confirmation_report(
        design=design,
        qualification=qualification,
        results=results,
    )
    assert report.disposition is WarpXConfirmationDisposition.CONFIRMED
    assert len(report.attempts) == 6
    assert all(attempt.confirmed for attempt in report.attempts)
    assert all(report.checks.values())
