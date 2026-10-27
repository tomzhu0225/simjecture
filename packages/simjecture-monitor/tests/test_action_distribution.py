import copy
import math
import random

import pytest
from simjecture_monitor import attention_support as attention
from simjecture_monitor.action_distribution import (
    CONTRACT,
    INDEPENDENT,
    choose,
    decoding_receipt,
    factors,
    log_probability,
    replay,
)
from simjecture_monitor.attention_server import AttentionService
from simjecture_monitor.decision_interface import ROUTES, scientific_request
from simjecture_monitor.sampling_trace import SamplingTrace
from simjecture_monitor.synthetic_attention import make_observation
from test_attention_server import Provider
from test_sampling_trace import save


class DenseProvider(Provider):
    """All compiler candidates, with a deliberately inconsistent raw maximum."""

    def __init__(self):
        super().__init__({})
        self.temperature = 3.0

    def predict(self, row):
        result = super().predict(row)
        probabilities = {}
        for field, question in row["questions"].items():
            labels = list(question["criteria"])
            weights = {label: 1.0 for label in labels}
            if field == "route":
                weights["lookup_helper"] = 20.0
            if field == "question_ref":
                weights["none"] = 30.0
            total = sum(weights.values())
            probabilities[field] = {label: weight / total for label, weight in weights.items()}
        result.update(
            probabilities=probabilities,
            answers={k: max(v, key=v.get) for k, v in probabilities.items()},
        )
        return result


def example(*, questions=True):
    packet = make_observation(1, "lookup_needed")
    if not questions:
        packet = packet.model_copy(update=dict(questions=[], retrieval_history=[]))
    view = attention.pack(packet, len, token_counter_id="test", budget_tokens=100000)
    return packet, scientific_request(packet, view)


@pytest.mark.parametrize("questions", [False, True])
def test_joint_distribution_matches_explicit_conditioning(questions):
    packet, row = example(questions=questions)
    provider = DenseProvider()
    probabilities = provider.predict(row)["probabilities"]
    actual = factors(probabilities, CONTRACT)[0]
    expected = {
        (r, q): p * v
        for r, p in probabilities["route"].items()
        for q, v in probabilities["question_ref"].items()
        if (ROUTES[r][1] == "none") == (q == "none")
    }
    total = sum(expected.values())
    assert sum(actual["probabilities"]) == pytest.approx(1.0)
    assert dict(zip(actual["candidates"], actual["probabilities"], strict=True)) == pytest.approx(
        {pair: p / total for pair, p in expected.items()}
    )
    assert decoding_receipt(probabilities, CONTRACT)["log_valid_pair_mass"] == pytest.approx(
        math.log(total)
    )
    greedy, _ = choose(probabilities, distribution=CONTRACT)
    assert (greedy["route"], greedy["question_ref"]) == max(expected, key=expected.get)
    service = AttentionService(
        provider, adapter_loaded=True, maximum_tokens=100000, decision_distribution=CONTRACT
    )
    for seed in range(60):
        result = service.predict(dict(observation=packet.model_dump(), sample=True, seed=seed))
        assert result["decision"]["status"] == "ok"
        assert result["greedy_answers"]["route"] == "lookup_helper"
        assert result["greedy_answers"]["question_ref"] == "none"
        assert replay(result["behavior"], row) == (
            result["behavior"]["sampled_answers"],
            result["behavior"]["sampled_joint_log_probability"],
        )
        assert log_probability(
            probabilities, result["decision_answers"], CONTRACT
        ) == pytest.approx(result["behavior"]["sampled_joint_log_probability"])
        if not questions:
            assert result["decision"]["support_kind"] == "none"


def test_old_independent_draws_and_general_decisions_are_unchanged():
    probabilities = {"arbitrary": {"a": 0.1, "b": 0.7, "c": 0.2}, "second": {"y": 0.3, "n": 0.7}}
    for seed in range(100):
        rng, expected, logp = random.Random(seed), {}, 0.0
        for field, values in probabilities.items():
            label = rng.choices(list(values), weights=list(values.values()), k=1)[0]
            expected[field] = label
            logp += math.log(values[label])
        assert choose(probabilities, seed=seed) == (expected, logp)
    with pytest.raises(ValueError, match="scientific field schema"):
        choose(probabilities, distribution=CONTRACT, seed=1)


def test_no_valid_probability_is_a_failure_not_an_invented_observe():
    _, row = example(questions=False)
    probabilities = DenseProvider().predict(row)["probabilities"]
    probabilities["route"] = {r: float(r == "lookup") for r in probabilities["route"]}
    with pytest.raises(ValueError, match="No positive probability"):
        choose(probabilities, distribution=CONTRACT, seed=1)


def test_trace_binds_distribution_and_rejects_changed_constraint_receipt(tmp_path):
    packet, row = example()
    trace = SamplingTrace(tmp_path / "episode/monitor", seed=17, decision_distribution=CONTRACT)
    request = trace.request(packet, policy="adapted")
    service = AttentionService(
        DenseProvider(), adapter_loaded=True, maximum_tokens=100000, decision_distribution=CONTRACT
    )
    result = service.predict(dict(observation=packet.model_dump(), **request))
    wrong = copy.deepcopy(result)
    wrong["behavior"]["decoding"]["log_valid_pair_mass"] += 0.01
    with pytest.raises(ValueError, match="normalization receipt"):
        trace.record(packet, wrong, decision_path=tmp_path / "unused")
    wrong = copy.deepcopy(result)
    wrong["behavior"]["distribution"] = INDEPENDENT
    with pytest.raises(ValueError, match="assigned episode"):
        trace.record(packet, wrong, decision_path=tmp_path / "unused")
    with pytest.raises(ValueError, match="served distribution"):
        service.predict(dict(observation=packet.model_dump(), distribution=INDEPENDENT))
    save(trace, packet, result)
    assert len(trace.data["responses"]) == 1
    altered = copy.deepcopy(row)
    altered["questions"]["question_ref"]["criteria"]["q99"] = "Unseen question"
    with pytest.raises(ValueError, match="actual decision schema"):
        replay(result["behavior"], altered)
