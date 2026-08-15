"""Read-only skills and installed executable capabilities for the sandbox MVP."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel


def _relative_path(value: str, *, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a contained relative path")
    return path


def _is_generated_skill_path(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"skill trees cannot contain symlinks: {path}")
        if _is_generated_skill_path(path.relative_to(root)):
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


class MVPSkillManifest(StrictModel):
    """Versioned documentation made visible to the autonomous agent."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    entrypoint: str = "SKILL.md"
    capability_names: tuple[str, ...] = ()

    @model_validator(mode="after")
    def contained_unique_paths(self) -> MVPSkillManifest:
        _relative_path(self.entrypoint, label="skill entrypoint")
        if len(self.capability_names) != len(set(self.capability_names)):
            raise ValueError("skill capability names must be unique")
        return self


@dataclass(frozen=True)
class _InstalledSkill:
    manifest: MVPSkillManifest
    root: Path
    content_hash: str


class MVPSkillCatalog:
    """Discover and read immutable, host-controlled skill documentation."""

    def __init__(self, installed: tuple[_InstalledSkill, ...] = ()) -> None:
        self._skills = {item.manifest.name: item for item in installed}
        if len(self._skills) != len(installed):
            raise ValueError("skill names must be unique")

    @classmethod
    def discover(cls, root: str | Path) -> MVPSkillCatalog:
        catalog_root = Path(root).resolve()
        if not catalog_root.is_dir():
            return cls()
        installed: list[_InstalledSkill] = []
        for manifest_path in sorted(catalog_root.glob("*/manifest.json")):
            skill_root = manifest_path.parent.resolve()
            manifest = MVPSkillManifest.model_validate_json(manifest_path.read_text())
            entrypoint = (skill_root / manifest.entrypoint).resolve()
            if not entrypoint.is_relative_to(skill_root) or not entrypoint.is_file():
                raise ValueError(f"skill {manifest.name!r} has no valid entrypoint")
            installed.append(
                _InstalledSkill(
                    manifest=manifest,
                    root=skill_root,
                    content_hash=_tree_hash(skill_root),
                )
            )
        return cls(tuple(installed))

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    @property
    def hashes(self) -> dict[str, str]:
        return {
            name: item.content_hash
            for name, item in sorted(self._skills.items())
        }

    def descriptors(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "name": item.manifest.name,
                "version": item.manifest.version,
                "description": item.manifest.description,
                "entrypoint": item.manifest.entrypoint,
                "capability_names": list(item.manifest.capability_names),
                "content_sha256": item.content_hash,
            }
            for item in sorted(self._skills.values(), key=lambda value: value.manifest.name)
        )

    def read(self, name: str, relative: str | None, *, max_chars: int) -> dict[str, Any]:
        try:
            installed = self._skills[name]
        except KeyError as error:
            raise ValueError(f"unknown skill {name!r}") from error
        if _tree_hash(installed.root) != installed.content_hash:
            raise RuntimeError(f"skill {name!r} changed after campaign discovery")
        requested = _relative_path(
            relative or installed.manifest.entrypoint,
            label="skill resource",
        )
        if _is_generated_skill_path(requested):
            raise ValueError("generated artifacts are not skill resources")
        path = (installed.root / requested).resolve()
        if not path.is_relative_to(installed.root) or not path.is_file():
            raise ValueError("requested skill resource is not a file")
        content = path.read_text(errors="replace")
        truncated = len(content) > max_chars
        if truncated:
            half = max(1, max_chars // 2)
            content = content[:half] + "\n... skill content truncated ...\n" + content[-half:]
        return {
            "skill": name,
            "version": installed.manifest.version,
            "path": requested.as_posix(),
            "content": content,
            "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "skill_sha256": installed.content_hash,
            "truncated": truncated,
        }

    def read_bytes(
        self,
        name: str,
        relative: str,
        *,
        max_bytes: int,
    ) -> tuple[dict[str, Any], bytes]:
        """Read one complete immutable resource for exact workspace materialization."""

        try:
            installed = self._skills[name]
        except KeyError as error:
            raise ValueError(f"unknown skill {name!r}") from error
        if _tree_hash(installed.root) != installed.content_hash:
            raise RuntimeError(f"skill {name!r} changed after campaign discovery")
        requested = _relative_path(relative, label="skill resource")
        if _is_generated_skill_path(requested):
            raise ValueError("generated artifacts are not skill resources")
        path = (installed.root / requested).resolve()
        if not path.is_relative_to(installed.root) or not path.is_file():
            raise ValueError("requested skill resource is not a file")
        content = path.read_bytes()
        if len(content) > max_bytes:
            raise ValueError("skill resource exceeds the sandbox materialization limit")
        return (
            {
                "skill": name,
                "version": installed.manifest.version,
                "path": requested.as_posix(),
                "content_sha256": hashlib.sha256(content).hexdigest(),
                "skill_sha256": installed.content_hash,
            },
            content,
        )


class MVPCapabilityManifest(StrictModel):
    """Model-visible identity of one installed executable capability."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    skill: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    executable_kind: str = Field(min_length=1)
    preflight_resource: str | None = Field(
        default=None,
        description=(
            "Optional executable examples/ resource from the named skill used for "
            "a harness-managed, cached, permanently non-evidentiary health check"
        ),
    )
    preflight_result: str | None = Field(
        default=None,
        description="Workspace-relative JSON result written by preflight_resource",
    )
    preflight_checks: tuple[str, ...] = Field(
        default=(),
        description="Dot-separated JSON boolean paths that must all equal true",
    )

    @model_validator(mode="after")
    def preflight_stays_in_examples(self) -> MVPCapabilityManifest:
        configured = self.preflight_resource is not None
        if configured != (self.preflight_result is not None) or configured != bool(
            self.preflight_checks
        ):
            raise ValueError(
                "capability preflight_resource, preflight_result, and "
                "preflight_checks must be configured together"
            )
        if not configured:
            return self
        assert self.preflight_resource is not None
        assert self.preflight_result is not None
        path = _relative_path(
            self.preflight_resource,
            label="capability preflight resource",
        )
        if not path.parts or path.parts[0] != "examples" or path.suffix != ".py":
            raise ValueError(
                "capability preflight resource must be a Python file under examples/"
            )
        result_path = _relative_path(
            self.preflight_result,
            label="capability preflight result",
        )
        if self.preflight_result in {"", "."} or result_path.suffix != ".json":
            raise ValueError("capability preflight result must be a JSON workspace path")
        for check in self.preflight_checks:
            if not check or any(
                not part.replace("_", "").replace("-", "").isalnum()
                for part in check.split(".")
            ):
                raise ValueError("capability preflight checks must be dot-separated keys")
        return self


class MVPCapabilityConfig(StrictModel):
    """Host installation details that are never disclosed to the model."""

    manifest: MVPCapabilityManifest
    runtime_root: str = Field(min_length=1)
    executable: str = Field(min_length=1)
    environment: dict[str, str] = Field(default_factory=dict)
    read_only_mounts: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Additional host roots, relative to the capability directory, mapped "
            "to absolute /opt/acs-dependencies paths"
        ),
    )
    device_paths: tuple[str, ...] = Field(
        default=(),
        description="Required host device nodes mapped at the same /dev path",
    )

    @model_validator(mode="after")
    def contained_executable(self) -> MVPCapabilityConfig:
        _relative_path(self.executable, label="capability executable")
        if any("\x00" in key or "\x00" in value for key, value in self.environment.items()):
            raise ValueError("capability environment cannot contain NUL bytes")
        reserved = {"HOME", "PATH"}.intersection(self.environment)
        if reserved:
            raise ValueError(
                f"capability environment cannot override sandbox variables: {sorted(reserved)}"
            )
        for destination, source in self.read_only_mounts.items():
            destination_path = Path(destination)
            if (
                not destination_path.is_absolute()
                or not destination_path.is_relative_to("/opt/acs-dependencies")
                or ".." in destination_path.parts
            ):
                raise ValueError(
                    "capability dependency mounts must target /opt/acs-dependencies"
                )
            if not source or "\x00" in source:
                raise ValueError("capability dependency source is invalid")
        for device in self.device_paths:
            device_path = Path(device)
            if (
                not device_path.is_absolute()
                or not device_path.is_relative_to("/dev")
                or ".." in device_path.parts
            ):
                raise ValueError("capability device paths must be contained under /dev")
        return self


def _python_distribution_records(runtime_root: Path) -> tuple[Path, ...]:
    """Find package records in bounded, conventional Python installation roots.

    A recursive walk from a broad capability root such as ``/usr`` can traverse
    unrelated SDKs and data trees on every command. Distribution metadata lives
    at a small set of well-defined depths, so inspect those locations directly.
    """

    patterns = (
        "*.dist-info/RECORD",
        "Lib/site-packages/*.dist-info/RECORD",
        "lib/python*/site-packages/*.dist-info/RECORD",
        "lib/python*/dist-packages/*.dist-info/RECORD",
        "lib64/python*/site-packages/*.dist-info/RECORD",
        "lib64/python*/dist-packages/*.dist-info/RECORD",
        "local/lib/python*/site-packages/*.dist-info/RECORD",
        "local/lib/python*/dist-packages/*.dist-info/RECORD",
    )
    return tuple(sorted({path for pattern in patterns for path in runtime_root.glob(pattern)}))


def _runtime_identity(runtime_root: Path, executable: Path) -> str:
    """Bind the executable and package-manager records without hashing a whole runtime."""

    digest = hashlib.sha256()
    relative = executable.relative_to(runtime_root).as_posix().encode()
    digest.update(relative)
    digest.update(executable.read_bytes())
    metadata = runtime_root / "conda-meta"
    if metadata.is_dir():
        for path in sorted(metadata.glob("*.json")):
            name = path.name.encode()
            digest.update(len(name).to_bytes(8, "big"))
            digest.update(name)
            digest.update(path.read_bytes())
    for path in _python_distribution_records(runtime_root):
        relative_record = path.relative_to(runtime_root).as_posix().encode()
        digest.update(len(relative_record).to_bytes(8, "big"))
        digest.update(relative_record)
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _dependency_identity(root: Path) -> str:
    """Bind package-manager records for one read-only dependency root."""

    digest = hashlib.sha256()
    metadata = root / "conda-meta"
    if metadata.is_dir():
        for path in sorted(metadata.glob("*.json")):
            name = path.name.encode()
            digest.update(len(name).to_bytes(8, "big"))
            digest.update(name)
            digest.update(path.read_bytes())
    else:
        stat = root.stat()
        digest.update(str(stat.st_dev).encode())
        digest.update(str(stat.st_ino).encode())
    return digest.hexdigest()


@dataclass(frozen=True)
class MVPCapabilityInstallation:
    manifest: MVPCapabilityManifest
    runtime_root: Path
    executable: Path
    environment: dict[str, str]
    read_only_mounts: tuple[tuple[Path, str], ...]
    dependency_identities: tuple[tuple[str, str], ...]
    device_paths: tuple[str, ...]
    config_hash: str
    runtime_identity: str

    @property
    def container_root(self) -> str:
        return f"/opt/acs-capabilities/{self.manifest.name}"

    @property
    def container_executable(self) -> str:
        relative = self.executable.relative_to(self.runtime_root).as_posix()
        return f"{self.container_root}/{relative}"

    @property
    def contract_hash(self) -> str:
        canonical = json.dumps(
            {
                "config_hash": self.config_hash,
                "runtime_identity": self.runtime_identity,
                "dependency_identities": self.dependency_identities,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def descriptor(self) -> dict[str, Any]:
        return {
            **self.manifest.model_dump(mode="json"),
            "contract_sha256": self.contract_hash,
            "runtime_identity_sha256": self.runtime_identity,
        }

    def assert_runtime_identity(self) -> None:
        observed = _runtime_identity(self.runtime_root, self.executable)
        if observed != self.runtime_identity:
            raise RuntimeError(
                f"capability {self.manifest.name!r} changed after campaign discovery"
            )
        for source, destination in self.read_only_mounts:
            expected = dict(self.dependency_identities)[destination]
            if _dependency_identity(source) != expected:
                raise RuntimeError(
                    f"capability dependency {destination!r} changed after discovery"
                )

    @classmethod
    def read(cls, path: str | Path) -> MVPCapabilityInstallation:
        config_path = Path(path).resolve()
        raw = config_path.read_bytes()
        config = MVPCapabilityConfig.model_validate_json(raw)
        runtime_root = (config_path.parent / config.runtime_root).resolve()
        if not runtime_root.is_dir():
            raise FileNotFoundError(f"capability runtime is unavailable: {runtime_root}")
        executable = (runtime_root / config.executable).absolute()
        if not executable.is_relative_to(runtime_root):
            raise ValueError("capability executable escapes its runtime")
        if not executable.is_file() or not os.access(executable, os.X_OK):
            raise ValueError("capability executable is unavailable or not executable")
        mounts: list[tuple[Path, str]] = []
        dependency_identities: list[tuple[str, str]] = []
        for destination, relative_source in sorted(config.read_only_mounts.items()):
            source = (config_path.parent / relative_source).resolve()
            if not source.is_dir():
                raise FileNotFoundError(
                    f"capability dependency is unavailable: {source}"
                )
            mounts.append((source, destination))
            dependency_identities.append((destination, _dependency_identity(source)))
        for device in config.device_paths:
            if not Path(device).exists():
                raise FileNotFoundError(
                    f"capability device is unavailable: {device}"
                )
        return cls(
            manifest=config.manifest,
            runtime_root=runtime_root,
            executable=executable,
            environment=dict(config.environment),
            read_only_mounts=tuple(mounts),
            dependency_identities=tuple(dependency_identities),
            device_paths=config.device_paths,
            config_hash=hashlib.sha256(raw).hexdigest(),
            runtime_identity=_runtime_identity(runtime_root, executable),
        )


class MVPCapabilityRegistry:
    """Installed executables that can be mounted one at a time into Bubblewrap."""

    def __init__(self, installed: tuple[MVPCapabilityInstallation, ...] = ()) -> None:
        self._capabilities = {item.manifest.name: item for item in installed}
        if len(self._capabilities) != len(installed):
            raise ValueError("capability names must be unique")

    @classmethod
    def discover(
        cls,
        root: str | Path,
        *,
        ignore_unavailable: bool = False,
    ) -> MVPCapabilityRegistry:
        config_root = Path(root).resolve()
        if not config_root.is_dir():
            return cls()
        installed: list[MVPCapabilityInstallation] = []
        for path in sorted(config_root.glob("*.json")):
            try:
                installed.append(MVPCapabilityInstallation.read(path))
            except FileNotFoundError:
                if not ignore_unavailable:
                    raise
        return cls(tuple(installed))

    def __contains__(self, name: str) -> bool:
        return name in self._capabilities

    def get(self, name: str) -> MVPCapabilityInstallation:
        try:
            return self._capabilities[name]
        except KeyError as error:
            raise ValueError(f"unknown or unavailable capability {name!r}") from error

    @property
    def hashes(self) -> dict[str, str]:
        return {
            name: item.contract_hash
            for name, item in sorted(self._capabilities.items())
        }

    def descriptors(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            item.descriptor()
            for item in sorted(
                self._capabilities.values(), key=lambda value: value.manifest.name
            )
        )


def discover_builtin_mvp_resources(
    project_root: str | Path | None = None,
) -> tuple[MVPSkillCatalog, MVPCapabilityRegistry]:
    """Load repository-shipped skills and any locally installed runtimes."""

    root = (
        Path(project_root).resolve()
        if project_root is not None
        else Path(__file__).resolve().parents[2]
    )
    packaged_skills = Path(__file__).resolve().parent / "builtin_skills"
    skill_root = (
        packaged_skills
        if project_root is None and packaged_skills.is_dir()
        else root / "skills"
    )
    skills = MVPSkillCatalog.discover(skill_root)
    capabilities = MVPCapabilityRegistry.discover(
        root / "capabilities",
        ignore_unavailable=True,
    )
    for descriptor in capabilities.descriptors():
        if descriptor["skill"] not in skills:
            raise ValueError(
                f"capability {descriptor['name']!r} references an unavailable skill"
            )
    return skills, capabilities
