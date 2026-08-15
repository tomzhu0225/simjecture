"""Bounded parameter design and numerical-validity policy."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

import numpy as np
from pydantic import Field, model_validator
from scipy.stats import qmc

from .models import AttemptOutcome, StrictModel


class ParameterRole(StrEnum):
    PHYSICAL = "physical"
    NUMERICAL = "numerical"


class ParameterScale(StrEnum):
    LINEAR = "linear"
    LOG = "log"
    INTEGER = "integer"


class RefinementDirection(StrEnum):
    NONE = "none"
    INCREASE = "increase"
    DECREASE = "decrease"


class PilotStage(StrEnum):
    SMOKE = "smoke"
    QUALIFICATION = "qualification"
    DISCOVERY = "discovery"
    CONVERGENCE = "convergence"


class RecoveryAction(StrEnum):
    ACCEPT = "accept"
    RETRY_REFINED = "retry_refined"
    RETRY_REFERENCE = "retry_reference"
    HUMAN_REVIEW = "human_review"


class ParameterDefinition(StrictModel):
    name: str = Field(min_length=1)
    role: ParameterRole
    scale: ParameterScale
    lower: float
    upper: float
    reference: float
    units: str = "dimensionless"
    refinement_direction: RefinementDirection = RefinementDirection.NONE
    refinement_factor: float = Field(default=2.0, gt=1)

    @model_validator(mode="after")
    def validate_interval(self) -> ParameterDefinition:
        if self.lower > self.upper:
            raise ValueError("parameter lower bound cannot exceed upper bound")
        if not self.lower <= self.reference <= self.upper:
            raise ValueError("parameter reference must lie inside its bounds")
        if self.scale is ParameterScale.LOG and self.lower <= 0:
            raise ValueError("log-scaled parameters require positive bounds")
        if self.scale is ParameterScale.INTEGER and any(
            not float(value).is_integer()
            for value in (self.lower, self.upper, self.reference)
        ):
            raise ValueError("integer parameter bounds and reference must be integral")
        if (
            self.role is ParameterRole.PHYSICAL
            and self.refinement_direction is not RefinementDirection.NONE
        ):
            raise ValueError("numerical refinement cannot change a physical parameter")
        return self

    def map_unit_interval(self, value: float) -> float:
        if not 0 <= value <= 1:
            raise ValueError("unit-interval design value is outside [0, 1]")
        if self.lower == self.upper:
            mapped = self.lower
        elif self.scale is ParameterScale.LOG:
            mapped = float(np.exp(np.log(self.lower) + value * np.log(self.upper / self.lower)))
        else:
            mapped = self.lower + value * (self.upper - self.lower)
        if self.scale is ParameterScale.INTEGER:
            mapped = float(round(mapped))
        return min(self.upper, max(self.lower, mapped))


class ReferenceQualification(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    smoke_attempt_id: str = Field(min_length=1)
    qualification_attempt_id: str = Field(min_length=1)
    diagnostics_hashes: tuple[str, str]

    @model_validator(mode="after")
    def require_distinct_attempts_and_hashes(self) -> ReferenceQualification:
        if self.smoke_attempt_id == self.qualification_attempt_id:
            raise ValueError("smoke and qualification attempts must be distinct")
        if any(
            len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
            for value in self.diagnostics_hashes
        ):
            raise ValueError("qualification diagnostics require lowercase SHA-256 hashes")
        return self


class ParameterSpace(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    parameters: tuple[ParameterDefinition, ...] = Field(min_length=1)
    reference_qualification: ReferenceQualification | None = None
    max_autonomous_failures: int = Field(default=2, ge=0)

    @model_validator(mode="after")
    def unique_names(self) -> ParameterSpace:
        names = [parameter.name for parameter in self.parameters]
        if len(names) != len(set(names)):
            raise ValueError("parameter names must be unique")
        return self

    def reference_values(self) -> dict[str, float]:
        return {parameter.name: parameter.reference for parameter in self.parameters}

    @property
    def reference_qualified(self) -> bool:
        return self.reference_qualification is not None

    def validate_values(self, values: dict[str, float]) -> None:
        expected = {parameter.name for parameter in self.parameters}
        if set(values) != expected:
            raise ValueError("parameter point must provide exactly the declared parameters")
        for parameter in self.parameters:
            value = values[parameter.name]
            if not parameter.lower <= value <= parameter.upper:
                raise ValueError(f"{parameter.name} is outside its declared bounds")
            if parameter.scale is ParameterScale.INTEGER and not float(value).is_integer():
                raise ValueError(f"{parameter.name} must be integral")


class RunPlan(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    stage: PilotStage
    parameter_values: dict[str, float]
    evidence_candidate: bool
    max_steps: int = Field(ge=1)
    design_seed: int = Field(ge=0)
    parent_attempt_id: str | None = None

    @model_validator(mode="after")
    def evidence_requires_discovery_stage(self) -> RunPlan:
        if self.evidence_candidate and self.stage is not PilotStage.DISCOVERY:
            raise ValueError("only a preregistered discovery run may be an evidence candidate")
        return self


def initial_smoke_plan(
    space: ParameterSpace,
    *,
    design_seed: int = 0,
    max_steps: int = 50,
) -> RunPlan:
    return RunPlan(
        stage=PilotStage.SMOKE,
        parameter_values=space.reference_values(),
        evidence_candidate=False,
        max_steps=max_steps,
        design_seed=design_seed,
    )


def qualification_plan(
    space: ParameterSpace,
    *,
    smoke_passed: bool,
    design_seed: int = 0,
    max_steps: int = 1_000,
) -> RunPlan:
    if not smoke_passed:
        raise ValueError("a reference qualification run requires a passing smoke run")
    return RunPlan(
        stage=PilotStage.QUALIFICATION,
        parameter_values=space.reference_values(),
        evidence_candidate=False,
        max_steps=max_steps,
        design_seed=design_seed,
    )


def discovery_design(
    space: ParameterSpace,
    *,
    count: int,
    design_seed: int,
    max_steps: int = 1_000,
) -> tuple[RunPlan, ...]:
    if not space.reference_qualified:
        raise ValueError("discovery is blocked until the reference point is qualified")
    if count < 1:
        raise ValueError("discovery design count must be positive")

    physical = [
        parameter for parameter in space.parameters if parameter.role is ParameterRole.PHYSICAL
    ]
    samples = (
        qmc.LatinHypercube(d=len(physical), seed=design_seed).random(count - 1)
        if physical and count > 1
        else np.empty((0, len(physical)))
    )
    values = [space.reference_values()]
    for sample in samples:
        point = space.reference_values()
        for parameter, unit_value in zip(physical, sample, strict=True):
            point[parameter.name] = parameter.map_unit_interval(float(unit_value))
        space.validate_values(point)
        values.append(point)
    return tuple(
        RunPlan(
            stage=PilotStage.DISCOVERY,
            parameter_values=point,
            evidence_candidate=True,
            max_steps=max_steps,
            design_seed=design_seed,
        )
        for point in values
    )


def refined_plan(
    space: ParameterSpace,
    failed_plan: RunPlan,
    *,
    max_steps: int | None = None,
) -> RunPlan | None:
    space.validate_values(failed_plan.parameter_values)
    values = dict(failed_plan.parameter_values)
    changed = False
    for parameter in space.parameters:
        current = values[parameter.name]
        if parameter.refinement_direction is RefinementDirection.INCREASE:
            candidate = min(parameter.upper, current * parameter.refinement_factor)
        elif parameter.refinement_direction is RefinementDirection.DECREASE:
            candidate = max(parameter.lower, current / parameter.refinement_factor)
        else:
            continue
        if parameter.scale is ParameterScale.INTEGER:
            candidate = float(round(candidate))
        if candidate != current:
            values[parameter.name] = candidate
            changed = True
    if not changed:
        return None
    space.validate_values(values)
    return RunPlan(
        stage=PilotStage.CONVERGENCE,
        parameter_values=values,
        evidence_candidate=False,
        max_steps=max_steps or failed_plan.max_steps,
        design_seed=failed_plan.design_seed,
        parent_attempt_id=failed_plan.parent_attempt_id,
    )


class NumericalDiagnostics(StrictModel):
    solver_converged: bool
    residual: float = Field(ge=0)
    nan_count: int = Field(ge=0)
    relative_energy_drift: float = Field(ge=0)
    boundary_contamination: float = Field(ge=0, le=1)
    numerical_damping_fraction: float = Field(ge=0, le=1)
    infrastructure_error: str | None = None


class NumericalGate(StrictModel):
    maximum_residual: float = Field(default=1e-8, gt=0)
    maximum_relative_energy_drift: float = Field(default=0.01, ge=0)
    maximum_boundary_contamination: float = Field(default=0.01, ge=0, le=1)
    maximum_numerical_damping_fraction: float = Field(default=0.05, ge=0, le=1)


class NumericalAssessment(StrictModel):
    outcome: AttemptOutcome
    evidence_eligible: bool
    reasons: tuple[str, ...]
    recovery_action: RecoveryAction


def assess_numerics(
    plan: RunPlan,
    diagnostics: NumericalDiagnostics,
    gate: NumericalGate,
    *,
    autonomous_failures_so_far: int = 0,
    max_autonomous_failures: int = 2,
) -> NumericalAssessment:
    if diagnostics.infrastructure_error:
        return NumericalAssessment(
            outcome=AttemptOutcome.INFRASTRUCTURE_FAILURE,
            evidence_eligible=False,
            reasons=(diagnostics.infrastructure_error,),
            recovery_action=(
                RecoveryAction.RETRY_REFERENCE
                if autonomous_failures_so_far < max_autonomous_failures
                else RecoveryAction.HUMAN_REVIEW
            ),
        )

    numerical_reasons: list[str] = []
    if not diagnostics.solver_converged:
        numerical_reasons.append("solver did not converge")
    if diagnostics.nan_count:
        numerical_reasons.append("result contains non-finite values")
    if diagnostics.residual > gate.maximum_residual:
        numerical_reasons.append("solver residual exceeds the numerical gate")
    if diagnostics.numerical_damping_fraction > gate.maximum_numerical_damping_fraction:
        numerical_reasons.append("numerical damping exceeds the declared limit")
    if numerical_reasons:
        return NumericalAssessment(
            outcome=AttemptOutcome.NUMERICAL_FAILURE,
            evidence_eligible=False,
            reasons=tuple(numerical_reasons),
            recovery_action=(
                RecoveryAction.RETRY_REFINED
                if autonomous_failures_so_far < max_autonomous_failures
                else RecoveryAction.HUMAN_REVIEW
            ),
        )

    validity_reasons: list[str] = []
    if diagnostics.relative_energy_drift > gate.maximum_relative_energy_drift:
        validity_reasons.append("energy drift exceeds the validity gate")
    if diagnostics.boundary_contamination > gate.maximum_boundary_contamination:
        validity_reasons.append("boundary contamination exceeds the validity gate")
    if validity_reasons:
        return NumericalAssessment(
            outcome=AttemptOutcome.VALIDITY_FAILURE,
            evidence_eligible=False,
            reasons=tuple(validity_reasons),
            recovery_action=RecoveryAction.HUMAN_REVIEW,
        )

    return NumericalAssessment(
        outcome=AttemptOutcome.SUCCESS,
        evidence_eligible=plan.evidence_candidate,
        reasons=(
            "numerical and validity gates passed"
            if plan.evidence_candidate
            else "pilot passed but was preregistered as non-evidentiary"
        ,),
        recovery_action=RecoveryAction.ACCEPT,
    )


def qualify_reference(
    *,
    smoke_attempt_id: str,
    smoke_plan: RunPlan,
    smoke_diagnostics: NumericalDiagnostics,
    smoke_assessment: NumericalAssessment,
    qualification_attempt_id: str,
    qualification_run_plan: RunPlan,
    qualification_diagnostics: NumericalDiagnostics,
    qualification_assessment: NumericalAssessment,
) -> ReferenceQualification:
    if smoke_plan.stage is not PilotStage.SMOKE:
        raise ValueError("the first reference attempt must be a smoke plan")
    if qualification_run_plan.stage is not PilotStage.QUALIFICATION:
        raise ValueError("the second reference attempt must be a qualification plan")
    if smoke_plan.parameter_values != qualification_run_plan.parameter_values:
        raise ValueError("smoke and qualification runs must use the same reference point")
    assessments = (smoke_assessment, qualification_assessment)
    if any(assessment.outcome is not AttemptOutcome.SUCCESS for assessment in assessments):
        raise ValueError("failed attempts cannot qualify a reference point")
    if any(assessment.evidence_eligible for assessment in assessments):
        raise ValueError("reference qualification attempts must be non-evidentiary")

    def diagnostics_hash(diagnostics: NumericalDiagnostics) -> str:
        canonical = json.dumps(
            diagnostics.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    return ReferenceQualification(
        smoke_attempt_id=smoke_attempt_id,
        qualification_attempt_id=qualification_attempt_id,
        diagnostics_hashes=(
            diagnostics_hash(smoke_diagnostics),
            diagnostics_hash(qualification_diagnostics),
        ),
    )
