"""Receipt accounting and portable native-agent commands, without paid model calls."""

import json
from pathlib import Path

import pytest

from conjecture_solver.llm_bench.runner import (
    Campaign,
    availability_error,
    command,
    inference_observed,
    native_usage,
    public_feedback,
    run_campaign,
)


def turn(root, name, events):
    path = root / name
    path.mkdir()
    (path / "events.jsonl").write_text("\n".join(json.dumps(e) for e in events))
    return path


def test_agy_cumulative_totals_are_not_added(tmp_path):
    def event(output):
        return {
            "event": "result",
            "result": {
                "conversation_id": "sample-conversation",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": output,
                    "cache_read_tokens": 1000,
                    "thinking_tokens": 5,
                },
            },
        }

    first = turn(tmp_path, "first", [event(20)])
    second = turn(tmp_path, "second", [event(30)])
    usage, cursor = native_usage("agy", [first, second])
    assert usage["output_tokens"] == 30
    assert usage["cached_input_tokens"] == 1000
    assert usage["input_tokens"] is None  # Undocumented cache semantics.
    assert usage["requests_without_usage"] == 1
    assert cursor == "sample-conversation"


def test_agy_error_zero_does_not_erase_paid_work(tmp_path):
    first = turn(
        tmp_path,
        "paid",
        [
            {
                "event": "result",
                "result": {
                    "status": "ERROR",
                    "usage": {"input_tokens": 200, "output_tokens": 30, "cache_read_tokens": 1000},
                },
            }
        ],
    )
    last = turn(
        tmp_path,
        "quota",
        [
            {
                "event": "result",
                "result": {
                    "status": "ERROR",
                    "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0},
                },
            }
        ],
    )
    (last / "stderr.log").write_text(
        'AGY_ERROR: {"status":"RESOURCE_EXHAUSTED","error_code":429,'
        '"short_error":"Individual quota reached"}\n'
    )
    usage, _ = native_usage("agy", [first, last])
    assert usage["output_tokens"] == 30
    assert usage["cached_input_tokens"] == 1000
    assert availability_error(last) == "Provider quota exhausted"
    assert inference_observed([first, last], usage)
    zero_usage, _ = native_usage("agy", [last])
    assert not inference_observed([last], zero_usage)


def test_localized_expiry_is_detected_only_in_error_channels(tmp_path):
    directory = turn(
        tmp_path,
        "expired",
        [{"type": "error", "message": "您的GLM Coding Plan套餐已到期，暂无法使用"}],
    )
    assert availability_error(directory) == "Coding subscription expired"
    prose = turn(
        tmp_path,
        "prose",
        [
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "model not found; quota exhausted"},
            }
        ],
    )
    assert availability_error(prose) is None


def test_temporary_rate_limit_is_not_declared_unavailable(tmp_path):
    directory = turn(tmp_path, "busy", [])
    (directory / "stderr.log").write_text(
        'AGY_ERROR: {"status":"RESOURCE_EXHAUSTED","error_code":429,'
        '"short_error":"Rate limit; retry shortly"}\n'
    )
    assert availability_error(directory) is None


def test_grok_partial_receipts_and_stream_duplicates(tmp_path):
    receipt = {
        "type": "assistant",
        "session_id": "session",
        "message": {
            "id": "msg_0",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": 0,
            },
        },
    }
    directory = turn(tmp_path, "grok", [receipt, receipt])
    usage, cursor = native_usage("grok", [directory])
    assert usage["input_tokens"] == 110
    assert usage["output_tokens"] == 20
    assert usage["cached_input_tokens"] == 100
    assert usage["requests_without_usage"] == 1  # Process stopped without final receipt.
    assert cursor == "session"


def test_native_tools_oauth_and_custom_model_preserved(tmp_path):
    campaign = Campaign(tmp_path, tmp_path, Path("/usr/bin/python"), None, 1, "test")
    config = {"backend": "grok", "model": "my-custom-model", "effort": "high"}
    argv = command(campaign, config, "task", tmp_path / "prompt", None, 20)
    assert "--oauth" in argv and "--always-approve" in argv
    assert argv[argv.index("--model") + 1] == "my-custom-model"
    assert "--resume" not in argv


def test_feedback_does_not_reveal_hidden_labels_or_expected_values():
    feedback = public_feedback(
        {
            "checks": [
                {"metric": "plot:n64:tracer_r50_mm", "passed": False},
                {"metric": "holdout:secret-clock:E_rad_after_ref_J", "passed": False},
            ]
        }
    )
    assert "plot:n64:tracer_r50_mm" in feedback
    assert "secret-clock" not in feedback


def test_invalid_custom_configs_fail_before_spending(tmp_path):
    with pytest.raises(ValueError, match="safe id"):
        run_campaign([{"id": "../escape", "backend": "codex", "model": "custom"}], tmp_path)
    with pytest.raises(ValueError, match="provider config"):
        run_campaign([{"id": "api", "backend": "builtin", "model": "custom"}], tmp_path)
