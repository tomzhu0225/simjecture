"""Build matching Python/DSH artifacts and a Linux launch archive."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    package = json.loads((ROOT / "integrations/dsh/package.json").read_text())
    if package["version"] != version:
        raise SystemExit("Python and DSH bundle versions must match")
    output = ROOT / "artifacts" / "releases" / f"v{version}"
    output.mkdir(parents=True, exist_ok=True)
    # Never package a previously launched directory: it may contain credentials,
    # environments, or scientific records. Every build starts from empty staging.
    with tempfile.TemporaryDirectory(prefix="simjecture-release-") as staging:
        launch = Path(staging) / f"simjecture-{version}-linux"
        packages = launch / "packages"
        packages.mkdir(parents=True)
        subprocess.run(["uv", "build", "--out-dir", str(packages)], cwd=ROOT, check=True)
        subprocess.run(
            ["npm", "pack", "./integrations/dsh", "--pack-destination", str(packages)],
            cwd=ROOT,
            check=True,
        )
        for source in (ROOT / "packaging/launch").iterdir():
            shutil.copy2(source, launch / source.name)
        for name in ("CHANGELOG.md", "LICENSE", "CITATION.cff"):
            shutil.copy2(ROOT / name, launch / name)
        (launch / "VERSION").write_text(version + "\n")
        for name in ("setup.sh", "launch.sh"):
            (launch / name).chmod(0o755)
            subprocess.run(["bash", "-n", str(launch / name)], check=True)
        paths = sorted(path for path in launch.rglob("*") if path.is_file())
        (launch / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(launch)}\n"
                for path in paths
            )
        )
        archive = output / f"simjecture-{version}-linux.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            stream.add(launch, arcname=launch.name)
        (output / "packages").mkdir(exist_ok=True)
        for artifact in packages.iterdir():
            shutil.copy2(artifact, output / "packages" / artifact.name)
        (output / "SHA256SUMS").write_text(
            f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n"
        )
        print(archive)


if __name__ == "__main__":
    main()
