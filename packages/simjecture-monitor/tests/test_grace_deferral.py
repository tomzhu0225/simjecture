import importlib.util
from pathlib import Path


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
    alert = dict(action="request_repair_judge", packet_sha256="sample")
    sup.monitor_pending = [alert]
    sup.monitor_alerts = [alert]
    sup.route_monitor_alerts()
    assert not forwarded and not sup.monitor_pending
    assert sup.grace_deferrals[0]["contradiction_age_seconds"] == 4
    monkeypatch.setattr(loaded.time, "time", lambda: 111)
    fresh = dict(action="request_repair_judge", packet_sha256="new-evidence")
    sup.monitor_pending = [fresh]
    sup.route_monitor_alerts()
    assert forwarded == [fresh]
