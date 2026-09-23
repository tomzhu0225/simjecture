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
