"""Operator-owned executor service for hosted scientific code.

Only the gateway UID can submit requests. Commands execute as separate reserved
UIDs with Landlock, seccomp and resource limits; the daemon never executes model
code as root. The gateway should use a private Unix HTTP socket on this profile.
"""

import argparse
import base64
import fnmatch
import hashlib
import io
import json
import math
import os
import pwd
import select
import shutil
import socket
import socketserver
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from contextlib import suppress
from pathlib import Path

from .confinement import landlock_abi

MAX_FRAME = 256 * 1024**2
MAX_FILES = 50000
MAX_BYTES = 512 * 1024**2


def safe_name(name):
    if not isinstance(name, str):
        raise ValueError("Use a filename string")
    p = Path(name)
    if (
        not p.parts
        or p.is_absolute()
        or ".." in p.parts
        or "\x00" in name
        or len(name) > 512
        or any(part.startswith(".executor-") for part in p.parts)
    ):
        raise ValueError("Files must remain in the experiment workspace")
    return p


def unpack(data, directory, uid):
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) > MAX_FILES:
            raise ValueError("Too many input files")
        for entry in archive.infolist():
            name = safe_name(entry.filename)
            mode = entry.external_attr >> 16
            if entry.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError("Only regular input files are admitted")
            total += entry.file_size
            if total > MAX_BYTES or entry.file_size > 128 * 1024**2:
                raise ValueError("Input storage allowance exceeded")
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, path.open("xb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            path.chmod(0o700 if mode & 0o111 else 0o600)
    for path in [directory, *directory.rglob("*")]:
        os.chown(path, uid, uid, follow_symlinks=False)
        if path.is_dir():
            path.chmod(0o700)


def processes(uid):
    import psutil

    rows = []
    for p in psutil.process_iter(("pid", "uids", "memory_info", "create_time")):
        try:
            if p.info["uids"].real == uid:
                rows.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return rows


def stop_uid(uid):
    # Dedicated, configured UIDs only. psutil identity checks guard PID reuse.
    import psutil

    rows = processes(uid)
    for p in rows:
        with suppress(psutil.NoSuchProcess):
            p.kill()
    _, alive = psutil.wait_procs(rows, timeout=5)
    if any(p.status() != psutil.STATUS_ZOMBIE for p in alive):
        raise RuntimeError("Unable to stop all executor processes")


def collect(directory, outputs):
    stream = io.BytesIO()
    total, count = 0, 0
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(directory).as_posix()
            if not any(
                fnmatch.fnmatchcase(relative, p) or relative.startswith(p.rstrip("/") + "/")
                for p in outputs
            ):
                continue
            # All job-UID processes are dead before collection, eliminating the
            # attacker-controlled path/symlink race while the root collector reads.
            if path.is_symlink() or not path.is_file():
                continue
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("Outputs must be regular, unlinked files")
            total += info.st_size
            count += 1
            if total > MAX_BYTES or count > MAX_FILES:
                raise ValueError("Output storage allowance exceeded")
            archive.write(path, relative)
    return stream.getvalue()


def console_text(stream):
    # Read the original root-owned descriptor. The job owns its working
    # directory and can replace pathnames, including the console filename.
    # Reopening that path as root would cross the filesystem boundary.
    stream.seek(0, os.SEEK_END)
    length = stream.tell()
    stream.seek(max(0, length - 4000))
    tail = stream.read()
    try:
        text = tail.decode("utf-8")
    except UnicodeDecodeError:
        text = tail.decode("utf-8", errors="replace")
        if text.count("\ufffd") > 3:
            return (
                f"Binary console output omitted ({length} bytes). "
                "Redirect it to a declared output file."
            )
    if b"\x00" in tail:
        return (
            f"Binary console output omitted ({length} bytes). "
            "Redirect it to a declared output file."
        )
    return text


def execute(request, config, uid, connection=None):
    if set(request) != {"command", "inputs", "outputs", "timeout"}:
        raise ValueError("Invalid executor request")
    command, timeout, outputs = request["command"], request["timeout"], request["outputs"]
    if not isinstance(command, str) or not 1 <= len(command) <= 12000:
        raise ValueError("Command must be bounded text")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or not 0 < timeout <= 86400
    ):
        raise ValueError("Invalid execution time")
    if (
        not isinstance(outputs, list)
        or len(outputs) > 64
        or not all(isinstance(p, str) for p in outputs)
    ):
        raise ValueError("Declare bounded output paths")
    for p in outputs:
        safe_name(p)
    encoded = request["inputs"]
    if not isinstance(encoded, str) or len(encoded) > MAX_FRAME:
        raise ValueError("Input frame is too large")
    stop_uid(uid)
    parent = Path(config["work_root"])
    parent.mkdir(parents=True, exist_ok=True)
    parent.chmod(0o711)
    directory = Path(tempfile.mkdtemp(prefix="lab-", dir=parent))
    started = time.time()
    process = None
    try:
        unpack(base64.b64decode(encoded, validate=True), directory, uid)
        for name in ("tmp", ".home", ".cache", ".mpl"):
            path = directory / name
            path.mkdir(exist_ok=True)
            os.chown(path, uid, uid)
            path.chmod(0o700)
        gpu_ids = config.get("gpu_ids") or [""]
        gpu = gpu_ids[uid % len(gpu_ids)]
        environment = {
            "PATH": config["path"],
            "HOME": str(directory / ".home"),
            "TMPDIR": str(directory / "tmp"),
            "XDG_CACHE_HOME": str(directory / ".cache"),
            "MPLCONFIGDIR": str(directory / ".mpl"),
            "MPLBACKEND": "Agg",
            "OMP_NUM_THREADS": str(config.get("cpus", 4)),
            "OPENBLAS_NUM_THREADS": "1",
            "PYTHONUNBUFFERED": "1",
            "LANG": "C.UTF-8",
            "CUDA_VISIBLE_DEVICES": str(gpu),
            "OMPI_MCA_orte_tmpdir_base": str(directory / "tmp"),
            "LD_LIBRARY_PATH": config.get("library_path", ""),
        }
        devices = [
            "/dev/null",
            "/dev/zero",
            "/dev/random",
            "/dev/urandom",
            "/dev/nvidiactl",
            "/dev/nvidia-uvm",
            "/dev/nvidia-uvm-tools",
            f"/dev/nvidia{gpu}",
        ]
        # CUDA enumerates visible devices before applying CUDA_VISIBLE_DEVICES;
        # ordinal IDs need not equal the host's device minor numbers.
        devices.extend(str(path) for path in Path("/dev").glob("nvidia[0-9]*"))
        devices += ["/dev/nvidia-modeset", "/dev/nvidia-caps"]

        policy = directory / ".executor-policy.json"
        policy.write_text(
            json.dumps(
                {
                    "uid": uid,
                    "work": str(directory),
                    "cpus": config.get("cpus", 4),
                    "timeout": timeout,
                    "read_only": config["read_only"],
                    "devices": devices,
                    "environment": environment,
                }
            )
        )
        policy.chmod(0o600)
        argv = [sys.executable, "-I", "-m", "conjecture_solver.public.lab_child", str(policy)]
        trace_this = config.get("operator_trace") and "warpx" in command
        if trace_this:
            argv = [
                "/usr/bin/strace",
                "-f",
                "-o",
                str(directory / ".executor-trace"),
                "-e",
                "trace=all",
                *argv,
            ]

        # Do not put the user's command/source in the globally visible argv.
        with (
            (directory / ".executor-stdout").open("w+b") as out,
            (directory / ".executor-stderr").open("w+b") as err,
        ):
            process = subprocess.Popen(
                argv,
                cwd=directory,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=out,
                stderr=err,
                start_new_session=True,
                close_fds=True,
            )
            process.stdin.write(command.encode() + b"\n")
            process.stdin.close()
            reason = None
            last_storage_check = 0
            while process.poll() is None:
                rows = processes(uid)
                rss = sum(p.info["memory_info"].rss for p in rows)
                if time.time() - started > timeout:
                    reason = "time_limit"
                elif rss > config.get("memory_bytes", 4 * 1024**3):
                    reason = "memory_limit"
                elif (
                    connection
                    and select.select([connection], [], [], 0)[0]
                    and not connection.recv(1, socket.MSG_PEEK)
                ):
                    reason = "caller_disconnected"
                if time.time() - last_storage_check > 1:
                    last_storage_check = time.time()
                    count, size = 0, 0
                    for path in directory.rglob("*"):
                        if path.is_file() and not path.is_symlink():
                            count += 1
                            size += path.stat().st_size
                    for path in Path("/dev/shm").rglob("*"):
                        with suppress(OSError):
                            info = path.lstat()
                            if info.st_uid == uid:
                                count += 1
                                size += info.st_size
                    if size > MAX_BYTES or count > MAX_FILES:
                        reason = "storage_limit"
                if reason:
                    stop_uid(uid)
                    break
                time.sleep(0.15)
            process.wait(timeout=5)
            stop_uid(uid)
            stdout, stderr = console_text(out), console_text(err)
        stop_uid(uid)
        payload = collect(directory, outputs)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
        missing = [
            pattern
            for pattern in outputs
            if not any(
                fnmatch.fnmatchcase(name, pattern) or name.startswith(pattern.rstrip("/") + "/")
                for name in names
            )
        ]
        return {
            "returncode": process.returncode,
            "stop_reason": reason,
            "seconds": time.time() - started,
            "uid": uid,
            "landlock_abi": landlock_abi(),
            "executor_revision": hashlib.sha256(
                b"".join(
                    Path(__file__).with_name(name).read_bytes()
                    for name in ("lab_broker.py", "lab_child.py", "confinement.py")
                )
            ).hexdigest(),
            "stdout": stdout,
            "stderr": stderr,
            "outputs": base64.b64encode(payload).decode(),
            "missing": missing,
            **(
                {"operator_trace": (directory / ".executor-trace").read_text()[:2000000]}
                if trace_this
                else {}
            ),
        }
    finally:
        stop_uid(uid)
        for path in sorted(Path("/dev/shm").rglob("*"), key=lambda p: len(p.parts), reverse=True):
            with suppress(OSError):
                if path.lstat().st_uid == uid:
                    if path.is_dir() and not path.is_symlink():
                        path.rmdir()
                    else:
                        path.unlink()
        if process:
            with suppress(Exception):
                process.wait(timeout=5)
        shutil.rmtree(directory)


class Broker(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, config):
        self.config = config
        self.slots = list(config["uids"])
        self.lock = threading.Condition()
        path = Path(config["socket"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.chmod(0o710)
        os.chown(path.parent, 0, config.get("gateway_gid", config["gateway_uid"]))
        path.unlink(missing_ok=True)
        super().__init__(str(path), Handler)
        os.chown(path, 0, config.get("gateway_gid", config["gateway_uid"]))
        path.chmod(0o660)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        _, peer, _ = struct.unpack(
            "3i", self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )
        if peer not in {0, self.server.config["gateway_uid"]}:
            return
        self.request.settimeout(30)
        with self.request.makefile("rb") as stream:
            body = stream.readline(MAX_FRAME + 1)
        if not body.endswith(b"\n") or len(body) > MAX_FRAME:
            return
        with self.server.lock:
            while not self.server.slots:
                self.server.lock.wait(timeout=1)
            uid = self.server.slots.pop()
        try:
            self.request.settimeout(None)
            result = execute(json.loads(body), self.server.config, uid, self.request)
        except Exception as error:
            result = {"error": str(error), "error_type": type(error).__name__}
        finally:
            with self.server.lock:
                self.server.slots.append(uid)
                self.server.lock.notify()
        with suppress(OSError):
            self.request.sendall(json.dumps(result).encode() + b"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    if os.getuid() != 0:
        parser.error("The executor daemon requires operator/root startup")
    config = json.loads(args.config.read_text())
    if len(set(config["uids"])) != len(config["uids"]) or not all(
        isinstance(uid, int)
        and uid >= 60000
        and pwd.getpwuid(uid).pw_name.startswith("simjecture-lab-")
        for uid in config["uids"]
    ):
        parser.error("Configure dedicated simjecture-lab-* UIDs only")
    landlock_abi()
    for uid in config["uids"]:
        stop_uid(uid)
    with Broker(config) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
