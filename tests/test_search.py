from __future__ import annotations

import json

import pytest

from conjecture_solver.confirmation import (
    ConfirmationDisposition,
    PICConfirmationRunner,
    confirmation_design_from_search,
)
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.llm import CompletionResult, ModelRoute
from conjecture_solver.search import (
    AISearchStrategyGenerator,
    AIStrategyDraft,
    BlindedSearchRequest,
    BlindedSearchRunner,
    CandidateSuggestion,
    SearchMethod,
    SearchStrategyRejected,
    SymmetricMixtureCandidate,
    baseline_strategies,
    offline_ai_fixture_strategy,
)


class QueuedSearchClient:
    def __init__(
        self,
        contents: list[str],
        finish_reasons: list[str] | None = None,
    ) -> None:
        self.contents = contents
        self.finish_reasons = finish_reasons or ["stop"] * len(contents)
        self.calls = 0
        self.messages: list[list[dict[str, str]]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResult:
        del escalation_reason, max_tokens, temperature
        self.messages.append(messages.copy())
        content = self.contents[self.calls]
        self.calls += 1
        return CompletionResult(
            request_id=f"offline_search_{self.calls}",
            model="deepseek-v4-flash-0731-fixture",
            content=content,
            finish_reason=self.finish_reasons[self.calls - 1],
            usage={"total_tokens": 0},
            route=route,
            route_reason="offline deterministic test fixture",
        )


def test_candidate_grammar_enforces_exact_target_moments() -> None:
    request = BlindedSearchRequest()
    candidate = SymmetricMixtureCandidate(
        inner_pair_weight=0.37,
        inner_drift=0.24,
        outer_drift=0.91,
    )
    distribution = candidate.distribution()

    assert distribution.density() == pytest.approx(1.0)
    assert distribution.mean() == pytest.approx(0.0, abs=1e-15)
    assert distribution.variance() == pytest.approx(1.0, abs=request.moment_tolerance)
    assert candidate.thermal_sigma > 0


def test_model_receives_blinded_bounds_and_no_prior_results() -> None:
    request = BlindedSearchRequest()
    fixture = offline_ai_fixture_strategy(request)
    draft = AIStrategyDraft(
        candidates=tuple(
            CandidateSuggestion(parameters=item.parameters, rationale=item.rationale)
            for item in fixture.proposals
        ),
        search_rationale="offline fixture",
    )
    client = QueuedSearchClient([draft.model_dump_json()])
    AISearchStrategyGenerator(client).generate(request)

    prompt_document = json.loads(client.messages[0][1]["content"])
    serialized = json.dumps(prompt_document, sort_keys=True)
    assert prompt_document["request"]["disclosure"].startswith("candidate grammar")
    assert "prior candidate evaluations" in serialized
    assert "known_witness" not in serialized
    assert "two_stream_growth_rate" not in serialized
    assert "hypothesis_falsified" not in serialized


def test_ai_strategy_repair_records_rejection_reason() -> None:
    request = BlindedSearchRequest()
    admitted = offline_ai_fixture_strategy(request)
    valid_draft = AIStrategyDraft(
        candidates=tuple(
            CandidateSuggestion(parameters=item.parameters, rationale=item.rationale)
            for item in admitted.proposals
        ),
        search_rationale="valid repaired batch",
    )
    duplicate_draft = AIStrategyDraft(
        candidates=(valid_draft.candidates[0],) * request.evaluations_per_method,
        search_rationale="invalid duplicate batch",
    )
    client = QueuedSearchClient(
        [duplicate_draft.model_dump_json(), valid_draft.model_dump_json()]
    )
    strategy = AISearchStrategyGenerator(client).generate(request)

    assert client.calls == 2
    assert len(strategy.model_calls) == 2
    assert "duplicate physical distribution" in strategy.model_calls[0].admission_errors[0]


def test_length_limited_empty_response_reaches_repair_gate() -> None:
    request = BlindedSearchRequest()
    admitted = offline_ai_fixture_strategy(request)
    valid_draft = AIStrategyDraft(
        candidates=tuple(
            CandidateSuggestion(parameters=item.parameters, rationale=item.rationale)
            for item in admitted.proposals
        ),
        search_rationale="valid second response",
    )
    client = QueuedSearchClient(
        ["", valid_draft.model_dump_json()],
        finish_reasons=["length", "stop"],
    )
    strategy = AISearchStrategyGenerator(client).generate(request)
    assert strategy.model_calls[0].finish_reason == "length"
    assert strategy.model_calls[0].admission_errors == ("incomplete completion: length",)
    assert len(strategy.proposals) == request.evaluations_per_method


def test_rejected_search_never_becomes_a_strategy() -> None:
    request = BlindedSearchRequest()
    admitted = offline_ai_fixture_strategy(request)
    short = AIStrategyDraft(
        candidates=(
            CandidateSuggestion(
                parameters=admitted.proposals[0].parameters,
                rationale="too short",
            ),
        ),
        search_rationale="invalid budget",
    )
    client = QueuedSearchClient([short.model_dump_json()])
    with pytest.raises(SearchStrategyRejected, match="exact evaluation budget"):
        AISearchStrategyGenerator(client, max_attempts=1).generate(request)


def test_equal_budget_search_is_replayable_without_supplied_strategy() -> None:
    request = BlindedSearchRequest()
    strategies = (
        offline_ai_fixture_strategy(request),
        *baseline_strategies(request),
    )
    with SQLiteEventLedger() as ledger:
        report = BlindedSearchRunner(
            campaign_id="campaign_blinded_search_test",
            ledger=ledger,
            request=request,
            strategies=strategies,
        ).run()
        event_count = len(ledger.load("campaign_blinded_search_test"))
        replay = BlindedSearchRunner(
            campaign_id="campaign_blinded_search_test",
            ledger=ledger,
            request=request,
        ).run()

        assert report == replay
        assert report.equal_evaluation_budget
        assert event_count == 39
        assert len(ledger.load("campaign_blinded_search_test")) == event_count
        assert ledger.verify_chain("campaign_blinded_search_test")
        assert all(
            len(result.evaluations) == request.evaluations_per_method
            for result in report.method_results
        )
        ai_result = next(
            result for result in report.method_results if result.method is SearchMethod.AI
        )
        assert ai_result.first_falsifying_ordinal == 1
        assert report.confirmation_candidate_id == ai_result.best_candidate_id


def test_frozen_ai_candidate_confirms_across_seed_resolution_matrix() -> None:
    request = BlindedSearchRequest()
    with SQLiteEventLedger() as ledger:
        search = BlindedSearchRunner(
            campaign_id="campaign_blinded_confirmation_test",
            ledger=ledger,
            request=request,
            strategies=(
                offline_ai_fixture_strategy(request),
                *baseline_strategies(request),
            ),
        ).run()
        design = confirmation_design_from_search(search)
        report = PICConfirmationRunner(
            campaign_id="campaign_blinded_confirmation_test",
            ledger=ledger,
            design=design,
        ).run()
        replay = PICConfirmationRunner(
            campaign_id="campaign_blinded_confirmation_test",
            ledger=ledger,
            design=design,
        ).run()

        assert report == replay
        assert report.disposition is ConfirmationDisposition.CONFIRMED
        assert report.eligible_attempts == report.confirming_attempts == 6
        assert all(attempt.moments_match for attempt in report.attempts)
        assert all(attempt.opposite_stability_classes for attempt in report.attempts)
        assert all(
            attempt.outcome_separation > request.outcome_tolerance
            for attempt in report.attempts
        )
        assert len(ledger.load("campaign_blinded_confirmation_test")) == 47
        assert ledger.verify_chain("campaign_blinded_confirmation_test")
