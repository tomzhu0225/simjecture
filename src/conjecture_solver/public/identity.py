"""Visitor-owned projects and verified identities; no provider tokens are retained."""

import json
import secrets
import time


class Identities:
    def account(self, owner):
        with self.connect() as db:
            row = db.execute(
                "SELECT a.id,a.github_id,a.login,a.name FROM accounts a JOIN visitors v "
                "ON a.id=v.account_id WHERE v.id=?",
                (owner,),
            ).fetchone()
        return dict(row) if row else None

    def authorize_identity(self, owner, github_id, login, name):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.connect(write=True) as db:
            visitor = db.execute("SELECT * FROM visitors WHERE id=?", (owner,)).fetchone()
            if not visitor or visitor["account_id"] or visitor["retiring"] or visitor["expired"]:
                raise ValueError("Sign out before connecting another account")
            account = db.execute(
                "SELECT id FROM accounts WHERE github_id=?", (str(github_id),)
            ).fetchone()
            identifier = account[0] if account else secrets.token_hex(16)
            db.execute(
                "INSERT INTO accounts(id,github_id,login,name,created) VALUES(?,?,?,?,?) "
                "ON CONFLICT(github_id) DO UPDATE SET login=excluded.login,name=excluded.name",
                (identifier, str(github_id), login, name, time.time()),
            )
            db.execute(
                "UPDATE visitors SET token_hash=?,csrf=?,account_id=?,created=? WHERE id=?",
                (self.digest(token), csrf, identifier, time.time(), owner),
            )
        return token, self.visitor(token)

    def oauth_start(self, owner):
        state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
        with self.connect(write=True) as db:
            row = db.execute(
                "SELECT retiring,expired FROM visitors WHERE id=?", (owner,)
            ).fetchone()
            if not row or row["retiring"] or row["expired"]:
                raise ValueError("Guest session ended; reload before signing in")
            db.execute("DELETE FROM oauth_states WHERE expires<?", (time.time(),))
            db.execute(
                "INSERT INTO oauth_states VALUES(?,?,?,?)",
                (self.digest(state), owner, verifier, time.time() + 600),
            )
        return state, verifier

    def oauth_hold(self, owner):
        with self.connect(write=True) as db:
            db.execute(
                "INSERT INTO visitor_leases VALUES(?,?,?) ON CONFLICT(id,visitor) "
                "DO UPDATE SET expires=excluded.expires",
                ("oauth-handoff-lease", owner, time.time() + 120),
            )

    def oauth_consume(self, state):
        with self.connect(write=True) as db:
            row = db.execute(
                "SELECT * FROM oauth_states WHERE digest=? AND expires>?",
                (self.digest(state), time.time()),
            ).fetchone()
            db.execute("DELETE FROM oauth_states WHERE digest=?", (self.digest(state),))
        return dict(row) if row else None

    def create_project(self, owner, name):
        identifier = secrets.token_hex(16)
        with self.connect(write=True) as db:
            count = db.execute(
                "SELECT COUNT(*) FROM projects WHERE " + self.owner_clause(), (owner, owner)
            ).fetchone()[0]
            if count >= 100:
                raise ValueError("Project storage allowance reached")
            db.execute(
                "INSERT INTO projects(id,owner,name,created) VALUES(?,?,?,?)",
                (identifier, owner, name, time.time()),
            )
        return self.project(identifier, owner)

    def projects(self, owner):
        with self.connect() as db:
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM projects WHERE "
                    + self.owner_clause()
                    + " ORDER BY created DESC",
                    (owner, owner),
                )
            ]
        return [self.project(identifier, owner) for identifier in ids]

    def project(self, identifier, owner=None):
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM projects WHERE id=?"
                + (" AND " + self.owner_clause() if owner else ""),
                (identifier, owner, owner) if owner else (identifier,),
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["brief"] = json.loads(row["brief"]) if row["brief"] else None
            result["messages"] = [
                dict(r)
                for r in db.execute(
                    "SELECT id,job,role,content,created FROM messages WHERE project=? ORDER BY id",
                    (identifier,),
                )
            ]
            result["jobs"] = [
                self.job(r[0])
                for r in db.execute(
                    "SELECT id FROM jobs WHERE project=? ORDER BY created", (identifier,)
                )
            ]
        return result

    def save_brief(self, identifier, brief):
        with self.connect(write=True) as db:
            db.execute(
                "UPDATE projects SET brief=?,brief_launched=0 WHERE id=?",
                (json.dumps(brief, allow_nan=False), identifier),
            )

    def finish_project_job(self, job, summary):
        if not job.get("project"):
            return
        with self.connect(write=True) as db:
            if not db.execute(
                "SELECT 1 FROM messages WHERE job=? AND role='assistant'", (job["id"],)
            ).fetchone():
                db.execute(
                    "INSERT INTO messages(project,job,role,content,created) "
                    "VALUES(?,?,'assistant',?,?)",
                    (job["project"], job["id"], summary, time.time()),
                )
