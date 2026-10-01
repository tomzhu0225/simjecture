"""Receipt-only harness tests; these do not claim numerical sandbox execution."""

import time

import pytest

from conjecture_solver import execution_worker
from conjecture_solver.execution_worker import Worker
from conjecture_solver.worker_protocol import WorkerConfig, load, private_put, put


def receipt(worker, index, status="succeeded", **values):
    identifier = f"job_{index:040x}"
    record = {"id": identifier, "status": status, "deadline": time.time() + 60, **values}
    worker.directory(identifier).mkdir(parents=True, exist_ok=True)
    put(worker.directory(identifier) / "state.json", record)
    return record


def test_targeted_status_reads_one_receipt_independent_of_history(tmp_path, monkeypatch):
    worker = Worker(tmp_path)
    for index in range(100):
        receipt(worker, index)
    target = receipt(worker, 100, "staging", deadline=time.time() - 1)
    reads = []

    def counted(path):
        reads.append(path)
        return load(path)

    monkeypatch.setattr(execution_worker, "load", counted)
    result = worker.status(target["id"])
    assert result["status"] == "timed_out"
    assert reads == [worker.directory(target["id"]) / "state.json"]
    assert load(reads[0]) == result


def test_aggregate_status_reconciles_each_receipt_once(tmp_path, monkeypatch):
    worker = Worker(tmp_path)
    private_put(worker.root / "config.json", WorkerConfig().model_dump())
    expired = receipt(worker, 1, "staging", deadline=time.time() - 1)
    receipt(worker, 2)
    reads = []

    def counted(path):
        reads.append(path)
        return load(path)

    monkeypatch.setattr(execution_worker, "load", counted)
    result = worker.status()
    assert result["total_jobs"] == 2
    assert next(r for r in result["jobs"] if r["id"] == expired["id"])["status"] == "timed_out"
    assert len([p for p in reads if p.name == "state.json"]) == 2


@pytest.mark.parametrize("reason,terminal", [("operator", "cancelled"), ("deadline", "timed_out")])
def test_targeted_status_confirms_finished_cancellation(tmp_path, reason, terminal):
    worker = Worker(tmp_path)
    record = receipt(worker, 1, "cancelling", cancellation_reason=reason, cancellation_processes=[])
    result = worker.status(record["id"])
    assert result["status"] == terminal
    assert result["cancellation_confirmed"]


def test_targeted_status_does_not_require_worker_configuration(tmp_path):
    worker = Worker(tmp_path)
    identifier = "job_" + "a" * 40
    assert worker.status(identifier) == {"id": identifier, "status": "not_found"}
