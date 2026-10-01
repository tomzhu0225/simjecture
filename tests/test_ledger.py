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



def test_concurrent_writers_preserve_chain_and_idempotency(tmp_path) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    path = tmp_path / "events.sqlite"
    with SQLiteEventLedger(path):
        pass
    workers = 6
    barrier = Barrier(workers)

    def append_events(worker: int) -> int:
        inserted = 0
        with SQLiteEventLedger(path) as ledger:
            for iteration in range(10):
                barrier.wait(timeout=10)
                result = ledger.append(
                    campaign_id="campaign_1",
                    event_type="value_recorded",
                    aggregate_type="test",
                    aggregate_id="test_1",
                    payload={"iteration": iteration},
                    idempotency_key=f"shared_{iteration}" if iteration % 2 else None,
                )
                inserted += result.inserted
        return inserted

    with ThreadPoolExecutor(max_workers=workers) as pool:
        inserted = sum(pool.map(append_events, range(workers)))
    with SQLiteEventLedger(path) as ledger:
        assert inserted == 5 * workers + 5
        assert len(ledger.load("campaign_1")) == inserted
        assert ledger.verify_chain("campaign_1")


def test_failed_append_releases_writer_and_preserves_chain(tmp_path) -> None:
    import sqlite3

    path = tmp_path / "events.sqlite"
    kwargs = dict(
        campaign_id="campaign_1",
        event_type="value_recorded",
        aggregate_type="test",
        aggregate_id="test_1",
        payload={},
    )
    with SQLiteEventLedger(path) as first, SQLiteEventLedger(path) as second:
        first.append(event_id="duplicate", **kwargs)
        with pytest.raises(sqlite3.IntegrityError):
            first.append(event_id="duplicate", **kwargs)
        second.append(**kwargs)
        assert first.verify_chain("campaign_1")
        assert len(first.load("campaign_1")) == 2


def test_reopening_existing_ledger_indexes_incremental_campaign_replay(tmp_path) -> None:
    path = tmp_path / "events.sqlite"
    with SQLiteEventLedger(path) as ledger:
        first = ledger.append(
            campaign_id="campaign_1", event_type="created", aggregate_type="test",
            aggregate_id="test_1", payload={},
        ).event
        ledger.append(
            campaign_id="campaign_2", event_type="created", aggregate_type="test",
            aggregate_id="test_2", payload={},
        )
        last = ledger.append(
            campaign_id="campaign_1", event_type="updated", aggregate_type="test",
            aggregate_id="test_1", payload={"value": 1},
        ).event
        # Simulate a database created before the index existed.
        ledger._connection.execute("DROP INDEX campaign_events_campaign_sequence")
        ledger._connection.commit()
    with SQLiteEventLedger(path) as ledger:
        assert ledger.load("campaign_1", after_sequence=first.sequence) == (last,)
        assert ledger.verify_chain("campaign_1")
        indexes = ledger._connection.execute("PRAGMA index_list(campaign_events)").fetchall()
        assert any(row["name"] == "campaign_events_campaign_sequence" for row in indexes)
