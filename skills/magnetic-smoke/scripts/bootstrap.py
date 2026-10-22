"""Prepare the optional prescribed-current magnetic screening runtime."""

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import sysconfig
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    if args.source:
        parser.error("This capability uses its bundled driver; --source is unsupported")
    if sys.version_info < (3, 12):
        parser.error("Use Python 3.12+ via SIMJECTURE_BOOTSTRAP_PYTHON for this optional runtime")
    prefix = args.prefix.resolve()
    marker = prefix.parent / "install-state" / f"{prefix.name}.json"
    if prefix.exists() and not marker.is_file():
        parser.error(f"Refusing to modify unmanaged runtime: {prefix}")
    if marker.is_file() and json.loads(marker.read_text()).get("profile") != "magnetic-smoke":
        parser.error("Runtime belongs to a different installer")
    package = args.project_root / "src/conjecture_solver"
    if not package.is_dir():
        spec = importlib.util.find_spec("conjecture_solver")
        if spec is None:
            parser.error("Cannot find the installed Simjecture package")
        package = Path(spec.origin).parent
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"profile": "magnetic-smoke", "ready": False}))
    venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    python = str(prefix / "bin/python")
    command = (
        [shutil.which("uv"), "pip", "install", "--python", python]
        if shutil.which("uv")
        else [python, "-m", "pip", "install"]
    )
    subprocess.run(command + ["numpy==2.5.1"], check=True)
    # A venv normally refers back to its host interpreter's standard library.
    # That host path is absent inside the capability's Bubblewrap namespace,
    # particularly for uv-managed Python. Keep the required files in the runtime
    # and use the descriptor's PYTHONHOME to locate them after mounting.
    stdlib = Path(sysconfig.get_path("stdlib"))
    relative_stdlib = Path("lib") / f"python{sys.version_info.major}.{sys.version_info.minor}"
    shutil.copytree(
        stdlib,
        prefix / relative_stdlib,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("site-packages", "dist-packages", "__pycache__"),
    )
    for library in (Path(sys.base_prefix) / "lib").glob("libpython*.so*"):
        shutil.copy2(library, prefix / "lib" / library.name)
    share = prefix / "share"
    share.mkdir(exist_ok=True)
    shutil.copy2(package / "magnetic_smoke.py", share / "magnetic_smoke.py")
    (share / "requirements.txt").write_text("numpy==2.5.1\n")
    record = {
        "profile": "magnetic-smoke",
        "version": "1.0",
        "driver_sha256": hashlib.sha256((share / "magnetic_smoke.py").read_bytes()).hexdigest(),
        "python_version": subprocess.check_output([python, "--version"], text=True).strip(),
        "packages": json.loads(
            subprocess.check_output([python, "-m", "pip", "list", "--format=json"])
        ),
    }
    (share / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
    marker.write_text(json.dumps({"profile": "magnetic-smoke", "ready": True}))


if __name__ == "__main__":
    main()
