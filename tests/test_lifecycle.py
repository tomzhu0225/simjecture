from __future__ import annotations

import pytest

from conjecture_solver.lifecycle import (
    CampaignState,
    InvalidTransition,
    LifecycleEvent,
    LifecycleEventType,
    apply_lifecycle_event,
)
from conjecture_solver.models import CampaignStatus


def transition(
    state: CampaignState,
    event_type: LifecycleEventType,
    **payload: str,
) -> CampaignState:
    return apply_lifecycle_event(
        state,
        LifecycleEvent(event_type=event_type, payload=payload),
    )


def test_pause_and_resume_preserve_campaign_identity() -> None:
    state = CampaignState(campaign_id="campaign_1")
    state = transition(state, LifecycleEventType.REQUEST_PAUSE)
    state = transition(state, LifecycleEventType.BEGIN_QUIESCING)
    state = transition(state, LifecycleEventType.MARK_PAUSED)
    assert state.status is CampaignStatus.PAUSED
    state = transition(state, LifecycleEventType.REQUEST_RESUME)
    state = transition(state, LifecycleEventType.COMMIT_RESUME)
    assert state.status is CampaignStatus.ACTIVE
    assert state.campaign_id == "campaign_1"
    assert state.revision == 5


def test_interruption_is_idempotent_and_not_a_campaign_termination() -> None:
    state = CampaignState(campaign_id="campaign_1")
    state = transition(
        state,
        LifecycleEventType.ATTEMPT_INTERRUPTED,
        attempt_id="attempt_1",
    )
    state = transition(
        state,
        LifecycleEventType.ATTEMPT_INTERRUPTED,
        attempt_id="attempt_1",
    )
    assert state.status is CampaignStatus.ACTIVE
    assert state.interrupted_attempt_ids == ("attempt_1",)


def test_invalid_resume_is_rejected() -> None:
    state = CampaignState(campaign_id="campaign_1")
    with pytest.raises(InvalidTransition):
        transition(state, LifecycleEventType.REQUEST_RESUME)


def test_crash_recovery_can_return_to_paused() -> None:
    state = CampaignState(campaign_id="campaign_1")
    state = transition(state, LifecycleEventType.DETECT_CRASH)
    assert state.status is CampaignStatus.RECOVERING
    state = transition(
        state,
        LifecycleEventType.COMPLETE_RECOVERY,
        target=CampaignStatus.PAUSED.value,
    )
    assert state.status is CampaignStatus.PAUSED
