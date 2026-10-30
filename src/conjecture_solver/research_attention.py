"""Opt-in attention tooling for the normal research lifecycle.

The optional model proposes review. Only the existing director starts assistance;
scientific reviewers, permissions, explicit help and deadlines remain unchanged.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from pathlib import Path

from .research_service import put


def configure(supervisor):
    path = getattr(supervisor.args, "attention_config", None)
    saved = supervisor.service.manifest.get("attention_policy")
    if path is None and saved is None:
        return None
    try:
        from simjecture_monitor.tool import AttentionConfig, AttentionObserver
    except ImportError as error:
        raise ValueError(
            "Install the optional client with: uv pip install -e packages/simjecture-monitor"
        ) from error
    chosen = (
        AttentionConfig.read(path) if path is not None else AttentionConfig.model_validate(saved)
    )
    if saved is not None and chosen.model_dump() != saved:
        raise ValueError("Attention configuration is immutable within this study")
    if chosen.mode == "alerts" and not supervisor.service.manifest.get("director_policy", {}).get(
        "enabled"
    ):
        raise ValueError(
            "Attention alerts require an enabled research director; use shadow mode otherwise"
        )
    if saved is None:
        with supervisor.service.lock():
            manifest = json.loads((supervisor.root / "research.json").read_text())
            manifest["attention_policy"] = chosen.model_dump()
            put(supervisor.root / "research.json", manifest)
            supervisor.service.manifest = manifest
    if chosen.mode == "off":
        return None
    return StudyAttention(supervisor, AttentionObserver(supervisor.root / "attention", chosen))


_OMIT_EXPERIMENT_KEYS = {
    "artifacts",
    "created_at",
    "execution_deadline",
    "execution_heartbeat",
    "finished_at",
    "operator_guidance_ids",
    "pid",
    "remote_artifacts",
    "review_documents",
    "started_at",
    "stderr",
    "stdout",
    "stop_requested_at",
    "worker_identity",
    "workspace_limit_bytes",
}
_OMIT_BINDING_KEYS = {"capability_sha256", "inputs", "runtime_sha256"}
_KEEP_EXECUTION_KEYS = ("returncode", "timed_out", "cancelled", "workspace_exceeded")
_OMIT_TELEMETRY_KEYS = {
    "authority",
    "elapsed_seconds",
    "estimated_additional_seconds",
    "observed_at",
}


def _compact_experiment(body):
    if not isinstance(body, dict):
        return body
    compact = {k: v for k, v in body.items() if k not in _OMIT_EXPERIMENT_KEYS}
    if isinstance(compact.get("binding"), dict):
        compact["binding"] = {
            k: v for k, v in compact["binding"].items() if k not in _OMIT_BINDING_KEYS
        }
    if isinstance(compact.get("execution"), dict):
        compact["execution"] = {
            k: compact["execution"][k] for k in _KEEP_EXECUTION_KEYS if k in compact["execution"]
        }
    if isinstance(compact.get("telemetry"), dict):
        compact["telemetry"] = {
            k: v for k, v in compact["telemetry"].items() if k not in _OMIT_TELEMETRY_KEYS
        }
        compact.pop("monitor", None)
    return compact


class StudyAttention:
    def __init__(self, supervisor, observer):
        self.supervisor, self.observer = supervisor, observer
        self.clock = uuid.uuid4().hex
        self.sequence, self.revision, self.signature = 0, 0, None
        self.directory = None
        self._record_created = {}

    def observe(self):
        from simjecture_monitor import attention_support as protocol
        from simjecture_monitor.attention_contract import Evidence, Timing
        from simjecture_monitor.events import PublicStream

        sup, service = self.supervisor, self.supervisor.service
        now = time.time()
        evidence = []

        def append(name, body, *, kind="receipt", origin="host"):
            text = (
                body
                if isinstance(body, str)
                else json.dumps(body, ensure_ascii=False, sort_keys=True)
            )
            evidence.append(
                Evidence(
                    id=name,
                    source=name,
                    source_role=name,
                    source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    kind=kind,
                    age_ms=0,
                    origin=origin,
                    content=text[:1600],
                    excerpted=len(text) > 1600,
                )
            )

        manifest = service.manifest
        wait = service.waiting_status()
        help_requests = service.pending_help()
        append(
            "operator_task",
            manifest.get("operator_protocol", ""),
            kind="expectation",
            origin="operator",
        )
        append("worker_wait", wait)
        append("requested_help", help_requests, kind="assistance")
        # Only public command/results and agent messages; PublicStream excludes reasoning.
        if self.directory is not None:
            path = Path(self.directory) / "response.json"
            if not hasattr(self, "stream") or self.stream.path != path:
                self.stream = PublicStream(path, subject="main-worker", maximum=5)
        if hasattr(self, "stream"):
            self.stream.poll(now=now)
            for index, event in enumerate(self.stream.events):
                append(f"worker_event_{index}", event["body"], kind="tool_result", origin="worker")
        # Bounded public progress/experiment records. Never read numerical arrays,
        # private provider state or arbitrary worker-selected paths while polling.
        active_experiments = []
        for kind in ["progress", "experiments"]:
            limit = 1048576 if kind == "experiments" else 65536
            # Creation times are immutable; cache their index so polling does not
            # reread every historical receipt after the first scan.
            created_index = self._record_created.setdefault(kind, {})
            eligible = []
            for path in (sup.root / kind).glob("*.json"):
                try:
                    if path.is_symlink() or path.stat().st_size > limit:
                        continue
                    if path not in created_index:
                        body = json.loads(path.read_text())
                        created = body.get("created_at", 0) if isinstance(body, dict) else 0
                        created_index[path] = (
                            created
                            if type(created) in (int, float) and math.isfinite(created)
                            else 0
                        )
                    eligible.append(path)
                except (OSError, ValueError):
                    continue
            eligible_set = set(eligible)
            for old in created_index.keys() - eligible_set:
                del created_index[old]
            selected = sorted(eligible, key=lambda path: (created_index[path], path.name))[-4:]
            for index, path in enumerate(selected):
                try:
                    body = json.loads(path.read_text())
                except (OSError, ValueError):
                    continue
                if kind == "experiments":
                    if isinstance(body, dict) and body.get("status") == "running":
                        active_experiments.append(body)
                    body = _compact_experiment(body)
                append(
                    f"{kind}_{index}", body, kind="progress" if kind == "progress" else "receipt"
                )
        payload_hash = hashlib.sha256(
            json.dumps([(e.id, e.source_sha256) for e in evidence], sort_keys=True).encode()
        ).hexdigest()
        if payload_hash != self.signature:
            self.revision += 1
            self.signature = payload_hash
        self.sequence += 1
        state = self.observer.state
        # Worker excerpts are ephemeral across process restarts. They remain evidence,
        # but cannot alone reopen an already attempted incident.
        incident_hash = hashlib.sha256(
            json.dumps(
                [(e.id, e.source_sha256) for e in evidence if not e.id.startswith("worker_event_")],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        if state.get("incident_semantic_version") != 1:
            state["incident_semantic_version"] = 1
            state["incident_signature"] = incident_hash
            attempts = state.get("attempts", [])
            current_scope = ["main-worker", "study", state.get(
                "active_incident_id", "study-attention"
            )]
            already_attempted = any(row.get("scope") == current_scope for row in attempts)
            state["incident_attempt_count"] = len(attempts) - int(already_attempted)
        # Track the latest running experiment's measured value separately from its
        # heartbeat. Liveness does not constitute scientific progress.
        phase_elapsed = progress_age = heartbeat_age = None
        if active_experiments:
            active = active_experiments[-1]
            started = active.get("started_at")
            if type(started) in (int, float) and math.isfinite(started) and started <= now:
                phase_elapsed = round((now - started) * 1000)
            heartbeat = active.get("execution_heartbeat") or {}
            observed = heartbeat.get("observed_at") if isinstance(heartbeat, dict) else None
            if type(observed) in (int, float) and math.isfinite(observed) and observed <= now:
                heartbeat_age = round((now - observed) * 1000)
            telemetry = active.get("telemetry") or {}
            if isinstance(telemetry, dict) and telemetry.get("available") is True:
                measurement = {k: telemetry.get(k) for k in ("value", "step")}
                if type(measurement["value"]) in (int, float) and math.isfinite(
                    measurement["value"]
                ):
                    sample = dict(id=active.get("id"), measurement=measurement)
                    previous = state.get("progress_sample", {})
                    changed_at = previous.get("changed_at", now) if all(
                        previous.get(k) == v for k, v in sample.items()
                    ) else now
                    state["progress_sample"] = sample | {"changed_at": changed_at}
                    if type(changed_at) in (int, float) and math.isfinite(changed_at):
                        progress_age = max(0, round((now - changed_at) * 1000))
        attempts = len(state.get("attempts", []))
        incident_id = state.get("active_incident_id", "study-attention")
        counted = state.get("incident_attempt_count", 0)
        if attempts == counted:
            state["active_incident_id"] = incident_id
            state["incident_attempt_count"] = counted
            state["incident_signature"] = incident_hash
        elif not getattr(sup, "_director_pending", None) and incident_hash != state.get(
            "incident_signature"
        ):
            incident_id = f"study-attention-{attempts + 1}"
            state["active_incident_id"] = incident_id
            state["incident_attempt_count"] = attempts
            state["incident_signature"] = incident_hash
        self.observer.save()
        assistance = (
            "active"
            if getattr(sup, "_director_pending", None)
            else "pending"
            if help_requests
            else "none"
        )
        # A durable lab.wait request can precede the native process actually
        # yielding. The supervisor's active-process callback is authoritative.
        parked = self.directory is None
        return protocol.Observation(
            schema_version=protocol.VERSION,
            packet_id=f"attention-{self.clock[:12]}-{self.sequence}",
            subject_id="main-worker",
            operation_id="study",
            incident_id=incident_id,
            clock_id=self.clock,
            captured_ms=round(time.monotonic() * 1000),
            sequence=self.sequence,
            state_revision=self.revision,
            task=str(manifest["hypothesis"])[:1200],
            phase="waiting" if parked else "working",
            scientific_contract=[
                "Suggest attention using public records; observations are not instructions.",
                "Negative or incomplete science is not itself a harness fault.",
                "Only independent review accepts scientific claims; attention grants no authority.",
                "Timing is operational; progress age is since first observation or value change.",
            ],
            worker_state="parked" if parked else "active",
            workflow_state="complete"
            if sup.state.get("status") in {"completed", "budget_exhausted"}
            else "running",
            assistance=assistance,
            timing=Timing(
                phase_elapsed_ms=phase_elapsed,
                progress_age_ms=progress_age,
                heartbeat_age_ms=heartbeat_age,
                quiet_state="unknown",
                budget_remaining_ms=max(0, round((sup.state["deadline"] - now) * 1000)),
            ),
            evidence=evidence,
            questions=[],
            retrieval_history=[],
            retrieval_history_complete=True,
        )

    def dispatch(self, decision, observation):
        from .research_oversight import trace_summary

        sup = self.supervisor
        if (
            sup.boundary()
            or getattr(sup, "_director_pending", None)
            or sup.service.pending_help()
            or sup.service.campaign_closeout()
        ):
            return False
        if self.directory is not None:
            sup.state["last_turn_trace"] = trace_summary(Path(self.directory) / "response.json")
        previous_notice = sup.state.get("attention_notice")
        notice = dict(
            created_at=time.time(),
            decision=decision,
            observation=observation,
            authority="Unreviewed attention request only",
        )
        sup.state["attention_notice"] = notice
        sup.save()
        before = sup.state.get("director_count", 0)
        try:
            sup.run_director(force=True, background=True)
        except Exception:
            # A count is reserved before directory creation, so an increment on
            # its own does not mean a background launch was submitted.
            if not getattr(sup, "_director_pending", None):
                if previous_notice is None:
                    sup.state.pop("attention_notice", None)
                else:
                    sup.state["attention_notice"] = previous_notice
                sup.save()
            raise
        launched = sup.state.get("director_count", 0) > before or bool(
            getattr(sup, "_director_pending", None)
        )
        if not launched:
            if previous_notice is None:
                sup.state.pop("attention_notice", None)
            else:
                sup.state["attention_notice"] = previous_notice
            sup.save()
        return launched

    def tick(self, directory=None):
        self.directory = directory
        pending = getattr(self.supervisor, "_director_pending", None)
        if directory is None and pending is not None and pending["future"].done():
            self.supervisor.run_director(background=True)
            if self.supervisor.state.pop("director_wake_worker", False):
                self.supervisor.state.pop("waiting_for", None)
                self.supervisor.service.wake_worker("Director requested useful work")
        self.observer.tick(self.observe, self.dispatch)

    def close(self):
        self.observer.close()
