"""Transactional, idempotent event records for interrupted and concurrent studies."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .contracts import canonical, fingerprint


class Journal:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, isolation_level=None, timeout=30)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS events (
            sequence INTEGER PRIMARY KEY,
            study_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            recorded_at REAL NOT NULL,
            payload TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            UNIQUE(study_id,event_id))""")

    def append(self, *, study_id, event_id, kind, payload):
        body = canonical(payload)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self.connection.execute(
                "SELECT kind,payload,event_hash FROM events WHERE study_id=? AND event_id=?",
                (study_id, event_id),
            ).fetchone()
            if existing:
                if existing[:2] != (kind, body):
                    raise ValueError("An idempotency key was reused for different research evidence")
                self.connection.execute("COMMIT")
                return existing[2]
            previous = self.connection.execute(
                "SELECT event_hash FROM events WHERE study_id=? ORDER BY sequence DESC LIMIT 1", (study_id,)
            ).fetchone()
            previous_hash = previous[0] if previous else "0" * 64
            recorded_at = time.time()
            event_hash = fingerprint(
                dict(
                    study_id=study_id,
                    event_id=event_id,
                    kind=kind,
                    recorded_at=recorded_at,
                    payload=payload,
                    previous_hash=previous_hash,
                )
            )
            self.connection.execute(
                "INSERT INTO events(study_id,event_id,kind,recorded_at,payload,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?)",
                (study_id, event_id, kind, recorded_at, body, previous_hash, event_hash),
            )
            self.connection.execute("COMMIT")
            return event_hash
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

    def export(self, study_id):
        rows = self.connection.execute(
            "SELECT event_id,kind,recorded_at,payload,previous_hash,event_hash FROM events WHERE study_id=? ORDER BY sequence",
            (study_id,),
        )
        return [
            dict(
                study_id=study_id,
                event_id=r[0],
                kind=r[1],
                recorded_at=r[2],
                payload=json.loads(r[3]),
                previous_hash=r[4],
                event_hash=r[5],
            )
            for r in rows
        ]

    def close(self):
        self.connection.close()
