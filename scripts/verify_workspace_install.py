"""Install a release bundle in a fresh HOME and verify its GUI without an agent/API key."""

from __future__ import annotations

import argparse
import functools
import json
import os
import signal
import socket
import subprocess
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def verify(release, destination):
    destination.mkdir(parents=True, exist_ok=False)
    home = destination / "home"
    home.mkdir()
    env = {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "UV_CACHE_DIR": str(destination / "cache"),
        "UV_NO_CONFIG": "1",
        "SIMJECTURE_INSTALL_DIR": str(home / "simjecture"),
    }
    # Honor network routing only; never copy CLI credentials or model API settings.
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    ):
        if name in os.environ:
            env[name] = os.environ[name]
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(release))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env["SIMJECTURE_RELEASE_BASE"] = f"http://127.0.0.1:{server.server_port}"
    print(f"Testing fresh-home installation in {destination}", flush=True)
    try:
        with (destination / "install.log").open("w") as log:
            subprocess.run(
                ["bash", str(release / "install.sh"), "--no-start", "--no-system-packages"],
                env=env,
                cwd=home,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=900,
            )
    finally:
        server.shutdown()
        server.server_close()
    root = home / "simjecture"
    version = (root / ".current-version").read_text().strip()
    app = root / "app" / version
    python = app / ".venv/bin/python"
    subprocess.run(
        [
            str(python),
            "-c",
            "import h5py, smolagents; "
            "from conjecture_solver.agent_skills import research_skills; "
            "assert 'flash-mhd' in research_skills()",
        ],
        env=env,
        cwd=app,
        check=True,
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with (destination / "server.log").open("w") as log:
        child = subprocess.Popen(
            [str(root / "start-workspace"), "--no-open", "--port", str(port)],
            env=env,
            cwd=home,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 30
            while True:
                try:
                    with urllib.request.urlopen(
                        url + "/api/workspace/bootstrap", timeout=2
                    ) as response:
                        bootstrap = json.load(response)
                    break
                except OSError:
                    if child.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError("Installed web server did not become ready") from None
                    time.sleep(0.2)
            assert bootstrap["projects"] == []
            assert not bootstrap["settings"]["api_configured"]
            for resource in (
                "/",
                "/assets/workspace-theme.js",
                "/assets/brand/simjecture-lockup-light.svg",
                "/assets/brand/simjecture-lockup-dark.svg",
                "/favicon.svg",
                "/favicon.ico",
                "/assets/workspace-monitor.js",
                "/assets/vendor/webawesome-3.14.0/components/tab/tab.js",
                "/api/workspace/tools",
            ):
                with urllib.request.urlopen(url + resource, timeout=10) as response:
                    assert response.status == 200 and response.read()
        finally:
            child.send_signal(signal.SIGINT)
            child.wait(timeout=15)
    result = dict(
        version=version,
        fresh_home=True,
        agent_or_api_key_required=False,
        system_package_changes=False,
        gui=True,
        skill_resources=True,
        hdf5_reader=True,
    )
    (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    verify(args.release_dir.resolve(), args.work_dir.resolve())
