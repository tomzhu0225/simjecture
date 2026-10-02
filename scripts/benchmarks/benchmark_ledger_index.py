"""Compare indexed campaign-head and incremental-replay queries.

Run from an installed checkout, for example:
    .venv/bin/python scripts/benchmarks/benchmark_ledger_index.py

This is a synthetic in-memory SQLite query benchmark, not an end-to-end
simulation speedup. Fixture rows intentionally omit a real cryptographic chain;
correctness of event creation is covered by tests/test_ledger.py. Timings exclude
fixture construction and index creation; the index costs storage and insert work.
"""

from __future__ import annotations

import argparse
import json
import statistics
import timeit

from conjecture_solver.ledger import SQLiteEventLedger


def positive_integer(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=positive_integer, default=40_000)
    parser.add_argument("--campaigns", type=positive_integer, default=8)
    parser.add_argument("--repeat", type=positive_integer, default=5)
    parser.add_argument("--number", type=positive_integer, default=500)
    args = parser.parse_args()
    with SQLiteEventLedger() as ledger:
        # Remove the new index if present to retain the pre-change baseline.
        connection = ledger._connection
        connection.execute("DROP INDEX IF EXISTS campaign_events_campaign_sequence")
        connection.executemany(
            "INSERT INTO campaign_events (campaign_id,event_id,event_type,aggregate_type,"
            "aggregate_id,idempotency_key,payload_json,created_at,previous_hash,event_hash) "
            "VALUES (?,?,'test','test','test',NULL,'{}','2026-10-01','GENESIS',?)",
            ((f"campaign_{i % args.campaigns}", f"event_{i}", str(i)) for i in range(args.rows)),
        )
        connection.commit()

        def head():
            return connection.execute(
                "SELECT event_hash FROM campaign_events "
                "WHERE campaign_id = ? ORDER BY sequence DESC LIMIT 1", ("campaign_0",)
            ).fetchone()[0]

        def tail():
            return ledger.load("campaign_0", after_sequence=max(0, args.rows - 100))

        def benchmark():
            return {
                name: statistics.median(
                    timeit.repeat(call, number=args.number, repeat=args.repeat)
                ) / args.number * 1e6
                for name, call in (("head_us", head), ("tail_us", tail))
            }

        expected = head(), tail()
        before = benchmark()
        connection.execute(
            "CREATE INDEX campaign_events_campaign_sequence "
            "ON campaign_events(campaign_id,sequence)"
        )
        after = benchmark()
        assert (head(), tail()) == expected
        print(json.dumps({
            "fixture": "synthetic in-memory query benchmark; excludes construction and writes",
            "rows": args.rows,
            "campaigns": args.campaigns,
            "repeats": args.repeat,
            "calls_per_repeat": args.number,
            "before": {key: round(value, 2) for key, value in before.items()},
            "after": {key: round(value, 2) for key, value in after.items()},
            "speedup": {key: round(before[key] / after[key], 2) for key in before},
        }, indent=2))


if __name__ == "__main__":
    main()
