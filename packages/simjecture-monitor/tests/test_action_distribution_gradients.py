"""Tiny tensor checks, run on the remote CPU coordinator; never load a model."""

import itertools
import math

import pytest

torch = pytest.importorskip("torch")

from simjecture_monitor.action_distribution import CONTRACT, choose, gradient_terms  # noqa: E402
from simjecture_monitor.decision_interface import BASES, ROUTES  # noqa: E402


def problem(questions):
    labels = dict(
        route=list(ROUTES),
        question_ref=["none", "q0"] if questions else ["none"],
        basis=list(BASES),
        evidence_primary=["none", "e0"],
        evidence_secondary=["none", "e0"],
    )
    encoded = dict(labels=labels, symbol_ids=list(range(10)))
    logits = torch.tensor(
        [[math.sin(i * 3 + j * 0.7) for j in range(10)] for i in range(5)], dtype=torch.float64
    )
    return logits, encoded


def full_joint(values, encoded, temperature):
    """Independent reference: enumerate the entire five-field action space."""
    labels = encoded["labels"]
    raw = {}
    for i, (field, candidates) in enumerate(labels.items()):
        v = values[i][: len(candidates)]
        weights = [math.exp(x / temperature - max(v) / temperature) for x in v]
        raw[field] = dict(zip(candidates, [w / sum(weights) for w in weights], strict=True))
    joint = {}
    for action in itertools.product(*labels.values()):
        choice = dict(zip(labels, action, strict=True))
        if (ROUTES[choice["route"]][1] == "none") != (choice["question_ref"] == "none"):
            continue
        joint[action] = math.prod(raw[field][choice[field]] for field in labels)
    total = sum(joint.values())
    return raw, {action: p / total for action, p in joint.items()}


@pytest.mark.parametrize("questions", [False, True])
def test_constrained_log_probability_kl_and_gradient_match_full_enumeration(questions):
    torch.set_num_threads(1)
    logits, encoded = problem(questions)
    temperature = 3.0
    raw, old_joint = full_joint(logits.tolist(), encoded, temperature)
    answers, old_logp = choose(raw, distribution=CONTRACT, seed=17)
    behavior = dict(distribution=CONTRACT, probabilities=raw, sampled_answers=answers)
    actual, saved, kl = gradient_terms(torch, logits, encoded, behavior, temperature=temperature)
    assert actual.item() == pytest.approx(old_logp, abs=1e-12)
    assert saved == pytest.approx(old_logp, abs=1e-12)
    assert abs(kl.item()) < 1e-12
    current = (logits + torch.cos(logits) * 0.13).requires_grad_(True)
    logp, _, kl = gradient_terms(torch, current, encoded, behavior, temperature=temperature)
    action = tuple(answers[k] for k in encoded["labels"])

    def objective(values):
        _, joint = full_joint(values, encoded, temperature)
        divergence = sum(p * math.log(p / old_joint[a]) for a, p in joint.items())
        return math.log(joint[action]) + 0.2 * divergence

    objective_tensor = logp + 0.2 * kl
    assert objective_tensor.item() == pytest.approx(objective(current.tolist()), abs=1e-12)
    objective_tensor.backward()
    epsilon = 1e-5
    for i, candidates in enumerate(encoded["labels"].values()):
        for j in range(10):
            if j >= len(candidates):
                assert current.grad[i, j].item() == 0
                continue
            plus, minus = current.tolist(), current.tolist()
            plus[i][j] += epsilon
            minus[i][j] -= epsilon
            numerical = (objective(plus) - objective(minus)) / (2 * epsilon)
            assert current.grad[i, j].item() == pytest.approx(numerical, abs=1e-8)
    if not questions:
        for index, route in enumerate(encoded["labels"]["route"]):
            if ROUTES[route][1] != "none":
                assert abs(current.grad[0, index].item()) < 1e-12
