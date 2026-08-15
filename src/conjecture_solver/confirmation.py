"""Independent PIC confirmation of a candidate frozen after analytic discovery."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .benchmarks.electrostatic_pic import (
    PICMixtureCaseResult,
    PICNumericalConfig,
    run_pic_mixture_case,
)
from .benchmarks.kinetic_sufficiency import DistributionMoments, GaussianMixture
from .ledger import SQLiteEventLedger, StoredEvent
from .models import StrictModel
from .search import BlindedSearchReport, SymmetricMixtureCandidate


class ConfirmationDisposition(StrEnum):
    CONFIRMED = "confirmed"
    NOT_CONFIRMED = "not_confirmed"
    INVALID = "invalid"


class PICConfirmationDesign(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str
    search_request_id: str
    candidate_id: str
    candidate: SymmetricMixtureCandidate
    reference_distribution: GaussianMixture
    outcome_tolerance: float = Field(gt=0)
    moment_tolerance: float = Field(gt=0)
    seeds: tuple[int, ...] = Field(default=(1, 7, 19), min_length=2)
    velocity_beams: tuple[int, ...] = Field(default=(192, 384), min_length=2)
    base_config: PICNumericalConfig = PICNumericalConfig()
    selection_frozen_before_confirmation: Literal[True] = True

    @model_validator(mode="after")
    def valid_matrix(self) -> PICConfirmationDesign:
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("confirmation seeds must be unique")
        if len(set(self.velocity_beams)) != len(self.velocity_beams):
            raise ValueError("confirmation velocity resolutions must be unique")
        if any(beams % 2 or beams < 64 for beams in self.velocity_beams):
            raise ValueError("confirmation velocity_beams must be even and at least 64")
        return self

    def configurations(self) -> tuple[PICNumericalConfig, ...]:
        return tuple(
            PICNumericalConfig.model_validate(
                {
                    **self.base_config.model_dump(mode="json"),
                    "velocity_beams": beams,
                    "seed": seed,
                }
            )
            for beams in self.velocity_beams
            for seed in self.seeds
        )


class PICConfirmationAttempt(StrictModel):
    id: str
    ordinal: int = Field(ge=1)
    config: PICNumericalConfig
    reference: PICMixtureCaseResult
    candidate: PICMixtureCaseResult
    moments_match: bool
    outcome_separation: float = Field(ge=0)
    opposite_stability_classes: bool
    eligible: bool
    confirms: bool


class PICConfirmationReport(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    design: PICConfirmationDesign
    attempts: tuple[PICConfirmationAttempt, ...] = Field(min_length=1)
    eligible_attempts: int = Field(ge=0)
    confirming_attempts: int = Field(ge=0)
    disposition: ConfirmationDisposition
    limitations: tuple[str, ...]


def confirmation_design_from_search(
    report: BlindedSearchReport,
) -> PICConfirmationDesign:
    if report.confirmation_candidate_id is None or report.confirmation_candidate is None:
        raise ValueError("search report has no frozen AI witness to confirm")
    identity_payload = json.dumps(
        {
            "search_request_id": report.request.id,
            "candidate_id": report.confirmation_candidate_id,
            "candidate": report.confirmation_candidate.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    identity = hashlib.sha256(identity_payload.encode()).hexdigest()[:16]
    return PICConfirmationDesign(
        id=f"pic_confirmation_{identity}",
        search_request_id=report.request.id,
        candidate_id=report.confirmation_candidate_id,
        candidate=report.confirmation_candidate,
        reference_distribution=report.request.reference_distribution,
        outcome_tolerance=report.request.outcome_tolerance,
        moment_tolerance=report.request.moment_tolerance,
    )


def _moments_match(
    left: DistributionMoments,
    right: DistributionMoments,
    tolerance: float,
) -> bool:
    return all(
        abs(getattr(left, name) - getattr(right, name)) <= tolerance
        for name in DistributionMoments.model_fields
    )


def run_confirmation_attempt(
    design: PICConfirmationDesign,
    config: PICNumericalConfig,
    ordinal: int,
) -> PICConfirmationAttempt:
    reference = run_pic_mixture_case(
        "unit_maxwellian_reference",
        design.reference_distribution,
        config,
    )
    candidate = run_pic_mixture_case(
        design.candidate_id,
        design.candidate.distribution(),
        config,
    )
    moment_match = _moments_match(
        reference.initial_moments,
        candidate.initial_moments,
        design.moment_tolerance,
    )
    separation = abs(candidate.effective_growth_rate - reference.effective_growth_rate)
    opposite = {reference.classification, candidate.classification} == {"damped", "unstable"}
    eligible = reference.validity_passed and candidate.validity_passed and moment_match
    confirms = eligible and opposite and separation > design.outcome_tolerance
    identity = hashlib.sha256(
        f"{design.id}:{config.model_dump_json()}".encode()
    ).hexdigest()[:16]
    return PICConfirmationAttempt(
        id=f"confirmation_attempt_{identity}",
        ordinal=ordinal,
        config=config,
        reference=reference,
        candidate=candidate,
        moments_match=moment_match,
        outcome_separation=separation,
        opposite_stability_classes=opposite,
        eligible=eligible,
        confirms=confirms,
    )


def build_confirmation_report(
    design: PICConfirmationDesign,
    attempts: tuple[PICConfirmationAttempt, ...],
) -> PICConfirmationReport:
    eligible = sum(attempt.eligible for attempt in attempts)
    confirming = sum(attempt.confirms for attempt in attempts)
    if eligible != len(attempts):
        disposition = ConfirmationDisposition.INVALID
    elif confirming == len(attempts):
        disposition = ConfirmationDisposition.CONFIRMED
    else:
        disposition = ConfirmationDisposition.NOT_CONFIRMED
    return PICConfirmationReport(
        design=design,
        attempts=attempts,
        eligible_attempts=eligible,
        confirming_attempts=confirming,
        disposition=disposition,
        limitations=(
            "confirmation is restricted to the declared 1D electrostatic PIC model",
            "the short-time envelope estimator is not qualified for threshold localization",
            "the same PIC implementation is reused across seeds and velocity resolutions",
        ),
    )


class ConfirmationProjection:
    def __init__(self) -> None:
        self.design: PICConfirmationDesign | None = None
        self.attempts: dict[int, PICConfirmationAttempt] = {}
        self.report: PICConfirmationReport | None = None

    @classmethod
    def replay(cls, events: tuple[StoredEvent, ...]) -> ConfirmationProjection:
        state = cls()
        for event in events:
            if event.event_type == "confirmation_started":
                state.design = PICConfirmationDesign.model_validate(event.payload["design"])
            elif event.event_type == "confirmation_attempt_completed":
                attempt = PICConfirmationAttempt.model_validate(event.payload["attempt"])
                state.attempts[attempt.ordinal] = attempt
            elif event.event_type == "confirmation_completed":
                state.report = PICConfirmationReport.model_validate(event.payload["report"])
        return state


class PICConfirmationRunner:
    """Replayable confirmation matrix with no adaptive candidate changes."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        design: PICConfirmationDesign,
    ) -> None:
        self.campaign_id = campaign_id
        self.ledger = ledger
        self.design = design

    def _state(self) -> ConfirmationProjection:
        return ConfirmationProjection.replay(self.ledger.load(self.campaign_id))

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

    def run(self) -> PICConfirmationReport:
        state = self._state()
        if state.design is not None and state.design != self.design:
            raise ValueError("confirmation campaign already exists with a different design")
        if state.report is not None:
            return state.report
        if state.design is None:
            self._append(
                "confirmation_started",
                "confirmation",
                self.design.id,
                {"design": self.design.model_dump(mode="json")},
                "confirmation-started",
            )
        state = self._state()
        for ordinal, config in enumerate(self.design.configurations(), start=1):
            if ordinal in state.attempts:
                continue
            attempt = run_confirmation_attempt(self.design, config, ordinal)
            self._append(
                "confirmation_attempt_completed",
                "confirmation_attempt",
                attempt.id,
                {"attempt": attempt.model_dump(mode="json")},
                f"confirmation-attempt:{ordinal}",
            )
            state = self._state()
        attempts = tuple(
            state.attempts[ordinal]
            for ordinal in range(1, len(self.design.configurations()) + 1)
        )
        report = build_confirmation_report(self.design, attempts)
        self._append(
            "confirmation_completed",
            "confirmation",
            self.design.id,
            {"report": report.model_dump(mode="json")},
            "confirmation-completed",
        )
        return self._state().report or report
