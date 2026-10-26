"""Durable help requests and temporary workers with explicit artifact handoffs.

Helpers are cooperative same-account agents, like the main native worker. Their
private workspaces prevent accidental edit collisions; they are not security
sandboxes. A helper handoff never approves science or edits the parent's files.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .research_helper_runtime import file_sha as sha
from .research_helper_runtime import owned_alive, recover_usage, regular_file, stop_native

ACTIVE = {"queued", "running"}
HELP_ID = r"^help_[a-f0-9]{24}$"


class HelperAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request: str = Field(pattern=HELP_ID)
    task: str = Field(min_length=16, max_length=8000)
    completion_criteria: str = Field(min_length=8, max_length=4000)
    outputs: list[str] = Field(min_length=1, max_length=32)
    timeout_seconds: float = Field(default=600, gt=0, allow_inf_nan=False)


class HelpReply(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request: str = Field(pattern=HELP_ID)
    advice: str = Field(min_length=16, max_length=8000)


class HelperResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: Literal["completed", "blocked"]
    summary: str = Field(min_length=16, max_length=8000)
    artifacts: list[str] = Field(default_factory=list, max_length=32)
    checks: list[str] = Field(default_factory=list, max_length=32)
    unresolved: list[str] = Field(default_factory=list, max_length=32)


def relative_path(name):
    path = Path(name)
    if not name or path.is_absolute() or ".." in path.parts or path == Path("."):
        raise ValueError("Use a nonempty relative file path without parent traversal")
    return path


def output_path(name):
    path = relative_path(name)
    if path.parts[0] in {"inputs", "CONTEXT.json", "HELPER_RESULT.json"}:
        raise ValueError("Helper output must be a new deliverable, not its inputs or handoff file")
    return path


class HelpService:
    def request_help(self, question, *, success_criteria, context="", files=(), key=None):
        """Queue a director decision with frozen, worker-selected context."""
        from .research_finalization import execution_deadline
        from .research_service import fingerprint, put

        if not self.manifest.get("director_policy", {}).get("enabled"):
            raise ValueError("Help dispatch requires an enabled research director")
        if not isinstance(question, str) or not 8 <= len(question.strip()) <= 8000:
            raise ValueError("Describe the help needed in 8 to 8000 characters")
        if not isinstance(success_criteria, str) or not 8 <= len(success_criteria.strip()) <= 4000:
            raise ValueError("State what a useful completed help task should deliver")
        if not isinstance(context, str) or len(context) > 48000:
            raise ValueError(
                "Context must be text of at most 48000 characters; attach larger files"
            )
        if not isinstance(files, (list, tuple)) or len(files) > 32:
            raise ValueError("Attach at most 32 research-relative context files")
        sources = {name: self._source(name) for name in files}
        if (
            sum(path.stat().st_size for path in sources.values())
            > self.storage_limits()["max_experiment_bytes"]
        ):
            raise ValueError("Help context exceeds the experiment storage allowance")
        body = dict(
            question=question.strip(),
            success_criteria=success_criteria.strip(),
            context=context,
            files={name: sha(path) for name, path in sources.items()},
        )
        identifier = "help_" + fingerprint(key if key is not None else body)[:24]
        path = self.root / "help_requests" / f"{identifier}.json"
        with self.lock():
            if path.exists():
                previous = self._read("help_requests", identifier)
                if previous["request_sha256"] != fingerprint(body):
                    raise ValueError("Help request key already belongs to different context")
                return previous
            if self.campaign_closeout():
                raise ValueError("Investigation finished; use a continuation to request new help")
            if time.time() >= execution_deadline(self.manifest):
                raise ValueError("No compute time remains for help dispatch")
            directory = self.root / "help_context" / identifier
            directory.mkdir(parents=True, exist_ok=True)
            for name, source in sources.items():
                target = directory / "inputs" / relative_path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                if sha(target) != body["files"][name]:
                    raise ValueError("Context changed while snapshotting; submit a fresh request")
            # Selected notes and the worker's explicit explanation are context,
            # never a substitute for the attached immutable source/data files.
            put(
                directory / "CONTEXT.json",
                dict(
                    **body,
                    hypothesis=self.manifest["hypothesis"],
                    operator_protocol=self.manifest.get("operator_protocol"),
                    recent_notes=sorted(self._all("notebook"), key=lambda r: r["created_at"])[-12:],
                    evidence_records=[
                        {k: row.get(k) for k in ("id", "status", "purpose")}
                        for row in sorted(self._all("experiments"), key=lambda r: r["created_at"])[
                            -32:
                        ]
                    ],
                    authority="Unreviewed worker context; original scientific requirements apply",
                ),
            )
            record = dict(
                id=identifier,
                status="queued",
                created_at=time.time(),
                request_sha256=fingerprint(body),
                **body,
                tasks=[],
                context_file=str((directory / "CONTEXT.json").relative_to(self.root)),
                context_sha256=sha(directory / "CONTEXT.json"),
            )
            path.parent.mkdir(exist_ok=True)
            put(path, record)
        return record

    def help_status(self, identifier=None):
        self.reconcile_helpers()
        if identifier:
            request = self._read("help_requests", identifier)
            return dict(request, helpers=[self._read("helper_tasks", i) for i in request["tasks"]])
        return dict(requests=self._all("help_requests"), tasks=self._all("helper_tasks"))

    def pending_help(self):
        return [r for r in self._all("help_requests") if r["status"] == "queued"]

    def validate_help_plan(self, tasks, replies):
        for task in tasks:
            self._read("help_requests", task.request)
            if len({str(output_path(name)) for name in task.outputs}) != len(task.outputs):
                raise ValueError("Helper outputs must be distinct")
            for output in task.outputs:
                output_path(output)
        for reply in replies:
            self._read("help_requests", reply.request)

    def assign_helpers(self, tasks, replies, *, director, worker_activity=None):
        """Persist assignments before dispatching their temporary agents."""
        from .research_finalization import execution_deadline
        from .research_service import fingerprint, put

        self.validate_help_plan(tasks, replies)
        assigned = []
        with self.lock():
            for task in tasks:
                request = self._read("help_requests", task.request)
                source = self.root / "help_context" / request["id"]
                if sha(source / "CONTEXT.json") != request["context_sha256"]:
                    raise ValueError("Frozen help context changed")
                for name, expected in request["files"].items():
                    if sha(source / "inputs" / name) != expected:
                        raise ValueError("Frozen help input changed")
            for task in tasks:
                request = self._read("help_requests", task.request)
                spec = task.model_dump(mode="json")
                identifier = (
                    "helper_" + fingerprint(dict(spec=spec, context=request["request_sha256"]))[:24]
                )
                path = self.root / "helper_tasks" / f"{identifier}.json"
                if path.exists():
                    # Repair a crash between task persistence and request linkage.
                    if request["status"] in ACTIVE:
                        request.update(
                            status="running",
                            tasks=list(dict.fromkeys(request["tasks"] + [identifier])),
                        )
                        put(self.root / "help_requests" / f"{request['id']}.json", request)
                    assigned.append(identifier)
                    continue
                if request["status"] not in ACTIVE:
                    raise ValueError("Help request is already resolved; submit a new request")
                if execution_deadline(self.manifest) <= time.time():
                    raise ValueError("No compute time remains for a helper")
                source = self.root / "help_context" / request["id"]
                work = self.root / "helpers" / identifier / "research"
                work.mkdir(parents=True, exist_ok=True)
                frozen = json.loads((source / "CONTEXT.json").read_text())
                frozen["recent_public_worker_activity"] = worker_activity or {}
                put(work / "CONTEXT.json", frozen)
                for name, expected in request["files"].items():
                    original = source / "inputs" / name
                    if sha(original) != expected:
                        raise ValueError("Frozen help input changed")
                    target = work / "inputs" / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, target)
                    if sha(target) != expected:
                        raise ValueError("Frozen help input changed during assignment")
                    target.chmod(0o444)
                path.parent.mkdir(exist_ok=True)
                put(
                    path,
                    dict(
                        id=identifier,
                        status="queued",
                        created_at=time.time(),
                        director=director,
                        **spec,
                        input_hashes=request["files"],
                        context_sha256=sha(work / "CONTEXT.json"),
                        workspace=str(work.relative_to(self.root)),
                        scientific_status="unreviewed",
                    ),
                )
                request.update(
                    status="running", tasks=list(dict.fromkeys(request["tasks"] + [identifier]))
                )
                put(self.root / "help_requests" / f"{request['id']}.json", request)
                assigned.append(identifier)
            for reply in replies:
                request = self._read("help_requests", reply.request)
                request.update(advice=reply.advice, director=director)
                if not request["tasks"]:
                    request.update(status="resolved", resolved_at=time.time())
                put(self.root / "help_requests" / f"{request['id']}.json", request)
        return assigned

    def reconcile_helpers(self):
        from .research_service import put

        if not (self.root / "help_requests").is_dir():
            return
        with self.lock():
            tasks = self._all("helper_tasks")
            for record in tasks:
                if record["status"] not in ACTIVE:
                    continue
                identity = record.get("process_identity")
                lost = (identity and not owned_alive(identity)) or (
                    record["status"] == "running" and not identity
                )
                expired = (
                    not lost
                    and record.get("deadline") is not None
                    and time.time() >= record["deadline"]
                )
                if lost or expired:
                    directory = self.root / "helpers" / record["id"]
                    if expired and owned_alive(identity):
                        # A live controller may be stopped or hung and unable to
                        # run its own watchdog. Stop it before reaping its native
                        # session so it cannot launch more work after expiry.
                        with suppress(ProcessLookupError):
                            os.kill(identity["pid"], signal.SIGKILL)
                    stop_native(directory)
                    record.update(
                        status="cancelled"
                        if record.get("cancel_requested")
                        else "timed_out"
                        if expired
                        else "failed",
                        finished_at=time.time(),
                        error="Helper deadline expired before a validated handoff"
                        if expired
                        else "Helper exited without a validated handoff receipt",
                        usage=recover_usage(directory),
                    )
                    put(self.root / "helper_tasks" / f"{record['id']}.json", record)
            for request in self._all("help_requests"):
                if request["status"] not in ACTIVE:
                    continue
                linked = [r["id"] for r in tasks if r["request"] == request["id"]]
                if linked:
                    request.update(tasks=linked, status="running")
                    if all(
                        self._read("helper_tasks", task)["status"] not in ACTIVE for task in linked
                    ):
                        request.update(status="resolved", resolved_at=time.time())
                    put(self.root / "help_requests" / f"{request['id']}.json", request)

    def dispatch_helpers(self, launch_options, *, maximum=2):
        from .mvp_launch import read_process_identity
        from .research_finalization import execution_deadline
        from .research_service import put

        self.reconcile_helpers()
        if self.campaign_closeout():
            self.cancel_helpers("Investigation finished")
            return []
        started = []
        with self.lock():
            tasks = sorted(self._all("helper_tasks"), key=lambda r: r["created_at"])
            occupied = sum(r["status"] in ACTIVE and bool(r.get("process_identity")) for r in tasks)
            for record in tasks:
                if record["status"] != "queued" or record.get("process_identity"):
                    continue
                if occupied >= maximum:
                    break
                record["deadline"] = min(
                    execution_deadline(self.manifest), time.time() + record["timeout_seconds"]
                )
                if record["deadline"] <= time.time():
                    record.update(status="timed_out", finished_at=time.time())
                else:
                    directory = self.root / "helpers" / record["id"]
                    put(directory / "launch.json", launch_options)
                    # The child waits on this lock until ownership is committed.
                    put(self.root / "helper_tasks" / f"{record['id']}.json", record)
                    command = [
                        sys.executable,
                        "-m",
                        "conjecture_solver.research_helpers",
                        "--root",
                        str(self.root),
                        "--execute",
                        record["id"],
                    ]
                    with (directory / "helper.log").open("a") as log:
                        child = subprocess.Popen(
                            command,
                            stdout=log,
                            stderr=log,
                            stdin=subprocess.DEVNULL,
                            start_new_session=True,
                            env=dict(
                                os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])
                            ),
                        )
                    try:
                        identity = read_process_identity(child.pid, argv=command)
                        if identity is None:
                            raise RuntimeError("Cannot track helper process identity")
                        record["process_identity"] = identity.model_dump(mode="json")
                        put(self.root / "helper_tasks" / f"{record['id']}.json", record)
                    except BaseException:
                        child.kill()
                        child.wait(timeout=5)
                        raise
                    occupied += 1
                    started.append(record["id"])
                    continue
                put(self.root / "helper_tasks" / f"{record['id']}.json", record)
        return started

    def cancel_helpers(self, reason):
        from .research_service import put

        with self.lock():
            for request in self._all("help_requests"):
                if request["status"] == "queued":
                    request.update(
                        status="resolved", resolved_at=time.time(), cancellation_reason=reason
                    )
                    put(self.root / "help_requests" / f"{request['id']}.json", request)
            for record in self._all("helper_tasks"):
                if record["status"] not in ACTIVE:
                    continue
                record.update(cancel_requested=True, cancellation_reason=reason)
                if record.get("process_identity"):
                    identity = record["process_identity"]
                    if owned_alive(identity):
                        with suppress(ProcessLookupError):
                            os.kill(identity["pid"], signal.SIGTERM)
                    else:
                        directory = self.root / "helpers" / record["id"]
                        stop_native(directory)
                        record.update(
                            status="cancelled",
                            finished_at=time.time(),
                            usage=recover_usage(directory),
                        )
                else:
                    record.update(status="cancelled", finished_at=time.time())
                put(self.root / "helper_tasks" / f"{record['id']}.json", record)

    def import_helper_artifact(self, task, artifact, destination):
        """Explicitly copy a verified handoff artifact; never overwrite worker edits."""
        from .research_service import fingerprint, put

        record = self._read("helper_tasks", task)
        info = record.get("result", {}).get("artifacts", {}).get(artifact)
        if record["status"] not in {"completed", "blocked"} or info is None:
            raise ValueError("No validated helper artifact is available")
        source = self.root / "helper_results" / record["id"] / relative_path(artifact)
        if source.is_symlink() or sha(source) != info["sha256"]:
            raise ValueError("Helper artifact changed after handoff")
        target = self.work / relative_path(destination)
        if not target.resolve().is_relative_to(self.work.resolve()) or target.is_symlink():
            raise ValueError("Destination must remain inside the research workspace")
        target.parent.mkdir(parents=True, exist_ok=True)
        with regular_file(source) as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        if sha(target) != info["sha256"]:
            target.unlink()
            raise ValueError("Helper artifact changed while importing")
        receipt = dict(
            task=task,
            artifact=artifact,
            destination=destination,
            **info,
            imported_at=time.time(),
            scientific_status="unreviewed",
        )
        folder = self.root / "helper_imports"
        folder.mkdir(exist_ok=True)
        key = fingerprint(
            dict(
                task=task,
                artifact=str(relative_path(artifact)),
                destination=str(relative_path(destination)),
            )
        )
        put(folder / (record["id"] + "-" + key[:24] + ".json"), receipt)
        return receipt


def finish_helper(service, identifier, returncode, *, usage=None, timed_out=False):
    """Validate explicit completion, freeze artifacts, then publish the terminal state."""
    from .research_service import put

    with service.lock():
        record = service._read("helper_tasks", identifier)
        work = service.root / record["workspace"]
        record.update(returncode=returncode, finished_at=time.time(), usage=usage or {})
        try:
            if record.get("cancel_requested"):
                record["status"] = "cancelled"
            elif timed_out:
                record["status"] = "timed_out"
            elif returncode:
                raise ValueError(f"Helper process failed with exit code {returncode}")
            else:
                handoff = work / "HELPER_RESULT.json"
                with regular_file(handoff, maximum=65536) as stream:
                    result = HelperResult.model_validate_json(stream.read(65537))
                if sha(work / "CONTEXT.json") != record["context_sha256"]:
                    raise ValueError("Helper changed its frozen context")
                if result.status == "completed" and not set(record["outputs"]) <= set(
                    result.artifacts
                ):
                    raise ValueError("Completed helper omitted required deliverables")
                if result.status == "blocked" and not result.unresolved:
                    raise ValueError("Blocked handoff must explain what remains unresolved")
                for name, expected in record["input_hashes"].items():
                    if sha(work / "inputs" / name) != expected:
                        raise ValueError("Helper changed its frozen context inputs")
                artifacts = {}
                for name in result.artifacts:
                    source = work / output_path(name)
                    if source.is_symlink() or not source.resolve().is_relative_to(work.resolve()):
                        raise ValueError("Helper artifact escapes its private workspace")
                    if not source.is_file():
                        raise ValueError("Helper artifact is missing or not a regular file")
                    artifacts[name] = dict(bytes=source.stat().st_size)
                if (
                    sum(a["bytes"] for a in artifacts.values())
                    > service.storage_limits()["max_experiment_bytes"]
                ):
                    raise ValueError("Helper result exceeds the experiment storage allowance")
                for name, info in artifacts.items():
                    info["sha256"] = sha(work / name)
                    target = service.root / "helper_results" / identifier / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with regular_file(work / name) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    if sha(target) != info["sha256"]:
                        raise ValueError("Helper output changed during handoff")
                    target.chmod(0o444)
                record.update(
                    status=result.status, result=dict(result.model_dump(), artifacts=artifacts)
                )
        except (OSError, ValueError) as error:
            record.update(status="failed", error=str(error))
        put(service.root / "helper_tasks" / f"{identifier}.json", record)
    service.reconcile_helpers()
    return record


def execute_helper(root, identifier):
    from .agent_supervisor import AgentSupervisor
    from .research_service import ResearchService, put

    service = ResearchService(root)
    with service.lock():
        record = service._read("helper_tasks", identifier)
        if record["status"] != "queued" or record.get("cancel_requested"):
            return
        identity = record.get("process_identity")
        if not identity or identity["pid"] != os.getpid() or not owned_alive(identity):
            return  # Dispatcher died before committing ownership; queued work can retry.
        record.update(status="running", started_at=time.time())
        put(service.root / "helper_tasks" / f"{identifier}.json", record)
    directory = service.root / "helpers" / identifier
    options = json.loads((directory / "launch.json").read_text())
    parent_control = options.pop("parent_control", None)
    args = argparse.Namespace(
        **options,
        campaign=service.root,
        state_dir=directory,
        workflow="frontier",
        wall_seconds=record["timeout_seconds"],
        turn_seconds=record["timeout_seconds"],
    )

    class HelperRunner(AgentSupervisor):
        def boundary(self):
            if parent_control and Path(parent_control).is_file():
                control = json.loads(Path(parent_control).read_text())
                if control.get("command") in {"pause", "cancel"}:
                    self.cancelled = True
            return super().boundary()

    from .agent_skills import skill_context

    runner = HelperRunner(args)
    runner.state["deadline"] = record["deadline"]
    runner.record_review_identity = True
    signal.signal(signal.SIGTERM, lambda *_: setattr(runner, "cancelled", True))
    prompt = f"""You are a temporary research helper assigned by the director.
Read CONTEXT.json and the files under inputs/ before working. They carry the
requesting worker's question, context, scientific requirements and evidence.
Your assignment: {record["task"]}
Completion criteria: {record["completion_criteria"]}
Required deliverables: {json.dumps(record["outputs"])}
Work only in {directory / "research"}. Preserve inputs/. Write separate output
files; never edit the parent worker's workspace or campaign records. You may
write code and run bounded local checks. Production simulations and scientific
acceptance remain with the parent worker's recorded workflow. Do not launch
additional agents or daemonize/detach subprocesses. Return source/analysis
artifacts for the parent to inspect.
{skill_context()}
Before exiting, write HELPER_RESULT.json matching this schema:
{json.dumps(HelperResult.model_json_schema())}
Use completed only when the specified deliverables and criteria are met; list
the checks actually performed and remaining limitations. Otherwise use blocked
and explain the obstacle. Process exit or saying 'done' is not a handoff.
Time remaining: {max(0, record["deadline"] - time.time()):.0f} seconds.
"""
    turn = directory / "turn-00001"
    turn.mkdir(exist_ok=True)
    returncode = 1
    try:
        returncode = runner.launch(turn, prompt)
    finally:
        stop_native(directory)
        if runner.cancelled:
            with service.lock():
                current = service._read("helper_tasks", identifier)
                current["cancel_requested"] = True
                put(service.root / "helper_tasks" / f"{identifier}.json", current)
        finish_helper(
            service,
            identifier,
            returncode,
            timed_out=returncode == 124 or time.time() >= record["deadline"],
            usage={k: v for k, v in runner.state.items() if k.startswith("usage_")},
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--execute", required=True)
    arguments = parser.parse_args()
    execute_helper(arguments.root, arguments.execute)
