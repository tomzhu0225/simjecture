from simjecture_monitor.generic_policy import GenericOperationalRules


def packet(**telemetry):
    return dict(
        packet_sha256="observation", state=dict(events=[], host_state=dict(telemetry=telemetry))
    )


def test_declared_quiet_window_and_retry_budget_prevent_premature_attention():
    rule = GenericOperationalRules()
    value = packet(
        no_new_output_seconds=40,
        quiet_remaining_seconds=20,
        consecutive_tool_failures=3,
        retry_budget_remaining=1,
    )
    assert rule.predict(value)["choice"] == "defer"
    value["state"]["host_state"]["telemetry"].update(
        quiet_remaining_seconds=0, retry_budget_remaining=0
    )
    assert rule.predict(value)["choice"] == "request_worker_help"


def test_active_assistance_and_successful_completion_override_old_error_counters():
    rule = GenericOperationalRules()
    value = packet(consecutive_tool_failures=4, no_new_output_seconds=60)
    assert rule.predict(value)["choice"] == "request_worker_help"
    value["state"]["host_state"]["authority_active"] = True
    assert rule.predict(value)["choice"] == "defer"
    value["state"]["host_state"]["authority_active"] = False
    value["state"]["host_state"]["telemetry"]["workflow_complete"] = True
    assert rule.predict(value)["choice"] == "defer"


def test_progress_avoids_attention_but_terminal_process_failure_routes_help():
    rule = GenericOperationalRules()
    value = packet(no_new_output_seconds=3, repeated_output_count=1)
    assert rule.predict(value)["choice"] == "defer"
    value["state"]["host_state"]["telemetry"]["terminal_exit_code"] = 2
    assert rule.predict(value)["choice"] == "request_worker_help"
