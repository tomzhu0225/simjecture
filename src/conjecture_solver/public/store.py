"""Durable visitor ownership, admission, and actual provider-request reservations."""

from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .identity import Identities

TERMINAL = {"completed", "failed", "cancelled", "budget_exhausted", "interrupted", "unresolved"}


class LimitReached(ValueError):
    pass


class CapacityUnavailable(LimitReached):
    pass


class RateLimited(LimitReached):
    def __init__(self, delay):
        self.delay = delay
        super().__init__("Waiting for shared model capacity")


class Store(Identities):
    def capacity_available(self):
        path = self.root / "settings.json"
        settings = json.loads(path.read_text()) if path.exists() else {}
        return shutil.disk_usage(self.root).free >= settings.get("minimum_free_bytes", 1024**3)

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.root / "public.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS visitors (
                    id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
                    csrf TEXT NOT NULL, created REAL NOT NULL, ip_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES visitors(id),
                    mode TEXT NOT NULL, hypothesis TEXT NOT NULL, status TEXT NOT NULL,
                    created REAL NOT NULL, started REAL, finished REAL, deadline REAL,
                    wall_seconds INTEGER NOT NULL, pid INTEGER, process_identity TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0, summary TEXT NOT NULL DEFAULT '');
                CREATE INDEX IF NOT EXISTS job_owner ON jobs(owner,created);
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, github_id TEXT UNIQUE NOT NULL,
                    login TEXT NOT NULL, name TEXT NOT NULL, created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES visitors(id),
                    name TEXT NOT NULL, created REAL NOT NULL, brief TEXT,
                    brief_launched INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY, project TEXT NOT NULL REFERENCES projects(id),
                    job TEXT REFERENCES jobs(id), role TEXT NOT NULL, content TEXT NOT NULL,
                    created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS oauth_states (
                    digest TEXT PRIMARY KEY, visitor TEXT NOT NULL REFERENCES visitors(id),
                    verifier TEXT NOT NULL, expires REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, job TEXT NOT NULL REFERENCES jobs(id),
                    created REAL NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS job_event ON events(job,id);
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, job TEXT NOT NULL REFERENCES jobs(id),
                    role TEXT NOT NULL, created REAL NOT NULL, finished REAL,
                    status TEXT NOT NULL, input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    model TEXT, provider_request_id TEXT, http_status INTEGER,
                    context_bytes INTEGER NOT NULL DEFAULT 0, finish_reason TEXT,
                    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
                    reasoning_tokens INTEGER NOT NULL DEFAULT 0);
            """)
            migrations = {
                "requests": {
                    "context_bytes": "INTEGER NOT NULL DEFAULT 0",
                    "finish_reason": "TEXT",
                    "cached_input_tokens": "INTEGER NOT NULL DEFAULT 0",
                    "reasoning_tokens": "INTEGER NOT NULL DEFAULT 0",
                },
                "visitors": {
                    "account_id": "TEXT REFERENCES accounts(id)",
                    "last_seen": "REAL",
                    "retiring": "INTEGER NOT NULL DEFAULT 0",
                    "expired": "INTEGER NOT NULL DEFAULT 0",
                },
                "jobs": {
                    "project": "TEXT REFERENCES projects(id)",
                    "quota_key": "TEXT",
                    "action": "TEXT",
                    "privileged": "INTEGER NOT NULL DEFAULT 0",
                    "study_brief": "TEXT",
                    "deleted": "INTEGER NOT NULL DEFAULT 0",
                },
                "projects": {"deleting": "INTEGER NOT NULL DEFAULT 0"},
            }
            for table, additions in migrations.items():
                columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for name, declaration in additions.items():
                    if name not in columns:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
            db.execute(
                "UPDATE jobs SET quota_key='guest:'||(SELECT ip_hash FROM visitors "
                "WHERE visitors.id=jobs.owner) WHERE quota_key IS NULL"
            )
            db.execute("UPDATE visitors SET last_seen=created WHERE last_seen IS NULL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS visitor_leases (id TEXT NOT NULL,"
                "visitor TEXT NOT NULL REFERENCES visitors(id), expires REAL NOT NULL,"
                "PRIMARY KEY(id,visitor))"
            )
        self.path.chmod(0o600)

    @contextmanager
    def connect(self, *, write=False):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def visitor(self, token):
        if not token or len(token) > 128:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM visitors WHERE token_hash=? AND created>? "
                "AND expired=0 AND retiring=0",
                (self.digest(token), time.time() - 30 * 86400),
            ).fetchone()
        return dict(row) if row else None

    def create_visitor(self, ip, *, max_per_day=10):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        ip_hash = self.digest(ip)
        identifier = secrets.token_hex(16)
        with self.connect(write=True) as db:
            count = db.execute(
                "SELECT COUNT(*) FROM visitors WHERE ip_hash=? AND created>?",
                (ip_hash, time.time() - 86400),
            ).fetchone()[0]
            if count >= max_per_day:
                raise LimitReached("Daily visitor limit reached for this connection")
            db.execute(
                "INSERT INTO visitors(id,token_hash,csrf,created,ip_hash,last_seen) "
                "VALUES(?,?,?,?,?,?)",
                (identifier, self.digest(token), csrf, time.time(), ip_hash, time.time()),
            )
        return token, self.visitor(token)

    @staticmethod
    def owner_clause(column="owner"):
        return (
            f"{column} IN (SELECT id FROM visitors WHERE id=? OR account_id="
            "(SELECT account_id FROM visitors WHERE id=?))"
        )

    def quota(self, owner, limits):
        with self.connect() as db:
            visitor = db.execute("SELECT * FROM visitors WHERE id=?", (owner,)).fetchone()
            key = (
                "account:" + visitor["account_id"]
                if visitor["account_id"]
                else "guest:" + visitor["ip_hash"]
            )
            rows = db.execute(
                "SELECT mode,status,started FROM jobs WHERE quota_key=? AND "
                "(started>? OR status='queued')",
                (key, time.time() - 86400),
            ).fetchall()
        result = {"key": key, "tier": "member" if visitor["account_id"] else "guest"}
        for kind in ("interactive", "research"):
            matched = [r for r in rows if (r["mode"] == "research") == (kind == "research")]
            used = sum(r["started"] is not None for r in matched)
            reserved = sum(r["status"] == "queued" for r in matched)
            result[kind] = {
                "limit": limits[kind],
                "used": used,
                "reserved": reserved,
                "remaining": max(0, limits[kind] - used - reserved)
                if limits[kind] is not None
                else None,
            }
        return result

    def enqueue(
        self,
        owner,
        mode,
        hypothesis,
        *,
        wall_seconds=600,
        daily_jobs=2,
        max_queue=20,
        limits=None,
        project=None,
        action=None,
        privileged=False,
        study_brief=None,
    ):
        if not self.capacity_available():
            raise CapacityUnavailable("Trial storage is temporarily full")
        identifier = secrets.token_hex(16)
        with self.connect(write=True) as db:
            visitor = db.execute("SELECT * FROM visitors WHERE id=?", (owner,)).fetchone()
            if not visitor:
                raise ValueError("Unknown visitor")
            if project and not db.execute(
                "SELECT id FROM projects WHERE id=? AND deleting=0 AND " + self.owner_clause(),
                (project, owner, owner),
            ).fetchone():
                raise ValueError("Conversation is unavailable or being deleted")
            active = db.execute(
                "SELECT COUNT(*) FROM jobs WHERE "
                + self.owner_clause()
                + " AND status IN ('queued','running')",
                (owner, owner),
            ).fetchone()[0]
            daily = db.execute(
                "SELECT COUNT(*) FROM jobs j JOIN visitors v ON j.owner=v.id "
                "WHERE v.ip_hash=? AND j.created>?",
                (visitor["ip_hash"], time.time() - 86400),
            ).fetchone()[0]
            key = (
                "account:" + visitor["account_id"]
                if visitor["account_id"]
                else "guest:" + visitor["ip_hash"]
            )
            if limits is not None:
                kind = "research" if mode == "research" else "interactive"
                daily = db.execute(
                    "SELECT COUNT(*) FROM jobs WHERE quota_key=? AND "
                    "(mode='research')=? AND (started>? OR status='queued')",
                    (key, int(kind == "research"), time.time() - 86400),
                ).fetchone()[0]
                daily_jobs = limits[kind]
            if (
                project
                and not db.execute(
                    "SELECT id FROM projects WHERE id=? AND " + self.owner_clause(),
                    (project, owner, owner),
                ).fetchone()
            ):
                raise ValueError("Unknown project")
            queued = db.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0]
            if active:
                raise LimitReached("Finish or cancel your current investigation first")
            if daily_jobs is not None and daily >= daily_jobs:
                raise LimitReached("Daily free investigation allowance reached")
            if queued >= max_queue:
                raise LimitReached("The trial queue is full; please return later")
            db.execute(
                "INSERT INTO jobs(id,owner,mode,hypothesis,status,created,wall_seconds"
                ",project,quota_key,action,privileged,study_brief) "
                "VALUES(?,?,?,?,'queued',?,?,?,?,?,?,?)",
                (
                    identifier,
                    owner,
                    mode,
                    hypothesis,
                    time.time(),
                    wall_seconds,
                    project,
                    key,
                    action,
                    int(privileged),
                    json.dumps(study_brief, allow_nan=False) if study_brief else None,
                ),
            )
            if project and mode == "interactive":
                db.execute(
                    "INSERT INTO messages(project,job,role,content,created) VALUES(?,?,'user',?,?)",
                    (project, identifier, hypothesis, time.time()),
                )
        self.event(identifier, "queued", {"message": "Waiting for an experiment slot"})
        return self.job(identifier, owner=owner)

    def job(self, identifier, *, owner=None):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE id=?"
                + (" AND deleted=0 AND " + self.owner_clause() if owner else ""),
                (identifier, owner, owner) if owner else (identifier,),
            ).fetchone()
            if not row:
                return None
            job = dict(row)
            if job["status"] == "queued":
                job["queue_position"] = db.execute(
                    "SELECT COUNT(*) FROM jobs WHERE status='queued' AND "
                    "(created<? OR (created=? AND id<=?))",
                    (job["created"], job["created"], identifier),
                ).fetchone()[0]
            usage = db.execute(
                "SELECT COUNT(*) requests, COALESCE(SUM(input_tokens),0) input_tokens, "
                "COALESCE(SUM(output_tokens),0) output_tokens FROM requests WHERE job=?",
                (identifier,),
            ).fetchone()
            job["usage"] = dict(usage)
            job["study_brief"] = json.loads(job["study_brief"]) if job["study_brief"] else None
        return job

    def jobs(self, owner):
        with self.connect() as db:
            ids = db.execute(
                "SELECT id FROM jobs WHERE "
                + self.owner_clause()
                + " AND deleted=0 ORDER BY created DESC LIMIT 100",
                (owner, owner),
            ).fetchall()
        return [job for row in ids if (job := self.job(row[0], owner=owner))]

    def claim(self, *, max_active=2):
        now = time.time()
        with self.connect(write=True) as db:
            if (
                db.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
                >= max_active
            ):
                return None
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created,id LIMIT 1"
            ).fetchone()
            if not row:
                return None
            db.execute(
                "UPDATE jobs SET status='running',started=?,deadline=? WHERE id=?",
                (now, now + row["wall_seconds"] if row["wall_seconds"] else None, row["id"]),
            )
        self.event(row["id"], "started", {"message": "Execution budget starts now"})
        return self.job(row["id"])

    def update(self, identifier, *, expected_status=None, **fields):
        allowed = {"pid", "process_identity", "status", "finished", "summary", "cancel_requested"}
        if not fields or set(fields) - allowed:
            raise ValueError("Invalid job update")
        with self.connect(write=True) as db:
            result = db.execute(
                "UPDATE jobs SET "
                + ",".join(k + "=?" for k in fields)
                + " WHERE id=?"
                + (" AND status=?" if expected_status else ""),
                (*fields.values(), identifier, expected_status)
                if expected_status
                else (*fields.values(), identifier),
            )
            return result.rowcount > 0

    def cancel(self, identifier, owner):
        with self.connect(write=True) as db:
            row = db.execute(
                "SELECT status FROM jobs WHERE id=? AND " + self.owner_clause(),
                (identifier, owner, owner),
            ).fetchone()
            if not row:
                return None
            if row[0] not in TERMINAL:
                db.execute(
                    "UPDATE jobs SET cancel_requested=1,status=CASE WHEN status='queued' "
                    "THEN 'cancelled' ELSE status END,finished=CASE WHEN status='queued' "
                    "THEN ? ELSE finished END WHERE id=?",
                    (time.time(), identifier),
                )
        self.event(identifier, "cancel_requested", {"message": "Cancellation requested"})
        return self.job(identifier, owner=owner)

    def event(self, identifier, kind, body):
        with self.connect(write=True) as db:
            db.execute(
                "INSERT INTO events(job,created,kind,body) VALUES(?,?,?,?)",
                (identifier, time.time(), kind, json.dumps(body, allow_nan=False)),
            )

    def events(self, identifier, *, after=0):
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE job=? AND id>? ORDER BY id LIMIT 200",
                (identifier, after),
            ).fetchall()
        return [
            dict(id=r["id"], created=r["created"], kind=r["kind"], **json.loads(r["body"]))
            for r in rows
        ]

    def reserve_request(
        self,
        identifier,
        role,
        *,
        daily=50,
        rpm=20,
        per_job=24,
        token_limit=200000,
        context_bytes=0,
    ):
        now = time.time()
        day = int(now // 86400) * 86400
        request = secrets.token_hex(16)
        with self.connect(write=True) as db:
            job = db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            if not job or job["cancel_requested"] or job["status"] != "running":
                raise LimitReached("Investigation stopped")
            if job["deadline"] is not None and now >= job["deadline"]:
                raise LimitReached("Execution time reached")
            used = db.execute(
                "SELECT COUNT(*), COALESCE(SUM(input_tokens+output_tokens),0) "
                "FROM requests WHERE job=?",
                (identifier,),
            ).fetchone()
            if not job["privileged"] and (used[0] >= per_job or used[1] >= token_limit):
                raise LimitReached("Investigation model budget reached")
            if (
                db.execute("SELECT COUNT(*) FROM requests WHERE created>=?", (day,)).fetchone()[0]
                >= daily
                and not job["privileged"]
            ):
                raise LimitReached("Shared daily model allowance reached")
            if (
                db.execute("SELECT COUNT(*) FROM requests WHERE created>?", (now - 60,)).fetchone()[
                    0
                ]
                >= rpm
            ):
                oldest = db.execute(
                    "SELECT MIN(created) FROM requests WHERE created>?", (now - 60,)
                ).fetchone()[0]
                raise RateLimited(max(0.1, oldest + 60.1 - now))
            db.execute(
                "INSERT INTO requests(id,job,role,created,status,context_bytes) "
                "VALUES(?,?,?,?,'started',?)",
                (request, identifier, role, now, context_bytes),
            )
        return request

    def finish_request(
        self,
        request,
        *,
        status,
        input_tokens=0,
        output_tokens=0,
        model=None,
        provider_request_id=None,
        http_status=None,
        finish_reason=None,
        cached_input_tokens=0,
        reasoning_tokens=0,
    ):
        with self.connect(write=True) as db:
            db.execute(
                "UPDATE requests SET finished=?,status=?,input_tokens=?,output_tokens=?,"
                "model=?,provider_request_id=?,http_status=?,finish_reason=?,"
                "cached_input_tokens=?,reasoning_tokens=? WHERE id=? AND status='started'",
                (
                    time.time(),
                    status,
                    input_tokens,
                    output_tokens,
                    model,
                    provider_request_id,
                    http_status,
                    finish_reason,
                    cached_input_tokens,
                    reasoning_tokens,
                    request,
                ),
            )
