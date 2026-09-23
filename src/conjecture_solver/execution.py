"""Host checks for explicit experiment execution backends."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess

BACKENDS = ("bubblewrap", "proot-cooperative")


def probe_execution_backend(backend: str) -> dict:
    if backend not in BACKENDS:
        raise ValueError("Unknown execution backend")
    report = {
        "backend": backend,
        "available": False,
        "kernel_isolation": backend == "bubblewrap",
        "network_isolation": backend == "bubblewrap",
    }
    binary = shutil.which("bwrap" if backend == "bubblewrap" else "proot")
    if not binary:
        report["reason"] = (
            f"Missing {'bubblewrap' if backend == 'bubblewrap' else 'proot'} executable"
        )
        return report
    if backend == "proot-cooperative":
        if os.geteuid() == 0:
            report["reason"] = "Cooperative execution requires an unprivileged account"
            return report
        if importlib.util.find_spec("psutil") is None:
            report["reason"] = "Install simjecture[process] for resident-memory monitoring"
            return report
        command = [binary, "-r", "/", "/usr/bin/true"]
    else:
        command = [
            binary,
            "--unshare-all",
            "--die-with-parent",
            "--ro-bind",
            "/",
            "/",
            "/usr/bin/true",
        ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        report["available"] = result.returncode == 0
        report["reason"] = (
            result.stderr.strip()[-2000:] if result.returncode else "Execution probe passed"
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        report["reason"] = str(error)
    if not report["available"] and backend == "bubblewrap":
        report["remedy"] = (
            "Enable Linux namespaces or explicitly select --execution-backend "
            "proot-cooperative on a dedicated unprivileged account; "
            "the fallback is not a security sandbox and shares host networking."
        )
    return report


def require_execution_backend(backend: str) -> dict:
    report = probe_execution_backend(backend)
    if not report["available"]:
        raise ValueError(
            f"{backend} preflight failed: {report['reason']}. {report.get('remedy', '')}"
        )
    return report
