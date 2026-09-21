"""Shared, read-only native-study status and a quiet live terminal display."""

from __future__ import annotations

import json
import sys
import threading
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def read(path):
    try:
        value = json.loads(Path(path).read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def supervisor_directory(root):
    launch = read(Path(root) / "study-launch.json")
    return Path(launch.get("state_dir") or Path(root) / "supervisor")


def study_status(root):
    root = Path(root)
    manifest = read(root / "research.json") or read(root / "mvp_manifest.json")
    launch = read(root / "study-launch.json")
    directory = supervisor_directory(root)
    state = read(directory / "state.json")
    mode = (
        read(root / "study-mode.json").get("mode")
        or state.get("mode")
        or ("minimal" if (root / "research.json").exists() else state.get("workflow", "structured"))
    )
    experiments = [read(p) for p in sorted((root / "experiments").glob("*.json"))]
    if mode != "minimal":
        experiments = [read(p) for p in sorted((root / "jobs/jobs").glob("*/state.json"))]
    reviews = [read(p) for p in sorted((root / "reviews").glob("*.json"))]
    experiments.sort(key=lambda e: str(e.get("created_at", "")))
    reviews.sort(key=lambda r: r.get("created_at", 0))
    now = time.time()
    started = manifest.get("created_at") or state.get("started_at", now)
    deadline = state.get("deadline", manifest.get("deadline", now))
    status = state.get("status", "initialized")
    elapsed_end = now if status == "running" else state.get("updated_at", now)
    counts = Counter(e.get("status", "unknown") for e in experiments)
    activity = state.get("activity", "Starting backend")
    if state.get("waiting_for"):
        activity = "Running numerical experiments"
    if status != "running":
        activity = status.replace("_", " ")
        if status == "paused_external_error" and state.get("last_error"):
            activity += ": " + state["last_error"]
    counters = list(state.get("usage_by_thread", {}).values())
    usage = {
        k: sum(u.get(k, 0) for u in counters)
        for k in ["input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens"]
    }
    return dict(
        usage=usage,
        usage_available=bool(counters),
        mode=mode,
        backend=launch.get("backend", state.get("backend", "unknown")),
        model=launch.get("model", state.get("model", "unknown")),
        status=status,
        activity=activity,
        round=state.get("round", 0),
        elapsed=max(0, elapsed_end - started),
        remaining=max(0, deadline - now),
        budget=max(0, deadline - started),
        heartbeat=state.get("heartbeat_at"),
        last_activity=state.get("last_activity_at"),
        experiments=experiments,
        experiment_counts=dict(counts),
        reviews=reviews,
        state=state,
        hypothesis=manifest.get("hypothesis", ""),
        launch=launch,
        manifest=manifest,
    )


def status_line(status):
    counts = status["experiment_counts"]
    return (
        f"{status['mode']} · {status['backend']}/{status['model']} | "
        f"{status['activity']} | {int(status['elapsed']) // 60:02d}:"
        f"{int(status['elapsed']) % 60:02d} elapsed · {int(status['remaining']) // 60}m left | "
        f"jobs {counts.get('running', 0)} running / {counts.get('succeeded', 0)} done / "
        f"{counts.get('failed', 0)} failed | "
        f"reviews {sum(r.get('status') == 'queued' for r in status['reviews'])} queued"
    )


class TerminalProgress:
    def __init__(self, root, *, quiet=False, stream=None):
        self.root, self.quiet = root, quiet
        self.stream = stream or sys.stderr
        self.stop = threading.Event()
        self.thread = None

    def __enter__(self):
        if not self.quiet:
            self.thread = threading.Thread(target=self._watch, daemon=True)
            self.thread.start()
        return self

    def _watch(self):
        previous, last = None, 0
        tty = self.stream.isatty()
        while not self.stop.is_set():
            status = study_status(self.root)
            key = (
                status["activity"],
                status["experiment_counts"],
                [(r.get("id"), r.get("status")) for r in status["reviews"]],
            )
            if tty or key != previous or time.monotonic() - last >= 30:
                line = status_line(status)
                if tty:
                    import shutil

                    width = shutil.get_terminal_size((120, 24)).columns
                    self.stream.write("\r\033[K" + line[: max(20, width - 1)])
                else:
                    self.stream.write(line + "\n")
                self.stream.flush()
                previous, last = key, time.monotonic()
            self.stop.wait(1)

    def __exit__(self, *exc):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
            prefix = "\r\033[K" if self.stream.isatty() else ""
            self.stream.write(prefix + status_line(study_status(self.root)) + "\n")
            self.stream.write(f"Records: {self.root}\n")
            self.stream.flush()


def minimal_snapshot(root):
    from .mvp_agent import MVPLoopState
    from .mvp_monitor import (
        ArtifactPaths,
        ClaimSummary,
        ComputeExecutionSummary,
        CurrentAction,
        HeartbeatObservation,
        HumanizedEvent,
        MVPRunSnapshot,
        RunIdentity,
        RunPhase,
        TerminalReportSummary,
        TokenUsageSummary,
    )

    root = Path(root)
    status = study_status(root)
    state, manifest = status["state"], status["manifest"]
    phases = {
        "running": RunPhase.INCOMPLETE,
        "initialized": RunPhase.INITIALIZED,
        "paused": RunPhase.PAUSED,
        "paused_external_error": RunPhase.PROVIDER_FAILED,
    }
    try:
        phase = RunPhase(status["status"])
    except ValueError:
        phase = phases.get(status["status"], RunPhase.INCOMPLETE)
    nodes = [dict(id="root", statement=status["hypothesis"], parent=None)]
    nodes += [read(p) for p in sorted((root / "commitments").glob("*.json"))]
    claims = []
    for node in nodes:
        reviews = [r for r in status["reviews"] if r.get("claim") == node["id"]]
        accepted = [r for r in reviews if r.get("verdict", {}).get("decision") == "approved"]
        verdict = accepted[-1].get("verdict", {}) if accepted else {}
        claims.append(
            ClaimSummary(
                id=node["id"],
                status=verdict.get("disposition", "open"),
                kind="scientific",
                relation="root" if node["id"] == "root" else "repairs",
                parent_id=node.get("parent"),
                statement=node["statement"],
                evidence_count=sum(len(r.get("experiments", [])) for r in reviews),
                sufficient_evidence_count=sum(len(r.get("experiments", [])) for r in accepted),
                closed_reason=verdict.get("rationale"),
            )
        )
    executions = tuple(
        ComputeExecutionSummary(
            id=e["id"],
            iteration=i,
            action_name="run_python",
            description=e.get("binding", {}).get("source", e["id"]),
            status=e["status"],
            returncode=e.get("execution", {}).get("returncode"),
            console_excerpt=(
                e.get("execution", {}).get("stdout", "")
                + "\n"
                + e.get("execution", {}).get("stderr", "")
            )[-12000:].strip()
            or None,
            capability=e.get("binding", {}).get("capability"),
            active_claim_id=e.get("commitment") or "root",
            elapsed_wall_seconds=max(
                0, e.get("finished_at", time.time()) - e.get("started_at", time.time())
            ),
        )
        for i, e in enumerate(status["experiments"], 1)
    )
    events = []
    for r in status["reviews"][-40:]:
        verdict = r.get("verdict", {})
        events.append(
            HumanizedEvent(
                sequence=len(events),
                kind="review",
                summary=f"{r.get('claim')}: {verdict.get('disposition', r.get('status'))}",
                research_note=verdict.get("rationale"),
                outcome=verdict.get("decision"),
            )
        )
    current = CurrentAction(
        iteration=max(1, status["round"]),
        description=status["activity"],
        pending=status["status"] == "running",
        model=status["model"],
        route=status["backend"],
    )
    now = datetime.now(UTC)
    report = None
    if (root / "research_report.json").exists():
        accepted = [c for c in claims if c.status in {"supported", "falsified"}]
        conclusion = "\n\n".join(
            f"**{c.status.title()}**: {c.statement}\n\n{c.closed_reason or ''}" for c in accepted
        )
        if status["status"] != "completed":
            conclusion = (
                "No completed scientific conclusion. Study status: "
                + status["activity"]
                + ".\n\n"
                + conclusion
            )
        report = TerminalReportSummary(
            status=status["status"],
            final_answer=conclusion or "No accepted scientific conclusion.",
            iterations=status["round"],
            elapsed_wall_seconds=status["elapsed"],
        )
    return MVPRunSnapshot(
        phase=phase,
        phase_label=status["status"].replace("_", " ").title(),
        identity=RunIdentity(
            run_directory=str(root),
            campaign_id=root.name,
            hypothesis=status["hypothesis"],
            campaign_instruction=manifest.get("operator_protocol"),
            config=dict(mode="minimal", backend=status["backend"], model=status["model"]),
            capability_hashes=manifest.get("capability_hashes", {}),
        ),
        configured_wall_seconds=status["budget"],
        elapsed_wall_seconds=status["elapsed"],
        iterations=status["round"],
        claims=tuple(claims),
        current_action=current,
        executions=executions,
        execution_total=len(executions),
        recent_events=tuple(events),
        loop_state=MVPLoopState(
            stage="falsification", role="falsifier", detail=status["activity"], updated_at=now
        ),
        latest_heartbeat=HeartbeatObservation(
            iteration=max(1, status["round"]),
            age_seconds=max(
                0, time.time() - state.get("heartbeat_at", state.get("updated_at", time.time()))
            ),
        ),
        artifacts=ArtifactPaths(
            run_directory=str(root),
            manifest=str(root / "research.json"),
            workspace=str(root / "research"),
            report=str(root / "research_report.json"),
        ),
        token_usage=TokenUsageSummary(
            prompt_tokens=status["usage"]["input_tokens"],
            completion_tokens=status["usage"]["output_tokens"],
            total_tokens=status["usage"]["input_tokens"] + status["usage"]["output_tokens"],
            cached_tokens=status["usage"]["cached_input_tokens"],
            label=(
                f"Reported: {status['usage']['input_tokens']:,} in / "
                f"{status['usage']['output_tokens']:,} out (completed turns)"
            )
            if status["usage_available"]
            else "Usage unavailable until a provider counter arrives",
        ),
        last_model=status["model"],
        report=report,
        workspace_bytes=sum(
            meta.get("bytes", 0)
            for e in status["experiments"]
            for meta in e.get("artifacts", {}).values()
        ),
        warnings=(
            ()
            if status["usage_available"]
            else ("No completed-turn provider usage is available for this record.",)
        ),
    )


def native_snapshot_overlay(root, snapshot):
    """Keep the legacy scientific ledger, overlay the actual native supervisor activity."""
    from .mvp_monitor import (
        ComputeExecutionSummary,
        CurrentAction,
        HeartbeatObservation,
        RunPhase,
        TokenUsageSummary,
    )

    status = study_status(root)
    phase = snapshot.phase
    if status["status"] == "paused":
        phase = RunPhase.PAUSED
    elif status["status"] == "paused_external_error":
        phase = RunPhase.PROVIDER_FAILED
    elif status["status"] in ["cancelled", "budget_exhausted"]:
        phase = RunPhase(status["status"])
    usage = status["usage"]
    jobs = []
    for number, job in enumerate(status["experiments"], 1):
        identifier = job.get("job_id")
        if not identifier:
            continue
        request = read(Path(root) / "jobs/jobs" / identifier / "request.json")
        meta = request.get("metadata", {})
        jobs.append(
            ComputeExecutionSummary(
                id=identifier,
                iteration=number,
                status=job["status"],
                action_name=meta.get("action", "run_python"),
                description=meta.get("research_note") or "Recorded numerical job",
                capability=meta.get("capability"),
                active_claim_id=meta.get("active_claim_id"),
                argv=tuple(meta.get("argv", [])),
                stage=meta.get("stage"),
            )
        )
    return snapshot.model_copy(
        update=dict(
            identity=snapshot.identity.model_copy(
                update={
                    "config": snapshot.identity.config
                    | dict(mode=status["mode"], backend=status["backend"], model=status["model"])
                }
            ),
            phase=phase,
            phase_label=status["status"].replace("_", " ").title(),
            elapsed_wall_seconds=status["elapsed"],
            configured_wall_seconds=status["budget"],
            iterations=status["round"],
            last_model=status["model"],
            current_action=CurrentAction(
                iteration=max(1, status["round"]),
                description=status["activity"],
                pending=status["status"] == "running",
                model=status["model"],
                route=status["backend"],
            ),
            latest_heartbeat=HeartbeatObservation(
                iteration=max(1, status["round"]),
                age_seconds=max(0, time.time() - status["state"].get("heartbeat_at", time.time())),
            ),
            executions=tuple(jobs) or snapshot.executions,
            execution_total=len(jobs) or snapshot.execution_total,
            token_usage=TokenUsageSummary(
                prompt_tokens=usage["input_tokens"],
                completion_tokens=usage["output_tokens"],
                total_tokens=usage["input_tokens"] + usage["output_tokens"],
                cached_tokens=usage["cached_input_tokens"],
                label=f"Reported: {usage['input_tokens']:,} in / {usage['output_tokens']:,} out"
                if status["usage_available"]
                else "Usage pending",
            ),
        )
    )
