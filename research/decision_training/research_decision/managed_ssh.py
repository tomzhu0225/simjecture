"""Recover an existing AtomGit forward without changing hosts or credentials."""

import os
import re
import subprocess
import time
from pathlib import Path, PureWindowsPath


def is_forward_failure(stderr):
    message = stderr.decode(errors="replace").lower()
    return any(fragment in message for fragment in (
        "ssh: connect to host 127.0.0.1", "connection to 127.0.0.1 closed by remote host",
        "connection reset by 127.0.0.1", "connection reset by peer",
    ))


def restore_existing_forward(route, timeout=60):
    try:
        identity = PureWindowsPath(route[route.index("-i") + 1])
    except (ValueError, IndexError):
        return False
    if not re.fullmatch(r"[0-9a-f]{32}", identity.name):
        return False
    base = identity.parents[2]
    if base.name != ".atomgitdevenv":
        return False
    command = base / "forward-bootstrap" / "vscode" / (identity.name + ".cmd")
    if os.name == "nt":
        executable = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
        present = Path(command).is_file()
    else:
        executable = "/mnt/c/Windows/System32/cmd.exe"
        local = Path("/mnt/" + command.drive[0].lower(), *command.parts[1:])
        present = local.is_file()
    if not present:
        return False
    # Execute the extension's existing, inspected restore entry. It restores
    # this environment's existing pinned local port, never creates a new node.
    result = subprocess.run(
        [executable, "/d", "/c", str(command)], capture_output=True,
        timeout=max(1, min(60, timeout)), check=False,
    )
    return result.returncode == 0


def run_ssh(route, command, *, input=None, timeout=60, stdout=None):
    deadline = time.monotonic() + timeout
    for attempt in range(3):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired("managed project SSH", timeout)
        result = subprocess.run(
            route + list(command), input=input, stdout=stdout or subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=remaining, check=False,
        )
        if result.returncode == 0 or not is_forward_failure(result.stderr) or attempt == 2:
            return result
        # Binary output callers restart their own partial-file transaction;
        # appending a new stream to existing archive bytes would be unsafe.
        if stdout is not None:
            restore_existing_forward(route, deadline - time.monotonic())
            return result
        if not restore_existing_forward(route, deadline - time.monotonic()):
            return result
    raise AssertionError("unreachable")
