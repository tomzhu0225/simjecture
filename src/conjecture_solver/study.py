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

from .agent_routes import review_route
from .research_service import ResearchService, put

MODES = ("minimal", "structured", "frontier")


def configure_parser(parser):
    parser.add_argument("operation", nargs="?", choices=("extend", "budget", "limits"))
    parser.add_argument("--limits-file", type=Path, help="JSON operating settings for study limits")
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--hypothesis-file", type=Path)
    parser.add_argument("--instructions-file", type=Path)
    parser.add_argument("--hours", type=float, help="Additional wall hours for study extend")
    parser.add_argument("--reason", default="", help="Reason for the budget extension")
    parser.add_argument("--request-key", help="Idempotency key for a budget extension")
    parser.add_argument("--request-id", help="Agent time request being granted")
    parser.add_argument(
        "--mode",
        "--workflow",
        dest="mode",
        choices=MODES,
        help="New studies default to minimal; resumes preserve their mode",
    )
    parser.add_argument(
        "--execution-backend",
        choices=("bubblewrap", "proot-cooperative", "process-cooperative"),
        help="Experiment execution; default bubblewrap, immutable on resume",
    )
    parser.add_argument(
        "--requirements-file",
        type=Path,
        help="Optional immutable JSON instrument/method requirements (minimal mode)",
    )
    parser.add_argument(
        "--guided-commission",
        type=Path,
        help="Validated starting package; supplied outputs are not evidence",
    )
    parser.add_argument(
        "--continue-from",
        type=Path,
        help="Parent minimal study for a new phase with a fresh explicit budget",
    )
    parser.add_argument(
        "--inherit-file",
        action="append",
        default=[],
        help="Parent research-relative file to copy as context",
    )
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument(
        "--capabilities",
        type=Path,
        default=Path("auto"),
        help="auto (default): all available tools; directory: restrict; none: Python only",
    )
    parser.add_argument("--machine-registry", type=Path, help="Local/SSH worker registry directory")
    parser.add_argument(
        "--machine",
        dest="machine_ids",
        action="append",
        default=[],
        help="Execution worker ID; repeat to select a pool (minimal mode)",
    )
    parser.add_argument("--wall-seconds", type=float, default=3600)
    parser.add_argument("--turn-seconds", type=float, default=600)
    parser.add_argument(
        "--backend", choices=["codex-glm", "codex", "grok", "agy", "builtin"], default="codex-glm"
    )
    parser.add_argument("--provider-config")
    parser.add_argument("--completion-policy", choices=["answer", "repair"])
    parser.add_argument("--model")
    parser.add_argument("--judge-model")
    parser.add_argument(
        "--judge-backend",
        choices=["codex-glm", "codex", "grok", "agy", "builtin"],
        help="Director and reviewer backend; defaults to the worker backend",
    )
    parser.add_argument("--judge-executable")
    parser.add_argument("--judge-provider-config")
    parser.add_argument(
        "--reasoning-effort", choices=["low", "medium", "high", "xhigh", "max", "ultra"]
    )
    parser.add_argument(
        "--judge-reasoning-effort", choices=["low", "medium", "high", "xhigh", "max", "ultra"]
    )
    parser.add_argument("--executable")
    parser.add_argument(
        "--director",
        dest="director_enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Research director can stop experiments and request replans (minimal)",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress live terminal progress")
    parser.add_argument(
        "--allow-solver-development",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Allow private experimental solver forks (new minimal studies default to allowed)",
    )
    parser.add_argument(
        "--director-storage-increases",
        action="store_true",
        default=None,
        help="Delegate recorded storage allowance increases to the director (minimal)",
    )
    parser.add_argument(
        "--director-registration-tuning",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Delegate probe deadlines/retries to the director (new minimal studies default on)",
    )
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
    if getattr(args, "operation", None):
        if args.operation == "limits":
            from .research_limits import configure_limits, operating_limits

            root = args.campaign.expanduser().resolve()
            if not (root / "research.json").is_file():
                raise ValueError("Operating settings require an existing minimal study")
            result = (
                configure_limits(
                    root,
                    json.loads(args.limits_file.read_text()),
                    reason=args.reason or "Operator changed study operating settings",
                )
                if args.limits_file
                else dict(limits=operating_limits(root))
            )
            print(json.dumps(result))
            return 0
        import uuid

        from .research_budget import budget_status, extend_budget

        root = args.campaign.expanduser().resolve()
        result = (
            extend_budget(
                root,
                hours=args.hours,
                reason=args.reason,
                key=args.request_key or uuid.uuid4().hex,
                request_id=args.request_id,
            )
            if args.operation == "extend"
            else budget_status(root)
        )
        print(json.dumps(result, indent=2))
        return 0
    if not args.instructions_file:
        raise ValueError("Provide --instructions-file when launching or resuming a study")
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
    saved_effort = previous.get("request", {}).get("reasoning_effort")
    effort = getattr(args, "reasoning_effort", None)
    if previous and effort is not None and effort != saved_effort:
        raise ValueError("Reasoning effort is part of the saved launch contract")
    args.reasoning_effort = effort if effort is not None else saved_effort
    saved_judge_effort = previous.get("request", {}).get("judge_reasoning_effort")
    judge_effort = getattr(args, "judge_reasoning_effort", None)
    if previous and judge_effort is not None and judge_effort != saved_judge_effort:
        raise ValueError("Judge reasoning effort is part of the saved launch contract")
    args.judge_reasoning_effort = judge_effort if judge_effort is not None else saved_judge_effort
    saved_director = previous.get("request", {}).get("director_enabled", False)
    chosen_director = getattr(args, "director_enabled", None)
    if previous and chosen_director is not None and chosen_director != saved_director:
        raise ValueError("Research director policy is part of the saved launch contract")
    args.director_enabled = (
        chosen_director if chosen_director is not None else saved_director if previous else True
    )
    args.state_dir = (args.state_dir or saved_state or args.campaign / "supervisor").resolve()
    if saved_state and args.state_dir != saved_state.resolve():
        raise ValueError("State directory is part of the saved launch contract")
    mode = selected_mode(args.campaign, args.mode, args.state_dir)
    requested_development = getattr(args, "allow_solver_development", None)
    if mode != "minimal" and requested_development is not None:
        raise ValueError("Solver development permission is supported in minimal mode only")
    existing_research = read(args.campaign / "research.json")
    if existing_research:
        saved_development = existing_research.get("solver_development_policy", {}).get("allowed")
        if requested_development is not None and requested_development != saved_development:
            raise ValueError("Solver development permission is immutable within a study")
        args.allow_solver_development = saved_development
    else:
        args.allow_solver_development = (
            (requested_development if requested_development is not None else True)
            if mode == "minimal"
            else None
        )
    from .mvp_guidance import MVPGuidedCommissioningPackage

    guided = (
        MVPGuidedCommissioningPackage.read(args.guided_commission)
        if getattr(args, "guided_commission", None)
        else None
    )
    if mode != "minimal" and getattr(args, "requirements_file", None):
        raise ValueError("--requirements-file is supported in minimal mode only")
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
    python_only = str(args.capabilities) == "none"
    if str(args.capabilities) == "auto":
        if existing_research:
            args.capabilities = existing_research.get("capabilities")
        elif getattr(args, "machine_ids", None):
            args.capabilities = None
        elif mode == "minimal":
            import uuid

            from .web.inventory import automatic_tool_paths, freeze_available_tools

            paths = automatic_tool_paths()
            parent_capabilities = (
                read(getattr(args, "continue_from", None) / "research.json").get("capabilities")
                if getattr(args, "continue_from", None)
                else None
            )
            if parent_capabilities:
                paths.insert(0, parent_capabilities)
            args.capabilities = freeze_available_tools(
                paths,
                args.campaign.parent / ".simjecture-tools" / uuid.uuid4().hex,
            )
        else:
            args.capabilities = None
    elif python_only:
        args.capabilities = None
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
    args.provider_config = getattr(args, "provider_config", None) or previous.get(
        "request", {}
    ).get("provider_config")
    saved_review = previous.get("reviewer_route", {})
    saved_request = previous.get("request", {})
    for field in ("judge_backend", "judge_executable", "judge_provider_config"):
        saved = saved_request.get(field) or saved_review.get(field)
        chosen = getattr(args, field, None)
        setattr(args, field, chosen or saved)
    review = review_route(
        args.backend,
        args.executable,
        args.provider_config,
        judge_backend=args.judge_backend,
        judge_executable=args.judge_executable,
        judge_provider_config=args.judge_provider_config,
    )
    if previous:
        original_review = review_route(
            previous["backend"],
            saved_request.get("agent_executable") or previous["backend"],
            saved_request.get("provider_config"),
            **{
                field: saved_request.get(field) or saved_review.get(field)
                for field in ("judge_backend", "judge_executable", "judge_provider_config")
            },
        )
        if review != original_review:
            raise ValueError("Reviewer backend is part of the saved launch contract")
    if review["backend"] == "builtin":
        from .workspace_agent import read_provider, require_runtime

        require_runtime()
        read_provider(review["provider_config"], api_only=True)
    elif shutil.which(review["executable"]) is None:
        raise ValueError(f"Reviewer executable {review['executable']!r} not found")
    if args.backend == "builtin":
        from .workspace_agent import read_provider, require_runtime

        require_runtime()
        read_provider(args.provider_config)
        if mode != "minimal":
            raise ValueError("Built-in research uses minimal mode")
    elif shutil.which(args.executable) is None:
        raise ValueError(
            f"Backend executable {args.executable!r} not found; install and log in "
            "to that CLI, or choose another backend"
        )
    from .execution import require_execution_backend

    machine_ids = getattr(args, "machine_ids", None) or previous.get("request", {}).get(
        "machine_ids", []
    )
    machine_registry = getattr(args, "machine_registry", None) or previous.get("request", {}).get(
        "machine_registry"
    )
    pool = None
    if machine_ids:
        from .execution_pool import MachineRegistry

        if mode != "minimal" or not machine_registry:
            raise ValueError("Execution pools require minimal mode and --machine-registry")
        prior_pool = read(args.campaign / "research.json").get("execution_pool")
        if prior_pool:
            if (
                list(prior_pool["workers"]) != machine_ids
                or Path(prior_pool["registry"]).resolve() != Path(machine_registry).resolve()
            ):
                raise ValueError("Execution pool is immutable within a study")
            pool = prior_pool
        else:
            pool = MachineRegistry(machine_registry).freeze(machine_ids)
        execution_probe = {"backend": "worker-pool", "available": True, "machines": machine_ids}
        if args.capabilities:
            require_execution_backend(args.execution_backend)
    else:
        execution_probe = require_execution_backend(args.execution_backend)
    hypothesis = args.hypothesis_file.read_text() if args.hypothesis_file else None
    parent = getattr(args, "continue_from", None)
    if parent:
        if mode != "minimal" or (args.campaign / "research.json").exists():
            raise ValueError("Continuation requires a new minimal study")
        prior = ResearchService(parent)
        if requested_development is None:
            inherited_development = prior.solver_development_policy()["allowed"]
            if inherited_development is not None:
                args.allow_solver_development = inherited_development
        hypothesis = hypothesis or prior.manifest["hypothesis"]
        if not python_only:
            args.capabilities = args.capabilities or prior.manifest.get("capabilities")
    if mode == "minimal":
        if not (args.campaign / "research.json").exists() and hypothesis is None:
            raise ValueError("New study requires --hypothesis-file")
        from .research_finalization import default_report_reserve

        service = (
            ResearchService.create(
                args.campaign,
                hypothesis,
                wall_seconds=args.wall_seconds,
                capabilities=args.capabilities,
                execution_backend=args.execution_backend,
                completion_policy=getattr(args, "completion_policy", None),
                execution_pool=pool,
                report_reserve_seconds=default_report_reserve(args.wall_seconds)
                if not (args.campaign / "research.json").exists()
                else None,
                allow_solver_development=args.allow_solver_development,
                method_review_scope=existing_research.get("method_review_scope", "study")
                if existing_research
                else "used_instruments",
            )
            if hypothesis is not None
            else ResearchService(args.campaign)
        )
        service.freeze_protocol(args.instructions_file.read_text())
        if getattr(args, "requirements_file", None):
            service.freeze_requirements(json.loads(args.requirements_file.read_text()))
        if getattr(args, "guided_commission", None):
            service.install_guidance(args.guided_commission)
        if parent:
            from .research_continuation import attach

            attach(service, parent, getattr(args, "inherit_file", []))
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
                guided_commissioning=guided,
                config=MVPAgentConfig(
                    execution_backend=args.execution_backend,
                    max_wall_seconds=args.wall_seconds,
                    require_independent_contract_review=True,
                ),
                capabilities=(
                    MVPCapabilityRegistry.discover(args.capabilities) if args.capabilities else None
                ),
            )
        elif guided is not None:
            from .mvp_guidance import MVPGuidedCommissioningPackage

            saved = MVPGuidedCommissioningPackage.read(
                args.campaign / "guided_commissioning_input" / "package.json"
            )
            if saved.package_sha256 != guided.package_sha256:
                raise ValueError("Guided commissioning is immutable on resume")
        if (
            (args.campaign / "mvp_manifest.json").exists()
            and hypothesis is not None
            and (
                CampaignKernel.open_existing(workspace=args.campaign).hypothesis
                != hypothesis.strip()
            )
        ):
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
            judge_backend=args.judge_backend,
            judge_executable=args.judge_executable,
            judge_provider_config=args.judge_provider_config,
            reasoning_effort=args.reasoning_effort,
            judge_reasoning_effort=args.judge_reasoning_effort,
            director_enabled=args.director_enabled,
            allow_solver_development=args.allow_solver_development,
            capability_directory=str(args.capabilities) if args.capabilities else None,
            method_review_scope=supervisor.service.manifest.get("method_review_scope", "study")
            if mode == "minimal"
            else "study",
            agent_executable=args.executable,
            provider_config=getattr(args, "provider_config", None),
            machine_registry=str(machine_registry) if machine_registry else None,
            machine_ids=machine_ids,
            completion_policy=supervisor.service.manifest.get("completion_policy", "repair")
            if mode == "minimal"
            else "repair",
        ).model_dump(mode="json")
        operator = args.campaign / "operator_input"
        operator.mkdir(exist_ok=True)
        # The request schema normalizes whitespace. Preserve the exact frozen
        # hypothesis for resumes, which compare it with the service manifest.
        (operator / "hypothesis.txt").write_text(
            hypothesis
            or (
                supervisor.service.manifest["hypothesis"]
                if mode == "minimal"
                else CampaignKernel.open_existing(args.campaign).hypothesis
            )
        )
        (operator / "instruction.txt").write_text(args.instructions_file.read_text())
    record.update(
        judge_model=args.judge_model,
        reviewer_route={
            "judge_backend": args.judge_backend,
            "judge_executable": args.judge_executable,
            "judge_provider_config": args.judge_provider_config,
        },
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
        try:
            return supervisor.run()
        finally:
            if mode == "minimal":
                from .research_audit import write_report

                write_report(supervisor.service, supervisor.state)


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
