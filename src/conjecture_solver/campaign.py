"""Crash-recoverable runner for the first end-to-end scientific campaign."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from .adapters.base import (
    JobReference,
    JobState,
    NormalizedResult,
    RunPackage,
    SimulatorAdapter,
)
from .benchmarks.kinetic_sufficiency import build_problem
from .control import CampaignControl
from .discovery import DiscoveryPackage
from .ledger import SQLiteEventLedger, StoredEvent
from .models import (
    AttemptOutcome,
    AttemptRecord,
    Claim,
    ClaimDisposition,
    EvidenceRole,
    ExperimentSpec,
    HypothesisNode,
    RunEvidence,
)


class CrashPoint(StrEnum):
    AFTER_CAMPAIGN_CREATED = "after_campaign_created"
    AFTER_ACTION_PLANNED = "after_action_planned"
    AFTER_ATTEMPT_RECORDED = "after_attempt_recorded"
    AFTER_SUBMIT_BEFORE_COMMIT = "after_submit_before_commit"
    AFTER_JOB_COMMITTED = "after_job_committed"
    AFTER_RETRIEVE_BEFORE_COMMIT = "after_retrieve_before_commit"
    AFTER_RESULT_COMMITTED = "after_result_committed"
    AFTER_ATTEMPT_COMPLETED = "after_attempt_completed"
    AFTER_EVIDENCE_COMMIT = "after_evidence_commit"
    AFTER_CLAIM_COMMIT = "after_claim_commit"
    AFTER_CAMPAIGN_COMPLETED = "after_campaign_completed"


class InjectedCrash(RuntimeError):
    def __init__(self, point: CrashPoint) -> None:
        super().__init__(f"injected crash at {point.value}")
        self.point = point


@dataclass
class CampaignProjection:
    hypothesis: HypothesisNode | None = None
    experiment: ExperimentSpec | None = None
    run_package: RunPackage | None = None
    attempt: AttemptRecord | None = None
    job: JobReference | None = None
    normalized_result: NormalizedResult | None = None
    evidence: RunEvidence | None = None
    claim: Claim | None = None
    completed_event: StoredEvent | None = None

    @classmethod
    def replay(cls, events: tuple[StoredEvent, ...]) -> CampaignProjection:
        state = cls()
        for event in events:
            payload = event.payload
            if event.event_type == "campaign_created":
                state.hypothesis = HypothesisNode.model_validate(payload["hypothesis"])
                state.experiment = ExperimentSpec.model_validate(payload["experiment"])
            elif event.event_type == "action_planned":
                state.run_package = RunPackage.model_validate(payload["run_package"])
            elif event.event_type in {"attempt_recorded", "attempt_completed"}:
                state.attempt = AttemptRecord.model_validate(payload["attempt"])
            elif event.event_type == "job_submitted":
                state.job = JobReference.model_validate(payload["job"])
            elif event.event_type == "result_retrieved":
                state.normalized_result = NormalizedResult.model_validate(
                    payload["normalized_result"]
                )
            elif event.event_type == "evidence_ingested":
                state.evidence = RunEvidence.model_validate(payload["evidence"])
            elif event.event_type == "claim_evaluated":
                state.claim = Claim.model_validate(payload["claim"])
            elif event.event_type == "campaign_completed":
                state.completed_event = event
        return state


def planted_experiment() -> ExperimentSpec:
    return ExperimentSpec(
        id="experiment_kinetic_sufficiency_v1",
        hypothesis_ids=("hypothesis_low_moments_sufficient_for_stability",),
        action_type="kinetic_sufficiency",
        physical_parameters={"wavenumber": 0.5},
        required_diagnostics=("dominant_linear_mode", "distribution_moments"),
        predictions={
            "sufficiency": "matched distributions have equal growth rate",
            "counterexample": "matched distributions differ in growth rate",
        },
        falsification_condition="a matched pair differs by more than 0.02",
    )


def planted_campaign_problem() -> tuple[HypothesisNode, ExperimentSpec]:
    hypothesis, _ = build_problem()
    return hypothesis, planted_experiment()


class CampaignRunner:
    """Resume one campaign by replaying its ledger before each side effect."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        adapter: SimulatorAdapter,
        hypothesis: HypothesisNode,
        experiment: ExperimentSpec,
        crash_at: CrashPoint | None = None,
        control: CampaignControl | None = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.ledger = ledger
        self.adapter = adapter
        self.hypothesis = hypothesis
        self.experiment = experiment
        self.crash_at = crash_at
        if control is not None and control.campaign_id != campaign_id:
            raise ValueError("control plane targets a different campaign")
        self.control = control

    def _crash(self, point: CrashPoint) -> None:
        if self.crash_at is point:
            raise InjectedCrash(point)

    def _events(self) -> tuple[StoredEvent, ...]:
        return self.ledger.load(self.campaign_id)

    def _state(self) -> CampaignProjection:
        return CampaignProjection.replay(self._events())

    def _append(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, object],
    ) -> StoredEvent:
        result = self.ledger.append(
            campaign_id=self.campaign_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            idempotency_key=f"{self.campaign_id}:{event_type}",
        )
        return result.event

    def _validate_identity(self, state: CampaignProjection) -> None:
        if state.experiment is not None and state.experiment != self.experiment:
            raise ValueError("campaign already exists with a different experiment")
        if state.hypothesis is not None and state.hypothesis != self.hypothesis:
            raise ValueError("campaign already exists with a different hypothesis")

    def _package(self, state: CampaignProjection) -> DiscoveryPackage:
        if not all(
            (
                state.hypothesis,
                state.experiment,
                state.attempt,
                state.normalized_result,
                state.evidence,
                state.claim,
                state.completed_event,
            )
        ):
            raise RuntimeError("cannot package an incomplete campaign")
        assert state.hypothesis is not None
        assert state.experiment is not None
        assert state.attempt is not None
        assert state.normalized_result is not None
        assert state.evidence is not None
        assert state.claim is not None
        assert state.completed_event is not None
        return DiscoveryPackage.create(
            campaign_id=self.campaign_id,
            hypothesis=state.hypothesis,
            experiment=state.experiment,
            attempt=state.attempt,
            evidence=state.evidence,
            claim=state.claim,
            normalized_result=state.normalized_result,
            provenance_event_hashes=tuple(event.event_hash for event in self._events()),
            generated_at=datetime.fromisoformat(state.completed_event.created_at),
        )

    def run(self) -> DiscoveryPackage:
        state = self._state()
        self._validate_identity(state)
        if state.completed_event is not None:
            return self._package(state)

        if state.experiment is None:
            self._append(
                "campaign_created",
                "campaign",
                self.campaign_id,
                {
                    "hypothesis": self.hypothesis.model_dump(mode="json"),
                    "experiment": self.experiment.model_dump(mode="json"),
                },
            )
        self._crash(CrashPoint.AFTER_CAMPAIGN_CREATED)
        state = self._state()

        if state.run_package is None:
            validation = self.adapter.validate(self.experiment)
            if not validation.valid:
                raise ValueError("; ".join(validation.errors))
            run_package = self.adapter.compile_input(self.experiment)
            self._append(
                "action_planned",
                "experiment",
                self.experiment.id,
                {
                    "validation": validation.model_dump(mode="json"),
                    "run_package": run_package.model_dump(mode="json"),
                },
            )
        self._crash(CrashPoint.AFTER_ACTION_PLANNED)
        state = self._state()
        assert state.run_package is not None

        if self.control is not None and state.job is None:
            self.control.require_action_authority(self.experiment.id)

        attempt_id = f"attempt_{hashlib.sha256(self.campaign_id.encode()).hexdigest()[:16]}"
        submission_key = f"{self.campaign_id}:submit:{state.run_package.package_hash}"
        if state.attempt is None:
            attempt = AttemptRecord(
                id=attempt_id,
                experiment_id=self.experiment.id,
                idempotency_key=submission_key,
            )
            self._append(
                "attempt_recorded",
                "attempt",
                attempt.id,
                {"attempt": attempt.model_dump(mode="json")},
            )
        self._crash(CrashPoint.AFTER_ATTEMPT_RECORDED)
        state = self._state()
        assert state.attempt is not None

        # Re-submission is intentional: a real scheduler must treat this as an
        # idempotent attach, including after the process died before commit.
        attached_job = self.adapter.submit(
            state.run_package,
            idempotency_key=state.attempt.idempotency_key,
        )
        if state.job is not None and attached_job != state.job:
            raise RuntimeError("adapter violated the idempotent submission contract")
        if state.job is None:
            self._crash(CrashPoint.AFTER_SUBMIT_BEFORE_COMMIT)
            self._append(
                "job_submitted",
                "attempt",
                state.attempt.id,
                {"job": attached_job.model_dump(mode="json")},
            )
        self._crash(CrashPoint.AFTER_JOB_COMMITTED)
        state = self._state()
        assert state.job is not None

        if state.normalized_result is None:
            status = self.adapter.monitor(state.job)
            if status.state is not JobState.COMPLETED:
                raise RuntimeError(f"job is not complete: {status.state.value}")
            raw_result = self.adapter.retrieve(state.job)
            normalized = self.adapter.normalize(raw_result)
            self._crash(CrashPoint.AFTER_RETRIEVE_BEFORE_COMMIT)
            self._append(
                "result_retrieved",
                "attempt",
                state.attempt.id,
                {
                    "raw_artifact_hashes": list(raw_result.artifact_hashes),
                    "normalized_result": normalized.model_dump(mode="json"),
                },
            )
        self._crash(CrashPoint.AFTER_RESULT_COMMITTED)
        state = self._state()
        assert state.normalized_result is not None

        if state.attempt.outcome is None:
            completed = AttemptRecord.model_validate(
                {
                    **state.attempt.model_dump(mode="json"),
                    "outcome": AttemptOutcome.SUCCESS.value,
                    "completed_at": datetime.now(UTC).isoformat(),
                    "external_job_id": state.job.job_id,
                }
            )
            self._append(
                "attempt_completed",
                "attempt",
                completed.id,
                {"attempt": completed.model_dump(mode="json")},
            )
        self._crash(CrashPoint.AFTER_ATTEMPT_COMPLETED)
        state = self._state()
        assert state.attempt is not None

        if self.control is not None:
            self.control.require_processing_authority()

        if state.evidence is None:
            observables = state.normalized_result.observables
            scientific_eligibility = bool(
                state.normalized_result.diagnostics.get(
                    "scientific_evidence_eligible",
                    True,
                )
            )
            evidence = RunEvidence(
                id=f"evidence_{attempt_id.removeprefix('attempt_')}",
                source_attempt_id=attempt_id,
                role=EvidenceRole.DISCOVERY,
                eligible=scientific_eligibility,
                eligibility_reason=(
                    "successful run passed adapter and result validity gates"
                    if scientific_eligibility
                    else "adapter marked the execution profile or numerical result ineligible"
                ),
                observable_values={
                    "maxwellian_growth_rate": float(observables["maxwellian_growth_rate"]),
                    "two_stream_growth_rate": float(observables["two_stream_growth_rate"]),
                    "outcome_separation": abs(
                        float(observables["two_stream_growth_rate"])
                        - float(observables["maxwellian_growth_rate"])
                    ),
                },
                independence_group=(
                    f"{state.run_package.adapter_name}:{state.run_package.package_hash}"
                ),
                artifact_hashes=state.normalized_result.artifact_hashes,
            )
            self._append(
                "evidence_ingested",
                "evidence",
                evidence.id,
                {"evidence": evidence.model_dump(mode="json")},
            )
        self._crash(CrashPoint.AFTER_EVIDENCE_COMMIT)
        state = self._state()
        assert state.evidence is not None

        if state.claim is None:
            falsified = state.evidence.eligible and bool(
                state.normalized_result.observables["hypothesis_falsified"]
            )
            disposition = (
                ClaimDisposition.REFUTED_WITHIN_MODEL
                if falsified
                else ClaimDisposition.UNRESOLVED
            )
            claim = Claim(
                id=f"claim_{hashlib.sha256(self.campaign_id.encode()).hexdigest()[:16]}",
                hypothesis_id=self.hypothesis.id,
                statement=(
                    "The low-order-moment predictive-sufficiency hypothesis is "
                    "refuted within the declared kinetic model."
                    if falsified
                    else "The declared test did not refute the hypothesis."
                ),
                disposition=disposition,
                scope=self.hypothesis.domain.description,
                evidence_ids=(state.evidence.id,),
                limitations=(
                    "discovery evidence; independent confirmation has not been run",
                    "scope is restricted to the preregistered model family and k=0.5",
                ),
            )
            self._append(
                "claim_evaluated",
                "claim",
                claim.id,
                {"claim": claim.model_dump(mode="json")},
            )
        self._crash(CrashPoint.AFTER_CLAIM_COMMIT)

        state = self._state()
        assert state.claim is not None
        self._append(
            "campaign_completed",
            "campaign",
            self.campaign_id,
            {"claim_id": state.claim.id},
        )
        self._crash(CrashPoint.AFTER_CAMPAIGN_COMPLETED)
        final_state = self._state()
        return self._package(final_state)
