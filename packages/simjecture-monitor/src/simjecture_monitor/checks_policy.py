"""Generic operations plus the pre-existing published-scientific-check rule.

This restores the generic failed-check route already present in RulesPolicy
before these fixtures existed. It uses public tool fields, not hidden case truth.
"""

from __future__ import annotations

from .generic_policy import GenericOperationalRules


class ChecksAwareRules(GenericOperationalRules):
    def predict(self, packet):
        result = super().predict(packet)
        host = packet["state"].get("host_state", {})
        busy = any(
            host.get(key)
            for key in [
                "authority_active",
                "director_active",
                "pending_explicit_help",
                "active_helpers",
            ]
        )
        complete = host.get("telemetry", {}).get("workflow_complete")
        if result["choice"] == "defer" and not busy and not complete:
            rows = host.get("public_artifacts", {}).get("diagnostic_rows", [])
            if any(row.get("original_checks_passed") is False for row in rows):
                result.update(choice="wake_director", reason="A published scientific check failed")
        result["policy"] = "generic-operations-and-checks-v1"
        return result
