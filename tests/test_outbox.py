from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from conjecture_solver.adapters.fake import (
    DeterministicKineticAdapter,
    DeterministicKineticScheduler,
)
from conjecture_solver.campaign import CampaignRunner, planted_campaign_problem
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.llm import CompletionResult, ModelRoute
from conjecture_solver.outbox import (
    DispatchAttemptStatus,
    ExternalOperation,
    ExternalOutbox,
    InjectedOutboxCrash,
    JournaledCompletionClient,
    JournaledSimulatorAdapter,
    OutboxCrashPoint,
    OutboxIntent,
    create_intent,
)


class FakeCompletionClient:
    def __init__(self, *, fail_first: bool = False) -> None:
        self.calls = 0
        self.fail_first = fail_first

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResult:
        del messages, escalation_reason, max_tokens, temperature
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("temporary provider outage")
        return CompletionResult(
            request_id=f"provider_request_{self.calls}",
            model="deepseek-v4-flash-0731-fixture",
            content='{"candidate": 1}',
            finish_reason="stop",
            usage={"total_tokens": 12},
            route=route,
            route_reason="offline outbox fixture",
        )


class TimeoutThenCompleteClient(FakeCompletionClient):
    def complete(self, *args: object, **kwargs: object) -> CompletionResult:
        if self.calls == 0:
            self.calls += 1
            raise httpx.ReadTimeout("provider response timed out after request dispatch")
        return super().complete(*args, **kwargs)


def completion_messages() -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "Return JSON."},
        {"role": "user", "content": "Select one bounded candidate."},
    ]


def test_intent_registration_is_idempotent_and_content_addressed() -> None:
    payload = {"request": "bounded model call", "max_tokens": 32}
    intent = create_intent(
        campaign_id="campaign_outbox",
        operation=ExternalOperation.MODEL_COMPLETION,
        logical_action_id="model_action",
        idempotency_key="model:one",
        payload=payload,
        external_idempotency_supported=False,
    )
    with SQLiteEventLedger() as ledger:
        outbox = ExternalOutbox(campaign_id="campaign_outbox", ledger=ledger)
        first = outbox.register(intent)
        second = outbox.register(intent)
        assert first.intent == second.intent
        assert len(ledger.load("campaign_outbox")) == 1

        changed_payload = {"request": "changed", "max_tokens": 32}
        canonical = json.dumps(changed_payload, sort_keys=True, separators=(",", ":"))
        changed = OutboxIntent.model_validate(
            {
                **intent.model_dump(mode="json"),
                "payload": changed_payload,
                "payload_hash": hashlib.sha256(canonical.encode()).hexdigest(),
            }
        )
        with pytest.raises(ValueError, match="changed content"):
            outbox.register(changed)


def test_completed_model_call_replays_without_provider() -> None:
    provider = FakeCompletionClient()
    with SQLiteEventLedger() as ledger:
        client = JournaledCompletionClient(
            campaign_id="campaign_model_outbox",
            ledger=ledger,
            client=provider,
        )
        first = client.complete(completion_messages(), max_tokens=64)
        replay = JournaledCompletionClient(
            campaign_id="campaign_model_outbox",
            ledger=ledger,
            client=provider,
        ).complete(completion_messages(), max_tokens=64)
        projection = ExternalOutbox(
            campaign_id="campaign_model_outbox",
            ledger=ledger,
        ).projection()

        assert first == replay
        assert provider.calls == 1
        assert len(projection.intents) == 1
        state = next(iter(projection.intents.values()))
        assert state.intent.external_idempotency_supported is False
        assert state.receipt is not None
        assert state.receipt.response["content"] == first.content
        assert len(ledger.load("campaign_model_outbox")) == 3
        assert ledger.verify_chain("campaign_model_outbox")


@pytest.mark.parametrize("crash_point", list(OutboxCrashPoint))
def test_model_dispatch_crashes_preserve_one_scientific_receipt(
    crash_point: OutboxCrashPoint,
) -> None:
    provider = FakeCompletionClient()
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedOutboxCrash):
            JournaledCompletionClient(
                campaign_id="campaign_model_crash",
                ledger=ledger,
                client=provider,
                crash_at=crash_point,
            ).complete(completion_messages())
        result = JournaledCompletionClient(
            campaign_id="campaign_model_crash",
            ledger=ledger,
            client=provider,
        ).complete(completion_messages())
        projection = ExternalOutbox(
            campaign_id="campaign_model_crash",
            ledger=ledger,
        ).projection()
        state = next(iter(projection.intents.values()))

        assert result.content == '{"candidate": 1}'
        assert state.receipt is not None
        assert sum(
            attempt.status is DispatchAttemptStatus.SUCCEEDED
            for attempt in state.attempts
        ) == 1
        assert ledger.verify_chain("campaign_model_crash")
        expected_provider_calls = (
            2 if crash_point is OutboxCrashPoint.AFTER_EXTERNAL_RESPONSE else 1
        )
        assert provider.calls == expected_provider_calls
        if crash_point in {
            OutboxCrashPoint.AFTER_DISPATCH_STARTED,
            OutboxCrashPoint.AFTER_EXTERNAL_RESPONSE,
        }:
            assert state.attempts[0].status is DispatchAttemptStatus.INTERRUPTED_UNKNOWN


def test_known_provider_failure_is_journaled_then_retry_can_succeed() -> None:
    provider = FakeCompletionClient(fail_first=True)
    with SQLiteEventLedger() as ledger:
        client = JournaledCompletionClient(
            campaign_id="campaign_model_failure",
            ledger=ledger,
            client=provider,
        )
        with pytest.raises(RuntimeError, match="temporary provider outage"):
            client.complete(completion_messages())
        result = client.complete(completion_messages())
        state = next(
            iter(
                ExternalOutbox(
                    campaign_id="campaign_model_failure",
                    ledger=ledger,
                ).projection().intents.values()
            )
        )

        assert result.request_id == "provider_request_2"
        assert [attempt.status for attempt in state.attempts] == [
            DispatchAttemptStatus.FAILED,
            DispatchAttemptStatus.SUCCEEDED,
        ]
        assert "temporary provider outage" in (state.attempts[0].failure_detail or "")


def test_transport_timeout_is_conservatively_recorded_as_unknown_outcome() -> None:
    provider = TimeoutThenCompleteClient()
    with SQLiteEventLedger() as ledger:
        client = JournaledCompletionClient(
            campaign_id="campaign_model_timeout",
            ledger=ledger,
            client=provider,
        )
        with pytest.raises(httpx.ReadTimeout):
            client.complete(completion_messages())
        result = client.complete(completion_messages())
        state = next(
            iter(
                ExternalOutbox(
                    campaign_id="campaign_model_timeout",
                    ledger=ledger,
                ).projection().intents.values()
            )
        )

        assert result.request_id == "provider_request_2"
        assert [attempt.status for attempt in state.attempts] == [
            DispatchAttemptStatus.INTERRUPTED_UNKNOWN,
            DispatchAttemptStatus.SUCCEEDED,
        ]
        assert "unknown outcome" in (state.attempts[0].failure_detail or "")


@pytest.mark.parametrize("crash_point", list(OutboxCrashPoint))
def test_simulator_submission_reconciles_to_one_external_job(
    crash_point: OutboxCrashPoint,
) -> None:
    scheduler = DeterministicKineticScheduler()
    delegate = DeterministicKineticAdapter(scheduler)
    _, experiment = planted_campaign_problem()
    run = delegate.compile_input(experiment)
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedOutboxCrash):
            JournaledSimulatorAdapter(
                campaign_id="campaign_simulator_crash",
                ledger=ledger,
                adapter=delegate,
                crash_at=crash_point,
            ).submit(run, idempotency_key="stable-scheduler-key")
        job = JournaledSimulatorAdapter(
            campaign_id="campaign_simulator_crash",
            ledger=ledger,
            adapter=DeterministicKineticAdapter(scheduler),
        ).submit(run, idempotency_key="stable-scheduler-key")
        state = next(
            iter(
                ExternalOutbox(
                    campaign_id="campaign_simulator_crash",
                    ledger=ledger,
                ).projection().intents.values()
            )
        )

        assert job.job_id in scheduler.jobs
        assert len(scheduler.jobs) == 1
        assert state.intent.external_idempotency_supported is True
        assert state.receipt is not None
        assert state.receipt.external_id == job.job_id
        assert ledger.verify_chain("campaign_simulator_crash")


def test_campaign_runner_uses_journaled_adapter_without_duplicate_evidence() -> None:
    scheduler = DeterministicKineticScheduler()
    hypothesis, experiment = planted_campaign_problem()
    with SQLiteEventLedger() as ledger:
        adapter = JournaledSimulatorAdapter(
            campaign_id="campaign_journaled_runner",
            ledger=ledger,
            adapter=DeterministicKineticAdapter(scheduler),
        )
        package = CampaignRunner(
            campaign_id="campaign_journaled_runner",
            ledger=ledger,
            adapter=adapter,
            hypothesis=hypothesis,
            experiment=experiment,
        ).run()
        event_count = len(ledger.load("campaign_journaled_runner"))
        replay = CampaignRunner(
            campaign_id="campaign_journaled_runner",
            ledger=ledger,
            adapter=JournaledSimulatorAdapter(
                campaign_id="campaign_journaled_runner",
                ledger=ledger,
                adapter=DeterministicKineticAdapter(scheduler),
            ),
            hypothesis=hypothesis,
            experiment=experiment,
        ).run()

        assert package.package_hash == replay.package_hash
        assert package.verify_hash()
        assert len(scheduler.jobs) == 1
        assert event_count == 12
        assert len(ledger.load("campaign_journaled_runner")) == event_count
        assert ledger.verify_chain("campaign_journaled_runner")
