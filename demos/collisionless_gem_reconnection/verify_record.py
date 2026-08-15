#!/usr/bin/env python3
"""Verify the curated GEM record against the terminal report and provenance map."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from conjecture_solver.mvp_guidance import MVPGuidedCommissioningPackage

DEMO_DIRECTORY = Path(__file__).resolve().parent
SEEDS = (20260902, 20260903, 20260904)
TOP_LEVEL_SHA256 = {
    "artifact_provenance.json": "66f616621492533910682109c356f2d9bdda4c2a4a89dbbd15bce267ec75db50",
    "claim_summary.md": "ab87410837e72984f46d228c6b7a5aeef05a6ce7df947b4251de4d1a8e240971",
    "guided_commissioning.json": "99a9fef1b60091cfd1a610bb08360157f23c35e41a9e506cfa6caf208de13029",
    "hypothesis_ledger.json": "a2bd8ebc1d6ba4a0640b34669f5d0639463c52c2bdf3da6048b2225c012ddead",
    "literature_searches.json": "a3ad2a95697ad0828c504d98d91c580b48839bc4c62f81a5d8f38191c159c632",
    "mvp_manifest.json": "8c68b5e28c33d9ae5a900866bf79c9003c34378fd8429befa427fab03f401265",
    "mvp_report.json": "d6988bae02e84275e91e86250e6d6f372051696c6d1f9702e45292c015cd7e55",
    "transcript.jsonl": "8d09357a71f4948b1d116dfd96c8b0e4731344d862f396d39b54070f3cbf0199",
}


def expected_workspace_paths() -> set[str]:
    paths = {
        "analyze_ensemble.py",
        "design_pin.json",
        "energy_reader.py",
        "fallback_solver_plan.json",
        "gen_fixtures.py",
        "campaign/analyze_manifest.json",
        "campaign/commission_summary.json",
        "campaign/ensemble_result.json",
        "fixtures/commission_manifest.json",
        "fixtures/commission_output.json",
        "fixtures/commission_output_wb.json",
        "guided/anchor_operator_validation.json",
        "guided/gem_anchor_validation.json",
        "guided/gem_collisionless.py",
        "guided/prior_campaign_0002_audit_summary.json",
        "guided/prior_campaign_0003_audit_summary.json",
        "guided/prior_campaign_audit_summary.json",
    }
    paths.update(
        f".acs/evidence_programs/iteration_{iteration:06d}.py"
        for iteration in (12, 13, 19, 20, 26, 27, 32, 33, 37, 41, 42, 43, 49)
    )
    for ppc in (8, 16):
        for temperature_ratio in (1, 20):
            for seed in SEEDS:
                label = f"p{ppc}_t{temperature_ratio}_s{seed}_summary.json"
                paths.add(f"campaign/summaries/{label}")
                paths.add(f"fixtures/inp/{label}")
    for temperature_ratio in (1, 20):
        run = f"campaign/run_p16_t{temperature_ratio}_s20260902"
        paths.update(
            {
                f"{run}/diagnostic_overview.svg",
                f"{run}/final_fields.npz",
                f"{run}/warpx_used_inputs",
            }
        )
    return paths


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path, default=DEMO_DIRECTORY / "record")
    args = parser.parse_args()
    record = args.record.resolve()

    for name, expected_digest in TOP_LEVEL_SHA256.items():
        actual_digest = sha256(record / name)
        if actual_digest != expected_digest:
            raise SystemExit(
                f"top-level record mismatch for {name}: "
                f"expected {expected_digest}, found {actual_digest}"
            )

    report = json.loads((record / "mvp_report.json").read_text())
    if (DEMO_DIRECTORY / "hypothesis.txt").read_text().strip() != report["hypothesis"]:
        raise SystemExit("public hypothesis input differs from the archived run")
    if (
        (DEMO_DIRECTORY / "campaign_instruction.txt").read_text().strip()
        != report["campaign_instruction"]
    ):
        raise SystemExit("public campaign instruction differs from the archived run")
    guided_package = MVPGuidedCommissioningPackage.read(
        DEMO_DIRECTORY / "guided_commission.json"
    )
    if guided_package.descriptor() != report["guided_commissioning"]:
        raise SystemExit("public guided package differs from the archived run")

    provenance = json.loads((record / "artifact_provenance.json").read_text())["artifacts"]
    expected_hashes = report["workspace_artifacts"]
    if set(provenance) != set(expected_hashes):
        raise SystemExit("terminal report and artifact-provenance file sets differ")

    workspace = record / "workspace"
    actual_paths = {
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    }
    expected_paths = expected_workspace_paths()
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        extra = sorted(actual_paths - expected_paths)
        raise SystemExit(f"curated workspace differs: missing={missing}, extra={extra}")

    for name in sorted(actual_paths):
        path = workspace / name
        actual_digest = sha256(path)
        if actual_digest != expected_hashes[name]:
            raise SystemExit(
                f"workspace hash mismatch for {name}: "
                f"expected {expected_hashes[name]}, found {actual_digest}"
            )
        if path.stat().st_size != int(provenance[name]["bytes"]):
            raise SystemExit(f"workspace byte count mismatch for {name}")

    if report["status"] != "completed" or report["iterations"] != 75:
        raise SystemExit("unexpected terminal campaign identity")
    ledger = json.loads((record / "hypothesis_ledger.json").read_text())
    dispositions = {claim["id"]: claim["status"] for claim in ledger["claims"]}
    expected_dispositions = {
        "claim_root": "open",
        "claim_confirm_seed_ensemble": "falsified",
        "claim_instr_simulator": "supported",
        "claim_instr_analyzer": "supported",
    }
    if dispositions != expected_dispositions:
        raise SystemExit(f"unexpected claim dispositions: {dispositions}")

    ensemble = json.loads(
        (workspace / "campaign" / "ensemble_result.json").read_text()
    )
    if ensemble["decision"]["falsified"] is not True:
        raise SystemExit("operational child does not retain its recorded disposition")
    if len(ensemble["runs"]) != 12:
        raise SystemExit("expected twelve held-out scientific runs")

    full_bytes = sum(int(item["bytes"]) for item in provenance.values())
    print(
        f"verified {len(actual_paths)} curated workspace artifacts against "
        f"the {len(expected_hashes)}-artifact, {full_bytes}-byte campaign record"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
