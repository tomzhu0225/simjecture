"""Check prospective prompt/control integration after the ordinary workflow audit.

This adds no scientific outcomes, labels or model-effect estimates. Missing
exercise of a help return or authorized repair leaves commissioning incomplete.
"""

import argparse
import hashlib
import json
from pathlib import Path

from simjecture_monitor.control_commission import (
    SCHEMA,
    audit,
    check_audited_subset,
    check_tool_hashes,
)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--workflow-audit", type=Path, required=True)
    parser.add_argument(
        "--audited-manifest", type=Path, help="Started-only manifest, if interrupted"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = read(args.plan)
    if value["schema"] != SCHEMA:
        raise ValueError("Wrong commissioning plan schema")
    check_tool_hashes(Path(__file__).parents[1], value["commissioning_tools_sha256"])
    campaign = read(args.campaign / "CAMPAIGN.json")
    if campaign["stage"] not in {"completed", "failed"}:
        raise ValueError("Cannot qualify an actively collecting campaign")
    for name, expected in value["source_files_sha256"].items():
        if sha(args.source / name) != expected:
            raise ValueError("Scientific control source changed: " + name)
    summary = read(args.workflow_audit / "summary.json")
    audited_manifest = args.audited_manifest or args.plan
    records = read(args.workflow_audit / "records.json")
    check_audited_subset(value, read(audited_manifest), records)
    if summary["manifest_sha256"] != sha(audited_manifest):
        raise ValueError("Workflow audit does not cover the commissioning plan")
    inputs = {
        str(path): sha(path)
        for path in [
            args.plan,
            audited_manifest,
            args.campaign / "CAMPAIGN.json",
            args.workflow_audit / "records.json",
            args.workflow_audit / "summary.json",
            args.workflow_audit / "hashes.json",
        ]
    }
    for name, expected in read(args.workflow_audit / "hashes.json").items():
        path = args.campaign / name
        if sha(path) != expected:
            raise ValueError("Trial artifact changed after its workflow audit: " + name)
        inputs[str(path)] = expected
    evidence = {}
    for row in records:
        root = args.campaign / row["id"]
        files = {}
        for name in [
            "research.json",
            "WORKER_PROMPT_MODE.json",
            "incident-ledger.json",
            "OUTCOME.json",
        ]:
            path = root / name
            files[name] = read(path) if path.is_file() else {}
            if path.is_file():
                inputs[str(path)] = sha(path)
        evidence[row["id"]] = dict(
            task_protocol=files["research.json"].get("operator_protocol"),
            prompt_receipt=files["WORKER_PROMPT_MODE.json"],
            feedback=files["incident-ledger.json"].get("feedback", []),
            authority_results=files["OUTCOME.json"].get("authority_results", []),
            parent_turn_limit=files["OUTCOME.json"].get("parent_turn_limit"),
            parent_turn_count=len(files["OUTCOME.json"].get("turns", [])),
        )
    result = audit(value, records, evidence, audit_violations=summary["violations"])
    result["inputs_sha256"] = inputs
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: val for key, val in result.items() if key != "inputs_sha256"}))
    if not result["commissioned"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
