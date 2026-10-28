"""Draft reference admission policy, with no dispatch or production integration.

These gates remove identifiable stale/duplicate/premature requests. They do not
establish an empirical false-alert rate or infer that a model's evidence is true.
Durable dispatch transactions and restart recovery belong to the host adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .attention_contract import Decision, Observation, PackedView


@dataclass(frozen=True)
class AdmissionProfile:
    # These are illustrative conformance settings, not fitted deployment optima.
    maximum_age_ms: int = 15_000
    minimum_silence_ms: int = 30_000
    minimum_confirmations: int = 2
    persistence_ms: int = 5_000
    maximum_gap_ms: int = 10_000
    require_grounding: bool = True

    def __post_init__(self):
        if (
            min(
                self.maximum_age_ms,
                self.minimum_silence_ms,
                self.persistence_ms,
                self.maximum_gap_ms,
            )
            <= 0
        ):
            raise ValueError("Admission durations must be positive")
        if self.minimum_confirmations < 2:
            raise ValueError("This reference profile requires at least two distinct snapshots")


class AdmissionGate:
    def __init__(self, profile=None):
        self.profile = profile or AdmissionProfile()
        self.pending = {}
        self.dispatched = set()

    def evaluate(
        self,
        submitted: Observation,
        view: PackedView,
        decision: Decision,
        current: Observation,
        *,
        now_ms: int,
    ):
        key = submitted.scope()

        def result(disposition, reason, *, reset=True):
            pending = self.pending.get(key)
            if (
                reset
                and pending
                and pending["clock_id"] == submitted.clock_id
                and pending["sequence"] <= submitted.sequence
            ):
                self.pending.pop(key, None)
            return dict(
                disposition=disposition,
                reason=reason,
                proposed_action=decision.action,
                packet_id=submitted.packet_id,
                current_packet_id=current.packet_id,
                incident_id=submitted.incident_id,
                authority="attention_only",
            )

        if (
            decision.packet_id != submitted.packet_id
            or view.packet_id != submitted.packet_id
            or decision.model_view_sha256 != view.sha256
            or sha256(view.text.encode()).hexdigest() != view.sha256
        ):
            return result("rejected", "input_binding_mismatch")
        if submitted.clock_id != current.clock_id or now_ms < max(
            submitted.captured_ms, current.captured_ms
        ):
            return result("rejected", "incomparable_clock")
        if now_ms - submitted.captured_ms > self.profile.maximum_age_ms:
            return result("recheck", "stale_response")
        if key != current.scope() or current.state_revision != submitted.state_revision:
            return result("recheck", "state_changed")
        if current.sequence < submitted.sequence or current.captured_ms < submitted.captured_ms:
            return result("rejected", "observation_order_reversed")
        if view.status != "ready" or decision.status != "ok":
            return result("recheck", "input_or_inference_failure")
        known = {e.id for e in submitted.evidence}
        if any(ref not in known for ref in view.included_ids) or any(
            ref not in view.included_ids for ref in decision.evidence_ids
        ):
            return result("rejected", "evidence_not_visible")
        if decision.action in {"observe", "recheck"}:
            return result(decision.action, "policy_choice")
        if current.workflow_state == "complete":
            return result("suppressed", "workflow_closed")
        if key in self.dispatched:
            return result("suppressed", "incident_already_dispatched")
        if current.assistance in {"pending", "active", "returned_required"}:
            return result("suppressed", "same_incident_already_served")
        if (
            current.assistance == "unknown"
            or current.workflow_state == "unknown"
            or current.missing_channels
        ):
            return result("recheck", "required_state_unknown")
        if self.profile.require_grounding and (
            decision.evidence_basis != "selected" or decision.basis == "unspecified"
        ):
            return result("recheck", "ungrounded_attention")
        if decision.basis == "silence":
            silence = current.timing.unexplained_silence_ms()
            if silence is None:
                return result("recheck", "silence_unknown")
            if silence < self.profile.minimum_silence_ms:
                return result("pending", "silence_allowance_not_exceeded")
        previous = self.pending.get(key)
        # Repeated delivery of one snapshot must never manufacture persistence.
        if (
            previous
            and previous["clock_id"] == current.clock_id
            and (
                submitted.sequence <= previous["sequence"]
                or submitted.captured_ms <= previous["last_ms"]
            )
        ):
            return result("pending", "no_new_observation", reset=False)
        if (
            previous is None
            or previous["action"] != decision.action
            or previous["basis"] != decision.basis
            or previous["clock_id"] != current.clock_id
            or submitted.captured_ms - previous["last_ms"] > self.profile.maximum_gap_ms
        ):
            previous = dict(
                action=decision.action,
                basis=decision.basis,
                first_ms=submitted.captured_ms,
                count=0,
            )
        previous.update(
            clock_id=current.clock_id,
            count=previous["count"] + 1,
            sequence=submitted.sequence,
            last_ms=submitted.captured_ms,
        )
        self.pending[key] = previous
        persisted = submitted.captured_ms - previous["first_ms"] >= self.profile.persistence_ms
        if previous["count"] < self.profile.minimum_confirmations or not persisted:
            return result("pending", "awaiting_persistence", reset=False)
        return result("admitted", "fresh_grounded_persistent_request", reset=False)

    def record_dispatch(self, packet: Observation):
        """Call only after the host records an actual dispatch, never on admission.

        This in-memory conformance implementation is not a durable transaction.
        Production adapters must persist and serialize incident transitions.
        """
        self.dispatched.add(packet.scope())
        self.pending.pop(packet.scope(), None)
