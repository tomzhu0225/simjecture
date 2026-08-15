"""Validated starting points for guided MVP commissioning campaigns."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel


def _workspace_relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"guided commissioning path must be workspace-relative: {value!r}")
    if path.as_posix() != value:
        raise ValueError(f"guided commissioning path must be canonical: {value!r}")
    return path.as_posix()


class MVPGuidedCommissioningSpec(StrictModel):
    """Operator-authored manifest for one known-runnable starting point.

    The package deliberately says only what was run and where its compact validation
    record lives. It does not qualify the supplied output as campaign evidence.
    """

    schema_version: Literal["0.1.0"] = "0.1.0"
    name: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    description: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    program_path: str = Field(min_length=1)
    validated_argv: tuple[str, ...] = Field(min_length=1)
    validation_summary_path: str = Field(min_length=1)
    operator_validation: str = Field(min_length=1)
    limitations: tuple[str, ...] = ()
    files: tuple[str, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def paths_and_command_are_self_contained(self) -> MVPGuidedCommissioningSpec:
        normalized_files = tuple(_workspace_relative_path(path) for path in self.files)
        if len(set(normalized_files)) != len(normalized_files):
            raise ValueError("guided commissioning files must be unique")
        program_path = _workspace_relative_path(self.program_path)
        summary_path = _workspace_relative_path(self.validation_summary_path)
        if program_path not in normalized_files:
            raise ValueError("program_path must be listed in files")
        if summary_path not in normalized_files:
            raise ValueError("validation_summary_path must be listed in files")
        if self.validated_argv[0] != program_path:
            raise ValueError("validated_argv[0] must equal program_path")
        if any(not argument for argument in self.validated_argv):
            raise ValueError("validated_argv arguments cannot be empty")
        return self


class MVPGuidedCommissioningFile(StrictModel):
    path: str = Field(min_length=1)
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class MVPGuidedCommissioningPackage:
    """Loaded, content-addressed guided commissioning package."""

    manifest_path: Path
    spec: MVPGuidedCommissioningSpec
    file_records: tuple[MVPGuidedCommissioningFile, ...]
    package_sha256: str

    @classmethod
    def read(cls, manifest_path: str | Path) -> MVPGuidedCommissioningPackage:
        requested_manifest = Path(manifest_path)
        if requested_manifest.is_symlink():
            raise ValueError("guided commissioning manifest must be a regular file")
        manifest = requested_manifest.resolve()
        if not manifest.is_file():
            raise ValueError("guided commissioning manifest must be a regular file")
        spec = MVPGuidedCommissioningSpec.model_validate_json(manifest.read_text())
        root = manifest.parent
        digest = hashlib.sha256()
        canonical_spec = json.dumps(
            spec.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        digest.update(len(canonical_spec).to_bytes(8, "big"))
        digest.update(canonical_spec)
        records: list[MVPGuidedCommissioningFile] = []
        for relative in sorted(spec.files):
            normalized = _workspace_relative_path(relative)
            requested = root / normalized
            path = requested.resolve()
            if requested.is_symlink() or not path.is_relative_to(root) or not path.is_file():
                raise ValueError(
                    f"guided commissioning file is missing, irregular, or escapes package: "
                    f"{relative!r}"
                )
            encoded = path.read_bytes()
            sha256 = hashlib.sha256(encoded).hexdigest()
            records.append(
                MVPGuidedCommissioningFile(
                    path=normalized,
                    bytes=len(encoded),
                    sha256=sha256,
                )
            )
            name = normalized.encode()
            digest.update(len(name).to_bytes(8, "big"))
            digest.update(name)
            digest.update(len(encoded).to_bytes(8, "big"))
            digest.update(encoded)
        return cls(
            manifest_path=manifest,
            spec=spec,
            file_records=tuple(records),
            package_sha256=digest.hexdigest(),
        )

    @property
    def root(self) -> Path:
        return self.manifest_path.parent

    def read_file(self, relative: str) -> bytes:
        normalized = _workspace_relative_path(relative)
        record = next(
            (item for item in self.file_records if item.path == normalized),
            None,
        )
        if record is None:
            raise ValueError(f"file is not declared by guided commissioning: {relative!r}")
        requested = self.root / normalized
        path = requested.resolve()
        if requested.is_symlink() or not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError(f"guided commissioning file identity changed: {relative!r}")
        encoded = path.read_bytes()
        if len(encoded) != record.bytes or hashlib.sha256(encoded).hexdigest() != record.sha256:
            raise ValueError(f"guided commissioning file identity changed: {relative!r}")
        return encoded

    def assert_identity(self) -> None:
        current = self.read(self.manifest_path)
        if current.package_sha256 != self.package_sha256:
            raise ValueError("guided commissioning package identity changed")

    def descriptor(self) -> dict[str, Any]:
        return {
            "available": True,
            "schema_version": self.spec.schema_version,
            "name": self.spec.name,
            "description": self.spec.description,
            "capability": self.spec.capability,
            "program_path": self.spec.program_path,
            "validated_argv": list(self.spec.validated_argv),
            "validation_summary_path": self.spec.validation_summary_path,
            "operator_validation": self.spec.operator_validation,
            "limitations": list(self.spec.limitations),
            "files": [item.model_dump(mode="json") for item in self.file_records],
            "package_sha256": self.package_sha256,
            "scientific_evidence_eligible": False,
            "policy": "operator_validated_starting_point_not_campaign_evidence",
        }
