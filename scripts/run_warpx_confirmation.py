#!/usr/bin/env python3
"""Run a fresh-seed confirmation matrix with a qualified WarpX instrument."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from conjecture_solver.adapters.warpx import (
    SubprocessWarpXScheduler,
    WarpXAdapter,
    WarpXPhysicsQualificationRecord,
)
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.warpx_confirmation import (
    WarpXConfirmationDisposition,
    WarpXConfirmationRunner,
    default_warpx_confirmation_design,
    register_qualified_warpx_instrument,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("qualification", type=Path)
    parser.add_argument("--warpx-python", type=Path, default=Path(".runtime/warpx-cpu/bin/python"))
    parser.add_argument("--work-root", type=Path, default=Path(".runtime/warpx-confirmation-v1"))
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("artifacts/warpx_confirmation.sqlite3"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/warpx_confirmation_report.json"),
    )
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    qualification = WarpXPhysicsQualificationRecord.model_validate_json(
        args.qualification.read_text()
    )
    instrument = register_qualified_warpx_instrument(qualification)
    design = default_warpx_confirmation_design(qualification)
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
        report = WarpXConfirmationRunner(
            campaign_id="campaign_qualified_warpx_confirmation_v1",
            ledger=ledger,
            instrument=instrument,
            adapter=adapter,
            design=design,
        ).run()
        if not ledger.verify_chain("campaign_qualified_warpx_confirmation_v1"):
            raise RuntimeError("confirmation event hash chain did not verify")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2) + "\n")
    report_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"disposition={report.disposition.value}")
    print(f"attempts={len(report.attempts)}")
    print(f"report_file_hash={report_hash}")
    print(f"report={args.output}")
    return 0 if report.disposition is WarpXConfirmationDisposition.CONFIRMED else 1


if __name__ == "__main__":
    raise SystemExit(main())
