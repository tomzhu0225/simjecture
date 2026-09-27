"""Build a versioned, credential-free source bundle for the one-command installer."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import shutil
import subprocess
import tarfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = {"src", "skills", "capabilities", "environments", "integrations", "scripts"}
FILES = {"pyproject.toml", "uv.lock", "README.md", "LICENSE"}
FORBIDDEN = {".private", ".runtime", ".venv", "__pycache__", "node_modules", ".env"}


def build(output):
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    script = (ROOT / "scripts/install-workspace.sh").read_text()
    if f"SIMJECTURE_VERSION={version}\n" not in script:
        raise ValueError("Installer and package versions differ")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"simjecture-{version}-workspace.tar.gz"
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    epoch = int(
        os.environ.get("SOURCE_DATE_EPOCH")
        or subprocess.check_output(["git", "log", "-1", "--format=%ct"], cwd=ROOT)
    )
    count = 0
    with (
        archive.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=epoch) as zipped,
        tarfile.open(fileobj=zipped, mode="w|") as tar,
    ):
        for name in sorted(filter(None, tracked)):
            relative = Path(name)
            if relative.parts[0] not in PREFIXES and name not in FILES:
                continue
            if FORBIDDEN.intersection(relative.parts):
                raise ValueError(f"Unexpected private/generated source: {name}")
            path = ROOT / relative
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Expected regular source file: {name}")
            body = path.read_bytes()
            info = tarfile.TarInfo(f"simjecture-{version}/{name}")
            info.size = len(body)
            info.mtime = epoch
            info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
            tar.addfile(info, io.BytesIO(body))
            count += 1
    shutil.copyfile(ROOT / "scripts/install-workspace.sh", output / "install.sh")
    checksums = []
    for path in sorted(output.iterdir()):
        if path.is_file() and (path.name == "install.sh" or path.suffix in {".gz", ".whl"}):
            checksums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    print(f"Bundled {count} tracked source files: {archive} ({archive.stat().st_size:,} bytes)")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    build(parser.parse_args().output.resolve())
