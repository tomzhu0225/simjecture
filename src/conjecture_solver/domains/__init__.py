"""Installed scientific-domain plugins."""

from __future__ import annotations

from functools import lru_cache

from .base import (
    DiagnosisDomainPlugin,
    DomainDiagnosisSummary,
    DomainEvolutionSummary,
    DomainPlugin,
    DomainPluginMetadata,
    DomainPluginRegistry,
    DomainRunSummary,
    DomainTemplateSummary,
    EvolutionDomainPlugin,
)


@lru_cache(maxsize=1)
def installed_domain_plugins() -> DomainPluginRegistry:
    """Load built-ins lazily so the core has no domain-specific imports."""

    from .kinetic_sufficiency import KineticSufficiencyDomainPlugin

    return DomainPluginRegistry((KineticSufficiencyDomainPlugin(),))


__all__ = [
    "DomainPlugin",
    "DomainEvolutionSummary",
    "DomainDiagnosisSummary",
    "DomainPluginMetadata",
    "DomainPluginRegistry",
    "DomainRunSummary",
    "DomainTemplateSummary",
    "EvolutionDomainPlugin",
    "DiagnosisDomainPlugin",
    "installed_domain_plugins",
]
