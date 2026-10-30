"""Synthetic same-worker artifact staging; no remote services or scientific claims."""

import base64
import hashlib
import os
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from conjecture_solver.execution_worker import Worker
from conjecture_solver.worker_protocol import CHUNK_BYTES, PROTOCOL, Experiment, fingerprint, put


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def worker(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    worker = Worker(tmp_path / "worker")
    result = worker.configure({"execution_backend": "process-cooperative"})
    assert result["features"]["artifact_inputs"] is True
    return worker


def specification(worker, job, code, inputs=None, remote_inputs=None, workspace_bytes=4 * 1024**3):
    return {
        "id": job,
        "binding": {
            "source": "run.py",
            "args": [],
            "inputs": {"run.py": sha(code)} | (inputs or {}),
            "capability": None,
            "runtime_sha256": None,
        },
        "outputs": ["result.bin"],
        "deadline": time.time() + 120,
        "timeout": 30,
        "config_sha256": fingerprint(worker.config.model_dump(mode="json")),
        "workspace_bytes": workspace_bytes,
        **({"remote_inputs": remote_inputs} if remote_inputs is not None else {}),
    }


def wait(worker, job):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        state = worker.status(job)
        if state["status"] not in {"staging", "queued", "running"}:
            return state
        time.sleep(0.05)
    pytest.fail("Synthetic worker did not finish")


def producer(worker):
    job = "job_" + "a" * 40
    code = b"from pathlib import Path\nPath('result.bin').write_bytes(b'x'*2097183)\n"
    worker.create(specification(worker, job, code))
    worker.stage(job, "run.py", 0, base64.b64encode(code).decode(), True)
    worker.submit(job)
    state = wait(worker, job)
    assert state["status"] == "succeeded", state
    return job, state["artifacts"]["result.bin"]


def consumer(worker, producer_job, meta):
    job = "job_" + "b" * 40
    code = (
        b"from pathlib import Path\np=Path('checkpoint.bin')\n"
        b"Path('result.bin').write_bytes(p.read_bytes()[:2])\n"
    )
    reference = {
        "job": producer_job,
        "path": "result.bin",
        "sha256": meta["sha256"],
        "bytes": meta["bytes"],
    }
    request = specification(
        worker, job, code, {"checkpoint.bin": meta["sha256"]}, {"checkpoint.bin": reference}
    )
    worker.create(request)
    worker.stage(job, "run.py", 0, base64.b64encode(code).decode(), True)
    return job, request


def test_producer_to_consumer_copies_locally_and_preserves_source(worker):
    parent, meta = producer(worker)
    job, request = consumer(worker, parent, meta)
    staged = worker.call(
        {
            "protocol": PROTOCOL,
            "method": "stage_artifact",
            "arguments": {"identifier": job, "name": "checkpoint.bin"},
        }
    )
    assert staged == {"offset": meta["bytes"], "complete": True}
    original = worker.directory(parent) / "workspace/result.bin"
    copied = worker.directory(job) / "workspace/checkpoint.bin"
    assert original.read_bytes() == copied.read_bytes()
    assert os.stat(original).st_ino != os.stat(copied).st_ino
    assert worker.stage_artifact(job, "checkpoint.bin") == staged
    assert worker.create(request)["id"] == job
    worker.submit(job)
    final = wait(worker, job)
    assert final["status"] == "succeeded", final
    copied.write_bytes(b"modified")
    assert sha(original.read_bytes()) == meta["sha256"]


def test_resident_copy_stops_at_destination_deadline(worker, monkeypatch):
    from types import SimpleNamespace

    import conjecture_solver.execution_worker as module

    parent, meta = producer(worker)
    job, request = consumer(worker, parent, meta)
    clock = [time.time()]
    monkeypatch.setattr(module, "time", SimpleNamespace(time=lambda: clock[0]))
    original = worker.stage
    calls = []

    def stage(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(result)
        clock[0] = request["deadline"] + 1
        return result

    monkeypatch.setattr(worker, "stage", stage)
    with pytest.raises(ValueError, match="deadline"):
        worker.stage_artifact(job, "checkpoint.bin")
    assert len(calls) == 1
    assert worker.status(job)["status"] == "timed_out"
    workspace = worker.directory(job) / "workspace"
    assert not (workspace / "checkpoint.bin").exists()
    assert (workspace / ".checkpoint.bin.upload").stat().st_size == CHUNK_BYTES
    assert sha((worker.directory(parent) / "workspace/result.bin").read_bytes()) == meta["sha256"]


def test_legacy_serialization_unchanged_and_remote_input_schema(worker):
    job = "job_" + "b" * 40
    code = b"print('fixture')"
    legacy = specification(worker, job, code)
    value = Experiment.model_validate(legacy)
    assert "remote_inputs" not in value.model_dump(mode="json")
    assert value.model_dump(mode="json") == Experiment.model_validate(
        legacy | {"remote_inputs": {}}
    ).model_dump(mode="json")
    valid = {"job": "job_" + "a" * 40, "path": "a.bin", "sha256": sha(b"x"), "bytes": 1}
    cases = [
        {"job": job},
        {"path": "../escape"},
        {"path": "/absolute"},
        {"sha256": "bad"},
        {"bytes": True},
        {"bytes": -1},
    ]
    for change in cases:
        with pytest.raises(ValidationError):
            Experiment.model_validate(
                specification(worker, job, code, {"x": sha(b"x")}, {"x": valid | change})
            )
    with pytest.raises(ValidationError, match="frozen"):
        Experiment.model_validate(specification(worker, job, code, {"x": sha(b"y")}, {"x": valid}))
    with pytest.raises(ValidationError, match="frozen"):
        Experiment.model_validate(specification(worker, job, code, {}, {"x": valid}))


def recorded_source(worker, data, status="succeeded", metadata=None):
    job = "job_" + "c" * 40
    directory = worker.directory(job)
    (directory / "workspace").mkdir(parents=True)
    (directory / "workspace/data.bin").write_bytes(data)
    meta = metadata or {"bytes": len(data), "sha256": sha(data)}
    put(directory / "state.json", {"id": job, "status": status, "artifacts": {"data.bin": meta}})
    return job, meta


def prepare_reference(worker, ref, workspace_bytes=4 * 1024**3):
    job = "job_" + "d" * 40
    code = b"print('fixture')"
    request = specification(
        worker,
        job,
        code,
        {"copy.bin": ref["sha256"]},
        {"copy.bin": ref},
        workspace_bytes=workspace_bytes,
    )
    worker.create(request)
    worker.stage(job, "run.py", 0, base64.b64encode(code).decode(), True)
    return job


def test_source_must_be_terminal_and_metadata_must_match(worker):
    source, meta = recorded_source(worker, b"data", status="running")
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": 4}
    job = prepare_reference(worker, ref)
    with pytest.raises(ValueError, match="terminal"):
        worker.stage_artifact(job, "copy.bin")
    put(
        worker.directory(source) / "state.json",
        {"id": source, "status": "succeeded", "artifacts": {}},
    )
    with pytest.raises(ValueError, match="recorded identity"):
        worker.stage_artifact(job, "copy.bin")
    put(
        worker.directory(source) / "state.json",
        {
            "id": source,
            "status": "succeeded",
            "artifacts": {"data.bin": {"bytes": 3, "sha256": meta["sha256"]}},
        },
    )
    with pytest.raises(ValueError, match="recorded identity"):
        worker.stage_artifact(job, "copy.bin")
    put(
        worker.directory(source) / "state.json",
        {
            "id": source,
            "status": "succeeded",
            "artifacts": {"data.bin": {"bytes": 4, "sha256": "0" * 64}},
        },
    )
    with pytest.raises(ValueError, match="recorded identity"):
        worker.stage_artifact(job, "copy.bin")
    with pytest.raises(ValueError, match="no frozen"):
        worker.stage_artifact(job, "missing")
    assert not (worker.directory(job) / "workspace/copy.bin").exists()


def test_changed_source_same_size_and_symlink_never_staged(worker, tmp_path):
    source, meta = recorded_source(worker, b"abcd")
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": 4}
    job = prepare_reference(worker, ref)
    source_file = worker.directory(source) / "workspace/data.bin"
    source_file.write_bytes(b"zzzz")
    with pytest.raises(ValueError, match="hash mismatch"):
        worker.stage_artifact(job, "copy.bin")
    assert not (worker.directory(job) / "workspace/copy.bin").exists()
    source_file.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"abcd")
    source_file.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        worker.stage_artifact(job, "copy.bin")


def test_reference_quota_and_cancel_are_enforced(worker):
    data = b"a" * (CHUNK_BYTES + 1)
    source, meta = recorded_source(worker, data)
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": len(data)}
    job = prepare_reference(worker, ref, workspace_bytes=CHUNK_BYTES)
    with pytest.raises(ValueError, match="workspace reservation"):
        worker.stage_artifact(job, "copy.bin")
    assert not (worker.directory(job) / "workspace/copy.bin").exists()
    worker.cancel(job)
    with pytest.raises(ValueError, match="no longer accepting"):
        worker.stage_artifact(job, "copy.bin")
    assert sha((worker.directory(source) / "workspace/data.bin").read_bytes()) == meta["sha256"]


def test_interrupted_copy_replays_verified_chunks_and_does_not_hardlink(worker, monkeypatch):
    data = b"x" * (CHUNK_BYTES + 75)
    source, meta = recorded_source(worker, data)
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": len(data)}
    job = prepare_reference(worker, ref)
    stage = worker.stage
    calls = []

    def interrupted(identifier, name, offset, encoded, final=False):
        calls.append(offset)
        if offset and len(calls) == 2:
            raise RuntimeError("simulated interruption")
        return stage(identifier, name, offset, encoded, final)

    monkeypatch.setattr(worker, "stage", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        worker.stage_artifact(job, "copy.bin")
    assert not (worker.directory(job) / "workspace/copy.bin").exists()
    result = worker.stage_artifact(job, "copy.bin")
    assert result == {"offset": len(data), "complete": True}
    assert calls == [0, CHUNK_BYTES, CHUNK_BYTES]
    assert (worker.directory(job) / "workspace/copy.bin").read_bytes() == data


def test_empty_source_stages_and_existing_copy_mutation_rejected(worker):
    source, meta = recorded_source(worker, b"")
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": 0}
    job = prepare_reference(worker, ref)
    assert worker.stage_artifact(job, "copy.bin") == {"offset": 0, "complete": True}
    target = worker.directory(job) / "workspace/copy.bin"
    target.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Previously staged input changed"):
        worker.stage_artifact(job, "copy.bin")


def test_missing_file_and_changed_size_rejected(worker):
    source, meta = recorded_source(worker, b"abcd")
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": 4}
    job = prepare_reference(worker, ref)
    source_file = worker.directory(source) / "workspace/data.bin"
    source_file.write_bytes(b"short")
    with pytest.raises(ValueError, match="changed size"):
        worker.stage_artifact(job, "copy.bin")
    source_file.unlink()
    with pytest.raises(ValueError, match="unavailable"):
        worker.stage_artifact(job, "copy.bin")
    assert not (worker.directory(job) / "workspace/copy.bin").exists()


def test_rerequest_rejects_changed_reference(worker):
    source, meta = recorded_source(worker, b"abcd")
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": 4}
    job = prepare_reference(worker, ref)
    request = (worker.directory(job) / "request.json").read_text()
    import json

    modified = json.loads(request)
    modified["remote_inputs"]["copy.bin"]["path"] = "another.bin"
    with pytest.raises(ValueError, match="different request"):
        worker.create(modified)


def test_linked_upload_is_never_followed(worker, tmp_path):
    source, meta = recorded_source(worker, b"abcd")
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": 4}
    job = prepare_reference(worker, ref)
    outside = tmp_path / "outside-upload"
    outside.write_bytes(b"safe")
    partial = worker.directory(job) / "workspace/.copy.bin.upload"
    partial.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        worker.stage_artifact(job, "copy.bin")
    assert outside.read_bytes() == b"safe"


def test_existing_hardlinked_upload_cannot_alias_producer(worker):
    source, meta = recorded_source(worker, b"abcd")
    ref = {"job": source, "path": "data.bin", "sha256": meta["sha256"], "bytes": 4}
    job = prepare_reference(worker, ref)
    original = worker.directory(source) / "workspace/data.bin"
    partial = worker.directory(job) / "workspace/.copy.bin.upload"
    os.link(original, partial)
    with pytest.raises(ValueError, match="hard links"):
        worker.stage_artifact(job, "copy.bin")
    assert not (worker.directory(job) / "workspace/copy.bin").exists()
    assert original.read_bytes() == b"abcd"
