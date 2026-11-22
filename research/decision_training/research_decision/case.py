"""Public case state, evidence-linked closeout, and complete cost accounting."""

from __future__ import annotations

import time
from pathlib import Path

from .contracts import observation, phase_conclusion, reject_private_fields
from .storage import read_json, write_json

TERMINAL = {"succeeded", "failed", "cancelled", "timed_out", "partial", "interrupted"}
RECEIPT_FIELDS = (
    "id",
    "status",
    "created_at",
    "started_at",
    "finished_at",
    "execution",
    "resources",
    "machine",
    "outputs",
    "artifacts",
    "remote_artifacts",
    "binding",
    "error",
    "purpose",
    "parent_experiment",
    "stage",
    "method",
)


def science_json(root, name, default=None):
    root = Path(root)
    primary = root / name
    return read_json(primary, default) if primary.exists() else read_json(root / "research" / name, default)


def receipts(root):
    return [read_json(p) for p in sorted((Path(root) / "experiments").glob("*.json"))]


def public_evidence(root, actual):
    available = {r["id"] for r in actual if r["status"] in TERMINAL}
    output = []
    for item in science_json(root, "verified-evidence.json", []):
        # A review can certify evidence; it cannot manufacture an execution.
        if not item.get("receipt_ids") or not set(item["receipt_ids"]) <= available:
            raise ValueError("Public evidence lacks real terminal execution receipts")
        reject_private_fields(item)
        output.append(item)
    return output


def public_state(root, *, native=None, receipt_ids=None, evidence_ids=None):
    root = Path(root)
    task = read_json(root / "task.json")
    now = time.time()
    records = receipts(root)
    completed = []
    for record in records:
        if record["status"] not in TERMINAL or not record.get("finished_at"):
            continue
        public = {key: record[key] for key in RECEIPT_FIELDS if key in record}
        execution = record.get("execution") or {}
        public["execution"] = {
            key: execution[key]
            for key in (
                "wall_seconds",
                "returncode",
                "timed_out",
                "cancelled",
                "workspace_bytes",
                "executor_sha256",
                "resource_limits",
            )
            if key in execution
        }
        diagnostics = []
        index = []
        import hashlib
        import json

        artifacts = record.get("remote_artifacts") or record.get("artifacts") or {}
        for name in sorted(record.get("outputs", [])):
            if Path(name).suffix.lower() != ".json" or name not in artifacts:
                continue
            metadata = artifacts[name]
            index.append(dict(name=name, sha256=metadata["sha256"], bytes=metadata["bytes"]))
            path = root / "experiments" / record["id"] / "workspace" / name
            if path.is_file() and metadata["bytes"] <= 16000:
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != metadata["sha256"]:
                    raise ValueError("Observed diagnostic identity changed")
                try:
                    values = json.loads(data)
                    reject_private_fields(values)
                except (ValueError, TypeError):
                    continue
                diagnostics.append(
                    dict(
                        artifact=name,
                        sha256=metadata["sha256"],
                        observed_values=values,
                        verification_level="real execution output; physical interpretation requires review",
                    )
                )
        public["diagnostic_artifact_index"] = index
        public["downloaded_numerical_observations"] = diagnostics
        public["diagnostic_projection"] = (
            "Complete cached JSON documents up to 16000 bytes; remaining artifacts explicitly indexed for evidence requests."
        )
        if public["status"] == "interrupted":
            public["status"] = "partial"
        completed.append(public)
    run = read_json(root / "study-run.json", {})
    remaining = max(0, run.get("deadline", now) - now)
    if native is not None:
        remaining = max(0, native.status()["remaining_seconds"])
    history = science_json(root, "public-history.json", [])
    available = run.get("public_resources", {}).copy()
    all_ids = [r["id"] for r in completed]
    if receipt_ids is not None:
        if not set(receipt_ids) <= set(all_ids):
            raise ValueError("Requested receipt is not a real terminal result")
        completed = [r for r in completed if r["id"] in receipt_ids]
        available["receipt_projection"] = dict(
            selected_ids=list(receipt_ids),
            omitted_ids=[i for i in all_ids if i not in receipt_ids],
            total_count=len(all_ids),
        )
    evidence = public_evidence(root, records)
    if evidence_ids is not None:
        if not set(evidence_ids) <= {e["evidence_id"] for e in evidence}:
            raise ValueError("Requested evidence is absent from the verified ledger")
        available["evidence_projection"] = dict(
            selected_ids=list(evidence_ids),
            omitted_ids=[e["evidence_id"] for e in evidence if e["evidence_id"] not in evidence_ids],
        )
        evidence = [e for e in evidence if e["evidence_id"] in evidence_ids]
    # Only an explicit public evidence ledger is exposed, never native reviewer
    # messages, grades, private scratch files, or the research controller state.
    return observation(
        task=task,
        hypotheses=task.get("hypotheses", []),
        physical_models=(
            [task["equations"]] if isinstance(task.get("equations"), str) else task.get("equations", [])
        ),
        available_resources=available,
        completed_receipts=completed,
        verified_evidence=evidence,
        necessary_history=history,
        remaining_wall_seconds=remaining,
        observed_at=now,
    )


def closeout(root, reason):
    root = Path(root)
    actual = receipts(root)
    if any(r["status"] not in TERMINAL for r in actual):
        raise ValueError("Settle or cancel active remote executions before closeout")
    evidence = public_evidence(root, actual)
    proposed = science_json(root, "proposed-conclusion.json", {})
    known = {item["evidence_id"] for item in evidence}
    supported, falsified, unresolved = [], [], list(proposed.get("unresolved", []))
    for category, destination in (("supported", supported), ("falsified", falsified)):
        for claim in proposed.get(category, []):
            ids = set(claim.get("evidence_ids", [])) if isinstance(claim, dict) else set()
            if ids and ids <= known:
                destination.append(claim)
            else:
                unresolved.append(dict(unverified_proposal=claim))
    if not supported and not falsified:
        unresolved.append("No evidence-linked scientific claim has yet been independently certified.")
    task = read_json(root / "task.json")
    result = phase_conclusion(
        supported=supported,
        falsified=falsified,
        unresolved=unresolved,
        scope=proposed.get("scope") or task.get("scope_statement") or task["question"],
        evidence_ids=sorted(known),
        termination_reason=reason,
    )
    result["execution_counts"] = {s: sum(r["status"] == s for r in actual) for s in sorted(TERMINAL)}
    result["actual_execution_wall_seconds"] = sum(
        max(0, float((r.get("execution") or {}).get("wall_seconds", 0))) for r in actual
    )
    result["cost_scope"] = "all recorded executions, including failed, interrupted and timed-out work"
    write_json(root / "phase_conclusion.json", result)
    return result
