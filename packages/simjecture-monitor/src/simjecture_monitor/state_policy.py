"""A public-state rules comparator that remembers successful diagnostic recovery."""

from __future__ import annotations

import json
import re

from .policy import RulesPolicy


def measured_lines(text):
    rows = []
    for line in str(text).splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def operation(body):
    command = str(body.get("command", ""))
    name = re.search(r"--name\s+([A-Za-z0-9_-]+)", command)
    if "experiment.py" in command and "analyze" in command and name:
        return name[1]
    return None


class StateAwareRules:
    """Use explicit active work and verified-format recovery, without case labels.

    A tool's numeric diagnostic output is still untrusted public context. These
    rules decide attention only and never approve science or repair authority.
    """

    def predict(self, packet):
        state = packet["state"]
        events = state["events"]
        host = state.get("host_state", {})
        active = any(
            host.get(key, False)
            for key in ["pending_explicit_help", "active_helpers", "authority_active"]
        )
        recovered = {}
        for index, event in enumerate(events):
            body = event["body"]
            name = operation(body)
            rows = measured_lines(body.get("aggregated_output", ""))
            if (
                name
                and body.get("exit_code") == 0
                and any(
                    "relative_field_error" in r and "relative_charge_residual" in r for r in rows
                )
            ):
                recovered[name] = index
        filtered = []
        for index, event in enumerate(events):
            body = event["body"]
            name = operation(body)
            if name and index < recovered.get(name, -1) and body.get("exit_code") not in (None, 0):
                continue
            filtered.append(event)
        candidate = RulesPolicy().predict(dict(packet, state=dict(state, events=filtered)))
        reason = "public failure rules after same-operation recovery filtering"
        if active:
            candidate["choice"] = "defer"
            reason = "Explicit assistance is already active"
        candidate.update(
            policy="state-aware-rules",
            reason=reason,
            removed_event_ids=[e["id"] for e in events if e not in filtered],
        )
        return candidate
