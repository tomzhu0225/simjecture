"""Real numerical workers: placement, queues, replay, recovery and artifact integrity."""

import base64
import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from conjecture_solver.execution import probe_execution_backend
from conjecture_solver.execution_pool import MachineRegistry, WorkerUnavailable, dispatch
from conjecture_solver.execution_worker import Worker
from conjecture_solver.research_service import ResearchService
from conjecture_solver.worker_protocol import Experiment, Machine, checksum, fingerprint, load


@pytest.fixture
def registry(tmp_path):
    if not probe_execution_backend("bubblewrap")["available"]:
        pytest.skip("Real numerical worker tests require Bubblewrap namespaces")
    result = MachineRegistry(tmp_path / "registry")
    for name in ("node-a", "node-b"):
        result.save(
            {
                "id": name,
                "kind": "local",
                "root": str(tmp_path / name),
                "python": sys.executable,
                "config": {"cpus": 2, "memory_mb": 4096, "max_jobs": 1},
            }
        )
        result.prepare(name)
    return result


def study(tmp_path, registry, source=None, seconds=120):
    service = ResearchService.create(
        tmp_path / "study",
        "Finite worker controls",
        wall_seconds=seconds,
        execution_pool=registry.freeze(["node-a", "node-b"]),
    )
    (service.work / "calc.py").write_text(
        source
        or (
            "import time,json,os\nfrom pathlib import Path\n"
            "time.sleep(1)\nPath('result.json').write_text(json.dumps({'value':4,'pid':os.getpid()}))\n"
        )
    )
    return service


def finish(service, ids, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        records = {r["id"]: r for r in service.status()["experiments"]}
        if all(records[i]["status"] not in {"queued", "running"} for i in ids):
            return [records[i] for i in ids]
        time.sleep(0.1)
    pytest.fail("Worker did not reach a terminal receipt")


def test_parallel_placement_retry_identity_and_central_artifacts(tmp_path, registry):
    service = study(tmp_path, registry)
    first = service.run("calc.py", outputs=["result.json"], key="first", stage="exploration")
    second = service.run("calc.py", outputs=["result.json"], key="second", stage="exploration")
    assert first["machine"] != second["machine"]
    assert (
        service.run("calc.py", outputs=["result.json"], key="first", stage="exploration")["id"]
        == first["id"]
    )
    results = finish(service, [first["id"], second["id"]])
    assert all(r["status"] == "succeeded" for r in results), results
    assert max(r["started_at"] for r in results) < min(r["finished_at"] for r in results)
    for record in results:
        path = service.root / "experiments" / record["id"] / "workspace/result.json"
        assert checksum(path) == record["artifacts"]["result.json"]["sha256"]
        assert json.loads(path.read_text())["value"] == 4
        assert record["scientific_status"] == "unreviewed"
        assert record["remote_job"].startswith("job_")


def test_capacity_queues_jobs_without_oversubscription(tmp_path, registry):
    service = study(
        tmp_path,
        registry,
        "import time\nfrom pathlib import Path\ntime.sleep(2)\n"
        "Path('result.json').write_text('{\"value\":4}')\n",
    )
    ids = [
        service.run(
            "calc.py", outputs=["result.json"], machine="node-a", stage="exploration", key=str(i)
        )["id"]
        for i in range(2)
    ]
    results = finish(service, ids)
    assert all(r["status"] == "succeeded" for r in results)
    early, late = sorted(results, key=lambda r: r["started_at"])
    assert late["started_at"] >= early["finished_at"]


def test_coordinator_process_restart_reattaches_existing_remote_job(tmp_path, registry):
    service = study(
        tmp_path,
        registry,
        "import time,uuid\nfrom pathlib import Path\ntime.sleep(3)\n"
        "Path('result.json').write_text('{\"value\":4}')\n",
    )
    receipt = service.run("calc.py", outputs=["result.json"], machine="node-a", stage="exploration")
    deadline = time.time() + 20
    while time.time() < deadline:
        record = service._read("experiments", receipt["id"])
        if record.get("remote_job") and record.get("status") == "running":
            break
        time.sleep(0.1)
    assert record.get("remote_job")
    job = record["remote_job"]
    remote = registry.worker_status("node-a")
    assert sum(r["id"] == job for r in remote["jobs"]) == 1
    os.killpg(record["worker_identity"]["pid"], signal.SIGKILL)
    reopened = ResearchService(service.root)
    final = finish(reopened, [receipt["id"]])[0]
    assert final["status"] == "succeeded", final
    assert final["remote_job"] == job
    assert sum(r["id"] == job for r in registry.worker_status("node-a")["jobs"]) == 1


def test_lost_submit_response_reconnects_without_duplicate(tmp_path, registry, monkeypatch):
    service = study(tmp_path, registry)
    monkeypatch.setattr(service, "_spawn_experiment", lambda record: None)
    receipt = service.run("calc.py", outputs=["result.json"], machine="node-a", stage="exploration")
    from conjecture_solver.execution_pool import Transport

    original = Transport.call
    lost = []

    def interrupted(self, method, **kwargs):
        result = original(self, method, **kwargs)
        if method == "submit" and not lost:
            lost.append(result["id"])
            raise WorkerUnavailable("Controlled lost submission response")
        return result

    monkeypatch.setattr(Transport, "call", interrupted)
    dispatch(service, receipt)
    final = service._read("experiments", receipt["id"])
    assert final["status"] == "succeeded"
    assert final["remote_job"] == lost[0]
    assert len(registry.worker_status("node-a")["jobs"]) == 1


def test_large_undeclared_arrays_stay_remote_and_fetch_checks_integrity(tmp_path, registry):
    service = study(
        tmp_path,
        registry,
        "from pathlib import Path\nPath('array.bin').write_bytes(b'x'*500000)\n"
        "Path('result.json').write_text('{\"value\":4}')\n",
    )
    receipt = service.run("calc.py", outputs=["result.json"], machine="node-a", stage="exploration")
    final = finish(service, [receipt["id"]])[0]
    destination = service.root / "experiments" / final["id"] / "workspace/array.bin"
    assert "array.bin" in final["remote_artifacts"] and not destination.exists()
    source = (
        Path(registry.machine("node-a").root) / "jobs" / final["remote_job"] / "workspace/array.bin"
    )
    source.write_bytes(b"y" * 500000)
    with pytest.raises(ValueError, match="SHA256"):
        service.fetch_remote(final["id"], "array.bin")
    assert not destination.exists()
    source.write_bytes(b"x" * 500000)
    imported = service.fetch_remote(final["id"], "array.bin")
    assert checksum(destination) == imported["sha256"]
    assert service.fetch_remote(final["id"], "array.bin") == imported


def test_worker_protocol_rejects_changed_requests_and_unsafe_chunks(tmp_path, registry):
    worker = Worker(registry.machine("node-a").root)
    probe = worker.probe()
    body = {
        "id": "job_" + "a" * 40,
        "binding": {
            "source": "calc.py",
            "args": [],
            "inputs": {"calc.py": fingerprint("source")},
            "capability": None,
            "runtime_sha256": None,
        },
        "outputs": ["result.json"],
        "deadline": time.time() + 120,
        "timeout": 30,
        "config_sha256": probe["config_sha256"],
        "worker_id": probe["worker_id"],
    }
    record = worker.create(body)
    assert worker.create(body) == record
    with pytest.raises(ValueError, match="different request"):
        worker.create(body | {"timeout": 31})
    with pytest.raises(ValueError, match="declared"):
        worker.stage(record["id"], "../escape", 0, "")
    with pytest.raises(ValueError, match="hash mismatch"):
        worker.stage(record["id"], "calc.py", 0, base64.b64encode(b"wrong").decode(), True)
    with pytest.raises(ValueError):
        Experiment.model_validate(body | {"outputs": ["/absolute"]})
    with pytest.raises(ValueError):
        Machine.model_validate({"id": "node", "host": "-oProxyCommand=evil", "root": "/tmp/node"})


def test_cancel_before_submit_is_durable_and_never_launches(tmp_path, registry):
    worker = Worker(registry.machine("node-a").root)
    job = "job_" + "b" * 40
    assert worker.cancel(job)["status"] == "cancelled"
    assert worker.status(job)["status"] == "cancelled"
    assert not (worker.directory(job) / "workspace").exists()


def test_passwords_remain_private_and_outside_public_metadata(tmp_path):
    registry = MachineRegistry(tmp_path)
    public = registry.save(
        {
            "id": "example",
            "host": "example.invalid",
            "root": "/tmp/worker",
            "password": "only-a-fixture-password",
        }
    )
    assert public["has_password"]
    assert "only-a-fixture-password" not in json.dumps(registry.catalogue())
    private = tmp_path / ".private/example.json"
    assert private.stat().st_mode & 0o777 == 0o600
    assert load(private)["password"] == "only-a-fixture-password"


def test_running_cancel_stops_descendants_before_releasing_resources(tmp_path, registry):
    service = study(
        tmp_path,
        registry,
        "import subprocess,sys,time\nfrom pathlib import Path\n"
        "subprocess.Popen([sys.executable,'-c',"
        '"import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)"])\n'
        "Path('started.txt').write_text('ready')\ntime.sleep(60)\n",
    )
    receipt = service.run("calc.py", outputs=["result.json"], machine="node-a", stage="exploration")
    worker = Worker(registry.machine("node-a").root)
    from conjecture_solver.execution_pool import job_identifier
    from conjecture_solver.mvp_launch import ProcessIdentity, process_identity_matches

    job = job_identifier(service, receipt)
    deadline = time.time() + 20
    import psutil

    while time.time() < deadline:
        current = worker.status(job)
        if current.get("process"):
            owner = psutil.Process(current["process"]["pid"])
            if any(
                "-c" in child.cmdline() and any("signal.signal" in arg for arg in child.cmdline())
                for child in owner.children(recursive=True)
            ):
                break
        time.sleep(0.1)
    else:
        pytest.fail("Bounded worker never started its subprocess")
    service.cancel_active()
    record = worker.status(job)
    assert record["status"] == "cancelled", record
    assert record["cancellation_confirmed"]
    assert len(record["cancellation_processes"]) >= 2
    assert not any(
        process_identity_matches(ProcessIdentity.model_validate(p))
        for p in record["cancellation_processes"]
    )
    assert finish(service, [receipt["id"]])[0]["status"] == "cancelled"


def test_worker_command_timeout_and_queue_deadline_are_terminal(tmp_path, registry):
    service = study(tmp_path, registry, "import time\ntime.sleep(30)\n")
    receipt = service.run(
        "calc.py", outputs=["result.json"], machine="node-a", stage="exploration", timeout=0.5
    )
    result = finish(service, [receipt["id"]])[0]
    assert result["status"] == "timed_out", result
    assert result["execution"]["timed_out"]
    worker = Worker(registry.machine("node-a").root)
    # No detached process is needed to test expiry while awaiting resources.
    from conjecture_solver.worker_protocol import put

    job = "job_" + "c" * 40
    path = worker.directory(job)
    path.mkdir()
    put(
        path / "state.json",
        {
            "id": job,
            "status": "queued",
            "deadline": time.time() - 1,
            "resources": {"cpus": 1, "memory_mb": 1024, "gpus": 0},
        },
    )
    record, reserved = worker._reserve(job)
    assert record["status"] == "timed_out" and not reserved


def test_gpu_reservations_are_distinct_and_not_released_while_cancelling(tmp_path):
    from conjecture_solver.worker_protocol import WorkerConfig, private_put, put

    worker = Worker(tmp_path)
    private_put(
        tmp_path / "config.json",
        WorkerConfig(cpus=4, memory_mb=4096, max_jobs=3, gpu_ids=["0", "1"]).model_dump(),
    )
    for index in range(3):
        job = "job_" + str(index) * 40
        directory = worker.directory(job)
        directory.mkdir(parents=True)
        put(
            directory / "state.json",
            {
                "id": job,
                "status": "queued",
                "deadline": time.time() + 60,
                "resources": {"cpus": 1, "memory_mb": 1024, "gpus": 1},
            },
        )
    first, second, third = ("job_" + str(i) * 40 for i in range(3))
    assert worker._reserve(first)[0]["assigned_gpu_ids"] == ["0"]
    assert worker._reserve(second)[0]["assigned_gpu_ids"] == ["1"]
    assert not worker._reserve(third)[1]
    from conjecture_solver.mvp_launch import read_process_identity

    record = worker.status(first)
    record.update(
        status="cancelling",
        cancellation_reason="operator",
        cancellation_processes=[read_process_identity(os.getpid()).model_dump()],
    )
    put(worker.directory(first) / "state.json", record)
    assert not worker._reserve(third)[1]
    record.update(status="cancelled")
    put(worker.directory(first) / "state.json", record)
    assert worker._reserve(third)[0]["assigned_gpu_ids"] == ["0"]


def test_frozen_worker_identity_and_code_cannot_silently_change(tmp_path, registry):
    service = study(tmp_path, registry)
    worker = Worker(registry.machine("node-a").root)
    monkey_record = {
        "id": "exp_" + "d" * 24,
        "machine": "node-a",
        "binding": service._binding("calc.py", [], [], None),
        "outputs": ["result.json"],
        "timeout": 5,
        "workspace_limit_bytes": 1024**2,
        "resources": {"cpus": 1, "memory_mb": 1024, "gpus": 0},
    }
    from conjecture_solver.execution_pool import _specification

    spec = _specification(service, monkey_record)
    with pytest.raises(ValueError, match="identity differs"):
        worker.create(spec | {"worker_id": "0" * 32})
    with pytest.raises(ValueError, match="code changed"):
        worker.create(spec | {"worker_code_sha256": "0" * 64})
    link = worker.directory(spec["id"])
    link.symlink_to(tmp_path)
    with pytest.raises(ValueError, match="symlinks"):
        worker.create(spec)


def test_running_pool_blocks_routing_changes_but_allows_authentication_renewal(tmp_path, registry):
    service = study(tmp_path, registry)
    service._spawn_experiment = lambda record: None
    service.run("calc.py", outputs=["result.json"], machine="node-a", stage="exploration")
    machine = registry.machine("node-a").model_dump(mode="json")
    with pytest.raises(ValueError, match="Drain active studies"):
        registry.save(machine | {"root": str(tmp_path / "replacement")})
    registry.save(machine | {"password": "fixture-renewed-password"})
    assert registry.public("node-a")["has_password"]
    with pytest.raises(ValueError, match="pool is immutable"):
        ResearchService.create(service.root, service.manifest["hypothesis"], execution_pool={})


def test_read_only_instrument_source_is_bounded_and_traversal_is_rejected(tmp_path):
    from conjecture_solver.worker_protocol import WorkerConfig, private_put

    runtime = tmp_path / "runtime"
    (runtime / "bin").mkdir(parents=True)
    (runtime / "bin/python").write_text("#!/bin/sh\nexit 0\n")
    (runtime / "bin/python").chmod(0o755)
    (runtime / "source.F90").write_text("! source\n" * 100)
    caps = tmp_path / "capabilities"
    caps.mkdir()
    (caps / "example.json").write_text(
        json.dumps(
            {
                "manifest": {
                    "name": "example",
                    "version": "1",
                    "description": "fixture",
                    "skill": "python-tool",
                    "executable_kind": "python",
                },
                "runtime_root": str(runtime),
                "executable": "bin/python",
            }
        )
    )
    worker = Worker(tmp_path / "worker")
    private_put(worker.root / "config.json", WorkerConfig(capabilities=[str(caps)]).model_dump())
    content = worker.read_instrument("example", path="source.F90", max_bytes=16)
    assert len(content["content"].encode()) == 16 and content["truncated"]
    assert (runtime / "source.F90").read_text() == "! source\n" * 100
    with pytest.raises(ValueError, match="relative"):
        worker.read_instrument("example", path="../secret")
    with pytest.raises(ValueError, match="registered"):
        worker.read_instrument("example", root="/etc")


def test_process_identity_recovers_briefly_empty_cmdline(monkeypatch):
    import conjecture_solver.mvp_launch as launch

    original = launch._read_process_argv(os.getpid())
    replies = iter([None, None, original])
    monkeypatch.setattr(launch, "_read_process_argv", lambda pid: next(replies))
    assert launch.read_process_identity(os.getpid()).argv == original


def test_generated_agent_client_exposes_worker_controls_through_real_rpc(tmp_path, registry):
    import argparse
    import runpy

    from conjecture_solver.research_supervisor import ResearchSupervisor

    service = study(
        tmp_path,
        registry,
        "from pathlib import Path\nPath('array.bin').write_bytes(b'x'*500000)\n"
        "Path('result.json').write_text('{\"value\":4}')\n",
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Commission the selected pool and retain recorded results.")
    ResearchSupervisor(
        argparse.Namespace(
            campaign=service.root,
            state_dir=service.root / "supervisor",
            instructions_file=instructions,
            wall_seconds=120,
            turn_seconds=10,
            backend="codex-glm",
            executable="unused",
            model="unused",
            judge_model="unused",
        )
    )
    client = runpy.run_path(str(service.work / "lab.py"))["lab"]
    assert set(client.machines()) == {"node-a", "node-b"}
    receipt = client.run("calc.py", outputs=["result.json"], machine="node-b", stage="exploration")
    assert finish(service, [receipt["id"]])[0]["status"] == "succeeded"
    fetched = client.fetch_remote(experiment=receipt["id"], path="array.bin")
    assert checksum(fetched["path"]) == fetched["sha256"]
    with pytest.raises(RuntimeError, match="machine-scoped"):
        client.read_instrument("missing-alias")
    from conjecture_solver.study_status import status_line, study_status

    snapshot = study_status(service.root)
    assert snapshot["execution_backend"] == "worker-pool"
    snapshot["experiments"][0].update(status="running", transport_status="unreachable")
    line = status_line(snapshot)
    assert "workers node-b:1" in line and "SSH unreachable node-b" in line
