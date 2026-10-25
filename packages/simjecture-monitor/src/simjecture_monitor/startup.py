"""Wait for a private model listener without retrying accepted inference work."""

from __future__ import annotations

import time

from .server import request


def ready_request(path, packet, *, process, startup_seconds=180, timeout=120):
    until = time.monotonic() + startup_seconds
    while True:
        if process.poll() is not None:
            raise RuntimeError("Model process exited before serving")
        try:
            return request(path, packet, timeout=timeout)
        except (FileNotFoundError, ConnectionRefusedError):
            # bind() creates the socket path before listen() can accept connections.
            # No request was accepted; inference and transport timeouts are not retried.
            if time.monotonic() >= until:
                raise RuntimeError("Model listener did not become ready") from None
            time.sleep(0.1)
