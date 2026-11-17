"""Controller RPC for owned processes and durable protocol files (no shell interpolation)."""

import base64
import json
import os
import shutil
from pathlib import Path, PureWindowsPath
from urllib.request import urlopen

from .storage import owned_path, read_json, write_json


def dispatch(root, packet):
    root = Path(root).resolve()
    operation = packet["operation"]
    if operation == "process":
        from .processes import manage

        return manage(root, **packet["arguments"])
    if operation in {"read", "write"}:
        path = owned_path(root, packet["path"])
        if operation == "read":
            return read_json(path)
        # Protocol publication cannot replace weights, executables or task data.
        if not path.is_relative_to(root / "data") and not path.is_relative_to(root / "checkpoints"):
            raise ValueError("Runtime publication is limited to data and checkpoint metadata")
        write_json(path, packet["value"], immutable=packet.get("immutable", False))
        return dict(written=True)
    if operation == "write_jsonl":
        path = owned_path(root, packet["path"])
        if not path.is_relative_to(root / "data"):
            raise ValueError("JSONL publication belongs to the owned data directory")
        payload = "".join(json.dumps(v, ensure_ascii=False, allow_nan=False) + "\n" for v in packet["values"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_text(encoding="utf-8") != payload:
                raise ValueError("An immutable dataset export already has different contents")
        else:
            temporary = path.with_suffix(path.suffix + ".partial")
            temporary.write_text(payload, encoding="utf-8")
            os.replace(temporary, path)
        return dict(written=True, rows=len(packet["values"]))
    if operation == "health":
        port = 19190 + int(packet["slot"])
        if port not in {19190, 19191}:
            raise ValueError("Unknown policy slot")
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as response:
                return json.load(response)
        except OSError:
            return dict(ready=False)
    if operation == "disk":
        usage = shutil.disk_usage(root)
        return dict(total=usage.total, used=usage.used, free=usage.free)
    raise ValueError("Unknown controller operation")


class Remote:
    def __init__(self, config):
        self.root = config["remote_root"]
        self.route = json.loads(Path(config["ssh_route"]).read_bytes())
        if os.name != "nt" and PureWindowsPath(self.route[0]).drive:
            binary = PureWindowsPath(self.route[0])
            self.route[0] = "/mnt/" + binary.drive[0].lower() + "/" + "/".join(binary.parts[1:])

    def call(self, operation, timeout=60, **fields):
        encoded = base64.b64encode(json.dumps(dict(operation=operation, **fields)).encode()).decode()
        script = (
            "import base64,json,sys\nsys.path.insert(0," + repr(self.root) + ")\n"
            "from research_decision.remote_control import dispatch\n"
            "print(json.dumps(dispatch("
            + repr(self.root)
            + ",json.loads(base64.b64decode("
            + repr(encoded)
            + ")))))\n"
        )
        from .managed_ssh import run_ssh

        result = run_ssh(
            self.route, ["python3", "-"],
            input=script.encode(),
            timeout=timeout,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace")[-2500:])
        return json.loads(result.stdout)

    def process(self, name, operation, argv=None, env=None):
        return self.call("process", arguments=dict(name=name, operation=operation, argv=argv, env=env))

    def read(self, path):
        return self.call("read", path=path)

    def write(self, path, value, immutable=False):
        return self.call("write", path=path, value=value, immutable=immutable)
