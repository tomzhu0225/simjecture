"""Bounded replay of stateless attention requests across a reconnecting local link.

Use only with the frozen inference service: it returns predictions and cannot
dispatch help. A replay sends the identical request, including a sampling seed.
The caller still applies freshness and admission checks to the returned result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import time
from pathlib import Path

LIMIT = 2_000_000


def relay(
    payload: bytes, upstream: Path | list[Path], *, deadline: float, retry_delay: float = 0.2
):
    """Return one complete response; never replay a returned application error."""
    if not payload.endswith(b"\n") or len(payload) > LIMIT:
        raise ValueError("Invalid attention request framing")
    value = json.loads(payload)
    if not isinstance(value, dict) or value.get("operation") not in (None, "health"):
        raise ValueError("Only stateless inference and health requests may be relayed")
    links = [upstream] if isinstance(upstream, Path) else list(upstream)
    if not links or len(set(links)) != len(links):
        raise ValueError("Require distinct links to the same frozen inference service")
    # No auth token, observation content, or raw model response enters the log.
    public = {key: item for key, item in value.items() if key != "auth_token"}
    receipt = {
        "request_sha256": hashlib.sha256(
            json.dumps(public, sort_keys=True, allow_nan=False).encode()
        ).hexdigest(),
        "connect_attempts": 0,
        "send_attempts": 0,
        "started_at": time.time(),
    }
    last_error = "NoAvailableLink"
    while time.monotonic() < deadline:
        index = receipt["connect_attempts"] % len(links)
        receipt["connect_attempts"] += 1
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(min(1.0, max(0.001, deadline - time.monotonic())))
                client.connect(str(links[index]))
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Attention transport deadline elapsed")
                client.settimeout(remaining)
                receipt["send_attempts"] += 1
                client.sendall(payload)
                response = client.makefile("rb").readline(LIMIT + 1)
            if not response.endswith(b"\n") or len(response) > LIMIT:
                raise ConnectionError("Incomplete or oversized attention response")
            parsed = json.loads(response)
            if not isinstance(parsed, dict):
                raise ValueError("Attention response must be an object")
            receipt.update(status="returned", ended_at=time.time(), returned_link_index=index)
            return response, receipt
        except (OSError, TimeoutError) as error:
            last_error = type(error).__name__
            # A delivered request might have executed before the link dropped.
            # Permit one replay, with no action dispatch inside this service.
            if receipt["send_attempts"] >= 2:
                break
            remaining = deadline - time.monotonic()
            if remaining > 0 and receipt["connect_attempts"] % len(links) == 0:
                time.sleep(min(retry_delay, remaining))
    receipt.update(status="unavailable", ended_at=time.time(), error_type=last_error)
    response = json.dumps({"error": "Attention transport unavailable within its bound"}) + "\n"
    return response.encode(), receipt


def serve(
    public: Path,
    upstream: list[Path],
    log: Path,
    *,
    stop_by: float,
    request_seconds: float,
):
    if public.exists():
        raise ValueError("Refuse to replace an existing attention listener")
    public.parent.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(public))
        public.chmod(0o600)
        listener.listen(4)
        listener.settimeout(1.0)
        try:
            while time.time() < stop_by:
                try:
                    client, _ = listener.accept()
                except TimeoutError:
                    continue
                with client:
                    started = time.monotonic()
                    client.settimeout(request_seconds)
                    try:
                        payload = client.makefile("rb").readline(LIMIT + 1)
                        response, receipt = relay(
                            payload,
                            upstream,
                            deadline=min(
                                started + request_seconds,
                                time.monotonic() + max(0.0, stop_by - time.time()),
                            ),
                        )
                    except (ValueError, OSError) as error:
                        response = b'{"error":"Invalid attention transport request"}\n'
                        receipt = {
                            "status": "rejected",
                            "error_type": type(error).__name__,
                            "ended_at": time.time(),
                        }
                    try:
                        client.sendall(response)
                    except OSError:
                        receipt["caller_disconnected"] = True
                    with log.open("a") as stream:
                        stream.write(json.dumps(receipt, allow_nan=False) + "\n")
        finally:
            public.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument(
        "--upstream", type=Path, action="append", required=True, help="Links to the same runtime"
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--stop-by", type=float, required=True)
    parser.add_argument("--request-seconds", type=float, default=20.0)
    args = parser.parse_args()
    if not 0 < args.request_seconds <= 20:
        parser.error("Keep transport recovery inside the host's 25-second request timeout")
    serve(
        args.socket,
        args.upstream,
        args.log,
        stop_by=args.stop_by,
        request_seconds=args.request_seconds,
    )


if __name__ == "__main__":
    main()
