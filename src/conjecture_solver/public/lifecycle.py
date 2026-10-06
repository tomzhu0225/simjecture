"""Temporary guest leases; signed-in projects and billing counters are retained."""

import json
import secrets
import shutil
import time
from contextlib import suppress

from ..mvp_launch import read_process_identity
from ..research_service import ResearchService
from .store import TERMINAL


class GuestLifecycle:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings

    def lease(self, visitor, identifier, *, leaving=False):
        if not isinstance(identifier, str) or not 16 <= len(identifier) <= 100:
            raise ValueError("Invalid page lease")
        if self.store.account(visitor):
            return {"temporary": False}
        now = time.time()
        duration = (
            self.settings().get("guest_leave_grace_seconds", 30)
            if leaving
            else self.settings().get("guest_lease_seconds", 180)
        )
        with self.store.connect(write=True) as db:
            row = db.execute(
                "SELECT account_id,retiring,expired FROM visitors WHERE id=?", (visitor,)
            ).fetchone()
            if not row or row["expired"] or row["retiring"]:
                raise ValueError("Guest session ended")
            if row["account_id"]:
                return {"temporary": False}
            db.execute(
                "INSERT INTO visitor_leases VALUES(?,?,?) ON CONFLICT(id,visitor) "
                "DO UPDATE SET expires=excluded.expires",
                (identifier, visitor, now + duration),
            )
            db.execute("UPDATE visitors SET last_seen=? WHERE id=?", (now, visitor))
        return {"temporary": True, "expires_in": duration}

    def tick(self):
        if not self.settings().get("guest_ephemeral", True):
            return
        now = time.time()
        with self.store.connect(write=True) as db:
            # An in-progress OAuth transition protects the guest investigation.
            rows = db.execute(
                "SELECT v.id,v.retiring FROM visitors v WHERE v.account_id IS NULL "
                "AND v.expired=0 AND NOT EXISTS(SELECT 1 FROM oauth_states o "
                "WHERE o.visitor=v.id AND o.expires>?) "
                "AND ((EXISTS(SELECT 1 FROM visitor_leases l WHERE l.visitor=v.id) "
                "AND NOT EXISTS(SELECT 1 FROM visitor_leases l "
                "WHERE l.visitor=v.id AND l.expires>?)) "
                "OR (NOT EXISTS(SELECT 1 FROM visitor_leases l WHERE l.visitor=v.id) "
                "AND v.last_seen<?))",
                (now, now, now - self.settings().get("guest_lease_seconds", 180)),
            ).fetchall()
            for row in rows:
                db.execute(
                    "UPDATE visitors SET retiring=1 WHERE id=? AND account_id IS NULL", (row["id"],)
                )
        for row in rows:
            self.retire(row["id"])

    def retire(self, visitor):
        if self.store.account(visitor):
            return
        with self.store.connect() as db:
            identifiers = [
                r[0] for r in db.execute("SELECT id FROM jobs WHERE owner=?", (visitor,))
            ]
        jobs = [self.store.job(identifier, owner=visitor) for identifier in identifiers]
        waiting = False
        for job in jobs:
            if job["status"] not in TERMINAL:
                self.store.cancel(job["id"], visitor)
                waiting = True
            if job["pid"]:
                actual = read_process_identity(job["pid"])
                expected = json.loads(job["process_identity"]) if job["process_identity"] else None
                if actual and expected and actual.starttime == expected["starttime"]:
                    waiting = True
            root = self.store.root / "jobs" / job["id"] / "study"
            if (root / "research.json").exists():
                with suppress(ValueError, OSError):
                    service = ResearchService(root)
                    for record in service._all("experiments"):
                        if record["status"] in {"queued", "running"}:
                            service.cancel(record["id"], reason="Temporary guest session ended")
                            expected = record.get("worker_identity")
                            actual = (
                                read_process_identity(record.get("pid", 0))
                                if record.get("pid")
                                else None
                            )
                            if actual and expected and actual.starttime == expected["starttime"]:
                                waiting = True
                            else:
                                from ..research_service import put

                                record.update(
                                    status="cancelled",
                                    finished_at=time.time(),
                                    cancellation_confirmed=True,
                                )
                                put(service.root / "experiments" / (record["id"] + ".json"), record)
        if waiting:
            return
        # Reserve final erasure against a concurrent sign-in before deleting paths.
        with self.store.connect(write=True) as db:
            row = db.execute("SELECT account_id FROM visitors WHERE id=?", (visitor,)).fetchone()
            if not row or row["account_id"]:
                return
            db.execute(
                "UPDATE visitors SET expired=1,token_hash=?,csrf='' WHERE id=?",
                (self.store.digest(secrets.token_urlsafe(32)), visitor),
            )
            projects = [
                r[0] for r in db.execute("SELECT id FROM projects WHERE owner=?", (visitor,))
            ]
            for job in jobs:
                db.execute("DELETE FROM events WHERE job=?", (job["id"],))
                db.execute(
                    "UPDATE jobs SET hypothesis='',summary='',project=NULL,study_brief=NULL,"
                    "action=NULL WHERE id=?",
                    (job["id"],),
                )
            db.execute(
                "DELETE FROM messages WHERE project IN (SELECT id FROM projects WHERE owner=?)",
                (visitor,),
            )
            db.execute("DELETE FROM projects WHERE owner=?", (visitor,))
            db.execute("DELETE FROM oauth_states WHERE visitor=?", (visitor,))
            db.execute("DELETE FROM visitor_leases WHERE visitor=?", (visitor,))
        for job in jobs:
            shutil.rmtree(self.store.root / "jobs" / job["id"], ignore_errors=True)
        for project in projects:
            shutil.rmtree(self.store.root / "projects" / project, ignore_errors=True)
