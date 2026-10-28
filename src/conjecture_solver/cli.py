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
from .llm import MissingCredential, ModelRoute, OpenAICompatibleClient
from .mvp_launch import (
    ResumeError,
    prepare_resume,
    request_verified_pause,
    start_managed_campaign,
)
from .mvp_monitor import format_human_status, load_run_snapshot, watch_run
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
        repository=args.repository,
        git_ref=args.git_ref,
    )
    print_deployment_report(report, as_json=args.json)
    return int(not (report.ready or report.planned))


def _doctor(args: argparse.Namespace) -> int:
    if getattr(args, "execution_backend", None):
        from .execution import probe_execution_backend

        report = probe_execution_backend(args.execution_backend)
        print(json.dumps(report, indent=2))
        return 0 if report["available"] else 1
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="simjecture")
    subcommands = parser.add_subparsers(dest="command", required=True)

    from .windows import configure_parser as configure_windows

    configure_windows(subcommands.add_parser(
        "windows", help="Experimental common interface for Windows application adapters"
    ))

    from .cst import configure_parser as configure_cst

    configure_cst(subcommands.add_parser(
        "cst", help="Experimental operator-side WSL bridge to installed Windows CST"
    ))

    from .study import configure_parser

    configure_parser(
        subcommands.add_parser("study", help="Launch a minimal research study")
    )

    steer = subcommands.add_parser("steer", help="Send advisory guidance to a minimal study")
    steer.add_argument("--campaign", type=Path, required=True)
    steer.add_argument("--message", required=True)
    steer.add_argument("--request-key")

    benchmark = subcommands.add_parser("benchmark")
    benchmark.add_argument(
        "name",
        choices=("kinetic-sufficiency", "electrostatic-pic"),
    )
    benchmark.add_argument("--json", action="store_true")
    benchmark.add_argument("--assert-falsified", action="store_true")
    benchmark.set_defaults(handler=_benchmark)

    from .llm_bench.pack import configure_parser as configure_llm_bench

    configure_llm_bench(
        subcommands.add_parser(
            "llm-benchmark", help="Experimental, versioned scientific coding task pack"
        )
    )

    from .execution_pool import configure_parser as configure_machines

    configure_machines(
        subcommands.add_parser(
            "machines", help="Configure, prepare and inspect local/SSH execution workers"
        )
    )

    from .attention_cli import configure as configure_attention
    from .knowledge_cli import configure as configure_knowledge
    from .workspace_cli import configure as configure_workspace

    configure_knowledge(
        subcommands.add_parser("knowledge", help="Search and connect local research knowledge")
    )
    configure_attention(
        subcommands.add_parser(
            "attention", help="Inspect or connect optional scientific attention tooling"
        )
    )

    for kind in ("workspace", "project", "conversation"):
        configure_workspace(
            subcommands.add_parser(kind, help=f"Manage local {kind}s (JSON output)"), kind
        )

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
        help=(
            "Audited local source checkout: required for WarpX CUDA; optional "
            "for EOS, opacity, and FLASH"
        ),
    )
    install.add_argument(
        "--repository",
        help=(
            "Operator-owned Git remote to clone for FLASH; Simjecture never "
            "supplies a default FLASH URL"
        ),
    )
    install.add_argument(
        "--git-ref",
        help="Git tag, branch, or commit for --repository",
    )
    install.add_argument(
        "--jobs",
        type=int,
        default=8,
        help="Build jobs for WarpX CUDA and EOS/opacity bootstraps",
    )
    install.add_argument(
        "--arch",
        help="CUDA compute capability digits, such as 89; omitted means auto-detect",
    )
    install.add_argument(
        "--repair",
        action="store_true",
        help=(
            "Update a Conda-managed WarpX CPU prefix, or replace an "
            "installer-managed EOS or opacity runtime"
        ),
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
    doctor.add_argument(
        "--execution-backend", choices=("bubblewrap", "proot-cooperative", "process-cooperative")
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
        help="Follow durable research records until a terminal report appears",
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

    web = subcommands.add_parser(
        "web",
        help="Open the local research workspace",
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
        choices=("native",),
        default="native",
        help=argparse.SUPPRESS,
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

    serve = subcommands.add_parser(
        "serve", help="Serve quota-limited public trials behind an HTTPS reverse proxy"
    )
    serve.add_argument(
        "--root", required=True, type=Path, help="Private public-service state directory"
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8788, type=int)
    serve.add_argument(
        "--unix-socket", type=Path, help="Private Unix HTTP socket for managed execution"
    )
    serve.add_argument("--development-http", action="store_true", help="Local testing only")

    def public_server(args):
        from .public.server import serve

        return serve(args)

    serve.set_defaults(handler=public_server)

    pause = subcommands.add_parser(
        "pause",
        help="Request a pause at the next MVP action boundary",
    )
    pause.add_argument("run_directory")
    pause.set_defaults(handler=_pause)

    resume = subcommands.add_parser(
        "resume",
        help="Resume a minimal study from its saved launch contract",
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
    if args.command == "steer":
        from .research_continuation import submit

        try:
            print(json.dumps(submit(args.campaign, args.message, key=args.request_key), indent=2))
            return 0
        except ValueError as error:
            parser.error(str(error))
    if args.command in {"study", "attention"}:
        try:
            return int(args.handler(args))
        except ValueError as error:
            parser.error(str(error))
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
