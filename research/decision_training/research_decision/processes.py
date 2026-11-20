"""Owned remote process groups: start-time checked, resumable, no broad pkill."""

import argparse
import os
import signal
import subprocess
import time
from pathlib import Path

from .storage import owned_path, read_json, write_json


def identity(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return raw[19] if raw[0] != "Z" else None
    except (FileNotFoundError, ProcessLookupError):
        return None


def active(record):
    return bool(record and identity(record["pid"]) == record["starttime"])


def manage(root, name, operation, argv=None, env=None):
    import fcntl

    root = Path(root).resolve()
    lock_path = root / "runtime/processes.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        return _manage(root, name, operation, argv, env)


def _manage(root, name, operation, argv=None, env=None):
    root = Path(root).resolve()
    if not name.replace("-", "").isalnum():
        raise ValueError("Use a simple project-owned process name")
    directory = root / "runtime/processes"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + ".json")
    record = read_json(path)
    if operation == "status":
        return dict(record=record, active=active(record))
    if operation == "stop":
        if active(record):
            # start_new_session makes this PID the group's owner. Recheck before
            # both signals; never identify another job by executable name.
            if os.getpgid(record["pid"]) != record["pid"]:
                raise ValueError("Recorded process no longer owns its process group")
            os.killpg(record["pid"], signal.SIGTERM)
            cutoff = time.monotonic() + 15
            while active(record) and time.monotonic() < cutoff:
                time.sleep(0.1)
            if active(record):
                os.killpg(record["pid"], signal.SIGKILL)
        return dict(active=False, record=record)
    if operation != "start" or not argv:
        raise ValueError("Process start requires an argument list")
    if active(record):
        if record["argv"] != argv:
            raise ValueError("An owned service is already active with another configuration")
        return dict(record=record, active=True, reused=True)
    # Executables and the project module belong to this prepared root; arguments
    # are passed directly, never interpreted as shell commands.
    executable = Path(argv[0]).absolute()
    if not executable.is_relative_to(root):
        raise ValueError("Service executable must use this project's resource wrapper")
    log = owned_path(root, "runtime/processes/" + name + ".log")
    with log.open("ab", buffering=0) as output:
        process = subprocess.Popen(
            argv,
            cwd=root,
            env=dict(os.environ, **(env or {})),
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            start_new_session=True,
        )
    time.sleep(0.1)
    token = identity(process.pid)
    if token is None:
        raise RuntimeError(f"{name} exited during start; inspect its owned process log")
    record = dict(pid=process.pid, starttime=token, argv=argv, started_at=time.time(), log=str(log))
    write_json(path, record)
    return dict(record=record, active=True, reused=False)


def main():
    import json
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    packet = json.load(sys.stdin)
    result = manage(args.root, **packet)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
