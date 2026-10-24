import importlib.util
from pathlib import Path

import pytest


def clock_type(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("heartbeat_test", scripts / "heartbeat_trials.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ParkingClock


def test_clock_produces_new_elapsed_evidence_without_any_worker_eof(monkeypatch):
    clock = clock_type(monkeypatch)()
    assert clock.observe(is_parked=True, now=100) is None
    assert clock.observe(is_parked=True, now=114.9) is None
    assert clock.observe(is_parked=True, now=115) == dict(sequence=1, parked_seconds=15)
    assert clock.observe(is_parked=True, now=115.1) is None
    assert clock.observe(is_parked=True, now=130) == dict(sequence=2, parked_seconds=30)


def test_clock_never_catches_up_in_a_burst_and_resets_for_next_wait(monkeypatch):
    clock = clock_type(monkeypatch)()
    assert clock.observe(is_parked=False, now=0) is None
    assert clock.observe(is_parked=True, now=1) is None
    assert clock.observe(is_parked=True, now=61) == dict(sequence=1, parked_seconds=60)
    assert clock.observe(is_parked=True, now=62) is None
    assert clock.observe(is_parked=False, now=63) is None
    assert clock.observe(is_parked=True, now=64) is None
    assert clock.observe(is_parked=True, now=79) == dict(sequence=2, parked_seconds=15)
    with pytest.raises(ValueError):
        clock_type(monkeypatch)(interval=0)
