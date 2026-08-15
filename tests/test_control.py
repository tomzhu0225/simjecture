from __future__ import annotations

import pytest

from conjecture_solver.adapters.fake import (
    DeterministicKineticAdapter,
    DeterministicKineticScheduler,
)
from conjecture_solver.campaign import (
    CampaignRunner,
    CrashPoint,
    InjectedCrash,
    planted_campaign_problem,
)
from conjecture_solver.control import (
    ActionVetoed,
    CampaignControl,
    CampaignPaused,
    CampaignStopped,
    ControlDirective,
    StaleControlRevision,
)
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.models import CampaignStatus, InterventionType


def directive(
    intervention_type: InterventionType,
    *,
    revision: int,
    payload: dict[str, object] | None = None,
    directive_id: str | None = None,
) -> ControlDirective:
    return ControlDirective(
        id=directive_id or f"control_{intervention_type.value}_{revision}",
        campaign_id="campaign_control_test",
        actor="human_operator",
        intervention_type=intervention_type,
        reason="deliberate test intervention",
        scope="future_actions",
        expected_revision=revision,
        payload=payload or {},
    )


def runner(
    ledger: SQLiteEventLedger,
    scheduler: DeterministicKineticScheduler,
    *,
    crash_at: CrashPoint | None = None,
) -> CampaignRunner:
    hypothesis, experiment = planted_campaign_problem()
    return CampaignRunner(
        campaign_id="campaign_control_test",
        ledger=ledger,
        adapter=DeterministicKineticAdapter(scheduler),
        hypothesis=hypothesis,
        experiment=experiment,
        crash_at=crash_at,
        control=CampaignControl(campaign_id="campaign_control_test", ledger=ledger),
    )


def test_pause_at_safe_boundary_then_resume_without_duplicate_job() -> None:
    scheduler = DeterministicKineticScheduler()
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedCrash):
            runner(ledger, scheduler, crash_at=CrashPoint.AFTER_ACTION_PLANNED).run()

        control = CampaignControl(campaign_id="campaign_control_test", ledger=ledger)
        control.issue(directive(InterventionType.PAUSE, revision=0))
        with pytest.raises(CampaignPaused):
            runner(ledger, scheduler).run()
        assert control.projection().state.status is CampaignStatus.PAUSED
        assert scheduler.jobs == {}

        control.issue(directive(InterventionType.RESUME, revision=1))
        package = runner(ledger, scheduler).run()
        assert package.verify_hash()
        assert control.projection().state.status is CampaignStatus.ACTIVE
        assert len(scheduler.jobs) == 1
        assert ledger.verify_chain("campaign_control_test")


def test_action_veto_prevents_external_submission() -> None:
    scheduler = DeterministicKineticScheduler()
    with SQLiteEventLedger() as ledger:
        control = CampaignControl(campaign_id="campaign_control_test", ledger=ledger)
        control.issue(
            directive(
                InterventionType.ACTION_VETO,
                revision=0,
                payload={"action_id": "experiment_kinetic_sufficiency_v1"},
            )
        )
        with pytest.raises(ActionVetoed):
            runner(ledger, scheduler).run()
        assert scheduler.jobs == {}
        assert not any(
            event.event_type == "attempt_recorded"
            for event in ledger.load("campaign_control_test")
        )


def test_pause_after_submission_persists_attempt_before_interpretation() -> None:
    scheduler = DeterministicKineticScheduler()
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedCrash):
            runner(ledger, scheduler, crash_at=CrashPoint.AFTER_JOB_COMMITTED).run()
        control = CampaignControl(campaign_id="campaign_control_test", ledger=ledger)
        control.issue(directive(InterventionType.PAUSE, revision=0))

        with pytest.raises(CampaignPaused):
            runner(ledger, scheduler).run()
        event_types = [event.event_type for event in ledger.load("campaign_control_test")]
        assert "attempt_completed" in event_types
        assert "evidence_ingested" not in event_types
        assert control.projection().state.status is CampaignStatus.PAUSED

        control.issue(directive(InterventionType.RESUME, revision=1))
        package = runner(ledger, scheduler).run()
        assert package.verify_hash()
        assert len(scheduler.jobs) == 1


def test_emergency_stop_prevents_external_submission() -> None:
    scheduler = DeterministicKineticScheduler()
    with SQLiteEventLedger() as ledger:
        control = CampaignControl(campaign_id="campaign_control_test", ledger=ledger)
        control.issue(directive(InterventionType.EMERGENCY_STOP, revision=0))
        with pytest.raises(CampaignStopped, match="emergency_stopped"):
            runner(ledger, scheduler).run()
        assert scheduler.jobs == {}


def test_priorities_and_suggestions_are_replayed_without_mutating_history() -> None:
    with SQLiteEventLedger() as ledger:
        control = CampaignControl(campaign_id="campaign_control_test", ledger=ledger)
        control.issue(
            directive(
                InterventionType.PRIORITY_UPDATE,
                revision=0,
                payload={"priorities": {"information_gain": 2.0, "cost": -1.0}},
            )
        )
        control.issue(
            directive(
                InterventionType.TACTICAL_SUGGESTION,
                revision=1,
                payload={"suggestion": "sample the threshold neighborhood next"},
            )
        )
        projection = control.projection()
        assert projection.priorities == {"information_gain": 2.0, "cost": -1.0}
        assert projection.tactical_suggestions == ["sample the threshold neighborhood next"]
        assert projection.state.status is CampaignStatus.ACTIVE


def test_stale_control_command_is_rejected() -> None:
    with SQLiteEventLedger() as ledger:
        control = CampaignControl(campaign_id="campaign_control_test", ledger=ledger)
        control.issue(
            directive(
                InterventionType.PRIORITY_UPDATE,
                revision=0,
                payload={"priorities": {"cost": 1.0}},
            )
        )
        with pytest.raises(StaleControlRevision):
            control.issue(
                directive(
                    InterventionType.TACTICAL_SUGGESTION,
                    revision=0,
                    payload={"suggestion": "this command was based on stale state"},
                )
            )


def test_contract_change_requires_reviewed_branch() -> None:
    with SQLiteEventLedger() as ledger:
        control = CampaignControl(campaign_id="campaign_control_test", ledger=ledger)
        with pytest.raises(ValueError, match="reviewed campaign branch"):
            control.issue(
                directive(
                    InterventionType.CONTRACT_AMENDMENT,
                    revision=0,
                    payload={"new_tolerance": 0.5},
                )
            )
        assert ledger.load("campaign_control_test") == ()
