"""Operator-side deployment and health checks for optional scientific runtimes."""

from __future__ import annotations

import importlib.metadata as metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field

from .models import StrictModel
from .mvp_agent import BubblewrapSandbox, MVPAgentConfig
from .mvp_skills import (
    MVPCapabilityConfig,
    MVPCapabilityInstallation,
    MVPCapabilityRegistry,
)

WARPX_CPU_CAPABILITY = "warpx-cpu-26.07"
WARPX_CUDA_CAPABILITY = "warpx-cuda-openpmd-26.07"
FLASH_MHD_CAPABILITY = "flash-island-coalescence-resistive-mhd-4.8"
PINNED_WARPX_REVISION = "312d507407a1bf6f01ae43fb41b5c3a3700d053c"

_CAPABILITY_CONFIGS = {
    WARPX_CPU_CAPABILITY: "warpx-cpu-26.07.json",
    WARPX_CUDA_CAPABILITY: "warpx-cuda-openpmd-26.07.json",
    FLASH_MHD_CAPABILITY: "flash-island-coalescence-resistive-mhd-4.8.json",
}
_CORE_DISTRIBUTIONS = (
    "simjecture",
    "httpx",
    "matplotlib",
    "numpy",
    "pandas",
    "pydantic",
    "scipy",
)


class DeploymentProfile(StrEnum):
    CORE = "core"
    WARPX_CPU = "warpx-cpu"
    WARPX_CUDA = "warpx-cuda"
    FLASH = "flash"


_PROFILE_BY_CAPABILITY = {
    WARPX_CPU_CAPABILITY: DeploymentProfile.WARPX_CPU,
    WARPX_CUDA_CAPABILITY: DeploymentProfile.WARPX_CUDA,
    FLASH_MHD_CAPABILITY: DeploymentProfile.FLASH,
}


class DeploymentCheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    PLANNED = "planned"


class DeploymentCheck(StrictModel):
    name: str = Field(min_length=1)
    status: DeploymentCheckStatus
    required: bool = True
    detail: str = Field(min_length=1)
    remedy: str | None = None


class DeploymentReport(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    profile: str = Field(min_length=1)
    project_root: str = Field(min_length=1)
    ready: bool
    planned: bool = False
    changed: bool = False
    command: tuple[str, ...] = ()
    checks: tuple[DeploymentCheck, ...]


def resolve_project_root(explicit: str | Path | None = None) -> Path:
    """Find the source checkout that owns deployment assets."""

    if explicit is not None:
        candidates = (Path(explicit).resolve(),)
    else:
        current = Path.cwd().resolve()
        source_fallback = Path(__file__).resolve().parents[2]
        candidates = (current, *current.parents, source_fallback)

    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if all(
            (candidate / marker).exists()
            for marker in ("pyproject.toml", "skills", "capabilities", "environments")
        ):
            return candidate
    requested = str(explicit) if explicit is not None else str(Path.cwd())
    raise FileNotFoundError(
        "deployment requires a source checkout containing pyproject.toml, skills/, "
        f"capabilities/, and environments/; none was found from {requested}"
    )


def _check(
    name: str,
    status: DeploymentCheckStatus,
    detail: str,
    *,
    required: bool = True,
    remedy: str | None = None,
) -> DeploymentCheck:
    return DeploymentCheck(
        name=name,
        status=status,
        required=required,
        detail=" ".join(detail.split()),
        remedy=" ".join(remedy.split()) if remedy else None,
    )


def _nested_value(payload: object, dotted_path: str) -> object:
    current = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


class DeploymentManager:
    """Provision project-local runtimes without granting authority to an agent."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = resolve_project_root(project_root)
        self.capability_root = self.project_root / "capabilities"
        self.runtime_root = self.project_root / ".runtime"

    def _core_checks(self, *, probe: bool) -> list[DeploymentCheck]:
        checks: list[DeploymentCheck] = []
        supported_python = sys.version_info >= (3, 11)
        checks.append(
            _check(
                "core.python",
                DeploymentCheckStatus.PASS if supported_python else DeploymentCheckStatus.FAIL,
                f"Python {sys.version.split()[0]} at {Path(sys.executable).resolve()}",
                remedy="Install Python 3.11 or newer." if not supported_python else None,
            )
        )
        linux = sys.platform.startswith("linux")
        checks.append(
            _check(
                "core.platform",
                DeploymentCheckStatus.PASS if linux else DeploymentCheckStatus.FAIL,
                f"platform={sys.platform}",
                remedy="The Bubblewrap MVP currently requires Linux." if not linux else None,
            )
        )
        lock_path = self.project_root / "uv.lock"
        locked_versions: dict[str, set[str]] = {}
        try:
            lock = tomllib.loads(lock_path.read_text())
            packages = lock["package"]
            if not isinstance(packages, list):
                raise ValueError("uv.lock package table is not a list")
            for package in packages:
                if not isinstance(package, dict):
                    raise ValueError("uv.lock contains a non-table package")
                name = str(package["name"])
                version = str(package["version"])
                locked_versions.setdefault(name, set()).add(version)
        except (OSError, KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
            checks.append(
                _check(
                    "core.lock",
                    DeploymentCheckStatus.FAIL,
                    f"cannot read the project lock: {error}",
                    remedy="Restore uv.lock and run `uv sync --frozen`.",
                )
            )
        else:
            checks.append(
                _check(
                    "core.lock",
                    DeploymentCheckStatus.PASS,
                    f"loaded {len(packages)} locked package record(s) from {lock_path}",
                )
            )
        for distribution in _CORE_DISTRIBUTIONS:
            try:
                version = metadata.version(distribution)
            except metadata.PackageNotFoundError:
                checks.append(
                    _check(
                        f"core.package.{distribution}",
                        DeploymentCheckStatus.FAIL,
                        f"{distribution} is not installed",
                        remedy="Install the locked project environment with `uv sync --frozen`.",
                    )
                )
            else:
                expected = locked_versions.get(distribution, set())
                matches_lock = version in expected
                checks.append(
                    _check(
                        f"core.package.{distribution}",
                        (
                            DeploymentCheckStatus.PASS
                            if matches_lock
                            else DeploymentCheckStatus.FAIL
                        ),
                        (
                            f"{distribution}={version}; "
                            f"locked={','.join(sorted(expected)) or 'missing'}"
                        ),
                        remedy=(
                            "Synchronize the exact environment with `uv sync --frozen`."
                            if not matches_lock
                            else None
                        ),
                    )
                )

        bubblewrap = shutil.which("bwrap")
        checks.append(
            _check(
                "core.bubblewrap",
                DeploymentCheckStatus.PASS if bubblewrap else DeploymentCheckStatus.FAIL,
                f"bubblewrap={bubblewrap}" if bubblewrap else "bubblewrap is unavailable",
                remedy=(
                    "Install the Bubblewrap operating-system package before autonomous runs."
                    if not bubblewrap
                    else None
                ),
            )
        )
        if bubblewrap and probe:
            command = [
                bubblewrap,
                "--unshare-all",
                "--die-with-parent",
                "--new-session",
            ]
            for system_root in ("/usr", "/lib", "/lib64"):
                if Path(system_root).exists():
                    command.extend(("--ro-bind", system_root, system_root))
            command.extend(("--dev", "/dev", "--proc", "/proc", "/usr/bin/true"))
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
            except (OSError, subprocess.SubprocessError) as error:
                result_detail = str(error)
                returncode = 1
            else:
                result_detail = result.stderr.strip() or "namespace creation succeeded"
                returncode = result.returncode
            checks.append(
                _check(
                    "core.bubblewrap_namespace",
                    (
                        DeploymentCheckStatus.PASS
                        if returncode == 0
                        else DeploymentCheckStatus.FAIL
                    ),
                    result_detail,
                    remedy=(
                        "Enable unprivileged user namespaces for Bubblewrap on this host."
                        if returncode != 0
                        else None
                    ),
                )
            )
        return checks

    def _capability_config_path(self, capability: str) -> Path:
        try:
            name = _CAPABILITY_CONFIGS[capability]
        except KeyError as error:
            raise ValueError(f"unknown deployment capability {capability!r}") from error
        return self.capability_root / name

    def _configured_runtime_root(self, capability: str) -> Path:
        path = self._capability_config_path(capability)
        config = MVPCapabilityConfig.model_validate_json(path.read_bytes())
        return (path.parent / config.runtime_root).resolve()

    def _skill_resource(self, installation: MVPCapabilityInstallation) -> Path:
        relative = Path(installation.manifest.preflight_resource or "")
        path = self.project_root / "skills" / installation.manifest.skill / relative
        if not path.is_file():
            raise FileNotFoundError(f"capability preflight resource is unavailable: {path}")
        return path

    def _probe_capability(self, installation: MVPCapabilityInstallation) -> str:
        manifest = installation.manifest
        if not manifest.preflight_resource or not manifest.preflight_result:
            return "capability has no declared preflight"
        source = self._skill_resource(installation)
        with tempfile.TemporaryDirectory(prefix="acs-capability-doctor-") as temporary:
            workspace = Path(temporary)
            program = workspace / manifest.preflight_resource
            program.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, program)
            registry = MVPCapabilityRegistry((installation,))
            sandbox = BubblewrapSandbox(
                workspace,
                MVPAgentConfig(
                    max_iterations=1,
                    max_wall_seconds=180,
                    max_command_seconds=120,
                    max_workspace_bytes=128 * 1024 * 1024,
                    max_file_bytes=64 * 1024 * 1024,
                    max_memory_bytes=4 * 1024 * 1024 * 1024,
                ),
                registry,
            )
            result = sandbox.run_capability(
                manifest.name,
                (manifest.preflight_resource,),
                timeout_seconds=120,
            )
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic output"
                raise RuntimeError(
                    f"preflight command exited with {result.returncode}: {detail}"
                )
            result_path = workspace / manifest.preflight_result
            if not result_path.is_file():
                raise RuntimeError(
                    f"preflight did not create {manifest.preflight_result!r}"
                )
            payload = json.loads(result_path.read_text())
            failed = [
                path
                for path in manifest.preflight_checks
                if _nested_value(payload, path) is not True
            ]
            if failed:
                raise RuntimeError(f"preflight checks were false: {', '.join(failed)}")
        return (
            f"{manifest.name} passed {len(manifest.preflight_checks)} declared "
            "preflight check(s)"
        )

    def _capability_checks(
        self,
        capability: str,
        *,
        required: bool,
        probe: bool,
    ) -> tuple[list[DeploymentCheck], MVPCapabilityInstallation | None]:
        status_on_failure = (
            DeploymentCheckStatus.FAIL if required else DeploymentCheckStatus.WARNING
        )
        config_path = self._capability_config_path(capability)
        if not config_path.is_file():
            return (
                [
                    _check(
                        f"capability.{capability}.configuration",
                        status_on_failure,
                        f"missing capability manifest {config_path}",
                        required=required,
                        remedy="Restore the versioned capability manifest from the repository.",
                    )
                ],
                None,
            )
        try:
            installation = MVPCapabilityInstallation.read(config_path)
        except (OSError, ValueError) as error:
            if capability == FLASH_MHD_CAPABILITY:
                remedy = (
                    "Obtain FLASH from the official FLASH Center under its license, "
                    "build and register the application-specific local runtime described "
                    "by `skills/flash-mhd/references/local-deployment.md`, then rerun "
                    "`simjecture doctor --profile flash`."
                )
            else:
                remedy = (
                    "Run `simjecture install "
                    f"{_PROFILE_BY_CAPABILITY[capability].value}`."
                )
            return (
                [
                    _check(
                        f"capability.{capability}.runtime",
                        status_on_failure,
                        str(error),
                        required=required,
                        remedy=remedy,
                    )
                ],
                None,
            )
        checks = [
            _check(
                f"capability.{capability}.runtime",
                DeploymentCheckStatus.PASS,
                (
                    f"runtime={installation.runtime_root}; "
                    f"contract_sha256={installation.contract_hash}"
                ),
                required=required,
            )
        ]
        if probe:
            try:
                detail = self._probe_capability(installation)
            except (OSError, ValueError, KeyError, RuntimeError, json.JSONDecodeError) as error:
                if capability == WARPX_CPU_CAPABILITY:
                    remedy = (
                        "Inspect the runtime and rerun the CPU profile installer with --repair."
                    )
                elif capability == WARPX_CUDA_CAPABILITY:
                    remedy = (
                        "Preserve or move the CUDA runtime and dependency roots, then perform "
                        "a fresh audited installation."
                    )
                else:
                    remedy = (
                        "Preserve the operator-supplied FLASH runtime, inspect its build "
                        "record and preflight input, and follow the flash-mhd deployment guide."
                    )
                checks.append(
                    _check(
                        f"capability.{capability}.preflight",
                        status_on_failure,
                        str(error),
                        required=required,
                        remedy=remedy,
                    )
                )
            else:
                checks.append(
                    _check(
                        f"capability.{capability}.preflight",
                        DeploymentCheckStatus.PASS,
                        detail,
                        required=required,
                    )
                )
        return checks, installation

    @staticmethod
    def _ready(checks: list[DeploymentCheck]) -> bool:
        return not any(
            item.required and item.status is DeploymentCheckStatus.FAIL for item in checks
        )

    def doctor(self, profile: str = "all", *, probe: bool = True) -> DeploymentReport:
        if profile not in {"all", *(item.value for item in DeploymentProfile)}:
            raise ValueError(f"unknown deployment profile {profile!r}")
        checks = self._core_checks(probe=probe)
        capabilities: tuple[tuple[str, bool], ...]
        if profile == DeploymentProfile.WARPX_CPU:
            capabilities = ((WARPX_CPU_CAPABILITY, True),)
        elif profile == DeploymentProfile.WARPX_CUDA:
            capabilities = ((WARPX_CUDA_CAPABILITY, True),)
        elif profile == DeploymentProfile.FLASH:
            capabilities = ((FLASH_MHD_CAPABILITY, True),)
        elif profile == "all":
            capabilities = (
                (WARPX_CPU_CAPABILITY, False),
                (WARPX_CUDA_CAPABILITY, False),
                (FLASH_MHD_CAPABILITY, False),
            )
        else:
            capabilities = ()
        for capability, required in capabilities:
            capability_checks, _ = self._capability_checks(
                capability,
                required=required,
                probe=probe,
            )
            checks.extend(capability_checks)
        return DeploymentReport(
            profile=profile,
            project_root=str(self.project_root),
            ready=self._ready(checks),
            checks=tuple(checks),
        )

    def _write_report(self, report: DeploymentReport) -> None:
        directory = self.runtime_root / "deployment"
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{report.profile}.json"
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(report.model_dump_json(indent=2) + "\n")
        os.replace(temporary, destination)

    def _already_ready(self, profile: DeploymentProfile) -> DeploymentReport | None:
        report = self.doctor(profile.value, probe=True)
        return report if report.ready else None

    def _install_cpu(
        self,
        *,
        dry_run: bool,
        repair: bool,
        environment_manager: str | None,
        capture_output: bool,
    ) -> DeploymentReport:
        ready = self._already_ready(DeploymentProfile.WARPX_CPU)
        if ready is not None:
            self._write_report(ready)
            return ready
        checks = self._core_checks(probe=True)
        if not self._ready(checks):
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CPU,
                project_root=str(self.project_root),
                ready=False,
                checks=tuple(checks),
            )
        prefix = self._configured_runtime_root(WARPX_CPU_CAPABILITY)
        managed_prefix = (prefix / "conda-meta").is_dir()
        if prefix.exists() and not repair:
            checks.append(
                _check(
                    "install.warpx-cpu.existing_runtime",
                    DeploymentCheckStatus.FAIL,
                    f"an existing but unhealthy runtime was left unchanged at {prefix}",
                    remedy="Inspect it, then rerun with --repair to update a Conda-managed prefix.",
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CPU,
                project_root=str(self.project_root),
                ready=False,
                checks=tuple(checks),
            )
        if prefix.exists() and repair and not managed_prefix:
            checks.append(
                _check(
                    "install.warpx-cpu.existing_runtime",
                    DeploymentCheckStatus.FAIL,
                    f"refusing to modify a non-Conda directory at {prefix}",
                    remedy="Move the directory aside and run the installer again.",
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CPU,
                project_root=str(self.project_root),
                ready=False,
                checks=tuple(checks),
            )
        manager = (
            shutil.which(environment_manager)
            if environment_manager
            else shutil.which("micromamba") or shutil.which("mamba")
        )
        if not manager:
            checks.append(
                _check(
                    "install.warpx-cpu.environment_manager",
                    DeploymentCheckStatus.FAIL,
                    "neither micromamba nor mamba is available",
                    remedy="Install Miniforge, Mambaforge, or Micromamba.",
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CPU,
                project_root=str(self.project_root),
                ready=False,
                checks=tuple(checks),
            )
        environment_file = self.project_root / "environments" / "warpx-cpu.yml"
        action = "update" if managed_prefix and repair else "create"
        if action == "update":
            command = (
                manager,
                "env",
                "update",
                "--yes",
                "--prefix",
                str(prefix),
                "--file",
                str(environment_file),
                "--prune",
            )
        else:
            command = (
                manager,
                "create",
                "--yes",
                "--prefix",
                str(prefix),
                "--file",
                str(environment_file),
            )
        if dry_run:
            checks.append(
                _check(
                    "install.warpx-cpu.command",
                    DeploymentCheckStatus.PLANNED,
                    " ".join(command),
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CPU,
                project_root=str(self.project_root),
                ready=False,
                planned=True,
                command=command,
                checks=tuple(checks),
            )
        result = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=capture_output,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() if capture_output else "environment manager failed"
            checks.append(
                _check(
                    "install.warpx-cpu.command",
                    DeploymentCheckStatus.FAIL,
                    detail or "environment manager failed without diagnostic output",
                    remedy="Review the Conda solver output; the existing prefix was not deleted.",
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CPU,
                project_root=str(self.project_root),
                ready=False,
                command=command,
                checks=tuple(checks),
            )
        report = self.doctor(DeploymentProfile.WARPX_CPU, probe=True)
        report = report.model_copy(update={"changed": True, "command": command})
        self._write_report(report)
        return report

    def _source_revision_check(self, source: Path) -> DeploymentCheck:
        git = shutil.which("git")
        if not source.is_dir():
            return _check(
                "install.warpx-cuda.source",
                DeploymentCheckStatus.FAIL,
                f"WarpX source directory is unavailable: {source}",
                remedy=f"Check out WarpX revision {PINNED_WARPX_REVISION}.",
            )
        if not git:
            return _check(
                "install.warpx-cuda.source",
                DeploymentCheckStatus.FAIL,
                "git is unavailable, so the WarpX source revision cannot be verified",
                remedy="Install Git and use the audited WarpX source checkout.",
            )
        result = subprocess.run(
            (git, "-C", str(source), "rev-parse", "HEAD"),
            check=False,
            capture_output=True,
            text=True,
        )
        observed = result.stdout.strip()
        if result.returncode != 0 or observed != PINNED_WARPX_REVISION:
            return _check(
                "install.warpx-cuda.source",
                DeploymentCheckStatus.FAIL,
                f"observed source revision={observed or 'unavailable'}",
                remedy=f"Use the audited WarpX revision {PINNED_WARPX_REVISION}.",
            )
        return _check(
            "install.warpx-cuda.source",
            DeploymentCheckStatus.PASS,
            f"WarpX source revision={observed}",
        )

    def _install_cuda(
        self,
        *,
        source: str | Path | None,
        jobs: int,
        arch: str | None,
        dry_run: bool,
        capture_output: bool,
    ) -> DeploymentReport:
        ready = self._already_ready(DeploymentProfile.WARPX_CUDA)
        if ready is not None:
            self._write_report(ready)
            return ready
        checks = self._core_checks(probe=True)
        prefix = self._configured_runtime_root(WARPX_CUDA_CAPABILITY)
        cuda_roots = (
            prefix,
            self.runtime_root / "cuda-toolkit-12.4",
            self.runtime_root / "warpx-cuda-openpmd-deps",
        )
        existing_roots = tuple(path for path in cuda_roots if path.exists())
        if existing_roots:
            checks.append(
                _check(
                    "install.warpx-cuda.existing_runtime",
                    DeploymentCheckStatus.FAIL,
                    (
                        "existing but unhealthy CUDA deployment roots were left unchanged: "
                        + ", ".join(str(path) for path in existing_roots)
                    ),
                    remedy=(
                        "Move the runtime and its project-local dependency prefixes aside, "
                        "then run a fresh audited installation."
                    ),
                )
            )
        if source is None:
            checks.append(
                _check(
                    "install.warpx-cuda.source",
                    DeploymentCheckStatus.FAIL,
                    "--source is required for a new CUDA build",
                    remedy=f"Supply a WarpX checkout at revision {PINNED_WARPX_REVISION}.",
                )
            )
        else:
            checks.append(self._source_revision_check(Path(source).resolve()))
        if jobs < 1:
            checks.append(
                _check(
                    "install.warpx-cuda.jobs",
                    DeploymentCheckStatus.FAIL,
                    f"jobs={jobs}",
                    remedy="Choose at least one build job.",
                )
            )
        if arch is not None and not arch.isdigit():
            checks.append(
                _check(
                    "install.warpx-cuda.arch",
                    DeploymentCheckStatus.FAIL,
                    f"invalid CUDA architecture={arch!r}",
                    remedy="Use digits such as 89, or omit --arch for detection.",
                )
            )
        if not self._ready(checks):
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CUDA,
                project_root=str(self.project_root),
                ready=False,
                checks=tuple(checks),
            )
        assert source is not None
        bootstrap = self.project_root / "skills" / "warpx" / "scripts" / "bootstrap_local_cuda.sh"
        if not bootstrap.is_file() or not os.access(bootstrap, os.X_OK):
            checks.append(
                _check(
                    "install.warpx-cuda.bootstrap",
                    DeploymentCheckStatus.FAIL,
                    f"CUDA bootstrap is unavailable or not executable: {bootstrap}",
                    remedy="Restore the versioned WarpX skill scripts.",
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CUDA,
                project_root=str(self.project_root),
                ready=False,
                checks=tuple(checks),
            )
        command = (
            str(bootstrap),
            "--source",
            str(Path(source).resolve()),
            "--jobs",
            str(jobs),
            *(("--arch", arch) if arch is not None else ()),
        )
        if dry_run:
            checks.append(
                _check(
                    "install.warpx-cuda.command",
                    DeploymentCheckStatus.PLANNED,
                    " ".join(command),
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CUDA,
                project_root=str(self.project_root),
                ready=False,
                planned=True,
                command=command,
                checks=tuple(checks),
            )
        result = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=capture_output,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() if capture_output else "CUDA bootstrap failed"
            checks.append(
                _check(
                    "install.warpx-cuda.command",
                    DeploymentCheckStatus.FAIL,
                    detail or "CUDA bootstrap failed without diagnostic output",
                    remedy="Preserve the build log and inspect the documented failure signatures.",
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CUDA,
                project_root=str(self.project_root),
                ready=False,
                command=command,
                checks=tuple(checks),
            )
        report = self.doctor(DeploymentProfile.WARPX_CUDA, probe=True)
        report = report.model_copy(update={"changed": True, "command": command})
        self._write_report(report)
        return report

    def install(
        self,
        profile: DeploymentProfile,
        *,
        dry_run: bool = False,
        repair: bool = False,
        environment_manager: str | None = None,
        source: str | Path | None = None,
        jobs: int = 8,
        arch: str | None = None,
        capture_output: bool = False,
    ) -> DeploymentReport:
        if profile is DeploymentProfile.CORE:
            report = self.doctor(DeploymentProfile.CORE, probe=True)
            if not dry_run:
                self._write_report(report)
            return report
        if profile is DeploymentProfile.WARPX_CPU:
            return self._install_cpu(
                dry_run=dry_run,
                repair=repair,
                environment_manager=environment_manager,
                capture_output=capture_output,
            )
        if profile is DeploymentProfile.FLASH:
            report = self.doctor(DeploymentProfile.FLASH, probe=True)
            if not dry_run:
                self._write_report(report)
            return report
        if repair:
            checks = self._core_checks(probe=True)
            checks.append(
                _check(
                    "install.warpx-cuda.repair",
                    DeploymentCheckStatus.FAIL,
                    "automatic in-place CUDA repair is intentionally unavailable",
                    remedy=(
                        "Preserve or move the existing instrument and dependency roots, "
                        "then perform a fresh audited build."
                    ),
                )
            )
            return DeploymentReport(
                profile=DeploymentProfile.WARPX_CUDA,
                project_root=str(self.project_root),
                ready=False,
                checks=tuple(checks),
            )
        return self._install_cuda(
            source=source,
            jobs=jobs,
            arch=arch,
            dry_run=dry_run,
            capture_output=capture_output,
        )


def print_deployment_report(report: DeploymentReport, *, as_json: bool) -> None:
    if as_json:
        print(report.model_dump_json(indent=2))
        return
    print(f"profile={report.profile}")
    print(f"ready={str(report.ready).lower()}")
    print(f"planned={str(report.planned).lower()}")
    print(f"changed={str(report.changed).lower()}")
    print(f"project_root={report.project_root}")
    for item in report.checks:
        print(
            f"check={item.name} status={item.status.value} "
            f"required={str(item.required).lower()} detail={item.detail}"
        )
        if item.remedy:
            print(f"remedy={item.name}: {item.remedy}")
