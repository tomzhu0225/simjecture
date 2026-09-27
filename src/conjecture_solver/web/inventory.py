"""Discover existing capability descriptors without rebuilding or renaming instruments."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

from ..mvp_skills import MVPCapabilityConfig

_SYSTEM_CACHE = {}


def discover_system_warpx(project_root, *, home=None):
    """Bounded discovery of executable builds and registered Conda environments.

    These are real installations, but are not automatically reclassified as a
    release-pinned Simjecture evidence instrument.
    """
    home = Path(home or Path.home())
    root = Path(project_root).resolve()
    key = (str(root), str(home))
    cached = _SYSTEM_CACHE.get(key)
    if cached and time.monotonic() - cached[0] < 30:
        return cached[1]
    found, seen = [], set()
    source_roots = {root.parent, home / "src"}
    for base in source_roots:
        for repository in sorted(base.glob("warpx*"))[:80]:
            for build in sorted(repository.glob("build*"))[:80]:
                cache = build / "CMakeCache.txt"
                if not cache.is_file():
                    continue
                text = cache.read_text(errors="replace")[: 1024 * 1024]
                compute = re.search(r"^WarpX_COMPUTE[^=]*=(.*)$", text, re.M)
                compute = compute.group(1).strip() if compute else ""
                if compute not in {"CUDA", "HIP", "SYCL", "OMP", "NOACC"}:
                    continue
                profile = "warpx-cuda" if compute in {"CUDA", "HIP", "SYCL"} else "warpx-cpu"
                python_flag = re.search(r"^WarpX_PYTHON[^=]*=(.*)$", text, re.M)
                python_bindings = (
                    python_flag.group(1).strip().upper() in {"ON", "TRUE", "1"}
                    if python_flag
                    else None
                )
                openpmd_flag = re.search(r"^WarpX_OPENPMD[^=]*=(.*)$", text, re.M)
                output_formats = ["AMReX plotfile"]
                if openpmd_flag and openpmd_flag.group(1).strip().upper() in {"ON", "TRUE", "1"}:
                    output_formats.append("openPMD")
                for binary in sorted((build / "bin").glob("warpx*")):
                    if not binary.is_file() or not os.access(binary, os.X_OK):
                        continue
                    actual = str(binary.resolve())
                    if actual in seen:
                        continue
                    seen.add(actual)
                    found.append(
                        dict(
                            id="system-" + hashlib.sha256(actual.encode()).hexdigest()[:12],
                            name=binary.name,
                            label=f"{binary.name} · {compute} · {build.name}",
                            version="local build",
                            description=f"Local {compute} build in {repository.name}",
                            runtime=str(build),
                            executable=str(binary),
                            profile=profile,
                            path=None,
                            registered=False,
                            compute=compute,
                            interface="native-input-file",
                            python_bindings=python_bindings,
                            output_formats=output_formats,
                        )
                    )
    prefixes = {home / "miniforge3", home / "miniconda3", home / "mambaforge"}
    environments = home / ".conda/environments.txt"
    if environments.is_file():
        prefixes.update(
            Path(p).expanduser() for p in environments.read_text().splitlines() if p.strip()
        )
    for base in tuple(prefixes):
        if (base / "envs").is_dir():
            prefixes.update((base / "envs").iterdir())
    for prefix in sorted(prefixes):
        metadata = list((prefix / "conda-meta").glob("warpx-*.json"))
        if not metadata or not (prefix / "bin/python").is_file():
            continue
        for path in metadata:
            try:
                package = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            flavor = str(package.get("build", ""))
            profile = (
                "warpx-cuda" if any(x in flavor.lower() for x in ("cuda", "gpu")) else "warpx-cpu"
            )
            found.append(
                dict(
                    id="system-" + hashlib.sha256(str(prefix).encode()).hexdigest()[:12],
                    name="WarpX Conda environment",
                    label=f"WarpX {package.get('version', '')} · {prefix.name}",
                    version=package.get("version", "unknown"),
                    description="Installed Conda WarpX package",
                    runtime=str(prefix),
                    executable=str(prefix / "bin/python"),
                    profile=profile,
                    path=None,
                    registered=False,
                    compute=flavor,
                )
            )
    _SYSTEM_CACHE[key] = (time.monotonic(), found)
    return found


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
