"""Controller-side transport for filesystem-isolated scientific roles."""

import argparse
import base64
import json
import shlex
import socketserver
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path


class ScienceGateway(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True

    def __init__(self, socket_path, route, remote_root, extra_routes=None):
        self.route = route
        self.remote_root = remote_root
        self.worker_routes = {"cannlab-science": (route, remote_root)}
        self.worker_routes.update(extra_routes or {})
        self.lock = threading.Lock()
        super().__init__(str(socket_path), GatewayHandler)


class GatewayHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 96 * 1024 * 1024:
                raise ValueError("Invalid transport payload size")
            request = json.loads(self.rfile.read(length))
            if self.path == "/worker-stream":
                self.stream_worker(request)
                return
            if self.path == "/worker":
                result = self.worker(request)
            elif self.path == "/policy":
                result = self.policy(request)
            else:
                raise ValueError("Unknown project transport endpoint")
            status = 200
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
            status = 502
            result = dict(error=str(error))
        payload = json.dumps(result, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def worker(self, request):
        route, remote_root = self.server.worker_routes[request.get("host", "cannlab-science")]
        command = request["command"]
        argv = shlex.split(command)
        worker_python = remote_root + "/resources/cpu-python"
        expected = [
            worker_python,
            "-m",
            "conjecture_solver.execution_worker",
            "--root",
            remote_root + "/cpu-worker",
        ]
        # Artifact streaming is a pinned upstream program. It accesses the same
        # recorded remote worker and its contained artifact methods.
        if argv != expected:
            from conjecture_solver.execution_pool import _FETCH_STREAM

            if argv != [worker_python, "-u", "-c", _FETCH_STREAM]:
                raise ValueError("Use the registered scientific execution-worker interface")
        payload = base64.b64decode(request["stdin"], validate=True)
        from .managed_ssh import run_ssh

        result = run_ssh(
            route, [command],
            input=payload,
            timeout=request.get("timeout", 3600),
        )
        return dict(
            exit_code=result.returncode,
            stdout=base64.b64encode(result.stdout).decode(),
            stderr=base64.b64encode(result.stderr).decode(),
        )

    def stream_worker(self, request):
        from conjecture_solver.execution_pool import _FETCH_STREAM

        route, remote_root = self.server.worker_routes[request.get("host", "cannlab-science")]
        expected = [remote_root + "/resources/cpu-python", "-u", "-c", _FETCH_STREAM]
        if shlex.split(request["command"]) != expected:
            raise ValueError("Artifact streams use the pinned worker fetch program")
        body = base64.b64decode(request["stdin"], validate=True)
        packet = json.loads(body)
        if packet["root"] != remote_root + "/cpu-worker":
            raise ValueError("Artifact stream belongs to another execution worker")
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(
                route + [request["command"]],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=errors,
            )
            try:
                process.stdin.write(body)
                process.stdin.close()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Connection", "close")
                self.end_headers()
                while chunk := process.stdout.read(262144):
                    self.wfile.write(chunk)
                    self.wfile.flush()
                if process.wait() != 0:
                    self.wfile.write(b'\n{"ok":false,"error":"Remote artifact stream interrupted"}\n')
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)

    def policy(self, request):
        slot = request["slot"]
        if slot not in (0, 1):
            raise ValueError("Unknown NPU policy slot")
        body = request["body"]
        from .contracts import reject_private_fields

        reject_private_fields(body["observation"])
        encoded = base64.b64encode(json.dumps(body, allow_nan=False).encode()).decode()
        script = (
            "import base64,json\nfrom urllib.request import Request,urlopen\n"
            + "body=base64.b64decode("
            + repr(encoded)
            + ")\n"
            + "with urlopen(Request('http://127.0.0.1:"
            + str(19190 + slot)
            + "/advice',data=body,headers={'Content-Type':'application/json'}),timeout="
            + str(max(1, body["observation"]["remaining_wall_seconds"]))
            + ") as response: print(response.read().decode())\n"
        )
        from .managed_ssh import run_ssh

        result = run_ssh(
            self.server.route, ["python3", "-"],
            input=script.encode(),
            timeout=max(10, body["observation"]["remaining_wall_seconds"] + 10),
        )
        if result.returncode:
            raise ValueError("The pinned remote policy service did not complete its request")
        return json.loads(result.stdout)

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--route", type=Path, required=True)
    parser.add_argument("--remote-root", required=True)
    args = parser.parse_args()
    route = json.loads(args.route.read_bytes())
    from pathlib import PureWindowsPath

    binary = PureWindowsPath(route[0])
    route[0] = "/mnt/" + binary.drive[0].lower() + "/" + "/".join(binary.parts[1:])
    args.socket.parent.mkdir(parents=True, exist_ok=True)
    with ScienceGateway(args.socket, route, args.remote_root) as server:
        args.socket.chmod(0o600)
        try:
            server.serve_forever()
        finally:
            args.socket.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
