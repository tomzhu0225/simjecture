"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .action_handlers import (
    blinded_campaign_handlers,
    build_blinded_multi_action_graph,
)
from .adapters.fake import DeterministicKineticAdapter
from .adapters.pic import ElectrostaticPICAdapter
from .autonomous_research import (
    ResearchCampaignReport,
    ResearchProblemContract,
    ResearchToolRegistry,
    UniversalResearchRunner,
)
from .benchmarks.electrostatic_pic import (
    build_pic_experiment,
    build_pic_problem,
    run_pic_sufficiency_benchmark,
)
from .benchmarks.kinetic_sufficiency import run_kinetic_sufficiency_benchmark
from .campaign import CampaignRunner, planted_campaign_problem
from .confirmation import PICConfirmationRunner, confirmation_design_from_search
from .control import CampaignControl
from .corrective_audit import append_corrective_audit
from .deployment import (
    DeploymentManager,
    DeploymentProfile,
    print_deployment_report,
    resolve_project_root,
)
from .discovery import DiscoveryPackage
from .domains import installed_domain_plugins
from .ledger import SQLiteEventLedger
from .literature import PublicLiteratureSearchClient
from .llm import MissingCredential, ModelRoute, OpenAICompatibleClient
from .mvp_agent import BubblewrapSandbox, MVPAgentConfig, MVPAgentRunner
from .mvp_control import CampaignPaused
from .mvp_guidance import MVPGuidedCommissioningPackage
from .mvp_launch import (
    ResumeError,
    persist_operator_launch,
    prepare_resume,
    request_verified_pause,
    start_managed_campaign,
)
from .mvp_monitor import format_human_status, load_run_snapshot, watch_run
from .mvp_skills import (
    MVPCapabilityRegistry,
    MVPSkillCatalog,
    discover_builtin_mvp_resources,
)
from .orchestration import MultiActionCampaignRunner
from .outbox import JournaledCompletionClient
from .research_tools import SubprocessResearchTool, SubprocessResearchToolConfig
from .schema_export import export_schemas
from .search import (
    BlindedSearchRequest,
    BlindedSearchRunner,
    SearchStrategy,
    baseline_strategies,
    offline_ai_fixture_strategy,
)
from .warpx_campaign import QualifiedWarpXCampaignPackage


class _ReplayOnlyCompletionClient:
    def complete(self, *_args: object, **_kwargs: object) -> object:
        raise MissingCredential(
            "campaign needs a new model decision; set DEEPSEEK_API_KEY "
            "(official) or CP_API_KEY (legacy proxy) to continue"
        )


def _benchmark(args: argparse.Namespace) -> int:
    if args.name == "electrostatic-pic":
        result = run_pic_sufficiency_benchmark()
        if args.json:
            print(result.model_dump_json(indent=2))
        else:
            print("benchmark=electrostatic-pic")
            print(f"moments_match={result.moments_match}")
            print(
                "maxwellian="
                f"{result.maxwellian.classification} "
                f"gamma_effective={result.maxwellian.effective_growth_rate:.12f} "
                f"energy_drift={result.maxwellian.relative_energy_drift:.3e}"
            )
            print(
                "two_stream="
                f"{result.two_stream.classification} "
                f"gamma_effective={result.two_stream.effective_growth_rate:.12f} "
                f"energy_drift={result.two_stream.relative_energy_drift:.3e}"
            )
            print(f"hypothesis_falsified={result.hypothesis_falsified}")
        return int(args.assert_falsified and not result.hypothesis_falsified)
    if args.name != "kinetic-sufficiency":
        raise ValueError(f"unknown benchmark {args.name}")
    result = run_kinetic_sufficiency_benchmark()
    if args.json:
        print(result.model_dump_json(indent=2))
    else:
        print("benchmark=kinetic-sufficiency")
        print(f"moments_match={result.moments_match}")
        print(
            "maxwellian="
            f"{result.maxwellian.classification} "
            f"gamma={result.maxwellian.mode.growth_rate:.12f}"
        )
        print(
            "two_stream="
            f"{result.two_stream.classification} "
            f"gamma={result.two_stream.mode.growth_rate:.12f}"
        )
        print(f"hypothesis_falsified={result.witness.falsifies}")
        print(f"outcome_separation={result.witness.outcome_separation:.12f}")
    if args.assert_falsified and not result.witness.falsifies:
        return 1
    return 0


def _schemas(args: argparse.Namespace) -> int:
    mismatches = export_schemas(Path(args.output), check=args.check)
    if mismatches:
        print("schema mismatch:")
        for mismatch in mismatches:
            print(f"  {mismatch}")
        return 1
    verb = "verified" if args.check else "wrote"
    print(f"{verb} public schemas in {args.output}")
    return 0


def _install(args: argparse.Namespace) -> int:
    manager = DeploymentManager(resolve_project_root(args.project_root))
    report = manager.install(
        DeploymentProfile(args.profile),
        dry_run=args.dry_run,
        repair=args.repair,
        environment_manager=args.environment_manager,
        source=args.source,
        jobs=args.jobs,
        arch=args.arch,
        capture_output=args.json,
    )
    print_deployment_report(report, as_json=args.json)
    return int(not (report.ready or report.planned))


def _doctor(args: argparse.Namespace) -> int:
    manager = DeploymentManager(resolve_project_root(args.project_root))
    report = manager.doctor(args.profile, probe=not args.skip_probes)
    print_deployment_report(report, as_json=args.json)
    return int(not report.ready)


def _campaign(args: argparse.Namespace) -> int:
    if args.name == "pic":
        hypothesis, _ = build_pic_problem()
        experiment = build_pic_experiment()
        adapter = ElectrostaticPICAdapter()
        default_campaign_id = "campaign_electrostatic_pic_v1"
    elif args.name == "planted":
        hypothesis, experiment = planted_campaign_problem()
        adapter = DeterministicKineticAdapter()
        default_campaign_id = "campaign_planted_kinetic_v1"
    else:
        raise ValueError(f"unknown campaign {args.name}")
    campaign_id = args.campaign_id or default_campaign_id
    with SQLiteEventLedger(args.ledger) as ledger:
        package = CampaignRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            adapter=adapter,
            hypothesis=hypothesis,
            experiment=experiment,
        ).run()
        path = package.write(args.output)
        if not ledger.verify_chain(campaign_id):
            raise RuntimeError("campaign ledger hash chain failed verification")
    print(f"campaign={campaign_id}")
    print(f"claim_disposition={package.claim.disposition.value}")
    print(f"package_hash={package.package_hash}")
    print(f"package={path}")
    return 0


def _verify_package(args: argparse.Namespace) -> int:
    payload = json.loads(Path(args.path).read_text())
    if not isinstance(payload, dict):
        raise ValueError("package must contain a JSON object")
    if payload.get("package_kind") == "universal_research_campaign":
        package = ResearchCampaignReport.read_verified(args.path)
        domain = "universal-research"
    else:
        plugin = installed_domain_plugins().recognize_package(payload)
        if plugin is not None:
            package = plugin.read_verified_package(args.path)
            domain = plugin.metadata.name
        elif "instrument" in payload and "campaign_report" in payload:
            package = QualifiedWarpXCampaignPackage.read_verified(args.path)
            domain = "legacy-qualified-warpx"
        else:
            package = DiscoveryPackage.read_verified(args.path)
            domain = "legacy-discovery"
    print(f"domain={domain}")
    print(f"verified_package_hash={package.package_hash}")
    print(f"campaign={package.campaign_id}")
    return 0


def _search(args: argparse.Namespace) -> int:
    request = BlindedSearchRequest()
    if args.ai_strategy:
        ai_strategy = SearchStrategy.model_validate_json(Path(args.ai_strategy).read_text())
    elif args.offline_ai_fixture:
        ai_strategy = offline_ai_fixture_strategy(request)
    else:
        raise ValueError("provide --ai-strategy or explicitly select --offline-ai-fixture")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with SQLiteEventLedger(args.ledger) as ledger:
        report = BlindedSearchRunner(
            campaign_id=args.campaign_id,
            ledger=ledger,
            request=request,
            strategies=(ai_strategy, *baseline_strategies(request)),
        ).run()
        (output / "blinded_search_report.json").write_text(report.model_dump_json(indent=2) + "\n")
        confirmation = None
        if not args.skip_confirmation:
            confirmation = PICConfirmationRunner(
                campaign_id=args.campaign_id,
                ledger=ledger,
                design=confirmation_design_from_search(report),
            ).run()
            (output / "pic_confirmation_report.json").write_text(
                confirmation.model_dump_json(indent=2) + "\n"
            )
        if not ledger.verify_chain(args.campaign_id):
            raise RuntimeError("search ledger hash chain failed verification")
    print(f"campaign={args.campaign_id}")
    print(f"equal_evaluation_budget={report.equal_evaluation_budget}")
    for result in report.method_results:
        print(
            f"method={result.method.value} "
            f"first_witness={result.first_falsifying_ordinal} "
            f"best_separation={result.best_outcome_separation}"
        )
    print(f"confirmation_candidate={report.confirmation_candidate_id}")
    if confirmation is not None:
        print(f"confirmation={confirmation.disposition.value}")
    print(f"output={output}")
    return 0


def _orchestrate(args: argparse.Namespace) -> int:
    request = BlindedSearchRequest()
    if args.ai_strategy:
        ai_strategy = SearchStrategy.model_validate_json(Path(args.ai_strategy).read_text())
    elif args.offline_ai_fixture:
        ai_strategy = offline_ai_fixture_strategy(request)
    else:
        raise ValueError("provide --ai-strategy or explicitly select --offline-ai-fixture")
    graph = build_blinded_multi_action_graph(request, ai_strategy)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with SQLiteEventLedger(args.ledger) as ledger:
        report = MultiActionCampaignRunner(
            campaign_id=args.campaign_id,
            ledger=ledger,
            graph=graph,
            handlers=blinded_campaign_handlers(),
        ).run()
        (output / "multi_action_campaign_report.json").write_text(
            report.model_dump_json(indent=2) + "\n"
        )
        if not ledger.verify_chain(args.campaign_id):
            raise RuntimeError("multi-action ledger hash chain failed verification")
    print(f"campaign={args.campaign_id}")
    print(f"disposition={report.disposition.value}")
    print(f"budget_spent={report.spent_units}")
    print(f"budget_remaining={report.remaining_units}")
    for state in report.action_states:
        print(f"action={state.action.id} status={state.status.value}")
    print(f"output={output}")
    return 0


def _solve_domain(args: argparse.Namespace) -> int:
    plugin = installed_domain_plugins().get(args.domain_plugin)
    summary = plugin.solve(args)
    print(f"domain={summary.domain}")
    print(f"campaign={summary.campaign_id}")
    print(f"disposition={summary.disposition}")
    for name, value in summary.metrics.items():
        print(f"{name}={value}")
    print(f"package_hash={summary.package_hash}")
    print(f"package={summary.package_path}")
    return summary.exit_code


def _template_domain(args: argparse.Namespace) -> int:
    plugin = installed_domain_plugins().get(args.domain_plugin)
    summary = plugin.write_template(args)
    print(f"domain={summary.domain}")
    print(f"template={summary.template_path}")
    for name, value in summary.metrics.items():
        print(f"{name}={value}")
    return 0


def _evolve_domain(args: argparse.Namespace) -> int:
    registry = installed_domain_plugins()
    plugin = registry.get(args.domain_plugin)
    if plugin not in registry.evolution_plugins:
        raise ValueError(f"domain plugin {args.domain_plugin!r} does not support evolution")
    summary = plugin.evolve(args)
    print(f"domain={summary.domain}")
    print(f"campaign={summary.campaign_id}")
    print(f"disposition={summary.disposition}")
    for name, value in summary.metrics.items():
        print(f"{name}={value}")
    print(f"package_hash={summary.package_hash}")
    print(f"package={summary.package_path}")
    return summary.exit_code


def _diagnose_domain(args: argparse.Namespace) -> int:
    registry = installed_domain_plugins()
    plugin = registry.get(args.domain_plugin)
    if plugin not in registry.diagnosis_plugins:
        raise ValueError(f"domain plugin {args.domain_plugin!r} does not support diagnosis")
    summary = plugin.diagnose(args)
    print(f"domain={summary.domain}")
    print(f"status={summary.status}")
    for name, value in summary.metrics.items():
        print(f"{name}={value}")
    print(f"source_package_hash={summary.source_package_hash}")
    print(f"diagnosis_hash={summary.diagnosis_hash}")
    print(f"diagnosis={summary.diagnosis_path}")
    return 0


def _domains(args: argparse.Namespace) -> int:
    metadata = [
        plugin.metadata.model_dump(mode="json") for plugin in installed_domain_plugins().plugins
    ]
    if args.json:
        print(json.dumps(metadata, indent=2))
        return 0
    for item in metadata:
        print(
            f"domain={item['name']} version={item['version']} "
            f"hypothesis_schema={item['hypothesis_schema']} "
            f"package_schema={item['package_schema']} "
            f"operations={','.join(item['operations'])}"
        )
    return 0


def _research(args: argparse.Namespace) -> int:
    if args.use_glm and not args.reason:
        raise ValueError("--use-glm requires --reason")
    contract = ResearchProblemContract.model_validate_json(Path(args.contract).read_text())
    configs = [SubprocessResearchToolConfig.read(path) for path in args.tool_config]
    tools = ResearchToolRegistry(tuple(SubprocessResearchTool(config) for config in configs))
    route = ModelRoute.ESCALATION if args.use_glm else ModelRoute.DEFAULT
    with SQLiteEventLedger(args.ledger) as ledger:
        try:
            raw_provider = OpenAICompatibleClient.from_environment()
        except MissingCredential:
            raw_provider = _ReplayOnlyCompletionClient()
        provider = JournaledCompletionClient(
            campaign_id=args.campaign_id,
            ledger=ledger,
            client=raw_provider,
        )
        report = UniversalResearchRunner(
            campaign_id=args.campaign_id,
            ledger=ledger,
            contract=contract,
            completion_client=provider,
            tools=tools,
            control=CampaignControl(campaign_id=args.campaign_id, ledger=ledger),
            route=route,
            escalation_reason=args.reason,
        ).run()
        path = report.write(args.output)
        if not ledger.verify_chain(args.campaign_id):
            raise RuntimeError("universal research ledger hash chain failed verification")
    print("domain=universal-research")
    print(f"campaign={args.campaign_id}")
    print(f"disposition={report.conclusion.disposition.value}")
    print(f"iterations={len(report.decisions)}")
    print(f"tool_calls={report.consumed_tool_calls}")
    print(f"compute_units={report.consumed_compute_units}")
    print(f"budget_overrun={report.budget_overrun}")
    print(f"package_hash={report.package_hash}")
    print(f"package={path}")
    return 0


def _mvp(args: argparse.Namespace) -> int:
    if args.use_glm and not args.reason:
        raise ValueError("--use-glm requires --reason")
    hypothesis = (
        args.hypothesis if args.hypothesis is not None else Path(args.hypothesis_file).read_text()
    )
    if args.instruction is not None and args.instruction_file is not None:
        raise ValueError("use only one of --instruction or --instruction-file")
    if args.instruction_file is not None:
        instruction = Path(args.instruction_file).read_text()
    else:
        instruction = args.instruction
    if instruction is not None and not instruction.strip():
        instruction = None
    config = MVPAgentConfig(
        max_iterations=args.max_iterations,
        max_wall_seconds=args.max_wall_seconds,
        max_command_seconds=args.max_command_seconds,
        max_workspace_bytes=args.max_workspace_mb * 1024 * 1024,
        max_file_bytes=args.max_file_mb * 1024 * 1024,
        max_memory_bytes=args.max_memory_mb * 1024 * 1024,
        max_tool_output_chars=args.max_tool_output_chars,
        command_heartbeat_seconds=args.command_heartbeat_seconds,
        recent_full_turns=args.recent_full_turns,
        max_model_retries=args.max_model_retries,
        model_failover_after=args.model_failover_after,
    )
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    persist_operator_launch(
        hypothesis=hypothesis,
        instruction=instruction,
        campaign_id=args.campaign_id,
        output_directory=output,
        max_wall_seconds=args.max_wall_seconds,
        max_command_seconds=args.max_command_seconds,
        max_workspace_mb=args.max_workspace_mb,
        max_file_mb=args.max_file_mb,
        max_memory_mb=args.max_memory_mb,
        max_iterations=args.max_iterations,
        max_tool_output_chars=args.max_tool_output_chars,
        command_heartbeat_seconds=args.command_heartbeat_seconds,
        literature_search_timeout_seconds=args.literature_search_timeout_seconds,
        recent_full_turns=args.recent_full_turns,
        max_model_retries=args.max_model_retries,
        model_failover_after=args.model_failover_after,
        ledger=args.ledger,
        guided_commission=args.guided_commission,
        skills_directory=args.skills_directory,
        capability_directory=args.capability_directory,
        use_glm=args.use_glm,
        reason=args.reason,
    )
    skills, capabilities = discover_builtin_mvp_resources()
    if args.skills_directory:
        skills = MVPSkillCatalog.discover(args.skills_directory)
    if args.capability_directory:
        capabilities = MVPCapabilityRegistry.discover(args.capability_directory)
    guided_commissioning = (
        MVPGuidedCommissioningPackage.read(args.guided_commission)
        if args.guided_commission
        else None
    )
    ledger_path = Path(args.ledger) if args.ledger else output / "mvp_ledger.sqlite3"
    route = ModelRoute.ESCALATION if args.use_glm else ModelRoute.DEFAULT
    with SQLiteEventLedger(ledger_path) as ledger:
        try:
            raw_provider = OpenAICompatibleClient.from_environment()
        except MissingCredential:
            raw_provider = _ReplayOnlyCompletionClient()
        provider = JournaledCompletionClient(
            campaign_id=args.campaign_id,
            ledger=ledger,
            client=raw_provider,
        )
        try:
            report = MVPAgentRunner(
                hypothesis=hypothesis,
                campaign_instruction=instruction,
                output_directory=output,
                completion_client=provider,
                sandbox=BubblewrapSandbox(
                    output / "workspace",
                    config,
                    capabilities,
                ),
                config=config,
                skills=skills,
                capabilities=capabilities,
                guided_commissioning=guided_commissioning,
                literature_search=PublicLiteratureSearchClient(
                    timeout_seconds=args.literature_search_timeout_seconds,
                ),
                route=route,
                escalation_reason=args.reason,
            ).run()
        except CampaignPaused as paused:
            if not ledger.verify_chain(args.campaign_id):
                raise RuntimeError(
                    "MVP model-call ledger hash chain failed verification"
                ) from paused
            print("mode=natural-language-sandbox-mvp")
            print(f"campaign={args.campaign_id}")
            print("status=paused")
            print("pause=action_boundary")
            print(f"iterations={paused.iterations}")
            print(f"resume=simjecture resume {output}")
            print(f"transcript={output / 'transcript.jsonl'}")
            return 0
        if not ledger.verify_chain(args.campaign_id):
            raise RuntimeError("MVP model-call ledger hash chain failed verification")
    open_ids = list(report.open_claim_ids)
    closed_ids = list(report.closed_claim_ids)
    if not open_ids and not closed_ids and report.claim_ledger:
        for claim in report.claim_ledger.get("claims", []):
            claim_id = str(claim.get("id", ""))
            if not claim_id:
                continue
            if claim.get("status") == "open":
                open_ids.append(claim_id)
            else:
                closed_ids.append(claim_id)
    print("mode=natural-language-sandbox-mvp")
    print(f"campaign={args.campaign_id}")
    print(f"status={report.status}")
    print(f"iterations={report.iterations}")
    print(f"artifacts={len(report.workspace_artifacts)}")
    print(f"open_claims={','.join(open_ids) or '-'}")
    print(f"closed_claims={','.join(closed_ids) or '-'}")
    claims = list((report.claim_ledger or {}).get("claims") or [])
    if claims:
        print(f"claim_count={len(claims)}")
        for claim in claims:
            claim_id = str(claim.get("id", "?"))
            status = str(claim.get("status", "?"))
            kind = str(claim.get("kind", "?"))
            relation = str(claim.get("relation", "?"))
            evidence_n = len(claim.get("evidence") or [])
            print(
                f"claim={claim_id} status={status} kind={kind} "
                f"relation={relation} evidence={evidence_n}"
            )
    for note in report.finish_claim_notes:
        print(f"finish_claim_note={note}")
    print(f"claim_ledger={output / 'hypothesis_ledger.json'}")
    print(f"claim_summary={output / 'claim_summary.md'}")
    print(f"report={output / 'mvp_report.json'}")
    print(f"transcript={output / 'transcript.jsonl'}")
    if report.status == "cancelled":
        return 130
    if report.status == "provider_failed":
        return 75
    return 0


def _status(args: argparse.Namespace) -> int:
    snapshot = load_run_snapshot(args.run_directory)
    if args.json:
        print(snapshot.model_dump_json(indent=2))
    else:
        print(format_human_status(snapshot), end="")
    return 0


def _corrective_audit(args: argparse.Namespace) -> int:
    record = append_corrective_audit(
        args.run_directory,
        reviewer=args.reviewer,
        finding=args.finding,
        corrected_interpretation=args.corrected_interpretation,
        artifacts=tuple(args.artifact),
    )
    if args.json:
        print(record.model_dump_json(indent=2))
    else:
        print(f"recorded {record.record_id} ({record.record_sha256})")
    return 0


def _watch(args: argparse.Namespace) -> int:
    return watch_run(
        args.run_directory,
        jsonl=args.jsonl,
        poll_seconds=args.poll_seconds,
    )


def _pause(args: argparse.Namespace) -> int:
    message = request_verified_pause(args.run_directory, source="cli")
    print(message)
    return 0 if message.startswith("pause requested") else 1


def _resume(args: argparse.Namespace) -> int:
    try:
        plan = prepare_resume(args.run_directory)
    except ResumeError as error:
        print(error, file=sys.stderr)
        return 2
    if args.detach:
        campaign = start_managed_campaign(plan)
        print(f"resumed pid={campaign.identity.pid}")
        print(f"output={plan.output_directory}")
        print(f"controller_log={plan.controller_log}")
        campaign.close()
        return 0
    completed = subprocess.run(list(plan.argv), check=False)
    return int(completed.returncode)


def _import_tui():
    from .tui import run_tui

    return run_tui


def _tui(args: argparse.Namespace) -> int:
    try:
        run_tui = _import_tui()
    except ImportError:
        print(
            "The terminal UI requires the optional tui extra.\n"
            "Install it with: uv sync --extra tui",
            file=sys.stderr,
        )
        return 2
    return int(run_tui(args.run_directory))


def _import_web():
    from .web import run_web

    return run_web


def _web(args: argparse.Namespace) -> int:
    run_web = _import_web()
    scan_roots = tuple(args.scan_root or ())
    return int(
        run_web(
            run_directory=args.run_directory,
            scan_roots=scan_roots,
            runs_root=args.runs_root,
            host=args.host,
            port=args.port,
            open_browser=not args.no_open,
            read_only=args.read_only,
            verbose=args.verbose,
            engine=args.engine,
        )
    )


def _dsh_run(args: argparse.Namespace) -> int:
    from .dsh_engine import run_from_cli

    return run_from_cli(args)


def _dsh_profile(_args: argparse.Namespace) -> int:
    from .dsh_engine import bundled_profile_path

    print(bundled_profile_path())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simjecture")
    subcommands = parser.add_subparsers(dest="command", required=True)

    benchmark = subcommands.add_parser("benchmark")
    benchmark.add_argument(
        "name",
        choices=("kinetic-sufficiency", "electrostatic-pic"),
    )
    benchmark.add_argument("--json", action="store_true")
    benchmark.add_argument("--assert-falsified", action="store_true")
    benchmark.set_defaults(handler=_benchmark)

    schemas = subcommands.add_parser("schemas")
    schemas.add_argument("--output", default="schemas")
    schemas.add_argument("--check", action="store_true")
    schemas.set_defaults(handler=_schemas)

    install = subcommands.add_parser(
        "install",
        help="Install or verify an operator-selected runtime profile",
    )
    install.add_argument(
        "profile",
        choices=tuple(profile.value for profile in DeploymentProfile),
    )
    install.add_argument(
        "--project-root",
        help="Source checkout containing capabilities, environments, and skills",
    )
    install.add_argument(
        "--environment-manager",
        help="Explicit micromamba or mamba executable for the WarpX CPU profile",
    )
    install.add_argument(
        "--source",
        help="Audited WarpX source checkout required for a new CUDA build",
    )
    install.add_argument("--jobs", type=int, default=8, help="CUDA compilation jobs")
    install.add_argument(
        "--arch",
        help="CUDA compute capability digits, such as 89; omitted means auto-detect",
    )
    install.add_argument(
        "--repair",
        action="store_true",
        help="Update an existing Conda-managed WarpX CPU prefix",
    )
    install.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate prerequisites and print the provisioning command without running it",
    )
    install.add_argument("--json", action="store_true")
    install.set_defaults(handler=_install)

    doctor = subcommands.add_parser(
        "doctor",
        help="Inspect core and optional runtime readiness without installing software",
    )
    doctor.add_argument(
        "--profile",
        choices=("all", *(profile.value for profile in DeploymentProfile)),
        default="all",
    )
    doctor.add_argument(
        "--project-root",
        help="Source checkout containing capabilities, environments, and skills",
    )
    doctor.add_argument(
        "--skip-probes",
        action="store_true",
        help="Inspect runtime manifests and files without executing capability smokes",
    )
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(handler=_doctor)

    campaign = subcommands.add_parser("campaign")
    campaign.add_argument("name", choices=("planted", "pic"))
    campaign.add_argument("--campaign-id")
    campaign.add_argument("--ledger", default="campaign.sqlite3")
    campaign.add_argument("--output", default="artifacts/planted")
    campaign.set_defaults(handler=_campaign)

    package = subcommands.add_parser("package")
    package_actions = package.add_subparsers(dest="package_action", required=True)
    verify_package = package_actions.add_parser("verify")
    verify_package.add_argument("path")
    verify_package.set_defaults(handler=_verify_package)

    search = subcommands.add_parser("search")
    search.add_argument("name", choices=("blinded",))
    strategy_source = search.add_mutually_exclusive_group(required=True)
    strategy_source.add_argument("--ai-strategy")
    strategy_source.add_argument("--offline-ai-fixture", action="store_true")
    search.add_argument("--campaign-id", default="campaign_blinded_search_v1")
    search.add_argument("--ledger", default="blinded_search.sqlite3")
    search.add_argument("--output", default="artifacts/blinded_search")
    search.add_argument("--skip-confirmation", action="store_true")
    search.set_defaults(handler=_search)

    orchestrate = subcommands.add_parser("orchestrate")
    orchestrate.add_argument("name", choices=("blinded",))
    orchestration_source = orchestrate.add_mutually_exclusive_group(required=True)
    orchestration_source.add_argument("--ai-strategy")
    orchestration_source.add_argument("--offline-ai-fixture", action="store_true")
    orchestrate.add_argument("--campaign-id", default="campaign_multi_action_blinded_v1")
    orchestrate.add_argument("--ledger", default="multi_action.sqlite3")
    orchestrate.add_argument("--output", default="artifacts/multi_action")
    orchestrate.set_defaults(handler=_orchestrate)

    domains = subcommands.add_parser("domains")
    domains.add_argument("--json", action="store_true")
    domains.set_defaults(handler=_domains)

    research = subcommands.add_parser(
        "research",
        help="Run a domain-neutral model-driven research campaign",
    )
    research.add_argument("contract")
    research.add_argument("--tool-config", action="append", required=True)
    research.add_argument("--campaign-id", default="campaign_universal_research_v1")
    research.add_argument("--ledger", default="universal_research.sqlite3")
    research.add_argument("--output", default="artifacts/universal-research")
    research.add_argument("--use-glm", action="store_true")
    research.add_argument("--reason")
    research.set_defaults(handler=_research)

    mvp = subcommands.add_parser(
        "mvp",
        help="Give a natural-language hypothesis to a generic sandboxed research agent",
    )
    hypothesis_source = mvp.add_mutually_exclusive_group(required=True)
    hypothesis_source.add_argument("--hypothesis")
    hypothesis_source.add_argument("--hypothesis-file")
    mvp.add_argument(
        "--instruction",
        help=(
            "Optional natural-language operational constraint kept separate from "
            "the root hypothesis"
        ),
    )
    mvp.add_argument(
        "--instruction-file",
        help="Read the optional operational instruction from a preserved file",
    )
    mvp.add_argument(
        "--guided-commission",
        help=(
            "Path to a content-addressed successful-prerun manifest whose files "
            "are installed as a non-evidentiary autonomous starting point"
        ),
    )
    mvp.add_argument("--campaign-id", default="campaign_natural_language_mvp_v1")
    mvp.add_argument("--ledger")
    mvp.add_argument("--output", default="artifacts/natural-language-mvp")
    mvp.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Optional positive model-turn ceiling; omitted means unlimited turns",
    )
    mvp.add_argument("--max-wall-seconds", type=float, default=21_600.0)
    mvp.add_argument("--max-command-seconds", type=float, default=600.0)
    mvp.add_argument("--max-workspace-mb", type=int, default=512)
    mvp.add_argument("--max-file-mb", type=int, default=64)
    mvp.add_argument("--max-memory-mb", type=int, default=4096)
    mvp.add_argument("--max-tool-output-chars", type=int, default=30_000)
    mvp.add_argument("--command-heartbeat-seconds", type=float, default=30.0)
    mvp.add_argument(
        "--literature-search-timeout-seconds",
        type=float,
        default=20.0,
        help=(
            "Per-provider timeout for the required startup reconnaissance attempt; "
            "provider failure is recorded and does not block computation"
        ),
    )
    mvp.add_argument(
        "--recent-full-turns",
        type=int,
        default=8,
        help=(
            "Keep this many recent model turns fully detailed in the prompt; "
            "older actions and tool results are compacted while the durable transcript "
            "stays complete"
        ),
    )
    mvp.add_argument(
        "--max-model-retries",
        type=int,
        default=3,
        help=(
            "Retry this many transient or empty model responses after the initial "
            "attempt; successful model turns remain unlimited"
        ),
    )
    mvp.add_argument(
        "--model-failover-after",
        type=int,
        default=2,
        help="Switch to the alternate model route after this many consecutive failures",
    )
    mvp.add_argument(
        "--skills-directory",
        help="Override the built-in read-only skill catalog directory",
    )
    mvp.add_argument(
        "--capability-directory",
        help="Override the built-in installed-capability configuration directory",
    )
    mvp.add_argument("--use-glm", action="store_true")
    mvp.add_argument("--reason")
    mvp.set_defaults(handler=_mvp)

    status = subcommands.add_parser(
        "status",
        help="Show a compact snapshot of a durable MVP run directory",
    )
    status.add_argument("run_directory")
    status.add_argument(
        "--json",
        action="store_true",
        help="Print the typed snapshot as JSON and exit",
    )
    status.set_defaults(handler=_status)

    corrective_audit = subcommands.add_parser(
        "corrective-audit",
        help="Append a hash-chained review without rewriting campaign artifacts",
    )
    corrective_audit.add_argument("run_directory")
    corrective_audit.add_argument("--reviewer", required=True)
    corrective_audit.add_argument("--finding", required=True)
    corrective_audit.add_argument("--corrected-interpretation", required=True)
    corrective_audit.add_argument(
        "--artifact",
        action="append",
        required=True,
        help="Campaign-relative immutable artifact to hash; repeat as needed",
    )
    corrective_audit.add_argument("--json", action="store_true")
    corrective_audit.set_defaults(handler=_corrective_audit)

    watch = subcommands.add_parser(
        "watch",
        help="Follow durable MVP events until a terminal report appears",
    )
    watch.add_argument("run_directory")
    watch.add_argument(
        "--jsonl",
        action="store_true",
        help="Emit one JSON snapshot per refresh instead of human text",
    )
    watch.add_argument(
        "--poll-seconds",
        type=float,
        default=0.5,
        help="Refresh interval while waiting for new durable records",
    )
    watch.set_defaults(handler=_watch)

    tui = subcommands.add_parser(
        "tui",
        help="Open the optional terminal dashboard (maintenance mode)",
    )
    tui.add_argument(
        "run_directory",
        nargs="?",
        help="Optional existing run directory to attach",
    )
    tui.set_defaults(handler=_tui)

    web = subcommands.add_parser(
        "web",
        help="Open the primary local interface for durable MVP campaigns",
    )
    web.add_argument(
        "run_directory",
        nargs="?",
        help="Optional existing run directory to open initially",
    )
    web.add_argument(
        "--scan-root",
        action="append",
        help="Directory to scan for campaigns; repeat to add more roots",
    )
    web.add_argument(
        "--runs-root",
        default="artifacts",
        help="Parent directory for campaigns launched from the browser",
    )
    web.add_argument("--host", default="127.0.0.1", help="Loopback address to bind")
    web.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Local HTTP port; use 0 for any free port",
    )
    open_group = web.add_mutually_exclusive_group()
    open_group.add_argument(
        "--open",
        dest="no_open",
        action="store_false",
        help="Open the local interface in a browser (the default)",
    )
    open_group.add_argument(
        "--no-open",
        dest="no_open",
        action="store_true",
        help="Print the URL without opening a browser",
    )
    web.set_defaults(no_open=False)
    web.add_argument(
        "--engine",
        choices=("dsh", "native"),
        default="dsh",
        help="Reasoning engine for newly launched campaigns (default: dsh)",
    )
    web.add_argument(
        "--read-only",
        action="store_true",
        help="Disable launch, pause, resume, and stop controls",
    )
    web.add_argument(
        "--verbose",
        action="store_true",
        help="Log local HTTP requests",
    )
    web.set_defaults(handler=_web)

    dsh_profile = subcommands.add_parser(
        "dsh-profile",
        help="Print the bundled DeepSeek Harness profile directory",
    )
    dsh_profile.set_defaults(handler=_dsh_profile)

    dsh_run = subcommands.add_parser("dsh-run", help=argparse.SUPPRESS)
    dsh_run.add_argument("--output", required=True)
    dsh_run.add_argument("--session-id", required=True)
    dsh_run.add_argument("--resume", action="store_true")
    dsh_run.set_defaults(handler=_dsh_run)

    pause = subcommands.add_parser(
        "pause",
        help="Request a pause at the next MVP action boundary",
    )
    pause.add_argument("run_directory")
    pause.set_defaults(handler=_pause)

    resume = subcommands.add_parser(
        "resume",
        help="Resume a paused or incomplete MVP campaign from stored operator input",
    )
    resume.add_argument("run_directory")
    resume.add_argument(
        "--detach",
        action="store_true",
        help="Start the runner in the background and write a supervisor record",
    )
    resume.set_defaults(handler=_resume)

    registry = installed_domain_plugins()
    solve = subcommands.add_parser("solve")
    solve_domains = solve.add_subparsers(dest="domain", required=True)
    for plugin in registry.plugins:
        domain_solve = solve_domains.add_parser(
            plugin.metadata.name,
            help=plugin.metadata.description,
        )
        plugin.configure_solve_parser(domain_solve)
        domain_solve.set_defaults(
            handler=_solve_domain,
            domain_plugin=plugin.metadata.name,
        )

    template = subcommands.add_parser("template")
    template_domains = template.add_subparsers(dest="domain", required=True)
    for plugin in registry.plugins:
        domain_template = template_domains.add_parser(
            plugin.metadata.name,
            help=plugin.metadata.description,
        )
        plugin.configure_template_parser(domain_template)
        domain_template.set_defaults(
            handler=_template_domain,
            domain_plugin=plugin.metadata.name,
        )

    if registry.evolution_plugins:
        evolve = subcommands.add_parser("evolve")
        evolve_domains = evolve.add_subparsers(dest="domain", required=True)
        for plugin in registry.evolution_plugins:
            domain_evolve = evolve_domains.add_parser(
                plugin.metadata.name,
                help=f"Evolve hypotheses in {plugin.metadata.description}",
            )
            plugin.configure_evolve_parser(domain_evolve)
            domain_evolve.set_defaults(
                handler=_evolve_domain,
                domain_plugin=plugin.metadata.name,
            )
    if registry.diagnosis_plugins:
        diagnose = subcommands.add_parser("diagnose")
        diagnose_domains = diagnose.add_subparsers(dest="domain", required=True)
        for plugin in registry.diagnosis_plugins:
            domain_diagnose = diagnose_domains.add_parser(
                plugin.metadata.name,
                help=f"Diagnose a verified package in {plugin.metadata.description}",
            )
            plugin.configure_diagnose_parser(domain_diagnose)
            domain_diagnose.set_defaults(
                handler=_diagnose_domain,
                domain_plugin=plugin.metadata.name,
            )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
