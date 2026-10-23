"""Private Unix-socket model server with idle and absolute shutdown bounds."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import socket
import time
from pathlib import Path

from .events import put


def request(path, packet, *, timeout=30):
    started = time.perf_counter()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)
        client.connect(str(path))
        client.sendall(json.dumps(packet).encode() + b"\n")
        stream = client.makefile("rb")
        result = json.loads(stream.readline(1048577))
    if result.get("error"):
        raise RuntimeError(result["error"])
    result["transport_seconds"] = time.perf_counter() - started
    result["client_received_at"] = time.time()
    return result


def main():
    from .model import MonitorModel

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--adapter")
    parser.add_argument("--wall-seconds", type=float, default=21600)
    parser.add_argument("--idle-seconds", type=float, default=1800)
    args = parser.parse_args()
    if args.socket.exists():
        raise ValueError("Socket already exists; do not replace another serving process")
    start = last = time.monotonic()
    status = dict(stage="loading", started_at=time.time(), pid=os.getpid())
    put(args.status, status)
    model = MonitorModel(args.checkpoint, adapter=args.adapter)
    status.update(stage="ready", load_seconds=time.monotonic() - start, calls=0)
    put(args.status, status)
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    args.socket.parent.mkdir(parents=True, exist_ok=True)
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(args.socket))
            args.socket.chmod(0o600)
            server.listen(8)
            server.settimeout(1)
            while (
                not stopped
                and time.monotonic() - start < args.wall_seconds
                and time.monotonic() - last < args.idle_seconds
            ):
                try:
                    connection, _ = server.accept()
                except TimeoutError:
                    continue
                with connection:
                    connection.settimeout(5)
                    try:
                        line = connection.makefile("rb").readline(1048577)
                        if len(line) > 1048576:
                            raise ValueError("Request too large")
                        packet = json.loads(line)
                        last = time.monotonic()
                        result = model.predict(packet)
                        status.update(
                            calls=status["calls"] + 1, last_call_at=time.time(), last_result=result
                        )
                        put(args.status, status)
                    except Exception as error:
                        result = dict(error=f"{type(error).__name__}: {error}")
                    with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                        connection.sendall(json.dumps(result).encode() + b"\n")
    finally:
        args.socket.unlink(missing_ok=True)
        status.update(stage="stopped", ended_at=time.time())
        put(args.status, status)


if __name__ == "__main__":
    main()
