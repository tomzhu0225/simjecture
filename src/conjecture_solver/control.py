"""Replayable human control plane for safe campaign boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import Field, model_validator

from .ledger import SQLiteEventLedger
from .lifecycle import (
    CampaignState,
    LifecycleEvent,
    LifecycleEventType,
    apply_lifecycle_event,
)
from .models import CampaignStatus, InterventionType, StrictModel, new_id


class StaleControlRevision(ValueError):
    pass


class CampaignPaused(RuntimeError):
    pass


class CampaignStopped(RuntimeError):
    pass


class ActionVetoed(RuntimeError):
    pass


class ControlDirective(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("control"))
    campaign_id: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    intervention_type: InterventionType
    reason: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    expected_revision: int = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> ControlDirective:
        if (
            self.intervention_type is InterventionType.ACTION_VETO
            and (
                not isinstance(self.payload.get("action_id"), str)
                or not self.payload["action_id"].strip()
            )
        ):
            raise ValueError("action veto requires action_id")
        if self.intervention_type is InterventionType.PRIORITY_UPDATE:
            priorities = self.payload.get("priorities")
            if not isinstance(priorities, dict) or not priorities:
                raise ValueError("priority update requires a non-empty priorities mapping")
            if any(not isinstance(value, (int, float)) for value in priorities.values()):
                raise ValueError("priority values must be numeric")
        if (
            self.intervention_type is InterventionType.TACTICAL_SUGGESTION
            and (
                not isinstance(self.payload.get("suggestion"), str)
                or not self.payload["suggestion"].strip()
            )
        ):
            raise ValueError("tactical suggestion requires suggestion text")
        return self


@dataclass
class ControlProjection:
    campaign_id: str
    state: CampaignState
    revision: int = 0
    directives: dict[str, ControlDirective] = field(default_factory=dict)
    vetoed_action_ids: set[str] = field(default_factory=set)
    priorities: dict[str, float] = field(default_factory=dict)
    tactical_suggestions: list[str] = field(default_factory=list)
    last_pause_directive_id: str | None = None

    @classmethod
    def replay(cls, campaign_id: str, ledger: SQLiteEventLedger) -> ControlProjection:
        projection = cls(campaign_id=campaign_id, state=CampaignState(campaign_id=campaign_id))
        for event in ledger.load(campaign_id):
            if event.event_type == "control_directive_recorded":
                directive = ControlDirective.model_validate(event.payload["directive"])
                projection.directives[directive.id] = directive
                projection.revision += 1
                if directive.intervention_type is InterventionType.ACTION_VETO:
                    projection.vetoed_action_ids.add(str(directive.payload["action_id"]))
                elif directive.intervention_type is InterventionType.PRIORITY_UPDATE:
                    projection.priorities.update(
                        {
                            str(name): float(value)
                            for name, value in directive.payload["priorities"].items()
                        }
                    )
                elif directive.intervention_type is InterventionType.TACTICAL_SUGGESTION:
                    projection.tactical_suggestions.append(
                        str(directive.payload["suggestion"])
                    )
                elif directive.intervention_type is InterventionType.PAUSE:
                    projection.last_pause_directive_id = directive.id
            elif event.event_type == "lifecycle_transition_recorded":
                lifecycle_event = LifecycleEvent.model_validate(event.payload["event"])
                projection.state = apply_lifecycle_event(projection.state, lifecycle_event)
        return projection


class CampaignControl:
    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
    ) -> None:
        self.campaign_id = campaign_id
        self.ledger = ledger

    def projection(self) -> ControlProjection:
        return ControlProjection.replay(self.campaign_id, self.ledger)

    def _append_transition(
        self,
        directive_id: str,
        transition: LifecycleEventType,
    ) -> None:
        event = LifecycleEvent(event_type=transition)
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type="lifecycle_transition_recorded",
            aggregate_type="campaign_control",
            aggregate_id=self.campaign_id,
            payload={"event": event.model_dump(mode="json")},
            idempotency_key=f"{self.campaign_id}:control:{directive_id}:{transition.value}",
        )

    def _complete_directive(self, directive: ControlDirective) -> ControlProjection:
        projection = self.projection()
        intervention = directive.intervention_type
        if intervention is InterventionType.PAUSE:
            if projection.state.status is CampaignStatus.ACTIVE:
                self._append_transition(directive.id, LifecycleEventType.REQUEST_PAUSE)
        elif intervention is InterventionType.RESUME:
            if projection.state.status is CampaignStatus.PAUSED:
                self._append_transition(directive.id, LifecycleEventType.REQUEST_RESUME)
                projection = self.projection()
            if projection.state.status is CampaignStatus.RESUMING:
                self._append_transition(directive.id, LifecycleEventType.COMMIT_RESUME)
        elif (
            intervention is InterventionType.EMERGENCY_STOP
            and projection.state.status
            not in {
                CampaignStatus.EMERGENCY_STOPPED,
                CampaignStatus.HUMAN_REVIEW,
                CampaignStatus.TERMINATED,
            }
        ):
            self._append_transition(directive.id, LifecycleEventType.EMERGENCY_STOP)
        return self.projection()

    def issue(self, directive: ControlDirective) -> ControlProjection:
        if directive.campaign_id != self.campaign_id:
            raise ValueError("control directive targets a different campaign")
        projection = self.projection()
        existing = projection.directives.get(directive.id)
        if existing is not None:
            if existing != directive:
                raise ValueError("control directive ID cannot be reused with changed content")
            return self._complete_directive(directive)
        if directive.expected_revision != projection.revision:
            raise StaleControlRevision(
                f"expected control revision {directive.expected_revision}, "
                f"current revision is {projection.revision}"
            )
        if directive.intervention_type in {
            InterventionType.CONTRACT_AMENDMENT,
            InterventionType.EVIDENCE_INJECTION,
        }:
            raise ValueError("contract or evidence changes require a reviewed campaign branch")

        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type="control_directive_recorded",
            aggregate_type="campaign_control",
            aggregate_id=directive.id,
            payload={"directive": directive.model_dump(mode="json")},
            idempotency_key=f"{self.campaign_id}:control:{directive.id}",
        )
        return self._complete_directive(directive)

    def quiesce_if_requested(self) -> ControlProjection:
        projection = self.projection()
        if projection.state.status in {
            CampaignStatus.PAUSE_REQUESTED,
            CampaignStatus.QUIESCING,
        }:
            directive_id = projection.last_pause_directive_id
            if directive_id is None:
                raise RuntimeError("pause transition has no originating directive")
            if projection.state.status is CampaignStatus.PAUSE_REQUESTED:
                self._append_transition(directive_id, LifecycleEventType.BEGIN_QUIESCING)
                projection = self.projection()
            if projection.state.status is CampaignStatus.QUIESCING:
                self._append_transition(directive_id, LifecycleEventType.MARK_PAUSED)
        return self.projection()

    def require_action_authority(self, action_id: str) -> None:
        projection = self.quiesce_if_requested()
        if action_id in projection.vetoed_action_ids:
            raise ActionVetoed(f"action {action_id} was vetoed")
        if projection.state.status is CampaignStatus.PAUSED:
            raise CampaignPaused(f"campaign {self.campaign_id} is paused")
        if projection.state.status is not CampaignStatus.ACTIVE:
            raise CampaignStopped(
                f"campaign {self.campaign_id} cannot start work while "
                f"{projection.state.status.value}"
            )

    def require_processing_authority(self) -> None:
        """Pause after in-flight execution is safely persisted, before interpretation."""

        projection = self.quiesce_if_requested()
        if projection.state.status is CampaignStatus.PAUSED:
            raise CampaignPaused(f"campaign {self.campaign_id} is paused")
        if projection.state.status is not CampaignStatus.ACTIVE:
            raise CampaignStopped(
                f"campaign {self.campaign_id} cannot process evidence while "
                f"{projection.state.status.value}"
            )
