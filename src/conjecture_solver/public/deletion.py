"""Durable owner-requested deletion; stop writers before erasing scientific content."""

import json
import shutil
import time

from ..mvp_launch import read_process_identity
from ..research_service import ResearchService, put
from .store import TERMINAL


def matching_process(pid, expected):
    actual = read_process_identity(pid) if pid else None
    return bool(actual and expected and actual.starttime == expected["starttime"])


def quiesce_jobs(store, jobs, reason):
    waiting = False
    for job in jobs:
        if job["status"] not in TERMINAL and not job["cancel_requested"]:
            store.cancel(job["id"], job["owner"])
            job = store.job(job["id"])
        expected = json.loads(job["process_identity"]) if job["process_identity"] else None
        alive = matching_process(job["pid"], expected)
        if alive:
            waiting = True  # The dispatcher sends TERM/KILL using the recorded identity.
        elif job["pid"] and expected and job["cancel_requested"] and job["status"] not in TERMINAL:
            store.update(job["id"], status="cancelled", finished=time.time())
            job["status"] = "cancelled"
        if job["status"] not in TERMINAL:
            waiting = True
        root = store.root / "jobs" / job["id"] / "study"
        if not (root / "research.json").exists():
            continue
        service = ResearchService(root)
        for record in service._all("experiments"):
            if record["status"] in {"queued", "running"}:
                service.cancel(record["id"], reason=reason)
            expected = record.get("worker_identity")
            pid = record.get("pid") or (expected or {}).get("pid")
            if matching_process(pid, expected):
                waiting = True
            elif record["status"] in {"queued", "running"}:
                record.update(
                    status="cancelled", finished_at=time.time(), cancellation_confirmed=True
                )
                put(service.root / "experiments" / (record["id"] + ".json"), record)
    return waiting


class ProjectDeletion:
    def __init__(self, store):
        self.store = store

    def request(self, identifier, owner):
        with self.store.connect(write=True) as db:
            project = db.execute(
                "SELECT id FROM projects WHERE id=? AND " + self.store.owner_clause(),
                (identifier, owner, owner),
            ).fetchone()
            if not project:
                raise LookupError("Conversation not found")
            db.execute("UPDATE projects SET deleting=1 WHERE id=?", (identifier,))
            db.execute(
                "UPDATE jobs SET deleted=1,cancel_requested=1,"
                "status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END,"
                "finished=CASE WHEN status='queued' THEN ? ELSE finished END WHERE project=?",
                (time.time(), identifier),
            )
        pending = not self.erase(identifier)
        return {
            "project": identifier,
            "pending": pending,
            "message": "Conversation removed. Stopping its work and deleting saved files."
            if pending
            else "Conversation and saved files deleted",
        }

    def tick(self):
        with self.store.connect() as db:
            identifiers = [r[0] for r in db.execute("SELECT id FROM projects WHERE deleting=1")]
        for identifier in identifiers:
            self.erase(identifier)

    def erase(self, identifier):
        with self.store.connect() as db:
            if not db.execute(
                "SELECT id FROM projects WHERE id=? AND deleting=1", (identifier,)
            ).fetchone():
                return True
            ids = [r[0] for r in db.execute("SELECT id FROM jobs WHERE project=?", (identifier,))]
        jobs = [self.store.job(j) for j in ids]
        if quiesce_jobs(self.store, jobs, "Conversation deleted by its owner"):
            return False
        # The tombstone rejects new jobs/uploads while stopped workers and their
        # workspaces are removed. Keep it durable if filesystem removal fails.
        for path in [
            *(self.store.root / "jobs" / j for j in ids),
            self.store.root / "projects" / identifier,
        ]:
            if path.exists():
                shutil.rmtree(path)
        with self.store.connect(write=True) as db:
            for job in ids:
                db.execute("DELETE FROM events WHERE job=?", (job,))
                db.execute(
                    "UPDATE jobs SET hypothesis='',summary='',project=NULL,study_brief=NULL,"
                    "action=NULL,pid=NULL,process_identity=NULL WHERE id=?",
                    (job,),
                )
            db.execute("DELETE FROM messages WHERE project=?", (identifier,))
            db.execute("DELETE FROM projects WHERE id=? AND deleting=1", (identifier,))
        return True
