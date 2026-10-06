"""Install the contributed solver and a self-contained, pinned Warp runtime."""

import argparse
import hashlib
import importlib.util
import json
import shutil
import stat
import subprocess
import sys
import time
import venv
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prefix", type=Path, required=True)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--source", type=Path)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--repair", action="store_true")
    a = p.parse_args()
    package = a.project_root / "src/conjecture_solver"
    if not package.is_dir():
        spec = importlib.util.find_spec("conjecture_solver")
        if spec is None:
            p.error("Cannot locate the installed Simjecture package")
        package = Path(spec.origin).parent
    source = (a.source or package / "vendor/cylinder_lbm").resolve()
    for name in ("cylinder_warp_lbm_solver.py", "requirements.txt"):
        if not (source / name).is_file():
            p.error(f"Missing solver source file: {source / name}")
    prefix = a.prefix.resolve()
    marker = prefix.parent / "install-state" / f"{prefix.name}.json"
    if prefix.exists() and not marker.is_file():
        p.error(f"Refusing to modify an unmanaged directory: {prefix}")
    if marker.exists() and json.loads(marker.read_text()).get("profile") != "warp-lbm":
        p.error("Runtime belongs to a different installer")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"profile": "warp-lbm", "ready": False}))
    started = time.time()
    print("Preparing Cylinder flow · Warp-LBM, contributed by Zifei Meng…", flush=True)
    if sys.version_info >= (3, 10) and Path(sys.base_prefix).is_relative_to("/usr"):
        venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    else:
        subprocess.run(
            [
                sys.executable,
                str(a.project_root / "scripts/prepare_runtime.py"),
                "warp-lbm",
                str(prefix),
            ],
            check=True,
        )
    python = str(prefix / "bin/python")
    requirements = source / "requirements.txt"
    uv = shutil.which("uv")
    command = (
        [uv, "pip", "install", "--python", python, "-r", str(requirements)]
        if uv
        else [python, "-m", "pip", "install", "-r", str(requirements)]
    )
    if a.repair:
        command.append("--force-reinstall")
    subprocess.run(command, check=True)
    subprocess.run([python, "-m", "pip", "check"], check=True)
    share = prefix / "share"
    share.mkdir(exist_ok=True)
    shutil.copytree(
        source,
        share / "source",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv", "results"),
    )
    shutil.copy2(package / "cylinder_lbm.py", share / "lbm_driver.py")
    freeze = subprocess.check_output([python, "-m", "pip", "freeze"], text=True)
    (share / "installed-requirements.txt").write_text(freeze)

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    record = {
        "profile": "warp-lbm",
        "version": "1.0",
        "author": "Zifei Meng",
        "author_url": "https://github.com/ZifeiMengSPH",
        "license": "Apache-2.0",
        "solver_sha256": digest(share / "source/cylinder_warp_lbm_solver.py"),
        "driver_sha256": digest(share / "lbm_driver.py"),
        "requirements_sha256": digest(requirements),
        "packages": json.loads(
            subprocess.check_output([python, "-m", "pip", "list", "--format=json"])
        ),
        "install_seconds": time.time() - started,
        "scope": "2D isothermal cylinder flow; supplied qualification is Re=100.",
    }
    (share / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
    capability = "warp-lbm-cylinder-1.0"
    mounted = f"/opt/acs-capabilities/{capability}"
    devices = []
    if Path("/dev/dxg").exists():
        devices = ["/dev/dxg"]
    else:
        devices = [
            str(f) for f in sorted(Path("/dev").glob("nvidia*")) if stat.S_ISCHR(f.stat().st_mode)
        ]
    environment = {
        "MPLBACKEND": "Agg",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "WARP_CACHE_PATH": "/tmp/warp-cache",
        "SIMJECTURE_LBM_SOURCE": mounted + "/share/source/cylinder_warp_lbm_solver.py",
        "SIMJECTURE_LBM_DRIVER": mounted + "/share/lbm_driver.py",
    }
    if Path("/dev/dxg").exists():
        environment["LD_LIBRARY_PATH"] = "/usr/lib/wsl/lib"
    descriptor = json.loads((a.project_root / "capabilities" / f"{capability}.json").read_text())
    descriptor.update(runtime_root="..", environment=environment, device_paths=devices)
    generated = prefix / "capabilities"
    generated.mkdir(exist_ok=True)
    (generated / f"{capability}.json").write_text(json.dumps(descriptor, indent=2) + "\n")
    marker.write_text(json.dumps({"profile": "warp-lbm", "ready": True}))
    print("Installed. Checking actual numerical execution through Simjecture…", flush=True)


if __name__ == "__main__":
    main()
