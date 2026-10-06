"""Operator-only preparation of curated native runtimes on the P40 host.

Run as the operator, never from a visitor request. Builds in new object
directories and copies existing CUDA binaries without altering research builds.
"""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path("/opt/simjecture-public/tools")
FLASH = Path("/opt/simjecture/reconnection-20261002/FLASH4.8")
WARPX = Path("/opt/simote/radiation-production-features-20260930/warpx")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    build_bin = ROOT / "build-bin"
    build_bin.mkdir(exist_ok=True)
    if not (build_bin / "python").exists():
        (build_bin / "python").symlink_to("/usr/bin/python3")
    build_environment = dict(
        os.environ,
        PATH=str(build_bin) + ":" + os.environ["PATH"],
        SETUP_SHORTCUTS=str(FLASH / "bin/setup_shortcuts.txt"),
    )
    records = {}
    for dimension in ("1d", "2d", "rz", "3d"):
        source = WARPX / f"build/features-cuda/bin/warpx.{dimension}.MPI.CUDA.DP.PDP"
        target = ROOT / f"warpx-{dimension}-cuda"
        if not target.exists():
            shutil.copy2(source, target)
            # Only debug symbols in the NEW deployed copy are removed.
            subprocess.run(["strip", "--strip-debug", str(target)], check=True)
        target.chmod(0o755)
        records[f"warpx-{dimension}-cuda"] = {
            "original": str(source),
            "original_sha256": digest(source),
            "deployed": str(target),
            "sha256": digest(target),
            "source_revision": (
                subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WARPX, text=True).strip()
                if (WARPX / ".git").exists()
                else "Copied source tree; binary identity retained"
            ),
        }
        print("Prepared", target, flush=True)

    for identifier, problem, dimension, geometry, solver in (
        ("flash-1d", "Sod", "1d", "cartesian", "+uhd"),
        ("flash-2d", "magnetoHD/OrszagTang", "2d", "cartesian", "+usm"),
        ("flash-rz", "Sedov", "2d", "cylindrical", "+uhd"),
    ):
        obj = "Public-" + identifier + "-20261006"
        target = ROOT / identifier
        command = [
            "/usr/bin/python3",
            str(FLASH / "bin/setup.py"),
            problem,
            "-auto",
            "-opt",
            "-" + dimension,
            "+" + geometry,
            "+ug",
            "-nofbs",
            solver,
            "+hdf5typeio",
            "parallelIO=True",
            "-site=UU-DESKTOP-NVML34D",
            "-objdir=" + obj,
        ]
        started = time.time()
        if not target.exists():
            with (ROOT / (identifier + ".build.log")).open("w") as log:
                subprocess.run(
                    command,
                    cwd=FLASH,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    env=build_environment,
                )
                subprocess.run(
                    ["make", "-j8"],
                    cwd=FLASH / obj,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    env=build_environment,
                )
            shutil.copy2(FLASH / obj / "flash4", target)
            subprocess.run(["strip", "--strip-debug", str(target)], check=True)
        target.chmod(0o755)
        provenance = ROOT / (identifier + "-provenance")
        provenance.mkdir(exist_ok=True)
        for name in ("setup_call", "setup_units", "setup_params", "Makefile.h"):
            shutil.copy2(FLASH / obj / name, provenance / name)
        records[identifier] = {
            "deployed": str(target),
            "sha256": digest(target),
            "application": problem,
            "geometry": geometry,
            "setup": command,
            "build_seconds": time.time() - started,
        }
        print("Built", target, flush=True)
    (ROOT / "build-records.json").write_text(json.dumps(records, indent=2) + "\n")
    for path in ROOT.rglob("*"):
        if path.is_file() and not os.access(path, os.X_OK):
            path.chmod(0o644)


if __name__ == "__main__":
    main()
