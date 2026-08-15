from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from conjecture_solver.ledger import IdempotencyConflict, SQLiteEventLedger


def test_append_and_replay_are_ordered_and_hash_chained() -> None:
    with SQLiteEventLedger() as ledger:
        first = ledger.append(
            campaign_id="campaign_1",
            event_type="campaign_created",
            aggregate_type="campaign",
            aggregate_id="campaign_1",
            payload={"status": "active"},
            idempotency_key="create",
        )
        second = ledger.append(
            campaign_id="campaign_1",
            event_type="pause_requested",
            aggregate_type="campaign",
            aggregate_id="campaign_1",
            payload={},
            idempotency_key="pause_1",
        )
        events = ledger.load("campaign_1")

        assert first.inserted and second.inserted
        assert [event.event_type for event in events] == [
            "campaign_created",
            "pause_requested",
        ]
        assert events[1].previous_hash == events[0].event_hash
        assert ledger.verify_chain("campaign_1")


@given(value=st.integers())
def test_idempotent_replay_does_not_duplicate_event(value: int) -> None:
    with SQLiteEventLedger() as ledger:
        kwargs = {
            "campaign_id": "campaign_1",
            "event_type": "value_recorded",
            "aggregate_type": "test",
            "aggregate_id": "test_1",
            "payload": {"value": value},
            "idempotency_key": "same_logical_action",
        }
        first = ledger.append(**kwargs)
        replay = ledger.append(**kwargs)
        assert first.inserted
        assert not replay.inserted
        assert first.event.sequence == replay.event.sequence
        assert len(ledger.load("campaign_1")) == 1


def test_idempotency_key_reuse_with_changed_payload_is_rejected() -> None:
    with SQLiteEventLedger() as ledger:
        base = {
            "campaign_id": "campaign_1",
            "event_type": "action_proposed",
            "aggregate_type": "action",
            "aggregate_id": "action_1",
            "idempotency_key": "action_key",
        }
        ledger.append(payload={"parameter": 1}, **base)
        with pytest.raises(IdempotencyConflict):
            ledger.append(payload={"parameter": 2}, **base)

