import hashlib
import json

from simjecture_monitor import attention_support as protocol
from simjecture_monitor.workflow_attention import (
    ScientificConsistencyRules,
    observation,
    public_record,
)


def raw():
    return dict(
        state=dict(
            task="Report actual saved electric fields in V/m; preserve original checks.",
            events=[],
            host_state=dict(
                worker_parked=True,
                remaining_seconds=500,
                telemetry=dict(
                    workflow_complete=False,
                    terminal_exit_code=None,
                    no_new_output_seconds=60.0,
                    quiet_remaining_seconds=0.0,
                    retry_budget_remaining=0,
                    consecutive_tool_failures=0,
                    repeated_output_count=4,
                    repeated_output_span_seconds=24.0,
                    source_records=[dict(request={"run": "current"}, source={"run": "current"})],
                ),
                public_artifacts=dict(
                    process_alive=True,
                    process_exit_code=None,
                    execution_plan=dict(started_at=100.0, quiet_until=150.0),
                    analysis_options={},
                    progress=dict(
                        phase="aggregation", loss=0.0001, calibration_value=0.8, target=0.8
                    ),
                    diagnostic_rows=[
                        dict(
                            name="current",
                            stored_peak_electric_field=1.5e9,
                            peak_electric_field_V_per_m=1.5e9,
                            relative_field_error=0.01,
                            relative_charge_residual=1e-8,
                            original_checks_passed=False,
                        )
                    ],
                ),
                progress_history=[],
            ),
        )
    )


def packet(value):
    return observation(
        value,
        subject_id="worker",
        operation_id="job",
        incident_id="incident",
        clock_id="observer",
        captured_ms=100000,
        sequence=1,
        state_revision=1,
        wall_time=200.0,
    )


def predict(value):
    observed = packet(value)
    view = protocol.pack(observed, len, token_counter_id="test:characters", budget_tokens=100000)
    choice = ScientificConsistencyRules().predict(observed, view)
    return choice, protocol.bind_choice(observed, view, choice, policy_id="rules-test")


def test_a_valid_negative_control_and_completed_calibration_do_not_trigger_expert_attention():
    value = raw()
    choice, _ = predict(value)
    assert choice.action == "observe"
    # This is a stalled unfinished iteration, rather than a completed small residual.
    value["state"]["host_state"]["public_artifacts"]["progress"]["loss"] = 0.5
    assert predict(value)[0].action == "request_worker_help"


def test_quiet_expiry_does_not_reuse_old_silence_or_old_repetitions():
    value = raw()
    host = value["state"]["host_state"]
    host["public_artifacts"]["progress"]["loss"] = 0.5
    host["public_artifacts"]["execution_plan"]["quiet_until"] = 199.858
    observed = packet(value)
    assert observed.timing.unexplained_silence_ms() == 142
    assert predict(value)[0].action == "observe"


def test_rule_uses_public_unit_consistency_and_cites_the_actual_visible_record():
    value = raw()
    value["state"]["host_state"]["public_artifacts"]["diagnostic_rows"][0][
        "peak_electric_field_V_per_m"
    ] *= 1000
    choice, decision = predict(value)
    assert choice.action == "wake_director"
    assert decision.evidence_ids == ["diagnostic_0-0"]


def test_old_worker_output_is_aged_and_long_public_records_are_not_silently_clipped():
    value = raw()
    text = "An earlier source read failed. " + ("Public log detail. " * 230)
    value["state"]["events"] = [dict(observed_at=180.0, body=dict(output=text))]
    observed = packet(value)
    records = [e for e in observed.evidence if e.source_role == "worker_event_0"]
    assert len(records) > 1 and all(e.age_ms == 20000 for e in records)
    assert public_record(observed, "worker_event_0") == dict(output=text)
    expected = hashlib.sha256(json.dumps(dict(output=text), sort_keys=True).encode()).hexdigest()
    assert all(e.source_sha256 == expected for e in records)
    assert predict(value)[0].action == "observe"


def test_nonfinite_measurements_remain_invalid_and_current_assistance_suppresses_duplicates():
    value = raw()
    value["state"]["host_state"]["public_artifacts"]["diagnostic_rows"][0][
        "stored_peak_electric_field"
    ] = float("nan")
    observed = packet(value)
    record = next(e for e in observed.evidence if e.id == "diagnostic_0-0")
    assert record.measurements[0].value is None and record.measurements[0].validity == "invalid"
    assert predict(value)[0].action == "recheck"
    value["state"]["host_state"]["active_helpers"] = 1
    assert predict(value)[0].action == "observe"


def test_sustained_divergence_is_detected_without_treating_a_single_overshoot_as_failure():
    value = raw()
    host = value["state"]["host_state"]
    host["telemetry"].update(
        no_new_output_seconds=1.0, repeated_output_count=1, repeated_output_span_seconds=0.0
    )
    host["public_artifacts"]["progress"]["loss"] = 0.4
    host["progress_history"] = [
        dict(phase="aggregation", loss=loss) for loss in [0.2, 0.25, 0.32, 0.4]
    ]
    choice, decision = predict(value)
    assert choice.action == "request_worker_help"
    assert decision.evidence_ids == ["progress_history-0"]
    host["progress_history"][1]["loss"] = 0.5
    assert predict(value)[0].action == "observe"
    host["public_artifacts"]["execution_plan"]["quiet_until"] = 195.0
    host["progress_history"][1]["loss"] = 0.25
    assert predict(value)[0].action == "observe"
