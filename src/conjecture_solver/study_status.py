"""Shared, read-only native-study status and a quiet live terminal display."""

from __future__ import annotations

import json
import math
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
    recorded_status = status
    if deadline <= now and status not in {"completed", "cancelled"}:
        status = "budget_exhausted"
    elif status == "running":
        from .mvp_launch import load_supervisor_record, process_identity_matches

        identity = load_supervisor_record(root)
        if identity and not process_identity_matches(identity):
            status = "interrupted"
    early_stop = (
        recorded_status in {"paused_external_error", "interrupted"}
        and state.get("updated_at", now) < deadline
    )
    elapsed_end = (
        min(now, state.get("updated_at", now))
        if early_stop
        else min(now, deadline)
        if status in {"running", "budget_exhausted"}
        else state.get("updated_at", now)
    )
    counts = Counter(e.get("status", "unknown") for e in experiments)
    activity = state.get("activity", "Starting backend")
    if state.get("waiting_for"):
        activity = "Running numerical experiments"
    if status != "running":
        activity = status.replace("_", " ")
        if status == "paused_external_error" and state.get("last_error"):
            activity = state.get("provider_attention") or (activity + ": " + state["last_error"])
        if status == "budget_exhausted" and early_stop:
            activity += " · stopped early: " + str(state.get("last_error") or recorded_status)
    if state.get("provider_next_retry_at") and status == "running":
        activity = (
            f"Reconnecting provider (attempt {state.get('provider_retry_count', 0)}, "
            f"{max(0, state['provider_next_retry_at'] - now):.0f}s to retry)"
        )
    if status == "running" and state.get("no_progress_streak", 0) >= 2:
        activity += f" · {state['no_progress_streak']} turns without observed progress"
    by_thread = dict(state.get("usage_by_thread", {}))
    if state.get("active_usage_directory") and status == "running":
        from .provider_usage import request_accounting

        active = Path(state["active_usage_directory"])
        if active.resolve().is_relative_to(directory.resolve()):
            current = request_accounting(active / "response.json")
            if current is not None:
                by_thread[active.resolve().relative_to(directory.resolve()).as_posix()] = current
    counters = list(by_thread.values())
    usage = {
        k: sum(u.get(k, 0) for u in counters)
        for k in ["input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens"]
    }
    from .research_methods import instrument_requirement

    by_role, cache_complete = {}, {}
    for name, counter in by_thread.items():
        role = state.get("usage_roles_by_thread", {}).get(name) or (
            "memory"
            if name.startswith("journal-summary-")
            else "reviewer"
            if name.startswith(("oversight-", "judge-", "review-"))
            else "director"
            if name.startswith("director-")
            else "worker"
            if name.startswith("turn-")
            else "other"
        )
        row = by_role.setdefault(
            role, dict(input_tokens=0, output_tokens=0, requests=0, cached_input_tokens=0)
        )
        for key in row:
            row[key] += counter.get(key, 0)
        cache_complete[role] = cache_complete.get(role, True) and bool(
            counter.get("cache_usage_complete", "cached_input_tokens" in counter)
        )
    for role, row in by_role.items():
        complete = cache_complete[role]
        row["cache_usage_complete"] = complete
        row["uncached_input_tokens"] = (
            row["input_tokens"] - row["cached_input_tokens"]
            if complete and row["input_tokens"] >= row["cached_input_tokens"]
            else None
        )
    usage_details = dict(
        by_role=by_role,
        requests=sum(u.get("requests", 0) for u in counters),
        request_count_complete=bool(counters) and all("requests" in u for u in counters),
        requests_without_usage=sum(u.get("requests_without_usage", 0) for u in counters),
        cache_usage_complete=bool(counters)
        and all(u.get("cache_usage_complete", "cached_input_tokens" in u) for u in counters),
        reasoning_usage_complete=bool(counters)
        and all(
            u.get("reasoning_usage_complete", "reasoning_output_tokens" in u) for u in counters
        ),
        cost_status="unavailable",
        cost_note="Provider billing and cache pricing are not inferred from token totals.",
    )
    available = set(manifest.get("capability_hashes", {}))
    available.update(
        r["name"]
        for p in (root / "capability_additions").glob("*.json")
        if (r := read(p)).get("name")
    )
    progress = []
    if mode == "minimal" and (root / "progress").is_dir():
        from .research_service import ResearchService

        progress = ResearchService(root).progress_summary(max(0, deadline - now))
    director_decisions = []
    if (root / "director").is_dir():
        from .research_service import ResearchService

        director_decisions = ResearchService(root).director_status()
    from .research_finalization import report_status

    return dict(
        finalization=report_status(root, manifest),
        director_policy=manifest.get("director_policy", {"enabled": False}),
        director_route=state.get("reviewer_route", {}),
        director_decisions=director_decisions,
        director_next_review_at=state.get("director_next_review_at"),
        director_deferred_count=state.get("director_deferred_count", 0),
        diagnostic_errors=state.get("diagnostic_errors", {}),
        recorded_error=state.get("last_error") if early_stop else None,
        stopped_with_remaining_seconds=max(0, deadline - state["updated_at"])
        if early_stop
        else None,
        live_experiments=[
            {
                k: e.get(k)
                for k in ["id", "status", "monitor", "telemetry", "cancel_requested", "stop_reason"]
            }
            for e in experiments
            if e.get("monitor") and e.get("status") in {"queued", "running"}
        ],
        receipt_progress=progress,
        execution_costs=[
            dict(
                id=e["id"],
                source=e.get("binding", {}).get("source"),
                args=e.get("binding", {}).get("args", []),
                machine=e.get("machine", "local"),
                status=e["status"],
                stage=e.get("stage"),
                wall_seconds=e["execution"]["wall_seconds"],
                end_to_end_seconds=max(0, e["finished_at"] - e["created_at"])
                if all(
                    type(e.get(k)) in {int, float} and math.isfinite(e[k])
                    for k in ("finished_at", "created_at")
                )
                else None,
            )
            for e in reversed(experiments)
            if (e.get("execution") or {}).get("wall_seconds") is not None
        ][:6],
        execution_backend="worker-pool"
        if manifest.get("execution_pool")
        else launch.get(
            "execution_backend",
            manifest.get(
                "execution_backend",
                manifest.get("config", {}).get("execution_backend", "bubblewrap"),
            ),
        ),
        provider_retry_count=state.get("provider_retry_count", 0),
        provider_error_category=state.get("provider_error_category"),
        provider_attention=state.get("provider_attention")
        if status == "paused_external_error"
        else None,
        provider_wait_seconds=state.get("provider_wait_seconds", 0),
        failed_provider_turn_seconds=state.get("failed_provider_turn_seconds", 0),
        oversight_count=state.get("oversight_count", 0),
        oversight_feedback=state.get("oversight_feedback"),
        no_progress_streak=state.get("no_progress_streak", 0),
        session_recoveries=state.get("session_recoveries", 0),
        methods=[read(p) for p in sorted((root / "methods").glob("*.json"))],
        usage=usage,
        usage_details=usage_details,
        instrument_requirement=instrument_requirement(manifest, available=sorted(available)),
        usage_available=any(
            u.get("accounting") != "provider_requests" or u.get("reported_requests", 0)
            for u in counters
        ),
        usage_incomplete_turns=state.get("usage_incomplete_turns", 0),
        mode=mode,
        backend=launch.get("backend", state.get("backend", "unknown")),
        model=launch.get("model", state.get("model", "unknown")),
        status=status,
        recorded_status=recorded_status,
        budget_expired=deadline <= now,
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
    placement = ""
    if status.get("execution_backend") == "worker-pool":
        active = Counter(
            e["machine"]
            for e in status["experiments"]
            if e.get("machine") and e["status"] in {"queued", "running"}
        )
        unreachable = sorted(
            {
                e["machine"]
                for e in status["experiments"]
                if e.get("machine") and e.get("transport_status") == "unreachable"
            }
        )
        if active:
            placement += " | workers " + ", ".join(
                f"{name}:{n}" for name, n in sorted(active.items())
            )
        if unreachable:
            placement += " | SSH unreachable " + ", ".join(unreachable)
    return (
        f"{status['mode']} · {status['backend']}/{status['model']} · "
        f"{status.get('execution_backend', 'bubblewrap')} | "
        f"{status['activity']} | {int(status['elapsed']) // 60:02d}:"
        f"{int(status['elapsed']) % 60:02d} elapsed · {int(status['remaining']) // 60}m left | "
        f"jobs {counts.get('running', 0)} running / {counts.get('succeeded', 0)} done / "
        f"{counts.get('failed', 0)} failed | "
        f"reviews {sum(r.get('status') == 'queued' for r in status['reviews'])} queued · "
        f"oversight {status.get('oversight_count', 0)} | "
        f"tokens {status['usage']['input_tokens']:,} in / "
        f"{status['usage']['output_tokens']:,} out · "
        f"provider wait {status.get('provider_wait_seconds', 0) / 60:.1f}m{placement}"
    )


class TerminalProgress:
    def __init__(self, root, *, quiet=False, stream=None):
        self.root, self.quiet = root, quiet
        self.stream = stream or sys.stderr
        self.stop = threading.Event()
        self.thread = None
        self.tty_drawn = False

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
                    usage = status["usage"]
                    accounting = (
                        f"Tokens {usage['input_tokens']:,} in / {usage['output_tokens']:,} out | "
                        f"Retry wait {status.get('provider_wait_seconds', 0) / 60:.1f}m | "
                        f"Requests {status['usage_details']['requests']}"
                    )
                    if self.tty_drawn:
                        self.stream.write("\033[F")
                    self.stream.write("\r\033[K" + line[: max(20, width - 1)] + "\n")
                    self.stream.write("\r\033[K" + accounting[: max(20, width - 1)])
                    self.tty_drawn = True
                else:
                    self.stream.write(line + "\n")
                self.stream.flush()
                previous, last = key, time.monotonic()
            self.stop.wait(1)

    def __exit__(self, *exc):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
            prefix = "\r\033[K\033[F\033[K" if self.tty_drawn else ""
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
            machine=e.get("machine", "local"),
            remote_job=e.get("remote_job"),
            transport_status=e.get("transport_status"),
            assigned_gpu_ids=e.get("assigned_gpu_ids") or [],
            active_claim_id=e.get("commitment") or "root",
            elapsed_wall_seconds=max(
                0,
                (e.get("finished_at") or time.time())
                - (e.get("started_at") or e.get("created_at") or time.time()),
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
        finishing = status.get("finalization", {})
        if finishing:
            conclusion = (
                f"Report: {finishing.get('report_status', 'not_started').replace('_', ' ')}. "
                "Report assessment and scientific claim approval are separate.\n\n" + conclusion
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
            config=dict(
                mode="minimal",
                backend=status["backend"],
                model=status["model"],
                execution_backend=status["execution_backend"],
                provider_retry_count=status["provider_retry_count"],
                provider_wait_seconds=status["provider_wait_seconds"],
            ),
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
            reasoning_tokens=status["usage"]["reasoning_output_tokens"],
            label=(
                f"Reported: {status['usage']['input_tokens']:,} in / "
                f"{status['usage']['output_tokens']:,} out (reported usage)"
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
                    | dict(
                        mode=status["mode"],
                        backend=status["backend"],
                        model=status["model"],
                        execution_backend=status["execution_backend"],
                        provider_retry_count=status["provider_retry_count"],
                        provider_wait_seconds=status["provider_wait_seconds"],
                    )
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
                reasoning_tokens=usage["reasoning_output_tokens"],
                label=f"Reported: {usage['input_tokens']:,} in / {usage['output_tokens']:,} out"
                if status["usage_available"]
                else "Usage pending",
            ),
        )
    )
