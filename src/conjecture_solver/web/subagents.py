"""Parallel isolated subagents for interactive workspace conversations.

Each subagent runs in its own folder under the conversation's ``simulations/``
directory with a frozen copy of selected project input files, live console output
for the side monitor, and a validated ``HELPER_RESULT.json`` handoff. Subagent
outputs remain isolated until explicitly imported into the conversation's
``files/`` directory.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
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

from pydantic import BaseModel, ConfigDict, Field

from ..mvp_launch import read_process_identity
from ..research_helper_runtime import file_sha as sha
from ..research_helper_runtime import regular_file, stop_native
from ..research_helpers import HelperResult, output_path, relative_path
from ..research_service import fingerprint, put
from .jobs import TERMINAL, read, resolve, selected_inputs, snapshot


class SubagentTaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(default="Subagent task", min_length=2, max_length=120)
    task: str = Field(min_length=8, max_length=8000)
    completion_criteria: str = Field(min_length=8, max_length=4000)
    outputs: list[str] = Field(min_length=1, max_length=16)
    input_files: list[str] | None = None
    timeout_seconds: float = Field(default=600, ge=5, le=7200, allow_inf_nan=False)


def normalize_tasks(payload: dict) -> list[SubagentTaskSpec]:
    raw_tasks = payload.get("tasks")
    if raw_tasks is None:
        raw_tasks = [
            {
                k: payload[k]
                for k in (
                    "name",
                    "task",
                    "completion_criteria",
                    "outputs",
                    "input_files",
                    "timeout_seconds",
                )
                if k in payload
            }
        ]
    if not isinstance(raw_tasks, list) or not 1 <= len(raw_tasks) <= 4:
        raise ValueError("Provide between one and four subagent tasks per dispatch")
    specs = [SubagentTaskSpec.model_validate(item) for item in raw_tasks]
    for spec in specs:
        cleaned = [str(output_path(name)) for name in spec.outputs]
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("Subagent outputs must be distinct relative file paths")
        spec.outputs = cleaned
    return specs


def launch_subagent(project: Path, spec: SubagentTaskSpec, connection_file: Path) -> dict:
    project = Path(project).resolve()
    selected = selected_inputs(project, spec.input_files)
    directory = project / "simulations"
    directory.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", spec.name.lower()).strip("-")[:56] or "subagent"
    with (directory / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        number = len(list(directory.glob("*/request.json"))) + 1
        identifier = f"{number:03d}-subagent-{slug}"
        while (directory / identifier).exists():
            number += 1
            identifier = f"{number:03d}-subagent-{slug}"
        root = directory / identifier
        root.mkdir()
        work = root / "workspace"
        (work / "inputs").mkdir(parents=True, exist_ok=True)
        inputs, input_manifest = [], {}
        for path, relative in selected:
            for dest in (work / relative, work / "inputs" / relative):
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, dest)
            stat = (work / relative).stat()
            with (work / relative).open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            name = relative.as_posix()
            inputs.append(name)
            input_manifest[name] = dict(
                sha256=digest,
                bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                ctime_ns=stat.st_ctime_ns,
            )
        context_data = dict(
            name=spec.name,
            task=spec.task,
            completion_criteria=spec.completion_criteria,
            outputs=spec.outputs,
            inputs={k: v["sha256"] for k, v in input_manifest.items()},
        )
        put(work / "CONTEXT.json", context_data)
        request = dict(
            id=identifier,
            name=spec.name,
            command=f"subagent: {spec.task.splitlines()[0][:120]}",
            kind="simulation",
            subagent=True,
            task=spec.task,
            completion_criteria=spec.completion_criteria,
            expected_outputs=spec.outputs,
            timeout_seconds=spec.timeout_seconds,
            work_directory=str(work),
            inputs=inputs,
            input_manifest=input_manifest,
            context_sha256=sha(work / "CONTEXT.json"),
            connection_file=str(connection_file),
            created_at=time.time(),
            scientific_status="exploration",
            source_turn=read(project / "project.json").get("active_turn"),
        )
        put(root / "request.json", request)
        put(root / "state.json", dict(status="queued", updated_at=time.time()))
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        cmd = [sys.executable, "-m", "conjecture_solver.web.subagents", "--run", str(root)]
        with (root / "controller.log").open("ab") as log:
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=project,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        identity = read_process_identity(process.pid, cmd, run_directory=root)
        if identity:
            put(root / "process.json", identity.model_dump(mode="json"))
        threading.Thread(target=process.wait, daemon=True).start()
    return snapshot(project, identifier)


def subagent_snapshot(project: Path, identifier: str) -> dict:
    base = snapshot(project, identifier, include_files=True)
    root = resolve(Path(project), identifier)
    handoff = read(root / "subagent_result.json")
    if handoff:
        base["subagent_result"] = handoff
    return base


def launch_subagents(
    project: Path,
    connection_factory,
    payload: dict,
) -> dict:
    specs = normalize_tasks(payload)
    wait = bool(payload.get("wait", True))
    launched = []
    for spec in specs:
        conn_path = connection_factory()
        launched.append(launch_subagent(project, spec, conn_path))
    if wait:
        deadline = time.time() + max(s.timeout_seconds for s in specs) + 15
        ids = [item["id"] for item in launched]
        while time.time() < deadline:
            current = [subagent_snapshot(project, i) for i in ids]
            if all(item["status"] in TERMINAL and not item.get("live") for item in current):
                return {"tasks": current, "completed": True}
            time.sleep(0.25)
        return {"tasks": [subagent_snapshot(project, i) for i in ids], "completed": False}
    return {"tasks": launched, "completed": False}


def validate_subagent_handoff(root: Path, request: dict) -> dict:
    work = Path(request["work_directory"])
    handoff = work / "HELPER_RESULT.json"
    with regular_file(handoff, maximum=65536) as stream:
        result = HelperResult.model_validate_json(stream.read(65537))
    if sha(work / "CONTEXT.json") != request["context_sha256"]:
        raise ValueError("Subagent modified its frozen CONTEXT.json")
    for name, expected in request.get("input_manifest", {}).items():
        if sha(work / "inputs" / name) != expected["sha256"]:
            raise ValueError("Subagent modified its frozen inputs/ copy")
    if result.status == "completed" and not set(request["expected_outputs"]) <= set(
        result.artifacts
    ):
        raise ValueError("Completed subagent omitted required deliverables")
    if result.status == "blocked" and not result.unresolved:
        raise ValueError("Blocked subagent handoff must explain what remains unresolved")
    artifacts = {}
    for name in result.artifacts:
        rel = output_path(name).as_posix()
        source = work / rel
        if source.is_symlink() or not source.resolve().is_relative_to(work.resolve()):
            raise ValueError("Subagent deliverable escapes its private workspace")
        if not source.is_file():
            raise ValueError(f"Subagent deliverable {rel} is missing or not a regular file")
        artifacts[rel] = dict(bytes=source.stat().st_size, sha256=sha(source))
    payload = dict(result.model_dump(), artifacts=artifacts)
    put(root / "subagent_result.json", payload)
    return payload


def import_subagent_outputs(
    project: Path,
    identifier: str,
    files: list[str] | None = None,
    *,
    overwrite: bool = False,
) -> list[dict]:
    project = Path(project).resolve()
    root = resolve(project, identifier)
    request = read(root / "request.json")
    handoff = read(root / "subagent_result.json")
    if not handoff or handoff.get("status") not in {"completed", "blocked"}:
        raise ValueError("Subagent has no validated handoff deliverables to import")
    artifacts = handoff.get("artifacts") or {}
    targets = list(artifacts) if files is None else [output_path(f).as_posix() for f in files]
    if not targets:
        raise ValueError("Specify at least one validated deliverable to import")
    for name in targets:
        if name not in artifacts:
            raise ValueError(f"Deliverable {name} is not in the validated subagent handoff")
    work = Path(request["work_directory"]).resolve()
    dest_root = (project / "files").resolve()
    imported = []
    for name in targets:
        info = artifacts[name]
        source = work / relative_path(name)
        if source.is_symlink() or not source.resolve().is_relative_to(work):
            raise ValueError("Subagent artifact escapes its workspace")
        if sha(source) != info["sha256"]:
            raise ValueError(f"Subagent artifact {name} changed after handoff")
        dest = dest_root / relative_path(name)
        if not dest.resolve().is_relative_to(dest_root) or dest.is_symlink():
            raise ValueError("Import destination must remain inside conversation files")
        if dest.exists() and not overwrite:
            raise ValueError(
                f"File {name} already exists in conversation files; set overwrite=True"
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        mode = "wb" if overwrite else "xb"
        with regular_file(source) as src, dest.open(mode) as dst:
            shutil.copyfileobj(src, dst)
        if sha(dest) != info["sha256"]:
            dest.unlink(missing_ok=True)
            raise ValueError("Subagent artifact changed during import")
        receipt = dict(
            subagent=identifier,
            artifact=name,
            destination=name,
            **info,
            imported_at=time.time(),
            scientific_status="exploration",
        )
        folder = project / "subagent_imports"
        folder.mkdir(exist_ok=True)
        key = fingerprint(dict(subagent=identifier, artifact=name))[:20]
        put(folder / f"{identifier}-{key}.json", receipt)
        imported.append(receipt)
    return imported


def build_subagent_prompt(request: dict, work: Path) -> str:
    from ..agent_skills import skill_context

    remaining = max(1.0, request["created_at"] + request["timeout_seconds"] - time.time())
    return (
        "You are an isolated interactive subagent working on a bounded task for the parent "
        "conversation.\n"
        f"Working directory: {work}\n"
        "Read CONTEXT.json and any copied input files in the working directory (preserved under "
        "inputs/). Never modify CONTEXT.json or files inside inputs/.\n"
        f"Task assignment: {request['task']}\n"
        f"Completion criteria: {request['completion_criteria']}\n"
        f"Required deliverables (relative to {work}): {json.dumps(request['expected_outputs'])}\n"
        f"{skill_context()}\n"
        "Write all required deliverable files in the working directory, then write "
        "HELPER_RESULT.json matching this exact JSON schema before finishing:\n"
        f"{json.dumps(HelperResult.model_json_schema())}\n"
        "Use status='completed' only when all required deliverables exist and completion "
        "criteria are satisfied; list all deliverable paths in artifacts and checks performed "
        "in checks. Otherwise use status='blocked' and list blockers in unresolved.\n"
        f"Time remaining: {remaining:.0f} seconds."
    )


def run_subagent(root: Path) -> int:
    root = Path(root).resolve()
    identity = read_process_identity(os.getpid(), run_directory=root)
    if identity:
        put(root / "process.json", identity.model_dump(mode="json"))
    request = read(root / "request.json")
    work = Path(request["work_directory"]).resolve()
    connection_file = Path(request["connection_file"])
    state = dict(status="running", started_at=time.time(), updated_at=time.time())
    put(root / "state.json", state)
    prompt = build_subagent_prompt(request, work)
    (root / "prompt.txt").write_text(prompt)
    timeout = max(5.0, request["created_at"] + request["timeout_seconds"] - time.time())
    deadline = request["created_at"] + request["timeout_seconds"]
    stopped = False

    def handle_stop(*_):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    child = None
    try:
        from ..console_log import ConsoleLog

        cmd = [
            sys.executable,
            "-m",
            "conjecture_solver.workspace_agent",
            "--provider-config",
            str(connection_file),
            "--prompt-file",
            str(root / "prompt.txt"),
            "--cwd",
            str(work),
            "--wall-seconds",
            str(timeout),
        ]
        with (root / "output.log").open("a+b", buffering=0) as output:
            child = subprocess.Popen(
                cmd,
                cwd=work,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=os.environ | {"PYTHONUNBUFFERED": "1"},
            )
            console = ConsoleLog(child.stdout, output, root)
            while child.poll() is None:
                if stopped or read(root / "control.json").get("command") == "cancel":
                    state["status"] = "cancelled"
                    break
                if time.time() >= deadline:
                    state["status"] = "timed_out"
                    break
                time.sleep(0.2)
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                with contextlib.suppress(subprocess.TimeoutExpired):
                    child.wait(timeout=3)
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            console.join()
        if state["status"] == "running":
            if child.returncode != 0:
                raise ValueError(f"Subagent exited with code {child.returncode}")
            handoff = validate_subagent_handoff(root, request)
            state["status"] = "succeeded" if handoff["status"] == "completed" else "failed"
            state["subagent_status"] = handoff["status"]
    except Exception as error:
        state.update(status="failed", error=str(error))
    finally:
        if child and child.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        stop_native(root)
        connection_file.unlink(missing_ok=True)
        state.update(finished_at=time.time(), updated_at=time.time())
        put(root / "state.json", state)
    return 0 if state["status"] == "succeeded" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    return run_subagent(args.run)


if __name__ == "__main__":
    raise SystemExit(main())
