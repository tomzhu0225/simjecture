"""Conversation deletion is tenant scoped, durable and preserves quota accounting."""

import subprocess
import sys
import time

import pytest

from conjecture_solver.mvp_launch import read_process_identity
from conjecture_solver.public.deletion import ProjectDeletion
from conjecture_solver.public.server import Dispatcher
from tests.test_public_lifecycle import sign_in, visitor
from tests.test_public_workspace import app as workspace_app
from tests.test_public_workspace import project, session


@pytest.fixture
def app(tmp_path):
    return workspace_app.__wrapped__(tmp_path)


def ask(client, identifier):
    response = client.post(
        "/api/workspace/message", json={"project": identifier, "message": "My private study"}
    )
    assert response.status_code == 200
    return response.json()["id"]


def delete(client, identifier):
    return client.post(
        "/api/workspace/delete-project", json={"project": identifier, "confirm": identifier}
    )


def test_delete_erases_content_and_artifacts_but_preserves_usage(app):
    client = session(app)
    account = sign_in(client, app)
    p, kept = project(client), project(client)
    store = app.state.store
    job = ask(client, p["id"])
    store.claim()
    request = store.reserve_request(
        job, "researcher", per_job=10, token_limit=1000, daily=10, rpm=10
    )
    store.finish_request(request, status="completed", input_tokens=20, output_tokens=3)
    store.update(job, status="completed", finished=time.time())
    stale_job = store.job(job)
    store.finish_project_job(stale_job, "Private conclusion")
    files = store.root / "projects" / p["id"] / "files"
    files.mkdir(parents=True)
    (files / "input.txt").write_text("My private input")
    artifacts = store.root / "jobs" / job
    artifacts.mkdir(parents=True)
    (artifacts / "result.txt").write_text("My private result")
    quota = store.quota(account["id"], {"interactive": 20, "research": 2})
    response = delete(client, p["id"])
    assert response.status_code == 200 and response.json()["pending"] is False
    assert not files.parent.exists() and not artifacts.exists()
    assert store.project(p["id"], account["id"]) is None
    assert store.project(kept["id"], account["id"])
    assert client.get("/api/jobs/" + job).status_code == 404
    assert client.get("/api/workspace/project?id=" + p["id"]).status_code == 404
    assert store.quota(account["id"], {"interactive": 20, "research": 2}) == quota
    raw = store.job(job)
    assert raw["hypothesis"] == raw["summary"] == "" and raw["project"] is None
    assert raw["usage"]["input_tokens"] == 20
    store.finish_project_job(stale_job, "Late worker write must not resurrect the conversation")
    with store.connect() as db:
        assert (
            db.execute("SELECT count(*) FROM messages WHERE project=?", (p["id"],)).fetchone()[0]
            == 0
        )
        assert db.execute("SELECT count(*) FROM events WHERE job=?", (job,)).fetchone()[0] == 0
    assert job not in client.get("/api/workspace/bootstrap").text


def test_delete_checks_confirmation_ownership_and_account_aliases(app):
    first, other = session(app), session(app)
    sign_in(first, app, identifier=123)
    p = project(first)
    assert delete(other, p["id"]).status_code == 404
    assert (
        first.post(
            "/api/workspace/delete-project", json={"project": p["id"], "confirm": "wrong"}
        ).status_code
        == 400
    )
    assert first.get("/api/workspace/project?id=" + p["id"]).status_code == 200
    second = session(app)
    sign_in(second, app, identifier=123)
    assert delete(second, p["id"]).status_code == 200
    assert first.get("/api/workspace/project?id=" + p["id"]).status_code == 404


def test_running_deletion_stops_writer_then_finishes_after_service_recovery(app):
    client = session(app)
    p = project(client)
    store = app.state.store
    job = ask(client, p["id"])
    store.claim()
    files = store.root / "projects" / p["id"] / "files"
    files.mkdir(parents=True)
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import time; from pathlib import Path\nwhile True:\n"
            " Path('writing.txt').write_text('active'); time.sleep(.05)",
        ],
        cwd=files,
        start_new_session=True,
    )
    try:
        store.update(
            job,
            pid=process.pid,
            process_identity=read_process_identity(process.pid).model_dump_json(),
        )
        deadline = time.monotonic() + 3
        while not (files / "writing.txt").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        response = delete(client, p["id"])
        assert response.status_code == 200 and response.json()["pending"] is True
        assert files.exists()  # Never erase underneath a still-running writer.
        assert client.get("/api/workspace/project?id=" + p["id"]).status_code == 404
        assert client.get("/api/jobs/" + job).status_code == 404
        assert store.jobs(visitor(client, app)["id"]) == []
        with pytest.raises(ValueError, match="unavailable or being deleted"):
            store.enqueue(
                visitor(client, app)["id"], "interactive", "Race with delete", project=p["id"]
            )
        Dispatcher(store, {}).tick()
        process.wait(timeout=5)
        ProjectDeletion(store).tick()  # New instance resumes the durable tombstone.
        assert not files.parent.exists()
        assert store.job(job)["project"] is None
        assert store.job(job)["status"] == "cancelled"
        assert store.project(p["id"]) is None
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def test_queued_deletion_refunds_only_unused_reservation(app):
    client = session(app)
    p = project(client)
    job = ask(client, p["id"])
    store = app.state.store
    assert (
        store.quota(visitor(client, app)["id"], {"interactive": 5, "research": 1})["interactive"][
            "reserved"
        ]
        == 1
    )
    assert delete(client, p["id"]).json()["pending"] is False
    assert store.claim() is None
    assert store.job(job)["status"] == "cancelled"
    assert (
        store.quota(visitor(client, app)["id"], {"interactive": 5, "research": 1})["interactive"][
            "remaining"
        ]
        == 5
    )
