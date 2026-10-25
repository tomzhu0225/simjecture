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
