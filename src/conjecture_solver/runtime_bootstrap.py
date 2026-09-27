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
    print("Package manager verified. Preparing WarpX CPU environment…", flush=True)
    return str(target)
