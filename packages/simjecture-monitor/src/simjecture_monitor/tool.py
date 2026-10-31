"""Optional attention client; inference is external and the host owns every action."""

from __future__ import annotations

import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import attention_support as protocol
from .action_distribution import CONTRACT, INDEPENDENT
from .attention_admission import AdmissionProfile
from .events import put
from .server import request

RELEASE = "tomzhu0225/Conjecture-1-4B@v0.1"
ADAPTER_SHA256 = "76bf1bdf4c6d6a261211057d3cab4c8609131788827569f9c33f802d3491dab5"
BASE_CONFIG_SHA256 = "ddc63e1c717afa86c865bb5e01313d89d72bb53b97ad4a8a03ba8510c0621670"


class AttentionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    mode: Literal["off", "shadow", "alerts"] = "shadow"
    socket: str = ""
    auth_token_file: str = ""
    policy: str = Field(default="conjecture1", min_length=1, max_length=80)
    adapter_sha256: str = Field(default=ADAPTER_SHA256, pattern=r"^[0-9a-f]{64}$")
    base_config_sha256: str = Field(default=BASE_CONFIG_SHA256, pattern=r"^[0-9a-f]{64}$")
    decision_distribution: Literal[INDEPENDENT, CONTRACT] = INDEPENDENT
    temperature: float = Field(default=1.0, gt=0, le=10)
    poll_seconds: float = Field(default=5.0, ge=1, le=300)
    timeout_seconds: float = Field(default=10.0, gt=0, le=25)
    maximum_requests: int = Field(default=720, ge=1, le=100000)
    maximum_alerts: int = Field(default=1, ge=1, le=100)
    cooldown_seconds: float = Field(default=90.0, ge=5, le=86400)

    @model_validator(mode="after")
    def explicit_runtime(self):
        if self.mode != "off" and not all(
            Path(value).is_absolute() for value in [self.socket, self.auth_token_file]
        ):
            raise ValueError("Specify absolute socket and token-file paths for the model service")
        return self

    @classmethod
    def read(cls, path):
        return cls.model_validate_json(Path(path).read_text())

    def admission_profile(self) -> AdmissionProfile:
        # The reference profile assumes short polling. Longer configured polls
        # must allow a fresh second observation to confirm the same request.
        # Bound scheduling slack below a whole extra poll and leave response
        # freshness, grounding and all other admission rules unchanged.
        reference = AdmissionProfile()
        poll_ms = math.ceil(self.poll_seconds * 1000)
        maximum_gap_ms = max(
            reference.maximum_gap_ms,
            poll_ms + min(poll_ms // 2, reference.maximum_age_ms),
        )
        return replace(reference, maximum_gap_ms=maximum_gap_ms)

    def verify_liveness(self, *, profile: AdmissionProfile | None = None) -> dict:
        profile = profile or self.admission_profile()
        poll_ms = math.ceil(self.poll_seconds * 1000)
        if profile.maximum_gap_ms <= poll_ms:
            raise ValueError("Admission confirmation gap must exceed the polling interval")
        steps = max(
            profile.minimum_confirmations,
            math.ceil(profile.persistence_ms / poll_ms) + 1,
        )
        gate = protocol.AdmissionGate(profile)
        content = "Synthetic pre-flight confirmation probe."
        digest = hashlib.sha256(content.encode()).hexdigest()
        last = None
        for index in range(steps):
            at_ms = 100_000 + index * poll_ms
            packet = protocol.Observation(
                schema_version=protocol.VERSION,
                packet_id=f"preflight-{index + 1}",
                subject_id="preflight-worker",
                operation_id="preflight-operation",
                incident_id="preflight-incident",
                clock_id="preflight-clock",
                captured_ms=at_ms,
                sequence=index + 1,
                state_revision=1,
                task="Verify cadence confirmation liveness.",
                phase="diagnostic",
                scientific_contract=["Confirm two fresh grounded observations."],
                worker_state="parked",
                workflow_state="running",
                assistance="none",
                timing=dict(
                    phase_elapsed_ms=40_000,
                    progress_age_ms=35_000,
                    heartbeat_age_ms=100,
                    quiet_state="none",
                ),
                evidence=[
                    dict(
                        id="preflight-evidence",
                        source="preflight-source",
                        source_role="diagnostic_log",
                        source_sha256=digest,
                        kind="progress",
                        age_ms=35_000,
                        origin="instrument",
                        content=content,
                    )
                ],
                questions=[],
                retrieval_history=[],
                retrieval_history_complete=True,
            )
            view = protocol.pack(
                packet, len, token_counter_id="preflight:characters", budget_tokens=100_000
            )
            choice = protocol.Choice(
                action="wake_director",
                support_kind="none",
                question_ref=None,
                basis="measurement",
                evidence=[next(iter(view.aliases))],
            )
            decision = protocol.bind_choice(packet, view, choice, policy_id=self.policy)
            last = gate.evaluate(packet, view, decision, packet, now_ms=at_ms)
        if not last or last.get("disposition") != "admitted":
            raise ValueError("Admission gate cannot confirm at the configured polling interval")
        return dict(
            confirmations_required=steps,
            confirmation_span_ms=(steps - 1) * poll_ms,
            maximum_gap_ms=profile.maximum_gap_ms,
            maximum_age_ms=profile.maximum_age_ms,
            budget_horizon_seconds=self.maximum_requests * self.poll_seconds,
        )


class AttentionClient:
    def __init__(self, config):
        self.config = config

    def call(self, payload):
        if self.config.mode == "off":
            raise ValueError("Attention is disabled")
        token = Path(self.config.auth_token_file).read_text().strip()
        if len(token) < 32:
            raise ValueError("The model service requires a private authentication token")
        return request(
            self.config.socket,
            payload | dict(auth_token=token),
            timeout=self.config.timeout_seconds,
        )

    def check_identity(self, identity):
        if (
            identity.get("checkpoint_config_sha256") != self.config.base_config_sha256
            or identity.get("adapter_files_sha256", {}).get("adapter_model.safetensors")
            != self.config.adapter_sha256
        ):
            raise ValueError("Served model differs from the configured base and adapter identities")

    def health(self):
        value = self.call(dict(operation="health"))["status"]
        if (
            value.get("stage") != "ready"
            or self.config.policy not in value.get("policies", [])
            or value.get("decision_distribution", INDEPENDENT) != self.config.decision_distribution
            or value.get("temperature") != self.config.temperature
        ):
            raise ValueError("Configured attention policy is not ready on this service")
        identity = value.get("model_identities", {}).get(
            self.config.policy, value.get("model_identity", {})
        )
        self.check_identity(identity)
        return dict(ready=True, policy=self.config.policy, model_identity=identity)

    def score(self, observation):
        packet = protocol.Observation.model_validate(observation)
        result = self.call(
            dict(
                observation=packet.model_dump(),
                policy=self.config.policy,
                distribution=self.config.decision_distribution,
            )
        )
        if result.get("policy") != self.config.policy or not result.get("adapter_active"):
            raise ValueError("Attention response did not use the configured adapter")
        self.check_identity(result.get("model_identity", {}))
        prediction = result.get("prediction", {})
        if result.get("decision", {}).get("status") == "ok" and (
            prediction.get("temperature") != self.config.temperature
            or prediction.get("prompt_sha256") != result.get("input_prompt_sha256")
            or not prediction.get("prompt_sha256")
            or result.get("behavior") is not None
        ):
            raise ValueError("Attention response used different scoring or sampling settings")
        view = protocol.PackedView.model_validate(result["view"])
        decision = protocol.Decision.model_validate(result["decision"])
        expected = protocol.pack(
            packet, len, token_counter_id="client:characters", budget_tokens=1000000
        )
        if (
            view.text != expected.text
            or view.aliases != expected.aliases
            or view.question_aliases != expected.question_aliases
            or view.included_ids != expected.included_ids
            or view.omitted_ids != expected.omitted_ids
            or view.packet_id != packet.packet_id
            or decision.packet_id != packet.packet_id
            or view.sha256 != hashlib.sha256(view.text.encode()).hexdigest()
            or decision.model_view_sha256 != view.sha256
        ):
            raise ValueError("Attention response is not bound to the submitted public observation")
        return result


class AttentionObserver:
    """One in-flight request; durable at-most-once host-action attempts per incident.

    Shadow mode never calls the dispatch callback. A reservation precedes host
    dispatch, so a crash cannot silently repeat an uncertain action on restart.
    Such a reservation is an attempt, not proof that the host started an actor.
    """

    def __init__(self, root, config, *, client=None):
        self.root, self.config = Path(root), config
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "state.json"
        self.state = (
            json.loads(self.path.read_text())
            if self.path.exists()
            else dict(
                requests=0,
                records=0,
                attempts=[],
                last_attempt_at=0,
            )
        )
        previous = self.state.setdefault("configuration", config.model_dump())
        if previous != config.model_dump():
            raise ValueError("Attention configuration is immutable within a study")
        self.client = client or AttentionClient(config)
        self.admission_profile = config.admission_profile()
        config.verify_liveness(profile=self.admission_profile)
        self.state["admission_profile"] = asdict(self.admission_profile)
        self.gate = protocol.AdmissionGate(self.admission_profile)
        self.gate.dispatched.update(
            tuple(row["scope"]) for row in self.state["attempts"] if row["status"] == "dispatched"
        )
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.pending = None
        self.next_poll = 0.0
        self.closed = False
        self.save()

    def save(self):
        put(self.path, self.state)

    def tick(self, observe, dispatch):
        if self.closed or self.config.mode == "off":
            return
        now = time.time()
        if self.pending is not None:
            future, submitted = self.pending
            if not future.done():
                return
            self.pending = None
            record = dict(
                submitted=submitted.model_dump(),
                mode=self.config.mode,
                at=now,
                admission_profile=asdict(self.admission_profile),
            )
            try:
                result = future.result()
                current = protocol.Observation.model_validate(observe())
                view = protocol.PackedView.model_validate(result["view"])
                decision = protocol.Decision.model_validate(result["decision"])
                admission = self.gate.evaluate(
                    submitted, view, decision, current, now_ms=current.captured_ms
                )
                if reason := admission.get("reason"):
                    reasons = self.state.setdefault("admission_reasons", {})
                    reasons[reason] = reasons.get(reason, 0) + 1
                record.update(
                    result=result,
                    current=current.model_dump(),
                    admission=admission,
                    dispatched=False,
                )
                if admission["disposition"] == "admitted":
                    if self.config.mode == "shadow":
                        record["host_disposition"] = "shadow_only"
                    elif decision.support_kind != "none" or decision.action not in {
                        "wake_director",
                        "request_worker_help",
                    }:
                        record["host_disposition"] = "unsupported_host_action"
                    elif any(
                        row["scope"] == list(submitted.scope()) for row in self.state["attempts"]
                    ):
                        record["host_disposition"] = "incident_already_attempted"
                    elif len(self.state["attempts"]) >= self.config.maximum_alerts:
                        record["host_disposition"] = "alert_budget_exhausted"
                    elif now - self.state["last_attempt_at"] < self.config.cooldown_seconds:
                        record["host_disposition"] = "cooldown"
                    else:
                        attempt = dict(scope=list(submitted.scope()), at=now, status="reserved")
                        self.state["attempts"].append(attempt)
                        self.state["last_attempt_at"] = now
                        self.save()
                        started = bool(dispatch(decision.model_dump(), submitted.model_dump()))
                        if started:
                            self.gate.record_dispatch(submitted)
                        attempt["status"] = "dispatched" if started else "host_declined"
                        record.update(dispatched=started, host_disposition=attempt["status"])
                    dispositions = self.state.setdefault("host_dispositions", {})
                    disposition = record["host_disposition"]
                    dispositions[disposition] = dispositions.get(disposition, 0) + 1
            except Exception as error:
                # Endpoint errors must never become synthetic observe decisions;
                # persist the type without copying credentials from remote text.
                record["error"] = type(error).__name__
            self.state["records"] += 1
            put(self.root / f"decision-{self.state['records']:06d}.json", record)
            self.save()
        if now < self.next_poll or self.state["requests"] >= self.config.maximum_requests:
            return
        self.next_poll = now + self.config.poll_seconds
        packet = protocol.Observation.model_validate(observe())
        if packet.workflow_state == "complete":
            return
        self.state["requests"] += 1
        self.save()
        self.pending = self.executor.submit(self.client.score, packet), packet

    def close(self):
        self.closed = True
        if self.pending is not None:
            self.pending[0].cancel()
        self.executor.shutdown(wait=False, cancel_futures=True)
