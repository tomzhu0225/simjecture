from simjecture_monitor.checks_policy import ChecksAwareRules


def test_failed_public_check_routes_director_but_existing_assistance_takes_precedence():
    packet = dict(
        packet_sha256="observation",
        state=dict(
            events=[],
            host_state=dict(
                telemetry={},
                public_artifacts=dict(diagnostic_rows=[dict(original_checks_passed=False)]),
            ),
        ),
    )
    rule = ChecksAwareRules()
    assert rule.predict(packet)["choice"] == "wake_director"
    packet["state"]["host_state"]["director_active"] = True
    assert rule.predict(packet)["choice"] == "defer"
    packet["state"]["host_state"]["director_active"] = False
    packet["state"]["host_state"]["telemetry"]["workflow_complete"] = True
    assert rule.predict(packet)["choice"] == "defer"
