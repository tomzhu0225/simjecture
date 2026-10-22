import argparse
import json
import time
from types import SimpleNamespace

import pytest

from conjecture_solver.provider_retry import (
    ProviderFailure,
    provider_failure,
    retry_delay,
    wait_for_provider,
)
from conjecture_solver.research_service import ResearchService
from conjecture_solver.research_supervisor import ResearchSupervisor


@pytest.mark.parametrize(
    "message,category",
    [
        ("stream disconnected before completion", "transient"),
        ("HTTP 503 overloaded", "transient"),
        ("HTTP 429 rate limit", "transient"),
        ("quota exhausted", "quota"),
        ("401 invalid API key", "authentication"),
        ("403 access denied", "permission"),
    ],
)
def test_provider_error_classification(tmp_path, message, category):
    (tmp_path / "stderr.log").write_text(message)
    error = provider_failure(tmp_path, 1)
    assert error.category == category
    assert error.retryable == (category == "transient")


def test_error_event_is_detected_even_with_zero_exit(tmp_path):
    (tmp_path / "response.json").write_text(
        json.dumps({"type": "turn.failed", "error": {"message": "stream disconnected"}})
    )
    assert provider_failure(tmp_path, 0).retryable
    (tmp_path / "response.json").write_text(
        json.dumps({"type": "item.completed", "item": {"text": "quota exhausted is an example"}})
    )
    assert provider_failure(tmp_path, 0) is None


def test_codex_completion_supersedes_recovered_reconnect_errors(tmp_path):
    events = [
        {"type": "turn.started"},
        {"type": "error", "message": "Reconnecting... 2/5 (tls handshake eof)"},
        {"type": "error", "message": "Reconnecting... 3/5 (tls handshake eof)"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Done"}},
        {"type": "turn.completed"},
    ]
    (tmp_path / "response.json").write_text("\n".join(json.dumps(e) for e in events))
    (tmp_path / "stderr.log").write_text("failed to connect to websocket: tls handshake eof")
    assert provider_failure(tmp_path, 0) is None


@pytest.mark.parametrize("returncode", [1, 124])
def test_codex_completion_does_not_hide_unsuccessful_exit(tmp_path, returncode):
    events = [
        {"type": "error", "message": "Reconnecting... (tls handshake eof)"},
        {"type": "turn.completed"},
    ]
    (tmp_path / "response.json").write_text("\n".join(json.dumps(e) for e in events))
    assert provider_failure(tmp_path, returncode).retryable


@pytest.mark.parametrize(
    "later_event,category",
    [
        ({"type": "error", "message": "connection lost"}, "transient"),
        ({"type": "turn.failed", "error": {"message": "connection lost"}}, "transient"),
        ({"type": "result", "is_error": True, "result": "402 Insufficient Balance"}, "quota"),
        ({"type": "turn.started"}, "transient"),
        ({"type": "turn.completed", "is_error": True}, "transient"),
    ],
)
def test_codex_completion_does_not_hide_later_failure(tmp_path, later_event, category):
    events = [
        {"type": "error", "message": "Reconnecting... (tls handshake eof)"},
        {"type": "turn.completed"},
        later_event,
    ]
    (tmp_path / "response.json").write_text("\n".join(json.dumps(e) for e in events))
    assert provider_failure(tmp_path, 0).category == category


@pytest.mark.parametrize("field", ["result", "message", "error"])
def test_actual_insufficient_balance_envelopes_pause_without_retry(tmp_path, field):
    (tmp_path / "response.json").write_text(
        json.dumps(
            {"type": "result", "is_error": True, field: "Error code: 402 - Insufficient Balance"}
        )
    )
    error = provider_failure(tmp_path, 0)
    state = {"deadline": time.time() + 600}
    original_deadline = state["deadline"]
    fake = SimpleNamespace(state=state, save=lambda: None, event=lambda *a, **kw: None)
    assert error.category == "quota" and not error.retryable
    assert not wait_for_provider(fake, error)
    assert state["status"] == "paused_external_error"
    assert "Restore credit" in state["provider_attention"]
    assert state["deadline"] == original_deadline
    assert not state.get("provider_retry_count")


def test_backoff_caps_and_obeys_deadline():
    assert retry_delay(100000) == 60
    state = {"deadline": time.time() + 0.05}
    fake = SimpleNamespace(
        state=state,
        save=lambda: None,
        event=lambda *a, **kw: None,
        boundary=lambda: time.time() >= state["deadline"],
    )
    before = time.monotonic()
    assert wait_for_provider(fake, ProviderFailure())
    assert time.monotonic() - before < 0.5
    assert state["provider_wait_seconds"] > 0
    assert "provider_next_retry_at" not in state


def test_reconnect_survives_more_than_three_failures_without_new_study(tmp_path, monkeypatch):
    service = ResearchService.create(
        tmp_path / "study", "An unresolved bounded claim", wall_seconds=60
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Continue from durable receipts.")
    args = argparse.Namespace(
        campaign=service.root,
        state_dir=service.root / "supervisor",
        wall_seconds=60,
        instructions_file=instructions,
        backend="codex",
        model="fixture",
        judge_model="fixture",
    )
    supervisor = ResearchSupervisor(args)
    deadline = service.manifest["deadline"]
    attempts = []
    monkeypatch.setattr("conjecture_solver.provider_retry.retry_delay", lambda attempt: 0)

    def launch(directory, prompt, judge=False):
        attempts.append(directory)
        if len(attempts) <= 5:
            raise ProviderFailure()
        supervisor.cancelled = True
        return 0

    monkeypatch.setattr(supervisor, "launch", launch)
    assert supervisor.run() == 0
    assert len(attempts) == 6
    assert supervisor.state["provider_retry_count"] == 5
    assert supervisor.state["status"] == "cancelled"
    assert ResearchService(service.root).manifest["deadline"] == deadline
    assert not service.status()["completed"]
