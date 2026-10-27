#!/usr/bin/env python3
"""Bounded post-run review using unmodified Simjecture 0.7.0 review APIs.

This is an operator-authorized review session, not a resumed numerical study.
Original numerical deadlines, receipts, methods, finalization and state are kept.
All model calls are ephemeral, read-only; the host records validated responses.
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel, ConfigDict, Field

from conjecture_solver.agent_supervisor import AgentSupervisor, parse_judge_stream
from conjecture_solver.research_audit import write_report
from conjecture_solver.research_finalization import ResearchFinalization, ReportAssessment
from conjecture_solver.research_limits import configure_limits
from conjecture_solver.research_service import ResearchService, ResearchVerdict, fingerprint, put, sha
from conjecture_solver.research_supervisor import research_review_prompt
from conjecture_solver.review_assets import packet_view


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_markdown: str = Field(min_length=1000, max_length=150000)


def protected(root):
    paths = [root / name for name in ("research.json", "supervisor/state.json", "finalization.json")]
    for kind in ("experiments", "methods", "commitments"):
        paths.extend(sorted((root / kind).glob("*.json")))
    return {str(p.relative_to(root)): sha(p) for p in paths if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--wall-seconds", type=float, default=1800)
    args = parser.parse_args()
    root, session = args.study.resolve(), args.session.resolve()
    session.mkdir(parents=True, exist_ok=False)
    service = ResearchService(root)
    original_state = json.loads((root / "supervisor/state.json").read_text())
    if original_state["status"] != "budget_exhausted":
        raise ValueError("This helper is for the expired, inactive numerical study only")
    if any(r["status"] in {"running", "queued"} for r in service._all("experiments")):
        raise ValueError("Numerical executions are still active")
    baseline = protected(root)
    put(session / "protected_before.json", baseline)
    for name in ("research_report.json", "research/RESULTS.md", "finalization.json"):
        source = root / name
        if source.exists():
            shutil.copyfile(source, session / ("original_" + source.name))
    shutil.copyfile(__file__, session / "complete_review.py")
    authorization = dict(
        created_at=time.time(), wall_seconds=args.wall_seconds,
        user_instruction="so do it",
        context="Approved 30-minute review-only continuation using existing results",
        scientific_steering=False, numerical_executions_allowed=False,
        runtime_version="0.7.0", runtime_commit="cfca558cb30868d7bc12af7a9b636303f7bc500b",
        controller="Case-owned post-run reviewer; unchanged released review transport and validators",
        controller_sha256=sha(Path(__file__)), original_study=str(root),
        original_deadline=service.manifest["deadline"], review=args.review,
    )
    put(session / "authorization.json", authorization)
    configure_limits(root, {"review_seconds": 300.0}, reason=
                     "Apply previously intended review setting via the operating-limits API; "
                     "post-run session has a separate 30-minute grant, no new simulations")
    host = AgentSupervisor(SimpleNamespace(
        campaign=root, state_dir=session, workflow="frontier", wall_seconds=args.wall_seconds,
        turn_seconds=300, backend="codex", model="gpt-6.1-sol", judge_model="gpt-6.1-sol",
        executable="/home/tomzhu0225/.local/bin/codex", reasoning_effort="high",
        judge_reasoning_effort="high", provider_config=None, judge_backend=None,
        judge_executable=None, judge_provider_config=None,
    ))
    outcome = dict(session=str(session), authority="Independent post-run review only",
                   numerical_status=original_state["status"], claim_review=args.review,
                   report_status="not_started", started_at=host.state["started_at"],
                   deadline=host.state["deadline"], authorization_sha256=sha(session / "authorization.json"))

    def check_protected():
        if protected(root) != baseline:
            raise ValueError("Protected numerical study records changed during review")

    def call(name, prompt, schema, allowances=(300, 600)):
        failures = []
        for attempt, seconds in enumerate(allowances, 1):
            if host.boundary():
                break
            directory = session / f"{name}-{attempt}"
            directory.mkdir()
            host.args.turn_seconds = seconds
            host.event("post_run_call", role=name, allowance_seconds=seconds)
            bounded = prompt + f"\nReturn the required JSON within {seconds} seconds."
            if failures:
                bounded += "\nPrevious attempt failed transport/schema validation: " + failures[-1]
            print(json.dumps(dict(stage=name, attempt=attempt, seconds=seconds)), flush=True)
            try:
                rc = host.launch(directory, bounded, judge=True)
                check_protected()
                if rc:
                    raise ValueError(f"Reviewer exited {rc}; no verdict recovered")
                result = schema.model_validate(parse_judge_stream(
                    directory / "response.json", "codex", allow_readonly_tools=True))
                put(directory / "validated_response.json", result.model_dump(mode="json"))
                return result, directory
            except (ValueError, RuntimeError) as error:
                failures.append(str(error))
                put(directory / "failure.json", dict(error=str(error), time=time.time()))
        raise ValueError(f"{name} did not complete: {failures}")

    try:
        request = service._read("reviews", args.review)
        if request["status"] != "queued" or service.review_blockers(request):
            raise ValueError("Claim review is not eligible and queued")
        packet = service.packet(service.review_body(request))
        put(session / "claim_packet.json", packet)
        verdict, directory = call("judge-claim", research_review_prompt(packet_view(root, packet)), ResearchVerdict)
        service.record_verdict(args.review, verdict.model_dump(mode="json"), packet_sha256=fingerprint(packet))
        outcome["claim_verdict"] = verdict.model_dump(mode="json")
        outcome["claim_response"] = str(directory.relative_to(session))
        put(session / "outcome.json", outcome)
        print(json.dumps(dict(stage="claim_recorded", **outcome["claim_verdict"])), flush=True)

        draft_prompt = (
            "You are revising this study's final scientific report after independent claim review. "
            "Read-only tools only: no files modified and no simulations, claims, methods or receipts created. "
            "Return the ENTIRE revised report in JSON under report_markdown; the host will save it. "
            "Keep a findings-first quantitative report, existing evidence references, controls, limitations "
            "and failed methods. Incorporate the actual independent verdict without strengthening it. "
            "If needs_revision, retain the unresolved claim and explain gaps and discriminating next tests. "
            "Correct these prior report-audit observations by inspecting existing artifacts: two broken "
            "figure links should refer to plots/mesh_refined_kinetic_fields.png and "
            "plots/mesh_refined_pressure_tensor.png; initial current/flow mismatch values must distinguish "
            "qualification baseline from fresh seeds 6101/6102. Do not change any scientific threshold or data. "
            "State that numerical execution used an initial two-hour allowance and independent claim/report "
            "review was completed in a separately authorized post-run review-only session, with no new simulations "
            "or human scientific verdict. Retain the difference between formal claim acceptance and report assessment. "
            f"Study: {root}\nReport: {root / 'research/RESULTS.md'}\n"
            f"Independent review: {root / 'reviews' / (args.review + '.json')}\n"
            f"SCHEMA: {json.dumps(Draft.model_json_schema())}"
        )
        draft, directory = call("report-draft", draft_prompt, Draft, (300,))
        check_protected()
        (root / "research/RESULTS.md").write_text(draft.report_markdown.rstrip() + "\n")
        outcome["report_writer_response"] = str(directory.relative_to(session))
        frozen, packet = service.freeze_report()
        frozen_hash = sha(frozen / "packet.json")
        report_prompt = ResearchFinalization._report_review_prompt(host, frozen, 300)
        report_prompt += (
            "\nCross-field schema rule: accepted REQUIRES issues=[]. Only blocking defects belong "
            "in issues; put nonblocking suggestions or scope qualifications in summary. Any blocking "
            "defect requires needs_revision and nonempty issues. Do not approve to fit the schema."
        )
        assessment, directory = call("judge-report", report_prompt, ReportAssessment, (300, 300))
        if sha(frozen / "packet.json") != frozen_hash or sha(frozen / "RESULTS.md") != packet["report_sha256"]:
            raise ValueError("Frozen report changed during independent assessment")
        put(frozen / "assessment.json", assessment.model_dump(mode="json"))
        outcome.update(report_status="reviewed" if assessment.decision == "accepted" else "needs_revision",
                       assessment=assessment.model_dump(mode="json"),
                       report=str((frozen / "RESULTS.md").relative_to(root)),
                       packet=str((frozen / "packet.json").relative_to(root)),
                       report_sha256=packet["report_sha256"], packet_sha256=frozen_hash,
                       assessment_sha256=sha(frozen / "assessment.json"),
                       report_response=str(directory.relative_to(session)))
        print(json.dumps(dict(stage="report_recorded", **outcome["assessment"])), flush=True)
        host.state["status"] = "completed"
    except Exception as error:
        outcome["error"] = f"{type(error).__name__}: {error}"
        host.state["status"] = host.boundary() or "review_incomplete"
        print(json.dumps(dict(stage="incomplete", error=outcome["error"])), flush=True)
    finally:
        check_protected()
        outcome["finished_at"] = time.time()
        outcome["session_status"] = host.state["status"]
        outcome["protected_records_unchanged"] = True
        put(session / "outcome.json", outcome)
        put(root / "post_run_review.json", outcome)
        host.save()
        # Refresh derived navigation only. Preserve the original terminal execution status.
        report = write_report(service, original_state)
        report["post_run_review"] = outcome
        put(root / "research_report.json", report)
        check_protected()
        print(json.dumps(dict(stage="finished", outcome=str(session / "outcome.json"))), flush=True)


if __name__ == "__main__":
    main()
