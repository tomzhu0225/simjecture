from __future__ import annotations

import pytest

from conjecture_solver.models import AttemptOutcome
from conjecture_solver.parameters import (
    NumericalDiagnostics,
    NumericalGate,
    ParameterDefinition,
    ParameterRole,
    ParameterScale,
    ParameterSpace,
    PilotStage,
    RecoveryAction,
    ReferenceQualification,
    RefinementDirection,
    assess_numerics,
    discovery_design,
    initial_smoke_plan,
    qualification_plan,
    qualify_reference,
    refined_plan,
)


def parameter_space(*, qualified: bool = False) -> ParameterSpace:
    return ParameterSpace(
        parameters=(
            ParameterDefinition(
                name="drift_speed",
                role=ParameterRole.PHYSICAL,
                scale=ParameterScale.LINEAR,
                lower=0.2,
                upper=1.0,
                reference=0.6,
            ),
            ParameterDefinition(
                name="grid_cells",
                role=ParameterRole.NUMERICAL,
                scale=ParameterScale.INTEGER,
                lower=32,
                upper=512,
                reference=128,
                refinement_direction=RefinementDirection.INCREASE,
            ),
            ParameterDefinition(
                name="time_step",
                role=ParameterRole.NUMERICAL,
                scale=ParameterScale.LOG,
                lower=0.00625,
                upper=0.1,
                reference=0.05,
                refinement_direction=RefinementDirection.DECREASE,
            ),
        ),
        reference_qualification=(
            ReferenceQualification(
                smoke_attempt_id="attempt_smoke",
                qualification_attempt_id="attempt_qualification",
                diagnostics_hashes=("a" * 64, "b" * 64),
            )
            if qualified
            else None
        ),
        max_autonomous_failures=2,
    )


def passing_diagnostics() -> NumericalDiagnostics:
    return NumericalDiagnostics(
        solver_converged=True,
        residual=1e-10,
        nan_count=0,
        relative_energy_drift=0.001,
        boundary_contamination=0.001,
        numerical_damping_fraction=0.01,
    )


def test_unqualified_reference_allows_pilots_but_blocks_discovery() -> None:
    space = parameter_space()
    smoke = initial_smoke_plan(space)
    qualification = qualification_plan(space, smoke_passed=True)

    assert smoke.stage is PilotStage.SMOKE and not smoke.evidence_candidate
    assert qualification.stage is PilotStage.QUALIFICATION
    assert not qualification.evidence_candidate
    with pytest.raises(ValueError, match="blocked"):
        discovery_design(space, count=3, design_seed=7)


def test_discovery_design_is_seeded_bounded_and_starts_at_reference() -> None:
    space = parameter_space(qualified=True)
    first = discovery_design(space, count=4, design_seed=7)
    replay = discovery_design(space, count=4, design_seed=7)

    assert first == replay
    assert first[0].parameter_values == space.reference_values()
    assert all(plan.evidence_candidate for plan in first)
    assert len({plan.parameter_values["drift_speed"] for plan in first}) == 4
    for plan in first:
        space.validate_values(plan.parameter_values)


def test_passing_pilots_create_hashed_reference_qualification() -> None:
    space = parameter_space()
    smoke = initial_smoke_plan(space)
    qualification = qualification_plan(space, smoke_passed=True)
    diagnostics = passing_diagnostics()
    smoke_assessment = assess_numerics(smoke, diagnostics, NumericalGate())
    qualification_assessment = assess_numerics(qualification, diagnostics, NumericalGate())

    record = qualify_reference(
        smoke_attempt_id="attempt_smoke_real",
        smoke_plan=smoke,
        smoke_diagnostics=diagnostics,
        smoke_assessment=smoke_assessment,
        qualification_attempt_id="attempt_qualification_real",
        qualification_run_plan=qualification,
        qualification_diagnostics=diagnostics,
        qualification_assessment=qualification_assessment,
    )

    assert all(len(value) == 64 for value in record.diagnostics_hashes)
    qualified = ParameterSpace.model_validate(
        {
            **space.model_dump(mode="json"),
            "reference_qualification": record.model_dump(mode="json"),
        }
    )
    assert discovery_design(qualified, count=1, design_seed=0)


def test_nonconvergence_and_overdamping_are_not_physical_evidence() -> None:
    plan = discovery_design(parameter_space(qualified=True), count=1, design_seed=4)[0]
    diagnostics = passing_diagnostics().model_copy(
        update={
            "solver_converged": False,
            "residual": 0.2,
            "numerical_damping_fraction": 0.4,
        }
    )
    assessment = assess_numerics(plan, diagnostics, NumericalGate())

    assert assessment.outcome is AttemptOutcome.NUMERICAL_FAILURE
    assert not assessment.evidence_eligible
    assert assessment.recovery_action is RecoveryAction.RETRY_REFINED
    assert any("damping" in reason for reason in assessment.reasons)


def test_numerical_failure_produces_bounded_convergence_plan() -> None:
    space = parameter_space(qualified=True)
    failed = discovery_design(space, count=1, design_seed=4)[0]
    retry = refined_plan(space, failed)

    assert retry is not None
    assert retry.stage is PilotStage.CONVERGENCE
    assert not retry.evidence_candidate
    assert retry.parameter_values["grid_cells"] == 256
    assert retry.parameter_values["time_step"] == pytest.approx(0.025)
    assert retry.parameter_values["drift_speed"] == failed.parameter_values["drift_speed"]


def test_passing_pilot_remains_non_evidentiary() -> None:
    plan = initial_smoke_plan(parameter_space())
    assessment = assess_numerics(plan, passing_diagnostics(), NumericalGate())
    assert assessment.outcome is AttemptOutcome.SUCCESS
    assert not assessment.evidence_eligible
    assert "non-evidentiary" in assessment.reasons[0]


def test_passing_discovery_run_can_become_evidence() -> None:
    plan = discovery_design(parameter_space(qualified=True), count=1, design_seed=4)[0]
    assessment = assess_numerics(plan, passing_diagnostics(), NumericalGate())
    assert assessment.outcome is AttemptOutcome.SUCCESS
    assert assessment.evidence_eligible


def test_retry_budget_escalates_repeated_failure_to_human_review() -> None:
    plan = discovery_design(parameter_space(qualified=True), count=1, design_seed=4)[0]
    diagnostics = passing_diagnostics().model_copy(update={"solver_converged": False})
    assessment = assess_numerics(
        plan,
        diagnostics,
        NumericalGate(),
        autonomous_failures_so_far=2,
        max_autonomous_failures=2,
    )
    assert assessment.recovery_action is RecoveryAction.HUMAN_REVIEW


def test_validity_failure_is_distinct_and_requires_review() -> None:
    plan = discovery_design(parameter_space(qualified=True), count=1, design_seed=4)[0]
    diagnostics = passing_diagnostics().model_copy(
        update={"relative_energy_drift": 0.2, "boundary_contamination": 0.3}
    )
    assessment = assess_numerics(plan, diagnostics, NumericalGate())
    assert assessment.outcome is AttemptOutcome.VALIDITY_FAILURE
    assert not assessment.evidence_eligible
    assert assessment.recovery_action is RecoveryAction.HUMAN_REVIEW


def test_refinement_stops_at_declared_numerical_bounds() -> None:
    space = parameter_space(qualified=True)
    failed = discovery_design(space, count=1, design_seed=4)[0]
    bounded = failed.model_copy(
        update={
            "parameter_values": {
                **failed.parameter_values,
                "grid_cells": 512.0,
                "time_step": 0.00625,
            }
        }
    )
    assert refined_plan(space, bounded) is None


def test_infrastructure_failure_is_distinct_from_numerical_failure() -> None:
    plan = initial_smoke_plan(parameter_space())
    diagnostics = passing_diagnostics().model_copy(
        update={"infrastructure_error": "scheduler allocation expired"}
    )
    assessment = assess_numerics(plan, diagnostics, NumericalGate())
    assert assessment.outcome is AttemptOutcome.INFRASTRUCTURE_FAILURE
    assert assessment.recovery_action is RecoveryAction.RETRY_REFERENCE
