"""Append-only event ledger used by the deterministic development slice."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class StoredEvent:
    sequence: int
    campaign_id: str
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    idempotency_key: str | None
    payload: dict[str, Any]
    created_at: str
    previous_hash: str
    event_hash: str


@dataclass(frozen=True)
class AppendResult:
    event: StoredEvent
    inserted: bool


class IdempotencyConflict(ValueError):
    pass


class SQLiteEventLedger:
    """SQLite test implementation.

    Production will implement the same contract in PostgreSQL.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._connection = sqlite3.connect(str(path))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS campaign_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                idempotency_key TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                UNIQUE(campaign_id, idempotency_key)
            )
            """
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SQLiteEventLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> StoredEvent:
        return StoredEvent(
            sequence=row["sequence"],
            campaign_id=row["campaign_id"],
            event_id=row["event_id"],
            event_type=row["event_type"],
            aggregate_type=row["aggregate_type"],
            aggregate_id=row["aggregate_id"],
            idempotency_key=row["idempotency_key"],
            payload=json.loads(row["payload_json"]),
            created_at=row["created_at"],
            previous_hash=row["previous_hash"],
            event_hash=row["event_hash"],
        )

    @staticmethod
    def _hash_event(
        *,
        campaign_id: str,
        event_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        idempotency_key: str | None,
        payload_json: str,
        created_at: str,
        previous_hash: str,
    ) -> str:
        canonical = json.dumps(
            {
                "aggregate_id": aggregate_id,
                "aggregate_type": aggregate_type,
                "campaign_id": campaign_id,
                "created_at": created_at,
                "event_id": event_id,
                "event_type": event_type,
                "idempotency_key": idempotency_key,
                "payload_json": payload_json,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def append(
        self,
        *,
        campaign_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
        event_id: str | None = None,
        created_at: datetime | None = None,
    ) -> AppendResult:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        if idempotency_key is not None:
            existing = self._connection.execute(
                """
                SELECT * FROM campaign_events
                WHERE campaign_id = ? AND idempotency_key = ?
                """,
                (campaign_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                stored = self._from_row(existing)
                if (
                    stored.event_type != event_type
                    or stored.aggregate_type != aggregate_type
                    or stored.aggregate_id != aggregate_id
                    or stored.payload != payload
                ):
                    raise IdempotencyConflict(
                        "an idempotency key cannot be reused for a different logical event"
                    )
                return AppendResult(event=stored, inserted=False)

        prior = self._connection.execute(
            """
            SELECT event_hash FROM campaign_events
            WHERE campaign_id = ? ORDER BY sequence DESC LIMIT 1
            """,
            (campaign_id,),
        ).fetchone()
        previous_hash = prior["event_hash"] if prior else "GENESIS"
        actual_event_id = event_id or f"event_{uuid4().hex}"
        actual_created_at = (created_at or datetime.now(UTC)).isoformat()
        event_hash = self._hash_event(
            campaign_id=campaign_id,
            event_id=actual_event_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            idempotency_key=idempotency_key,
            payload_json=payload_json,
            created_at=actual_created_at,
            previous_hash=previous_hash,
        )
        cursor = self._connection.execute(
            """
            INSERT INTO campaign_events (
                campaign_id, event_id, event_type, aggregate_type, aggregate_id,
                idempotency_key, payload_json, created_at, previous_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                actual_event_id,
                event_type,
                aggregate_type,
                aggregate_id,
                idempotency_key,
                payload_json,
                actual_created_at,
                previous_hash,
                event_hash,
            ),
        )
        self._connection.commit()
        row = self._connection.execute(
            "SELECT * FROM campaign_events WHERE sequence = ?",
            (cursor.lastrowid,),
        ).fetchone()
        assert row is not None
        return AppendResult(event=self._from_row(row), inserted=True)

    def load(self, campaign_id: str, *, after_sequence: int = 0) -> tuple[StoredEvent, ...]:
        rows = self._connection.execute(
            """
            SELECT * FROM campaign_events
            WHERE campaign_id = ? AND sequence > ?
            ORDER BY sequence
            """,
            (campaign_id, after_sequence),
        ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def verify_chain(self, campaign_id: str) -> bool:
        previous_hash = "GENESIS"
        for event in self.load(campaign_id):
            payload_json = json.dumps(event.payload, sort_keys=True, separators=(",", ":"))
            expected = self._hash_event(
                campaign_id=event.campaign_id,
                event_id=event.event_id,
                event_type=event.event_type,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                idempotency_key=event.idempotency_key,
                payload_json=payload_json,
                created_at=event.created_at,
                previous_hash=previous_hash,
            )
            if event.previous_hash != previous_hash or event.event_hash != expected:
                return False
            previous_hash = event.event_hash
        return True
