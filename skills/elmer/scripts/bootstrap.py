"""Bundle an operator-supplied Elmer installation without changing its source."""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import venv
from pathlib import Path

REQUIREMENTS = [
    "numpy==2.5.1",
    "scipy==1.17.1",
    "meshio==5.3.5",
    "gmsh==4.15.2",
    "pyvista==0.49.1",
    "matplotlib==3.11.1",
]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bundle_libraries(binary, destination):
    """Copy resolved non-system dependencies, preserving their SONAME filenames."""
    environment = os.environ.copy()
    home = destination.parent
    environment["LD_LIBRARY_PATH"] = ":".join(
        [
            str(home / "lib/elmersolver"),
            str(home / "share/elmersolver/lib"),
            environment.get("LD_LIBRARY_PATH", ""),
        ]
    )
    result = subprocess.run(
        ["ldd", str(binary)], text=True, capture_output=True, check=True, env=environment
    )
    if "not found" in result.stdout:
        raise ValueError(f"Unresolved dependencies for {binary}: {result.stdout}")
    for name, raw in re.findall(r"^\s*(\S+) => (/\S+)", result.stdout, re.M):
        path = Path(raw).resolve()
        if path.is_relative_to("/usr/lib") or path.is_relative_to("/lib"):
            continue
        target = destination / name
        if target.exists() and sha(target) != sha(path):
            raise ValueError(f"Conflicting library {name}")
        shutil.copy2(path, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    if sys.version_info < (3, 12) or sys.platform != "linux":
        parser.error("This bundle requires Linux and Python 3.12+")
    source, prefix = args.source.resolve(), args.prefix.resolve()
    if source == prefix or source.is_relative_to(prefix) or prefix.is_relative_to(source):
        parser.error("Source and runtime must be separate directories")
    for name in (
        "bin/ElmerGrid",
        "lib/elmersolver/libelmersolver.so",
        "share/elmersolver/lib/elements.def",
    ):
        if not (source / name).is_file():
            parser.error(f"Missing prebuilt Elmer file: {name}")
    if not any((source / "bin" / n).is_file() for n in ("ElmerSolver", "ElmerSolver_mpi")):
        parser.error("ElmerSolver executable missing")
    marker = prefix.parent / "install-state" / f"{prefix.name}.json"
    if prefix.exists() and not marker.is_file():
        parser.error(f"Refusing unmanaged runtime: {prefix}")
    if marker.is_file() and json.loads(marker.read_text()).get("profile") != "elmer":
        parser.error("Runtime belongs to another installer")
    package = args.project_root / "src/conjecture_solver"
    if not package.is_dir():
        spec = importlib.util.find_spec("conjecture_solver")
        if spec is None:
            parser.error("Cannot locate Simjecture package")
        package = Path(spec.origin).parent
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"profile": "elmer", "ready": False}))
    venv.EnvBuilder(with_pip=True, symlinks=False, clear=True).create(prefix)
    python = prefix / "bin/python"
    command = (
        [shutil.which("uv"), "pip", "install", "--python", str(python)]
        if shutil.which("uv")
        else [str(python), "-m", "pip", "install"]
    )
    subprocess.run(command + REQUIREMENTS, check=True)
    stdlib = Path(sysconfig.get_path("stdlib"))
    shutil.copytree(
        stdlib,
        prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "site-packages", "dist-packages", "__pycache__", "EXTERNALLY-MANAGED"
        ),
    )
    for library in (Path(sys.base_prefix) / "lib").glob("libpython*.so*"):
        shutil.copy2(library, prefix / "lib" / library.name)
    home = prefix / "elmer"
    if home.exists():
        shutil.rmtree(home)
    shutil.copytree(source, home, symlinks=False)
    deps = home / "deps"
    deps.mkdir(exist_ok=True)
    for binary in [
        home / "bin/ElmerGrid",
        *home.glob("bin/ElmerSolver*"),
        *home.glob("lib/elmersolver/*.so"),
        *home.glob("share/elmersolver/lib/*.so"),
    ]:
        if binary.is_file():
            bundle_libraries(binary, deps)
    # Gmsh's wheel needs GLU even in headless mode. An operator can supply its
    # existing local library through LD_LIBRARY_PATH; host /usr libraries stay host-bound.
    gmsh_lib = next((prefix / "lib").glob("libgmsh.so*"))
    bundle_libraries(gmsh_lib, deps)
    share = prefix / "share"
    share.mkdir(exist_ok=True)
    for name in ("elmer.py", "elmer_em.py", "elmer_em_case.sif"):
        shutil.copy2(package / name, share / name)
    (share / "requirements.txt").write_text("\n".join(REQUIREMENTS) + "\n")
    env = os.environ | {"SIMJECTURE_ELMER_HOME": str(home), "LD_LIBRARY_PATH": str(deps)}
    # No build record exists yet; runtime() computes the effective file identities.
    record_path = share / "build-record.json"
    record_path.unlink(missing_ok=True)
    identity = json.loads(
        subprocess.check_output(
            [
                str(python),
                "-c",
                "import sys,json;sys.path.insert(0,sys.argv[1]);"
                "import elmer;print(json.dumps(elmer.runtime()[3]))",
                str(share),
            ],
            env=env,
            text=True,
        )
    )
    record = {
        "profile": "elmer",
        "version": "0.1",
        "source_installation": str(source),
        "elmer_identity": identity,
        "source_policy": "Operator-supplied build; no source modifications or automatic patches.",
        "driver_sha256": sha(share / "elmer.py"),
        "packages": json.loads(
            subprocess.check_output([str(python), "-m", "pip", "list", "--format=json"])
        ),
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n")
    marker.write_text(json.dumps({"profile": "elmer", "ready": True}))


if __name__ == "__main__":
    main()
