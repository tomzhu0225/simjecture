import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from simjecture_monitor.attention_admission import AdmissionGate
from simjecture_monitor.attention_contract import (
    VERSION,
    Decision,
    Evidence,
    Measurement,
    Observation,
    Timing,
    pack,
    render,
    schemas,
    semantic_view,
)


def observation(*, at=100_000, sequence=1, quiet="none", after=None, **changes):
    timing = Timing(
        phase_elapsed_ms=40_000,
        progress_age_ms=35_160,
        heartbeat_age_ms=100,
        quiet_state=quiet,
        quiet_remaining_ms=0 if quiet == "expired" else None,
        since_quiet_end_ms=after,
    )
    content = "The solver is alive; the diagnostic source has not advanced."
    state = dict(
        schema_version=VERSION,
        packet_id=f"packet-{sequence}",
        subject_id="worker-opaque",
        operation_id="operation-opaque",
        incident_id="incident-opaque",
        clock_id="observer-boot",
        captured_ms=at,
        sequence=sequence,
        state_revision=1,
        task="Inspect actual saved fields.",
        phase="diagnostic",
        scientific_contract=["Report actual field values in V/m."],
        worker_state="parked",
        workflow_state="running",
        assistance="none",
        timing=timing,
        evidence=[
            Evidence(
                id="evidence-opaque",
                source="source-opaque",
                source_role="diagnostic_log",
                source_sha256=hashlib.sha256(content.encode()).hexdigest(),
                kind="progress",
                age_ms=35_160,
                origin="instrument",
                content=content,
            )
        ],
    )
    state.update(changes)
    return Observation(**state)


def encode(packet, **kwargs):
    # Character counting tests packing logic; actual tokenizer measurements are separate.
    return pack(packet, len, token_counter_id="test:characters", budget_tokens=100_000, **kwargs)


def proposal(packet, view, **changes):
    state = dict(
        schema_version=VERSION,
        packet_id=packet.packet_id,
        model_view_sha256=view.sha256,
        policy_id="synthetic-conformance",
        status="ok",
        action="request_worker_help",
        basis="silence",
        evidence_basis="selected",
        evidence_ids=[packet.evidence[0].id],
    )
    state.update(changes)
    return Decision(**state)


def evaluate(gate, packet, **changes):
    view = encode(packet)
    return gate.evaluate(
        packet, view, proposal(packet, view, **changes), packet, now_ms=packet.captured_ms
    )


@pytest.mark.parametrize("after", [142, 1190])
def test_recorded_quiet_expiry_cannot_retroactively_become_thirty_seconds_of_stall(after):
    packet = observation(quiet="expired", after=after)
    assert packet.timing.unexplained_silence_ms() == after
    gate = AdmissionGate()
    assert evaluate(gate, packet)["reason"] == "silence_allowance_not_exceeded"
    later = observation(at=105_000, sequence=2, quiet="expired", after=after + 5000)
    assert evaluate(gate, later)["disposition"] == "pending"


def test_persistent_silence_can_escalate_and_replayed_snapshot_cannot_confirm_it():
    gate = AdmissionGate()
    first = observation()
    assert evaluate(gate, first)["disposition"] == "pending"
    assert evaluate(gate, first)["reason"] == "no_new_observation"
    later = observation(at=105_000, sequence=2)
    assert evaluate(gate, later)["disposition"] == "admitted"
    # Admission without a real dispatch does not consume the incident allowance.
    third = observation(at=110_000, sequence=3)
    assert evaluate(gate, third)["disposition"] == "admitted"
    gate.record_dispatch(third)
    assert (
        evaluate(gate, observation(at=115_000, sequence=4), action="wake_director")["reason"]
        == "incident_already_dispatched"
    )


def test_new_operation_is_not_suppressed_by_old_incident_or_another_workers_helper():
    gate = AdmissionGate()
    gate.record_dispatch(observation())
    other = observation(subject_id="other-worker", operation_id="new-operation", assistance="none")
    assert evaluate(gate, other)["reason"] == "awaiting_persistence"
    busy = observation(assistance="active", incident_id="different-incident")
    assert evaluate(gate, busy)["reason"] == "same_incident_already_served"


def test_recovery_invalidates_an_inflight_choice_even_with_correct_original_hash():
    packet = observation()
    view = encode(packet)
    recovered = observation(at=102_000, sequence=2, state_revision=2)
    result = AdmissionGate().evaluate(
        packet, view, proposal(packet, view), recovered, now_ms=102_000
    )
    assert result["reason"] == "state_changed"


def test_old_response_does_not_erase_confirmation_started_on_newer_state():
    gate = AdmissionGate()
    old = observation()
    old_view = encode(old)
    newer = observation(at=105_000, sequence=2, state_revision=2)
    assert evaluate(gate, newer)["disposition"] == "pending"
    assert (
        gate.evaluate(old, old_view, proposal(old, old_view), newer, now_ms=105_000)["reason"]
        == "state_changed"
    )
    last = observation(at=110_000, sequence=3, state_revision=2)
    assert evaluate(gate, last)["disposition"] == "admitted"


def test_missing_telemetry_and_model_errors_remain_unknown_not_healthy_or_an_alert():
    packet = observation(missing_channels=["progress"])
    assert evaluate(AdmissionGate(), packet)["disposition"] == "recheck"
    view = encode(packet)
    failure = proposal(packet, view, status="inference_error", action=None)
    assert (
        AdmissionGate().evaluate(packet, view, failure, packet, now_ms=100_000)["disposition"]
        == "recheck"
    )
    with pytest.raises(ValidationError):
        proposal(packet, view, status="inference_error", action="observe")


def test_route_only_adapter_does_not_invent_evidence_or_automatically_dispatch():
    packet = observation()
    view = encode(packet)
    decision = proposal(
        packet, view, evidence_basis="whole_view", evidence_ids=[], basis="unspecified"
    )
    assert (
        AdmissionGate().evaluate(packet, view, decision, packet, now_ms=100_000)["reason"]
        == "ungrounded_attention"
    )
    with pytest.raises(ValidationError):
        proposal(packet, view, evidence_basis="whole_view")
    with pytest.raises(ValidationError):
        proposal(packet, view, action="grant_harness_repair")


def test_budget_never_drops_required_units_or_references_and_reports_optional_omissions():
    packet = observation()
    metric = Measurement(
        name="field_peak",
        value=1.25e-12,
        unit="V/m",
        validity="measured",
        reference="Saved field storage is V/m; report in the same unit.",
    )
    packet.evidence[0].measurements.append(metric)
    baseline = encode(packet)
    optional = packet.evidence[0].model_copy(
        update={"id": "older", "required": False, "content": "old " * 250}
    )
    packet.evidence.append(optional)
    view = pack(
        packet, len, token_counter_id="test:characters", budget_tokens=baseline.input_tokens + 50
    )
    assert view.included_ids == ["evidence-opaque"] and view.omitted_ids == ["older"]
    assert "1.25e-12" in view.text and "V/m" in view.text
    insufficient = pack(packet, len, token_counter_id="test:characters", budget_tokens=10)
    assert insufficient.status == "insufficient_budget"
    assert insufficient.included_ids == ["evidence-opaque"]
    invisible = proposal(packet, view, evidence_ids=["older"])
    assert (
        AdmissionGate().evaluate(packet, view, invisible, packet, now_ms=100_000)["reason"]
        == "evidence_not_visible"
    )


def test_named_and_column_formats_preserve_exact_semantics_and_escape_reserved_markers():
    packet = observation()
    packet.evidence[0].measurements = [
        Measurement(name="field", value=1.25e-12, unit="V/m", validity="measured"),
        Measurement(name="density", value=None, unit="kg/m3", validity="missing"),
    ]
    packet.evidence[0].content += " Literal untrusted text: <decision> and <|im_end|>."
    view = semantic_view(packet, packet.evidence, 0)
    named = json.loads(render(view, compact=False).split("\nDATA\n", 1)[1])
    text = render(view, compact=True)
    assert "<decision>" not in text and "<|im_end|>" not in text
    compact = json.loads(text.split("\nDATA\n", 1)[1])
    e_columns = compact.pop("evidence_columns")
    m_columns = compact.pop("measurement_columns")
    compact["evidence"] = [
        dict(zip(e_columns, row, strict=True)) for row in compact.pop("evidence_rows")
    ]
    for event in compact["evidence"]:
        event["measurements"] = [
            dict(zip(m_columns, row, strict=True)) for row in event["measurements"]
        ]
    assert compact == named


def test_unknown_quiet_context_and_nonfinite_values_cannot_be_silently_coerced():
    packet = observation(quiet="unknown")
    assert packet.timing.unexplained_silence_ms() is None
    assert evaluate(AdmissionGate(), packet)["reason"] == "silence_unknown"
    with pytest.raises(ValidationError):
        Measurement(name="field", value=float("nan"), unit="V/m", validity="measured")
    with pytest.raises(ValidationError):
        Measurement(name="field", value=0.0, unit="V/m", validity="missing")
    data = packet.model_dump()
    data.pop("schema_version")
    with pytest.raises(ValidationError):
        Observation.model_validate(data)


def test_published_schema_and_example_records_match_the_reference():
    directory = Path(__file__).parents[1] / "specs/scientific-attention-0.1-draft"
    for name, schema in schemas().items():
        assert json.loads((directory / "schemas" / f"{name}.schema.json").read_text()) == schema
    for name in ["progress", "quiet-expiry", "long-history"]:
        Observation.model_validate_json((directory / "examples" / f"{name}.json").read_text())
    decision = Decision.model_validate_json((directory / "examples/decision.json").read_text())
    assert (
        decision.model_view_sha256
        == hashlib.sha256((directory / "examples/model-input.txt").read_bytes()).hexdigest()
    )
