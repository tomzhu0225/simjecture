"""Case-authenticated native Lab authority outside the role filesystem namespace."""

import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from .storage import read_json, write_json


class NativeLabProxy:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def call(*args, **kwargs):
            run = read_json(self.root / "study-run.json")
            token = run.get("transport_token")
            for _ in range(30):
                if token:
                    break
                token = read_json(self.root / ".transport-capability.json", {}).get("token")
                if not token:
                    __import__("time").sleep(0.1)
            body = dict(root=str(self.root), token=token, method=name, args=args, kwargs=kwargs)
            request = Request(
                os.environ.get("SCIENCE_LAB_ENDPOINT", "http://127.0.0.1:19175") + "/lab",
                data=json.dumps(body, allow_nan=False).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urlopen(
                    request, timeout=max(30, run["deadline"] - __import__("time").time() + 5)
                ) as response:
                    result = json.load(response)
            except __import__("urllib.error", fromlist=["HTTPError"]).HTTPError as error:
                result = json.load(error)
            if not result.get("ok"):
                raise ValueError(result.get("error", "Native Lab operation failed"))
            return result["result"]

        return call


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-store", type=Path, required=True)
    parser.add_argument("--port", type=int, default=19175)
    args = parser.parse_args()

    def capabilities():
        import time
        import uuid

        while True:
            for path in (args.case_store / "runs").glob("*/study-run.json"):
                if not (path.parent / ".transport-capability.json").exists():
                    write_json(
                        path.parent / ".transport-capability.json",
                        dict(token=uuid.uuid4().hex),
                        immutable=True,
                    )
            time.sleep(0.5)

    __import__("threading").Thread(target=capabilities, daemon=True).start()
    from conjecture_solver.research_service import Lab

    methods = {name for name, value in vars(Lab).items() if not name.startswith("_") and callable(value)}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            status = 200
            try:
                length = int(self.headers.get("Content-Length", 0))
                if self.path != "/lab" or not 0 < length < 32 * 1024**2:
                    raise ValueError("Invalid case operation")
                packet = json.loads(self.rfile.read(length))
                root = Path(packet["root"]).resolve()
                if not root.is_relative_to(args.case_store.resolve() / "runs"):
                    raise ValueError("Case is outside the project scientific workspace")
                run = read_json(root / "study-run.json")
                expected = (
                    (
                        run.get("transport_token")
                        or read_json(root / ".transport-capability.json", {}).get("token", "")
                    )
                    if run
                    else ""
                )
                if not expected or not hmac.compare_digest(expected, packet.get("token", "")):
                    raise ValueError("Invalid case capability")
                if packet["method"] not in methods:
                    raise ValueError("Unknown public native Lab method")
                result = getattr(Lab(root), packet["method"])(
                    *packet.get("args", []), **packet.get("kwargs", {})
                )
                reply = dict(ok=True, result=result)
            except Exception as error:
                status = 400
                reply = dict(ok=False, error=str(error))
            payload = json.dumps(reply, allow_nan=False, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
