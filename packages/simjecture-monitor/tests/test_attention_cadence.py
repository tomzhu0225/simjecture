import json

import pytest
from simjecture_monitor import tool
from test_optional_tool import Client, Immediate, config, observer, packet, result


def tick_at(value, clock, observe, calls, at):
    clock[0] = at
    value.tick(observe, lambda *args: calls.append(args) or True)


def admissions(root):
    return [
        json.loads(path.read_text())["admission"]["reason"]
        for path in sorted(root.glob("decision-*.json"))
    ]


@pytest.mark.parametrize("poll", [60, 300])
def test_real_poll_cadence_dispatches_after_two_fresh_confirmations(tmp_path, monkeypatch, poll):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=float(poll))
    calls = []
    for at in (1000, 1001, 1000 + poll, 1001 + poll):
        tick_at(value, clock, observe, calls, at)
    assert value.state["requests"] == 2
    assert admissions(tmp_path) == ["awaiting_persistence", "fresh_grounded_persistent_request"]
    assert len(calls) == 1
    value.close()

    restored = tool.AttentionObserver(
        tmp_path, config("alerts", poll_seconds=float(poll)), client=Client()
    )
    restored.executor.shutdown()
    restored.executor = Immediate()
    for at in (1002 + poll, 1003 + poll, 1002 + 2 * poll, 1003 + 2 * poll):
        tick_at(restored, clock, observe, calls, at)
    assert len(calls) == 1
    restored.close()


@pytest.mark.parametrize("poll", [60, 300])
def test_shadow_confirms_without_host_dispatch(tmp_path, monkeypatch, poll):
    value, clock, observe = observer(tmp_path, "shadow", monkeypatch, poll_seconds=float(poll))
    calls = []
    for at in (1000, 1001, 1000 + poll, 1001 + poll):
        tick_at(value, clock, observe, calls, at)
    assert value.state["requests"] == 2
    assert admissions(tmp_path) == ["awaiting_persistence", "fresh_grounded_persistent_request"]
    assert calls == []
    assert (
        json.loads((tmp_path / "decision-000002.json").read_text())["host_disposition"]
        == "shadow_only"
    )
    value.close()


@pytest.mark.parametrize("failure", ["stale", "mismatched"])
def test_stale_or_mismatched_result_cannot_confirm(tmp_path, monkeypatch, failure):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=60.0)
    calls = []
    tick_at(value, clock, observe, calls, 1000)
    tick_at(value, clock, observe, calls, 1001)
    if failure == "mismatched":

        class WrongClient:
            def score(self, p):
                response = result(p)
                response["decision"]["packet_id"] = "different-packet"
                return response

        value.client = WrongClient()
    tick_at(value, clock, observe, calls, 1060)
    tick_at(value, clock, observe, calls, 1076 if failure == "stale" else 1061)
    assert value.state["requests"] == 2
    assert admissions(tmp_path) == [
        "awaiting_persistence",
        "stale_response" if failure == "stale" else "input_binding_mismatch",
    ]
    assert calls == []
    value.close()


def test_request_budget_does_not_add_confirmation_calls(tmp_path, monkeypatch):
    value, clock, observe = observer(
        tmp_path, "alerts", monkeypatch, poll_seconds=60.0, maximum_requests=1
    )
    calls = []
    for at in (1000, 1001, 1060, 1061, 1120, 1121):
        tick_at(value, clock, observe, calls, at)
    assert value.state["requests"] == 1
    assert admissions(tmp_path) == ["awaiting_persistence"]
    assert calls == []
    value.close()


def test_changed_state_cannot_confirm(tmp_path, monkeypatch):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=60.0)
    calls = []
    tick_at(value, clock, observe, calls, 1000)
    tick_at(value, clock, observe, calls, 1001)
    tick_at(value, clock, observe, calls, 1030)
    assert value.state["requests"] == 1
    tick_at(value, clock, observe, calls, 1060)

    def changed():
        return packet(clock[0], 999).model_copy(update={"state_revision": 2})

    tick_at(value, clock, changed, calls, 1061)
    assert admissions(tmp_path) == ["awaiting_persistence", "state_changed"]
    assert value.state["requests"] == 2
    assert calls == []
    value.close()


@pytest.mark.parametrize("poll", [60, 300])
def test_missed_poll_resets_confirmation(tmp_path, monkeypatch, poll):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=float(poll))
    calls = []
    for at in (1000, 1001, 1001 + 2 * poll, 1002 + 2 * poll):
        tick_at(value, clock, observe, calls, at)
    assert admissions(tmp_path) == ["awaiting_persistence", "awaiting_persistence"]
    assert calls == []
    for at in (1001 + 3 * poll, 1002 + 3 * poll):
        tick_at(value, clock, observe, calls, at)
    assert admissions(tmp_path)[-1] == "fresh_grounded_persistent_request"
    assert len(calls) == 1
    assert value.state["requests"] == 3
    value.close()


def test_uncertain_dispatch_reservation_survives_restart_at_long_poll(tmp_path, monkeypatch):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=60.0)
    calls = []

    def uncertain(*args):
        calls.append(args)
        raise RuntimeError("host may already have started")

    for at in (1000, 1001, 1060):
        tick_at(value, clock, observe, calls, at)
    clock[0] = 1061
    value.tick(observe, uncertain)
    assert len(calls) == 1
    assert value.state["attempts"][0]["status"] == "reserved"
    value.close()
    restored = tool.AttentionObserver(
        tmp_path, config("alerts", poll_seconds=60.0), client=Client()
    )
    restored.executor.shutdown()
    restored.executor = Immediate()
    for at in (1062, 1063, 1122, 1123):
        tick_at(restored, clock, observe, calls, at)
    assert len(calls) == 1
    assert restored.state["attempts"][0]["status"] == "reserved"
    restored.close()


def test_ungrounded_responses_cannot_confirm(tmp_path, monkeypatch):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=60.0)

    class UngroundedClient:
        def score(self, p):
            response = result(p)
            response["decision"]["basis"] = "unspecified"
            return response

    value.client = UngroundedClient()
    calls = []
    for at in (1000, 1001, 1060, 1061):
        tick_at(value, clock, observe, calls, at)
    assert admissions(tmp_path) == ["ungrounded_attention", "ungrounded_attention"]
    assert calls == []
    value.close()


@pytest.mark.parametrize("poll,gap", [(5, 10000), (60, 75000), (300, 315000)])
def test_effective_profile_is_recorded(tmp_path, monkeypatch, poll, gap):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=float(poll))
    calls = []
    tick_at(value, clock, observe, calls, 1000)
    tick_at(value, clock, observe, calls, 1001)
    state = json.loads((tmp_path / "state.json").read_text())
    record = json.loads((tmp_path / "decision-000001.json").read_text())
    for profile in (state["admission_profile"], record["admission_profile"]):
        assert profile["maximum_gap_ms"] == gap
        assert profile["maximum_age_ms"] == 15000
    value.close()


def test_legacy_state_adds_profile_without_rewriting_old_decision(tmp_path, monkeypatch):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=60.0)
    calls = []
    tick_at(value, clock, observe, calls, 1000)
    tick_at(value, clock, observe, calls, 1001)
    value.close()

    state_path = tmp_path / "state.json"
    decision_path = tmp_path / "decision-000001.json"
    state = json.loads(state_path.read_text())
    original_config = state["configuration"]
    state.pop("admission_profile")
    state_path.write_text(json.dumps(state))
    old_decision = json.loads(decision_path.read_text())
    old_decision.pop("admission_profile")
    decision_path.write_text(json.dumps(old_decision))
    old_bytes = decision_path.read_bytes()

    restored = tool.AttentionObserver(
        tmp_path, config("alerts", poll_seconds=60.0), client=Client()
    )
    restored.executor.shutdown()
    restored.executor = Immediate()
    saved = json.loads(state_path.read_text())
    assert saved["configuration"] == original_config
    assert saved["admission_profile"]["maximum_gap_ms"] == 75000
    assert decision_path.read_bytes() == old_bytes
    tick_at(restored, clock, observe, calls, 1060)
    tick_at(restored, clock, observe, calls, 1061)
    new_decision = json.loads((tmp_path / "decision-000002.json").read_text())
    assert new_decision["admission_profile"]["maximum_gap_ms"] == 75000
    assert decision_path.read_bytes() == old_bytes
    restored.close()


@pytest.mark.parametrize("poll", [1.0, 5.0, 60.0, 300.0])
def test_preflight_liveness_and_funnel_counters(tmp_path, monkeypatch, poll):
    from simjecture_monitor.attention_admission import AdmissionProfile

    cfg = config("alerts", poll_seconds=poll, maximum_requests=3000)
    liveness = cfg.verify_liveness()
    assert liveness["maximum_gap_ms"] > poll * 1000
    assert liveness["budget_horizon_seconds"] == 3000 * poll
    with pytest.raises(ValueError, match="Confirmation gap is too small"):
        AdmissionProfile(minimum_confirmations=2, persistence_ms=5000, maximum_gap_ms=4000)
    if poll >= 60.0:
        with pytest.raises(ValueError, match="confirmation gap must exceed"):
            cfg.verify_liveness(profile=AdmissionProfile())

    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, poll_seconds=60.0)
    calls = []
    for at in (1000, 1001, 1060, 1061):
        tick_at(value, clock, observe, calls, at)
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["admission_reasons"] == {
        "awaiting_persistence": 1,
        "fresh_grounded_persistent_request": 1,
    }
    assert state["host_dispositions"] == {"dispatched": 1}
    value.close()
