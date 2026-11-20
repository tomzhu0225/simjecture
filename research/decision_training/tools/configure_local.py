"""Write ignored, machine-local settings. Does not start a model or simulator."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-root", required=True, help="Same package path on both remote hosts")
    parser.add_argument("--training-host", default="training-node", help="Existing OpenSSH config alias")
    parser.add_argument("--simulation-host", default="simulation-node", help="Existing OpenSSH config alias")
    parser.add_argument("--ssh-client", default="/usr/bin/ssh")
    parser.add_argument("--case-store", type=Path)
    parser.add_argument("--codex-binary", default=shutil.which("codex") or "/opt/codex/codex")
    parser.add_argument("--auth-file", type=Path, default=Path.home() / ".codex/auth.json")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("Run the controller configuration on Linux or WSL")
    root = Path(__file__).resolve().parents[1]
    repo = root.parents[1]
    (root / "config").mkdir(exist_ok=True)
    def write(name, value):
        path = root / "config" / name
        if path.exists():
            raise FileExistsError("Keep the existing local configuration: " + name)
        path.write_text(json.dumps(value, indent=2) + "\n")
        path.chmod(0o600)
    for name, host in [("ssh-route.local.json", args.training_host), ("ssh-cpu-route.local.json", args.simulation_host)]:
        write(name, [args.ssh_client, "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host])
    write("pipeline.local.json", dict(
        package=str(root), remote_root=args.remote_root,
        ssh_route=str(root / "config/ssh-route.local.json"),
        case_store=str((args.case_store or root / "controller-runtime").resolve()),
        codex_wrapper=str(root / "bin/codex-science"),
        machine_registry=str(root / "controller-machine-registry"),
        machine_ids=["remote-cpu", "independent-cpu"],
        assessment_timeout_seconds=900, policy_start_timeout_seconds=300,
        remote_minimum_free_bytes=20 * 1024**3, study_disk_bytes=16 * 1024**3,
        public_resources=dict(
            worker="independent-cpu", cpus=16, memory_mb=24576, gpus=0,
            local_scientific_fallback=False, training_NPU_access=False,
            solvers=["NumPy/SciPy CPU", "Athena++ if qualified", "WarpX if qualified"],
        ),
    ))
    write("isolation.local.json", dict(
        package=str(root), simjecture_source=str(repo / "src"),
        codex_binary=args.codex_binary, auth_file=str(args.auth_file.resolve()),
        python_runtime=sys.base_prefix, python_environment=sys.prefix,
        python_executable=sys.executable,
        python_site_packages=str(Path(sys.prefix) / f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"),
        role_home="/science-home", transport_socket=str(root / "runtime/transport.sock"),
        network_proxy=None,
    ))
    for path in (root / "bin").iterdir():
        if path.is_file():
            path.chmod(0o755)
    print(json.dumps(dict(configured=True, models_started=0, simulations_started=0)))


if __name__ == "__main__":
    main()
