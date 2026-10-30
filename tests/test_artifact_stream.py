"""Synthetic transport tests; no remote jobs or private fixtures."""

import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import pytest

from conjecture_solver.execution_pool import (
    Transport,
    WorkerTimeout,
    WorkerUnavailable,
    _partial_path,
    _stream_fetch,
    download,
)
from conjecture_solver.worker_protocol import CHUNK_BYTES


def artifact(tmp_path):
    root = tmp_path / "worker"
    job = "job_" + "a" * 40
    workspace = root / "jobs" / job / "workspace"
    workspace.mkdir(parents=True)
    data = bytes(range(256)) * (CHUNK_BYTES // 256 * 3 + 43)
    (workspace / "result.bin").write_bytes(data)
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    (workspace.parent / "state.json").write_text(
        json.dumps(
            {
                "id": job,
                "status": "succeeded",
                "artifacts": {"result.bin": meta},
            }
        )
    )
    transport = Transport(
        {"id": "synthetic", "kind": "local", "root": str(root), "python": sys.executable}
    )
    return transport, job, data, meta


def test_single_process_streams_multiple_old_worker_fetches(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module

    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    transport, job, data, meta = artifact(tmp_path)
    started = []
    popen = module.subprocess.Popen

    def count(*args, **kwargs):
        started.append(1)
        return popen(*args, **kwargs)

    monkeypatch.setattr(module.subprocess, "Popen", count)
    dest = tmp_path / "download" / "result.bin"
    download(transport, job, "result.bin", meta, dest)
    assert dest.read_bytes() == data
    assert len(started) == 1
    assert not _partial_path(dest, job, "result.bin", meta).exists()


def test_disconnect_retains_partial_and_resumes_without_duplicate_chunks(tmp_path):
    data = b"x" * (3 * CHUNK_BYTES + 3)
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    class Simulated:
        failed = False
        offsets = []

        def call(self, method, **kw):
            assert method == "fetch"
            off = kw["offset"]
            self.offsets.append(off)
            if off == CHUNK_BYTES and not self.failed:
                self.failed = True
                raise WorkerUnavailable("synthetic interruption")
            return dict(
                meta, offset=off, data=base64.b64encode(data[off : off + CHUNK_BYTES]).decode()
            )

    fake = Simulated()
    dest = tmp_path / "result.bin"
    with pytest.raises(WorkerUnavailable):
        download(fake, "job-a", "result.bin", meta, dest)
    assert _partial_path(dest, "job-a", "result.bin", meta).stat().st_size == CHUNK_BYTES
    download(fake, "job-a", "result.bin", meta, dest)
    assert dest.read_bytes() == data
    assert fake.offsets == [0, CHUNK_BYTES, CHUNK_BYTES, 2 * CHUNK_BYTES, 3 * CHUNK_BYTES]


def test_tampered_partial_and_changed_identity_never_import(tmp_path):
    data = b"legitimate output"
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    dest = tmp_path / "result"
    partial = _partial_path(dest, "job-a", "result", meta)
    partial.write_bytes(b"X" * len(data))
    partial.chmod(0o600)

    class NoCalls:
        def call(self, *args, **kwargs):
            pytest.fail("Complete partial should be verified without a fetch")

    with pytest.raises(ValueError, match="SHA256"):
        download(NoCalls(), "job-a", "result", meta, dest)
    assert partial.stat().st_size == 0 and not dest.exists()
    partial.unlink()
    partial.symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="Unsafe"):
        download(NoCalls(), "job-a", "result", meta, dest)
    assert partial.is_symlink()


def test_stalled_stream_has_bounded_timeout_and_reaps_process(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module

    monkeypatch.setattr(module, "_FETCH_STREAM", "import time; time.sleep(30)")
    transport = Transport(
        {"id": "synthetic", "kind": "local", "root": str(tmp_path), "python": sys.executable}
    )
    with pytest.raises(WorkerTimeout):
        list(_stream_fetch(transport, "job-a", "result", {"bytes": 1}, 0, timeout=0.2))


def test_stream_rejects_remote_mutation_and_preserves_destination(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    transport, job, data, meta = artifact(tmp_path)
    (Path(transport.machine.root) / "jobs" / job / "workspace/result.bin").write_bytes(
        b"z" * len(data)
    )
    destination = tmp_path / "result.bin"
    with pytest.raises(ValueError, match="SHA256"):
        download(transport, job, "result.bin", meta, destination)
    assert not destination.exists()


def test_dispatch_retries_terminal_result_after_deadline_without_resubmission(monkeypatch):
    import conjecture_solver.execution_pool as module

    job = "job_" + "a" * 40
    record = {"id": "exp_fixture", "machine": "fixture", "status": "running"}
    service = type("Service", (), {})()
    service.root = Path("/synthetic")
    service.manifest = {
        "deadline": 1,
        "execution_pool": {"registry": "unused", "workers": {"fixture": {}}},
    }
    service._read = lambda *_: record
    calls = []

    class StubTransport:
        def call(self, method, **kwargs):
            calls.append(method)
            assert method == "status" and kwargs["identifier"] == job
            return {"id": job, "status": "succeeded"}

    class Registry:
        def __init__(self, *args):
            pass

        def transport(self, *args, **kwargs):
            return StubTransport()

    monkeypatch.setattr(module, "MachineRegistry", Registry)
    monkeypatch.setattr(module, "_specification", lambda *_: {"id": job})

    def save(_service, _record, **values):
        record.update(values)

    monkeypatch.setattr(module, "save_progress", save)
    attempts = []

    def consume(*args):
        attempts.append(1)
        if len(attempts) == 1:
            raise WorkerUnavailable("synthetic disconnect")
        record["status"] = "succeeded"

    monkeypatch.setattr(module, "import_result", consume)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    module.dispatch(service, record)
    assert calls == ["status"]
    assert len(attempts) == 1 and record["status"] == "running"
    assert record["collection_deferred"]
    assert record["remote_terminal_status"] == "succeeded"


def test_explicit_fetch_accounts_for_existing_partial_only_once(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module
    from conjecture_solver.research_service import ResearchService, put

    data = b"a" * (2 * CHUNK_BYTES + 100)
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    service = ResearchService.create(tmp_path / "study", "A synthetic claim.")
    manifest = dict(service.manifest)
    manifest["execution_pool"] = {"registry": "unused", "workers": {"fixture": {}}}
    put(service.root / "research.json", manifest)
    experiment = "exp_" + "a" * 24
    job = "job_" + "a" * 40
    directory = service.root / "experiments" / experiment
    (directory / "workspace").mkdir(parents=True)
    put(
        service.root / "experiments" / (experiment + ".json"),
        {
            "id": experiment,
            "status": "succeeded",
            "remote_job": job,
            "machine": "fixture",
            "remote_artifacts": {"result.bin": meta},
            "artifacts": {},
            "workspace_limit_bytes": len(data) + 1024,
        },
    )
    partial = _partial_path(directory / "workspace/result.bin", job, "result.bin", meta)
    partial.write_bytes(data[:CHUNK_BYTES])
    partial.chmod(0o600)

    class StubTransport:
        def call(self, method, **kwargs):
            offset = kwargs["offset"]
            return dict(
                meta,
                offset=offset,
                data=base64.b64encode(data[offset : offset + CHUNK_BYTES]).decode(),
            )

    class Registry:
        def __init__(self, *args):
            pass

        def transport(self, *args, **kwargs):
            return StubTransport()

    monkeypatch.setattr(module, "MachineRegistry", Registry)
    result = service.fetch_remote(experiment, "result.bin")
    assert Path(result["path"]).read_bytes() == data


def test_changed_remote_identity_is_rejected_without_replacing_existing_file(tmp_path):
    data = b"expected"
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    destination = tmp_path / "result"
    destination.write_bytes(b"prior file")

    class Changed:
        def call(self, *_args, **kwargs):
            return {
                "offset": kwargs["offset"],
                "bytes": len(data),
                "sha256": "0" * 64,
                "data": base64.b64encode(data).decode(),
            }

    with pytest.raises(ValueError, match="identity changed"):
        download(Changed(), "job-a", "result", meta, destination)
    assert destination.read_bytes() == b"prior file"
    assert _partial_path(destination, "job-a", "result", meta).stat().st_size == 0


def test_stream_consumer_error_reaps_subprocess_and_redacts_password(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module

    monkeypatch.setattr(
        module,
        "_FETCH_STREAM",
        (
            "import json,time\n"
            "print(json.dumps({'ok':False,'error':'error synthetic-secret'}),flush=True)\n"
            "time.sleep(30)\n"
        ),
    )
    started = []
    popen = module.subprocess.Popen

    def capture(*args, **kwargs):
        process = popen(*args, **kwargs)
        started.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", capture)
    transport = Transport(
        {"id": "fixture", "kind": "local", "root": str(tmp_path), "python": sys.executable},
        password="synthetic-secret",
    )
    data = b"test"
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    with pytest.raises(ValueError) as error:
        download(transport, "job-a", "result", meta, tmp_path / "result")
    assert "synthetic-secret" not in str(error.value)
    assert "[redacted]" in str(error.value)
    assert len(started) == 1 and started[0].poll() is not None


def test_partial_moved_before_lock_is_never_written_or_unlinked(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module

    data = b"some content"
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    destination = tmp_path / "result"
    partial = _partial_path(destination, "job-a", "result", meta)
    partial.write_bytes(b"original")
    partial.chmod(0o600)
    original = module.fcntl.flock

    def moved(fd, operation):
        original(fd, operation)
        partial.rename(destination)

    monkeypatch.setattr(module.fcntl, "flock", moved)
    with pytest.raises(WorkerUnavailable, match="moved"):
        download(object(), "job-a", "result", meta, destination)
    assert destination.read_bytes() == b"original"
    assert not partial.exists()


def test_reconcile_does_not_respawn_deferred_collection_after_deadline(tmp_path, monkeypatch):
    import conjecture_solver.mvp_launch as launch
    from conjecture_solver.research_service import ResearchService, put

    service = ResearchService.create(tmp_path / "study", "A synthetic claim.")
    manifest = dict(service.manifest)
    manifest["deadline"] = 1
    put(service.root / "research.json", manifest)
    identity = launch.read_process_identity(os.getpid()).model_dump(mode="json")
    record = {
        "id": "exp_fixture",
        "status": "running",
        "machine": "fixture",
        "worker_identity": identity,
        "remote_terminal_status": "succeeded",
        "collection_deferred": True,
    }
    put(service.root / "experiments/exp_fixture.json", record)
    monkeypatch.setattr(launch, "process_identity_matches", lambda _: False)
    monkeypatch.setattr(service, "_spawn_experiment", lambda _: pytest.fail("respawned"))
    service.reconcile_workers()
    assert service._read("experiments", "exp_fixture")["status"] == "running"
    manifest["deadline"] = time.time() + 100
    put(service.root / "research.json", manifest)
    resumed = []
    monkeypatch.setattr(service, "_spawn_experiment", lambda record: resumed.append(record["id"]))
    service.reconcile_workers()
    assert resumed == ["exp_fixture"]
    assert service._read("experiments", "exp_fixture")["status"] == "queued"
    record["collection_cancel_requested"] = True
    put(service.root / "experiments/exp_fixture.json", record)
    resumed.clear()
    service.reconcile_workers()
    assert not resumed


def test_continuous_stream_is_stopped_at_absolute_deadline(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module

    monkeypatch.setattr(
        module,
        "_FETCH_STREAM",
        (
            "import base64,json,time\n"
            "i=0\n"
            "while True:\n"
            " print(json.dumps({'ok':True,'result':{'data':base64.b64encode(b'x'*1024).decode(),"
            "'offset':i}}),flush=True)\n"
            " i+=1024\n"
            " time.sleep(0.01)\n"
        ),
    )
    started = []
    popen = module.subprocess.Popen

    def capture(*args, **kwargs):
        process = popen(*args, **kwargs)
        started.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", capture)
    transport = Transport(
        {"id": "fixture", "kind": "local", "root": str(tmp_path), "python": sys.executable}
    )
    chunks = []
    with pytest.raises(WorkerTimeout):
        for chunk in _stream_fetch(
            transport, "job-a", "result", {"bytes": 10**9}, 0, timeout=2, deadline=time.time() + 0.2
        ):
            chunks.append(chunk)
    assert len(chunks) > 1
    assert started[0].poll() is not None


def test_invalid_chunk_closes_stream_process_before_return(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module

    monkeypatch.setattr(
        module,
        "_FETCH_STREAM",
        (
            "import base64,json,time\n"
            "print(json.dumps({'ok':True,'result':{'offset':0,'bytes':1,"
            "'sha256':'0'*64,'data':base64.b64encode(b'x').decode()}}),flush=True)\n"
            "time.sleep(30)\n"
        ),
    )
    started = []
    popen = module.subprocess.Popen

    def capture(*args, **kwargs):
        process = popen(*args, **kwargs)
        started.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", capture)
    transport = Transport(
        {"id": "fixture", "kind": "local", "root": str(tmp_path), "python": sys.executable}
    )
    meta = {"bytes": 1, "sha256": hashlib.sha256(b"x").hexdigest()}
    with pytest.raises(ValueError, match="identity changed"):
        download(transport, "job-a", "result", meta, tmp_path / "result")
    assert len(started) == 1 and started[0].poll() is not None


def test_hardlinked_or_nonprivate_partial_is_never_modified(tmp_path):
    data = b"expected"
    meta = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    destination = tmp_path / "result"
    partial = _partial_path(destination, "job-a", "result", meta)
    outside = tmp_path / "outside"
    outside.write_bytes(b"do not change")
    outside.chmod(0o600)
    os.link(outside, partial)
    with pytest.raises(ValueError, match="Unsafe"):
        download(object(), "job-a", "result", meta, destination)
    assert outside.read_bytes() == b"do not change"
    partial.unlink()
    partial.write_bytes(b"other")
    partial.chmod(0o644)
    with pytest.raises(ValueError, match="Unsafe"):
        download(object(), "job-a", "result", meta, destination)
    assert partial.read_bytes() == b"other"


def test_cancel_does_not_mark_uncollected_terminal_job_complete(monkeypatch):
    import conjecture_solver.execution_pool as module

    record = {
        "status": "running",
        "remote_terminal_status": "succeeded",
        "collection_deferred": True,
    }
    service = object()
    monkeypatch.setattr(
        module, "MachineRegistry", lambda *_: pytest.fail("must not contact worker")
    )

    def save(_service, _record, **values):
        record.update(values)
        return record

    monkeypatch.setattr(module, "save_progress", save)
    assert module.cancel_remote(service, record) is record
    assert record["status"] == "running" and record["collection_cancel_requested"]


def test_successful_worker_racing_cancel_still_needs_collection(monkeypatch):
    import conjecture_solver.execution_pool as module

    job = "job_" + "a" * 40
    record = {"id": "exp_fixture", "machine": "fixture", "status": "running"}
    service = type("Service", (), {})()
    service.manifest = {"execution_pool": {"registry": "unused", "workers": {"fixture": {}}}}

    class FakeTransport:
        def call(self, method, **kwargs):
            assert method == "cancel" and kwargs["identifier"] == job
            return {"id": job, "status": "succeeded"}

    class Registry:
        def __init__(self, *_):
            pass

        def transport(self, *_args, **_kwargs):
            return FakeTransport()

    monkeypatch.setattr(module, "MachineRegistry", Registry)
    monkeypatch.setattr(module, "job_identifier", lambda *_: job)

    def save(_service, _record, **values):
        record.update(values)
        return record

    monkeypatch.setattr(module, "save_progress", save)
    module.cancel_remote(service, record)
    assert record["status"] == "running" and record["remote_terminal_status"] == "succeeded"


def test_cancel_stalled_stream_reaps_process_and_keeps_partial(tmp_path, monkeypatch):
    import conjecture_solver.execution_pool as module

    monkeypatch.setattr(module, "_FETCH_STREAM", "import time; time.sleep(30)")
    started = []
    popen = module.subprocess.Popen

    def capture(*args, **kwargs):
        process = popen(*args, **kwargs)
        started.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", capture)
    transport = Transport(
        {"id": "fixture", "kind": "local", "root": str(tmp_path), "python": sys.executable}
    )
    meta = {"bytes": 4, "sha256": hashlib.sha256(b"test").hexdigest()}
    destination = tmp_path / "result"
    partial = _partial_path(destination, "job-a", "result", meta)
    partial.write_bytes(b"te")
    partial.chmod(0o600)
    stop = time.monotonic() + 0.2
    with pytest.raises(module.CollectionCancelled):
        download(
            transport,
            "job-a",
            "result",
            meta,
            destination,
            should_stop=lambda: time.monotonic() >= stop,
        )
    assert partial.read_bytes() == b"te" and not destination.exists()
    assert started[0].poll() is not None
