"""Fresh Linux Codex role with a case-only filesystem and transport socket."""

import json
import os
import subprocess
import sys
from pathlib import Path


def command(config, argv, cwd):
    case = Path(cwd).resolve()
    while not (case / "initial-state.json").exists() and not (case / "role-packet.json").exists():
        if case.parent == case:
            raise ValueError("Scientific roles require a materialized case or independent review packet")
        case = case.parent
    state = case / ".role-runtime"
    state.mkdir(exist_ok=True)
    package = Path(config["package"])
    native_codex = config["codex_binary"]
    resources = Path(native_codex).parent
    role_home = config.get("role_home", "/science-home")
    mounts = [
        "bwrap",
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
    ]
    for directory in ["/usr", "/bin", "/lib", "/lib64", "/etc"]:
        if Path(directory).exists():
            mounts.extend(["--ro-bind", directory, directory])
    for path in [config["python_runtime"], config["python_environment"]]:
        mounts.extend(["--ro-bind", path, path])
    mounts.extend(
        [
            "--dir",
            role_home,
            "--bind",
            str(state),
            role_home + "/.codex",
            "--ro-bind",
            config["auth_file"],
            role_home + "/.codex/auth.json",
            "--dir",
            "/app/bin",
            "--ro-bind",
            native_codex,
            "/app/bin/codex-science",
            "--ro-bind",
            str(resources / "codex-code-mode-host"),
            "/app/bin/codex-code-mode-host",
            "--ro-bind",
            str(resources / "rg"),
            "/app/bin/rg",
            "--ro-bind",
            config["python_executable"],
            "/app/bin/python",
            "--ro-bind",
            str(package / "research_decision"),
            "/app/research_decision",
            "--ro-bind",
            str(package / "research_decision/science_sitecustomize.py"),
            "/app/sitecustomize.py",
            "--ro-bind",
            config.get("simjecture_source", str(package.parents[1] / "src")),
            "/app/vendor/simjecture/src",
            "--ro-bind",
            str(package / "schemas"),
            "/app/schemas",
            "--ro-bind",
            str(package / "controller-machine-registry"),
            str(package / "controller-machine-registry"),
            "--ro-bind",
            str(package / "bin/ssh-isolated"),
            "/app/bin/ssh",
            "--ro-bind",
            config["transport_socket"],
            "/run/science-transport.sock",
            "--bind",
            str(case),
            str(case),
            "--chdir",
            str(Path(cwd).resolve()),
            "--setenv",
            "PYTHONHOME",
            config["python_runtime"],
            "--setenv",
            "PYTHONPATH",
            "/app:/app/vendor/simjecture/src:"
            + config.get("python_site_packages", config["python_environment"] + "/lib/python3.12/site-packages"),
            "--setenv",
            "HOME",
            role_home,
            "--setenv",
            "CODEX_HOME",
            role_home + "/.codex",
            "--setenv",
            "PATH",
            "/app/bin:/usr/bin:/bin",
            "--setenv",
            "SCIENCE_TRANSPORT_SOCKET",
            "/run/science-transport.sock",
        ]
    )
    if config.get("network_proxy"):
        proxy = "http://127.0.0.1:" + str(config["network_proxy"]["listen_port"])
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            mounts += ["--setenv", key, proxy]
        mounts += ["--setenv", "NO_PROXY", "127.0.0.1,localhost"]
    return mounts + ["--", "/app/bin/codex-science", *argv]


def main():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config/isolation.local.json").read_bytes())
    argv = sys.argv[1:]
    if not argv or argv[0] != "exec":
        raise ValueError("Scientific role launcher accepts Codex exec")
    # Existing native worker resume IDs stay within this one case's role runtime.
    argv = [argv[0], "--ignore-user-config", "--ignore-rules", *argv[1:]]
    environment = dict(os.environ)
    for key in list(environment):
        if key.startswith(("CODEX_", "SIMJECTURE_RESEARCH_POLICY", "TASTELEAP_")):
            environment.pop(key, None)
    result = subprocess.run(command(config, argv, Path.cwd()), env=environment, check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
