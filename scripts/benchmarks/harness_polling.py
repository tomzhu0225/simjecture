"""Synthetic receipt/log benchmarks; no numerical execution or provider calls."""

import json
import statistics
import subprocess
import tempfile
import time
import tracemalloc
from pathlib import Path

from conjecture_solver.execution_worker import Worker
from conjecture_solver.provider_usage import request_accounting
from conjecture_solver.worker_protocol import put


def baseline(module):
    namespace = {
        "__package__": "conjecture_solver",
        "__file__": str(Path("src/conjecture_solver") / (module + ".py")),
    }
    exec(
        subprocess.check_output(
            ["git", "show", "2f66b8d:src/conjecture_solver/" + module + ".py"], text=True
        ),
        namespace,
    )
    return namespace


def timing(fn):
    samples = []
    for _ in range(20):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return statistics.median(samples) * 1000


def memory(fn):
    tracemalloc.start()
    result = fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak, result


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    worker = Worker(root)
    for index in range(1000):
        identifier = f"job_{index:040x}"
        worker.directory(identifier).mkdir(parents=True)
        put(worker.directory(identifier) / "state.json", {"id": identifier, "status": "succeeded"})
    old_worker = baseline("execution_worker")["Worker"](root)
    before = timing(lambda: old_worker.status(identifier))
    after = timing(lambda: worker.status(identifier))
    path = root / "response.json"
    with path.open("w") as stream:
        for i in range(200):
            stream.write(json.dumps({"type": "assistant", "content": "x" * 100000}) + "\n")
            stream.write(
                json.dumps(
                    {
                        "type": "provider_request",
                        "request_id": str(i),
                        "status": "succeeded",
                        "usage": {"input_tokens": 100, "output_tokens": 10},
                    }
                )
                + "\n"
            )
    old_accounting = baseline("provider_usage")["request_accounting"]
    old_peak, old_totals = memory(lambda: old_accounting(path))
    new_peak, new_totals = memory(lambda: request_accounting(path))
    assert old_totals == new_totals
    print(
        json.dumps(
            {
                "scope": (
                "Synthetic 1000 persisted terminal receipts; 20 median targeted polls; "
                "synthetic 20 MB provider log; no simulation or model invocation"
            ),
                "poll_before_ms": before,
                "poll_after_ms": after,
                "poll_speedup": before / after,
                "accounting_before_peak_bytes": old_peak,
                "accounting_after_peak_bytes": new_peak,
                "accounting_peak_reduction": old_peak / new_peak,
            },
            indent=2,
        )
    )
