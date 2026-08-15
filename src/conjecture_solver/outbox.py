"""Durable journal for external side effects and their reconciliation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

import httpx
from pydantic import Field, model_validator

from .adapters.base import (
    CapabilityManifest,
    CostEstimate,
    JobReference,
    JobStatus,
    NormalizedResult,
    RawResult,
    RunPackage,
    SimulatorAdapter,
    ValidationReport,
)
from .ledger import SQLiteEventLedger, StoredEvent
from .llm import CompletionResult, ModelRoute
from .models import ExperimentSpec, StrictModel


class ExternalOperation(StrEnum):
    MODEL_COMPLETION = "model_completion"
    SIMULATOR_SUBMISSION = "simulator_submission"
    RESEARCH_TOOL = "research_tool"


class DispatchAttemptStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED_UNKNOWN = "interrupted_unknown"


class OutboxIntent(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    operation: ExternalOperation
    logical_action_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    payload: dict[str, Any]
    payload_hash: str = Field(pattern="^[0-9a-f]{64}$")
    external_idempotency_supported: bool

    @model_validator(mode="after")
    def payload_matches_hash(self) -> OutboxIntent:
        canonical = json.dumps(self.payload, sort_keys=True, separators=(",", ":"))
        if hashlib.sha256(canonical.encode()).hexdigest() != self.payload_hash:
            raise ValueError("outbox payload hash does not match its payload")
        return self


class DispatchAttempt(StrictModel):
    id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    ordinal: int = Field(ge=1)
    status: DispatchAttemptStatus
    started_at: datetime
    completed_at: datetime | None = None
    failure_detail: str | None = None

    @model_validator(mode="after")
    def coherent_attempt(self) -> DispatchAttempt:
        if self.status is DispatchAttemptStatus.STARTED:
            if self.completed_at is not None or self.failure_detail is not None:
                raise ValueError("a started dispatch attempt cannot be terminal")
        elif self.completed_at is None:
            raise ValueError("terminal dispatch attempts require completed_at")
        if self.status in {
            DispatchAttemptStatus.FAILED,
            DispatchAttemptStatus.INTERRUPTED_UNKNOWN,
        } and not self.failure_detail:
            raise ValueError("failed or interrupted dispatch requires failure_detail")
        if self.status is DispatchAttemptStatus.SUCCEEDED and self.failure_detail:
            raise ValueError("successful dispatch cannot include failure_detail")
        return self


class ExternalReceipt(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    intent_id: str
    attempt_id: str
    external_id: str | None = None
    response: dict[str, Any]
    response_hash: str = Field(pattern="^[0-9a-f]{64}$")
    received_at: datetime

    @model_validator(mode="after")
    def response_matches_hash(self) -> ExternalReceipt:
        canonical = json.dumps(self.response, sort_keys=True, separators=(",", ":"))
        if hashlib.sha256(canonical.encode()).hexdigest() != self.response_hash:
            raise ValueError("external receipt hash does not match its response")
        return self


@dataclass
class IntentState:
    intent: OutboxIntent
    attempts: list[DispatchAttempt]
    receipt: ExternalReceipt | None = None

    @property
    def active_attempt(self) -> DispatchAttempt | None:
        if self.attempts and self.attempts[-1].status is DispatchAttemptStatus.STARTED:
            return self.attempts[-1]
        return None


class OutboxProjection:
    def __init__(self) -> None:
        self.intents: dict[str, IntentState] = {}

    @classmethod
    def replay(cls, events: tuple[StoredEvent, ...]) -> OutboxProjection:
        state = cls()
        for event in events:
            if event.event_type == "external_intent_registered":
                intent = OutboxIntent.model_validate(event.payload["intent"])
                state.intents[intent.id] = IntentState(intent=intent, attempts=[])
            elif event.event_type == "external_dispatch_started":
                attempt = DispatchAttempt.model_validate(event.payload["attempt"])
                state.intents[attempt.intent_id].attempts.append(attempt)
            elif event.event_type in {
                "external_dispatch_failed",
                "external_dispatch_interrupted",
            }:
                attempt = DispatchAttempt.model_validate(event.payload["attempt"])
                attempts = state.intents[attempt.intent_id].attempts
                if not attempts or attempts[-1].id != attempt.id:
                    raise ValueError("terminal dispatch event has no matching start")
                attempts[-1] = attempt
            elif event.event_type == "external_dispatch_succeeded":
                attempt = DispatchAttempt.model_validate(event.payload["attempt"])
                receipt = ExternalReceipt.model_validate(event.payload["receipt"])
                attempts = state.intents[attempt.intent_id].attempts
                if not attempts or attempts[-1].id != attempt.id:
                    raise ValueError("successful dispatch has no matching start")
                attempts[-1] = attempt
                state.intents[attempt.intent_id].receipt = receipt
        return state


def create_intent(
    *,
    campaign_id: str,
    operation: ExternalOperation,
    logical_action_id: str,
    idempotency_key: str,
    payload: dict[str, Any],
    external_idempotency_supported: bool,
) -> OutboxIntent:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_hash = hashlib.sha256(canonical.encode()).hexdigest()
    identity = hashlib.sha256(
        f"{campaign_id}:{operation.value}:{logical_action_id}:{idempotency_key}:{payload_hash}".encode()
    ).hexdigest()[:20]
    return OutboxIntent(
        id=f"intent_{identity}",
        campaign_id=campaign_id,
        operation=operation,
        logical_action_id=logical_action_id,
        idempotency_key=idempotency_key,
        payload=payload,
        payload_hash=payload_hash,
        external_idempotency_supported=external_idempotency_supported,
    )


class ExternalOutbox:
    def __init__(self, *, campaign_id: str, ledger: SQLiteEventLedger) -> None:
        self.campaign_id = campaign_id
        self.ledger = ledger

    def projection(self) -> OutboxProjection:
        return OutboxProjection.replay(self.ledger.load(self.campaign_id))

    def register(self, intent: OutboxIntent) -> IntentState:
        if intent.campaign_id != self.campaign_id:
            raise ValueError("outbox intent targets a different campaign")
        existing = self.projection().intents.get(intent.id)
        if existing is not None:
            if existing.intent != intent:
                raise ValueError("outbox intent ID cannot be reused with changed content")
            return existing
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type="external_intent_registered",
            aggregate_type="external_intent",
            aggregate_id=intent.id,
            payload={"intent": intent.model_dump(mode="json")},
            idempotency_key=f"{self.campaign_id}:outbox:{intent.id}:registered",
        )
        return self.projection().intents[intent.id]

    def state(self, intent_id: str) -> IntentState:
        try:
            return self.projection().intents[intent_id]
        except KeyError as error:
            raise LookupError(f"unknown outbox intent {intent_id}") from error

    def begin(self, intent_id: str) -> DispatchAttempt:
        state = self.state(intent_id)
        if state.receipt is not None:
            raise ValueError("a completed outbox intent cannot be dispatched again")
        if state.active_attempt is not None:
            raise ValueError("outbox intent already has an active dispatch attempt")
        ordinal = len(state.attempts) + 1
        attempt = DispatchAttempt(
            id=f"dispatch_{intent_id.removeprefix('intent_')}_{ordinal}",
            intent_id=intent_id,
            ordinal=ordinal,
            status=DispatchAttemptStatus.STARTED,
            started_at=datetime.now(UTC),
        )
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type="external_dispatch_started",
            aggregate_type="dispatch_attempt",
            aggregate_id=attempt.id,
            payload={"attempt": attempt.model_dump(mode="json")},
            idempotency_key=f"{self.campaign_id}:outbox:{attempt.id}:started",
        )
        return attempt

    def interrupt_active(self, intent_id: str, detail: str) -> DispatchAttempt:
        state = self.state(intent_id)
        active = state.active_attempt
        if active is None:
            raise ValueError("outbox intent has no active dispatch to interrupt")
        interrupted = active.model_copy(
            update={
                "status": DispatchAttemptStatus.INTERRUPTED_UNKNOWN,
                "completed_at": datetime.now(UTC),
                "failure_detail": detail,
            }
        )
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type="external_dispatch_interrupted",
            aggregate_type="dispatch_attempt",
            aggregate_id=active.id,
            payload={"attempt": interrupted.model_dump(mode="json")},
            idempotency_key=f"{self.campaign_id}:outbox:{active.id}:interrupted",
        )
        return interrupted

    def fail(self, intent_id: str, detail: str) -> DispatchAttempt:
        state = self.state(intent_id)
        active = state.active_attempt
        if active is None:
            raise ValueError("outbox intent has no active dispatch to fail")
        failed = active.model_copy(
            update={
                "status": DispatchAttemptStatus.FAILED,
                "completed_at": datetime.now(UTC),
                "failure_detail": detail,
            }
        )
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type="external_dispatch_failed",
            aggregate_type="dispatch_attempt",
            aggregate_id=active.id,
            payload={"attempt": failed.model_dump(mode="json")},
            idempotency_key=f"{self.campaign_id}:outbox:{active.id}:failed",
        )
        return failed

    def succeed(
        self,
        intent_id: str,
        *,
        response: dict[str, Any],
        external_id: str | None,
    ) -> ExternalReceipt:
        state = self.state(intent_id)
        active = state.active_attempt
        if active is None:
            raise ValueError("outbox intent has no active dispatch to complete")
        completed_at = datetime.now(UTC)
        succeeded = active.model_copy(
            update={
                "status": DispatchAttemptStatus.SUCCEEDED,
                "completed_at": completed_at,
            }
        )
        canonical = json.dumps(response, sort_keys=True, separators=(",", ":"))
        receipt = ExternalReceipt(
            intent_id=intent_id,
            attempt_id=active.id,
            external_id=external_id,
            response=response,
            response_hash=hashlib.sha256(canonical.encode()).hexdigest(),
            received_at=completed_at,
        )
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type="external_dispatch_succeeded",
            aggregate_type="external_intent",
            aggregate_id=intent_id,
            payload={
                "attempt": succeeded.model_dump(mode="json"),
                "receipt": receipt.model_dump(mode="json"),
            },
            idempotency_key=f"{self.campaign_id}:outbox:{active.id}:succeeded",
        )
        return receipt


class OutboxCrashPoint(StrEnum):
    AFTER_INTENT_REGISTERED = "after_intent_registered"
    AFTER_DISPATCH_STARTED = "after_dispatch_started"
    AFTER_EXTERNAL_RESPONSE = "after_external_response"
    AFTER_RECEIPT_COMMITTED = "after_receipt_committed"


class InjectedOutboxCrash(RuntimeError):
    def __init__(self, point: OutboxCrashPoint) -> None:
        super().__init__(f"injected outbox crash at {point.value}")
        self.point = point


class JournaledCompletionClient:
    """Completion client that commits intent before provider dispatch."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        client: Any,
        crash_at: OutboxCrashPoint | None = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.outbox = ExternalOutbox(campaign_id=campaign_id, ledger=ledger)
        self.client = client
        self.crash_at = crash_at

    def _crash(self, point: OutboxCrashPoint) -> None:
        if self.crash_at is point:
            raise InjectedOutboxCrash(point)

    @staticmethod
    def _result_from_receipt(receipt: ExternalReceipt) -> CompletionResult:
        response = receipt.response
        return CompletionResult(
            request_id=str(response["request_id"]),
            model=str(response["model"]),
            content=str(response["content"]),
            finish_reason=str(response["finish_reason"]),
            usage=dict(response["usage"]),
            route=ModelRoute(str(response["route"])),
            route_reason=str(response["route_reason"]),
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> CompletionResult:
        payload: dict[str, Any] = {
            "messages": messages,
            "route": route.value,
            "escalation_reason": escalation_reason,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        request_hash = hashlib.sha256(canonical.encode()).hexdigest()
        intent = create_intent(
            campaign_id=self.campaign_id,
            operation=ExternalOperation.MODEL_COMPLETION,
            logical_action_id=f"model_completion_{request_hash[:16]}",
            idempotency_key=f"model:{request_hash}",
            payload=payload,
            external_idempotency_supported=False,
        )
        state = self.outbox.register(intent)
        self._crash(OutboxCrashPoint.AFTER_INTENT_REGISTERED)
        if state.receipt is not None:
            return self._result_from_receipt(state.receipt)
        if state.active_attempt is not None:
            self.outbox.interrupt_active(
                intent.id,
                "controller restarted with an uncommitted model-call outcome; "
                "the incomplete response is discarded",
            )
        self.outbox.begin(intent.id)
        self._crash(OutboxCrashPoint.AFTER_DISPATCH_STARTED)
        try:
            result = self.client.complete(
                messages,
                route=route,
                escalation_reason=escalation_reason,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except InjectedOutboxCrash:
            raise
        except httpx.TransportError as error:
            self.outbox.interrupt_active(
                intent.id,
                f"{type(error).__name__}: provider transport ended with unknown outcome: "
                f"{error}",
            )
            raise
        except Exception as error:
            self.outbox.fail(intent.id, f"{type(error).__name__}: {error}")
            raise
        self._crash(OutboxCrashPoint.AFTER_EXTERNAL_RESPONSE)
        response = {
            "request_id": result.request_id,
            "model": result.model,
            "content": result.content,
            "finish_reason": result.finish_reason,
            "usage": result.usage,
            "route": result.route.value,
            "route_reason": result.route_reason,
        }
        receipt = self.outbox.succeed(
            intent.id,
            response=response,
            external_id=result.request_id or None,
        )
        self._crash(OutboxCrashPoint.AFTER_RECEIPT_COMMITTED)
        return self._result_from_receipt(receipt)


class JournaledSimulatorAdapter:
    """Adapter decorator that journals and reconciles idempotent submission."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        adapter: SimulatorAdapter,
        crash_at: OutboxCrashPoint | None = None,
    ) -> None:
        self.campaign_id = campaign_id
        self.outbox = ExternalOutbox(campaign_id=campaign_id, ledger=ledger)
        self.adapter = adapter
        self.crash_at = crash_at

    def _crash(self, point: OutboxCrashPoint) -> None:
        if self.crash_at is point:
            raise InjectedOutboxCrash(point)

    def capabilities(self) -> CapabilityManifest:
        return self.adapter.capabilities()

    def validate(self, experiment: ExperimentSpec) -> ValidationReport:
        return self.adapter.validate(experiment)

    def estimate_cost(self, experiment: ExperimentSpec) -> CostEstimate:
        return self.adapter.estimate_cost(experiment)

    def compile_input(self, experiment: ExperimentSpec) -> RunPackage:
        return self.adapter.compile_input(experiment)

    def submit(self, run: RunPackage, *, idempotency_key: str) -> JobReference:
        payload = {
            "run": run.model_dump(mode="json"),
            "adapter": self.adapter.capabilities().adapter_name,
        }
        intent = create_intent(
            campaign_id=self.campaign_id,
            operation=ExternalOperation.SIMULATOR_SUBMISSION,
            logical_action_id=run.experiment_id,
            idempotency_key=idempotency_key,
            payload=payload,
            external_idempotency_supported=True,
        )
        state = self.outbox.register(intent)
        self._crash(OutboxCrashPoint.AFTER_INTENT_REGISTERED)
        if state.receipt is not None:
            return JobReference.model_validate(state.receipt.response["job"])
        if state.active_attempt is not None:
            self.outbox.interrupt_active(
                intent.id,
                "controller restarted before the scheduler receipt committed; "
                "redispatch will use the same external idempotency key",
            )
        self.outbox.begin(intent.id)
        self._crash(OutboxCrashPoint.AFTER_DISPATCH_STARTED)
        try:
            job = self.adapter.submit(run, idempotency_key=idempotency_key)
        except InjectedOutboxCrash:
            raise
        except Exception as error:
            self.outbox.fail(intent.id, f"{type(error).__name__}: {error}")
            raise
        self._crash(OutboxCrashPoint.AFTER_EXTERNAL_RESPONSE)
        receipt = self.outbox.succeed(
            intent.id,
            response={"job": job.model_dump(mode="json")},
            external_id=job.job_id,
        )
        self._crash(OutboxCrashPoint.AFTER_RECEIPT_COMMITTED)
        return JobReference.model_validate(receipt.response["job"])

    def monitor(self, job: JobReference) -> JobStatus:
        return self.adapter.monitor(job)

    def retrieve(self, job: JobReference) -> RawResult:
        return self.adapter.retrieve(job)

    def normalize(self, result: RawResult) -> NormalizedResult:
        return self.adapter.normalize(result)

    def cancel(self, job: JobReference) -> JobStatus:
        return self.adapter.cancel(job)
