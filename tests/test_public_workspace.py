"""Hosted identity, permission, and quota boundaries behind the shared workspace."""

import json
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from conjecture_solver.public.server import COOKIE, create_app

TestClient = pytest.importorskip("fastapi.testclient").TestClient


@pytest.fixture
def app(tmp_path):
    (tmp_path / "provider.json").write_text(
        json.dumps(
            {
                "api_key": "private-model-key",
                "model": "provided-model",
                "base_url": "https://provider.example/v1",
                "public_enabled": True,
            }
        )
    )
    (tmp_path / "settings.json").write_text(json.dumps({"public_origin": "http://testserver"}))
    return create_app(tmp_path, dispatch=False, secure_cookies=False)


def session(app):
    client = TestClient(app)
    response = client.post("/api/session", json={}, headers={"Origin": "http://testserver"})
    assert response.status_code == 200
    client.headers.update(
        {"Origin": "http://testserver", "X-CSRF-Token": response.json()["csrf_token"]}
    )
    return client


def project(client):
    response = client.post("/api/workspace/projects", json={"name": "A plasma investigation"})
    assert response.status_code == 200
    return response.json()


def test_shared_assets_and_hosted_bootstrap_never_expose_credentials(app):
    client = session(app)
    app.state.login.credentials = {
        "client_id": "public-client",
        "client_secret": "memory-only-secret",
    }
    boot = client.get("/api/workspace/bootstrap")
    assert boot.json()["hosting"]["quota"]["interactive"]["limit"] == 5
    assert boot.json()["hosting"]["quota"]["research"]["limit"] == 1
    assert boot.json()["hosting"]["login_available"] is True
    assert "private-model-key" not in boot.text and "memory-only-secret" not in boot.text
    assert 'meta name="simjecture-hosted"' in client.get("/workspace").text
    for path in ("/assets/workspace.js", "/assets/workspace.css", "/assets/workspace-monitor.js"):
        assert client.get(path).status_code == 200


def test_every_admin_mutation_is_rejected_even_without_ui(app):
    client = session(app)
    p = project(client)
    for route in (
        "install",
        "api-settings",
        "save-machine",
        "register-tool",
        "upload",
        "prepare-machine",
        "start-benchmark-campaign",
        "prepare-benchmark",
        "grade-benchmark",
        "import-benchmark-reports",
    ):
        assert client.post("/api/workspace/" + route, json={"project": p["id"]}).status_code == 403
    for payload in ({"model": "another-model"}, {"backend": "codex"}, {"reasoning_effort": "high"}):
        assert client.post("/api/workspace/agent", json=payload).status_code == 403
    assert (
        client.post(
            "/api/workspace/message", json={"project": p["id"], "message": "Hi", "command": "id"}
        ).status_code
        == 400
    )


def test_projects_messages_and_studies_are_tenant_scoped(app):
    first, second = session(app), session(app)
    p = project(first)
    assert second.get("/api/workspace/project?id=" + p["id"]).status_code == 404
    assert (
        second.post(
            "/api/workspace/message", json={"project": p["id"], "message": "Hi"}
        ).status_code
        == 404
    )
    admitted = first.post(
        "/api/workspace/message",
        json={"project": p["id"], "message": "Explain the two-stream instability"},
    )
    assert admitted.status_code == 200
    assert second.get("/api/jobs/" + admitted.json()["id"]).status_code == 404
    assert (
        first.get("/api/workspace/project?id=" + p["id"]).json()["messages"][0]["text"]
        == "Explain the two-stream instability"
    )


def test_hosted_benchmarks_expose_only_shipped_public_results(app):
    client = session(app)
    p = project(client)
    root = app.state.store.root
    (root / "benchmark-reports").mkdir()
    (root / "benchmark-reports/private.json").write_text('{"private": "tenant data"}')
    response = client.get("/api/workspace/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert {t["id"] for t in data["official"]["tasks"]} == {"csv-energy", "rz-diagnostics"}
    assert any(r["passes"] for t in data["official"]["tasks"] for r in t["rows"])
    assert data["projects"] == data["campaigns"] == []
    assert data["local_leaderboard"]["cohorts"] == []
    assert all(r["pack_version"] == data["version"] for r in data["grade_reports"])
    assert p["id"] not in response.text and "tenant data" not in response.text
    assert "private-model-key" not in response.text


def test_queue_cancellation_refunds_and_limits_are_separate(app):
    client = session(app)
    p = project(client)
    store = app.state.store
    for _ in range(6):
        j = client.post(
            "/api/workspace/message", json={"project": p["id"], "message": "Hello"}
        ).json()
        client.post("/api/jobs/" + j["id"] + "/cancel", json={})
    assert (
        client.get("/api/workspace/bootstrap").json()["hosting"]["quota"]["interactive"][
            "remaining"
        ]
        == 5
    )
    for _ in range(5):
        response = client.post(
            "/api/workspace/message", json={"project": p["id"], "message": "Hello"}
        )
        assert response.status_code == 200
        job = store.claim()
        store.update(job["id"], status="completed", finished=time.time())
    assert (
        client.post(
            "/api/workspace/message", json={"project": p["id"], "message": "Another"}
        ).status_code
        == 429
    )
    brief = client.post(
        "/api/workspace/brief",
        json={"project": p["id"], "question": "Equal moments imply equal growth rates at k=0.5."},
    )
    assert brief.status_code == 200
    launch = client.post("/api/workspace/launch", json={"project": p["id"]})
    assert launch.status_code == 200
    # Repeat launch returns the same campaign and consumes no second reservation.
    assert client.post("/api/workspace/launch", json={"project": p["id"]}).json() == launch.json()


def test_login_preserves_projects_across_devices_but_not_across_accounts(app):
    first = session(app)
    p = project(first)
    store = app.state.store
    guest = store.visitor(first.cookies.get(COOKIE))
    token, member = store.authorize_identity(guest["id"], 123, "scientist", "Scientist")
    assert store.visitor(first.cookies.get(COOKIE)) is None  # Session fixation is prevented.
    first.cookies.set(COOKIE, token)
    first.headers["X-CSRF-Token"] = member["csrf"]
    assert (
        first.get("/api/workspace/bootstrap").json()["hosting"]["quota"]["interactive"]["limit"]
        == 20
    )
    second = session(app)
    other = store.visitor(second.cookies.get(COOKIE))
    token, _ = store.authorize_identity(other["id"], 123, "scientist", "Scientist")
    second.cookies.set(COOKIE, token)
    assert second.get("/api/workspace/project?id=" + p["id"]).status_code == 200
    third = session(app)
    other = store.visitor(third.cookies.get(COOKIE))
    token, _ = store.authorize_identity(other["id"], 456, "another", "Another")
    third.cookies.set(COOKIE, token)
    assert third.get("/api/workspace/project?id=" + p["id"]).status_code == 404


def test_login_does_not_erase_guest_usage(app):
    client = session(app)
    p = project(client)
    s = app.state.store
    client.post("/api/workspace/message", json={"project": p["id"], "message": "Hi"})
    job = s.claim()
    s.update(job["id"], status="completed")
    visitor = s.visitor(client.cookies.get(COOKIE))
    s.authorize_identity(visitor["id"], 123, "scientist", "Scientist")
    _, fresh = s.create_visitor("testclient")
    assert s.quota(fresh["id"], {"interactive": 5, "research": 1})["interactive"]["used"] == 1


def test_github_flow_checks_state_pkce_verified_identity_and_never_saves_secret(app, monkeypatch):
    client = session(app)
    p = project(client)
    app.state.login.credentials = {
        "client_id": "public-client",
        "client_secret": "ephemeral-client-secret",
    }
    calls = []

    def provider(request):
        calls.append(request)
        if request.url.host == "github.com":
            form = parse_qs(request.content.decode())
            assert form["client_secret"] == ["ephemeral-client-secret"] and form["code_verifier"]
            return httpx.Response(
                200, json={"access_token": "ephemeral-access-token", "expires_in": 28800}
            )
        if request.url.path == "/user":
            return httpx.Response(200, json={"id": 123, "login": "scientist", "name": "Scientist"})
        return httpx.Response(200, json=[{"email": "scientist@example.org", "verified": True}])

    real = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: real(**kw, transport=httpx.MockTransport(provider))
    )
    response = client.get("/api/auth/github/start", follow_redirects=False)
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert client.get("/api/auth/github/callback?state=wrong&code=code").status_code == 400
    response = client.get(
        "/api/auth/github/callback",
        params={"state": query["state"][0], "code": "code"},
        follow_redirects=False,
    )
    assert response.status_code == 303 and response.headers["location"] == "/workspace"
    boot = client.get("/api/workspace/bootstrap").json()
    assert boot["hosting"]["account"]["login"] == "scientist"
    assert client.get("/api/workspace/project?id=" + p["id"]).status_code == 200
    assert len(calls) == 3
    database = app.state.store.path.read_bytes()
    assert b"ephemeral-client-secret" not in database and b"ephemeral-access-token" not in database
    assert (
        client.get(
            "/api/auth/github/callback", params={"state": query["state"][0], "code": "code"}
        ).status_code
        == 400
    )


def test_owner_requires_verified_github_id_and_has_unbounded_runtime(app, tmp_path):
    from conjecture_solver.public.worker import execute

    settings = {"public_origin": "http://testserver", "owner_github_ids": [75157161]}
    (tmp_path / "settings.json").write_text(json.dumps(settings))
    client = session(app)
    visitor = app.state.store.visitor(client.cookies.get(COOKIE))
    token, row = app.state.store.authorize_identity(visitor["id"], 75157161, "tomzhu0225", "Owner")
    client.cookies.set(COOKIE, token)
    client.headers["X-CSRF-Token"] = row["csrf"]
    boot = client.get("/api/workspace/bootstrap").json()["hosting"]
    assert boot["quota"]["tier"] == "owner"
    assert boot["quota"]["interactive"]["limit"] is None and boot["wall_seconds"] is None
    job = client.post("/api/jobs", json={"mode": "reproduce"}).json()
    admitted = app.state.store.claim()
    assert admitted["deadline"] is None and admitted["privileged"] == 1
    execute(tmp_path, job["id"])
    assert app.state.store.job(job["id"])["status"] == "completed"
    manifest = json.loads((tmp_path / "jobs" / job["id"] / "study/research.json").read_text())
    assert manifest["hosted_runtime_policy"]["unbounded"] is True
    other = session(app)
    v = app.state.store.visitor(other.cookies.get(COOKIE))
    token, _ = app.state.store.authorize_identity(v["id"], 456, "tomzhu0225", "Pretend owner")
    other.cookies.set(COOKIE, token)
    assert other.get("/api/workspace/bootstrap").json()["hosting"]["quota"]["tier"] == "member"


def test_ephemeral_oauth_inlet_does_not_write_credentials(app):
    import socket

    login = app.state.login
    login.start_inlet()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(3)
            client.connect(str(app.state.store.root / ".oauth-inlet.sock"))
            client.sendall(b'{"client_id":"client","client_secret":"never-on-disk"}\n')
            assert b"loaded in memory" in client.recv(200)
        assert login.ready()
        for path in app.state.store.root.iterdir():
            if path.is_file():
                assert b"never-on-disk" not in path.read_bytes()
    finally:
        login.close()
    assert not login.ready()


def test_interactive_worker_returns_chat_and_prepared_brief(app, monkeypatch):
    from smolagents.models import (
        ChatMessage,
        ChatMessageToolCall,
        ChatMessageToolCallFunction,
        Model,
    )

    from conjecture_solver.public.worker import execute

    class Scripted(Model):
        def __init__(self):
            super().__init__()
            self.calls = 0

        def generate(self, *args, **kwargs):
            self.calls += 1
            name = "prepare_study" if self.calls == 1 else "final_answer"
            arguments = (
                {
                    "question": "Equal moments imply equal growth at k=0.5.",
                    "success_criteria": "Match moments and compare refined growth rates.",
                }
                if self.calls == 1
                else {"answer": "The study brief is ready for your review."}
            )
            return ChatMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ChatMessageToolCall(
                        id=str(self.calls),
                        type="function",
                        function=ChatMessageToolCallFunction(name=name, arguments=arguments),
                    )
                ],
            )

    monkeypatch.setattr("conjecture_solver.public.worker.budget_model", lambda *args: Scripted())
    client = session(app)
    p = project(client)
    j = client.post("/api/workspace/prepare", json={"project": p["id"], "approach": "draft"}).json()
    app.state.store.claim()
    execute(app.state.store.root, j["id"])
    result = client.get("/api/workspace/project?id=" + p["id"]).json()
    assert result["brief"]["question"] == "Equal moments imply equal growth at k=0.5."
    assert result["messages"][-1]["content"] == "The study brief is ready for your review."
    assert result["running"] is False


def test_stopping_one_simulation_preserves_the_parent_agent_and_other_experiments(app):
    from conjecture_solver.research_service import ResearchService, put

    client = session(app)
    p = project(client)
    job = client.post(
        "/api/workspace/message", json={"project": p["id"], "message": "Run controls"}
    ).json()
    store = app.state.store
    store.claim()
    service = ResearchService.create(
        store.root / "jobs" / job["id"] / "study", "A numerical campaign", wall_seconds=120
    )
    for identifier in ("exp_one", "exp_two"):
        put(
            service.root / "experiments" / (identifier + ".json"),
            {"id": identifier, "status": "running", "worker_identity": None},
        )
    response = client.post(
        "/api/workspace/stop-simulation",
        json={
            "project": p["id"],
            "simulation": job["id"] + ".exp_one",
        },
    )
    assert response.status_code == 200
    assert service._read("experiments", "exp_one")["cancel_requested"] is True
    assert not service._read("experiments", "exp_two").get("cancel_requested")
    assert store.job(job["id"])["cancel_requested"] == 0
    other = project(client)
    assert (
        client.post(
            "/api/workspace/stop-simulation",
            json={
                "project": other["id"],
                "simulation": job["id"] + ".exp_two",
            },
        ).status_code
        == 404
    )


def test_low_disk_space_blocks_both_admission_routes_without_charging(app, monkeypatch):
    client = session(app)
    p = project(client)
    monkeypatch.setattr(app.state.store, "capacity_available", lambda: False)
    for path, data in (
        ("/api/workspace/message", {"project": p["id"], "message": "Run an experiment"}),
        ("/api/jobs", {"mode": "reproduce"}),
    ):
        assert client.post(path, json=data).status_code == 503
    assert not app.state.store.jobs(app.state.store.visitor(client.cookies.get(COOKIE))["id"])
