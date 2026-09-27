"""Durable interactive simulations with live logs and verified process controls.

Interactive jobs are exploration. They do not become accepted study evidence by
finishing successfully. Each run owns a named folder beside its conversation.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from ..mvp_launch import ProcessIdentity, process_identity_matches, read_process_identity
from ..research_service import put

TERMINAL = {"succeeded", "failed", "cancelled", "timed_out", "interrupted"}


def read(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}


def is_live(record):
    try:
        return bool(record) and process_identity_matches(ProcessIdentity.model_validate(record))
    except ValueError:
        return False


def tail(path, limit=24000):
    if not path.is_file() or path.is_symlink():
        return ""
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - limit))
        return stream.read(limit).decode(errors="replace")


def resolve(project, identifier):
    if not re.fullmatch(r"[a-z0-9-]{1,110}", identifier or ""):
        raise ValueError("Unknown simulation")
    root = project / "simulations" / identifier
    if not (root / "request.json").is_file() or root.is_symlink():
        raise ValueError("Unknown simulation")
    return root


def launch(project, payload):
    project = Path(project).resolve()
    name = str(payload.get("name") or "Simulation").strip()[:120]
    command = payload.get("command")
    if not isinstance(command, str) or not command.strip() or len(command) > 32000:
        raise ValueError("Provide a simulation command of at most 32000 characters")
    timeout = float(payload.get("timeout_seconds", 3600))
    if not 1 <= timeout <= 604800:
        raise ValueError("Simulation deadline must be between one second and seven days")
    kind = payload.get("kind", "simulation")
    if kind not in {"simulation", "command"}:
        raise ValueError("Unknown execution kind")
    directory = project / "simulations"
    directory.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:64] or "simulation"
    with (directory / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        number = len(list(directory.glob("*/request.json"))) + 1
        identifier = f"{number:03d}-{slug}"
        while (directory / identifier).exists():
            number += 1
            identifier = f"{number:03d}-{slug}"
        root = directory / identifier
        root.mkdir()
        work = project / "files" if kind == "command" else root / "workspace"
        work.mkdir(exist_ok=True)
        inputs = []
        if kind == "simulation":
            total = 0
            for path in (project / "files").rglob("*"):
                relative = path.relative_to(project / "files")
                if (
                    path.is_symlink()
                    or any(part.startswith(".") for part in relative.parts)
                    or not path.is_file()
                    or not path.resolve().is_relative_to(project / "files")
                ):
                    continue
                total += path.stat().st_size
                if total > 512 * 1024**2:
                    raise ValueError("Simulation inputs exceed 512 MB; use explicit external paths")
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                inputs.append(relative.as_posix())
        request = dict(
            id=identifier,
            name=name,
            command=command,
            kind=kind,
            timeout_seconds=timeout,
            work_directory=str(work),
            inputs=inputs,
            created_at=time.time(),
            scientific_status="exploration",
            source_turn=read(project / "project.json").get("active_turn"),
        )
        put(root / "request.json", request)
        put(root / "state.json", dict(status="queued", updated_at=time.time()))
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        command = [sys.executable, "-m", "conjecture_solver.web.jobs", "--run", str(root)]
        with (root / "controller.log").open("ab") as log:
            process = subprocess.Popen(
                command,
                env=env,
                cwd=project,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        identity = read_process_identity(process.pid, command, run_directory=root)
        if identity:
            put(root / "process.json", identity.model_dump(mode="json"))
        threading.Thread(target=process.wait, daemon=True).start()
        (root / "README.md").write_text(
            f"# {name}\n\nInteractive exploration; not independently accepted evidence.\n\n"
            f"Command:\n```sh\n{command}\n```\n\n"
            "- [Live output](output.log)\n- [Run state](state.json)\n"
            + (
                "- [Inputs and outputs](workspace/)\n"
                if kind == "simulation"
                else "- [Conversation files](../../files/)\n"
            )
        )
    return snapshot(project, identifier)


def snapshot(project, identifier, *, include_files=False):
    root = resolve(Path(project), identifier)
    request, state = read(root / "request.json"), read(root / "state.json")
    live = is_live(read(root / "process.json"))
    status = state.get("status", "queued")
    if status not in TERMINAL and not live and time.time() - request["created_at"] > 3:
        status = "interrupted"
    result = (
        request
        | state
        | dict(
            status=status,
            live=live,
            path=str(root),
            elapsed_seconds=max(0, state.get("finished_at", time.time()) - request["created_at"]),
            output=tail(root / "output.log"),
            controller_output=tail(root / "controller.log", 2000),
        )
    )
    if include_files:
        work = Path(request["work_directory"])
        files = []
        for path in work.rglob("*"):
            relative = path.relative_to(work)
            if path.is_symlink() or any(p.startswith(".") for p in relative.parts):
                continue
            if path.is_file() and path.resolve().is_relative_to(work):
                files.append(dict(name=relative.as_posix(), bytes=path.stat().st_size))
            if len(files) >= 200:
                break
        result["files"] = files
    return result


def list_jobs(project):
    directory = Path(project) / "simulations"
    return [snapshot(project, p.parent.name) for p in sorted(directory.glob("*/request.json"))][
        -100:
    ]


def cancel(project, identifier):
    root = resolve(Path(project), identifier)
    state = read(root / "state.json")
    if state.get("status") in TERMINAL:
        return {"message": "Simulation already finished"}
    if not is_live(read(root / "process.json")):
        raise ValueError("No verified running simulation; no signal sent")
    put(root / "control.json", dict(command="cancel"))
    return {"message": "Simulation stop requested"}


def run(root):
    # Register from the initialized controller too: /proc/cmdline can briefly be
    # unreadable to the parent immediately after exec on some hosts.
    identity = read_process_identity(os.getpid(), run_directory=root)
    if identity:
        put(root / "process.json", identity.model_dump(mode="json"))
    request = read(root / "request.json")
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    deadline = request["created_at"] + request["timeout_seconds"]
    state = dict(status="running", started_at=time.time(), updated_at=time.time())
    put(root / "state.json", state)
    child = None
    try:
        with (root / "output.log").open("ab", buffering=0) as output:
            child = subprocess.Popen(
                ["/bin/bash", "-c", request["command"]],
                cwd=request["work_directory"],
                stdout=output,
                stderr=output,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=os.environ | {"PYTHONUNBUFFERED": "1"},
            )
            identity = read_process_identity(child.pid)
            if identity:
                put(root / "child.json", identity.model_dump(mode="json"))
            while child.poll() is None:
                if stopped or read(root / "control.json").get("command") == "cancel":
                    state["status"] = "cancelled"
                    break
                if time.time() >= deadline:
                    state["status"] = "timed_out"
                    break
                if (root / "output.log").stat().st_size > 64 * 1024**2:
                    state.update(status="failed", error="Console output exceeded 64 MB")
                    break
                time.sleep(0.2)
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            state["returncode"] = child.returncode
            if state["status"] == "running":
                state["status"] = "succeeded" if child.returncode == 0 else "failed"
    except Exception as error:
        state.update(status="failed", error=str(error))
    finally:
        if child:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        state.update(finished_at=time.time(), updated_at=time.time())
        put(root / "state.json", state)
    return 0 if state["status"] == "succeeded" else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path)
    parser.add_argument("--project-dir", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--command")
    parser.add_argument("--timeout-seconds", type=float, default=3600)
    args = parser.parse_args()
    if args.run:
        return run(args.run)
    if not args.project_dir or not args.command:
        parser.error("Supply --project-dir and --command")
    print(
        json.dumps(
            launch(
                args.project_dir,
                dict(name=args.name, command=args.command, timeout_seconds=args.timeout_seconds),
            )
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
