from simjecture_monitor.accounting import native_usage
from simjecture_monitor.events import put


def test_resumed_counters_cover_interrupted_thread_without_double_counting(tmp_path):
    for number, usage in enumerate(
        [
            None,
            dict(input_tokens=100, output_tokens=10),
            dict(input_tokens=250, cached_input_tokens=200, output_tokens=30),
        ]
    ):
        put(
            tmp_path / str(number) / "usage.json",
            dict(
                backend="codex",
                scope="cumulative_thread",
                thread_id="same",
                role="worker",
                usage=usage,
                reported_at=number,
            ),
        )
    put(
        tmp_path / "unknown/usage.json",
        dict(
            backend="codex",
            scope="cumulative_thread",
            thread_id=None,
            role="reviewer",
            usage=None,
            reported_at=4,
        ),
    )
    result = native_usage(tmp_path)
    assert result["known_cumulative_thread_totals"] == dict(
        input_tokens=250, cached_input_tokens=200, output_tokens=30
    )
    assert result["invocation_receipts"] == 4 and result["measured_threads"] == 1
    assert result["uncovered_thread_ids"] == []
    assert len(result["unidentified_invocations"]) == 1
    assert result["invocation_receipts_without_usage"] == 2


def test_later_interruption_leaves_new_usage_uncovered(tmp_path):
    for number, usage in enumerate([dict(input_tokens=100, output_tokens=10), None]):
        put(
            tmp_path / str(number) / "usage.json",
            dict(
                backend="codex",
                scope="cumulative_thread",
                thread_id="unfinished",
                role="worker",
                usage=usage,
                reported_at=number,
            ),
        )
    result = native_usage(tmp_path)
    assert result["known_cumulative_thread_totals"]["input_tokens"] == 100
    assert result["uncovered_thread_ids"] == ["unfinished"]
