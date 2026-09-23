"""Launch an agent-owned study; minimal is the default for new studies."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
from pathlib import Path

from .research_service import ResearchService, put

MODES = ("minimal", "structured", "frontier")


def configure_parser(parser):
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--hypothesis-file", type=Path)
    parser.add_argument("--instructions-file", type=Path, required=True)
    parser.add_argument(
        "--mode",
        "--workflow",
        dest="mode",
        choices=MODES,
        help="New studies default to minimal; resumes preserve their mode",
    )
    parser.add_argument(
        "--execution-backend",
        choices=("bubblewrap", "proot-cooperative"),
        help="Experiment execution; default bubblewrap, immutable on resume",
    )
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--capabilities", type=Path)
    parser.add_argument("--wall-seconds", type=float, default=3600)
    parser.add_argument("--turn-seconds", type=float, default=600)
    parser.add_argument(
        "--backend", choices=["codex-glm", "codex", "grok", "agy"], default="codex-glm"
    )
    parser.add_argument("--model")
    parser.add_argument("--judge-model")
    parser.add_argument("--executable")
    parser.add_argument("--quiet", action="store_true", help="Suppress live terminal progress")
    parser.set_defaults(handler=run)


def selected_mode(root, requested=None, state_dir=None):
    recorded = None
    if (root / "study-mode.json").exists():
        recorded = json.loads((root / "study-mode.json").read_text())["mode"]
    elif (root / "research.json").exists():
        recorded = "minimal"
    elif (state := (state_dir or root / "supervisor") / "state.json").exists():
        recorded = json.loads(state.read_text()).get("workflow", "structured")
    elif (root / "mvp_manifest.json").exists():
        recorded = "structured"
    if recorded not in (None, *MODES):
        raise ValueError("Unknown recorded study mode")
    if recorded and requested and recorded != requested:
        raise ValueError("Study mode is immutable on resume; choose a new campaign directory")
    return recorded or requested or "minimal"


def run(args):
    root = args.campaign.expanduser().resolve()
    root.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(str(root).encode()).hexdigest()[:20]
    with (root.parent / f".simjecture-{digest}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("A native supervisor already owns this study") from error
        return _run(args)


def _run(args):
    from .agent_supervisor import AgentSupervisor
    from .research_supervisor import ResearchSupervisor
    from .study_status import read

    args.campaign = args.campaign.expanduser().resolve()
    previous = read(args.campaign / "study-launch.json")
    args.backend = args.backend or previous.get("backend") or "codex-glm"
    args.model = args.model or previous.get("model")
    if previous.get("backend") and (
        args.backend != previous["backend"] or args.model != previous.get("model")
    ):
        raise ValueError(
            "Backend/model are part of the launch contract; use a new study to change them"
        )
    saved_state = Path(previous["state_dir"]) if previous.get("state_dir") else None
    args.state_dir = (args.state_dir or saved_state or args.campaign / "supervisor").resolve()
    if saved_state and args.state_dir != saved_state.resolve():
        raise ValueError("State directory is part of the saved launch contract")
    mode = selected_mode(args.campaign, args.mode, args.state_dir)
    saved_execution = previous.get("execution_backend")
    if not saved_execution and (args.campaign / "research.json").exists():
        saved_execution = read(args.campaign / "research.json").get(
            "execution_backend", "bubblewrap"
        )
    if not saved_execution and (args.campaign / "mvp_manifest.json").exists():
        saved_execution = (
            read(args.campaign / "mvp_manifest.json")
            .get("config", {})
            .get("execution_backend", "bubblewrap")
        )
    requested_execution = getattr(args, "execution_backend", None)
    if saved_execution and requested_execution and saved_execution != requested_execution:
        raise ValueError("Execution backend is immutable on resume")
    args.execution_backend = requested_execution or saved_execution or "bubblewrap"
    if not 0 < args.turn_seconds <= args.wall_seconds:
        raise ValueError("Require 0 < turn-seconds <= wall-seconds")
    # Validate inputs before materializing any study state.
    protocol = args.instructions_file.read_text()
    protocol_hash = hashlib.sha256(protocol.encode()).hexdigest()
    if previous.get("protocol_sha256") and protocol_hash != previous["protocol_sha256"]:
        raise ValueError("Operator instructions are immutable within a study")
    if not args.model:
        if args.backend != "codex-glm":
            raise ValueError("Select the intended backend model explicitly with --model")
        args.model = "glm-5.3"
    args.judge_model = args.judge_model or previous.get("judge_model") or args.model
    if previous.get("judge_model") and args.judge_model != previous["judge_model"]:
        raise ValueError("Judge model is part of the saved launch contract")
    args.executable = (
        args.executable or previous.get("request", {}).get("agent_executable") or args.backend
    )
    if shutil.which(args.executable) is None:
        raise ValueError(
            f"Backend executable {args.executable!r} not found; install and log in "
            "to that CLI, or choose another backend"
        )
    from .execution import require_execution_backend

    execution_probe = require_execution_backend(args.execution_backend)
    hypothesis = args.hypothesis_file.read_text() if args.hypothesis_file else None
    if mode == "minimal":
        if not (args.campaign / "research.json").exists() and hypothesis is None:
            raise ValueError("New study requires --hypothesis-file")
        service = (
            ResearchService.create(
                args.campaign,
                hypothesis,
                wall_seconds=args.wall_seconds,
                capabilities=args.capabilities,
                execution_backend=args.execution_backend,
            )
            if hypothesis is not None
            else ResearchService(args.campaign)
        )
        service.freeze_protocol(args.instructions_file.read_text())
        supervisor = ResearchSupervisor(args)
    else:
        from .campaign_kernel import CampaignKernel
        from .mvp_agent import MVPAgentConfig
        from .mvp_skills import MVPCapabilityRegistry

        if not (args.campaign / "mvp_manifest.json").exists():
            if hypothesis is None:
                raise ValueError("New study requires --hypothesis-file")
            if args.campaign.exists() and any(args.campaign.iterdir()):
                raise ValueError("New study requires an empty campaign directory")
            CampaignKernel.open(
                workspace=args.campaign,
                hypothesis=hypothesis,
                config=MVPAgentConfig(
                    execution_backend=args.execution_backend,
                    max_wall_seconds=args.wall_seconds,
                    require_independent_contract_review=True,
                ),
                capabilities=(
                    MVPCapabilityRegistry.discover(args.capabilities) if args.capabilities else None
                ),
            )
        elif hypothesis is not None:
            if CampaignKernel.open_existing(args.campaign).hypothesis != hypothesis:
                raise ValueError("Original hypothesis is immutable")
        args.workflow = mode
        supervisor = AgentSupervisor(args)
    put(args.campaign / "study-mode.json", dict(mode=mode, schema_version=1))
    from .mvp_launch import read_process_identity, write_supervisor_record
    from .study_status import TerminalProgress

    record = read(args.campaign / "study-launch.json")
    record.update(
        mode=mode,
        backend=args.backend,
        model=args.model,
        state_dir=str(args.state_dir),
        execution_backend=args.execution_backend,
    )
    if "request" not in record:
        from .study_launch import NativeStudyRequest

        record["request"] = NativeStudyRequest(
            hypothesis=hypothesis
            or (
                supervisor.service.manifest["hypothesis"]
                if mode == "minimal"
                else CampaignKernel.open_existing(args.campaign).hypothesis
            ),
            instruction=args.instructions_file.read_text(),
            campaign_id=("study-" + re.sub(r"[^A-Za-z0-9_.-]", "-", args.campaign.name))[:128],
            output_directory=str(args.campaign),
            max_wall_seconds=args.wall_seconds,
            max_command_seconds=args.turn_seconds,
            mode=mode,
            execution_backend=args.execution_backend,
            backend=args.backend,
            model=args.model,
            judge_model=args.judge_model,
            capability_directory=str(args.capabilities) if args.capabilities else None,
            agent_executable=args.executable,
        ).model_dump(mode="json")
        operator = args.campaign / "operator_input"
        operator.mkdir(exist_ok=True)
        (operator / "hypothesis.txt").write_text(record["request"]["hypothesis"])
        (operator / "instruction.txt").write_text(args.instructions_file.read_text())
    record.update(
        judge_model=args.judge_model,
        protocol_sha256=protocol_hash,
        execution_preflight=execution_probe,
    )
    put(args.campaign / "study-launch.json", record)
    identity = read_process_identity(os.getpid())
    if identity:
        write_supervisor_record(args.campaign, identity)
    if supervisor.state.get("status") not in {"completed", "cancelled", "budget_exhausted"}:
        (args.state_dir / "control.json").unlink(missing_ok=True)
        supervisor.state["status"] = "running"
        supervisor.save()
    signal.signal(signal.SIGTERM, lambda *_: setattr(supervisor, "cancelled", True))
    signal.signal(signal.SIGINT, lambda *_: setattr(supervisor, "cancelled", True))
    with TerminalProgress(args.campaign, quiet=getattr(args, "quiet", False)):
        return supervisor.run()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    configure_parser(parser)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
