"""Evidence inspection and host-written reports; no scientific verdicts inferred."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

TEXT_SUFFIXES = {".json", ".txt", ".md", ".csv", ".log"}


def strict_json(text):
    def reject(value):
        raise ValueError(f"Non-finite JSON constant: {value}")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite JSON number")
        return number

    return json.loads(text, parse_constant=reject, parse_float=finite_float)


def output_findings(workspace, outputs):
    findings = []
    for name in outputs:
        path = workspace / name
        if not path.is_file() or path.suffix != ".json" or path.stat().st_size > 262144:
            continue
        try:
            obj = strict_json(path.read_text())
        except (ValueError, UnicodeError) as error:
            findings.append(dict(path=name, kind="invalid_json", detail=str(error)))
            continue
        if isinstance(obj, dict):
            failed = (
                [
                    k
                    for k, v in obj.get("checks", {}).items()
                    if v is False and k != "scientific_evidence_eligible"
                ]
                if isinstance(obj.get("checks"), dict)
                else []
            )
            if failed:
                findings.append(dict(path=name, kind="failed_checks", detail=failed))
    return findings


def review_documents(workspace, record, *, require_document=True):
    """Read compact text only. Raw arrays stay hashed, listed, and explicitly uninspected."""
    selected = record.get("review_documents")
    if selected is None:
        selected = [
            p
            for p in record["outputs"]
            if Path(p).suffix.lower() in TEXT_SUFFIXES
            and (workspace / p).is_file()
            and (workspace / p).stat().st_size <= 262144
        ]
    documents = {}
    for name in selected:
        path = workspace / name
        if not path.is_file() or path.stat().st_size > 262144:
            raise ValueError("Review documents must exist and be at most 256 KiB")
        try:
            documents[name] = path.read_text()
        except UnicodeError as error:
            raise ValueError(
                "Review documents must be UTF-8 text; retain binary outputs separately"
            ) from error
    if require_document and not documents:
        raise ValueError("Supply a compact text/JSON result document alongside raw outputs")
    raw = {p: record.get("artifacts", {}).get(p) for p in record["outputs"] if p not in documents}
    return documents, raw, output_findings(workspace, record["outputs"])


def study_findings(snapshot, manifest):
    experiments = snapshot["experiments"]
    coverage = []
    for c in snapshot["commitments"]:
        runs = [e for e in experiments if e.get("commitment") == c["id"]]
        missing = [
            b["args"]
            for b in c["bindings"]
            if not any(e["binding"] == b and e["status"] == "succeeded" for e in runs)
        ]
        coverage.append(
            dict(
                commitment=c["id"],
                planned=len(c["bindings"]),
                missing=len(missing),
                missing_cases=missing,
            )
        )
    durations = [
        e.get("execution", {}).get("wall_seconds", 0)
        for e in experiments
        if e["status"] == "succeeded"
    ]
    estimate = (sum(durations) / len(durations)) if durations else None
    outstanding = sum(c["missing"] for c in coverage)
    estimate_total = estimate * outstanding if estimate else None
    review_reserve = min(300, max(0, manifest["deadline"] - manifest["created_at"]) * 0.05)
    budget_warning = None
    if snapshot["remaining_seconds"] < review_reserve + (estimate_total or 0):
        budget_warning = (
            "Remaining budget may not cover the outstanding committed cases plus analysis/review. "
            "Prioritize required validation and independent review; do not weaken the claim."
        )
    return dict(
        recommended_review_reserve_seconds=review_reserve,
        budget_warning=budget_warning,
        execution_counts=dict(Counter(e["status"] for e in experiments)),
        scientific_status="accepted" if snapshot["completed"] else "unresolved",
        coverage=coverage,
        estimated_serial_validation_seconds=estimate_total,
        estimate_note="Heuristic from completed jobs, excluding analysis/review; not a guarantee.",
        flagged_experiments=[
            dict(id=e["id"], findings=e["output_findings"])
            for e in experiments
            if e.get("output_findings")
        ],
        no_independent_review=not bool(snapshot["reviews"]),
    )


def write_report(service, state):
    from .research_journal import sync_journal
    from .research_service import put

    snapshot = service.status()
    sync_journal(service)
    brief = service.write_brief()
    report = dict(
        status=state["status"],
        **snapshot,
        research_brief=brief,
        supervision={
            k: state.get(k)
            for k in (
                "round",
                "no_progress_streak",
                "session_recoveries",
                "oversight_count",
                "oversight_feedback",
                "usage_by_thread",
                "usage_incomplete_turns",
                "provider_retry_count",
                "journal_summary_count",
                "journal_summary_seconds",
                "journal_summary_error",
            )
        },
    )
    put(service.root / "research_report.json", report)
    rows = [
        "# Host-generated study ledger",
        "",
        f"Execution status: {state['status']}. "
        f"Scientific status: {snapshot['audit']['scientific_status']}.",
        "",
        "Execution success is not scientific acceptance. Worker notes are separate.",
        "",
        "| Experiment | Purpose | Parent | Stage | Execution | Method |",
        "|---|---|---|---|---|---|",
    ]
    for e in sorted(snapshot["experiments"], key=lambda e: e["created_at"]):
        rows.append(
            f"| {e['id']} | {e.get('purpose') or 'unspecified'} | "
            f"{e.get('parent_experiment') or '—'} | {e.get('stage', 'evidence')} | {e['status']} | "
            f"{e.get('method') or 'unreviewed'} |"
        )
    rows += ["", "## Outstanding planned cases", ""]
    for c in snapshot["audit"]["coverage"]:
        rows.append(
            f"- {c['commitment']}: {c['missing']} of {c['planned']} cases lack successful receipts."
        )
    rows += [
        "",
        f"Independent claim reviews: {len(snapshot['reviews'])}.",
        f"Methods reviews: {len(snapshot['methods'])}.",
        "",
        "See research_report.json for complete provenance, findings and review outcomes.",
    ]
    path = service.root / "STUDY_LEDGER.md"
    temp = path.with_suffix(".tmp")
    temp.write_text("\n".join(rows) + "\n")
    temp.replace(path)
    # Small machine-readable ledger for comparison scripts; failed attempts stay visible.
    table = service.root / "experiments.tsv"
    temp = table.with_suffix(".tmp")
    with temp.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(
            [
                "id",
                "purpose",
                "parent",
                "plan",
                "stage",
                "execution",
                "capability",
                "source_sha256",
                "wall_seconds",
                "args",
            ]
        )
        for e in sorted(snapshot["experiments"], key=lambda e: e["created_at"]):
            b = e["binding"]
            writer.writerow(
                [
                    e["id"],
                    e.get("purpose"),
                    e.get("parent_experiment"),
                    e.get("plan"),
                    e.get("stage", "evidence"),
                    e["status"],
                    b.get("capability"),
                    b.get("inputs", {}).get(b.get("source")),
                    e.get("execution", {}).get("wall_seconds"),
                    json.dumps(b.get("args", [])),
                ]
            )
    temp.replace(table)
