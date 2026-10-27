import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from test_workflow_attention import raw


def module(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    path = scripts / "scientific_workflow_trials.py"
    spec = importlib.util.spec_from_file_location("scientific_workflow_test", path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


class Lifecycle:
    def initialize(self, arm):
        self.arm = arm
        self.public_sequence = 1
        self.monitor_latest = raw()
        self.worker_parked = True
        self.discretionary_used = False
        host = self.monitor_latest["state"]["host_state"]
        host.update(
            authority_active=False, director_active=False, pending_explicit_help=0, active_helpers=0
        )

    def monitor_tick(self, directory):
        self.public_sequence += 1

    def snapshot(self, directory, now):
        self.public_sequence += 1
        value = copy.deepcopy(self.monitor_latest)
        value["state"]["host_state"]["worker_parked"] = self.worker_parked
        value["state"]["host_state"].update(getattr(self, "current_host_updates", {}))
        return value


def test_revision_tracks_scientific_changes_not_elapsed_time(monkeypatch):
    mod = module(monkeypatch)
    sup = mod.supervisor_type(SimpleNamespace(RawSupervisor=Lifecycle))()
    sup.initialize("rules")
    first = sup.canonical(sup.monitor_latest, 200.0)
    sup.monitor_latest["state"]["host_state"]["remaining_seconds"] -= 10
    second = sup.canonical(sup.monitor_latest, 210.0)
    assert first.state_revision == second.state_revision
    sup.monitor_latest["state"]["host_state"]["public_artifacts"]["analysis_options"]["gain"] = 0.7
    third = sup.canonical(sup.monitor_latest, 211.0)
    assert third.state_revision == second.state_revision + 1


def test_receipt_refresh_does_not_accelerate_the_fixed_poll_cadence(monkeypatch):
    mod = module(monkeypatch)
    clock = [100.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: clock[0])
    sup = mod.supervisor_type(SimpleNamespace(RawSupervisor=Lifecycle))()
    sup.initialize("observe")
    calls = []

    def receive(*args):
        calls.append(clock[0])
        sup.public_sequence += 1  # A fresh admission snapshot is not a new poll slot.

    sup.receive = receive
    for now in [100.0, 100.5, 101.0, 104.9, 105.0]:
        clock[0] = now
        sup.monitor_tick(None)
    assert calls == [100.0, 105.0]


def test_model_arm_sends_the_declared_adapter_policy(monkeypatch):
    mod = module(monkeypatch)
    monkeypatch.delenv("SIMJECTURE_ATTENTION_TOKEN_FILE", raising=False)
    sup = mod.supervisor_type(
        SimpleNamespace(RawSupervisor=Lifecycle), model_policy="continued_sft"
    )()
    sup.initialize("adapted")
    sent = []
    sup.monitor_socket = "/private/service.sock"
    sup.monitor_executor = SimpleNamespace(
        submit=lambda fn, path, payload, **kw: sent.append(payload)
    )
    sup.monitor_tick(None)
    assert len(sent) == 1 and sent[0]["policy"] == "continued_sft"


def test_response_from_another_adapter_cannot_be_admitted(monkeypatch):
    import pytest

    mod = module(monkeypatch)
    sup = mod.supervisor_type(SimpleNamespace(RawSupervisor=Lifecycle), model_policy="rl")()
    sup.initialize("adapted")
    with pytest.raises(ValueError, match="differs from the requested"):
        sup.receive(None, None, {"policy": "continued_sft"}, None)


def test_sampling_occurs_only_when_parked_and_never_logs_forwarding_credentials(
    monkeypatch, tmp_path
):
    import json

    mod = module(monkeypatch)
    clock = [100.0]
    monkeypatch.setattr(mod.time, "monotonic", lambda: clock[0])
    token = tmp_path / "token"
    token.write_text("test-forwarding-credential" * 3)
    monkeypatch.setenv("SIMJECTURE_ATTENTION_TOKEN_FILE", str(token))
    sup = mod.supervisor_type(SimpleNamespace(RawSupervisor=Lifecycle), sampling_seed=17)()
    sup.monitor_dir = tmp_path / "episode/monitor"
    sup.initialize("adapted")
    sent = []
    sup.monitor_socket = "/private/service.sock"
    sup.monitor_executor = SimpleNamespace(
        submit=lambda fn, path, payload, **kw: sent.append(payload)
    )
    sup.worker_parked = False
    sup.monitor_tick(None)
    assert sent == [] and sup.sampling_trace.data["requests"] == []
    clock[0] = 105.0
    sup.worker_parked = True
    # The legacy five-second snapshot still predates the live park transition.
    sup.monitor_latest["state"]["host_state"]["worker_parked"] = False
    sup.monitor_tick(None)
    assert len(sent) == 1 and sent[0]["sample"] is True
    assert sent[0]["seed"] == sup.sampling_trace.data["requests"][0]["seed"]
    assert sent[0]["observation"]["worker_state"] == "parked"
    assert sent[0]["auth_token"] == token.read_text()
    for path in sup.monitor_dir.glob("*.json"):
        assert token.read_text() not in path.read_text()
        json.loads(path.read_text())


def test_new_help_is_seen_before_sending_a_cached_eligible_observation(monkeypatch):
    mod = module(monkeypatch)
    monkeypatch.delenv("SIMJECTURE_ATTENTION_TOKEN_FILE", raising=False)
    sup = mod.supervisor_type(SimpleNamespace(RawSupervisor=Lifecycle))()
    sup.initialize("adapted")
    sup.current_host_updates = dict(active_helpers=1)
    sent = []
    sup.monitor_socket = "/private/service.sock"
    sup.monitor_executor = SimpleNamespace(submit=lambda *args, **kw: sent.append(args))
    sup.monitor_tick(None)
    assert sent == []


def test_routine_control_routes_through_the_shared_receipt_path_without_a_model(monkeypatch):
    mod = module(monkeypatch)
    sup = mod.supervisor_type(SimpleNamespace(RawSupervisor=Lifecycle))()
    sup.initialize("routine_help")
    received = []
    sup.receive = lambda raw, packet, result, directory: received.append(result)
    # There is deliberately no model executor or model socket on this instance.
    sup.monitor_tick(None)
    assert len(received) == 1
    decision = received[0]["decision"]
    assert decision["policy_id"] == "routine_help"
    assert decision["action"] == "request_worker_help"
    assert decision["evidence_ids"]
