"""Experiment executable wrapper: shared native-role leases and owned cleanup.

Set SIMJECTURE_NATIVE_BUDGET and SIMJECTURE_CONTINUATION in each controller's
environment. Every native role must use this executable, including read-only
judges and helpers. This is a cooperative resource boundary, not a sandbox.
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager, suppress
from pathlib import Path

from conjecture_solver.research_helper_runtime import owned_alive, process_stat

from .events import digest, put


@contextmanager
def locked(path):
    path = Path(path)
    with path.with_suffix(".lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        state = json.loads(path.read_text())
        yield state
        put(path, state)


def stop_session(identity):
    """Only a recorded Linux session from this boot is eligible for cleanup."""
    if not identity or identity["session"] != identity["pid"]:
        return
    leader = process_stat(identity["pid"])
    if leader and leader["starttime"] != identity["starttime"]:
        return
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        current = process_stat(int(path.name))
        if (
            current
            and current["pid"] != os.getpid()
            and current["session"] == identity["session"]
            and int(current["starttime"]) >= int(identity["starttime"])
            and owned_alive(current)
        ):
            with suppress(ProcessLookupError):
                os.kill(current["pid"], signal.SIGKILL)


def reap(state):
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    for row in state["starts"]:
        if row.get("ended_at") is not None:
            continue
        if row["boot_id"] != boot or not owned_alive(row["wrapper"]):
            if row["boot_id"] == boot:
                stop_session(row["wrapper"])
            row.update(ended_at=time.time(), recovered=True)


def reserve(path, continuation, *, deadline):
    while time.time() < deadline:
        with locked(path) as state:
            reap(state)
            if time.time() >= state["deadline"]:
                return None
            previous = [r for r in state["starts"] if r["continuation"] == continuation]
            if (
                len(state["starts"]) >= state["maximum_starts"]
                or len(previous) >= state["maximum_per_continuation"]
            ):
                return None
            active = [r for r in state["starts"] if r.get("ended_at") is None]
            if len(active) < state["maximum_concurrent"]:
                row = dict(
                    id=uuid.uuid4().hex,
                    continuation=continuation,
                    started_at=time.time(),
                    ended_at=None,
                    wrapper=process_stat(os.getpid()),
                    boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                    cwd=str(Path.cwd()),
                    argv_sha256=digest(sys.argv[1:]),
                    readonly="--ephemeral" in sys.argv,
                    deadline=min(deadline, state["deadline"]),
                )
                state["starts"].append(row)
                return row, state["executable"]
        time.sleep(0.25)
    return None


def main():
    if os.getsid(0) != os.getpid():
        os.setsid()
    path = Path(os.environ["SIMJECTURE_NATIVE_BUDGET"])
    continuation = os.environ["SIMJECTURE_CONTINUATION"]
    deadline = float(os.environ["SIMJECTURE_CONTINUATION_DEADLINE"])
    reserved = reserve(path, continuation, deadline=deadline)
    if reserved is None:
        print("Native experiment budget exhausted", file=sys.stderr)
        raise SystemExit(125)
    row, executable = reserved
    deadline = row["deadline"]
    child = None
    stopped = False

    def signal_stop(signum, frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, signal_stop)
    signal.signal(signal.SIGINT, signal_stop)
    code = 125
    try:
        args = sys.argv[1:]
        # Native experimental subjects cannot recursively create unmetered agents.
        args[-1:-1] = ["-c", "features.multi_agent=false"]
        child = subprocess.Popen([executable, *args])
        with locked(path) as state:
            current = next(r for r in state["starts"] if r["id"] == row["id"])
            current["native"] = process_stat(child.pid)
        while child.poll() is None:
            if stopped or time.time() >= deadline:
                stop_session(row["wrapper"])
                break
            time.sleep(0.2)
        code = child.wait(timeout=5)
    finally:
        stop_session(row["wrapper"])
        with locked(path) as state:
            current = next(r for r in state["starts"] if r["id"] == row["id"])
            current.update(ended_at=time.time(), returncode=code, cancelled=stopped)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
