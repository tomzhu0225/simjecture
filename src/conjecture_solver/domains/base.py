"""Stable boundary between the domain-neutral CLI and scientific domains."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import Field

from ..models import PropositionClass, StrictModel


class DomainPluginMetadata(StrictModel):
    """Machine-readable declaration of one installed scientific domain."""

    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    hypothesis_schema: str = Field(min_length=1)
    package_schema: str = Field(min_length=1)
    model_families: tuple[str, ...] = Field(min_length=1)
    proposition_classes: tuple[PropositionClass, ...] = Field(min_length=1)
    operations: tuple[Literal["template", "solve", "evolve", "diagnose"], ...] = (
        "template",
        "solve",
    )


class DomainRunSummary(StrictModel):
    """Domain-independent result returned to the command-line facade."""

    domain: str
    campaign_id: str
    disposition: str
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_path: str
    exit_code: int = Field(default=0, ge=0, le=255)
    metrics: dict[str, str | int | float | bool] = Field(default_factory=dict)


class DomainTemplateSummary(StrictModel):
    domain: str
    template_path: str
    metrics: dict[str, str | int | float | bool] = Field(default_factory=dict)


class DomainEvolutionSummary(StrictModel):
    """Domain-independent summary of one bounded hypothesis-evolution cycle."""

    domain: str
    campaign_id: str
    disposition: str
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_path: str
    exit_code: int = Field(default=0, ge=0, le=255)
    metrics: dict[str, str | int | float | bool] = Field(default_factory=dict)


class DomainDiagnosisSummary(StrictModel):
    """Domain-independent summary of one read-only package diagnosis."""

    domain: str
    source_package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnosis_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    diagnosis_path: str
    status: str
    metrics: dict[str, str | int | float | bool] = Field(default_factory=dict)


@runtime_checkable
class VerifiedPackage(Protocol):
    campaign_id: str
    package_hash: str


@runtime_checkable
class DomainPlugin(Protocol):
    """Required interface for an installed autonomous-solve domain."""

    metadata: DomainPluginMetadata

    def configure_solve_parser(self, parser: argparse.ArgumentParser) -> None: ...

    def configure_template_parser(self, parser: argparse.ArgumentParser) -> None: ...

    def solve(self, args: argparse.Namespace) -> DomainRunSummary: ...

    def write_template(self, args: argparse.Namespace) -> DomainTemplateSummary: ...

    def recognizes_package(self, payload: dict[str, Any]) -> bool: ...

    def read_verified_package(self, path: str | Path) -> VerifiedPackage: ...


@runtime_checkable
class EvolutionDomainPlugin(Protocol):
    """Optional capability for domains supporting bounded hypothesis evolution."""

    metadata: DomainPluginMetadata

    def configure_evolve_parser(self, parser: argparse.ArgumentParser) -> None: ...

    def evolve(self, args: argparse.Namespace) -> DomainEvolutionSummary: ...


@runtime_checkable
class DiagnosisDomainPlugin(Protocol):
    """Optional capability for read-only diagnosis of verified domain packages."""

    metadata: DomainPluginMetadata

    def configure_diagnose_parser(self, parser: argparse.ArgumentParser) -> None: ...

    def diagnose(self, args: argparse.Namespace) -> DomainDiagnosisSummary: ...


@dataclass(frozen=True)
class DomainPluginRegistry:
    """Immutable, validated registry used by every generic public command."""

    _plugins: tuple[DomainPlugin, ...]

    def __post_init__(self) -> None:
        names = [plugin.metadata.name for plugin in self._plugins]
        if len(names) != len(set(names)):
            raise ValueError("domain plugin names must be unique")

    @property
    def plugins(self) -> tuple[DomainPlugin, ...]:
        return tuple(sorted(self._plugins, key=lambda plugin: plugin.metadata.name))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(plugin.metadata.name for plugin in self.plugins)

    def get(self, name: str) -> DomainPlugin:
        for plugin in self._plugins:
            if plugin.metadata.name == name:
                return plugin
        raise ValueError(f"unknown domain plugin {name!r}; installed: {', '.join(self.names)}")

    def recognize_package(self, payload: dict[str, Any]) -> DomainPlugin | None:
        matches = [plugin for plugin in self._plugins if plugin.recognizes_package(payload)]
        if len(matches) > 1:
            names = ", ".join(plugin.metadata.name for plugin in matches)
            raise ValueError(f"package ambiguously matches domain plugins: {names}")
        return matches[0] if matches else None

    @property
    def evolution_plugins(self) -> tuple[EvolutionDomainPlugin, ...]:
        return tuple(plugin for plugin in self.plugins if isinstance(plugin, EvolutionDomainPlugin))

    @property
    def diagnosis_plugins(self) -> tuple[DiagnosisDomainPlugin, ...]:
        return tuple(plugin for plugin in self.plugins if isinstance(plugin, DiagnosisDomainPlugin))
