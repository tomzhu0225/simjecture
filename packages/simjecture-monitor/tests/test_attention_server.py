import contextlib
import math

import pytest
from simjecture_monitor import attention_support as attention
from simjecture_monitor.attention_server import AttentionService, sampled_answers
from simjecture_monitor.decision_interface import encode_request, scientific_request
from simjecture_monitor.synthetic_attention import make_observation, scripted_preference
from test_decision_interface import CharacterTokenizer


class Provider:
    def __init__(self, answers):
        self.tokenizer = CharacterTokenizer()
        self.identity = {"base_revision": "pinned", "adapter_sha256": "adapter"}
        self.model = self
        self.disabled = False
        self.calls = []
        self.answers = answers

    @contextlib.contextmanager
    def disable_adapter(self):
        self.disabled = True
        try:
            yield
        finally:
            self.disabled = False

    def predict(self, row):
        self.calls.append(self.disabled)
        return dict(
            answers=self.answers,
            probabilities={k: {v: 1.0} for k, v in self.answers.items()},
            prompt_sha256=encode_request(row, self.tokenizer, maximum_tokens=100000)[
                "prompt_sha256"
            ],
        )


def example():
    packet = make_observation(1, "lookup_needed")
    view = attention.pack(packet, len, token_counter_id="test", budget_tokens=100000)
    choice = scripted_preference(packet, view)
    row = scientific_request(packet, view, target=choice)
    return packet, {k: v["label"] for k, v in row["targets"].items()}


def test_base_and_adapter_use_same_input_and_explicit_weight_context():
    packet, answers = example()
    model = Provider(answers)
    service = AttentionService(model, adapter_loaded=True, maximum_tokens=100000)
    a = service.predict(dict(observation=packet.model_dump(), policy="base"))
    b = service.predict(dict(observation=packet.model_dump(), policy="adapted"))
    assert model.calls == [True, False] and not model.disabled
    assert a["input_prompt_sha256"] == b["input_prompt_sha256"]
    assert not a["adapter_active"] and b["adapter_active"]
    assert a["decision"]["status"] == b["decision"]["status"] == "ok"
    assert a["decision"]["model_view_sha256"] == a["view"]["sha256"]


def test_budget_failure_never_calls_model_and_unavailable_adapter_is_rejected():
    packet, answers = example()
    model = Provider(answers)
    service = AttentionService(model, adapter_loaded=False, maximum_tokens=1)
    result = service.predict(dict(observation=packet.model_dump()))
    assert result["decision"]["status"] == "insufficient_input"
    assert result["view"]["input_tokens"] > 1 and model.calls == []
    with pytest.raises(ValueError, match="not available"):
        service.predict(dict(observation=packet.model_dump(), policy="adapted"))


def test_invalid_question_binding_is_an_error_without_fabricated_citations():
    packet, answers = example()
    answers.update(
        route="worker_help", question_ref="q0", evidence_primary="none", evidence_secondary="none"
    )
    service = AttentionService(Provider(answers), adapter_loaded=False, maximum_tokens=100000)
    result = service.predict(dict(observation=packet.model_dump()))
    assert result["decision"]["status"] == "inference_error"
    assert result["prediction"]["answers"] == answers


def test_sample_receipt_retains_exact_distribution_and_greedy_shadow():
    packet, answers = example()
    service = AttentionService(Provider(answers), adapter_loaded=True, maximum_tokens=100000)
    result = service.predict(dict(observation=packet.model_dump(), sample=True, seed=17))
    assert result["behavior"]["sampled_answers"] == result["greedy_answers"] == answers
    assert result["behavior"]["sampled_joint_log_probability"] == 0
    assert result["behavior"]["probabilities"] == result["prediction"]["probabilities"]
    assert result["behavior"]["prompt_sha256"] == result["input_prompt_sha256"]
    distribution = {"route": {"observe": 0.75, "director": 0.25}, "basis": {"trend": 1.0}}
    chosen, logp = sampled_answers(distribution, 17)
    assert logp == pytest.approx(math.log(distribution["route"][chosen["route"]]))
    assert (chosen, logp) == sampled_answers(distribution, 17)
    with pytest.raises(ValueError, match="Invalid behavior"):
        sampled_answers({"route": {"observe": float("nan")}}, 1)
