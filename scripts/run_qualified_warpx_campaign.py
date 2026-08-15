#!/usr/bin/env python3
"""Run analytic discovery and qualified WarpX confirmation as one durable DAG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from conjecture_solver.action_handlers import (
    build_qualified_warpx_campaign_graph,
    qualified_warpx_campaign_handlers,
)
from conjecture_solver.adapters.warpx import (
    SubprocessWarpXScheduler,
    WarpXAdapter,
    WarpXPhysicsQualificationRecord,
)
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.orchestration import MultiActionCampaignRunner
from conjecture_solver.search import (
    BlindedSearchRequest,
    SearchStrategy,
    offline_qualified_warpx_fixture_strategy,
)
from conjecture_solver.warpx_campaign import build_qualified_warpx_campaign_package
from conjecture_solver.warpx_confirmation import register_qualified_warpx_instrument


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qualification", type=Path)
    parser.add_argument("strategy", type=Path, nargs="?")
    parser.add_argument(
        "--offline-ai-fixture",
        action="store_true",
        help="use the deterministic exact-scope CI batch; this is not a live model result",
    )
    parser.add_argument(
        "--warpx-python",
        type=Path,
        default=Path(".runtime/warpx-cpu/bin/python"),
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=Path(".runtime/warpx-confirmation-v2"),
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("artifacts/qualified_warpx_campaign.sqlite3"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/qualified_warpx_campaign"),
    )
    parser.add_argument(
        "--campaign-id",
        default="campaign_blinded_qualified_warpx_v1",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    qualification = WarpXPhysicsQualificationRecord.model_validate_json(
        args.qualification.read_text()
    )
    instrument = register_qualified_warpx_instrument(qualification)
    request = BlindedSearchRequest()
    if args.offline_ai_fixture == (args.strategy is not None):
        parser.error("provide exactly one strategy file or --offline-ai-fixture")
    strategy = (
        offline_qualified_warpx_fixture_strategy(request)
        if args.offline_ai_fixture
        else SearchStrategy.model_validate_json(args.strategy.read_text())
    )
    graph = build_qualified_warpx_campaign_graph(request, strategy, instrument)
    scheduler = SubprocessWarpXScheduler(
        work_root=args.work_root.resolve() / "jobs",
        command=(
            sys.executable,
            str(project_root / "scripts" / "run_warpx_pair.py"),
            "--warpx-python",
            str(args.warpx_python.resolve()),
        ),
        profile=instrument.execution_profile,
        timeout_seconds=300,
    )
    adapter = WarpXAdapter(scheduler, physics_qualification=qualification)
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with SQLiteEventLedger(args.ledger) as ledger:
        report = MultiActionCampaignRunner(
            campaign_id=args.campaign_id,
            ledger=ledger,
            graph=graph,
            handlers=qualified_warpx_campaign_handlers(
                instrument=instrument,
                adapter=adapter,
            ),
        ).run()
        package = build_qualified_warpx_campaign_package(
            campaign_id=args.campaign_id,
            ledger=ledger,
            instrument=instrument,
            campaign_report=report,
        )
        if not ledger.verify_chain(args.campaign_id):
            raise RuntimeError("campaign event hash chain did not verify")

    args.output.mkdir(parents=True, exist_ok=True)
    report_path = args.output / "campaign_report.json"
    report_path.write_text(report.model_dump_json(indent=2) + "\n")
    package_path = package.write(args.output)
    print(f"disposition={report.disposition.value}")
    print(f"spent_units={report.spent_units:g}")
    print(f"confirmation={package.confirmation_report.disposition.value}")
    print(f"evidence_records={len(package.evidence)}")
    print(f"claim={package.claim.disposition.value}")
    print(f"package_hash={package.package_hash}")
    print(f"package={package_path}")
    return 0 if report.disposition.value == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
