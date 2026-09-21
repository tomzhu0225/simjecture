"""Native study launch contracts shared by CLI, browser and TUI."""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Literal

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
    mode: Literal["minimal", "structured", "frontier"] = "minimal"
    backend: Literal["codex-glm", "codex", "grok", "agy"] = "codex-glm"
    model: str | None = None
    judge_model: str | None = None
    agent_executable: str | None = None


def materialize_native(request, *, resume=False):
    root = Path(request.output_directory).expanduser().resolve()
    record = root / "study-launch.json"
    existing = read(record)
    model = request.model or ("glm-5.3" if request.backend == "codex-glm" else None)
    if not model:
        raise ValueError("Choose an explicit model for this backend")
    executable = request.agent_executable or request.backend
    if shutil.which(executable) is None:
        raise ValueError(f"Backend executable {executable!r} not found; install its CLI first")
    if request.engine != "native":
        raise ValueError("Native study modes cannot use the legacy DSH engine")
    identity = load_supervisor_record(root) if root.exists() else None
    if identity and process_identity_matches(identity):
        raise ResumeError("Study is already running; attach to its status")
    if existing and existing.get("request") != request.model_dump(mode="json"):
        raise ValueError("Existing study launch contract differs")
    if resume and not existing:
        raise ResumeError("No saved native launch contract")
    protocol = (
        request.instruction or "Investigate the stated hypothesis within its scientific scope."
    )
    if not resume:
        if root.exists() and any(root.iterdir()):
            raise ValueError("Choose a new empty study directory")
        if request.mode == "minimal":
            service = ResearchService.create(
                root,
                request.hypothesis,
                wall_seconds=request.max_wall_seconds,
                capabilities=request.capability_directory,
            )
            service.freeze_protocol(protocol)
        else:
            from .campaign_kernel import CampaignKernel
            from .mvp_agent import MVPAgentConfig
            from .mvp_skills import MVPCapabilityRegistry

            CampaignKernel.open(
                workspace=root,
                hypothesis=request.hypothesis,
                config=MVPAgentConfig(
                    max_wall_seconds=request.max_wall_seconds,
                    require_independent_contract_review=True,
                ),
                capabilities=(
                    MVPCapabilityRegistry.discover(request.capability_directory)
                    if request.capability_directory
                    else None
                ),
            )
    directory = Path(existing.get("state_dir") or root / "supervisor")
    if resume:
        state = read(directory / "state.json")
        if state.get("status") in ["completed", "cancelled", "budget_exhausted"]:
            raise ResumeError("Study is terminal; create a new study to change its budget")
        if state.get("deadline", time.time() + 1) <= time.time():
            raise ResumeError("The original wall-time deadline has expired")
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
    if request.capability_directory:
        argv += ["--capabilities", request.capability_directory]
    if request.agent_executable:
        argv += ["--executable", request.agent_executable]
    put(
        record,
        dict(
            request=request.model_dump(mode="json"),
            backend=request.backend,
            model=model,
            mode=request.mode,
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
    return materialize_native(NativeStudyRequest.model_validate(record["request"]), resume=True)


def control_native(root, action):
    root = Path(root)
    identity = load_supervisor_record(root)
    if not identity or not process_identity_matches(identity):
        raise ResumeError("No verified running study; no control sent")
    if action not in ["pause", "cancel"]:
        raise ValueError("Unknown control")
    put(supervisor_directory(root) / "control.json", dict(command=action))
    return f"{action} requested for native study"
