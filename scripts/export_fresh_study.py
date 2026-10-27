"""Export a completed v0.7 investigation without bulk states or provider streams.

The original receipt bytes remain authoritative. An omission ledger records every
excluded declared artifact; this export is not a substitute for full solver data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def export(source, target, *, version, commit):
    source, target = source.resolve(), target.resolve()
    state = read(source / "supervisor/state.json")
    if state["status"] not in {"completed", "budget_exhausted"}:
        raise ValueError("Only inactive terminal numerical studies may be exported")
    if target.exists() or target.is_relative_to(source):
        raise ValueError("Choose a new destination outside the original study")
    report = read(source / "research_report.json")
    launch = read(source / "study-launch.json")
    manifest = read(source / "research.json")
    records = [read(p) for p in sorted((source / "experiments").glob("*.json"))]
    if any(r["status"] in {"running", "queued"} for r in records):
        raise ValueError("Numerical executions remain active")
    post = (
        read(source / "post_run_review.json")
        if (source / "post_run_review.json").exists()
        else None
    )
    if post and post.get("session_status") not in {
        "completed",
        "review_incomplete",
        "budget_exhausted",
    }:
        raise ValueError("Post-run review is still active")
    target.mkdir(parents=True)
    omitted, other_omissions = {}, {}
    allowed = {
        ".py",
        ".json",
        ".jsonl",
        ".csv",
        ".png",
        ".svg",
        ".md",
        ".txt",
        ".npz",
        ".par",
        ".log",
        ".tsv",
    }
    limit = 2 * 1024**2

    def copy(relative, *, required=False, declared=False, unrestricted=False):
        path = source / relative
        if not path.is_file() or path.is_symlink():
            if required:
                raise ValueError(f"Missing required input: {relative}")
            return
        if not path.resolve().is_relative_to(source):
            raise ValueError(f"Escaping source path: {relative}")
        relative = path.relative_to(source)
        if not (unrestricted or (path.suffix.lower() in allowed and path.stat().st_size <= limit)):
            ledger = omitted if declared else other_omissions
            ledger[str(relative)] = dict(
                sha256=digest(path),
                bytes=path.stat().st_size,
                reason="Bulk artifact omitted; complete numerical replay requires original data.",
            )
            return
        destination = target / relative
        if not destination.resolve().is_relative_to(target):
            raise ValueError(f"Escaping destination: {relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)

    for name in [
        "research.json",
        "research_report.json",
        "STUDY_LEDGER.md",
        "RESULTS_INDEX.md",
        "study-mode.json",
        "finalization.json",
        "campaign_closeout.json",
        "post_run_review.json",
        "operating_limits.json",
        "experiments.tsv",
    ]:
        copy(
            Path(name),
            required=name in {"research.json", "research_report.json"},
            unrestricted=True,
        )
    for group in [
        "methods",
        "reviews",
        "commitments",
        "director",
        "director-acks",
        "report_requests",
        "report_reviews",
        "review_objects",
        "operator_input",
        "operating_limit_changes",
        "budget_requests",
        "budget_decisions",
        "notebook",
        "guided_commissioning_input",
    ]:
        for path in sorted((source / group).rglob("*")):
            copy(
                path.relative_to(source),
                unrestricted=(
                    group == "guided_commissioning_input"
                    or (
                        group == "review_objects"
                        and path.is_file()
                        and path.stat().st_size <= limit
                    )
                ),
            )
    for path in sorted((source / "research").rglob("*")):
        if not any(p in {".git", "__pycache__"} for p in path.parts):
            copy(path.relative_to(source))
    for record in records:
        copy(Path("experiments") / (record["id"] + ".json"), required=True, unrestricted=True)
        workspace = source / "experiments" / record["id"] / "workspace"
        wanted = (
            set(record["binding"]["inputs"])
            | set(record.get("outputs", []))
            | set(record.get("artifacts", {}))
        )
        for name in sorted(wanted):
            path = workspace / name
            if not path.resolve().is_relative_to(workspace.resolve()):
                raise ValueError(f"Escaping declared artifact: {name}")
            copy(path.relative_to(source), declared=True)

    usage_states = [("numerical_study", state)]
    if post:
        session = Path(post["session"])
        review_state = read(session / "state.json")
        usage_states.append(("post_run_review", review_state))
        review_dir = target / "post_run_session"
        review_dir.mkdir()
        for name in [
            "authorization.json",
            "protected_before.json",
            "complete_review.py",
            "outcome.json",
            "events.jsonl",
            "original_research_report.json",
            "original_finalization.json",
            "original_RESULTS.md",
        ]:
            path = session / name
            if path.is_file():
                shutil.copyfile(path, review_dir / name)
        for path in session.glob("*/validated_response.json"):
            if path.parent.name.startswith("judge-"):
                destination = review_dir / path.parent.name / path.name
                destination.parent.mkdir(exist_ok=True)
                shutil.copyfile(path, destination)
    usage = {}
    for scope, s in usage_states:
        for thread, values in s.get("usage_by_thread", {}).items():
            role = s.get("usage_roles_by_thread", {}).get(thread, "unknown")
            for key, value in values.items():
                if type(value) in {int, float}:
                    usage.setdefault(scope, {}).setdefault(role, {}).setdefault(key, 0)
                    usage[scope][role][key] += value
    request = launch["request"]
    metadata = dict(
        schema_version=2,
        created_at=datetime.now(UTC).isoformat(),
        source_commit=commit,
        software_version=version,
        source_study=source.name,
        mode=request["mode"],
        completion_policy=request["completion_policy"],
        worker={k: request[k] for k in ["backend", "model", "reasoning_effort"]},
        reviewer=state.get("reviewer_route"),
        wall_budget_seconds=request["max_wall_seconds"],
        final_numerical_deadline=manifest["deadline"],
        original_numerical_deadline=manifest.get("original_deadline", manifest["deadline"]),
        numerical_budget_extensions=manifest.get("budget_extensions", []),
        elapsed_seconds=state["updated_at"] - state["started_at"],
        status=state["status"],
        recorded_completed=report.get("completed"),
        original_disposition=report.get("original_disposition"),
        experiments=dict(Counter(r["status"] for r in records)),
        usage_by_scope_and_role=usage,
        usage_incomplete_turns=sum(s.get("usage_incomplete_turns", 0) for _, s in usage_states),
        usage_note="Native reported counters; incomplete turns remain explicit. Not an invoice.",
        timing_note=(
            "Investigation duration on shared hardware; not a controlled performance benchmark."
        ),
        original_supervisor_state_sha256=digest(source / "supervisor/state.json"),
        post_run_review=post,
        scope=(
            "Original numerical receipts, sources, methods, claim/report reviews and compact "
            "artifacts. Bulk solver states, licensed solver implementations and private provider "
            "streams are excluded. Integrity verification is not numerical replay or scientific "
            "endorsement."
        ),
        omitted_declared_files=omitted,
        omitted_other_files=other_omissions,
        files={
            str(p.relative_to(target)): digest(p) for p in sorted(target.rglob("*")) if p.is_file()
        },
    )
    (target / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                target=str(target),
                files=len(metadata["files"]),
                omitted_declared=len(omitted),
                experiments=metadata["experiments"],
                original_disposition=metadata["original_disposition"],
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    export(args.source, args.target, version=args.version, commit=args.commit)
