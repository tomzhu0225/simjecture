"""Discover existing capability descriptors without rebuilding or renaming instruments."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ..mvp_skills import MVPCapabilityConfig


def discover_installed(project_root):
    root = Path(project_root)
    paths = set((root / "capabilities").glob("*.json"))
    # Existing local research installations use these directories. Do not scan
    # transcripts, arbitrary home directories, or reinterpret a binary as a new solver.
    for pattern in (
        ".private/*/capabilities*/*.json",
        ".runtime/*/capabilities/*.json",
        "artifacts/projects/*/capabilities*/*.json",
    ):
        paths.update(root.glob(pattern))
    configured = os.environ.get("SIMJECTURE_DEFAULT_CAPABILITIES")
    if configured:
        paths.update(Path(configured).expanduser().glob("*.json"))
    found = {}
    for path in sorted(paths):
        try:
            resolved = path.resolve()
            config = MVPCapabilityConfig.model_validate(json.loads(resolved.read_text()))
            runtime = (resolved.parent / config.runtime_root).resolve()
            executable = runtime / config.executable
            if not executable.is_file() or not os.access(executable, os.X_OK):
                continue
            identity = (str(runtime), config.manifest.name)
            found.setdefault(
                identity,
                dict(
                    id="installed-" + hashlib.sha256(str(resolved).encode()).hexdigest()[:12],
                    name=config.manifest.name,
                    version=config.manifest.version,
                    description=config.manifest.description,
                    path=str(resolved),
                    runtime=str(runtime),
                    label=f"{config.manifest.name} · {config.manifest.version}",
                ),
            )
        except (OSError, ValueError):
            continue
    return list(found.values())
