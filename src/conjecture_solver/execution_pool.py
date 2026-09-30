"""Local/SSH machine registry and durable experiment transport."""

import base64
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

from .worker_protocol import (
    ACTIVE,
    CHUNK_BYTES,
    PROTOCOL,
    TERMINAL,
    Experiment,
    Machine,
    Resources,
    checksum,
    contained,
    fingerprint,
    load,
    lock,
    private_put,
    put,
)


class WorkerUnavailable(RuntimeError):
    """Transport uncertainty does not establish experiment failure."""


def profile_identity(profile):
    return {
        key: value
        for key, value in profile.items()
        if key not in {"identity_file", "control_path", "known_hosts"}
    }


class Transport:
    def __init__(self, machine, password=None):
        self.machine = Machine.model_validate(machine)
        self.password = password

    def command(self, argv, *, login_user=False):
        if self.machine.run_as and not login_user:
            argv = ["runuser", "-u", self.machine.run_as, "--", *argv]
        if self.machine.kind == "local":
            return argv
        binary = shutil.which("ssh")
        if not binary:
            raise ValueError("Install the OpenSSH client to connect execution workers")
        arguments = [
            binary,
            "-T",
            "-p",
            str(self.machine.port),
            "-o",
            "ConnectTimeout=5",
            "-o",
            "StrictHostKeyChecking=accept-new"
            if self.machine.automatic_setup
            else "StrictHostKeyChecking=yes",
            "-o",
            "ServerAliveInterval=10",
            "-o",
            "ServerAliveCountMax=2",
            "-o",
            "LogLevel=ERROR",
        ]
        if self.machine.user:
            arguments += ["-l", self.machine.user]
        if self.machine.identity_file:
            arguments += [
                "-i",
                str(Path(self.machine.identity_file).expanduser()),
                "-o",
                "IdentitiesOnly=yes",
            ]
        if self.machine.known_hosts:
            arguments += ["-o", f"UserKnownHostsFile={self.machine.known_hosts}"]
        control_path = self.machine.control_path
        if not control_path:
            sockets = Path(tempfile.gettempdir()) / f"simjecture-ssh-{os.getuid()}"
            sockets.mkdir(mode=0o700, exist_ok=True)
            if sockets.is_symlink() or sockets.stat().st_uid != os.getuid():
                raise ValueError("SSH socket directory must belong to the coordinator user")
            sockets.chmod(0o700)
            control_path = str(
                sockets
                / fingerprint(
                    {
                        key: getattr(self.machine, key)
                        for key in ("host", "port", "user", "identity_file", "known_hosts")
                    }
                )[:32]
            )
            arguments += ["-o", "ControlMaster=auto", "-o", "ControlPersist=60"]
        arguments += ["-S", control_path]
        arguments += [
            "-o",
            "BatchMode=no" if self.password else "BatchMode=yes",
            self.machine.host,
            shlex.join(argv),
        ]
        return arguments

    def run(self, argv, payload, *, timeout=20, login_user=False):
        env = dict(os.environ)
        askpass_directory = None
        if self.password:
            askpass_directory = tempfile.TemporaryDirectory(prefix="simjecture-ssh-askpass-")
            askpass = Path(askpass_directory.name) / "askpass.sh"
            askpass.write_text(
                "#!/bin/sh\nexec "
                + shlex.join([sys.executable, str(Path(__file__).with_name("ssh_askpass.py"))])
                + ' "$@"\n'
            )
            askpass.chmod(0o700)
            env.update(
                SIMJECTURE_SSH_PASSWORD=self.password,
                SSH_ASKPASS=str(askpass),
                SSH_ASKPASS_REQUIRE="force",
                DISPLAY="simjecture-worker",
            )
        try:
            result = subprocess.run(
                self.command(argv, login_user=login_user),
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                start_new_session=True,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise WorkerUnavailable(f"Worker {self.machine.id} did not respond") from error
        finally:
            if askpass_directory:
                askpass_directory.cleanup()
        try:
            envelope = json.loads(result.stdout)
            if not isinstance(envelope, dict):
                raise ValueError("Invalid worker envelope")
        except ValueError as error:
            # Bound diagnostics; OpenSSH errors contain no password arguments.
            detail = (
                result.stderr[-1000:].replace(self.password, "[redacted]")
                if self.password
                else result.stderr[-1000:]
            )
            detail = detail or f"invalid response (exit {result.returncode})"
            raise WorkerUnavailable(f"Worker {self.machine.id}: {detail}") from error
        if not envelope.get("ok"):
            raise ValueError(envelope.get("error", "Worker rejected the request"))
        return envelope["result"]

    def call(self, method, *, timeout=20, **arguments):
        return self.run(
            [
                self.machine.python,
                "-m",
                "conjecture_solver.execution_worker",
                "--root",
                self.machine.root,
            ],
            {"protocol": PROTOCOL, "method": method, "arguments": arguments},
            timeout=timeout,
        )


HOST_SETUP = r"""
import json, os, pathlib, pwd, shutil, subprocess, sys
request = json.load(sys.stdin)
user = request.get("run_as")
if user:
    if os.geteuid() != 0:
        raise ValueError("Run-as provisioning requires a root SSH login")
    try: account = pwd.getpwnam(user)
    except KeyError:
        subprocess.run(["useradd","--system","--create-home","--home-dir","/var/lib/"+user,
                        "--shell","/usr/sbin/nologin",user], check=True,
                       stdout=sys.stderr, stderr=sys.stderr)
        account = pwd.getpwnam(user)
    root = pathlib.Path(request["root"])
    root.mkdir(parents=True,exist_ok=True)
    os.chown(root,account.pw_uid,account.pw_gid)
needed = "proot" if request["backend"] == "proot-cooperative" else "bwrap"
if not shutil.which(needed):
    if os.geteuid() != 0 or not shutil.which("apt-get"):
        raise ValueError("Install "+needed+" before preparing this worker")
    subprocess.run(["apt-get","update"],check=True,stdout=sys.stderr,stderr=sys.stderr)
    subprocess.run(["apt-get","install","-y","proot" if needed=="proot" else "bubblewrap"],
                   check=True,stdout=sys.stderr,stderr=sys.stderr)
print(json.dumps({"ok":True,"result":{"ready":True}}))
"""

BOOTSTRAP = r"""
import base64, hashlib, io, json, os, pathlib, shutil, subprocess, sys, urllib.request, zipfile
request = json.load(sys.stdin)
root = pathlib.Path(request["root"])
root.mkdir(parents=True,exist_ok=True)
os.chdir(root)
bundle = base64.b64decode(request["source"])
digest = hashlib.sha256(bundle).hexdigest()
program = root / "programs" / digest
program.mkdir(parents=True, exist_ok=True)
source = program / "source"
source.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
    for entry in archive.infolist():
        path = pathlib.Path(entry.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe worker source bundle")
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.read(entry))
        if path.name == "ssh_askpass.py": target.chmod(0o755)
venv = program / "venv"
python = venv / "bin/python"
if not (program / "install-complete").exists():
    uv = shutil.which("uv")
    if not uv and (root / "bootstrap/bin/uv").is_file():
        uv = str(root / "bootstrap/bin/uv")
    if not uv:
        bootstrap = root / "bootstrap"
        bootstrap.mkdir(exist_ok=True)
        installer = bootstrap / "uv-install.sh"
        if shutil.which("curl"):
            subprocess.run(["curl","--fail","--location","--silent","--show-error",
                            "--retry","3","--connect-timeout","20","--max-time","120",
                            "--output",str(installer),"https://astral.sh/uv/install.sh"],
                           check=True,stdout=sys.stderr,stderr=sys.stderr)
        else:
            download = urllib.request.Request("https://astral.sh/uv/install.sh",
                                               headers={"User-Agent":"simjecture-worker"})
            with urllib.request.urlopen(download,timeout=60) as response:
                installer.write_bytes(response.read())
        environment = dict(os.environ, UV_INSTALL_DIR=str(bootstrap / "bin"), UV_NO_MODIFY_PATH="1")
        subprocess.run(["sh",str(installer)],env=environment,check=True,
                       stdout=sys.stderr,stderr=sys.stderr)
        uv = str(bootstrap / "bin/uv")
    environment = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(root / "python"),
                       UV_CACHE_DIR=str(root / "cache"), UV_NO_CONFIG="1")
    if not python.exists():
        subprocess.run([uv,"venv","--python","3.12","--python-preference","only-managed",str(venv)],
                       env=environment,check=True,stdout=sys.stderr,stderr=sys.stderr)
    subprocess.run([uv,"pip","install","--python",str(python),
                    "simjecture[process,flash-demo]==0.5.3rc1"],env=environment,
                   check=True,stdout=sys.stderr,stderr=sys.stderr)
    subprocess.run([str(python), "-c",
      "import sysconfig,pathlib; pathlib.Path(sysconfig.get_paths()['purelib'],"
      "'simjecture-worker-source.pth').write_text("
      + repr("import sys; sys.path.insert(0, " + repr(str(source)) + ")\n") + ")"], check=True)
    subprocess.run([str(python),"-c","import numpy,h5py,psutil,pydantic"],check=True)
    (program / "install-complete").write_text(digest)
print(json.dumps({"ok":True,"result":{"python":str(python),"source_sha256":digest}}))
"""


class MachineRegistry:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()

    def path(self, identifier):
        if not isinstance(identifier, str) or not __import__("re").fullmatch(
            r"[a-z][a-z0-9-]{0,39}", identifier
        ):
            raise ValueError("Invalid machine ID")
        return self.root / "profiles" / f"{identifier}.json"

    def machine(self, identifier):
        value = load(self.path(identifier))
        if not value:
            raise ValueError("Unknown execution machine")
        return Machine.model_validate(value["machine"])

    def transport(self, identifier, *, frozen=None):
        machine = self.machine(identifier)
        if frozen:
            current = machine.model_dump(mode="json")
            routing = ("id", "kind", "host", "port", "user", "root", "run_as")
            if any(current[key] != frozen["profile"][key] for key in routing):
                raise ValueError("Execution machine routing changed; create a new study")
            # Keep the original program/config while allowing credential/socket renewal.
            machine = Machine.model_validate(
                frozen["profile"]
                | {key: current[key] for key in ("identity_file", "control_path", "known_hosts")}
            )
        secret = load(self.root / ".private" / f"{identifier}.json").get("password")
        return Transport(machine.model_dump(mode="json"), secret)

    def save(self, payload):
        # Passwords never enter public profiles, worker specs, study manifests or exports.
        payload = dict(payload)
        password = payload.pop("password", None)
        machine = Machine.model_validate(payload)
        with lock(self.root):
            if machine.kind == "ssh" and machine.automatic_setup and not machine.known_hosts:
                key_file = contained(self.root, ".private/known_hosts")
                key_file.parent.mkdir(mode=0o700, exist_ok=True)
                key_file.touch(mode=0o600, exist_ok=True)
                machine.known_hosts = str(key_file)
            old = load(self.path(machine.id))
            value = machine.model_dump(mode="json")
            routing = ("kind", "host", "port", "user", "root", "run_as")
            if old and any(old["machine"][key] != value[key] for key in routing):
                for entry in load(self.root / "allocations.json").values():
                    if entry["machine"] == machine.id and (
                        load(entry["receipt"]).get("status") in {"queued", "running"}
                        or (
                            not Path(entry["receipt"]).exists()
                            and time.time() - entry["created_at"] < 60
                        )
                    ):
                        raise ValueError("Drain active studies before changing machine routing")
            private_put(
                self.path(machine.id),
                {
                    "machine": value,
                    "probe": old.get("probe")
                    if old
                    and Machine.model_validate(old["machine"]).model_dump(mode="json") == value
                    else None,
                    **{key: old[key] for key in ("hardware", "availability") if key in old},
                },
            )
            if password is not None:
                private_put(self.root / ".private" / f"{machine.id}.json", {"password": password})
        return self.public(machine.id)

    def public(self, identifier):
        record = load(self.path(identifier))
        secret = load(self.root / ".private" / f"{identifier}.json")
        preparation = load(self.root / "preparation" / identifier / "state.json")
        if preparation.get("status") == "working" and preparation.get("process"):
            from .mvp_launch import ProcessIdentity, process_identity_matches

            if not process_identity_matches(ProcessIdentity.model_validate(preparation["process"])):
                preparation.update(status="failed", error="Worker preparation process interrupted")
        log = self.root / "preparation" / identifier / "prepare.log"
        if log.is_file():
            with log.open("rb") as stream:
                stream.seek(max(0, log.stat().st_size - 4000))
                preparation["log"] = stream.read().decode(errors="replace")
        return record | {"has_password": bool(secret.get("password")), "preparation": preparation}

    def catalogue(self):
        return [self.public(p.stem) for p in sorted((self.root / "profiles").glob("*.json"))]

    def check(self, identifier):
        transport = self.transport(identifier)
        started = time.monotonic()
        try:
            result = transport.call("probe", timeout=60)
        except (WorkerUnavailable, ValueError) as error:
            with lock(self.root):
                path = self.path(identifier)
                record = load(path)
                record.update(error=str(error), checked_at=time.time())
                private_put(path, record)
            raise
        if result.get("protocol") != PROTOCOL:
            raise ValueError("Worker protocol is incompatible")
        if abs(result["clock"] - time.time()) > 30:
            raise ValueError("Worker clock differs by more than 30 seconds; synchronize it first")
        if not result["execution"]["available"]:
            raise ValueError(result["execution"]["reason"])
        if result["capacity"] != transport.machine.config.model_dump(mode="json"):
            raise ValueError("Worker configuration differs; prepare the selected profile first")
        path = self.path(identifier)
        with lock(self.root):
            record = load(path)
            if Machine.model_validate(record["machine"]).model_dump(
                mode="json"
            ) != transport.machine.model_dump(mode="json"):
                raise ValueError("Machine profile changed during readiness check; check again")
            record.update(probe=result, checked_at=time.time(), error=None)
            record["availability"] = {
                "online": True,
                "status": "ready",
                "checked_at": time.time(),
                "latency_ms": round((time.monotonic() - started) * 1000),
            }
            private_put(path, record)
        return self.public(identifier)

    def prepare(self, identifier):
        self._preparation_phase(identifier, "Connecting and inspecting the host")
        transport = self.transport(identifier)
        if transport.machine.kind == "ssh" and transport.machine.automatic_setup:
            from .machine_setup import DISCOVER

            detected = transport.run(["python3", "-c", DISCOVER], {}, login_user=True)
            options = transport.machine.automatic_setup
            profile = transport.machine.model_dump(mode="json")
            profile["run_as"] = options.run_as or ("simjecture" if detected["uid"] == 0 else None)
            profile["root"] = options.root or (
                f"/var/lib/simjecture/workers/{identifier}"
                if detected["uid"] == 0
                else str(Path(detected["home"]) / ".local/share/simjecture/workers" / identifier)
            )
            self.save(profile)
            transport = self.transport(identifier)
        if transport.machine.kind == "ssh":
            transport.run(
                ["python3", "-c", HOST_SETUP],
                {
                    "root": transport.machine.root,
                    "run_as": transport.machine.run_as,
                    "backend": transport.machine.config.execution_backend,
                },
                timeout=600,
                login_user=True,
            )
            source = io.BytesIO()
            with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(Path(__file__).parent.rglob("*.py")):
                    if "__pycache__" not in path.parts and "builtin_skills" not in path.parts:
                        entry = zipfile.ZipInfo(
                            "conjecture_solver/" + str(path.relative_to(Path(__file__).parent))
                        )
                        entry.compress_type = zipfile.ZIP_DEFLATED
                        archive.writestr(entry, path.read_bytes())
            self._preparation_phase(identifier, "Preparing the private Python environment")
            installed = transport.run(
                ["python3", "-c", BOOTSTRAP],
                {
                    "root": transport.machine.root,
                    "source": base64.b64encode(source.getvalue()).decode(),
                },
                timeout=600,
            )
            machine = transport.machine.model_dump(mode="json") | {"python": installed["python"]}
            self.save(machine)
            transport = self.transport(identifier)
            if transport.machine.automatic_setup:
                from .machine_setup import INSTALL_BACKEND

                self._preparation_phase(identifier, "Detecting hardware and execution environment")
                suggested = transport.call("suggest_configuration", timeout=15)
                options = transport.machine.automatic_setup
                config = transport.machine.config.model_dump(mode="json")
                for key in ("cpus", "memory_mb", "max_jobs", "gpu_ids"):
                    config[key] = (
                        getattr(options, key)
                        if getattr(options, key) is not None
                        else suggested[key]
                    )
                config["capabilities"] = options.capabilities
                config["execution_backend"] = (
                    options.execution_backend
                    if options.execution_backend != "auto"
                    else suggested.get("execution_backend") or "proot-cooperative"
                )
                transport.run(
                    ["python3", "-c", INSTALL_BACKEND],
                    {"backend": config["execution_backend"]},
                    timeout=600,
                    login_user=True,
                )
                machine = transport.machine.model_dump(mode="json") | {"config": config}
                self.save(machine)
                with lock(self.root):
                    path = self.path(identifier)
                    record = load(path)
                    record["hardware"] = suggested["hardware"]
                    private_put(path, record)
                transport = self.transport(identifier)
        self._preparation_phase(identifier, "Verifying the experiment launcher")
        transport.call(
            "configure", timeout=60, config=transport.machine.config.model_dump(mode="json")
        )
        return self.check(identifier)

    def _preparation_phase(self, identifier, message):
        with lock(self.root):
            path = self.root / "preparation" / identifier / "state.json"
            state = load(path)
            if state.get("status") == "working":
                state.update(phase=message, updated_at=time.time())
                private_put(path, state)

    def freeze(self, identifiers):
        if not identifiers or len(set(identifiers)) != len(identifiers):
            raise ValueError("Choose distinct execution machines")
        workers, capabilities = {}, {}
        for identifier in identifiers:
            record = self.check(identifier)
            profile, probe = record["machine"], record["probe"]
            workers[identifier] = {
                "profile": profile,
                "profile_sha256": fingerprint(profile_identity(profile)),
                "probe": probe,
            }
            for name, descriptor in probe["capabilities"].items():
                alias = f"{name}--at-{identifier}"
                capabilities[alias] = {
                    "machine": identifier,
                    "worker_capability": name,
                    "runtime_sha256": descriptor["contract_sha256"],
                    "descriptor": descriptor,
                }
        return {
            "protocol": PROTOCOL,
            "registry": str(self.root),
            "workers": workers,
            "capabilities": capabilities,
        }

    def worker_status(self, identifier):
        return self.transport(identifier).call("status", timeout=10)

    def start_prepare(self, identifier):
        from .mvp_launch import ProcessIdentity, process_identity_matches, read_process_identity

        self.machine(identifier)
        directory = self.root / "preparation" / identifier
        with lock(self.root):
            current = load(directory / "state.json")
            if current.get("process") and process_identity_matches(
                ProcessIdentity.model_validate(current["process"])
            ):
                return {"message": "Worker preparation is already running"}
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            with (directory / "prepare.log").open("w") as log:
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "conjecture_solver.execution_pool",
                        "--registry",
                        str(self.root),
                        "prepare-job",
                        identifier,
                    ],
                    stdout=log,
                    stderr=log,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])),
                )
            process = read_process_identity(child.pid)
            private_put(
                directory / "state.json",
                {
                    "status": "working",
                    "process": process.model_dump(mode="json") if process else None,
                },
            )
        return {"message": "Worker preparation started"}

    def prepare_job(self, identifier):
        directory = self.root / "preparation" / identifier
        try:
            self.prepare(identifier)
            state = {"status": "ready", "finished_at": time.time()}
        except Exception as error:
            state = {"status": "failed", "error": str(error), "finished_at": time.time()}
        with lock(self.root):
            current = load(directory / "state.json")
            private_put(directory / "state.json", current | state)
        return state


def select_worker(
    pool, capability, requested, resources, *, reservation=None, receipt=None, deadline=None
):
    resources = Resources.model_validate(resources or {})
    if capability in pool["capabilities"]:
        chosen = pool["capabilities"][capability]["machine"]
        if requested and requested != chosen:
            raise ValueError("Capability is qualified on a different worker")
        candidates = [chosen]
    elif capability:
        raise ValueError("Use the advertised, machine-scoped capability alias")
    else:
        candidates = [requested] if requested else list(pool["workers"])
    eligible = []
    registry = MachineRegistry(pool["registry"])
    book = load(registry.root / "allocations.json")
    for identifier in candidates:
        if identifier not in pool["workers"]:
            raise ValueError("Machine is outside this study's frozen pool")
        config = pool["workers"][identifier]["profile"]["config"]
        if (
            resources.cpus > config["cpus"]
            or resources.memory_mb > config["memory_mb"]
            or resources.gpus > len(config["gpu_ids"])
        ):
            continue
        try:
            jobs = registry.transport(identifier, frozen=pool["workers"][identifier]).call(
                "status", timeout=5
            )["jobs"]
            pressure = sum(r["status"] in ACTIVE for r in jobs)
            remote_ids = {r["id"] for r in jobs if r["status"] in ACTIVE}
            for job, entry in book.items():
                if (
                    entry["machine"] != identifier
                    or job in remote_ids
                    or entry["deadline"] <= time.time()
                ):
                    continue
                state = load(entry["receipt"])
                if state.get("status") in {"queued", "running"} or (
                    not state and time.time() - entry["created_at"] < 60
                ):
                    pressure += 1
        except WorkerUnavailable:
            pressure = 1_000_000
        eligible.append((pressure, identifier))
    if not eligible:
        raise ValueError("No selected worker can satisfy the requested resources")
    selected = min(eligible)[1]
    if reservation:
        book[reservation] = {
            "machine": selected,
            "receipt": str(receipt),
            "deadline": deadline,
            "created_at": time.time(),
        }
        private_put(registry.root / "allocations.json", book)
    return selected, resources.model_dump(mode="json")


def reserve_worker(pool, capability, requested, resources, *, reservation, receipt, deadline):
    with lock(pool["registry"]):
        return select_worker(
            pool,
            capability,
            requested,
            resources,
            reservation=reservation,
            receipt=receipt,
            deadline=deadline,
        )


def job_identifier(service, record):
    return (
        "job_"
        + fingerprint(
            {
                "study": service.manifest.get("study_id", str(service.root)),
                "experiment": record["id"],
            }
        )[:40]
    )


def _specification(service, record):
    pool = service.manifest["execution_pool"]
    machine = record["machine"]
    probe = pool["workers"][machine]["probe"]
    return Experiment(
        id=job_identifier(service, record),
        binding=record["binding"],
        outputs=record["outputs"],
        deadline=service.manifest["deadline"],
        timeout=record["timeout"],
        workspace_bytes=record["workspace_limit_bytes"],
        resources=record["resources"],
        config_sha256=probe["config_sha256"],
        worker_code_sha256=probe["worker_code_sha256"],
        worker_id=probe["worker_id"],
    ).model_dump(mode="json")


def save_progress(service, record, **values):
    if values.get("started_at", "missing") is None:
        values.pop("started_at")
    with service.lock():
        current = service._read("experiments", record["id"])
        if current["status"] in TERMINAL:
            return current
        current.update(values)
        put(service.root / "experiments" / (record["id"] + ".json"), current)
    return current


def download(transport, job, name, metadata, destination):
    destination = Path(destination)
    if destination.is_file() and checksum(destination) == metadata["sha256"]:
        return
    if destination.is_symlink():
        raise ValueError("Artifact destination is linked")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name("." + destination.name + "." + uuid.uuid4().hex)
    try:
        with temporary.open("wb") as output:
            while output.tell() < metadata["bytes"]:
                chunk = transport.call(
                    "fetch", identifier=job, name=name, offset=output.tell(), length=CHUNK_BYTES
                )
                if (
                    chunk["sha256"] != metadata["sha256"]
                    or chunk["bytes"] != metadata["bytes"]
                    or chunk["offset"] != output.tell()
                ):
                    raise ValueError("Artifact identity changed during retrieval")
                raw = base64.b64decode(chunk["data"], validate=True)
                if (
                    not raw
                    or len(raw) > CHUNK_BYTES
                    or output.tell() + len(raw) > metadata["bytes"]
                ):
                    raise ValueError("Invalid artifact chunk")
                output.write(raw)
        if checksum(temporary) != metadata["sha256"]:
            raise ValueError("Retrieved artifact SHA256 mismatch")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def import_result(service, record, transport, remote):
    workspace = service.root / "experiments" / record["id"] / "workspace"
    artifacts = remote.get("artifacts", {})
    selected = set(record["outputs"]) | set(record["binding"]["inputs"])
    # Small diagnostic files remain convenient; large undeclared arrays stay worker-local.
    selected |= {
        name
        for name, meta in artifacts.items()
        if meta["bytes"] <= 262144 and Path(name).suffix in {".json", ".txt", ".md", ".log", ".csv"}
    }
    transferred = {}
    if (
        sum(artifacts[name]["bytes"] for name in selected if name in artifacts)
        > record["workspace_limit_bytes"]
    ):
        raise ValueError("Imported artifacts exceed the coordinator storage reservation")
    for name in sorted(selected):
        if name in artifacts:
            download(transport, remote["id"], name, artifacts[name], contained(workspace, name))
            transferred[name] = artifacts[name]
    result = {
        key: remote[key]
        for key in (
            "status",
            "execution",
            "missing_outputs",
            "input_mutations",
            "output_findings",
            "scientific_status",
            "error",
            "started_at",
            "finished_at",
            "assigned_gpu_ids",
            "cancellation_confirmed",
            "cancellation_reason",
        )
        if key in remote
    }
    result.update(
        artifacts=transferred,
        remote_artifacts=artifacts,
        remote_job=remote["id"],
        transport_status="connected",
    )
    return save_progress(service, record, **result)


def dispatch(service, record):
    pool = service.manifest["execution_pool"]
    transport = MachineRegistry(pool["registry"]).transport(
        record["machine"], frozen=pool["workers"][record["machine"]]
    )
    spec = _specification(service, record)
    workspace = service.root / "experiments" / record["id"] / "workspace"
    job = spec["id"]
    while True:
        current = service._read("experiments", record["id"])
        if current["status"] in TERMINAL:
            return
        # A restored key/password/control socket can recover an existing job.
        transport = MachineRegistry(pool["registry"]).transport(
            record["machine"], frozen=pool["workers"][record["machine"]]
        )
        try:
            state = transport.call("status", identifier=job)
            if state["status"] == "not_found":
                if time.time() >= service.manifest["deadline"]:
                    save_progress(service, record, status="timed_out", finished_at=time.time())
                    return
                state = transport.call("create", specification=spec)
            if state.get("request_sha256") and state["request_sha256"] != fingerprint(spec):
                raise ValueError("Worker job receipt binds a different experiment request")
            if current.get("cancel_requested") and state["status"] in ACTIVE:
                state = transport.call("cancel", identifier=job)
            if state["status"] == "staging":
                for name in spec["binding"]["inputs"]:
                    path = contained(workspace, name)
                    with path.open("rb") as stream:
                        offset = 0
                        while True:
                            raw = stream.read(CHUNK_BYTES)
                            final = stream.tell() == path.stat().st_size
                            transport.call(
                                "stage",
                                identifier=job,
                                name=name,
                                offset=offset,
                                data=base64.b64encode(raw).decode(),
                                final=final,
                            )
                            offset += len(raw)
                            if final:
                                break
                state = transport.call("submit", identifier=job)
            if time.time() >= service.manifest["deadline"] and state["status"] in ACTIVE:
                state = transport.call("cancel", identifier=job, reason="deadline")
            if state["status"] in TERMINAL:
                import_result(service, record, transport, state)
                return
            save_progress(
                service,
                record,
                status="queued"
                if state["status"] == "staging"
                else "running"
                if state["status"] == "cancelling"
                else state["status"],
                remote_job=job,
                transport_status="connected",
                started_at=state.get("started_at"),
                assigned_gpu_ids=state.get("assigned_gpu_ids", []),
            )
        except WorkerUnavailable as error:
            save_progress(
                service, record, transport_status="unreachable", transport_error=str(error)
            )
            if time.time() >= service.manifest["deadline"]:
                # Worker enforces the same absolute deadline; do not claim a confirmed stop.
                save_progress(
                    service,
                    record,
                    status="timed_out",
                    finished_at=time.time(),
                    cancellation_confirmed=False,
                )
                return
        time.sleep(1)


def cancel_remote(service, record):
    pool = service.manifest["execution_pool"]
    try:
        transport = MachineRegistry(pool["registry"]).transport(
            record["machine"], frozen=pool["workers"][record["machine"]]
        )
        state = transport.call("cancel", identifier=job_identifier(service, record))
        return save_progress(
            service,
            record,
            status="running" if state["status"] == "cancelling" else state["status"],
            **(
                {"finished_at": state.get("finished_at", time.time())}
                if state["status"] in TERMINAL
                else {}
            ),
            cancel_requested=True,
            cancellation_confirmed=state["status"] in TERMINAL,
        )
    except WorkerUnavailable as error:
        return save_progress(
            service,
            record,
            cancel_requested=True,
            transport_status="unreachable",
            transport_error=str(error),
            cancellation_confirmed=False,
        )


def configure_parser(parser):
    parser.add_argument("--registry", type=Path, required=True)
    commands = parser.add_subparsers(dest="machine_action", required=True)
    commands.add_parser("list")
    add = commands.add_parser("add")
    add.add_argument("--file", type=Path, required=True)
    for action in ("prepare", "check", "status", "prepare-job"):
        commands.add_parser(action).add_argument("id")
    parser.set_defaults(handler=cli)


def cli(args):
    registry = MachineRegistry(args.registry)
    try:
        action = args.machine_action
        if action == "list":
            result = registry.catalogue()
        elif action == "add":
            result = registry.save(json.loads(args.file.read_text()))
        elif action == "status":
            result = registry.worker_status(args.id)
        elif action == "prepare-job":
            result = registry.prepare_job(args.id)
        else:
            result = getattr(registry, action)(args.id)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, WorkerUnavailable) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    configure_parser(parser)
    raise SystemExit(cli(parser.parse_args()))
