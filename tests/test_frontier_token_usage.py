"""Accounting regressions: resumed threads, interrupted turns and fresh reviewers."""

import importlib.util
import json
from pathlib import Path

MODULE = Path(__file__).parents[1] / "research/evaluations/frontier-workflow/token_usage.py"
spec = importlib.util.spec_from_file_location("frontier_token_usage", MODULE)
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


def write(path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


def count(n):
    return {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": n,
                    "cached_input_tokens": n // 2,
                    "output_tokens": 10,
                    "reasoning_output_tokens": 3,
                    "total_tokens": n + 10,
                }
            },
        },
    }


def test_resume_interrupted_and_reviewer_counted_once(tmp_path):
    root = tmp_path / "euler-frontier"
    for turn in (1, 2):
        write(
            root / f"supervisor/turn-{turn:05d}/response.json",
            [
                {"type": "thread.started", "thread_id": "worker"},
                *(
                    [
                        {
                            "type": "turn.completed",
                            "usage": {"input_tokens": 100, "output_tokens": 10},
                        }
                    ]
                    if turn == 1
                    else []
                ),
            ],
        )
    write(
        root / "supervisor/review-1/response.json",
        [{"type": "thread.started", "thread_id": "reviewer"}],
    )
    w = write(tmp_path / "worker.jsonl", [count(100), count(100), count(250)])
    r = write(tmp_path / "reviewer.jsonl", [count(30)])
    # A partially written trailing event must not discard prior usage.
    with w.open("a") as stream:
        stream.write('{"type":')
    result = usage.collect_run(root, {"worker": [w], "reviewer": [r]})
    assert result["combined_reported_usage"] == {
        "input_tokens": 280,
        "cached_input_tokens": 140,
        "output_tokens": 20,
        "reasoning_output_tokens": 6,
        "total_tokens": 300,
    }
    assert result["categories"]["worker"]["unique_threads"] == 1
    assert result["categories"]["worker"]["invocations_without_turn_completed"] == 1
    assert result["categories"]["reviewer"]["reported_usage"]["input_tokens"] == 30


def test_missing_receipt_is_not_zero(tmp_path):
    root = tmp_path / "euler-structured"
    write(
        root / "supervisor/turn-00001/response.json",
        [{"type": "thread.started", "thread_id": "missing"}],
    )
    result = usage.collect_run(root, {})
    assert result["combined_reported_usage"] is None
    assert result["categories"]["worker"]["threads_without_usage"] == 1


def test_fallback_is_last_cumulative_receipt_not_sum(tmp_path):
    root = tmp_path / "euler-frontier"
    for turn, n in [(1, 100), (2, 250)]:
        write(
            root / f"supervisor/turn-{turn:05d}/response.json",
            [
                {"type": "thread.started", "thread_id": "worker"},
                {"type": "turn.completed", "usage": {"input_tokens": n, "output_tokens": 10}},
            ],
        )
    result = usage.collect_run(root, {})
    assert result["combined_reported_usage"]["input_tokens"] == 250
    assert result["combined_reported_usage"]["total_tokens"] == 260


def test_counter_regression_is_visible(tmp_path):
    path = write(tmp_path / "session.jsonl", [count(100), count(40)])
    assert usage.cumulative_usage(path)["counter_regressions"]
