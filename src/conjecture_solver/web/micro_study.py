"""Response-wise self-contained micro-studies and on-demand independent reviews.

Allows an interactive workspace agent to execute a bounded autonomous verification
study within a single conversation turn or invoke an independent skeptical reviewer
on frozen project files without leaving the interactive chat workflow.
"""

from __future__ import annotations

import contextlib
import json
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..research_service import put
from ..review_assets import INLINE_SOURCE_BYTES, freeze_file
from ..workspace_agent import contained, run_agent


class MicroStudySpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=8, max_length=4000)
    success_criteria: str = Field(min_length=8, max_length=4000)
    constraints: str = Field(default="", max_length=4000)
    minutes: float = Field(default=15.0, ge=1.0, le=60.0, allow_inf_nan=False)
    completion_policy: Literal["answer", "repair"] = "answer"
    instrument: str = Field(default="", max_length=120)
    input_files: list[str] | None = None
    wait: bool = True


class IndependentReviewSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    claim: str = Field(min_length=8, max_length=4000)
    criteria: str = Field(default="", max_length=4000)
    evidence_files: list[str] = Field(min_length=1, max_length=32)


class IndependentReviewVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: Literal["accepted", "rejected", "needs_controls"]
    summary: str = Field(min_length=8, max_length=8000)
    missing_controls: list[str] = Field(default_factory=list, max_length=32)
    unverified_assumptions: list[str] = Field(default_factory=list, max_length=32)


def _extract_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Reviewer response did not contain a JSON verdict object")
    return json.loads(text[start : end + 1])


def review_work(workspace, identifier: str, payload: dict) -> dict:
    """Run an independent skeptical review over frozen SHA-256 project files."""
    spec = IndependentReviewSpec.model_validate(payload)
    directory = workspace.directory(identifier)
    files_root = (directory / "files").resolve()
    with workspace.lock():
        project = json.loads((directory / "project.json").read_text())
        config = workspace.project_connection(project)
        review_config = (
            config
            if config.get("backend") == "builtin"
            else (
                workspace.api_config()
                | {
                    "backend": "builtin",
                    "model": workspace.api_config().get("model") or config.get("model"),
                }
            )
        )
        if not review_config.get("base_url") or not review_config.get("model"):
            raise ValueError("Configure an API endpoint and model for independent review")
        reviews_root = directory / "reviews"
        reviews_root.mkdir(exist_ok=True)
        number = len(list(reviews_root.glob("*/packet.json"))) + 1
        review_id = f"rev-{number:03d}-{uuid.uuid4().hex[:8]}"
        review_dir = reviews_root / review_id
        review_dir.mkdir(parents=True, exist_ok=False)
        manifest, inline_sources = {}, {}
        for rel in spec.evidence_files:
            source = contained(files_root, rel)
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Evidence file {rel} must be a regular project file")
            frozen = freeze_file(review_dir, source)
            manifest[rel] = frozen
            if frozen["bytes"] <= INLINE_SOURCE_BYTES:
                inline_sources[rel] = source.read_text(encoding="utf-8", errors="replace")
        packet = dict(
            review_id=review_id,
            claim=spec.claim,
            criteria=spec.criteria or "Verify evidence, controls, and assumptions critically.",
            evidence_manifest=manifest,
            inline_sources=inline_sources,
            created_at=time.time(),
        )
        put(review_dir / "packet.json", packet)
    prompt = (
        "You are Simjecture's independent skeptical reviewer auditing interactive work.\n"
        "Examine whether the frozen evidence files justify the stated claim.\n"
        "Check for missing controls, unverified assumptions, or overclaims.\n"
        "For files larger than 32 KB not included in inline_sources, call "
        "read_review_asset(sha256=..., offset=..., max_bytes=...) using the SHA256 in "
        "evidence_manifest.\n"
        f"REVIEW PACKET:\n{json.dumps(packet, indent=2)}\n\n"
        "Respond with a JSON object matching this exact schema:\n"
        f"{json.dumps(IndependentReviewVerdict.model_json_schema())}"
    )
    raw = run_agent(
        prompt,
        review_dir,
        review_config,
        model=review_config.get("judge_model") or review_config["model"],
        wall_seconds=180,
        judge=True,
        review_root=review_dir,
    )
    verdict = IndependentReviewVerdict.model_validate(_extract_json_object(raw))
    result = dict(
        review_id=review_id,
        claim=spec.claim,
        **verdict.model_dump(),
        evidence_manifest=manifest,
        reviewed_at=time.time(),
    )
    put(review_dir / "verdict.json", result)
    summary_md = [
        f"# Independent Review `{review_id}`",
        "",
        f"- **Status:** `{verdict.status}`",
        f"- **Claim:** {spec.claim}",
        "",
        "## Summary",
        verdict.summary,
        "",
        "## Missing Controls",
        *([f"- {item}" for item in verdict.missing_controls] or ["- None identified"]),
        "",
        "## Unverified Assumptions",
        *([f"- {item}" for item in verdict.unverified_assumptions] or ["- None identified"]),
    ]
    report_name = f"REVIEW_{review_id}.md"
    (files_root / report_name).write_text("\n".join(summary_md) + "\n")
    result["report_file"] = report_name
    return result


def materialize_micro_study(workspace, identifier: str, spec: MicroStudySpec, application=None):
    from ..mvp_launch import start_managed_campaign
    from ..study_launch import NativeStudyRequest, materialize_native
    from .application import CampaignRegistry
    from .jobs import selected_inputs
    from .workspace import folder_name, load, private_json

    directory = workspace.directory(identifier)
    with workspace.lock():
        project = load(directory / "project.json")
        config = workspace.project_connection(project)
        selected = selected_inputs(directory, spec.input_files)
        number = len(project.get("studies", [])) + 1
        slug = re.sub(r"[^a-z0-9-]", "-", folder_name(spec.question)).strip("-") or "micro-study"
        campaign_id = f"{number:03d}-micro-{slug}"
        root = directory / "studies" / campaign_id
        while root.exists():
            number += 1
            campaign_id = f"{number:03d}-micro-{slug}"
            root = directory / "studies" / campaign_id
        root.parent.mkdir(exist_ok=True)
        frozen = workspace.root / "connections" / f"{identifier}-{number:03d}.json"
        private_json(frozen, config)
        judge_model = config.get("judge_model") or config["model"]
        capability_directory = (
            workspace._available_tools(instrument=spec.instrument or None)
            if spec.instrument
            else workspace._available_tools()
        )
        instruction = (
            f"Project objective: {project['name']}\n"
            f"Micro-study evidence criteria: {spec.success_criteria}\n"
            f"Constraints: {spec.constraints}\n"
            "Project input files are in project_inputs/. Execute a focused, self-contained "
            "verification study and record receipts before concluding."
        )
        request = NativeStudyRequest(
            hypothesis=spec.question,
            instruction=instruction,
            campaign_id="study-" + campaign_id,
            output_directory=str(root),
            engine="native",
            mode="minimal",
            backend=config["backend"],
            model=config["model"],
            judge_model=judge_model,
            reasoning_effort=config.get("reasoning_effort") or None,
            director_enabled=False,
            allow_solver_development=True,
            provider_config=str(frozen) if config["backend"] == "builtin" else None,
            completion_policy=spec.completion_policy,
            max_wall_seconds=spec.minutes * 60.0,
            max_command_seconds=min(600, int(spec.minutes * 60.0)),
            capability_directory=capability_directory,
            method_review_scope="used_instruments",
            execution_backend=workspace.execution["backend"],
        )
        plan = materialize_native(request)
        inputs = root / "research" / "project_inputs"
        inputs.mkdir(exist_ok=True)
        for source, rel in selected:
            target = inputs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        brief = dict(
            question=spec.question,
            success_criteria=spec.success_criteria,
            constraints=spec.constraints,
            hours=round(spec.minutes / 60.0, 4),
            completion_policy=spec.completion_policy,
            instrument=spec.instrument,
            micro_study=True,
        )
        put(root / "project-brief.json", brief)
        campaign = start_managed_campaign(plan)
        campaign.close()
        token = (
            application.registry.register(root)
            if application is not None
            else CampaignRegistry.token_for(root)
        )
        record = dict(
            campaign=token,
            campaign_id=campaign_id,
            question=spec.question,
            micro_study=True,
            path=str(root),
            created_at=time.time(),
            source_turn=project.get("active_turn"),
            explain_on_finish=False,
        )
        project.setdefault("studies", []).append(record)
        project["updated_at"] = time.time()
        put(directory / "project.json", project)
        workspace.write_index(directory)
    return root, record


def collect_micro_study_summary(directory: Path, root: Path, record: dict) -> dict:
    from ..research_finalization import working_report
    from ..study_status import study_status
    from .workspace import load

    live = study_status(root)
    report_data = load(root / "research_report.json")
    results_file = working_report(root, live.get("finalization")) or (root / "research/RESULTS.md")
    results_rel = (
        results_file.relative_to(root).as_posix()
        if results_file.exists()
        else "research/RESULTS.md"
    )
    ledger_text = (
        (root / "STUDY_LEDGER.md").read_text(encoding="utf-8", errors="replace")[:8000]
        if (root / "STUDY_LEDGER.md").is_file()
        else ""
    )
    experiments = live.get("experiments", [])
    exp_count = len(experiments) if isinstance(experiments, list) else experiments.get("total", 0)
    summary_file = f"MICRO_STUDY_{record['campaign_id']}.md"
    lines = [
        f"# Micro-Study `{record['campaign_id']}`",
        "",
        f"- **Question:** {record['question']}",
        f"- **Status:** `{live['status']}`",
        f"- **Study link:** `study:{record['campaign']}/{results_rel}`",
        f"- **Experiments recorded:** {exp_count}",
        "",
    ]
    if report_data.get("summary"):
        lines += ["## Report Summary", str(report_data["summary"]), ""]
    if ledger_text:
        lines += ["## Ledger Excerpt", ledger_text, ""]
    (directory / "files" / summary_file).write_text("\n".join(lines))
    return dict(
        campaign=record["campaign"],
        campaign_id=record["campaign_id"],
        question=record["question"],
        status=live["status"],
        activity=live.get("activity"),
        experiments=live.get("experiments", {}),
        report=report_data,
        summary_file=summary_file,
        study_link=f"study:{record['campaign']}/{results_rel}",
        path=str(root),
    )


def run_micro_study(workspace, identifier: str, payload: dict, application=None) -> dict:
    """Launch and optionally wait for a bounded self-contained autonomous micro-study."""
    from ..study_status import study_status

    spec = MicroStudySpec.model_validate(payload)
    directory = workspace.directory(identifier)
    root, record = materialize_micro_study(workspace, identifier, spec, application=application)
    if not spec.wait:
        return collect_micro_study_summary(directory, root, record)
    terminal = {
        "completed",
        "cancelled",
        "budget_exhausted",
        "interrupted",
        "paused_external_error",
    }
    deadline = time.time() + spec.minutes * 60.0 + 30.0
    last_activity = None
    while time.time() < deadline:
        live = study_status(root)
        act = live.get("activity")
        if act and act != last_activity:
            last_activity = act
            with contextlib.suppress(ValueError, OSError):
                workspace.progress_update(identifier, f"Micro-study {record['campaign_id']}: {act}")
        if live["status"] in terminal:
            break
        time.sleep(0.5)
    return collect_micro_study_summary(directory, root, record)
