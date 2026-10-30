"""Read-only deployment observations, also sent to registered workers over SSH.

Keep this module standard-library-only: an older worker must be inspectable before
we know whether its installed Simjecture source matches the coordinator.
"""

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import shutil
import stat
import sys
from pathlib import Path


def file_identity(path):
    """Hash a regular file without blocking on a FIFO or returning its contents."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("not_regular_file")
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    current = os.stat(path)

    def signature(value):
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns

    if signature(before) != signature(after) or signature(after) != signature(current):
        raise ValueError("file_changed_during_check")
    return {"sha256": digest.hexdigest(), "bytes": after.st_size}


def inspect_host(files, storage_path):
    spec = importlib.util.find_spec("conjecture_solver")
    if spec is None or spec.origin is None:
        raise ValueError("Simjecture package is unavailable")
    source = Path(spec.origin).parent
    digest = hashlib.sha256()
    # Match the Python files shipped by MachineRegistry.prepare. Installed skill
    # assets and scientific runtime identities are checked separately.
    paths = sorted(source.rglob("*.py"))
    if not paths:
        raise ValueError("No installed Python source files were found")
    for path in paths:
        relative = path.relative_to(source)
        if "__pycache__" in relative.parts or "builtin_skills" in relative.parts:
            continue
        digest.update(relative.as_posix().encode() + b"\0")
        digest.update(bytes.fromhex(file_identity(path)["sha256"]))
    result = {
        "simjecture_version": importlib.metadata.version("simjecture"),
        "python_source_sha256": digest.hexdigest(),
        "python_version": sys.version.split()[0],
        "files": {},
        "storage": {},
    }
    for item in files:
        try:
            value = file_identity(item["path"])
        except OSError as error:
            value = {"error": "file_unavailable", "errno": error.errno}
        except ValueError as error:
            value = {"error": str(error)}
        result["files"][item["id"]] = value
    try:
        result["storage"] = {"free_bytes": shutil.disk_usage(storage_path).free}
    except OSError as error:
        result["storage"] = {"error": "storage_unavailable", "errno": error.errno}
    return result


if __name__ == "__main__":
    try:
        request = json.load(sys.stdin)
        response = {"ok": True, "result": inspect_host(**request)}
    except Exception as error:
        # Never forward environment, file contents, or arbitrary exception text.
        response = {"ok": False, "error": "Deployment probe failed: " + type(error).__name__}
    print(json.dumps(response))
