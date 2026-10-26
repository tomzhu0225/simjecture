import copy

import pytest
from simjecture_monitor.multiadapter_server import MultiAdapterService
from test_attention_server import Provider, example


class NamedProvider(Provider):
    def __init__(self, answers):
        super().__init__(answers)
        self.active_adapter = "default"
        self.identity = {"initial": "identity"}
        self.selected_calls = []

    def set_adapter(self, name):
        self.active_adapter = name

    def predict(self, row):
        self.selected_calls.append(
            (self.active_adapter, copy.deepcopy(self.identity), self.disabled)
        )
        return super().predict(row) | dict(model_identity=copy.deepcopy(self.identity))


def test_named_policy_uses_its_weights_identity_and_canonical_policy_id():
    packet, answers = example()
    model = NamedProvider(answers)
    identities = {
        "rl": {"weight_hash": "rl-hash"},
        "continued_sft": {"weight_hash": "control-hash"},
    }
    service = MultiAdapterService(
        model, {"rl": "rl", "continued_sft": "default"}, identities, maximum_tokens=100000
    )
    results = [
        service.predict(dict(observation=packet.model_dump(), policy=policy))
        for policy in identities
    ]
    assert [call[:2] for call in model.selected_calls] == [
        ("rl", identities["rl"]),
        ("default", identities["continued_sft"]),
    ]
    assert model.active_adapter == "default" and model.identity == {"initial": "identity"}
    for policy, result in zip(identities, results, strict=True):
        assert result["policy"] == policy and result["adapter_active"]
        assert (
            result["model_identity"] == result["prediction"]["model_identity"] == identities[policy]
        )
        assert result["decision"]["policy_id"] == "scientific-attention-" + policy
    assert results[0]["input_prompt_sha256"] == results[1]["input_prompt_sha256"]
    service.predict(dict(observation=packet.model_dump(), policy="base"))
    assert model.selected_calls[-1][-1] is True


def test_adapter_selection_is_restored_after_an_invalid_request():
    _, answers = example()
    model = NamedProvider(answers)
    service = MultiAdapterService(model, {"rl": "rl"}, {"rl": {"weights": "rl"}})
    with pytest.raises(ValueError):
        service.predict(dict(policy="rl", observation={}))
    assert model.active_adapter == "default" and model.identity == {"initial": "identity"}
    with pytest.raises(ValueError, match="Unknown named"):
        service.predict(dict(policy="unregistered", observation={}))
