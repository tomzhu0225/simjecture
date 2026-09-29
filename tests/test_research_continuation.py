"""Continuation provenance, durable steering and reviewer-output failure regression."""

import json
import time
from types import SimpleNamespace

import pytest

from conjecture_solver.research_continuation import attach, deliver, preview, steering, submit
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.study_status import study_status


def test_expired_parent_continues_without_changing_history(tmp_path):
    parent = ResearchService.create(tmp_path / "parent", "Original physical question")
    parent.freeze_protocol("Keep an independent energy balance")
    parent.freeze_requirements({"require_method_review": True})
    (parent.work / "calculate.py").write_text("print(3)\n")
    put(
        parent.root / "experiments/old.json",
        {"id": "old", "status": "succeeded", "stage": "exploration"},
    )
    manifest = parent.manifest | {"deadline": time.time() - 1}
    put(parent.root / "research.json", manifest)
    before = (parent.root / "research.json").read_bytes()
    child = ResearchService.create(tmp_path / "child", manifest["hypothesis"], wall_seconds=7200)
    child.freeze_protocol("Investigate resolved axial modes")
    attach(child, parent.root, ["calculate.py"])
    assert (parent.root / "research.json").read_bytes() == before
    assert child.manifest["deadline"] > time.time() + 7100
    assert not child._all("experiments")
    assert not child._all("reviews")
    assert child.manifest["requirements"]["require_method_review"]
    summary = json.loads((child.root / "continuation_input/summary.json").read_text())
    assert summary["experiments"][0]["stage"] == "exploration"
    (child.work / "inherited/calculate.py").write_text("print(4)\n")
    assert ResearchService(child.root).manifest["continuation"]
    (child.root / "continuation_input/files/calculate.py").write_text("forged")
    with pytest.raises(ValueError, match="identity changed"):
        ResearchService(child.root)


def test_continuation_rejects_escape_and_no_implicit_secrets(tmp_path):
    parent = ResearchService.create(tmp_path / "parent", "Q")
    secret = tmp_path / "secret"
    secret.write_text("private")
    (parent.work / "escape.py").symlink_to(secret)
    (parent.work / ".credentials.json").write_text("private")
    (parent.work / "lab.py").write_text("client")
    assert not preview(parent.root)["files"]
    for name in ["../secret", "escape.py", ".credentials.json", "lab.py"]:
        child = ResearchService.create(
            tmp_path / ("child" + str(len(list(tmp_path.iterdir())))), "Q"
        )
        with pytest.raises(ValueError):
            attach(child, parent.root, [name])
        assert not (child.root / "continuation_input").exists()


def test_steering_survives_restart_without_changing_contract(tmp_path):
    s = ResearchService.create(tmp_path / "study", "Q")
    s.freeze_protocol("Original protocol")
    before = (s.root / "research.json").read_bytes()
    first = submit(s.root, "Check boundary work independently", key="request-1")
    assert submit(s.root, first["message"], key="request-1")["id"] == first["id"]
    with pytest.raises(ValueError, match="different guidance"):
        submit(s.root, "Different text", key="request-1")
    assert steering(s.root)[0]["delivered_at"] is None
    assert deliver(ResearchService(s.root))[0]["message"] == first["message"]
    assert steering(s.root)[0]["delivered_at"]
    assert deliver(ResearchService(s.root))[0]["message"] == first["message"]
    assert (s.root / "research.json").read_bytes() == before
    put(s.root / "research.json", s.manifest | {"deadline": time.time() - 1})
    with pytest.raises(ValueError, match="Continue investigation"):
        submit(s.root, "More work")


def test_steering_reaches_worker_and_reviewers(tmp_path):
    from tests.test_research_oversight import make

    s, supervisor = make(tmp_path)
    submit(s.root, "Distinguish numerical viscosity from physical heating")
    prompt = supervisor.prompt()
    assert "Distinguish numerical viscosity" in prompt
    assert steering(s.root)[0]["delivered_at"]
    # Scientific reviewer packets include applicable guidance, not just the worker.
    packet = s.packet(
        {"claim": "root", "disposition": "falsified", "experiments": [], "conclusion": "Unresolved"}
    )
    assert packet["operator_steering"][0]["message"].startswith("Distinguish numerical")


def test_expired_status_does_not_claim_running(tmp_path):
    s = ResearchService.create(tmp_path / "study", "Q")
    (s.root / "supervisor").mkdir()
    put(
        s.root / "supervisor/state.json",
        dict(status="paused_external_error", deadline=time.time() - 1, last_error="Empty verdict"),
    )
    status = study_status(s.root)
    assert status["status"] == "budget_exhausted"
    assert status["recorded_status"] == "paused_external_error"
    assert status["remaining"] == 0


def test_empty_judge_output_retries_once_and_counts_both_attempts(tmp_path, monkeypatch):
    from conjecture_solver import workspace_agent as agent

    events, calls = [], []
    responses = [("", "length", 32768), ('{"decision":"revise"}', "stop", 20)]

    class Model:
        def generate(self, messages, **kwargs):
            calls.append(kwargs)
            content, reason, tokens = responses.pop(0)
            return SimpleNamespace(
                content=content,
                tool_calls=None,
                token_usage=SimpleNamespace(input_tokens=10, output_tokens=tokens),
                raw={"choices": [{"finish_reason": reason}]},
            )

    monkeypatch.setattr(agent, "model_for", lambda *a, **k: Model())
    monkeypatch.setattr(agent, "emit", lambda kind, **kw: events.append((kind, kw)))
    result = agent.run_agent(
        "Review evidence",
        tmp_path,
        {"model": "deepseek-flash", "base_url": "https://api.deepseek.com"},
        judge=True,
        wall_seconds=10,
    )
    assert json.loads(result)["decision"] == "revise"
    assert len(calls) == 2
    assert calls[1]["extra_body"]["thinking"]["type"] == "disabled"
    assert sum(v["output_tokens"] for k, v in events if k == "usage") == 32788
    assert [v["finish_reason"] for k, v in events if k == "review_response"] == ["length", "stop"]


def test_repeated_empty_judge_is_an_error_not_approval(tmp_path, monkeypatch):
    from conjecture_solver import workspace_agent as agent

    response = SimpleNamespace(content="", tool_calls=None, token_usage=None, raw=None)
    monkeypatch.setattr(
        agent, "model_for", lambda *a, **k: SimpleNamespace(generate=lambda *a, **k: response)
    )
    monkeypatch.setattr(agent, "emit", lambda *a, **k: None)
    with pytest.raises(ValueError, match="empty or truncated"):
        agent.run_agent(
            "Review",
            tmp_path,
            {"model": "fixture", "base_url": "http://localhost"},
            judge=True,
            wall_seconds=10,
        )


def test_failed_oversight_backs_off_but_never_approves(tmp_path, monkeypatch):
    from tests.test_research_oversight import make, proposal

    s, supervisor = make(tmp_path)
    method = proposal(s)
    monkeypatch.setattr(supervisor, "launch", lambda *a, **k: 0)
    monkeypatch.setattr(
        "conjecture_solver.research_oversight.parse_judge_stream",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("empty")),
    )
    for count in range(1, 4):
        supervisor.run_oversight(s._read("methods", method["id"]))
        record = s._read("methods", method["id"])
        assert record["status"] == "queued"
        assert record["review_failures"] == count
        assert record["retry_after"] > time.time() + 120 * 2 ** (count - 1) - 3


def test_reviewer_output_budget_survives_smolagents_default_precedence():
    pytest.importorskip("smolagents")
    from conjecture_solver.workspace_agent import model_for

    model = model_for(
        {"model": "deepseek-flash", "base_url": "http://localhost:1"}, max_tokens=32768
    )
    request = model._prepare_completion_kwargs(messages=[{"role": "user", "content": "Review"}])
    assert request["max_tokens"] == 32768


def test_read_only_web_blocks_steering_and_continuation(tmp_path):
    import threading

    import httpx

    from conjecture_solver.web.application import SimjectureWebApplication
    from conjecture_solver.web.server import create_server

    parent = ResearchService.create(tmp_path / "parent", "Q")
    app = SimjectureWebApplication(
        initial_run=parent.root, runs_root=tmp_path / "runs", allow_mutations=False
    )
    token = app.registry.register(parent.root)
    server = create_server(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
            boot = client.get("/api/workspace/bootstrap").json()
            for endpoint in ["steer-study", "prepare-continuation"]:
                response = client.post(
                    "/api/workspace/" + endpoint,
                    headers={"X-Simjecture-Token": boot["control_token"]},
                    json={"campaign": token, "message": "Advice", "guidance": "Next phase"},
                )
                assert response.status_code == 403
        assert not steering(parent.root)
        assert not app.workspace.projects()
    finally:
        server.shutdown()
        server.server_close()
