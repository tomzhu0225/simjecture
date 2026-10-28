import copy
from concurrent.futures import Future

import pytest
from simjecture_monitor import attention_support as protocol
from simjecture_monitor import tool
from test_attention_contract import observation


def config(mode="shadow", **changes):
    return tool.AttentionConfig(
        mode=mode, socket="/private/model.sock", auth_token_file="/private/token", **changes
    )


def packet(clock, sequence):
    return protocol.Observation.model_validate(
        observation(at=round(clock * 1000), sequence=sequence).model_dump()
        | dict(
            schema_version=protocol.VERSION,
            questions=[],
            retrieval_history=[],
            retrieval_history_complete=True,
        )
    )


def result(p):
    view = protocol.pack(p, len, token_counter_id="test", budget_tokens=1000000)
    choice = protocol.Choice(
        action="wake_director",
        support_kind="none",
        question_ref=None,
        basis="measurement",
        evidence=[next(iter(view.aliases))],
    )
    return dict(
        policy="conjecture1",
        adapter_active=True,
        model_identity=dict(
            checkpoint_config_sha256=tool.BASE_CONFIG_SHA256,
            adapter_files_sha256={"adapter_model.safetensors": tool.ADAPTER_SHA256},
        ),
        view=view.model_dump(),
        decision=protocol.bind_choice(p, view, choice, policy_id="test").model_dump(),
    )


class Immediate:
    def submit(self, fn, *args):
        future = Future()
        try:
            future.set_result(fn(*args))
        except Exception as e:
            future.set_exception(e)
        return future

    def shutdown(self, **kwargs):
        pass


class Client:
    def score(self, p):
        return result(p)


def observer(tmp_path, mode, monkeypatch, **changes):
    clock = [1000.0]
    monkeypatch.setattr(tool.time, "time", lambda: clock[0])
    value = tool.AttentionObserver(tmp_path, config(mode, **changes), client=Client())
    value.executor.shutdown()
    value.executor = Immediate()
    sequence = [0]

    def observe():
        sequence[0] += 1
        return packet(clock[0], sequence[0])

    return value, clock, observe


@pytest.mark.parametrize("mode", ["off", "shadow", "alerts"])
def test_only_explicit_alert_mode_dispatches_and_restart_cannot_repeat(tmp_path, monkeypatch, mode):
    value, clock, observe = observer(tmp_path, mode, monkeypatch)
    calls = []
    for _ in range(6):
        value.tick(observe, lambda *args: calls.append(args) or True)
        clock[0] += 6
    assert len(calls) == int(mode == "alerts")
    assert value.state["requests"] == (0 if mode == "off" else 6)
    value.close()
    restored = tool.AttentionObserver(tmp_path, config(mode), client=Client())
    restored.executor.shutdown()
    restored.executor = Immediate()
    for _ in range(4):
        restored.tick(observe, lambda *args: calls.append(args) or True)
        clock[0] += 6
    assert len(calls) == int(mode == "alerts")
    restored.close()


def test_uncertain_dispatch_is_not_retried_and_request_budget_is_durable(tmp_path, monkeypatch):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch, maximum_requests=3)
    calls = []

    def fail(*args):
        calls.append(args)
        raise RuntimeError("A host action might have started")

    for _ in range(9):
        value.tick(observe, fail)
        clock[0] += 6
    assert len(calls) == 1
    assert value.state["attempts"][0]["status"] == "reserved"
    assert value.state["requests"] == 3
    value.close()
    with pytest.raises(ValueError, match="immutable"):
        tool.AttentionObserver(tmp_path, config("shadow"))


def test_stale_response_or_changed_state_never_dispatches(tmp_path, monkeypatch):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch)
    calls = []
    for _ in range(4):
        value.tick(observe, lambda *args: calls.append(args) or True)
        clock[0] += 20
    assert calls == []
    value.close()


def test_client_rejects_wrong_weights_policy_and_fabricated_view(monkeypatch):
    p = packet(1000, 1)
    good = result(p)
    client = tool.AttentionClient(config())
    monkeypatch.setattr(client, "call", lambda payload: good)
    assert client.score(p)["policy"] == "conjecture1"
    for kind in ["weights", "policy", "text", "aliases", "packet"]:
        bad = copy.deepcopy(good)
        if kind == "weights":
            bad["model_identity"]["adapter_files_sha256"]["adapter_model.safetensors"] = "0" * 64
        elif kind == "policy":
            bad["policy"] = "base"
        elif kind == "text":
            bad["view"]["text"] += "fabricated"
        elif kind == "aliases":
            bad["view"]["aliases"] = {}
        else:
            bad["decision"]["packet_id"] = "other"
        monkeypatch.setattr(client, "call", lambda payload, response=bad: response)
        with pytest.raises(ValueError):
            client.score(p)


def test_closing_observer_cannot_dispatch_a_late_response(tmp_path, monkeypatch):
    value, clock, observe = observer(tmp_path, "alerts", monkeypatch)
    calls = []
    value.tick(observe, lambda *args: calls.append(args))
    value.close()
    clock[0] += 10
    value.tick(observe, lambda *args: calls.append(args))
    assert calls == []
