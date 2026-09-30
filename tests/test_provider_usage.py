import json
from types import SimpleNamespace

from conjecture_solver.provider_usage import context_metadata, reported_usage, request_accounting


def stream(tmp_path, events):
    path = tmp_path / "response.json"
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


def test_request_receipts_deduplicate_without_adding_step_totals(tmp_path):
    receipt = dict(
        type="provider_request",
        request_id="one",
        status="succeeded",
        usage=dict(
            input_tokens=100, output_tokens=20, cached_input_tokens=60, reasoning_output_tokens=12
        ),
    )
    result = request_accounting(
        stream(
            tmp_path,
            [
                dict(type="provider_request", request_id="one", status="started"),
                receipt,
                receipt,
                dict(type="usage", input_tokens=100, output_tokens=20),
                dict(type="provider_request", request_id="two", status="started"),
            ],
        )
    )
    assert result["input_tokens"] == 100 and result["output_tokens"] == 20
    assert result["cached_input_tokens"] == 60 and result["reasoning_output_tokens"] == 12
    assert result["requests"] == 2 and result["requests_without_usage"] == 1
    assert not result["cache_usage_complete"]


def test_missing_details_remain_unknown_and_legacy_studies_work(tmp_path):
    response = SimpleNamespace(raw={"usage": {"prompt_tokens": 20, "completion_tokens": 5}})
    usage = reported_usage(response)
    assert usage["cached_input_tokens"] is None
    assert usage["reasoning_output_tokens"] is None
    legacy = request_accounting(
        stream(tmp_path, [dict(type="usage", input_tokens=20, output_tokens=5)])
    )
    assert legacy["input_tokens"] == 20
    assert legacy["accounting"] == "legacy_steps" and not legacy["cache_usage_complete"]


def test_deepseek_native_cache_and_reasoning_are_preserved():
    response = SimpleNamespace(
        raw={
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "prompt_cache_hit_tokens": 80,
                "prompt_cache_miss_tokens": 20,
                "completion_tokens_details": {"reasoning_tokens": 15},
            }
        }
    )
    usage = reported_usage(response)
    assert usage["cached_input_tokens"] == 80
    assert usage["uncached_input_tokens"] == 20
    assert usage["reasoning_output_tokens"] == 15


def test_context_metadata_never_contains_message_or_reasoning_text():
    request = {
        "messages": [
            {
                "role": "assistant",
                "content": "secret-content",
                "reasoning_content": "private-reasoning",
            }
        ],
        "tools": [{"description": "private-tool-description"}],
    }
    metadata = context_metadata(request)
    encoded = json.dumps(metadata)
    assert all(
        s not in encoded
        for s in ["secret-content", "private-reasoning", "private-tool-description"]
    )
    assert metadata["messages"][0]["reasoning_bytes"] == len("private-reasoning")
    assert metadata["messages"][0]["sha256"]


def test_each_completion_retry_is_recorded_before_step_aggregation(monkeypatch):
    from smolagents import OpenAIServerModel
    from smolagents.models import ChatMessage, TokenUsage

    from conjecture_solver import workspace_agent

    events = []
    monkeypatch.setattr(
        workspace_agent, "emit", lambda kind, **kw: events.append({"type": kind, **kw})
    )

    def generate(self, messages, *args, **kwargs):
        return ChatMessage(
            role="assistant",
            content="Let me inspect that.",
            raw=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(reasoning_content="private"))]
            ),
            token_usage=TokenUsage(input_tokens=100, output_tokens=10),
        )

    monkeypatch.setattr(OpenAIServerModel, "generate", generate)
    model = workspace_agent.model_for({"model": "deepseek-flash", "base_url": "http://127.0.0.1:1"})
    import pytest

    with pytest.raises(RuntimeError, match="did not complete"):
        model.generate(
            [{"role": "user", "content": "Do work"}],
            tools_to_call_from=[SimpleNamespace(name="final_answer")],
        )
    receipts = [e for e in events if e["type"] == "provider_request" and e["status"] == "succeeded"]
    assert len(receipts) == 4
    assert sum(e["usage"]["input_tokens"] for e in receipts) == 400
    assert len({e["request_id"] for e in receipts}) == 4
    assert len({e["generation_id"] for e in receipts}) == 1
    assert [e["reason"] for e in receipts] == ["generation"] + ["completion_check"] * 3


def test_live_usage_replaces_same_turn_and_keeps_nested_review_identity(tmp_path):
    import time

    from conjecture_solver.research_service import put
    from conjecture_solver.study_status import study_status

    root = tmp_path / "study"
    turn = root / "supervisor/oversight-00001/evidence-1"
    turn.mkdir(parents=True)
    put(root / "research.json", dict(created_at=time.time(), deadline=time.time() + 60))
    usage = dict(
        input_tokens=100, output_tokens=20, cached_input_tokens=80, reasoning_output_tokens=10
    )
    stream(turn, [dict(type="provider_request", request_id="one", status="succeeded", usage=usage)])
    put(
        root / "supervisor/state.json",
        dict(
            status="running",
            active_usage_directory=str(turn),
            usage_by_thread={"oversight-00001/evidence-1": usage},
        ),
    )
    status = study_status(root)
    assert status["usage"]["input_tokens"] == 100
    assert status["usage_details"]["requests"] == 1
    assert status["usage_details"]["by_role"]["reviewer"]["input_tokens"] == 100
