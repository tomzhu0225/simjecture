"""Checksummed, project-local bootstrap for optional runtime provisioning."""

import hashlib
import os
import platform
import tempfile
import urllib.request
from pathlib import Path

MICROMAMBA_VERSION = "2.9.0-0"
# Official mamba-org/micromamba-releases GitHub release asset digests.
MICROMAMBA_ASSETS = {
    "x86_64": ("linux-64", "366cd9cd8be14df1ab8ed50352a82111082a36686b2d389fdb79a92c3fafb3e3"),
    "aarch64": (
        "linux-aarch64",
        "9f93b974adcb4d166996af969b6cd371287d1a3e52733704727884d9b74cb7a7",
    ),
}


def ensure_micromamba(runtime_root: Path, *, dry_run=False) -> str:
    if platform.system() != "Linux" or platform.machine() not in MICROMAMBA_ASSETS:
        raise ValueError(
            "Automatic Micromamba setup supports Linux x86_64 and aarch64; "
            "supply an environment manager on this platform."
        )
    asset, checksum = MICROMAMBA_ASSETS[platform.machine()]
    target = runtime_root / "bootstrap" / f"micromamba-{MICROMAMBA_VERSION}-{asset}"
    if dry_run:
        return str(target)
    if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == checksum:
        target.chmod(0o755)
        return str(target)
    url = f"https://github.com/mamba-org/micromamba-releases/releases/download/{MICROMAMBA_VERSION}/micromamba-{asset}"
    print(f"Preparing package manager: downloading Micromamba {MICROMAMBA_VERSION}…", flush=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        digest = hashlib.sha256()
        with (
            urllib.request.urlopen(url, timeout=90) as response,
            tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output,
        ):
            temporary = Path(output.name)
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 64 * 1024**2:
                    raise ValueError("Micromamba download exceeded 64 MiB")
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest() != checksum:
            raise ValueError("Micromamba checksum mismatch; the downloaded binary was not executed")
        temporary.chmod(0o755)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("Package manager verified.", flush=True)
    return str(target)


# Package files are shared through Micromamba's cache; separate environments
# retain independent ABI constraints without downloading identical packages twice.
RUNTIME_PACKAGES = {
    "warp-lbm": ["python=3.12", "pip"],
    "iter-pack": ["python=3.12", "pip", "git"],
    "cuda-toolkit": [
        "cuda-nvcc=12.4",
        "cuda-cudart-dev=12.4",
        "libcublas-dev=12.4",
        "libcurand-dev=10.3.5.147",
        "libcusparse-dev=12.3.1.170",
        "cuda-profiler-api=12.4",
        "cuda-nvtx-dev=12.4",
        "gcc_linux-64=12.4",
        "gxx_linux-64=12.4",
    ],
    "cuda-io": ["hdf5=1.14.6=nompi_*", "cmake", "ninja", "make", "pkg-config"],
    "cuda-python": [
        "python=3.12",
        "cupy",
        "cuda-version=12.4",
        "pip",
        "git",
        "setuptools",
        "wheel",
        "packaging",
        "picmistandard=0.34.0",
        "periodictable",
        "openpmd-api",
        "matplotlib-base",
        "numpy",
    ],
    "singularity-eos": ["python=3.11", "git", "gxx_linux-64=12", "make"],
    "m-aneos": ["python=3.11", "git", "gfortran_linux-64=12", "make"],
    "optab": [
        "python=3.11",
        "pip",
        "git",
        "make",
        "gfortran_linux-64=12",
        "hdf5=1.14.*=mpi_openmpi_*",
        "openmpi",
        "numpy<2",
        "h5py",
        "requests",
        "wget",
        "curl",
        "tqdm",
    ],
    "atomec": [
        "python=3.10",
        "pip",
        "git",
        "libxc=6.2.2",
        "pylibxc=6.2.2",
        "numpy=1.26",
        "scipy=1.11",
        "pandas<2",
        "sqlalchemy<2",
    ],
    "flash": [
        "python=3.11",
        "pip",
        "git",
        "make",
        "gfortran_linux-64=12",
        "gcc_linux-64=12",
        "hdf5=1.14.*=mpi_openmpi_*",
        "openmpi",
        "numpy<2",
        "h5py",
    ],
}


def prepare_runtime_environment(profile: str, prefix: Path) -> None:
    import json
    import subprocess

    packages = RUNTIME_PACKAGES[profile]
    marker = prefix.parent / "install-state" / f"{prefix.name}.json"
    if prefix.exists() and not marker.is_file():
        raise ValueError(f"Refusing to replace unmanaged directory {prefix}")
    if marker.is_file():
        record = json.loads(marker.read_text())
        if record.get("profile") != profile:
            raise ValueError(f"Runtime at {prefix} belongs to another tool")
        if (
            record.get("ready")
            and record.get("packages") == packages
            and (prefix / "conda-meta/history").is_file()
        ):
            print(f"Reusing managed {profile} dependencies at {prefix}", flush=True)
            return
    manager = ensure_micromamba(prefix.parent)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"profile": profile, "packages": packages}, indent=2))
    environment = os.environ.copy()
    environment["MAMBA_ROOT_PREFIX"] = str(prefix.parent / "package-cache")
    print(
        f"Installing {profile} prerequisites into {prefix} (no administrator required)…", flush=True
    )
    subprocess.run(
        [
            manager,
            "install" if (prefix / "conda-meta/history").exists() else "create",
            "--yes",
            "--prefix",
            str(prefix),
            "--override-channels",
            "--channel",
            "conda-forge",
            "--strict-channel-priority",
            *packages,
        ],
        env=environment,
        cwd=prefix.parent,
        check=True,
    )

    marker.write_text(
        json.dumps({"profile": profile, "packages": packages, "ready": True}, indent=2)
    )
