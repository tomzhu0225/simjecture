from types import SimpleNamespace

import pytest
from simjecture_monitor.startup import ready_request


def test_bound_but_not_listening_socket_is_retried_without_repeating_inference(monkeypatch):
    calls = []

    def request(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionRefusedError("not listening yet")
        return {"choice": "defer"}

    monkeypatch.setattr("simjecture_monitor.startup.request", request)
    monkeypatch.setattr("simjecture_monitor.startup.time.sleep", lambda _: None)
    assert ready_request("socket", {}, process=SimpleNamespace(poll=lambda: None)) == {
        "choice": "defer"
    }
    assert len(calls) == 2


def test_accepted_but_timed_out_request_is_not_retried(monkeypatch):
    def request(*args, **kwargs):
        raise TimeoutError("accepted inference timed out")

    monkeypatch.setattr("simjecture_monitor.startup.request", request)
    with pytest.raises(TimeoutError):
        ready_request("socket", {}, process=SimpleNamespace(poll=lambda: None))
