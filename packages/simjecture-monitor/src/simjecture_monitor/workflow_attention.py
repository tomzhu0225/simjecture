"""Bridge legacy public scientific-workflow records to the versioned attention contract.

No hidden fixture identity or verifier outcome is accepted. This adapter is for
the retained streaming experiment interface, not a universal scientific parser.
"""

from __future__ import annotations

import hashlib
import json
import math

from . import attention_contract as core
from . import attention_support as protocol


def digest(value):
    # Legacy tool records can contain nonfinite numeric spellings. Preserve their
    # source identity; typed measurements below explicitly mark them invalid.
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def observation(
    raw,
    *,
    subject_id,
    operation_id,
    incident_id,
    clock_id,
    captured_ms,
    sequence,
    state_revision,
    wall_time,
):
    """Use host clock/identity and public raw records, retaining complete required content."""
    state = raw["state"]
    host = state["host_state"]
    telemetry = host.get("telemetry", {})
    public = host.get("public_artifacts", {})
    plan = public.get("execution_plan", {})
    evidence = []

    def append(role, kind, payload, *, origin="host", measurements=(), age_ms=0):
        text = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
        source_hash = digest(payload)
        for part, start in enumerate(range(0, max(1, len(text)), 1600)):
            evidence.append(
                core.Evidence(
                    id=f"{role}-{part}",
                    source=role,
                    source_role=role,
                    source_sha256=source_hash,
                    kind=kind,
                    age_ms=age_ms,
                    origin=origin,
                    content=text[start : start + 1600],
                    measurements=list(measurements) if part == 0 else [],
                    required=True,
                    excerpted="[excerpt]" in text,
                )
            )

    def measurement(name, value, unit="1"):
        valid = (
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
        )
        return core.Measurement(
            name=name,
            value=float(value) if valid else None,
            unit=unit,
            validity="measured" if valid else "missing" if value is None else "invalid",
        )

    append("declared_task", "expectation", state["task"], origin="operator")
    append("telemetry", "receipt", telemetry)
    append("process", "receipt", {k: public.get(k) for k in ["process_alive", "process_exit_code"]})
    append("execution_plan", "expectation", plan)
    append("analysis_options", "tool_result", public.get("analysis_options", {}), origin="worker")
    progress = public.get("progress", {})
    append(
        "progress",
        "progress",
        progress,
        origin="instrument",
        measurements=[
            measurement(key, progress.get(key))
            for key in ["loss", "calibration_value", "target"]
            if key in progress
        ],
    )
    append("progress_history", "progress", host.get("progress_history", []), origin="instrument")
    for index, row in enumerate(public.get("diagnostic_rows", [])):
        values = []
        for key, name, unit in [
            ("stored_peak_electric_field", "saved_electric_field_peak", "V/m"),
            ("peak_electric_field_V_per_m", "reported_electric_field_peak", "V/m"),
            ("relative_field_error", "relative_field_error", "1"),
            ("relative_charge_residual", "relative_charge_residual", "1"),
        ]:
            if key in row:
                values.append(measurement(name, row[key], unit))
        append(f"diagnostic_{index}", "measurement", row, origin="instrument", measurements=values)
    for index, event in enumerate(state.get("events", [])):
        # Avoid literal duplicate structured records; distinct log excerpts stay visible.
        if event.get("body") == public:
            continue
        observed_at = event.get("observed_at", wall_time)
        age = max(0, round((wall_time - observed_at) * 1000))
        append(
            f"worker_event_{index}",
            "tool_result",
            event.get("body", event),
            origin="worker",
            age_ms=age,
        )
    quiet_until = plan.get("quiet_until")
    if quiet_until is None:
        quiet, remaining, after = "unknown", None, None
    elif wall_time < quiet_until:
        quiet, remaining, after = "active", max(1, round((quiet_until - wall_time) * 1000)), None
    else:
        quiet, remaining, after = "expired", 0, max(0, round((wall_time - quiet_until) * 1000))
    assistance = (
        "active"
        if any(host.get(k) for k in ["authority_active", "director_active", "active_helpers"])
        else "pending"
        if host.get("pending_explicit_help")
        else "none"
    )
    return protocol.Observation(
        schema_version=protocol.VERSION,
        packet_id=f"packet-{sequence}-{digest(raw)[:16]}",
        subject_id=subject_id,
        operation_id=operation_id,
        incident_id=incident_id,
        clock_id=clock_id,
        captured_ms=captured_ms,
        sequence=sequence,
        state_revision=state_revision,
        task=(
            "Monitor the declared scientific workflow "
            "while its worker waits for public diagnostics."
        ),
        phase=str(progress.get("phase", "awaiting_diagnostics")),
        scientific_contract=[
            "Apply the complete declared_task record and preserve original scientific criteria.",
            "Saved and reported electric-field peaks denote the same quantity in V/m.",
            "An accurately reported failed physical check is a valid scientific outcome.",
            "The diagnostic aggregation goal is absolute calibration error below 1e-3.",
            "A protected component can only be referred to an independent repair judge.",
        ],
        worker_state="parked" if host.get("worker_parked") else "active",
        workflow_state="complete" if telemetry.get("workflow_complete") else "running",
        assistance=assistance,
        timing=core.Timing(
            phase_elapsed_ms=max(0, round((wall_time - plan["started_at"]) * 1000))
            if plan.get("started_at") is not None
            else None,
            progress_age_ms=round(telemetry["no_new_output_seconds"] * 1000)
            if telemetry.get("no_new_output_seconds") is not None
            else None,
            heartbeat_age_ms=0 if public.get("process_alive") else None,
            quiet_state=quiet,
            quiet_remaining_ms=remaining,
            since_quiet_end_ms=after,
            retries_remaining=telemetry.get("retry_budget_remaining"),
            budget_remaining_ms=round(host["remaining_seconds"] * 1000)
            if host.get("remaining_seconds") is not None
            else None,
        ),
        evidence=evidence,
        questions=[],
        retrieval_history=[],
        retrieval_history_complete=True,
        missing_channels=[] if telemetry else ["workflow_telemetry"],
    )


def public_record(packet, role):
    records = [e for e in packet.evidence if e.source_role == role]
    if not records:
        return None
    return json.loads("".join(e.content for e in records))


class ScientificConsistencyRules:
    """Strong public-data comparator, frozen before new scientific test collection.

    Extends operational monitoring with units, current provenance and calibrated
    progress checks. It never looks up fixture names or private expected actions.
    """

    UNITS = {
        "V/m": ("field", 1.0),
        "kV/m": ("field", 1e3),
        "MV/m": ("field", 1e6),
        "T": ("magnetic", 1.0),
        "mT": ("magnetic", 1e-3),
        "Pa": ("pressure", 1.0),
        "kPa": ("pressure", 1e3),
        "Hz": ("frequency", 1.0),
        "MHz": ("frequency", 1e6),
        "J": ("energy", 1.0),
        "mJ": ("energy", 1e-3),
        "m/s": ("speed", 1.0),
        "km/s": ("speed", 1e3),
    }

    def predict(self, packet, view):
        aliases = {value: key for key, value in view.aliases.items()}

        def choice(action="observe", basis="unspecified", refs=()):
            return protocol.Choice(
                action=action,
                support_kind="none",
                question_ref=None,
                basis=basis,
                evidence=[aliases[ref] for ref in refs],
            )

        if (
            packet.assistance in {"pending", "active", "returned_required"}
            or packet.workflow_state == "complete"
        ):
            return choice()
        if packet.missing_channels or packet.assistance == "unknown":
            return choice("recheck", "missing")
        telemetry = public_record(packet, "telemetry") or {}
        for e in packet.evidence:
            if any(m.validity != "measured" for m in e.measurements):
                return choice("recheck", "missing", [e.id])
            values = {m.name: m for m in e.measurements if m.validity == "measured"}
            for name, saved in values.items():
                if not name.startswith("saved_"):
                    continue
                reported = values.get("reported_" + name.removeprefix("saved_"))
                if reported is None:
                    continue
                first, second = self.UNITS.get(saved.unit), self.UNITS.get(reported.unit)
                if not first or not second or first[0] != second[0]:
                    return choice("recheck", "measurement", [e.id])
                if not math.isclose(
                    saved.value * first[1], reported.value * second[1], rel_tol=1e-6, abs_tol=1e-12
                ):
                    return choice("wake_director", "measurement", [e.id])
        for row in telemetry.get("source_records", []):
            requested, observed = row.get("request", {}), row.get("source", {})
            common = set(requested) & set(observed)
            if any(requested[k] != observed[k] for k in common):
                return choice(
                    "request_repair_judge" if row.get("owner") == "protected" else "wake_director",
                    "source",
                    [e.id for e in packet.evidence if e.source_role == "telemetry"][:1],
                )
        refs = [e.id for e in packet.evidence if e.source_role in {"telemetry", "progress"}][:2]
        if telemetry.get("terminal_exit_code") not in (None, 0):
            return choice("request_worker_help", "source", refs)
        if packet.timing.quiet_state == "active":
            return choice()
        if (
            telemetry.get("consecutive_tool_failures", 0) >= 3
            and telemetry.get("retry_budget_remaining", 0) <= 0
        ):
            return choice("request_worker_help", "repetition", refs)
        progress = public_record(packet, "progress") or {}
        loss = progress.get("loss")
        goal_met = (
            isinstance(loss, (int, float))
            and not isinstance(loss, bool)
            and math.isfinite(loss)
            and loss < 1e-3
        )
        if not goal_met:
            silence = packet.timing.unexplained_silence_ms()
            if silence is not None and silence >= 30000:
                return choice("request_worker_help", "silence", refs)
            recent_window = packet.timing.since_quiet_end_ms
            if (
                (recent_window is None or recent_window >= 18000)
                and telemetry.get("repeated_output_count", 0) >= 4
                and telemetry.get("repeated_output_span_seconds", 0) >= 18
            ):
                return choice("request_worker_help", "repetition", refs)
        return choice()
