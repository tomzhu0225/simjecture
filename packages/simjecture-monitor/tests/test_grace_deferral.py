import importlib.util
from pathlib import Path

from simjecture_monitor.policy import AlertGate


def test_grace_defers_dispatch_then_forwards_fresh_evidence_after_window(tmp_path, monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("grace_test", scripts / "grace_trials.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    monkeypatch.setattr(loaded.time, "time", lambda: 104)
    forwarded = []

    class Base:
        def route_monitor_alerts(self):
            forwarded.extend(self.monitor_pending)

    class Subject(loaded.GraceMixin, Base):
        pass

    sup = Subject()
    sup.root = sup.monitor_dir = tmp_path
    sup.worker_parked = True
    sup.first_mismatch_at = 100
    sup.monitor_gate = AlertGate(cooldown=60)
    packet = dict(packet_sha256="sample", state=dict(subject="worker", events=[]))
    decision = dict(choice="request_repair_judge", packet_sha256="sample")
    alert = sup.monitor_gate.accept(packet, decision, now=104)
    sup.monitor_pending = [alert]
    sup.monitor_alerts = [alert]
    sup.route_monitor_alerts()
    assert not forwarded and not sup.monitor_pending
    assert sup.grace_deferrals[0]["contradiction_age_seconds"] == 4
    monkeypatch.setattr(loaded.time, "time", lambda: 111)
    packet["packet_sha256"] = decision["packet_sha256"] = "new-evidence"
    fresh = sup.monitor_gate.accept(packet, decision, now=111)
    assert fresh is not None  # A deferred route did not consume the sixty-second cooldown.
    sup.monitor_pending = [fresh]
    sup.route_monitor_alerts()
    assert forwarded == [fresh]


def test_releasing_old_reservation_does_not_erase_newer_cooldown():
    gate = AlertGate(cooldown=60)
    packet = dict(packet_sha256="first", state=dict(subject="worker", events=[]))
    decision = dict(choice="request_repair_judge", packet_sha256="first")
    old = gate.accept(packet, decision, now=100)
    packet["packet_sha256"] = decision["packet_sha256"] = "second"
    newer = gate.accept(packet, decision, now=161)
    assert newer is not None
    gate.defer_before_dispatch(old)
    packet["packet_sha256"] = decision["packet_sha256"] = "third"
    assert gate.accept(packet, decision, now=162) is None
    assert gate.last[("worker", "request_repair_judge")] == 161
