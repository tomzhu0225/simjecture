"""Frozen generic operational comparator for raw workflow observations.

No test-family names or injected-fault labels enter this policy. Thresholds and
schema are fixed before held-out fixture execution.
"""

from __future__ import annotations


class GenericOperationalRules:
    def predict(self, packet):
        host = packet["state"].get("host_state", {})
        telemetry = host.get("telemetry", {})
        action, reason = "defer", "No generic operational threshold reached"
        busy = (
            host.get("authority_active")
            or host.get("pending_explicit_help", 0)
            or host.get("active_helpers", 0)
            or host.get("director_active")
        )
        if busy:
            reason = "Assistance is already active"
        elif telemetry.get("workflow_complete"):
            reason = "Workflow reports completion; worker can inspect final results"
        elif telemetry.get("terminal_exit_code") not in (None, 0):
            action, reason = "request_worker_help", "A supervised process exited unsuccessfully"
        elif (
            telemetry.get("consecutive_tool_failures", 0) >= 3
            and telemetry.get("retry_budget_remaining", 0) <= 0
        ):
            action, reason = "request_worker_help", "Three unsuccessful tool executions"
        elif telemetry.get("source_records"):
            for row in telemetry["source_records"]:
                requested, observed = row.get("request", {}), row.get("source", {})
                common = set(requested) & set(observed)
                if common and any(requested[k] != observed[k] for k in common):
                    action = (
                        "request_repair_judge"
                        if row.get("owner") == "protected"
                        else "wake_director"
                    )
                    reason = "Published request/source identity fields disagree"
                    break
        if action == "defer" and not busy and not telemetry.get("workflow_complete"):
            quiet = telemetry.get("quiet_remaining_seconds", 0) > 0
            if not quiet and telemetry.get("no_new_output_seconds", 0) >= 30:
                action, reason = "request_worker_help", "No new output for thirty seconds"
            elif (
                not quiet
                and telemetry.get("repeated_output_count", 0) >= 4
                and telemetry.get("repeated_output_span_seconds", 0) >= 18
            ):
                action, reason = "request_worker_help", "Repeated output without advancement"
        return dict(
            choice=action,
            policy="generic-operational-v1",
            reason=reason,
            packet_sha256=packet["packet_sha256"],
            forward_seconds=0,
        )
