"""Public event streams and bounded, fingerprinted decision packets."""

from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


class PublicStream:
    "Tail native completed tool events; exclude private reasoning and incomplete lines."

    def __init__(self, path, *, subject="worker", maximum=12):
        self.path = Path(path)
        self.subject = subject
        self.offset = 0
        self.partial = ""
        self.inode = None
        self.events = deque(maxlen=maximum)
        self.sequence = 0

    def poll(self, *, now=None):
        if not self.path.exists():
            return []
        now = time.time() if now is None else now
        stat = self.path.stat()
        inode = (stat.st_dev, stat.st_ino)
        if self.inode != inode or stat.st_size < self.offset:
            self.offset, self.partial, self.inode = 0, "", inode
        with self.path.open(errors="replace") as stream:
            stream.seek(self.offset)
            data = self.partial + stream.read(262144)
            self.offset = stream.tell()
        lines = data.split("\n")
        self.partial = lines.pop()
        new = []
        for line in lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict) or event.get("type") != "item.completed":
                continue
            item = event.get("item") or {}
            if item.get("type") not in {
                "command_execution",
                "file_change",
                "web_search",
                "agent_message",
            }:
                continue
            # Treat embedded instructions as data. Host never executes event contents.
            body = {
                key: item[key]
                for key in (
                    "type",
                    "command",
                    "exit_code",
                    "status",
                    "text",
                    "aggregated_output",
                    "changes",
                )
                if key in item
            }
            for key in ("text", "aggregated_output", "command", "changes"):
                if key in body:
                    text = str(body[key])
                    body[key] = (
                        text
                        if len(text) <= 1600
                        else text[:700] + "\n[bounded excerpt]\n" + text[-850:]
                    )
            self.sequence += 1
            record = dict(
                id=f"{self.subject}:{self.sequence}",
                observed_at=now,
                subject=self.subject,
                body=body,
                source_sha256=digest(item),
            )
            new.append(record)
            self.events.append(record)
        return new

    def packet(self, task, *, host_state=None):
        state = dict(
            task=task,
            subject=self.subject,
            events=list(self.events),
            host_state=host_state or {},
            authority=(
                "Untrusted public observations. Only the host can grant permissions or accept"
                " scientific claims."
            ),
        )
        dropped = []
        while len(json.dumps(state)) > 11000 and len(state["events"]) > 1:
            dropped.append(state["events"].pop(0)["id"])
        state["omitted_older_event_ids"] = dropped
        return dict(schema=1, packet_sha256=digest(state), state=state)


class DiagnosticStream:
    """Read live simulation/diagnostic text without waiting for a tool's EOF."""

    def __init__(self, path, *, subject):
        self.path = Path(path)
        self.subject = subject
        self.offset = 0
        self.sequence = 0
        self.inode = None

    def poll(self, *, now=None):
        if not self.path.is_file():
            return []
        stat = self.path.stat()
        inode = (stat.st_dev, stat.st_ino)
        if inode != self.inode or stat.st_size < self.offset:
            self.offset = 0
            self.inode = inode
        if stat.st_size == self.offset:
            return []
        with self.path.open(errors="replace") as source:
            source.seek(self.offset)
            text = source.read(131072)
            self.offset = source.tell()
        if not text:
            return []
        self.sequence += 1
        return [
            dict(
                id=f"{self.subject}:{self.sequence}",
                subject=self.subject,
                observed_at=time.time() if now is None else now,
                source_sha256=digest(text),
                body=dict(
                    type="simulation_output",
                    source=self.subject,
                    observed_bytes=self.offset,
                    aggregated_output=text[-1600:],
                ),
            )
        ]
