"""Explicit cooperative execution; NOT a kernel security sandbox."""

import ctypes
import hashlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path

import psutil


def digest(path):
    h = hashlib.sha256()
    paths = sorted(path.rglob("*")) if path.is_dir() else [path]
    for p in paths:
        if p.is_symlink():
            raise ValueError("symlink in copied experiment input")
        if p.is_file():
            h.update(str(p.relative_to(path) if path.is_dir() else p.name).encode())
            with p.open("rb") as f:
                for b in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(b)
    return h.hexdigest()


def main():
    if os.geteuid() == 0:
        raise RuntimeError("cooperative process fallback refuses root")
    parent_pid = os.getppid()
    # The durable worker owns this runner even when an operator kills the worker.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "Cannot establish parent-death notification")
    if os.getppid() != parent_pid:
        return 125
    args = sys.argv[1:]
    bindings = []
    env = {}
    dirs = []
    cwd = "/work"
    while args and args[0].startswith("--"):
        flag = args.pop(0)
        if flag in ("--unshare-all", "--die-with-parent", "--new-session", "--clearenv"):
            continue
        if flag in ("--ro-bind", "--bind", "--dev-bind"):
            bindings.append((flag, args.pop(0), args.pop(0)))
        elif flag == "--setenv":
            key, value = args.pop(0), args.pop(0)
            env[key] = value
        elif flag == "--chdir":
            cwd = args.pop(0)
        elif flag in ("--dir", "--tmpfs", "--dev", "--proc"):
            dest = args.pop(0)
            dirs.append(dest)
            if flag in ("--dev", "--proc"):
                bindings.append(("--bind", dest, dest))
        else:
            raise ValueError(f"unsupported fallback option {flag}")
    if not args:
        raise ValueError("missing executable")
    max_rss = int(os.environ.get("SIMJECTURE_PROCESS_MAX_RSS", 4 * 1024**3))
    with tempfile.TemporaryDirectory(prefix="simjecture-proot-") as temporary:
        root = Path(temporary) / "root"
        root.mkdir()
        (root / "bin").symlink_to("usr/bin")
        (root / "sbin").symlink_to("usr/sbin")
        for d in dirs:
            (root / d.lstrip("/")).mkdir(parents=True, exist_ok=True)
        native = env.get("SIMJECTURE_EXECUTION_BACKEND") == "process-cooperative"
        workspace = next((Path(s) for _, s, d in bindings if d == "/work"), None)
        cmd = [shutil.which("proot") or "/usr/bin/proot", "-r", str(root), "-w", cwd]
        sealed = []
        for i, (kind, source, dest) in enumerate(bindings):
            if kind == "--ro-bind" and dest.startswith("/work/"):
                original = Path(source)
                copy = (
                    workspace / dest.removeprefix("/work/")
                    if native and workspace is not None
                    else Path(temporary) / f"input-{i}" / original.name
                )
                copy.parent.mkdir(parents=True, exist_ok=True)
                if original.is_dir():
                    shutil.copytree(original, copy, dirs_exist_ok=native)
                else:
                    shutil.copy2(original, copy)
                if native:
                    for p in list(copy.rglob("*")) if copy.is_dir() else [copy]:
                        if p.is_file():
                            p.chmod(p.stat().st_mode & ~0o222)
                sealed.append((copy, digest(copy)))
                source = str(copy)
            cmd.extend(["-b", f"{source}:{dest}!"])
        cmd.extend(args)
        if native:
            mappings = sorted(
                [
                    (dest.rstrip("/"), source)
                    for _, source, dest in bindings
                    if not dest.startswith("/work/")
                ],
                key=lambda x: len(x[0]),
                reverse=True,
            ) + [("/tmp", str(root / "tmp"))]

            def translate(value):
                for dest, source in mappings:
                    if value == dest or value.startswith(dest + "/"):
                        return str(Path(source)) + value[len(dest) :]
                return value

            env = {k: ":".join(translate(part) for part in v.split(":")) for k, v in env.items()}
            cmd = [translate(value) for value in args]
            cwd = translate(cwd)
        else:
            cwd = temporary
        proc = subprocess.Popen(cmd, env=env, cwd=cwd, start_new_session=True)

        def stop(*_):
            with suppress(psutil.NoSuchProcess):
                for child in psutil.Process(proc.pid).children(recursive=True):
                    with suppress(psutil.NoSuchProcess):
                        child.kill()
            with suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        try:
            while proc.poll() is None:
                try:
                    parent = psutil.Process(proc.pid)
                    rss = 0
                    for child in [parent, *parent.children(recursive=True)]:
                        with suppress(psutil.NoSuchProcess):
                            rss += child.memory_info().rss
                    if rss > max_rss:
                        print("cooperative runner: resident-memory limit exceeded", file=sys.stderr)
                        stop()
                except psutil.NoSuchProcess:
                    pass
                time.sleep(0.05)
            rc = proc.wait()
        finally:
            stop()
        for path, expected in sealed:
            if digest(path) != expected:
                print("cooperative runner: sealed input modified", file=sys.stderr)
                return 125
        return rc if rc >= 0 else 128 - rc


if __name__ == "__main__":
    sys.exit(main())
