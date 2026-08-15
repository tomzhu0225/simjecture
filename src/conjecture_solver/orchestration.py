"""Replayable multi-action campaign graph with durable budget reservations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import Field, model_validator

from .control import ActionVetoed, CampaignControl
from .ledger import SQLiteEventLedger, StoredEvent
from .models import DecisionRecord, EvidenceRole, StrictModel


class ActionOrigin(StrEnum):
    HUMAN = "human"
    AI = "ai"
    DETERMINISTIC = "deterministic"
    MIXED = "mixed"


class ActionStatus(StrEnum):
    PENDING = "pending"
    RESERVED = "reserved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    VETOED = "vetoed"


class ActionFailureKind(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    SPECIFICATION = "specification"
    NUMERICAL = "numerical"
    VALIDITY = "validity"


class OrchestrationDisposition(StrEnum):
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"


class CampaignAction(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    dependencies: tuple[str, ...] = ()
    evidence_role: EvidenceRole
    independence_group: str = Field(min_length=1)
    origin: ActionOrigin
    budget_units: float = Field(gt=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def no_duplicate_dependencies(self) -> CampaignAction:
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("action dependencies must be unique")
        if self.id in self.dependencies:
            raise ValueError("an action cannot depend on itself")
        return self


class CampaignBudget(StrictModel):
    total_units: float = Field(gt=0)
    unit_name: str = Field(default="normalized_compute_unit", min_length=1)


class CampaignActionGraph(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    actions: tuple[CampaignAction, ...] = Field(min_length=1)
    budget: CampaignBudget

    @model_validator(mode="after")
    def valid_dag_and_confirmation_independence(self) -> CampaignActionGraph:
        by_id = {action.id: action for action in self.actions}
        if len(by_id) != len(self.actions):
            raise ValueError("campaign action IDs must be unique")
        for action in self.actions:
            missing = set(action.dependencies) - set(by_id)
            if missing:
                raise ValueError(f"action {action.id} has unknown dependencies: {sorted(missing)}")
            if action.evidence_role is EvidenceRole.CONFIRMATION:
                if not action.dependencies:
                    raise ValueError("confirmation actions require discovery dependencies")
                if any(
                    by_id[dependency].independence_group == action.independence_group
                    for dependency in action.dependencies
                ):
                    raise ValueError(
                        "confirmation action must use a different independence group"
                    )

        remaining = {action.id: set(action.dependencies) for action in self.actions}
        resolved: set[str] = set()
        while remaining:
            ready = {action_id for action_id, deps in remaining.items() if deps <= resolved}
            if not ready:
                raise ValueError("campaign action graph contains a dependency cycle")
            resolved.update(ready)
            for action_id in ready:
                del remaining[action_id]
        return self


class ActionExecution(StrictModel):
    action_id: str
    evidence_eligible: bool
    output: dict[str, Any]
    output_hash: str = Field(pattern="^[0-9a-f]{64}$")
    artifact_hashes: tuple[str, ...] = ()


class ActionFailureRecord(StrictModel):
    action_id: str
    kind: ActionFailureKind
    detail: str = Field(min_length=1)
    budget_consumed: bool = True


class CampaignActionState(StrictModel):
    action: CampaignAction
    status: ActionStatus
    reserved_units: float = Field(ge=0)
    spent_units: float = Field(ge=0)
    decision: DecisionRecord | None = None
    execution: ActionExecution | None = None
    failure: ActionFailureRecord | None = None
    block_reason: str | None = None


class MultiActionCampaignReport(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    campaign_id: str
    graph: CampaignActionGraph
    action_states: tuple[CampaignActionState, ...]
    disposition: OrchestrationDisposition
    spent_units: float = Field(ge=0)
    remaining_units: float = Field(ge=0)
    termination_reason: str


class ActionExecutionError(RuntimeError):
    def __init__(self, kind: ActionFailureKind, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


@dataclass(frozen=True)
class ActionContext:
    campaign_id: str
    ledger: SQLiteEventLedger
    control: CampaignControl | None = None


class ActionHandler(Protocol):
    def execute(
        self,
        context: ActionContext,
        action: CampaignAction,
        dependencies: dict[str, ActionExecution],
    ) -> ActionExecution: ...


class MultiActionCrashPoint(StrEnum):
    AFTER_GRAPH_REGISTERED = "after_graph_registered"
    AFTER_ACTION_SELECTED = "after_action_selected"
    AFTER_BUDGET_RESERVED = "after_budget_reserved"
    AFTER_ACTION_STARTED = "after_action_started"
    AFTER_HANDLER_BEFORE_COMMIT = "after_handler_before_commit"
    AFTER_ACTION_COMPLETED = "after_action_completed"
    AFTER_CAMPAIGN_COMPLETED = "after_campaign_completed"


class InjectedOrchestrationCrash(RuntimeError):
    def __init__(self, point: MultiActionCrashPoint, action_id: str | None = None) -> None:
        suffix = f" for {action_id}" if action_id else ""
        super().__init__(f"injected orchestration crash at {point.value}{suffix}")
        self.point = point
        self.action_id = action_id


class MultiActionProjection:
    def __init__(self) -> None:
        self.graph: CampaignActionGraph | None = None
        self.statuses: dict[str, ActionStatus] = {}
        self.reserved: dict[str, float] = {}
        self.spent: dict[str, float] = {}
        self.executions: dict[str, ActionExecution] = {}
        self.decisions: dict[str, DecisionRecord] = {}
        self.failures: dict[str, ActionFailureRecord] = {}
        self.block_reasons: dict[str, str] = {}
        self.report: MultiActionCampaignReport | None = None

    @classmethod
    def replay(cls, events: tuple[StoredEvent, ...]) -> MultiActionProjection:
        state = cls()
        for event in events:
            if event.event_type == "action_graph_registered":
                state.graph = CampaignActionGraph.model_validate(event.payload["graph"])
                state.statuses = {
                    action.id: ActionStatus.PENDING for action in state.graph.actions
                }
            elif event.event_type == "action_budget_reserved":
                action_id = str(event.payload["action_id"])
                units = float(event.payload["units"])
                state.statuses[action_id] = ActionStatus.RESERVED
                state.reserved[action_id] = units
            elif event.event_type == "action_selected":
                decision = DecisionRecord.model_validate(event.payload["decision"])
                state.decisions[decision.selected_action_id] = decision
            elif event.event_type == "action_started":
                action_id = str(event.payload["action_id"])
                state.statuses[action_id] = ActionStatus.RUNNING
            elif event.event_type == "action_completed":
                execution = ActionExecution.model_validate(event.payload["execution"])
                action_id = execution.action_id
                state.statuses[action_id] = ActionStatus.COMPLETED
                state.executions[action_id] = execution
                state.spent[action_id] = state.reserved.pop(action_id, 0.0)
            elif event.event_type == "action_failed":
                failure = ActionFailureRecord.model_validate(event.payload["failure"])
                action_id = failure.action_id
                state.statuses[action_id] = ActionStatus.FAILED
                state.failures[action_id] = failure
                reserved = state.reserved.pop(action_id, 0.0)
                if failure.budget_consumed:
                    state.spent[action_id] = reserved
            elif event.event_type == "action_blocked":
                action_id = str(event.payload["action_id"])
                state.statuses[action_id] = ActionStatus.BLOCKED
                state.block_reasons[action_id] = str(event.payload["reason"])
            elif event.event_type == "action_vetoed":
                action_id = str(event.payload["action_id"])
                state.statuses[action_id] = ActionStatus.VETOED
                state.block_reasons[action_id] = str(event.payload["reason"])
            elif event.event_type == "multi_action_campaign_completed":
                state.report = MultiActionCampaignReport.model_validate(event.payload["report"])
        return state

    @property
    def spent_units(self) -> float:
        return sum(self.spent.values())

    @property
    def reserved_units(self) -> float:
        return sum(self.reserved.values())

    def remaining_units(self) -> float:
        if self.graph is None:
            return 0.0
        return self.graph.budget.total_units - self.spent_units - self.reserved_units

    def dependency_executions(self, action: CampaignAction) -> dict[str, ActionExecution]:
        return {dependency: self.executions[dependency] for dependency in action.dependencies}


_TERMINAL_ACTION_STATUSES = {
    ActionStatus.COMPLETED,
    ActionStatus.FAILED,
    ActionStatus.BLOCKED,
    ActionStatus.VETOED,
}


class MultiActionCampaignRunner:
    """Execute a registered action DAG with exactly-once scientific commits."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        graph: CampaignActionGraph,
        handlers: dict[str, ActionHandler],
        control: CampaignControl | None = None,
        crash_at: MultiActionCrashPoint | None = None,
        crash_action_id: str | None = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.ledger = ledger
        self.graph = graph
        self.handlers = handlers
        self.control = control
        self.crash_at = crash_at
        self.crash_action_id = crash_action_id
        missing_handlers = {action.action_type for action in graph.actions} - set(handlers)
        if missing_handlers:
            raise ValueError(f"missing action handlers: {sorted(missing_handlers)}")
        if control is not None and control.campaign_id != campaign_id:
            raise ValueError("control plane targets a different campaign")

    def _state(self) -> MultiActionProjection:
        return MultiActionProjection.replay(self.ledger.load(self.campaign_id))

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
            idempotency_key=f"{self.campaign_id}:orchestration:{suffix}",
        )

    def _crash(self, point: MultiActionCrashPoint, action_id: str | None = None) -> None:
        if self.crash_at is not point:
            return
        if self.crash_action_id is not None and self.crash_action_id != action_id:
            return
        raise InjectedOrchestrationCrash(point, action_id)

    def _block(self, action: CampaignAction, reason: str) -> None:
        self._append(
            "action_blocked",
            "campaign_action",
            action.id,
            {"action_id": action.id, "reason": reason},
            f"action:{action.id}:blocked",
        )

    def _build_report(self, state: MultiActionProjection) -> MultiActionCampaignReport:
        action_states = tuple(
            CampaignActionState(
                action=action,
                status=state.statuses[action.id],
                reserved_units=state.reserved.get(action.id, 0.0),
                spent_units=state.spent.get(action.id, 0.0),
                decision=state.decisions.get(action.id),
                execution=state.executions.get(action.id),
                failure=state.failures.get(action.id),
                block_reason=state.block_reasons.get(action.id),
            )
            for action in self.graph.actions
        )
        all_completed = all(
            action_state.status is ActionStatus.COMPLETED for action_state in action_states
        )
        non_completed = [
            action_state.status.value
            for action_state in action_states
            if action_state.status is not ActionStatus.COMPLETED
        ]
        return MultiActionCampaignReport(
            campaign_id=self.campaign_id,
            graph=self.graph,
            action_states=action_states,
            disposition=(
                OrchestrationDisposition.COMPLETED
                if all_completed
                else OrchestrationDisposition.INCOMPLETE
            ),
            spent_units=state.spent_units,
            remaining_units=max(0.0, state.remaining_units()),
            termination_reason=(
                "all registered actions completed"
                if all_completed
                else "terminal non-completed actions: " + ", ".join(non_completed)
            ),
        )

    def run(self) -> MultiActionCampaignReport:
        state = self._state()
        if state.graph is not None and state.graph != self.graph:
            raise ValueError("campaign already exists with a different action graph")
        if state.report is not None:
            return state.report
        if state.graph is None:
            self._append(
                "action_graph_registered",
                "action_graph",
                self.graph.id,
                {"graph": self.graph.model_dump(mode="json")},
                "graph-registered",
            )
        self._crash(MultiActionCrashPoint.AFTER_GRAPH_REGISTERED)

        while True:
            state = self._state()
            made_progress = False
            for action in self.graph.actions:
                status = state.statuses[action.id]
                if status in _TERMINAL_ACTION_STATUSES:
                    continue

                dependency_statuses = {
                    dependency: state.statuses[dependency]
                    for dependency in action.dependencies
                }
                failed_dependencies = {
                    dependency: status
                    for dependency, status in dependency_statuses.items()
                    if status in {
                        ActionStatus.FAILED,
                        ActionStatus.BLOCKED,
                        ActionStatus.VETOED,
                    }
                }
                if failed_dependencies:
                    detail = ", ".join(
                        f"{dependency}={dependency_status.value}"
                        for dependency, dependency_status in failed_dependencies.items()
                    )
                    self._block(action, f"dependency did not complete: {detail}")
                    made_progress = True
                    state = self._state()
                    continue
                if any(
                    dependency_status is not ActionStatus.COMPLETED
                    for dependency_status in dependency_statuses.values()
                ):
                    continue

                if status is ActionStatus.PENDING:
                    if self.control is not None:
                        try:
                            self.control.require_action_authority(action.id)
                        except ActionVetoed as error:
                            self._append(
                                "action_vetoed",
                                "campaign_action",
                                action.id,
                                {"action_id": action.id, "reason": str(error)},
                                f"action:{action.id}:vetoed",
                            )
                            made_progress = True
                            state = self._state()
                            continue
                    if action.budget_units > state.remaining_units() + 1e-12:
                        self._block(
                            action,
                            f"insufficient budget: requires {action.budget_units}, "
                            f"remaining {state.remaining_units()}",
                        )
                        made_progress = True
                        state = self._state()
                        continue
                    if action.id not in state.decisions:
                        ready_candidates = tuple(
                            candidate.id
                            for candidate in self.graph.actions
                            if state.statuses[candidate.id] is ActionStatus.PENDING
                            and all(
                                state.statuses[dependency] is ActionStatus.COMPLETED
                                for dependency in candidate.dependencies
                            )
                            and candidate.budget_units <= state.remaining_units() + 1e-12
                        )
                        last_sequence = max(
                            (
                                event.sequence
                                for event in self.ledger.load(self.campaign_id)
                            ),
                            default=0,
                        )
                        decision = DecisionRecord(
                            id=f"decision_{action.id}",
                            campaign_id=self.campaign_id,
                            checkpoint_id=f"ledger_sequence_{last_sequence}",
                            candidate_action_ids=ready_candidates,
                            selected_action_id=action.id,
                            predicted_outcomes={"scientific_purpose": action.purpose},
                            validator_report={
                                "dependencies_completed": True,
                                "budget_authorized": True,
                                "selection_policy": "declared_graph_order",
                                "evidence_role": action.evidence_role.value,
                            },
                        )
                        self._append(
                            "action_selected",
                            "decision",
                            decision.id,
                            {"decision": decision.model_dump(mode="json")},
                            f"action:{action.id}:selected",
                        )
                        made_progress = True
                        self._crash(
                            MultiActionCrashPoint.AFTER_ACTION_SELECTED,
                            action.id,
                        )
                        state = self._state()
                    self._append(
                        "action_budget_reserved",
                        "campaign_action",
                        action.id,
                        {"action_id": action.id, "units": action.budget_units},
                        f"action:{action.id}:budget-reserved",
                    )
                    made_progress = True
                    self._crash(MultiActionCrashPoint.AFTER_BUDGET_RESERVED, action.id)
                    state = self._state()
                    status = state.statuses[action.id]

                if status is ActionStatus.RESERVED:
                    self._append(
                        "action_started",
                        "campaign_action",
                        action.id,
                        {"action_id": action.id},
                        f"action:{action.id}:started",
                    )
                    made_progress = True
                    self._crash(MultiActionCrashPoint.AFTER_ACTION_STARTED, action.id)
                    state = self._state()
                    status = state.statuses[action.id]

                if status is ActionStatus.RUNNING:
                    handler = self.handlers[action.action_type]
                    try:
                        execution = handler.execute(
                            ActionContext(self.campaign_id, self.ledger, self.control),
                            action,
                            state.dependency_executions(action),
                        )
                    except ActionExecutionError as error:
                        failure = ActionFailureRecord(
                            action_id=action.id,
                            kind=error.kind,
                            detail=error.detail,
                        )
                        self._append(
                            "action_failed",
                            "campaign_action",
                            action.id,
                            {"failure": failure.model_dump(mode="json")},
                            f"action:{action.id}:failed",
                        )
                        made_progress = True
                        state = self._state()
                        continue
                    if execution.action_id != action.id:
                        raise RuntimeError(
                            "action handler returned an execution for another action"
                        )
                    self._crash(
                        MultiActionCrashPoint.AFTER_HANDLER_BEFORE_COMMIT,
                        action.id,
                    )
                    if self.control is not None:
                        self.control.require_processing_authority()
                    self._append(
                        "action_completed",
                        "campaign_action",
                        action.id,
                        {"execution": execution.model_dump(mode="json")},
                        f"action:{action.id}:completed",
                    )
                    made_progress = True
                    self._crash(MultiActionCrashPoint.AFTER_ACTION_COMPLETED, action.id)
                    state = self._state()

            if all(
                status in _TERMINAL_ACTION_STATUSES for status in state.statuses.values()
            ):
                report = self._build_report(state)
                self._append(
                    "multi_action_campaign_completed",
                    "campaign",
                    self.campaign_id,
                    {"report": report.model_dump(mode="json")},
                    "campaign-completed",
                )
                self._crash(MultiActionCrashPoint.AFTER_CAMPAIGN_COMPLETED)
                return self._state().report or report
            if not made_progress:
                raise RuntimeError("action graph made no progress and has no terminal report")
