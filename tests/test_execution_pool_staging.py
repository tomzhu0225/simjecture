"""Synthetic transport tests for bounded, idempotent staging acknowledgements."""

import base64
from types import SimpleNamespace

import pytest

from conjecture_solver.execution_pool import _stage_input
from conjecture_solver.worker_protocol import CHUNK_BYTES


def test_reconnected_completed_input_needs_only_one_chunk(tmp_path):
    path = tmp_path / "large.bin"
    path.write_bytes(b"x" * (3 * CHUNK_BYTES + 7))
    calls = []

    def call(method, **arguments):
        calls.append((method, arguments))
        return {"offset": path.stat().st_size, "complete": True}

    _stage_input(SimpleNamespace(call=call), "job", path.name, path)
    assert len(calls) == 1
    assert len(base64.b64decode(calls[0][1]["data"])) == CHUNK_BYTES


@pytest.mark.parametrize("size", [0, 7, CHUNK_BYTES, CHUNK_BYTES + 7])
def test_staging_sends_exact_chunks_and_final_ack(tmp_path, size):
    path = tmp_path / "input.bin"
    path.write_bytes(b"x" * size)
    received = bytearray()
    final = []

    def call(method, **arguments):
        assert method == "stage"
        assert arguments["offset"] == len(received)
        received.extend(base64.b64decode(arguments["data"]))
        final.append(arguments["final"])
        return {"offset": len(received), "complete": arguments["final"]}

    _stage_input(SimpleNamespace(call=call), "job", path.name, path)
    assert received == path.read_bytes()
    assert final == [False] * (len(final) - 1) + [True]


@pytest.mark.parametrize(
    "reply", [{"offset": 1, "complete": True}, {"offset": 3, "complete": False}]
)
def test_staging_rejects_inconsistent_final_ack(tmp_path, reply):
    path = tmp_path / "input.bin"
    path.write_bytes(b"abc")
    with pytest.raises(ValueError, match="acknowledge"):
        _stage_input(SimpleNamespace(call=lambda *a, **kw: reply), "job", path.name, path)


@pytest.mark.parametrize("complete_before_reconnect", [False, True])
def test_real_worker_stage_replays_partial_and_completed_inputs(
    tmp_path, complete_before_reconnect
):
    import time

    from conjecture_solver.execution_worker import Worker
    from conjecture_solver.worker_protocol import WorkerConfig, checksum, fingerprint, private_put

    worker = Worker(tmp_path / "worker")
    config = WorkerConfig().model_dump(mode="json")
    private_put(worker.root / "config.json", config)
    source = tmp_path / "input.py"
    source.write_bytes(b"#" * (2 * CHUNK_BYTES + 7))
    identifier = "job_" + "a" * 40
    worker.create(
        {
            "id": identifier,
            "binding": {
                "source": source.name,
                "inputs": {source.name: checksum(source)},
                "args": [],
                "capability": None,
                "runtime_sha256": None,
            },
            "outputs": ["result.json"],
            "deadline": time.time() + 60,
            "timeout": 30,
            "config_sha256": fingerprint(config),
        }
    )
    calls = []

    def call(method, **arguments):
        assert method == "stage"
        calls.append(arguments)
        return worker.stage(**arguments)

    transport = SimpleNamespace(call=call)
    if complete_before_reconnect:
        _stage_input(transport, identifier, source.name, source)
    else:
        worker.stage(identifier, source.name, 0, base64.b64encode(b"#" * CHUNK_BYTES).decode())
    calls.clear()
    _stage_input(transport, identifier, source.name, source)
    assert len(calls) == (1 if complete_before_reconnect else 3)
    assert checksum(worker.directory(identifier) / "workspace" / source.name) == checksum(source)
