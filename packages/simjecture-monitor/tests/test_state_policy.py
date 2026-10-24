import json

from simjecture_monitor.events import digest
from simjecture_monitor.state_policy import StateAwareRules


def event(identifier, name, *, success=False):
    output = (
        json.dumps(
            dict(
                relative_field_error=0.01,
                relative_charge_residual=1e-12,
                original_checks_passed=True,
            )
        )
        if success
        else "HARNESS_CONTRACT_ERROR"
    )
    return dict(
        id=identifier,
        body=dict(
            type="command_execution",
            command="experiment.py analyze --name " + name,
            exit_code=0 if success else 1,
            aggregated_output=output,
        ),
    )


def predict(events, host=None):
    state = dict(events=events, host_state=host or {})
    return StateAwareRules().predict(dict(state=state, packet_sha256=digest(state)))


def test_same_operation_success_clears_stale_error_but_another_operation_does_not():
    failed = event("failure", "control")
    assert predict([failed])["choice"] == "request_repair_judge"
    recovered = predict([failed, event("success", "control", success=True)])
    assert recovered["choice"] == "defer" and recovered["removed_event_ids"] == ["failure"]
    assert (
        predict([failed, event("other", "refined", success=True)])["choice"]
        == "request_repair_judge"
    )


def test_active_authority_does_not_need_another_discretionary_wake():
    assert predict([event("failure", "control")], dict(authority_active=True))["choice"] == "defer"
