from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from conjecture_solver.mvp_control import (
    ControlCommand,
    begin_or_resume_clock,
    elapsed_from_clock,
    format_token_counts,
    parse_usage_payload,
    pause_at_boundary,
    poll_control,
    read_clock,
    read_pause_state,
    write_control,
)


def test_parse_usage_payload_accepts_openai_and_deepseek_shapes() -> None:
    openai = parse_usage_payload(
        {
            "prompt_tokens": 100,
            "completion_tokens": 20,
            "total_tokens": 120,
            "prompt_tokens_details": {"cached_tokens": 12},
            "completion_tokens_details": {"reasoning_tokens": 4},
        }
    )
    assert openai["prompt_tokens"] == 100
    assert openai["completion_tokens"] == 20
    assert openai["total_tokens"] == 120
    assert openai["cached_tokens"] == 12
    assert openai["reasoning_tokens"] == 4
    alt = parse_usage_payload({"input_tokens": 10, "output_tokens": 5})
    assert alt["prompt_tokens"] == 10
    assert alt["completion_tokens"] == 5
    assert alt["total_tokens"] == 15
    dsh = parse_usage_payload(
        {
            "inputTokens": 12,
            "outputTokens": 7,
            "cacheReadTokens": 80,
            "cacheWriteTokens": 3,
            "reasoningTokens": 5,
        }
    )
    assert dsh == {
        "prompt_tokens": 12,
        "completion_tokens": 7,
        "total_tokens": 102,
        "cached_tokens": 83,
        "reasoning_tokens": 5,
    }
    assert parse_usage_payload(None)["total_tokens"] == 0


def test_format_token_counts_is_human_readable() -> None:
    label = format_token_counts(
        prompt_tokens=12480,
        completion_tokens=3102,
        total_tokens=15582,
        turns=4,
        missing_turns=1,
        cached_tokens=200,
    )
    assert "12,480 in" in label
    assert "3,102 out" in label
    assert "15,582 total" in label
    assert "4 turns" in label
    assert "1 without usage" in label
    assert "200 cached" in label


def test_control_file_round_trip(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    assert poll_control(root) is ControlCommand.NONE
    write_control(root, ControlCommand.PAUSE, source="test")
    assert poll_control(root) is ControlCommand.PAUSE
    assert (root / "operator_input" / "control.json").is_file()


def test_clock_accumulates_across_pause_and_resume(tmp_path: Path) -> None:
    root = tmp_path / "clock"
    root.mkdir()
    t0 = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)
    begin_or_resume_clock(root, now=t0)
    pause_at_boundary(root, iterations=3, now=t0 + timedelta(seconds=90))
    paused = read_clock(root)
    assert paused is not None
    assert paused.state == "paused"
    assert paused.accumulated_active_seconds == 90
    assert read_pause_state(root) is not None
    assert poll_control(root) is ControlCommand.NONE
    t1 = t0 + timedelta(seconds=200)
    begin_or_resume_clock(root, now=t1)
    clock = read_clock(root)
    assert clock is not None
    assert clock.state == "running"
    assert clock.accumulated_active_seconds == 90
    assert read_pause_state(root) is None
    elapsed = elapsed_from_clock(clock, now=t1 + timedelta(seconds=10))
    assert elapsed == 100
