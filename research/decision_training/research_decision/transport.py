"""Narrow Unix-socket client available inside a scientific role workspace."""

import base64
import http.client
import json
import os
import socket
import sys


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout=3600):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def request(path, payload, *, timeout=3600):
    connection = UnixConnection(os.environ["SCIENCE_TRANSPORT_SOCKET"], timeout)
    try:
        connection.request(
            "POST", path, json.dumps(payload, allow_nan=False).encode(), {"Content-Type": "application/json"}
        )
        response = connection.getresponse()
        result = json.load(response)
        if response.status != 200:
            raise RuntimeError(result.get("error", "Scientific transport failed"))
        return result
    finally:
        connection.close()


def ssh_main():
    if len(sys.argv) < 3 or sys.argv[-2] not in {"cannlab-science", "cannlab-cpu"}:
        raise ValueError("Use the configured remote science worker")
    payload = dict(
        host=sys.argv[-2], command=sys.argv[-1], stdin=base64.b64encode(sys.stdin.buffer.read()).decode()
    )
    if " -u -c " in sys.argv[-1]:
        connection = UnixConnection(os.environ["SCIENCE_TRANSPORT_SOCKET"])
        try:
            connection.request(
                "POST", "/worker-stream", json.dumps(payload).encode(), {"Content-Type": "application/json"}
            )
            response = connection.getresponse()
            if response.status != 200:
                raise RuntimeError(response.read().decode())
            while chunk := response.read(262144):
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
        finally:
            connection.close()
        return
    reply = request("/worker", payload)
    sys.stdout.buffer.write(base64.b64decode(reply["stdout"]))
    sys.stderr.buffer.write(base64.b64decode(reply["stderr"]))
    raise SystemExit(reply["exit_code"])


if __name__ == "__main__":
    ssh_main()
