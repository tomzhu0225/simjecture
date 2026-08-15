"""Pure campaign lifecycle transitions."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from .models import CampaignStatus, StrictModel


class LifecycleEventType(StrEnum):
    REQUEST_PAUSE = "request_pause"
    BEGIN_QUIESCING = "begin_quiescing"
    MARK_PAUSED = "mark_paused"
    REQUEST_RESUME = "request_resume"
    COMMIT_RESUME = "commit_resume"
    DETECT_CRASH = "detect_crash"
    COMPLETE_RECOVERY = "complete_recovery"
    EMERGENCY_STOP = "emergency_stop"
    REQUIRE_HUMAN_REVIEW = "require_human_review"
    TERMINATE = "terminate"
    ATTEMPT_INTERRUPTED = "attempt_interrupted"


class LifecycleEvent(StrictModel):
    event_type: LifecycleEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class CampaignState(StrictModel):
    campaign_id: str
    status: CampaignStatus = CampaignStatus.ACTIVE
    revision: int = Field(default=0, ge=0)
    interrupted_attempt_ids: tuple[str, ...] = ()


class InvalidTransition(ValueError):
    pass


def _require(state: CampaignState, allowed: set[CampaignStatus], event: LifecycleEvent) -> None:
    if state.status not in allowed:
        allowed_names = ", ".join(sorted(item.value for item in allowed))
        raise InvalidTransition(
            f"{event.event_type.value} requires one of [{allowed_names}], got {state.status.value}"
        )


def apply_lifecycle_event(state: CampaignState, event: LifecycleEvent) -> CampaignState:
    status = state.status
    interrupted = state.interrupted_attempt_ids

    match event.event_type:
        case LifecycleEventType.REQUEST_PAUSE:
            _require(state, {CampaignStatus.ACTIVE}, event)
            status = CampaignStatus.PAUSE_REQUESTED
        case LifecycleEventType.BEGIN_QUIESCING:
            _require(state, {CampaignStatus.PAUSE_REQUESTED}, event)
            status = CampaignStatus.QUIESCING
        case LifecycleEventType.MARK_PAUSED:
            _require(state, {CampaignStatus.QUIESCING}, event)
            status = CampaignStatus.PAUSED
        case LifecycleEventType.REQUEST_RESUME:
            _require(state, {CampaignStatus.PAUSED}, event)
            status = CampaignStatus.RESUMING
        case LifecycleEventType.COMMIT_RESUME:
            _require(state, {CampaignStatus.RESUMING}, event)
            status = CampaignStatus.ACTIVE
        case LifecycleEventType.DETECT_CRASH:
            _require(
                state,
                {
                    CampaignStatus.ACTIVE,
                    CampaignStatus.PAUSE_REQUESTED,
                    CampaignStatus.QUIESCING,
                    CampaignStatus.RESUMING,
                },
                event,
            )
            status = CampaignStatus.RECOVERING
        case LifecycleEventType.COMPLETE_RECOVERY:
            _require(state, {CampaignStatus.RECOVERING}, event)
            target = event.payload.get("target", CampaignStatus.ACTIVE.value)
            if target not in {CampaignStatus.ACTIVE.value, CampaignStatus.PAUSED.value}:
                raise InvalidTransition("recovery target must be active or paused")
            status = CampaignStatus(target)
        case LifecycleEventType.EMERGENCY_STOP:
            _require(
                state,
                {
                    CampaignStatus.ACTIVE,
                    CampaignStatus.PAUSE_REQUESTED,
                    CampaignStatus.QUIESCING,
                    CampaignStatus.RESUMING,
                    CampaignStatus.RECOVERING,
                    CampaignStatus.PAUSED,
                },
                event,
            )
            status = CampaignStatus.EMERGENCY_STOPPED
        case LifecycleEventType.REQUIRE_HUMAN_REVIEW:
            _require(state, {CampaignStatus.EMERGENCY_STOPPED}, event)
            status = CampaignStatus.HUMAN_REVIEW
        case LifecycleEventType.TERMINATE:
            _require(
                state,
                {
                    CampaignStatus.ACTIVE,
                    CampaignStatus.PAUSED,
                    CampaignStatus.HUMAN_REVIEW,
                    CampaignStatus.EMERGENCY_STOPPED,
                },
                event,
            )
            status = CampaignStatus.TERMINATED
        case LifecycleEventType.ATTEMPT_INTERRUPTED:
            attempt_id = event.payload.get("attempt_id")
            if not isinstance(attempt_id, str) or not attempt_id:
                raise InvalidTransition("attempt_interrupted requires attempt_id")
            if attempt_id not in interrupted:
                interrupted = (*interrupted, attempt_id)

    return state.model_copy(
        update={
            "status": status,
            "revision": state.revision + 1,
            "interrupted_attempt_ids": interrupted,
        }
    )
