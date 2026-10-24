"""A small action menu plus essential deterministic comparators."""

from __future__ import annotations

import time
from collections import Counter

ACTIONS = {
    "defer": "Continue observing. Progress is plausible; no new intervention is warranted.",
    "request_worker_help": (
        "Repeated unsuccessful worker attempts or an unreported blocker justify asking the "
        "director to arrange bounded assistance."
    ),
    "wake_director": (
        "A simulation, diagnostic, conflicting assumption or research-requirement anomaly "
        "needs the director's attention now."
    ),
    "request_repair_judge": (
        "Evidence points specifically to a broken orchestration/harness component that the "
        "worker and director lack permission to repair. Request independent diagnosis and a "
        "scoped authority decision; grant no permission yourself."
    ),
}


class RulesPolicy:
    "Public error repetition, explicit fault signatures and required-check failures."

    def predict(self, packet):
        events = packet["state"]["events"]
        bodies = [r["body"] for r in events]
        failures = [
            r
            for r in bodies
            if r.get("type") == "command_execution" and r.get("exit_code") not in (None, 0)
        ]
        repeated = Counter(r.get("command", "") for r in failures)
        outputs = "\n".join(str(r.get("aggregated_output", "")) for r in bodies[-4:])
        if any(code in outputs for code in ("HARNESS_CONTRACT_ERROR", "HarnessProtocolError")):
            action = "request_repair_judge"
        elif repeated and max(repeated.values()) >= 3:
            action = "request_worker_help"
        elif any(
            code in outputs
            for code in (
                '"required_check_passed": false',
                '"nonfinite": true',
                '"acceptance_passed": false',
                '"original_checks_passed": false',
            )
        ):
            action = "wake_director"
        else:
            action = "defer"
        return dict(
            choice=action,
            packet_sha256=packet["packet_sha256"],
            policy="rules",
            forward_seconds=0,
            evidence=[r["id"] for r in events[-4:]],
        )


class PeriodicPolicy:
    def __init__(self, interval=60):
        self.interval = interval
        self.last = time.monotonic()

    def predict(self, packet):
        now = time.monotonic()
        choice = "wake_director" if now - self.last >= self.interval else "defer"
        if choice != "defer":
            self.last = now
        return dict(
            choice=choice, packet_sha256=packet["packet_sha256"], policy="periodic", evidence=[]
        )


class AlertGate:
    "Reject stale choices, suppress duplicate incidents and retain acknowledgements."

    def __init__(self, cooldown=60):
        self.cooldown = cooldown
        self.last = {}
        self.acknowledged = set()

    def defer_before_dispatch(self, alert):
        """Release an accepted alert that the host deferred without dispatch.

        Do not erase a newer alert's cooldown when an older reservation is
        released. This does not acknowledge, execute or grant the alert.
        """
        key = (alert["subject"], alert["action"])
        if self.last.get(key) == alert["created_at"]:
            self.last.pop(key)
        self.acknowledged.discard((*key, alert["packet_sha256"]))

    def accept(self, packet, decision, *, now=None):
        if decision.get("packet_sha256") != packet["packet_sha256"]:
            raise ValueError("Stale monitor response")
        action = decision.get("choice")
        if action not in ACTIONS:
            raise ValueError("Unknown monitor action")
        if action == "defer":
            return None
        now = time.time() if now is None else now
        subject = packet["state"]["subject"]
        key = (subject, action)
        if now - self.last.get(key, float("-inf")) < self.cooldown:
            return None
        fingerprint = (subject, action, packet["packet_sha256"])
        if fingerprint in self.acknowledged:
            return None
        self.last[key] = now
        self.acknowledged.add(fingerprint)
        return dict(
            origin="coprocessor",
            subject=subject,
            action=action,
            packet_sha256=packet["packet_sha256"],
            evidence_event_ids=[r["id"] for r in packet["state"]["events"]],
            created_at=now,
            authority="Attention request only; no repair permission or scientific approval",
        )
