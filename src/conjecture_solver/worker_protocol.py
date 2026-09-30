"""Versioned execution requests. Scientific state belongs to the coordinator."""

import contextlib
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROTOCOL = "simjecture-worker/1"
ACTIVE = {"staging", "queued", "running", "cancelling"}
TERMINAL = {"succeeded", "failed", "cancelled", "timed_out", "interrupted"}
CHUNK_BYTES = 1024 * 1024


class Resources(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cpus: int = Field(default=1, ge=1, le=65536)
    memory_mb: int = Field(default=1024, ge=128, le=16 * 1024**2)
    gpus: int = Field(default=0, ge=0, le=256)


class WorkerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    execution_backend: Literal["bubblewrap", "proot-cooperative"] = "bubblewrap"
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    cpus: int = Field(default=2, ge=1, le=65536)
    memory_mb: int = Field(default=4096, ge=128, le=16 * 1024**2)
    gpu_ids: list[str] = Field(default_factory=list, max_length=256)
    max_jobs: int = Field(default=2, ge=1, le=256)

    @model_validator(mode="after")
    def valid_paths_devices(self):
        if any(not Path(p).is_absolute() or ".." in Path(p).parts for p in self.capabilities):
            raise ValueError("Worker capability directories must be absolute")
        if len(set(self.gpu_ids)) != len(self.gpu_ids) or any(
            not re.fullmatch(r"[0-9]+|GPU-[a-zA-Z0-9-]+", s) for s in self.gpu_ids
        ):
            raise ValueError("GPU IDs must be distinct indices or GPU UUIDs")
        return self


class Machine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{0,39}$")
    label: str = Field(default="", max_length=160)
    kind: Literal["local", "ssh"] = "ssh"
    host: str = Field(default="", max_length=253)
    port: int = Field(default=22, ge=1, le=65535)
    user: str = Field(default="", pattern=r"^[a-zA-Z0-9_.-]*$", max_length=64)
    root: str
    python: str = "python3"
    run_as: str | None = Field(default=None, pattern=r"^[a-zA-Z_][a-zA-Z0-9_.-]*$")
    identity_file: str | None = None
    control_path: str | None = None
    known_hosts: str | None = None
    config: WorkerConfig = Field(default_factory=WorkerConfig)

    @model_validator(mode="after")
    def valid_machine(self):
        if not Path(self.root).is_absolute() or ".." in Path(self.root).parts or self.root == "/":
            raise ValueError("Choose an absolute, dedicated worker directory")
        if self.kind == "ssh" and (
            not self.host
            or self.host.startswith("-")
            or not re.fullmatch(r"[a-zA-Z0-9_.:\[\]-]+", self.host)
        ):
            raise ValueError("Use an SSH hostname, address or configured SSH alias")
        if not self.python or "\x00" in self.python:
            raise ValueError("Choose the worker Python executable")
        return self


class Experiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol: Literal["simjecture-worker/1"] = PROTOCOL
    id: str = Field(pattern=r"^job_[a-f0-9]{40}$")
    binding: dict
    outputs: list[str] = Field(min_length=1, max_length=20000)
    deadline: float = Field(gt=0)
    timeout: float = Field(gt=0, le=604800)
    workspace_bytes: int = Field(default=4 * 1024**3, ge=1024**2, le=1024**4)
    resources: Resources = Field(default_factory=Resources)
    config_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    worker_code_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    worker_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def validate_files(self):
        b = self.binding
        if not isinstance(b.get("inputs"), dict) or b.get("source") not in b["inputs"]:
            raise ValueError("Freeze source and input hashes")
        for name in [*b["inputs"], *self.outputs]:
            safe_relative(name)
        if len(set(self.outputs)) != len(self.outputs) or set(self.outputs) & set(b["inputs"]):
            raise ValueError("Outputs must be distinct and separate from inputs")
        if any(not re.fullmatch(r"[a-f0-9]{64}", h) for h in b["inputs"].values()):
            raise ValueError("Invalid input SHA256")
        if not isinstance(b.get("args"), list) or any(
            not isinstance(arg, str) or "\x00" in arg for arg in b["args"]
        ):
            raise ValueError("Arguments must be strings without NUL")
        return self


def safe_relative(name):
    path = Path(name)
    if (
        not isinstance(name, str)
        or not name
        or path.is_absolute()
        or ".." in path.parts
        or name in {".", ""}
        or "\x00" in name
    ):
        raise ValueError("Use a contained relative file path")
    return path


def contained(root, name):
    root = Path(root).resolve()
    relative = safe_relative(name)
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("Worker paths must not traverse symlinks")
    if not current.resolve().is_relative_to(root):
        raise ValueError("Worker path escapes its directory")
    return current


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def load(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {} if default is None else default


def put(path, value):
    from .research_service import put as atomic_put

    atomic_put(path, value)


@contextlib.contextmanager
def lock(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root / ".worker.lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def private_put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    put(path, value)
    os.chmod(path, 0o600)
