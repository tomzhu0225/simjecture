"""Owned helper process cleanup, bounded file reads and crash usage recovery."""

from __future__ import annotations

import hashlib
import json
import os
import signal
import stat
from contextlib import contextmanager, suppress
from pathlib import Path


@contextmanager
def regular_file(path, *, maximum=None):
    # NONBLOCK prevents FIFO substitution from blocking before fstat; NOFOLLOW
    # also checks the opened object rather than a racy earlier pathname check.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or (maximum is not None and info.st_size > maximum):
            raise ValueError("Expected a regular file within the size allowance")
        yield stream


def file_sha(path):
    with regular_file(path) as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def process_stat(pid):
    try:
        path = Path(f"/proc/{pid}")
        if path.stat().st_uid != os.getuid():
            return None
        fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] == "Z":
            return None
        return dict(pid=int(pid), ppid=int(fields[1]), session=int(fields[3]), starttime=fields[19])
    except (OSError, ValueError, IndexError):
        return None


def owned_alive(identity):
    current = process_stat(identity["pid"]) if identity else None
    return bool(current and current["starttime"] == str(identity["starttime"]))


def stop_native(directory):
    """Reap the recorded native session, including children surviving its leader.

    PID plus Linux start time survives exec without authorizing a reused PID.
    Helpers must not daemonize or detach tools into other sessions.
    """
    path = directory / "turn-00001/child_identity.json"
    if not path.is_file():
        return
    identity = json.loads(path.read_text())
    leader = process_stat(identity["pid"])
    if leader and leader["starttime"] != str(identity["starttime"]):
        return
    members = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        current = process_stat(int(path.name))
        if (
            current
            and current["session"] == identity["pid"]
            and int(current["starttime"]) >= int(identity["starttime"])
        ):
            members.append(current)
    for member in members:
        if owned_alive(member):
            with suppress(ProcessLookupError):
                os.kill(member["pid"], signal.SIGKILL)


def recover_usage(directory):
    """Recover flushed counters after controller loss; mark unknown coverage."""
    from .provider_usage import request_accounting

    turn = directory / "turn-00001"
    response = turn / "response.json"
    if not (turn / "child_identity.json").exists():
        return {}
    thread, usage = None, None
    if response.is_file():
        with response.open() as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "thread.started":
                    thread = event.get("thread_id")
                if event.get("type") == "turn.completed":
                    usage = event.get("usage")
        if not usage:
            usage = request_accounting(response)
    if usage:
        return {"usage_by_thread": {thread or "turn-00001": usage}}
    missing = {"usage_incomplete_turns": 1}
    if thread:
        missing["usage_unreported_threads"] = {thread: "helper"}
    else:
        missing["usage_unidentified_calls"] = 1
    return missing
