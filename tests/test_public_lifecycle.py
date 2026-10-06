"""Guest lifetime, scientific uploads and frozen hosted campaign contracts."""

import base64
import json
import time

import pytest

from conjecture_solver.public.lifecycle import GuestLifecycle
from conjecture_solver.public.server import COOKIE
from tests.test_public_workspace import app as workspace_app
from tests.test_public_workspace import project, session


@pytest.fixture
def app(tmp_path):
    return workspace_app.__wrapped__(tmp_path)


def visitor(client, app):
    return app.state.store.visitor(client.cookies.get(COOKIE))


def sign_in(client, app, identifier=123):
    row = visitor(client, app)
    token, row = app.state.store.authorize_identity(row["id"], identifier, "scientist", "Scientist")
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    client.headers["X-CSRF-Token"] = row["csrf"]
    return row


def expire_leases(app, owner):
    with app.state.store.connect(write=True) as db:
        db.execute("UPDATE visitor_leases SET expires=? WHERE visitor=?", (time.time() - 1, owner))
        db.execute("UPDATE visitors SET last_seen=? WHERE id=?", (time.time() - 1000, owner))


def test_last_guest_tab_erases_scientific_content_and_revokes_cookie(app):
    client = session(app)
    p = project(client)
    row = visitor(client, app)
    root = app.state.store.root
    files = root / "projects" / p["id"] / "files"
    files.mkdir(parents=True, exist_ok=True)
    (files / "private.txt").write_text("my research")
    j = client.post(
        "/api/workspace/message", json={"project": p["id"], "message": "my hypothesis"}
    ).json()
    directory = root / "jobs" / j["id"]
    directory.mkdir(parents=True)
    (directory / "my-artifact.json").write_text("private data")
    gc = GuestLifecycle(app.state.store, lambda: {})
    gc.lease(row["id"], "first-tab-123456789")
    expire_leases(app, row["id"])
    gc.tick()  # Cancel queued work before erasure.
    gc.tick()
    assert not directory.exists() and not files.parent.exists()
    assert app.state.store.visitor(client.cookies.get(COOKIE)) is None
    assert app.state.store.job(j["id"])["hypothesis"] == ""
    assert client.get("/api/workspace/bootstrap").status_code == 401
    with app.state.store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_other_tab_refresh_and_oauth_transition_keep_guest_work(app):
    client = session(app)
    p = project(client)
    row = visitor(client, app)
    gc = GuestLifecycle(app.state.store, lambda: {})
    gc.lease(row["id"], "tab-one-123456789")
    gc.lease(row["id"], "tab-two-123456789")
    with app.state.store.connect(write=True) as db:
        db.execute("UPDATE visitor_leases SET expires=0 WHERE id='tab-one-123456789'")
    gc.tick()
    assert app.state.store.project(p["id"], row["id"])
    expire_leases(app, row["id"])
    app.state.store.oauth_start(row["id"])
    gc.tick()
    assert visitor(client, app)
    gc.lease(row["id"], "refresh-tab-123456789")
    gc.tick()
    assert app.state.store.project(p["id"], row["id"])


def test_signed_in_work_survives_all_tab_leases_expiring(app):
    client = session(app)
    p = project(client)
    row = sign_in(client, app)
    expire_leases(app, row["id"])
    gc = GuestLifecycle(app.state.store, lambda: {})
    gc.tick()
    assert gc.lease(row["id"], "member-tab-123456789") == {"temporary": False}
    assert client.get("/api/workspace/project?id=" + p["id"]).status_code == 200


def test_signed_in_upload_is_private_and_click_defaults_to_download(app):
    client, other = session(app), session(app)
    p = project(client)
    sign_in(client, app)
    body = {
        "project": p["id"],
        "name": "inputs.json",
        "data": base64.b64encode(b'{"dt":0.01}').decode(),
    }
    assert client.post("/api/workspace/upload", json=body).status_code == 200
    route = f"/api/workspace/file?id={p['id']}&path=inputs.json"
    response = client.get(route)
    assert response.status_code == 200 and response.json() == {"dt": 0.01}
    assert response.headers["content-disposition"] == 'attachment; filename="inputs.json"'
    assert other.get(route).status_code == 404
    assert other.post("/api/workspace/upload", json=body).status_code == 403
    # Replacing the file is permitted; unsafe paths and executable browser markup are not.
    body["data"] = base64.b64encode(b"new content").decode()
    assert client.post("/api/workspace/upload", json=body).status_code == 200
    for name in ("../escape.json", "/absolute.json", ".executor-policy.json", "nested/file.json"):
        assert client.post("/api/workspace/upload", json={**body, "name": name}).status_code == 400
    body.update(name="plot.html", data=base64.b64encode(b"<script>alert(1)</script>").decode())
    assert client.post("/api/workspace/upload", json=body).status_code == 200
    preview = client.get(f"/api/workspace/preview?id={p['id']}&path=plot.html")
    assert preview.headers["content-disposition"].startswith("attachment;")
    assert "sandbox" in preview.headers["content-security-policy"]


def test_campaign_freezes_brief_and_honors_shorter_execution_budget(app):
    client = session(app)
    p = project(client)
    brief = {
        "project": p["id"],
        "question": "Does the pendulum conserve energy?",
        "hours": 0.001,
        "constraints": "Use SciPy; retain raw trajectories",
        "success_criteria": "Timestep convergence",
    }
    assert client.post("/api/workspace/brief", json=brief).status_code == 200
    response = client.post("/api/workspace/launch", json={"project": p["id"]})
    assert response.status_code == 200, response.text
    job = app.state.store.jobs(visitor(client, app)["id"])[0]
    assert job["wall_seconds"] == 4
    assert job["study_brief"]["constraints"] == brief["constraints"]
    client.post("/api/workspace/brief", json={**brief, "constraints": "Changed after queuing"})
    assert app.state.store.job(job["id"])["study_brief"]["constraints"] == brief["constraints"]
    claimed = app.state.store.claim()
    assert claimed["deadline"] - claimed["started"] == 4


@pytest.mark.parametrize("hours", [True, float("nan"), float("inf"), 1e308, -1, 0])
def test_invalid_guest_time_budgets_never_become_unbounded(app, hours):
    client = session(app)
    p = project(client)
    with pytest.raises(ValueError):
        app.state.workspace.brief(app.state.store.project(p["id"]), {"hours": hours})


def test_private_gateway_required_for_general_execution(tmp_path, monkeypatch):
    from argparse import Namespace

    from conjecture_solver.public.server import serve

    (tmp_path / "settings.json").write_text(json.dumps({"executor_qualified": True}))
    called = []
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: called.append(kwargs))
    args = Namespace(
        root=tmp_path, host="127.0.0.1", port=8788, development_http=False, unix_socket=None
    )
    with pytest.raises(ValueError, match="private Unix HTTP socket"):
        serve(args)
    assert not called


def test_executor_never_collects_symlinks_or_hardlinks(tmp_path):
    import io
    import zipfile

    from conjecture_solver.public.lab_broker import collect, safe_name

    private = tmp_path / "private.txt"
    private.write_text("host secret")
    work = tmp_path / "work"
    work.mkdir()
    (work / "escape.txt").symlink_to(private)
    with zipfile.ZipFile(io.BytesIO(collect(work, ["*"]))) as archive:
        assert archive.namelist() == []
    (work / "escape.txt").unlink()
    (work / "linked.txt").hardlink_to(private)
    with pytest.raises(ValueError, match="unlinked files"):
        collect(work, ["*"])
    for name in ("../../host", "/etc/passwd", ".executor-policy.json"):
        with pytest.raises(ValueError):
            safe_name(name)


def test_console_reads_open_descriptor_after_job_replaces_path(tmp_path):
    from conjecture_solver.public.lab_broker import console_text

    private = tmp_path / "private"
    private.write_bytes(b"operator secret")
    console = tmp_path / "console"
    with console.open("w+b") as stream:
        stream.write(b"actual experiment output")
        stream.flush()
        console.unlink()
        console.symlink_to(private)
        assert console_text(stream) == "actual experiment output"


def test_binary_console_does_not_flood_model_context(tmp_path):
    from conjecture_solver.public.lab_broker import console_text

    with (tmp_path / "binary").open("w+b") as stream:
        stream.write(b"\x00\xff" * 5000)
        stream.flush()
        text = console_text(stream)
        assert "Binary console output omitted" in text and len(text) < 120
