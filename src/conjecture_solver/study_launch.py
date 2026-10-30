"""Native study launch contracts shared by CLI and browser."""

from __future__ import annotations

import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .agent_routes import review_route
from .mvp_launch import (
    MVPLaunchPlan,
    MVPLaunchRequest,
    ResumeError,
    load_supervisor_record,
    process_identity_matches,
)
from .research_service import ResearchService, put
from .study_status import read, supervisor_directory


class NativeStudyRequest(MVPLaunchRequest):
    capability_directory: str | None = "auto"
    execution_backend: Literal["bubblewrap", "proot-cooperative", "process-cooperative"] = (
        "bubblewrap"
    )
    mode: Literal["minimal"] = "minimal"
    engine: Literal["native"] = "native"
    dsh_session_id: None = None
    backend: Literal["codex-glm", "codex", "grok", "agy", "builtin"] = "codex-glm"
    completion_policy: Literal["answer", "repair"] = "repair"
    provider_config: str | None = None
    model: str | None = None
    judge_model: str | None = None
    judge_backend: Literal["codex-glm", "codex", "grok", "agy", "builtin"] | None = None
    judge_executable: str | None = None
    judge_provider_config: str | None = None
    reasoning_effort: Literal["low", "medium", "high", "xhigh", "max", "ultra"] | None = None
    judge_reasoning_effort: Literal["low", "medium", "high", "xhigh", "max", "ultra"] | None = None
    director_model: str | None = None
    director_reasoning_effort: Literal["low", "medium", "high", "xhigh", "max", "ultra"] | None = (
        None
    )
    director_enabled: bool = Field(default=True, strict=True)
    attention_config: str | None = None
    allow_solver_development: bool | None = Field(default=True, strict=True)
    agent_executable: str | None = None
    machine_registry: str | None = None
    machine_ids: list[str] = []
    method_review_scope: Literal["study", "used_instruments"] = "study"

    max_experiment_bytes: int | None = Field(default=None, strict=True, gt=0, le=sys.maxsize)
    max_total_bytes: int | None = Field(default=None, strict=True, gt=0, le=sys.maxsize)
    report_reserve_seconds: float | None = Field(
        default=None, strict=True, gt=0, allow_inf_nan=False
    )

    @model_validator(mode="after")
    def validate_initial_budgets(self):
        if (
            self.max_experiment_bytes is not None
            and self.max_total_bytes is not None
            and self.max_total_bytes < self.max_experiment_bytes
        ):
            raise ValueError("Total storage allowance must cover one experiment")
        if (
            self.report_reserve_seconds is not None
            and self.report_reserve_seconds >= self.max_wall_seconds
        ):
            raise ValueError("Report reserve must be smaller than the wall budget")
        return self


def materialize_native(request, *, resume=False):
    if request.mode != "minimal" or request.engine != "native":
        from .mvp_launch import REMOVED_WORKFLOW_MESSAGE

        raise ValueError(REMOVED_WORKFLOW_MESSAGE)
    root = Path(request.output_directory).expanduser().resolve()
    record = root / "study-launch.json"
    existing = read(record)
    if (
        not resume
        and not existing
        and request.mode == "minimal"
        and (request.allow_solver_development is None)
    ):
        raise ValueError("Choose a boolean solver development permission for a new study")
    model = request.model or ("glm-5.3" if request.backend == "codex-glm" else None)
    if not model:
        raise ValueError("Choose an explicit model for this backend")
    executable = request.agent_executable or request.backend
    if request.backend == "builtin":
        from .workspace_agent import read_provider, require_runtime

        require_runtime()
        read_provider(request.provider_config)
        if request.mode != "minimal":
            raise ValueError("Built-in research uses minimal mode")
    elif shutil.which(executable) is None:
        raise ValueError(f"Backend executable {executable!r} not found; install its CLI first")
    review = review_route(
        request.backend,
        executable,
        request.provider_config,
        judge_backend=request.judge_backend,
        judge_executable=request.judge_executable,
        judge_provider_config=request.judge_provider_config,
    )
    if review["backend"] == "builtin":
        from .workspace_agent import read_provider, require_runtime

        require_runtime()
        read_provider(review["provider_config"], api_only=True)
    elif shutil.which(review["executable"]) is None:
        raise ValueError("Reviewer executable not found; install its CLI first")
    if request.engine != "native":
        raise ValueError("Native study modes cannot use the legacy DSH engine")
    identity = load_supervisor_record(root) if root.exists() else None
    if identity and process_identity_matches(identity):
        raise ResumeError("Study is already running; attach to its status")
    saved_request = existing.get("request", {})
    if request.capability_directory == "auto":
        from .web.inventory import automatic_tool_paths, freeze_available_tools

        if existing:
            capabilities = saved_request.get("capability_directory")
        elif request.machine_ids:
            capabilities = None  # Frozen workers advertise their own installed tools.
        else:
            capabilities = freeze_available_tools(
                automatic_tool_paths(),
                root.parent / ".simjecture-tools" / uuid.uuid4().hex,
            )
        request = request.model_copy(
            update={
                "capability_directory": capabilities,
                "method_review_scope": saved_request.get("method_review_scope", "study")
                if existing
                else "used_instruments",
            }
        )
    elif request.capability_directory == "none":
        request = request.model_copy(update={"capability_directory": None})
    if saved_request:
        # Omitted optional budget fields inherit the saved launch contract on resume.
        if resume:
            request = request.model_copy(
                update={
                    name: saved_request.get(name)
                    for name in (
                        "max_experiment_bytes",
                        "max_total_bytes",
                        "report_reserve_seconds",
                    )
                    if name not in request.model_fields_set
                }
            )
        if "director_enabled" not in saved_request:
            saved_request = saved_request | {"director_enabled": False}
        if "allow_solver_development" not in saved_request:
            saved_request = saved_request | {"allow_solver_development": None}
        saved_request = NativeStudyRequest.model_validate(saved_request).model_dump(mode="json")
    if existing and saved_request != request.model_dump(mode="json"):
        raise ValueError("Existing study launch contract differs")
    if resume and not existing:
        raise ResumeError("No saved native launch contract")
    from .execution import require_execution_backend

    pool = None
    if request.machine_ids:
        from .execution_pool import MachineRegistry

        if request.mode != "minimal" or not request.machine_registry:
            raise ValueError("Execution pools require minimal mode and a machine registry")
        if not resume:
            pool = MachineRegistry(request.machine_registry).freeze(request.machine_ids)
        execution_probe = {
            "backend": "worker-pool",
            "available": True,
            "machines": request.machine_ids,
        }
        if request.capability_directory:
            require_execution_backend(request.execution_backend)
    else:
        execution_probe = require_execution_backend(request.execution_backend)
    protocol = (
        request.instruction or "Investigate the stated hypothesis within its scientific scope."
    )
    if not resume:
        if root.exists() and any(root.iterdir()):
            raise ValueError("Choose a new empty study directory")
        service = ResearchService.create(
            root,
            request.hypothesis,
            wall_seconds=request.max_wall_seconds,
            capabilities=request.capability_directory,
            execution_backend=request.execution_backend,
            completion_policy=request.completion_policy,
            execution_pool=pool,
            allow_solver_development=request.allow_solver_development,
            method_review_scope=request.method_review_scope,
            max_experiment_bytes=request.max_experiment_bytes,
            max_total_bytes=request.max_total_bytes,
            report_reserve_seconds=request.report_reserve_seconds,
        )
        service.freeze_protocol(protocol)
    directory = Path(existing.get("state_dir") or root / "supervisor")
    if resume:
        state = read(directory / "state.json")
        if state.get("status") in ["completed", "cancelled", "budget_exhausted"]:
            raise ResumeError("Study is terminal; create a new study to change its budget")
        deadline = (
            read(root / "research.json").get("deadline", state.get("deadline"))
            if request.mode == "minimal"
            else state.get("deadline")
        )
        if deadline is not None and deadline <= time.time():
            raise ResumeError("The current wall-time deadline has expired")
        (directory / "control.json").unlink(missing_ok=True)
    operator = root / "operator_input"
    operator.mkdir(exist_ok=True)
    hypothesis = operator / "hypothesis.txt"
    instructions = operator / "instruction.txt"
    if not resume:
        hypothesis.write_text(request.hypothesis)
        instructions.write_text(protocol)
    argv = [
        sys.executable,
        "-m",
        "conjecture_solver.study",
        "--campaign",
        str(root),
        "--state-dir",
        str(directory),
        "--hypothesis-file",
        str(hypothesis),
        "--instructions-file",
        str(instructions),
        "--mode",
        request.mode,
        "--execution-backend",
        request.execution_backend,
        "--backend",
        request.backend,
        "--model",
        model,
        "--judge-model",
        request.judge_model or model,
        "--wall-seconds",
        str(request.max_wall_seconds),
        "--turn-seconds",
        str(min(request.max_command_seconds, request.max_wall_seconds)),
    ]
    for name in ("max_experiment_bytes", "max_total_bytes", "report_reserve_seconds"):
        value = getattr(request, name)
        if value is not None:
            argv += ["--" + name.replace("_", "-"), str(value)]
    if request.capability_directory:
        argv += ["--capabilities", request.capability_directory]
    if request.machine_ids:
        argv += ["--machine-registry", request.machine_registry]
        for machine in request.machine_ids:
            argv += ["--machine", machine]
    if request.agent_executable:
        argv += ["--executable", request.agent_executable]
    for name in ("judge_backend", "judge_executable", "judge_provider_config"):
        value = getattr(request, name)
        if value:
            argv += ["--" + name.replace("_", "-"), value]
    argv += ["--completion-policy", request.completion_policy]
    if request.provider_config:
        argv += ["--provider-config", request.provider_config]
    if request.reasoning_effort:
        argv += ["--reasoning-effort", request.reasoning_effort]
    if request.judge_reasoning_effort:
        argv += ["--judge-reasoning-effort", request.judge_reasoning_effort]
    for name in ("director_model", "director_reasoning_effort"):
        value = getattr(request, name)
        if value:
            argv += ["--" + name.replace("_", "-"), value]
    argv += ["--director" if request.director_enabled else "--no-director"]
    if request.attention_config:
        argv += ["--attention-config", str(Path(request.attention_config).expanduser().resolve())]
    if request.mode == "minimal" and request.allow_solver_development is not None:
        argv += [
            "--allow-solver-development"
            if request.allow_solver_development
            else "--no-allow-solver-development"
        ]
    put(
        record,
        dict(
            request=request.model_dump(mode="json"),
            backend=request.backend,
            model=model,
            mode=request.mode,
            execution_backend=request.execution_backend,
            execution_preflight=execution_probe,
            state_dir=str(directory),
            argv=argv,
        ),
    )
    put(root / "study-mode.json", dict(mode=request.mode, schema_version=1))
    return MVPLaunchPlan(
        request=request,
        output_directory=str(root),
        hypothesis_file=str(hypothesis),
        instruction_file=str(instructions),
        launch_record=str(record),
        controller_log=str(root / "controller.log"),
        argv=tuple(argv),
    )


def resume_native(root):
    record = read(Path(root) / "study-launch.json")
    if not record.get("request"):
        raise ResumeError("Repeat the original study command to resume this direct CLI study")
    saved = record["request"]
    if record.get("mode", saved.get("mode")) != "minimal":
        from .mvp_launch import REMOVED_WORKFLOW_MESSAGE

        raise ResumeError(REMOVED_WORKFLOW_MESSAGE)
    if "director_enabled" not in saved:
        saved = saved | {"director_enabled": False}
    if "allow_solver_development" not in saved:
        saved = saved | {"allow_solver_development": None}
    return materialize_native(NativeStudyRequest.model_validate(saved), resume=True)


def control_native(root, action):
    root = Path(root)
    identity = load_supervisor_record(root)
    if not identity or not process_identity_matches(identity):
        raise ResumeError("No verified running study; no control sent")
    if action not in ["pause", "cancel"]:
        raise ValueError("Unknown control")
    put(supervisor_directory(root) / "control.json", dict(command=action))
    return f"{action} requested for native study"
