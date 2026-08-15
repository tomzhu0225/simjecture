from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from conjecture_solver.action_handlers import (
    blinded_campaign_handlers,
    build_blinded_multi_action_graph,
)
from conjecture_solver.confirmation import ConfirmationDisposition, PICConfirmationReport
from conjecture_solver.control import CampaignControl, CampaignPaused, ControlDirective
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.models import CampaignStatus, EvidenceRole, InterventionType
from conjecture_solver.orchestration import (
    ActionContext,
    ActionExecution,
    ActionExecutionError,
    ActionFailureKind,
    ActionOrigin,
    ActionStatus,
    CampaignAction,
    CampaignActionGraph,
    CampaignBudget,
    InjectedOrchestrationCrash,
    MultiActionCampaignRunner,
    MultiActionCrashPoint,
    OrchestrationDisposition,
)
from conjecture_solver.search import BlindedSearchRequest, offline_ai_fixture_strategy


class IdempotentFixtureHandler:
    def __init__(self) -> None:
        self.outputs: dict[str, ActionExecution] = {}
        self.physical_executions = 0
        self.invocations = 0

    def execute(
        self,
        context: ActionContext,
        action: CampaignAction,
        dependencies: dict[str, ActionExecution],
    ) -> ActionExecution:
        del context
        self.invocations += 1
        existing = self.outputs.get(action.id)
        if existing is not None:
            return existing
        self.physical_executions += 1
        output: dict[str, object] = {
            "action": action.id,
            "dependencies": sorted(dependencies),
        }
        canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
        execution = ActionExecution(
            action_id=action.id,
            evidence_eligible=True,
            output=output,
            output_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        )
        self.outputs[action.id] = execution
        return execution


class FailingFixtureHandler:
    def execute(
        self,
        context: ActionContext,
        action: CampaignAction,
        dependencies: dict[str, ActionExecution],
    ) -> ActionExecution:
        del context, action, dependencies
        raise ActionExecutionError(
            ActionFailureKind.NUMERICAL,
            "fixture solver did not converge",
        )


def action(
    action_id: str,
    *,
    dependencies: tuple[str, ...] = (),
    role: EvidenceRole = EvidenceRole.DISCOVERY,
    group: str = "fixture_solver",
    units: float = 1.0,
) -> CampaignAction:
    return CampaignAction(
        id=action_id,
        action_type="fixture",
        purpose="exercise orchestration semantics",
        dependencies=dependencies,
        evidence_role=role,
        independence_group=group,
        origin=ActionOrigin.DETERMINISTIC,
        budget_units=units,
    )


def graph(
    *actions: CampaignAction,
    total_units: float | None = None,
) -> CampaignActionGraph:
    return CampaignActionGraph(
        id="fixture_action_graph",
        actions=actions,
        budget=CampaignBudget(
            total_units=(
                sum(item.budget_units for item in actions)
                if total_units is None
                else total_units
            )
        ),
    )


def control_directive(
    intervention_type: InterventionType,
    *,
    revision: int,
    action_id: str | None = None,
) -> ControlDirective:
    payload = {"action_id": action_id} if action_id is not None else {}
    return ControlDirective(
        id=f"orchestration_control_{intervention_type.value}_{revision}",
        campaign_id="campaign_orchestration_control",
        actor="human_operator",
        intervention_type=intervention_type,
        reason="orchestration control test",
        scope="future_actions",
        expected_revision=revision,
        payload=payload,
    )


def test_action_graph_rejects_cycles_and_nonindependent_confirmation() -> None:
    with pytest.raises(ValidationError, match="dependency cycle"):
        graph(
            action("one", dependencies=("two",)),
            action("two", dependencies=("one",)),
        )

    discovery = action("discovery")
    with pytest.raises(ValidationError, match="different independence group"):
        graph(
            discovery,
            action(
                "confirmation",
                dependencies=(discovery.id,),
                role=EvidenceRole.CONFIRMATION,
                group=discovery.independence_group,
            ),
        )


@pytest.mark.parametrize("crash_point", list(MultiActionCrashPoint))
def test_every_orchestration_boundary_recovers_exactly_once(
    crash_point: MultiActionCrashPoint,
) -> None:
    one_action = action("recoverable_action", units=2.0)
    campaign_graph = graph(one_action)
    handler = IdempotentFixtureHandler()
    target_action = (
        None
        if crash_point
        in {
            MultiActionCrashPoint.AFTER_GRAPH_REGISTERED,
            MultiActionCrashPoint.AFTER_CAMPAIGN_COMPLETED,
        }
        else one_action.id
    )
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedOrchestrationCrash) as raised:
            MultiActionCampaignRunner(
                campaign_id="campaign_orchestration_recovery",
                ledger=ledger,
                graph=campaign_graph,
                handlers={"fixture": handler},
                crash_at=crash_point,
                crash_action_id=target_action,
            ).run()
        assert raised.value.point is crash_point

        report = MultiActionCampaignRunner(
            campaign_id="campaign_orchestration_recovery",
            ledger=ledger,
            graph=campaign_graph,
            handlers={"fixture": handler},
        ).run()
        event_count = len(ledger.load("campaign_orchestration_recovery"))
        replay = MultiActionCampaignRunner(
            campaign_id="campaign_orchestration_recovery",
            ledger=ledger,
            graph=campaign_graph,
            handlers={"fixture": handler},
        ).run()

        assert report == replay
        assert report.disposition is OrchestrationDisposition.COMPLETED
        assert report.spent_units == 2.0
        assert report.remaining_units == 0.0
        assert event_count == 6
        assert len(ledger.load("campaign_orchestration_recovery")) == event_count
        assert ledger.verify_chain("campaign_orchestration_recovery")
        assert handler.physical_executions == 1


def test_budget_exhaustion_blocks_action_and_dependent_work() -> None:
    first = action("first", units=2.0)
    second = action("second", dependencies=(first.id,), units=2.0)
    campaign_graph = graph(first, second, total_units=3.0)
    handler = IdempotentFixtureHandler()
    with SQLiteEventLedger() as ledger:
        report = MultiActionCampaignRunner(
            campaign_id="campaign_budget_exhaustion",
            ledger=ledger,
            graph=campaign_graph,
            handlers={"fixture": handler},
        ).run()

        assert report.disposition is OrchestrationDisposition.INCOMPLETE
        assert report.spent_units == 2.0
        assert report.remaining_units == 1.0
        assert report.action_states[0].status is ActionStatus.COMPLETED
        assert report.action_states[1].status is ActionStatus.BLOCKED
        assert "insufficient budget" in (report.action_states[1].block_reason or "")
        assert handler.physical_executions == 1


def test_numerical_failure_consumes_budget_but_not_physics_evidence() -> None:
    failed = action("failed", units=2.0)
    dependent = action("dependent", dependencies=(failed.id,), units=1.0)
    campaign_graph = graph(failed, dependent)
    with SQLiteEventLedger() as ledger:
        report = MultiActionCampaignRunner(
            campaign_id="campaign_action_failure",
            ledger=ledger,
            graph=campaign_graph,
            handlers={"fixture": FailingFixtureHandler()},
        ).run()

        assert report.disposition is OrchestrationDisposition.INCOMPLETE
        assert report.spent_units == 2.0
        assert report.action_states[0].status is ActionStatus.FAILED
        assert report.action_states[0].execution is None
        assert report.action_states[0].failure is not None
        assert report.action_states[0].failure.kind is ActionFailureKind.NUMERICAL
        assert report.action_states[1].status is ActionStatus.BLOCKED


def test_veto_prevents_budget_reservation_and_handler_execution() -> None:
    candidate = action("vetoed_action")
    campaign_graph = graph(candidate)
    handler = IdempotentFixtureHandler()
    with SQLiteEventLedger() as ledger:
        control = CampaignControl(
            campaign_id="campaign_orchestration_control",
            ledger=ledger,
        )
        control.issue(
            control_directive(
                InterventionType.ACTION_VETO,
                revision=0,
                action_id=candidate.id,
            )
        )
        report = MultiActionCampaignRunner(
            campaign_id="campaign_orchestration_control",
            ledger=ledger,
            graph=campaign_graph,
            handlers={"fixture": handler},
            control=control,
        ).run()

        assert report.action_states[0].status is ActionStatus.VETOED
        assert report.spent_units == 0.0
        assert handler.physical_executions == 0
        assert not any(
            event.event_type == "action_budget_reserved"
            for event in ledger.load("campaign_orchestration_control")
        )


def test_pause_between_actions_then_resume_preserves_budget_and_outputs() -> None:
    first = action("first")
    second = action("second", dependencies=(first.id,))
    campaign_graph = graph(first, second)
    handler = IdempotentFixtureHandler()
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedOrchestrationCrash):
            MultiActionCampaignRunner(
                campaign_id="campaign_orchestration_control",
                ledger=ledger,
                graph=campaign_graph,
                handlers={"fixture": handler},
                crash_at=MultiActionCrashPoint.AFTER_ACTION_COMPLETED,
                crash_action_id=first.id,
            ).run()
        control = CampaignControl(
            campaign_id="campaign_orchestration_control",
            ledger=ledger,
        )
        control.issue(control_directive(InterventionType.PAUSE, revision=0))
        with pytest.raises(CampaignPaused):
            MultiActionCampaignRunner(
                campaign_id="campaign_orchestration_control",
                ledger=ledger,
                graph=campaign_graph,
                handlers={"fixture": handler},
                control=control,
            ).run()
        assert control.projection().state.status is CampaignStatus.PAUSED
        assert handler.physical_executions == 1

        control.issue(control_directive(InterventionType.RESUME, revision=1))
        report = MultiActionCampaignRunner(
            campaign_id="campaign_orchestration_control",
            ledger=ledger,
            graph=campaign_graph,
            handlers={"fixture": handler},
            control=control,
        ).run()
        assert report.disposition is OrchestrationDisposition.COMPLETED
        assert report.spent_units == 2.0
        assert handler.physical_executions == 2


def test_pause_during_running_action_defers_commit_until_resume() -> None:
    running = action("running_action", units=2.0)
    campaign_graph = graph(running)
    handler = IdempotentFixtureHandler()
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedOrchestrationCrash):
            MultiActionCampaignRunner(
                campaign_id="campaign_orchestration_control",
                ledger=ledger,
                graph=campaign_graph,
                handlers={"fixture": handler},
                crash_at=MultiActionCrashPoint.AFTER_ACTION_STARTED,
                crash_action_id=running.id,
            ).run()
        control = CampaignControl(
            campaign_id="campaign_orchestration_control",
            ledger=ledger,
        )
        control.issue(control_directive(InterventionType.PAUSE, revision=0))
        with pytest.raises(CampaignPaused):
            MultiActionCampaignRunner(
                campaign_id="campaign_orchestration_control",
                ledger=ledger,
                graph=campaign_graph,
                handlers={"fixture": handler},
                control=control,
            ).run()
        event_types = [
            event.event_type for event in ledger.load("campaign_orchestration_control")
        ]
        assert "action_completed" not in event_types
        assert handler.physical_executions == 1

        control.issue(control_directive(InterventionType.RESUME, revision=1))
        report = MultiActionCampaignRunner(
            campaign_id="campaign_orchestration_control",
            ledger=ledger,
            graph=campaign_graph,
            handlers={"fixture": handler},
            control=control,
        ).run()
        assert report.disposition is OrchestrationDisposition.COMPLETED
        assert report.spent_units == 2.0
        assert handler.physical_executions == 1
        assert handler.invocations == 2


def test_real_blinded_discovery_and_pic_confirmation_use_general_action_graph() -> None:
    request = BlindedSearchRequest()
    campaign_graph = build_blinded_multi_action_graph(
        request,
        offline_ai_fixture_strategy(request),
    )
    with SQLiteEventLedger() as ledger:
        report = MultiActionCampaignRunner(
            campaign_id="campaign_real_multi_action",
            ledger=ledger,
            graph=campaign_graph,
            handlers=blinded_campaign_handlers(),
        ).run()
        event_count = len(ledger.load("campaign_real_multi_action"))
        replay = MultiActionCampaignRunner(
            campaign_id="campaign_real_multi_action",
            ledger=ledger,
            graph=campaign_graph,
            handlers=blinded_campaign_handlers(),
        ).run()

        assert report == replay
        assert report.disposition is OrchestrationDisposition.COMPLETED
        assert report.spent_units == 44.0
        assert report.remaining_units == 0.0
        assert event_count == 57
        assert len(ledger.load("campaign_real_multi_action")) == event_count
        assert ledger.verify_chain("campaign_real_multi_action")
        assert all(
            state.status is ActionStatus.COMPLETED
            and state.decision is not None
            and state.execution is not None
            for state in report.action_states
        )
        confirmation = PICConfirmationReport.model_validate(
            report.action_states[1].execution.output["confirmation_report"]
        )
        assert confirmation.disposition is ConfirmationDisposition.CONFIRMED
