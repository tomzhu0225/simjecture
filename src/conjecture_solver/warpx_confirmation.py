"""Independent fresh-seed confirmation using a physics-qualified WarpX profile."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from statistics import median
from typing import Literal

from pydantic import Field, model_validator

from .adapters.base import JobState, NormalizedResult, SimulatorAdapter
from .adapters.warpx import (
    WARPX_ADAPTER_VERSION,
    WarpXExecutionProfile,
    WarpXNumericalConfig,
    WarpXPairSummary,
    WarpXPhysicalConfig,
    WarpXPhysicsQualificationRecord,
    build_warpx_experiment,
    qualified_warpx_profile,
    warpx_physics_qualification_hash,
)
from .control import CampaignControl
from .ledger import SQLiteEventLedger, StoredEvent
from .models import StrictModel
from .outbox import (
    InjectedOutboxCrash,
    JournaledSimulatorAdapter,
    OutboxCrashPoint,
)


class WarpXConfirmationDisposition(StrEnum):
    CONFIRMED = "confirmed"
    INCONCLUSIVE = "inconclusive"


class WarpXAttemptFailureKind(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    NUMERICAL = "numerical"
    VALIDITY = "validity"


class QualifiedWarpXInstrument(StrictModel):
    """A passing qualification bound to the exact executable adapter profile."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    adapter_name: Literal["warpx_picmi"] = "warpx_picmi"
    adapter_version: str = WARPX_ADAPTER_VERSION
    qualification_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification: WarpXPhysicsQualificationRecord
    execution_profile: WarpXExecutionProfile

    @model_validator(mode="after")
    def qualification_is_exact(self) -> QualifiedWarpXInstrument:
        expected_hash = warpx_physics_qualification_hash(self.qualification)
        if not self.qualification.passed or not self.qualification.authorizes_scientific_evidence:
            raise ValueError("registered WarpX instrument requires a passing qualification")
        if self.qualification_hash != expected_hash:
            raise ValueError("registered instrument qualification hash does not match its record")
        if self.execution_profile != qualified_warpx_profile(self.qualification):
            raise ValueError("registered instrument profile does not match its qualification")
        return self


def register_qualified_warpx_instrument(
    qualification: WarpXPhysicsQualificationRecord,
) -> QualifiedWarpXInstrument:
    qualification_hash = warpx_physics_qualification_hash(qualification)
    return QualifiedWarpXInstrument(
        id=f"qualified_warpx_{qualification_hash[:20]}",
        qualification_hash=qualification_hash,
        qualification=qualification,
        execution_profile=qualified_warpx_profile(qualification),
    )


class WarpXConfirmationResolution(StrictModel):
    id: str = Field(min_length=1)
    grid_cells: int = Field(ge=32)
    electron_macroparticles_per_cell: int = Field(ge=16)
    time_step_omega_pe: float = Field(gt=0)
    diagnostic_interval_steps: int = Field(ge=1)


class WarpXConfirmationDesign(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    qualification_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical: WarpXPhysicalConfig
    seeds: tuple[int, ...] = Field(default=(211, 307, 401), min_length=3)
    resolutions: tuple[WarpXConfirmationResolution, ...] = Field(min_length=2)
    selection_frozen_before_confirmation: Literal[True] = True

    @model_validator(mode="after")
    def matrix_is_unique(self) -> WarpXConfirmationDesign:
        if len(set(self.seeds)) != len(self.seeds) or any(seed < 1 for seed in self.seeds):
            raise ValueError("confirmation seeds must be unique positive integers")
        if len({resolution.id for resolution in self.resolutions}) != len(self.resolutions):
            raise ValueError("confirmation resolution identifiers must be unique")
        return self


class WarpXConfirmationAttempt(StrictModel):
    seed: int = Field(ge=1)
    resolution_id: str = Field(min_length=1)
    normalized_result: NormalizedResult
    checks: dict[str, bool]
    confirmed: bool

    @model_validator(mode="after")
    def result_matches_checks(self) -> WarpXConfirmationAttempt:
        if not self.checks or self.confirmed != all(self.checks.values()):
            raise ValueError("confirmation attempt status must equal all checks")
        return self


class WarpXConfirmationFailure(StrictModel):
    ordinal: int = Field(ge=1)
    seed: int = Field(ge=1)
    resolution_id: str = Field(min_length=1)
    experiment_id: str = Field(min_length=1)
    external_job_id: str | None = None
    kind: WarpXAttemptFailureKind
    detail: str = Field(min_length=1)
    consumed_case_units: Literal[2] = 2


class WarpXConfirmationReport(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    design: WarpXConfirmationDesign
    attempts: tuple[WarpXConfirmationAttempt, ...] = ()
    failures: tuple[WarpXConfirmationFailure, ...] = ()
    median_reference_rates_by_resolution: dict[str, float]
    median_candidate_rates_by_resolution: dict[str, float]
    checks: dict[str, bool]
    disposition: WarpXConfirmationDisposition

    @model_validator(mode="after")
    def disposition_matches_checks(self) -> WarpXConfirmationReport:
        expected = (
            WarpXConfirmationDisposition.CONFIRMED
            if self.checks and all(self.checks.values())
            else WarpXConfirmationDisposition.INCONCLUSIVE
        )
        if self.disposition is not expected:
            raise ValueError("confirmation disposition must follow the report checks")
        attempt_keys = {(attempt.seed, attempt.resolution_id) for attempt in self.attempts}
        failure_keys = {(failure.seed, failure.resolution_id) for failure in self.failures}
        if attempt_keys & failure_keys:
            raise ValueError("a confirmation matrix point cannot both succeed and fail")
        return self


def default_warpx_confirmation_design(
    qualification: WarpXPhysicsQualificationRecord,
) -> WarpXConfirmationDesign:
    if not qualification.passed:
        raise ValueError("a failed WarpX qualification cannot define confirmation")
    return WarpXConfirmationDesign(
        qualification_hash=warpx_physics_qualification_hash(qualification),
        physical=qualification.scope.physical,
        resolutions=(
            WarpXConfirmationResolution(
                id="coarse",
                grid_cells=64,
                electron_macroparticles_per_cell=512,
                time_step_omega_pe=0.05,
                diagnostic_interval_steps=2,
            ),
            WarpXConfirmationResolution(
                id="refined",
                grid_cells=128,
                electron_macroparticles_per_cell=512,
                time_step_omega_pe=0.025,
                diagnostic_interval_steps=4,
            ),
        ),
    )


def build_warpx_confirmation_report(
    *,
    design: WarpXConfirmationDesign,
    qualification: WarpXPhysicsQualificationRecord,
    results: tuple[NormalizedResult, ...],
    failures: tuple[WarpXConfirmationFailure, ...] = (),
) -> WarpXConfirmationReport:
    qualification_hash = warpx_physics_qualification_hash(qualification)
    if not qualification.passed or design.qualification_hash != qualification_hash:
        raise ValueError("confirmation design does not name a passing qualification")
    resolution_by_numerics = {
        (
            resolution.grid_cells,
            resolution.electron_macroparticles_per_cell,
            resolution.time_step_omega_pe,
            resolution.diagnostic_interval_steps,
        ): resolution.id
        for resolution in design.resolutions
    }
    calibration_packages = {point.run_package_hash for point in qualification.calibration_points}
    calibration_manifests = {
        digest
        for point in qualification.calibration_points
        for digest in (
            point.reference_diagnostic_manifest_hash,
            point.candidate_diagnostic_manifest_hash,
        )
    }
    attempts: list[WarpXConfirmationAttempt] = []
    for result in results:
        diagnostics = result.diagnostics
        numerical = WarpXNumericalConfig.model_validate(diagnostics["numerical"])
        physical = WarpXPhysicalConfig.model_validate(diagnostics["physical"])
        profile = WarpXExecutionProfile.model_validate(diagnostics["execution_profile"])
        pair = WarpXPairSummary.model_validate(diagnostics["pair_summary"])
        resolution_id = resolution_by_numerics.get(
            (
                numerical.grid_cells,
                numerical.electron_macroparticles_per_cell,
                numerical.time_step_omega_pe,
                numerical.diagnostic_interval_steps,
            ),
            "outside_design",
        )
        run_package_hash = str(diagnostics["run_package_hash"])
        result_manifests = {
            pair.reference.diagnostic_manifest_hash,
            pair.candidate.diagnostic_manifest_hash,
        }
        checks = {
            "configuration_matches_frozen_design": (
                physical == design.physical
                and numerical.random_seed in design.seeds
                and resolution_id != "outside_design"
            ),
            "configuration_is_in_qualified_scope": not qualification.scope.validation_errors(
                physical,
                numerical,
            ),
            "qualified_profile_hash_matches": (
                profile.qualified_for_scientific_evidence
                and profile.qualification_hash == qualification_hash
            ),
            "numerical_validity_passed": bool(
                diagnostics["validity_gates"]["numerical_validity_passed"]
            ),
            "reference_is_damped": pair.reference.classification == "damped",
            "candidate_is_unstable": pair.candidate.classification == "unstable",
            "effective_rates_are_separated": (
                pair.candidate.effective_growth_rate_omega_pe
                - pair.reference.effective_growth_rate_omega_pe
                >= qualification.minimum_effective_rate_separation
            ),
            "raw_witness_satisfies_predicate": bool(diagnostics["raw_witness_satisfies_predicate"]),
            "result_is_scientific_evidence_eligible": bool(
                diagnostics["scientific_evidence_eligible"]
            ),
            "normalized_result_falsifies_hypothesis": bool(
                result.observables["hypothesis_falsified"]
            ),
            "package_was_not_used_for_calibration": run_package_hash not in calibration_packages,
            "diagnostics_were_not_used_for_calibration": not bool(
                result_manifests & calibration_manifests
            ),
        }
        attempts.append(
            WarpXConfirmationAttempt(
                seed=numerical.random_seed,
                resolution_id=resolution_id,
                normalized_result=result,
                checks=checks,
                confirmed=all(checks.values()),
            )
        )

    expected_keys = {
        (seed, resolution.id) for seed in design.seeds for resolution in design.resolutions
    }
    observed_keys = {(attempt.seed, attempt.resolution_id) for attempt in attempts}
    failed_keys = {(failure.seed, failure.resolution_id) for failure in failures}
    if any(key not in expected_keys for key in failed_keys):
        raise ValueError("confirmation failure is outside the frozen design")
    if len(failed_keys) != len(failures):
        raise ValueError("confirmation failures must identify unique matrix points")

    def medians(observable: str) -> dict[str, float]:
        return {
            resolution.id: float(
                median(
                    float(attempt.normalized_result.observables[observable])
                    for attempt in attempts
                    if attempt.resolution_id == resolution.id
                )
            )
            for resolution in design.resolutions
            if any(attempt.resolution_id == resolution.id for attempt in attempts)
        }

    reference_medians = medians("maxwellian_growth_rate")
    candidate_medians = medians("two_stream_growth_rate")

    def median_range(values: dict[str, float]) -> float:
        return max(values.values()) - min(values.values()) if values else math.inf

    checks = {
        "confirmation_matrix_is_complete": (
            observed_keys | failed_keys == expected_keys
            and len(attempts) + len(failures) == len(expected_keys)
        ),
        "no_execution_failures": not failures,
        "every_attempt_confirmed": bool(attempts)
        and all(attempt.confirmed for attempt in attempts),
        "confirmation_packages_are_unique": (
            len(
                {
                    str(attempt.normalized_result.diagnostics["run_package_hash"])
                    for attempt in attempts
                }
            )
            == len(attempts)
        ),
        "reference_median_rate_is_resolution_converged": (
            median_range(reference_medians) <= qualification.maximum_median_rate_shift
        ),
        "candidate_median_rate_is_resolution_converged": (
            median_range(candidate_medians) <= qualification.maximum_median_rate_shift
        ),
    }
    disposition = (
        WarpXConfirmationDisposition.CONFIRMED
        if all(checks.values())
        else WarpXConfirmationDisposition.INCONCLUSIVE
    )
    return WarpXConfirmationReport(
        design=design,
        attempts=tuple(sorted(attempts, key=lambda attempt: (attempt.resolution_id, attempt.seed))),
        failures=tuple(sorted(failures, key=lambda failure: (failure.resolution_id, failure.seed))),
        median_reference_rates_by_resolution=reference_medians,
        median_candidate_rates_by_resolution=candidate_medians,
        checks=checks,
        disposition=disposition,
    )


class WarpXConfirmationCrashPoint(StrEnum):
    AFTER_CONFIRMATION_STARTED = "after_confirmation_started"
    AFTER_JOB_RECEIPT = "after_job_receipt"
    AFTER_RESULT_RETRIEVED = "after_result_retrieved"
    AFTER_MATRIX_POINT_COMMITTED = "after_matrix_point_committed"
    AFTER_CONFIRMATION_COMPLETED = "after_confirmation_completed"


class InjectedWarpXConfirmationCrash(RuntimeError):
    def __init__(self, point: WarpXConfirmationCrashPoint, ordinal: int | None = None) -> None:
        suffix = f" at matrix ordinal {ordinal}" if ordinal is not None else ""
        super().__init__(f"injected WarpX confirmation crash at {point.value}{suffix}")
        self.point = point
        self.ordinal = ordinal


@dataclass
class WarpXConfirmationProjection:
    design: WarpXConfirmationDesign | None = None
    attempts: dict[tuple[int, str], WarpXConfirmationAttempt] | None = None
    failures: dict[tuple[int, str], WarpXConfirmationFailure] | None = None
    report: WarpXConfirmationReport | None = None

    def __post_init__(self) -> None:
        if self.attempts is None:
            self.attempts = {}
        if self.failures is None:
            self.failures = {}

    @classmethod
    def replay(cls, events: tuple[StoredEvent, ...]) -> WarpXConfirmationProjection:
        state = cls()
        for event in events:
            if event.event_type == "qualified_warpx_confirmation_started":
                state.design = WarpXConfirmationDesign.model_validate(event.payload["design"])
            elif event.event_type == "qualified_warpx_confirmation_attempt_completed":
                attempt = WarpXConfirmationAttempt.model_validate(event.payload["attempt"])
                assert state.attempts is not None
                state.attempts[(attempt.seed, attempt.resolution_id)] = attempt
            elif event.event_type == "qualified_warpx_confirmation_attempt_failed":
                failure = WarpXConfirmationFailure.model_validate(event.payload["failure"])
                assert state.failures is not None
                state.failures[(failure.seed, failure.resolution_id)] = failure
            elif event.event_type == "qualified_warpx_confirmation_completed":
                state.report = WarpXConfirmationReport.model_validate(event.payload["report"])
        return state


class WarpXConfirmationRunner:
    """Restart-safe execution of every point in a frozen qualified matrix."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        instrument: QualifiedWarpXInstrument,
        adapter: SimulatorAdapter,
        design: WarpXConfirmationDesign,
        control: CampaignControl | None = None,
        crash_at: WarpXConfirmationCrashPoint | None = None,
        crash_ordinal: int | None = None,
        outbox_crash_at: OutboxCrashPoint | None = None,
    ) -> None:
        if design.qualification_hash != instrument.qualification_hash:
            raise ValueError("confirmation design names a different qualified instrument")
        if adapter.capabilities().adapter_name != instrument.adapter_name:
            raise ValueError("confirmation adapter does not match the registered instrument")
        self.campaign_id = campaign_id
        self.ledger = ledger
        self.instrument = instrument
        self.adapter = JournaledSimulatorAdapter(
            campaign_id=campaign_id,
            ledger=ledger,
            adapter=adapter,
            crash_at=outbox_crash_at,
        )
        self.design = design
        self.control = control
        self.crash_at = crash_at
        self.crash_ordinal = crash_ordinal

    def _state(self) -> WarpXConfirmationProjection:
        return WarpXConfirmationProjection.replay(self.ledger.load(self.campaign_id))

    def _append(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, object],
        suffix: str,
    ) -> None:
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            idempotency_key=f"{self.campaign_id}:{suffix}",
        )

    def _crash(self, point: WarpXConfirmationCrashPoint, ordinal: int | None = None) -> None:
        if self.crash_at is point and (self.crash_ordinal is None or self.crash_ordinal == ordinal):
            raise InjectedWarpXConfirmationCrash(point, ordinal)

    def _record_failure(self, failure: WarpXConfirmationFailure) -> None:
        self._append(
            "qualified_warpx_confirmation_attempt_failed",
            "warpx_confirmation_attempt",
            failure.experiment_id,
            {"failure": failure.model_dump(mode="json")},
            f"qualified-warpx-confirmation:{failure.resolution_id}:{failure.seed}:failed",
        )

    def run(self) -> WarpXConfirmationReport:
        state = self._state()
        if state.design is not None and state.design != self.design:
            raise ValueError("campaign already contains a different WarpX confirmation design")
        if state.report is not None:
            return state.report
        if state.design is None:
            self._append(
                "qualified_warpx_confirmation_started",
                "warpx_confirmation",
                self.instrument.id,
                {
                    "instrument_id": self.instrument.id,
                    "design": self.design.model_dump(mode="json"),
                },
                "qualified-warpx-confirmation:started",
            )
        self._crash(WarpXConfirmationCrashPoint.AFTER_CONFIRMATION_STARTED)

        ordinal = 0
        for resolution in self.design.resolutions:
            for seed in self.design.seeds:
                ordinal += 1
                state = self._state()
                assert state.attempts is not None and state.failures is not None
                key = (seed, resolution.id)
                if key in state.attempts or key in state.failures:
                    continue
                if self.control is not None:
                    self.control.require_processing_authority()
                numerical = WarpXNumericalConfig(
                    grid_cells=resolution.grid_cells,
                    electron_macroparticles_per_cell=(resolution.electron_macroparticles_per_cell),
                    ion_macroparticles_per_cell=16,
                    time_step_omega_pe=resolution.time_step_omega_pe,
                    final_time_omega_pe=20.0,
                    diagnostic_interval_steps=resolution.diagnostic_interval_steps,
                    random_seed=seed,
                )
                experiment = build_warpx_experiment(
                    physical=self.design.physical,
                    numerical=numerical,
                    experiment_id=(f"warpx_confirmation_{resolution.id}_seed_{seed}_v1"),
                )
                validation = self.adapter.validate(experiment)
                if not validation.valid:
                    raise ValueError("; ".join(validation.errors))
                run = self.adapter.compile_input(experiment)
                try:
                    job = self.adapter.submit(
                        run,
                        idempotency_key=f"{experiment.id}:submit",
                    )
                except InjectedOutboxCrash:
                    raise
                except Exception as error:
                    self._record_failure(
                        WarpXConfirmationFailure(
                            ordinal=ordinal,
                            seed=seed,
                            resolution_id=resolution.id,
                            experiment_id=experiment.id,
                            kind=WarpXAttemptFailureKind.INFRASTRUCTURE,
                            detail=f"{type(error).__name__}: {error}",
                        )
                    )
                    self._crash(
                        WarpXConfirmationCrashPoint.AFTER_MATRIX_POINT_COMMITTED,
                        ordinal,
                    )
                    continue
                self._crash(WarpXConfirmationCrashPoint.AFTER_JOB_RECEIPT, ordinal)
                status = self.adapter.monitor(job)
                if status.state is not JobState.COMPLETED:
                    kind = (
                        WarpXAttemptFailureKind.NUMERICAL
                        if status.state is JobState.FAILED
                        else WarpXAttemptFailureKind.INFRASTRUCTURE
                    )
                    self._record_failure(
                        WarpXConfirmationFailure(
                            ordinal=ordinal,
                            seed=seed,
                            resolution_id=resolution.id,
                            experiment_id=experiment.id,
                            external_job_id=job.job_id,
                            kind=kind,
                            detail=(
                                f"scheduler state {status.state.value}: "
                                f"{status.detail or 'no detail'}"
                            ),
                        )
                    )
                else:
                    try:
                        normalized = self.adapter.normalize(self.adapter.retrieve(job))
                    except Exception as error:
                        self._record_failure(
                            WarpXConfirmationFailure(
                                ordinal=ordinal,
                                seed=seed,
                                resolution_id=resolution.id,
                                experiment_id=experiment.id,
                                external_job_id=job.job_id,
                                kind=WarpXAttemptFailureKind.VALIDITY,
                                detail=f"{type(error).__name__}: {error}",
                            )
                        )
                    else:
                        self._crash(
                            WarpXConfirmationCrashPoint.AFTER_RESULT_RETRIEVED,
                            ordinal,
                        )
                        attempt_report = build_warpx_confirmation_report(
                            design=self.design,
                            qualification=self.instrument.qualification,
                            results=(normalized,),
                        ).attempts[0]
                        self._append(
                            "qualified_warpx_confirmation_attempt_completed",
                            "warpx_confirmation_attempt",
                            experiment.id,
                            {"attempt": attempt_report.model_dump(mode="json")},
                            (f"qualified-warpx-confirmation:{resolution.id}:{seed}:completed"),
                        )
                self._crash(
                    WarpXConfirmationCrashPoint.AFTER_MATRIX_POINT_COMMITTED,
                    ordinal,
                )
                if self.control is not None:
                    self.control.require_processing_authority()

        state = self._state()
        assert state.attempts is not None and state.failures is not None
        report = build_warpx_confirmation_report(
            design=self.design,
            qualification=self.instrument.qualification,
            results=tuple(
                attempt.normalized_result
                for attempt in sorted(
                    state.attempts.values(),
                    key=lambda item: (item.resolution_id, item.seed),
                )
            ),
            failures=tuple(state.failures.values()),
        )
        self._append(
            "qualified_warpx_confirmation_completed",
            "warpx_confirmation",
            self.instrument.id,
            {"report": report.model_dump(mode="json")},
            "qualified-warpx-confirmation:completed",
        )
        self._crash(WarpXConfirmationCrashPoint.AFTER_CONFIRMATION_COMPLETED)
        return self._state().report or report
