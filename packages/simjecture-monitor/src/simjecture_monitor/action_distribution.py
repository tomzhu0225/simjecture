"""A versioned joint action distribution for the public scientific output contract.

The raw masked-token probabilities stay unchanged. The scientific variant
conditions route/question pairs on structural validity, without deciding whether
attention is scientifically useful. Serving, replay and the optimizer use the
same factor support. General-decision tasks retain their independent fields.
"""

from __future__ import annotations

import math
import random

from .decision_interface import BASES, ROUTES
from .events import digest

INDEPENDENT = "independent/v1"
CONTRACT = "scientific-route-question/v1"
DISTRIBUTIONS = (INDEPENDENT, CONTRACT)
SCIENTIFIC_FIELDS = {"route", "question_ref", "basis", "evidence_primary", "evidence_secondary"}


def kind(behavior):
    value = behavior.get("distribution", INDEPENDENT)
    if value not in DISTRIBUTIONS:
        raise ValueError("Unknown action distribution")
    return value


def factor_support(labels, distribution):
    """Return (field names, allowed label tuples) in a deterministic order."""
    if distribution not in DISTRIBUTIONS:
        raise ValueError("Unknown action distribution")
    if not labels or any(
        not values or len(values) != len(set(values)) for values in labels.values()
    ):
        raise ValueError("Empty or repeated action labels")
    if distribution == INDEPENDENT:
        return [((field,), [(label,) for label in values]) for field, values in labels.items()]
    if (
        set(labels) != SCIENTIFIC_FIELDS
        or set(labels["route"]) != set(ROUTES)
        or set(labels["basis"]) != set(BASES)
        or "none" not in labels["question_ref"]
        or any(
            q != "none" and not (q.startswith("q") and q[1:].isdigit())
            for q in labels["question_ref"]
        )
    ):
        raise ValueError("Constrained distribution requires the full scientific field schema")
    pairs = [
        (route, question)
        for route in labels["route"]
        for question in labels["question_ref"]
        if (ROUTES[route][1] == "none") == (question == "none")
    ]
    # Nothing here removes a stale, quiet or scientifically unhelpful request.
    # Those decisions belong to the learned policy and the separate host gate.
    return [(("route", "question_ref"), pairs)] + [
        ((field,), [(label,) for label in values])
        for field, values in labels.items()
        if field not in {"route", "question_ref"}
    ]


def factors(probabilities, distribution=INDEPENDENT):
    labels = {field: list(values) for field, values in probabilities.items()}
    support = factor_support(labels, distribution)
    for values in probabilities.values():
        if any(not math.isfinite(v) or v < 0 for v in values.values()) or not math.isclose(
            sum(values.values()), 1.0, rel_tol=1e-5, abs_tol=1e-6
        ):
            raise ValueError("Invalid behavior distribution")
    result = []
    for fields, candidates in support:
        if distribution == INDEPENDENT:
            # Preserve historical draws and logged floats exactly.
            weights = list(probabilities[fields[0]].values())
            normalizer = 0.0
        else:
            scores = [
                sum(
                    math.log(probabilities[field][label])
                    if probabilities[field][label] > 0
                    else -math.inf
                    for field, label in zip(fields, candidate, strict=True)
                )
                for candidate in candidates
            ]
            maximum = max(scores)
            if not math.isfinite(maximum):
                raise ValueError("No positive probability on valid action combinations")
            normalizer = maximum + math.log(sum(math.exp(s - maximum) for s in scores))
            weights = [math.exp(score - normalizer) for score in scores]
            # Saved float32 softmax values can sum slightly away from one.
            # Report validity mass relative to their normalized marginals.
            normalizer -= sum(math.log(sum(probabilities[field].values())) for field in fields)
        result.append(
            dict(
                fields=fields,
                candidates=candidates,
                probabilities=weights,
                log_normalizer=normalizer,
            )
        )
    return result


def decoding_receipt(probabilities, distribution):
    value = factors(probabilities, distribution)
    return dict(
        distribution=distribution,
        support_sha256=digest([(f["fields"], f["candidates"]) for f in value]),
        log_valid_pair_mass=value[0]["log_normalizer"] if distribution == CONTRACT else None,
    )


def choose(probabilities, *, distribution=INDEPENDENT, seed=None):
    """Sample the normalized joint distribution, or return its joint maximum."""
    if seed is not None and type(seed) is not int:
        raise ValueError("Sampling requires an integer seed")
    rng, answers, logp = random.Random(seed), {}, 0.0
    for factor in factors(probabilities, distribution):
        values = factor["probabilities"]
        index = (
            max(range(len(values)), key=values.__getitem__)
            if seed is None
            else rng.choices(range(len(values)), weights=values, k=1)[0]
        )
        answers.update(zip(factor["fields"], factor["candidates"][index], strict=True))
        logp += math.log(values[index])
    return answers, logp


def log_probability(probabilities, answers, distribution):
    value = 0.0
    for factor in factors(probabilities, distribution):
        selected = tuple(answers[field] for field in factor["fields"])
        probability = factor["probabilities"][factor["candidates"].index(selected)]
        if probability <= 0:
            raise ValueError("Recorded action has zero probability under the replayed policy")
        value += math.log(probability)
    return value


def validate_support(probabilities, row):
    expected = {field: list(q["criteria"]) for field, q in row["questions"].items()}
    if {field: list(v) for field, v in probabilities.items()} != expected:
        raise ValueError("Behavior support differs from the actual decision schema")


def replay(behavior, row):
    distribution = kind(behavior)
    if type(behavior.get("seed")) is not int:
        raise ValueError("Behavior replay requires the recorded integer seed")
    if distribution == CONTRACT:
        validate_support(behavior["probabilities"], row)
        expected = decoding_receipt(behavior["probabilities"], distribution)
        receipt = behavior.get("decoding", {})
        if (
            set(receipt) != set(expected)
            or receipt.get("distribution") != expected["distribution"]
            or receipt.get("support_sha256") != expected["support_sha256"]
            or not isinstance(receipt.get("log_valid_pair_mass"), (int, float))
            or not math.isclose(
                receipt["log_valid_pair_mass"],
                expected["log_valid_pair_mass"],
                abs_tol=1e-12,
                rel_tol=1e-12,
            )
        ):
            raise ValueError("Behavior constraint or normalization receipt changed")
    return choose(behavior["probabilities"], distribution=distribution, seed=behavior["seed"])


def gradient_terms(torch, logits, encoded, behavior, *, temperature):
    """Differentiable log probability and KL of the distribution actually served.

    No model loading occurs here. Small CPU tensors suffice to test gradients;
    the training script supplies its existing GPU logits and torch module.
    """
    distribution = kind(behavior)
    labels = encoded["labels"]
    if {k: list(v) for k, v in behavior["probabilities"].items()} != labels:
        raise ValueError("Optimizer and behavior action support differ")
    raw = {
        field: (logits[i, encoded["symbol_ids"][: len(values)]] / temperature).log_softmax(-1)
        for i, (field, values) in enumerate(labels.items())
    }
    current_logp, old_logp, kl = logits.new_zeros(()), 0.0, logits.new_zeros(())
    for factor in factors(behavior["probabilities"], distribution):
        fields, candidates = factor["fields"], factor["candidates"]
        scores = torch.stack(
            [
                sum(
                    raw[field][labels[field].index(label)]
                    for field, label in zip(fields, candidate, strict=True)
                )
                for candidate in candidates
            ]
        )
        logp = scores.log_softmax(-1)
        selected = candidates.index(tuple(behavior["sampled_answers"][field] for field in fields))
        reference = logits.new_tensor(factor["probabilities"])
        if factor["probabilities"][selected] <= 0:
            raise ValueError("Selected behavior action has zero probability")
        current_logp = current_logp + logp[selected]
        old_logp += math.log(factor["probabilities"][selected])
        kl = kl + (logp.exp() * (logp - reference.clamp_min(1e-12).log())).sum()
    return current_logp, old_logp, kl
