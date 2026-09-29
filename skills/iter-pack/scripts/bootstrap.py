"""Provision the optional pack in a managed, isolated Python environment."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    if args.source:
        parser.error("This pack uses pinned public packages; --source is not supported")
    if not shutil.which("git") or not shutil.which("cc"):
        parser.error("Install git and a C compiler for the pinned CHERAB extension builds")
    prefix = args.prefix.resolve()
    marker = prefix.parent / "install-state" / (prefix.name + ".json")
    if prefix.exists() and not marker.exists():
        parser.error(f"Refusing to modify unmanaged directory: {prefix}")
    if marker.exists() and json.loads(marker.read_text()).get("profile") != "iter-pack":
        parser.error("Runtime belongs to a different installer")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"profile": "iter-pack", "ready": False}))
    started = time.time()
    print("Creating isolated ITER diagnostics environment…", flush=True)
    # Copy Python so /usr's standard library remains accessible in the sandbox;
    # do not link to an unrelated uv-managed environment outside the capability.
    if sys.version_info[:2] in {(3, 11), (3, 12)} and not (prefix / "conda-meta").exists():
        venv.EnvBuilder(with_pip=True, symlinks=False).create(prefix)
    else:
        # Older system Python is common on remote hosts. Provision a local
        # interpreter instead of linking to the agent's external uv runtime.
        subprocess.run(
            [
                sys.executable,
                str(args.project_root / "scripts/prepare_runtime.py"),
                "iter-pack",
                str(prefix),
            ],
            check=True,
        )
    python = str(prefix / "bin/python")
    requirements = Path(__file__).with_name("requirements.txt")
    env = os.environ | {"CHERAB_NCPU": str(args.jobs), "MPLBACKEND": "Agg"}
    installer = shutil.which("uv")
    command = (
        [installer, "pip", "install", "--python", python, "-r", str(requirements)]
        if installer
        else [
            python,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--retries",
            "3",
            "--timeout",
            "60",
            "-r",
            str(requirements),
        ]
    )
    if args.repair:
        command.append("--force-reinstall")
    subprocess.run(command, env=env, check=True)
    subprocess.run([python, "-m", "pip", "check"], check=True)
    share = prefix / "share"
    share.mkdir(exist_ok=True)
    packages = json.loads(subprocess.check_output([python, "-m", "pip", "list", "--format=json"]))
    freeze = subprocess.check_output([python, "-m", "pip", "freeze"], text=True)
    (share / "installed-requirements.txt").write_text(freeze)
    record = {
        "installer": "simjecture",
        "profile": "iter-pack",
        "version": "1.0",
        "python": subprocess.check_output([python, "--version"], text=True).strip(),
        "packages": packages,
        "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
        "requirements": requirements.read_text(),
        "install_seconds": time.time() - started,
        "scope": "Diagnostics and data; not JOREK, SOLPS or DINA solvers",
    }
    (share / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
    marker.write_text(json.dumps({"profile": "iter-pack", "ready": True}))
    print(
        "Installed. Simjecture will now run numerical readiness checks in its execution sandbox.",
        flush=True,
    )


if __name__ == "__main__":
    main()
