"""Versioned operator deployment plans and point-in-time operational checks.

This does not install software, start services, authorize a launch, create study
state, or qualify scientific instruments. It composes existing machine probes.
"""

from __future__ import annotations

import errno
import hashlib
import math
import re
import time
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from . import deployment_probe

SHA256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,39}$")]
PositiveBytes = Annotated[int, Field(strict=True, gt=0, le=2**63 - 1)]


class DeploymentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class DeploymentSoftware(DeploymentRecord):
    simjecture_version: str = Field(min_length=1)
    python_source_sha256: SHA256 | None = None


class DeploymentRole(DeploymentRecord):
    backend: Literal["codex", "codex-glm", "grok", "agy", "builtin"]
    model: str = Field(min_length=1)
    reasoning_effort: Literal["low", "medium", "high", "xhigh", "max", "ultra"] | None = None


class DeploymentStudy(DeploymentRecord):
    worker: DeploymentRole
    director: DeploymentRole
    reviewer: DeploymentRole
    wall_seconds: float = Field(gt=0, strict=True)
    report_reserve_seconds: float = Field(gt=0, strict=True)
    initial_max_experiment_bytes: PositiveBytes
    initial_max_total_bytes: PositiveBytes
    director_storage_increases: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def budgets(self):
        if self.director.backend != self.reviewer.backend:
            raise ValueError("The current study launcher shares the director and reviewer backend")
        if self.report_reserve_seconds >= self.wall_seconds:
            raise ValueError("Reporting reserve must be smaller than the study wall allowance")
        if self.initial_max_total_bytes < self.initial_max_experiment_bytes:
            raise ValueError("Study storage must cover one experiment allowance")
        return self


class DeploymentCapability(DeploymentRecord):
    name: str = Field(min_length=1)
    contract_sha256: SHA256 | None = None


class DeploymentWorker(DeploymentRecord):
    id: Identifier
    config_sha256: SHA256 | None = None
    minimum_free_bytes: int = Field(default=0, strict=True, ge=0)
    capabilities: list[DeploymentCapability] = Field(default_factory=list)

    @model_validator(mode="after")
    def distinct_capabilities(self):
        if len({c.name for c in self.capabilities}) != len(self.capabilities):
            raise ValueError("Capability names must be distinct within each worker")
        return self


class DeploymentFile(DeploymentRecord):
    id: Identifier
    path: str = Field(min_length=1)
    sha256: SHA256
    machine: Identifier | None = None
    required: bool = Field(default=True, strict=True)
    purpose: Literal[
        "hypothesis",
        "instructions",
        "prior_evidence",
        "restart",
        "material",
        "source",
        "attention_config",
        "other",
    ] = "other"

    @model_validator(mode="after")
    def paths(self):
        if "\x00" in self.path:
            raise ValueError("File paths cannot contain NUL")
        if self.machine and (not self.path.startswith("/") or ".." in Path(self.path).parts):
            raise ValueError("Worker files require absolute paths without parent traversal")
        return self


class DeploymentAttention(DeploymentRecord):
    config_file: Identifier
    required: bool = Field(default=True, strict=True)


class CampaignDeploymentManifest(DeploymentRecord):
    schema_version: Literal["simjecture-deployment/1"]
    name: str = Field(min_length=1, max_length=160)
    machine_registry: str = Field(min_length=1)
    software: DeploymentSoftware
    workers: list[DeploymentWorker] = Field(min_length=1)
    files: list[DeploymentFile] = Field(default_factory=list)
    study: DeploymentStudy
    attention: DeploymentAttention | None = None

    @model_validator(mode="after")
    def references(self):
        workers = {w.id for w in self.workers}
        files = {f.id: f for f in self.files}
        if len(workers) != len(self.workers) or len(files) != len(self.files):
            raise ValueError("Worker IDs and file IDs must each be unique")
        if any(f.machine and f.machine not in workers for f in self.files):
            raise ValueError("Every worker file must reference a declared worker")
        if self.attention:
            config = files.get(self.attention.config_file)
            if config is None or config.machine is not None or config.purpose != "attention_config":
                raise ValueError("Attention must reference a coordinator attention_config file")
            if self.attention.required and not config.required:
                raise ValueError("Required attention needs a required configuration file")
        if "\x00" in self.machine_registry:
            raise ValueError("Registry paths cannot contain NUL")
        return self


class DeploymentCheck(DeploymentRecord):
    id: str
    status: Literal["planned", "passed", "failed", "skipped"]
    required: bool = True
    detail: str
    observed: dict[str, Any] = Field(default_factory=dict)
    next_action: str | None = None


class _HostInspection(DeploymentRecord):
    simjecture_version: str
    python_source_sha256: SHA256
    python_version: str
    files: dict[str, dict[str, Any]]
    storage: dict[str, Any]


class CampaignDeploymentReport(DeploymentRecord):
    schema_version: Literal["simjecture-deployment-report/1"] = "simjecture-deployment-report/1"
    name: str
    manifest_sha256: SHA256
    mode: Literal["plan", "check"]
    checked_at: float
    status: Literal["planned", "ready", "blocked"]
    checks: list[DeploymentCheck]
    declared_study: DeploymentStudy
    scientific_qualification: Literal["not_assessed"] = "not_assessed"
    study_created: Literal[False] = False
    unchecked: list[str] = Field(
        default_factory=lambda: [
            "Model-provider authentication, model availability, and model inference",
            "Scientific solver execution, numerical convergence, and claim acceptance",
            "Attention warm-up, lease, restart recovery, and service supervision",
            "Future resource availability and authorization to launch a study",
        ]
    )


def _path(base, value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def read_manifest(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise ValueError("Cannot read deployment manifest") from error
    try:
        manifest = CampaignDeploymentManifest.model_validate_json(raw)
    except ValidationError as error:
        # Pydantic's default formatting includes rejected values (possibly secrets).
        details = "; ".join(
            ".".join(map(str, item["loc"])) + ": " + item["msg"]
            for item in error.errors(include_input=False, include_context=False, include_url=False)
        )
        raise ValueError("Invalid deployment manifest: " + details) from None
    return manifest, hashlib.sha256(raw).hexdigest()


def deployment_report(path, *, check=False, timeout_seconds=120):
    """Plan offline, or inspect current workers/files without preparing or freezing them."""
    from .execution_pool import MachineRegistry, WorkerUnavailable, ssh_endpoint

    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        raise ValueError("Inspection timeout must be positive and finite")
    path = Path(path).resolve()
    manifest, digest = read_manifest(path)
    results = []

    def add(identifier, status, detail, *, required=True, observed=None, next_action=None):
        results.append(
            DeploymentCheck(
                id=identifier,
                status=status,
                required=required,
                detail=detail,
                observed=observed or {},
                next_action=next_action,
            )
        )

    def assess(identifier, passed, detail, **kwargs):
        add(identifier, "passed" if passed else "failed", detail, **kwargs)

    files = {f.id: f for f in manifest.files}
    coordinator_files = [f for f in manifest.files if f.machine is None]

    def file_results(items, probe):
        for item in items:
            actual = probe.get(item.id, {})
            matches = actual.get("sha256") == item.sha256
            missing_optional = not item.required and actual.get("errno") == errno.ENOENT
            # Optional means absence is allowed, not that corrupted data is trusted.
            add(
                "file:" + item.id,
                "skipped" if missing_optional else "passed" if matches else "failed",
                "Optional file absent"
                if missing_optional
                else "File identity matches"
                if matches
                else "File missing, unreadable, changing, or different from its expected identity",
                required=not missing_optional,
                observed=actual,
                next_action=None
                if matches or missing_optional
                else "Verify this file; review identity changes before updating the plan.",
            )

    if not check:
        add("coordinator", "planned", "Check installed package version and Python source identity")
        for worker in manifest.workers:
            add(
                "worker:" + worker.id, "planned", "Check registered worker, code, storage and tools"
            )
            add("code:" + worker.id, "planned", "Compare worker and coordinator Python source")
            add("storage:" + worker.id, "planned", "Inspect current worker free space")
            for capability in worker.capabilities:
                add(
                    "capability:" + worker.id + ":" + capability.name,
                    "planned",
                    "Check registered instrument identity, not scientific qualification",
                )
        for item in manifest.files:
            add("file:" + item.id, "planned", "Verify file SHA256", required=item.required)
        if manifest.attention:
            add(
                "attention",
                "planned",
                "Check configured service health and model identity",
                required=manifest.attention.required,
            )
    else:
        try:
            coordinator = deployment_probe.inspect_host(
                [{"id": f.id, "path": str(_path(path.parent, f.path))} for f in coordinator_files],
                str(path.parent),
            )
            coordinator = _HostInspection.model_validate(coordinator).model_dump()
        except (OSError, ValueError, ImportError) as error:
            coordinator = {"files": {}}
            add(
                "coordinator-inspection",
                "failed",
                "Coordinator inspection did not complete",
                observed={"error_type": type(error).__name__},
                next_action="Check the installed package and readable source files.",
            )
        expected = manifest.software
        matches = coordinator.get("simjecture_version") == expected.simjecture_version and (
            expected.python_source_sha256 is None
            or coordinator["python_source_sha256"] == expected.python_source_sha256
        )
        assess(
            "coordinator",
            matches,
            "Installed Simjecture identity versus manifest",
            observed={
                k: coordinator.get(k)
                for k in ["simjecture_version", "python_source_sha256", "python_version"]
            },
            next_action=None
            if matches
            else "Use the selected coordinator runtime or revise the plan.",
        )
        if "simjecture_version" in coordinator:
            file_results(coordinator_files, coordinator["files"])
        else:
            for item in coordinator_files:
                add(
                    "file:" + item.id,
                    "skipped",
                    "Coordinator inspection failed; file unchecked",
                    required=item.required,
                )
        registry = MachineRegistry(_path(path.parent, manifest.machine_registry))
        endpoints = set()
        for worker in manifest.workers:
            items = [f for f in manifest.files if f.machine == worker.id]
            try:
                machine = registry.machine(worker.id)
                endpoint = ssh_endpoint(machine.model_dump())
                if endpoint and endpoint in endpoints:
                    raise ValueError("Multiple profiles select the same SSH endpoint")
                if endpoint:
                    endpoints.add(endpoint)
                record = registry.check(worker.id)
                transport = registry.transport(worker.id)
                if (
                    transport.machine.model_dump() != machine.model_dump()
                    or record["machine"] != machine.model_dump()
                ):
                    raise ValueError("Worker profile changed during inspection")
                probe = record["probe"]
                observed = {
                    k: probe[k]
                    for k in ["worker_id", "config_sha256", "capacity", "python", "protocol"]
                }
                matches = worker.config_sha256 is None or (
                    probe["config_sha256"] == worker.config_sha256
                )
                assess(
                    "worker:" + worker.id,
                    matches,
                    "Registered worker launcher and configuration",
                    observed=observed,
                    next_action=None
                    if matches
                    else "Review the worker configuration; do not reconfigure active studies.",
                )
                actual = transport.run(
                    [machine.python, "-c", Path(deployment_probe.__file__).read_text()],
                    {
                        "files": [{"id": f.id, "path": f.path} for f in items],
                        "storage_path": machine.root,
                    },
                    timeout=timeout_seconds,
                )
                actual = _HostInspection.model_validate(actual).model_dump()
                same_code = all(
                    actual[k] == coordinator.get(k)
                    for k in ["simjecture_version", "python_source_sha256"]
                )
                assess(
                    "code:" + worker.id,
                    same_code,
                    "Worker and coordinator Python source match",
                    observed={
                        k: actual[k]
                        for k in ["simjecture_version", "python_source_sha256", "python_version"]
                    },
                    next_action=None
                    if same_code
                    else "Prepare a matching worker generation after draining affected studies.",
                )
                free = actual["storage"].get("free_bytes")
                enough_space = type(free) is int and free >= worker.minimum_free_bytes
                assess(
                    "storage:" + worker.id,
                    enough_space,
                    "Current free space versus planning reserve",
                    observed=actual["storage"],
                    next_action=None
                    if enough_space
                    else "Provision space if needed; this check reserves no storage.",
                )
                file_results(items, actual["files"])
                for capability in worker.capabilities:
                    available = probe["capabilities"].get(capability.name)
                    identity = available.get("contract_sha256") if available else None
                    matches = (
                        isinstance(identity, str)
                        and bool(re.fullmatch(r"[a-f0-9]{64}", identity))
                        and (
                            capability.contract_sha256 is None
                            or identity == capability.contract_sha256
                        )
                    )
                    assess(
                        "capability:" + worker.id + ":" + capability.name,
                        matches,
                        "Registered instrument identity; scientific qualification is not assessed",
                        observed={"contract_sha256": identity},
                        next_action=None
                        if matches
                        else "Install/register this instrument with the existing machine tooling.",
                    )
            except (OSError, ValueError, KeyError, TypeError, WorkerUnavailable) as error:
                add(
                    "probe:" + worker.id,
                    "failed",
                    "Worker inspection did not complete",
                    observed={"error_type": type(error).__name__},
                    next_action="Check worker readiness, file access, and the inspection timeout.",
                )
                for item in items:
                    if not any(r.id == "file:" + item.id for r in results):
                        add(
                            "file:" + item.id,
                            "skipped",
                            "Worker unavailable; file was not checked",
                            required=item.required,
                        )
                for identifier in [
                    "worker:" + worker.id,
                    "code:" + worker.id,
                    "storage:" + worker.id,
                    *("capability:" + worker.id + ":" + c.name for c in worker.capabilities),
                ]:
                    if not any(r.id == identifier for r in results):
                        add(identifier, "skipped", "Worker inspection failed; item unchecked")
        if manifest.attention:
            item = files[manifest.attention.config_file]
            verified = next(r for r in results if r.id == "file:" + item.id).status == "passed"
            if not verified:
                add(
                    "attention",
                    "skipped",
                    "Attention configuration was not verified",
                    required=manifest.attention.required,
                )
            else:
                try:
                    from simjecture_monitor.tool import AttentionClient, AttentionConfig

                    raw = _path(path.parent, item.path).read_bytes()
                    if hashlib.sha256(raw).hexdigest() != item.sha256:
                        raise ValueError("Attention configuration changed during inspection")
                    config = AttentionConfig.model_validate_json(raw)
                    value = AttentionClient(config).health()
                    if value.get("ready") is not True:
                        raise ValueError("Attention service is not ready")
                    add(
                        "attention",
                        "passed",
                        "Service health and pinned model identity verified",
                        required=manifest.attention.required,
                        observed={"ready": value["ready"], "policy": value["policy"]},
                    )
                except Exception as error:
                    add(
                        "attention",
                        "failed",
                        "Attention health check did not succeed",
                        required=manifest.attention.required,
                        observed={"error_type": type(error).__name__},
                        next_action="Inspect the service with 'simjecture attention check'.",
                    )

    ready = check and all(r.status == "passed" for r in results if r.required)
    return CampaignDeploymentReport(
        name=manifest.name,
        manifest_sha256=digest,
        mode="check" if check else "plan",
        checked_at=time.time(),
        status="ready" if ready else "blocked" if check else "planned",
        checks=results,
        declared_study=manifest.study,
    )


def configure_parser(parser):
    parser.add_argument("operation", choices=["plan", "check"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120,
        help="Per-worker file/source inspection timeout; registry checks retain their own timeout",
    )
    parser.set_defaults(handler=run)


def run(args):
    # Refuse accidental overwrite before doing any potentially expensive checks.
    if args.output and args.output.exists():
        raise ValueError("Choose a new report path; previous preparation receipts are preserved")
    if args.output and not args.output.parent.is_dir():
        raise ValueError("Create the report's parent directory before running checks")
    report = deployment_report(
        args.manifest, check=args.operation == "check", timeout_seconds=args.timeout_seconds
    )
    body = report.model_dump_json(indent=2) + "\n"
    if args.output:
        try:
            with args.output.open("x") as stream:
                stream.write(body)
        except OSError as error:
            raise ValueError("Cannot create the report; choose a new writable path") from error
    print(body, end="")
    return int(report.status == "blocked")
