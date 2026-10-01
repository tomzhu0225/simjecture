"""Headless, durable job runner invoked through SSH JSON RPC or locally."""

import argparse
import base64
import os
import re
import subprocess
import sys
import time
import uuid
from contextlib import suppress
from pathlib import Path

from .worker_protocol import (
    ACTIVE,
    CHUNK_BYTES,
    PROTOCOL,
    TERMINAL,
    Experiment,
    WorkerConfig,
    checksum,
    contained,
    fingerprint,
    load,
    lock,
    private_put,
    put,
)


class Worker:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def configure(self, config):
        config = WorkerConfig.model_validate(config).model_dump(mode="json")
        with lock(self.root):
            old = load(self.root / "config.json")
            if old and old != config and any(r["status"] in ACTIVE for r in self.jobs()):
                raise ValueError("Drain active worker jobs before changing its configuration")
            (self.root / "jobs").mkdir(exist_ok=True)
            private_put(self.root / "config.json", config)
            if not (self.root / "identity.json").exists():
                private_put(self.root / "identity.json", {"worker_id": uuid.uuid4().hex})
        return self.probe()

    @property
    def config(self):
        saved = load(self.root / "config.json")
        if not saved:
            raise ValueError("Worker is not configured; prepare it first")
        return WorkerConfig.model_validate(saved)

    def registry(self):
        from .mvp_skills import MVPCapabilityRegistry

        installed = []
        for directory in self.config.capabilities:
            if not Path(directory).is_dir():
                raise ValueError("Worker capability directory is unavailable")
            registry = MVPCapabilityRegistry.discover(directory)
            installed.extend(registry.get(name) for name in registry.hashes)
        return MVPCapabilityRegistry(tuple(installed))

    def probe(self):
        import importlib.metadata
        import socket

        from .execution import probe_execution_backend

        registry = self.registry()
        execution = probe_execution_backend(self.config.execution_backend)
        devices = []
        if self.config.gpu_ids:
            inventory = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,uuid,name", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            devices = [
                dict(zip(("index", "uuid", "name"), line.split(", ", 2), strict=True))
                for line in inventory.stdout.splitlines()
                if line.strip()
            ]
            selected = [
                next((d["uuid"] for d in devices if identifier in (d["index"], d["uuid"])), None)
                for identifier in self.config.gpu_ids
            ]
            if None in selected or len(set(selected)) != len(selected):
                raise ValueError("Configured GPU IDs are unavailable or refer to the same device")
        readiness = None
        if execution["available"]:
            from .experiment_executor import execute_frozen

            health = self.root / "health"
            health.mkdir(parents=True, exist_ok=True)
            with lock(health):
                source = health / "worker_probe.py"
                source.write_text(
                    "from pathlib import Path\n"
                    "Path('worker_probe.json').write_text('{\"ready\":true}')\n"
                )
                binding = {
                    "source": source.name,
                    "args": [],
                    "inputs": {source.name: checksum(source)},
                    "capability": None,
                    "runtime_sha256": None,
                }
                readiness = execute_frozen(
                    health,
                    binding,
                    ["worker_probe.json"],
                    timeout=15,
                    execution_backend=self.config.execution_backend,
                    max_memory_bytes=min(self.config.memory_mb, 1024) * 1024**2,
                )
            if readiness["status"] != "succeeded":
                execution.update(
                    available=False, reason="Exact numerical launcher readiness failed"
                )
        return {
            "protocol": PROTOCOL,
            "worker_id": load(self.root / "identity.json")["worker_id"],
            "host": socket.gethostname(),
            "uid": os.geteuid(),
            "python": sys.version.split()[0],
            "simjecture": importlib.metadata.version("simjecture"),
            "worker_code_sha256": checksum(Path(__file__)),
            "config_sha256": fingerprint(self.config.model_dump(mode="json")),
            "execution": execution,
            "launcher_readiness": readiness,
            "clock": time.time(),
            "capacity": self.config.model_dump(mode="json"),
            "gpu_inventory": devices,
            "capabilities": {
                name: registry.get(name).descriptor()
                | {
                    "readable_roots": [
                        "runtime",
                        *[
                            destination
                            for _path, destination in registry.get(name).read_only_mounts
                        ],
                    ]
                }
                for name in registry.hashes
            },
        }

    def directory(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r"job_[a-f0-9]{40}", identifier):
            raise ValueError("Invalid worker job ID")
        return contained(self.root, "jobs/" + identifier)

    def jobs(self):
        return [load(p) for p in sorted((self.root / "jobs").glob("*/state.json"))]

    def create(self, specification):
        spec = Experiment.model_validate(specification)
        config = self.config
        if spec.config_sha256 != fingerprint(config.model_dump(mode="json")):
            raise ValueError("Worker configuration differs from the frozen study")
        if spec.worker_code_sha256 and checksum(Path(__file__)) != spec.worker_code_sha256:
            raise ValueError("Worker code changed since study preparation")
        if spec.worker_id and spec.worker_id != load(self.root / "identity.json").get("worker_id"):
            raise ValueError("Worker identity differs from the frozen study")
        if (
            spec.resources.cpus > config.cpus
            or spec.resources.memory_mb > config.memory_mb
            or spec.resources.gpus > len(config.gpu_ids)
        ):
            raise ValueError("Experiment exceeds this worker's capacity")
        path = self.directory(spec.id)
        body = spec.model_dump(mode="json")
        with lock(self.root):
            if self.config != config:
                raise ValueError("Worker configuration changed during submission")
            current = load(path / "state.json")
            if current:
                if current["status"] in TERMINAL and not current.get("request_sha256"):
                    return current
                if current["request_sha256"] != fingerprint(body):
                    raise ValueError("Job ID already binds a different request")
                return current
            if spec.deadline <= time.time():
                raise ValueError("Experiment deadline expired")
            if sum(r["status"] in ACTIVE for r in self.jobs()) >= 256:
                raise ValueError("Worker queue is full")
            (path / "workspace").mkdir(parents=True)
            put(path / "request.json", body)
            record = {
                "id": spec.id,
                "status": "staging",
                "created_at": time.time(),
                "request_sha256": fingerprint(body),
                "resources": spec.resources.model_dump(),
                "deadline": spec.deadline,
            }
            put(path / "state.json", record)
        return record

    def stage(self, identifier, name, offset, data, final=False):
        raw = base64.b64decode(data, validate=True)
        if len(raw) > CHUNK_BYTES or not isinstance(offset, int) or offset < 0:
            raise ValueError("Invalid bounded input chunk")
        directory = self.directory(identifier)
        spec = Experiment.model_validate(load(directory / "request.json"))
        if name not in spec.binding["inputs"]:
            raise ValueError("Input was not declared")
        with lock(self.root):
            state = load(directory / "state.json")
            destination = contained(directory / "workspace", name)
            expected = spec.binding["inputs"][name]
            if destination.is_file():
                if checksum(destination) != expected:
                    raise ValueError("Previously staged input changed")
                return {"offset": destination.stat().st_size, "complete": True}
            if state["status"] != "staging":
                raise ValueError("Job is no longer accepting inputs")
            destination.parent.mkdir(parents=True, exist_ok=True)
            partial = destination.with_name("." + destination.name + ".upload")
            size = partial.stat().st_size if partial.exists() else 0
            if offset < size:
                with partial.open("rb") as stream:
                    stream.seek(offset)
                    if stream.read(len(raw)) != raw:
                        raise ValueError("Replayed chunk differs")
            elif offset == size:
                used = sum(
                    p.stat().st_size
                    for p in (directory / "workspace").rglob("*")
                    if p.is_file() and not p.is_symlink()
                )
                if used + len(raw) > spec.workspace_bytes:
                    raise ValueError("Input upload exceeds workspace reservation")
                with partial.open("ab") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            else:
                raise ValueError("Input chunk skips data")
            if final:
                if checksum(partial) != expected:
                    raise ValueError("Staged input hash mismatch")
                partial.replace(destination)
            return {"offset": offset + len(raw), "complete": final}

    def submit(self, identifier):
        from .mvp_launch import read_process_identity

        directory = self.directory(identifier)
        with lock(self.root):
            record = load(directory / "state.json")
            if record["status"] != "staging":
                return record
            spec = Experiment.model_validate(load(directory / "request.json"))
            for name, digest in spec.binding["inputs"].items():
                if checksum(contained(directory / "workspace", name)) != digest:
                    raise ValueError("Inputs incomplete or changed")
            if spec.deadline <= time.time():
                record.update(status="timed_out", finished_at=time.time())
                put(directory / "state.json", record)
                return record
            record.update(status="queued", submitted_at=time.time())
            with (directory / "worker.log").open("a") as log:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "conjecture_solver.execution_worker",
                        "--root",
                        str(self.root),
                        "--execute",
                        identifier,
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
            identity = read_process_identity(child.pid, argv=child.args)
            record["process"] = identity.model_dump(mode="json") if identity else None
            put(directory / "state.json", record)
        return record

    def _reconcile_locked(self, records=None):
        from .mvp_launch import ProcessIdentity, process_identity_matches

        records = self.jobs() if records is None else records
        for record in records:
            if record["status"] not in ACTIVE:
                continue
            if record["status"] == "cancelling":
                if any(
                    process_identity_matches(ProcessIdentity.model_validate(p))
                    for p in record.get("cancellation_processes", [])
                ):
                    continue
                record.update(
                    status="timed_out"
                    if record["cancellation_reason"] == "deadline"
                    else "cancelled",
                    finished_at=time.time(),
                    cancellation_confirmed=True,
                )
            elif record["status"] == "staging" and time.time() >= record["deadline"]:
                record.update(status="timed_out", finished_at=time.time())
            elif record.get("process") and not process_identity_matches(
                ProcessIdentity.model_validate(record["process"])
            ):
                record.update(
                    status="interrupted",
                    finished_at=time.time(),
                    error="Worker process disappeared before its terminal receipt",
                )
            else:
                continue
            put(self.directory(record["id"]) / "state.json", record)
        return records

    def status(self, identifier=None):
        with lock(self.root):
            if identifier:
                record = load(self.directory(identifier) / "state.json")
                if not record:
                    return {"id": identifier, "status": "not_found"}
                # Individual polls and artifact chunks must not scan job history.
                self._reconcile_locked([record])
                return record
            jobs = self._reconcile_locked()
        visible = [r for r in jobs if r["status"] in ACTIVE] + [
            r for r in jobs if r["status"] not in ACTIVE
        ][-100:]
        return {
            "protocol": PROTOCOL,
            "total_jobs": len(jobs),
            "jobs": [
                {
                    key: r.get(key)
                    for key in (
                        "id",
                        "status",
                        "resources",
                        "assigned_gpu_ids",
                        "created_at",
                        "started_at",
                        "finished_at",
                        "deadline",
                    )
                }
                for r in visible
            ],
            "capacity": self.config.model_dump(mode="json"),
        }

    def heartbeat(self):
        """Cheap availability check; no numerical launch or instrument rehashing."""
        state = self.status()
        return {
            "protocol": PROTOCOL,
            "worker_id": load(self.root / "identity.json")["worker_id"],
            "clock": time.time(),
            "capacity": state["capacity"],
            "jobs": [r for r in state["jobs"] if r["status"] in ACTIVE],
        }

    def suggest_configuration(self):
        from .execution import probe_execution_backend
        from .machine_setup import hardware

        result = hardware()
        backend = probe_execution_backend("bubblewrap")
        if not backend["available"]:
            backend = probe_execution_backend("proot-cooperative")
        result["execution_backend"] = backend["backend"] if backend["available"] else None
        return result

    def _reserve(self, identifier):
        with lock(self.root):
            config = self.config
            jobs = self._reconcile_locked()
            path = self.directory(identifier)
            current = load(path / "state.json")
            if current["status"] != "queued":
                return current, False
            if time.time() >= current["deadline"]:
                current.update(status="timed_out", finished_at=time.time())
                put(path / "state.json", current)
                return current, False
            running = [r for r in jobs if r["status"] in {"running", "cancelling"}]
            used_gpus = {gpu for r in running for gpu in r.get("assigned_gpu_ids", [])}
            free_gpus = [gpu for gpu in config.gpu_ids if gpu not in used_gpus]
            resources = current["resources"]
            fits = (
                len(running) < config.max_jobs
                and sum(r["resources"]["cpus"] for r in running) + resources["cpus"] <= config.cpus
                and sum(r["resources"]["memory_mb"] for r in running) + resources["memory_mb"]
                <= config.memory_mb
                and len(free_gpus) >= resources["gpus"]
            )
            if not fits:
                return current, False
            current.update(
                status="running",
                started_at=time.time(),
                assigned_gpu_ids=free_gpus[: resources["gpus"]],
            )
            put(path / "state.json", current)
            return current, True

    def execute(self, identifier):
        from .experiment_executor import execute_frozen

        while True:
            record, reserved = self._reserve(identifier)
            if record["status"] in TERMINAL:
                return
            if reserved:
                break
            time.sleep(0.2)
        directory = self.directory(identifier)
        spec = Experiment.model_validate(load(directory / "request.json"))
        try:
            capability = spec.binding.get("worker_capability", spec.binding["capability"])
            registry = self.registry()
            cap_root = None
            if capability:
                runtime = registry.get(capability)
                # Use its original descriptor directory; identity paths remain worker-local.
                cap_root = next(
                    p
                    for p in self.config.capabilities
                    if capability
                    in __import__(
                        "conjecture_solver.mvp_skills", fromlist=["MVPCapabilityRegistry"]
                    ).MVPCapabilityRegistry.discover(p)
                )
                if runtime.contract_hash != spec.binding["runtime_sha256"]:
                    raise ValueError("Frozen worker capability changed")
            remaining = min(spec.timeout, spec.deadline - time.time())
            if remaining <= 0:
                record.update(status="timed_out")
            else:
                record.update(
                    execute_frozen(
                        directory / "workspace",
                        spec.binding,
                        spec.outputs,
                        timeout=remaining,
                        execution_backend=self.config.execution_backend,
                        capabilities=cap_root,
                        max_workspace_bytes=spec.workspace_bytes,
                        max_memory_bytes=spec.resources.memory_mb * 1024**2,
                        gpu_ids=record["assigned_gpu_ids"],
                        cpus=spec.resources.cpus,
                    )
                )
                if record.get("execution", {}).get("timed_out"):
                    record["status"] = "timed_out"
        except Exception as error:
            record.update(status="failed", error=str(error))
        record["finished_at"] = time.time()
        with lock(self.root):
            current = load(directory / "state.json")
            if current["status"] in {"cancelling", "cancelled", "timed_out"}:
                return
            put(directory / "state.json", record)

    def cancel(self, identifier, reason="operator"):
        import psutil

        from .mvp_launch import ProcessIdentity, process_identity_matches, read_process_identity

        if reason not in {"operator", "deadline"}:
            raise ValueError("Unknown cancellation reason")
        terminal = "timed_out" if reason == "deadline" else "cancelled"

        with lock(self.root):
            path = self.directory(identifier)
            record = load(path / "state.json")
            if not record:
                path.mkdir(parents=True, exist_ok=True)
                record = {"id": identifier, "status": terminal, "finished_at": time.time()}
                put(path / "state.json", record)
                return record
            if record["status"] in TERMINAL:
                return record
            identity = record.get("process")
            processes = []
            for saved in record.get("cancellation_processes", []):
                if process_identity_matches(ProcessIdentity.model_validate(saved)):
                    with suppress(psutil.NoSuchProcess):
                        processes.append(psutil.Process(saved["pid"]))
            if identity and process_identity_matches(ProcessIdentity.model_validate(identity)):
                with suppress(psutil.NoSuchProcess):
                    owner = psutil.Process(identity["pid"])
                    processes.extend([*owner.children(recursive=True), owner])
            record.update(
                status="cancelling",
                cancellation_reason=reason,
                cancellation_confirmed=False,
                cancellation_processes=[
                    p.model_dump(mode="json")
                    for child in processes
                    if (p := read_process_identity(child.pid)) is not None
                ],
            )
            put(path / "state.json", record)
            for process in processes:
                with suppress(psutil.NoSuchProcess):
                    process.terminate()
            _gone, alive = psutil.wait_procs(processes, timeout=3)
            for process in alive:
                with suppress(psutil.NoSuchProcess):
                    process.kill()
            psutil.wait_procs(alive, timeout=2)
            if not any(
                process_identity_matches(ProcessIdentity.model_validate(p))
                for p in record["cancellation_processes"]
            ):
                record.update(status=terminal, finished_at=time.time(), cancellation_confirmed=True)
            put(path / "state.json", record)
        return record

    def fetch(self, identifier, name, offset=0, length=CHUNK_BYTES):
        if not isinstance(offset, int) or offset < 0 or not 0 < length <= CHUNK_BYTES:
            raise ValueError("Invalid bounded artifact range")
        state = self.status(identifier)
        if state["status"] not in TERMINAL:
            raise ValueError("Fetch artifacts after the worker writes its terminal receipt")
        metadata = state.get("artifacts", {}).get(name)
        if not metadata:
            raise ValueError("Artifact was not recorded")
        path = contained(self.directory(identifier) / "workspace", name)
        if path.stat().st_size != metadata["bytes"]:
            raise ValueError("Remote artifact changed after recording")
        with path.open("rb") as stream:
            stream.seek(offset)
            raw = stream.read(length)
        return {
            "data": base64.b64encode(raw).decode(),
            "offset": offset,
            "sha256": metadata["sha256"],
            "bytes": metadata["bytes"],
        }

    def read_instrument(self, capability, root="runtime", path=".", max_bytes=16000):
        if not isinstance(max_bytes, int) or not 0 < max_bytes <= 65536:
            raise ValueError("Use a bounded source excerpt")
        installed = self.registry().get(capability)
        installed.assert_runtime_identity()
        roots = {"runtime": installed.runtime_root} | {
            destination: source for source, destination in installed.read_only_mounts
        }
        if root not in roots:
            raise ValueError("Read only registered instrument roots")
        target = roots[root] if path == "." else contained(roots[root], path)
        if target.is_dir():
            return {
                "entries": [
                    {"name": p.name, "directory": p.is_dir()}
                    for p in sorted(target.iterdir())[:100]
                    if not p.is_symlink()
                ]
            }
        if not target.is_file():
            raise ValueError("Instrument file not found")
        with target.open("rb") as stream:
            text = stream.read(max_bytes).decode("utf-8")
        return {"content": text, "truncated": target.stat().st_size > max_bytes}

    def call(self, request):
        if request.get("protocol") != PROTOCOL:
            raise ValueError("Unsupported worker protocol")
        methods = {
            "configure",
            "probe",
            "create",
            "stage",
            "submit",
            "status",
            "heartbeat",
            "suggest_configuration",
            "cancel",
            "fetch",
            "read_instrument",
        }
        method = request.get("method")
        if method not in methods:
            raise ValueError("Unknown execution worker method")
        return getattr(self, method)(**request.get("arguments", {}))


def main():
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execute")
    args = parser.parse_args()
    worker = Worker(args.root)
    if args.execute:
        worker.execute(args.execute)
        return
    try:
        raw = sys.stdin.buffer.read(2 * CHUNK_BYTES + 1)
        if len(raw) > 2 * CHUNK_BYTES:
            raise ValueError("Worker RPC exceeds the message limit")
        result = worker.call(json.loads(raw))
        print(json.dumps({"ok": True, "result": result}, allow_nan=False))
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
