"""Public admission and ownership boundaries, including a real PIC execution."""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from conjecture_solver.public.server import create_app
from conjecture_solver.public.store import LimitReached, Store
from conjecture_solver.public.worker import PICCase, execute


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, dispatch=False, secure_cookies=False)


def session(app):
    client = TestClient(app)
    response = client.post("/api/session", json={}, headers={"Origin": "http://testserver"})
    assert response.status_code == 200
    client.headers.update(
        {"Origin": "http://testserver", "X-CSRF-Token": response.json()["csrf_token"]}
    )
    return client


def test_visitors_cannot_read_or_cancel_other_jobs(app):
    first, second = session(app), session(app)
    job = first.post("/api/jobs", json={"mode": "reproduce"}).json()
    path = "/api/jobs/" + job["id"]
    assert first.get(path).status_code == 200
    for suffix in ("", "/events", "/artifacts"):
        assert second.get(path + suffix).status_code == 404
    assert second.post(path + "/cancel", json={}).status_code == 404
    assert second.get("/api/me").json()["jobs"] == []
    assert first.post(path + "/cancel", json={}).json()["status"] == "cancelled"


def test_csrf_origin_and_private_operator_endpoints(app):
    client = session(app)
    assert (
        client.post(
            "/api/jobs", json={"mode": "reproduce"}, headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/jobs", json={"mode": "reproduce"}, headers={"X-CSRF-Token": "wrong"}
        ).status_code
        == 403
    )
    for path in (
        "/api/workspace/settings",
        "/api/bootstrap/../provider.json",
    ):
        assert client.get(path).status_code in {403, 404}
    assert client.get("/api/workspace/machines").json()["machines"] == []
    assert "control_token" not in client.get("/api/bootstrap").json()
    assert client.get("/").headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in client.get("/").headers["content-security-policy"]


def test_input_and_body_limits(app):
    client = session(app)
    for payload in (
        {"mode": "shell"},
        {"mode": "reproduce", "command": "id"},
        {"mode": "research", "hypothesis": "x" * 4001},
    ):
        assert client.post("/api/jobs", json=payload).status_code == 422
    assert (
        client.post(
            "/api/jobs", content=b"x" * 16385, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )
    assert (
        client.post("/api/jobs", content=b"{}", headers={"Content-Type": "text/plain"}).status_code
        == 415
    )


def test_www_uses_canonical_origin_and_preserves_path_and_query(app, tmp_path):
    (tmp_path / "settings.json").write_text(
        json.dumps({"public_origin": "https://simjecture.example"})
    )
    client = TestClient(app, base_url="https://www.simjecture.example", follow_redirects=False)
    response = client.get("/healthz?check=1")
    assert response.status_code == 308
    assert response.headers["location"] == "https://simjecture.example/healthz?check=1"
    assert client.get("https://other.example/healthz").status_code == 200


def test_provider_connection_requires_explicit_public_enablement(app, tmp_path):
    (tmp_path / "provider.json").write_text(
        json.dumps(
            {
                "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
                "api_key": "private-key",
                "model": "mimo-v2.6-pro",
            }
        )
    )
    client = session(app)
    assert client.get("/api/bootstrap").json()["research_ready"] is False
    assert client.post("/api/jobs", json={"mode": "research"}).status_code == 503
    assert "private-key" not in client.get("/api/bootstrap").text


def test_duplicate_and_daily_admission(app):
    client = session(app)
    first = client.post("/api/jobs", json={"mode": "reproduce"})
    assert first.status_code == 202
    assert client.post("/api/jobs", json={"mode": "reproduce"}).status_code == 429
    client.post("/api/jobs/" + first.json()["id"] + "/cancel", json={})
    # A queued cancellation is refunded; five admitted interactive tasks consume the allowance.
    for _ in range(5):
        second = client.post("/api/jobs", json={"mode": "reproduce"})
        assert second.status_code == 202
        app.state.store.claim()
        app.state.store.update(second.json()["id"], status="completed", finished=time.time())
    assert client.post("/api/jobs", json={"mode": "reproduce"}).status_code == 429
    other = session(app)
    assert other.post("/api/jobs", json={"mode": "reproduce"}).status_code == 429


def test_atomic_cross_coordinator_admission_and_waiting_time(tmp_path):
    store = Store(tmp_path)
    for i in range(5):
        _, visitor = store.create_visitor(str(i))
        store.enqueue(visitor["id"], "reproduce", "Test matched distributions", wall_seconds=60)
    with store.connect(write=True) as db:
        db.execute("UPDATE jobs SET created=?", (time.time() - 7200,))

    def claim(_):
        return Store(tmp_path).claim(max_active=2)

    with ThreadPoolExecutor(max_workers=5) as pool:
        admitted = [j for j in pool.map(claim, range(5)) if j]
    assert len(admitted) == 2
    assert len({j["id"] for j in admitted}) == 2
    assert all(j["deadline"] - time.time() > 55 for j in admitted)
    with store.connect() as db:
        queued = [r[0] for r in db.execute("SELECT id FROM jobs WHERE status='queued'")]
    assert all(store.job(identifier)["queue_position"] > 0 for identifier in queued)


def test_provider_failures_count_and_request_budget_is_global(tmp_path):
    store = Store(tmp_path)
    _, a = store.create_visitor("a")
    _, b = store.create_visitor("b")
    for owner in (a, b):
        store.enqueue(owner["id"], "research", "Plasma hypothesis")
    one, two = store.claim(), store.claim()
    request = store.reserve_request(one["id"], "worker", daily=1)
    store.finish_request(request, status="failed", http_status=429)
    with pytest.raises(LimitReached, match="daily"):
        store.reserve_request(two["id"], "reviewer", daily=1)
    assert store.job(one["id"])["usage"]["requests"] == 1


def test_recovery_cannot_overwrite_a_completed_worker(tmp_path):
    store = Store(tmp_path)
    _, owner = store.create_visitor("owner")
    queued = store.enqueue(owner["id"], "reproduce", "A plasma hypothesis")
    store.claim()
    store.update(queued["id"], status="completed", summary="Retained numerical result")
    store.update(queued["id"], expected_status="running", status="interrupted")
    assert store.job(queued["id"])["status"] == "completed"


@pytest.mark.parametrize(
    "mode,finish,terminal",
    [
        ("interactive", "stop", True),
        ("research", "stop", False),
        ("interactive", "length", False),
    ],
)
def test_interactive_terminal_text_does_not_require_a_second_model_request(
    tmp_path, monkeypatch, mode, finish, terminal
):
    import httpx
    from openai import OpenAI
    from smolagents import OpenAIServerModel

    from conjecture_solver.public.worker import budget_model

    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "id": "response",
                "object": "chat.completion",
                "created": 1,
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": finish,
                        "message": {
                            "role": "assistant",
                            "content": "Here are the actual findings.",
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 6, "total_tokens": 16},
            },
        )

    monkeypatch.setattr(
        OpenAIServerModel,
        "create_client",
        lambda self: OpenAI(
            **self.client_kwargs,
            http_client=httpx.Client(transport=httpx.MockTransport(provider)),
        ),
    )
    store = Store(tmp_path)
    _, visitor = store.create_visitor("testing")
    job = store.enqueue(visitor["id"], mode, "An interactive question")
    store.claim()
    model = budget_model(
        store,
        job["id"],
        {
            "api_key": "private",
            "model": "test",
            "base_url": "https://provider.example/v1",
        },
        "researcher",
    )
    response = model.generate([{"role": "user", "content": "Explain the recorded evidence"}])
    assert len(calls) == 1 and store.job(job["id"])["usage"]["requests"] == 1
    if terminal:
        call = response.tool_calls[0].function
        assert (
            call.name == "final_answer"
            and call.arguments["answer"] == "Here are the actual findings."
        )
    else:
        assert not response.tool_calls
    assert response.raw.choices[0].message.content == "Here are the actual findings."


def test_public_model_uses_native_calls_and_no_hidden_sdk_retries(tmp_path, monkeypatch):
    import httpx
    from openai import OpenAI, RateLimitError
    from smolagents import OpenAIServerModel

    from conjecture_solver.public.worker import budget_model

    calls = []

    def provider(request):
        calls.append(json.loads(request.content))
        return httpx.Response(429, json={"error": {"message": "private-key", "type": "rate_limit"}})

    monkeypatch.setattr(
        OpenAIServerModel,
        "create_client",
        lambda self: OpenAI(
            **self.client_kwargs, http_client=httpx.Client(transport=httpx.MockTransport(provider))
        ),
    )
    store = Store(tmp_path)
    _, owner = store.create_visitor("owner")
    job = store.enqueue(owner["id"], "research", "A plasma hypothesis")
    store.claim()
    model = budget_model(
        store,
        job["id"],
        {
            "base_url": "https://provider.example/v1",
            "api_key": "private-key",
            "model": "test-model",
            "retry_transient": False,
        },
        "researcher",
    )
    with pytest.raises(RateLimitError):
        model.generate([{"role": "user", "content": "Run the next experiment"}])
    assert len(calls) == 1
    assert calls[0]["messages"][-1]["content"] == "Run the next experiment"
    assert store.job(job["id"])["usage"]["requests"] == 1
    assert "private-key" not in json.dumps(store.events(job["id"]))


def test_local_context_rejection_does_not_spend_provider_allowance(tmp_path):
    from conjecture_solver.public.worker import budget_model

    store = Store(tmp_path)
    _, owner = store.create_visitor("owner")
    job = store.enqueue(owner["id"], "research", "Plasma hypothesis")
    store.claim()
    model = budget_model(
        store,
        job["id"],
        {
            "base_url": "https://provider.example/v1",
            "api_key": "private-key",
            "model": "test-model",
        },
        "reviewer",
    )
    with pytest.raises(LimitReached, match="context"):
        model.generate([{"role": "user", "content": "x" * 240001}])
    assert store.job(job["id"])["usage"]["requests"] == 0


def test_transient_retry_is_visible_and_preserves_native_request(tmp_path, monkeypatch):
    import httpx
    from openai import OpenAI
    from smolagents import OpenAIServerModel

    from conjecture_solver.public.worker import budget_model

    calls = []

    def provider(request):
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(503, json={"error": {"message": "private-key"}})
        return httpx.Response(
            200,
            json={
                "id": "recorded-response",
                "object": "chat.completion",
                "created": 1,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "Recovered"},
                    }
                ],
                "usage": {
                    "prompt_tokens": 17,
                    "completion_tokens": 9,
                    "total_tokens": 26,
                    "prompt_tokens_details": {"cached_tokens": 12},
                    "completion_tokens_details": {"reasoning_tokens": 4},
                },
            },
        )

    monkeypatch.setattr(
        OpenAIServerModel,
        "create_client",
        lambda self: OpenAI(
            **self.client_kwargs, http_client=httpx.Client(transport=httpx.MockTransport(provider))
        ),
    )
    monkeypatch.setattr("conjecture_solver.provider_retry.retry_delay", lambda _: 0)
    store = Store(tmp_path)
    _, owner = store.create_visitor("owner")
    job = store.enqueue(owner["id"], "research", "Plasma hypothesis")
    store.claim()
    model = budget_model(
        store,
        job["id"],
        {
            "base_url": "https://provider.example/v1",
            "api_key": "private-key",
            "model": "test-model",
            "reviewer_request_parameters": {"thinking": {"type": "disabled"}},
        },
        "reviewer",
    )
    assert (
        model.generate([{"role": "user", "content": "Read recorded data"}]).content == "Recovered"
    )
    assert len(calls) == 2 and calls[0] == calls[1]
    assert calls[0]["thinking"] == {"type": "disabled"}
    with store.connect() as db:
        rows = [dict(row) for row in db.execute("SELECT * FROM requests ORDER BY created")]
    assert [row["status"] for row in rows] == ["failed", "succeeded"]
    assert rows[0]["http_status"] == 503
    assert rows[1]["cached_input_tokens"] == 12 and rows[1]["reasoning_tokens"] == 4
    assert rows[1]["finish_reason"] == "stop" and rows[1]["context_bytes"] > 0
    assert "private-key" not in json.dumps(store.events(job["id"]))


def test_compact_review_preserves_all_sources_and_original_packet():
    import copy

    from conjecture_solver.public.worker import compact_review_packet
    from conjecture_solver.research_service import fingerprint

    packet = {
        "experiments": [
            {
                "sources": {"solver.py": "actual source\n" * 50, "case.json": '{"grid":32}'},
                "documents": {"metric": 2.3},
            },
            {
                "sources": {"solver.py": "actual source\n" * 50, "case.json": '{"grid":64}'},
                "documents": {"metric": 2.4},
            },
        ]
    }
    before = fingerprint(packet)
    compact = compact_review_packet(packet)
    restored = copy.deepcopy(compact)
    sources = restored.pop("shared_sources")
    restored.pop("source_reference_instructions")
    for e in restored["experiments"]:
        e["sources"] = {
            name: sources[digest] for name, digest in e.pop("source_references").items()
        }
    assert fingerprint(restored) == before == fingerprint(packet)
    assert len(json.dumps(compact)) < len(json.dumps(packet))


def test_simulation_allowance_keeps_existing_evidence_available(tmp_path):
    from conjecture_solver.public.worker import run_case
    from conjecture_solver.research_service import ResearchService, put

    store = Store(tmp_path)
    _, owner = store.create_visitor("owner")
    job = store.enqueue(owner["id"], "research", "A plasma hypothesis")
    store.claim()
    (tmp_path / "settings.json").write_text(json.dumps({"experiments_per_job": 1}))
    service = ResearchService.create(
        tmp_path / "study",
        "A plasma hypothesis",
        wall_seconds=60,
        execution_backend="process-cooperative",
        completion_policy="answer",
    )
    put(service.root / "experiments/exp_prior.json", {"id": "exp_prior", "status": "succeeded"})
    result = run_case(store, job["id"], service, {})
    assert result["status"] == "simulation_allowance_reached"
    assert service._read("experiments", "exp_prior")["status"] == "succeeded"
    assert store.job(job["id"])["status"] == "running"
    assert store.reserve_request(job["id"], "reviewer")


@pytest.mark.parametrize(
    "config",
    [
        {"grid_cells": 1024},
        {"velocity_beams": 1000000},
        {"time_step": 1e-12},
        {"stream_drift": float("nan")},
        {"source": "/etc/passwd"},
        {"seed": -1},
    ],
)
def test_public_tool_rejects_unbounded_or_executable_parameters(config):
    with pytest.raises(ValueError):
        PICCase.model_validate(config).validated()


def test_real_recorded_numerical_job_and_verified_artifacts(app, tmp_path):
    client = session(app)
    job = client.post("/api/jobs", json={"mode": "reproduce"}).json()
    admitted = app.state.store.claim()
    execute(tmp_path, admitted["id"])
    result = client.get("/api/jobs/" + job["id"]).json()
    assert result["status"] == "completed", result["summary"]
    assert result["usage"]["requests"] == 0
    files = client.get("/api/jobs/" + job["id"] + "/artifacts").json()["artifacts"]
    assert {f["name"] for f in files} == {"result.json", "evolution.png"}
    for f in files:
        path = "/api/jobs/" + job["id"] + "/artifacts/" + f["experiment"] + "/" + f["name"]
        response = client.get(path)
        assert response.status_code == 200
        if f["name"] == "result.json":
            scientific = response.json()
            assert scientific["moments_match"] is True
            assert scientific["maxwellian"]["validity_passed"] is True
            assert scientific["two_stream"]["validity_passed"] is True
            assert scientific["hypothesis_falsified"] is True
            original = (
                tmp_path
                / "jobs"
                / job["id"]
                / "study/experiments"
                / f["experiment"]
                / "workspace/result.json"
            )
            original.write_text("{}")
            assert client.get(path).status_code == 404
