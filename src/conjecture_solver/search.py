"""Blinded, budget-matched search over a constrained distribution grammar."""

from __future__ import annotations

import hashlib
import itertools
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Protocol

import numpy as np
from pydantic import Field, ValidationError, model_validator
from scipy.stats import qmc

from .benchmarks.kinetic_sufficiency import (
    DistributionMoments,
    GaussianComponent,
    GaussianMixture,
    LinearMode,
    moments,
    solve_modes,
)
from .ledger import SQLiteEventLedger, StoredEvent
from .llm import CompletionResult, ModelRoute
from .models import StrictModel, utc_now


class SearchMethod(StrEnum):
    AI = "ai"
    GRID = "grid"
    RANDOM = "random"
    LATIN_HYPERCUBE = "latin_hypercube"


class CandidateOutcome(StrEnum):
    VALID = "valid"
    NUMERICAL_FAILURE = "numerical_failure"


class ParameterInterval(StrictModel):
    minimum: float
    maximum: float

    @model_validator(mode="after")
    def ordered(self) -> ParameterInterval:
        if self.minimum >= self.maximum:
            raise ValueError("parameter interval must have positive width")
        return self

    def map_unit(self, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("normalized parameter must lie in [0, 1]")
        return self.minimum + value * (self.maximum - self.minimum)


class SymmetricMixtureSearchSpace(StrictModel):
    """Two symmetric drift pairs with a shared derived thermal width."""

    grammar: Literal["symmetric_unit_variance_gaussian_mixture_v1"] = (
        "symmetric_unit_variance_gaussian_mixture_v1"
    )
    inner_pair_weight: ParameterInterval = ParameterInterval(minimum=0.1, maximum=0.9)
    inner_drift: ParameterInterval = ParameterInterval(minimum=0.0, maximum=0.95)
    outer_drift: ParameterInterval = ParameterInterval(minimum=0.0, maximum=0.95)
    required_order: Literal["inner_drift <= outer_drift"] = "inner_drift <= outer_drift"
    derived_width: Literal[
        "sqrt(1-inner_pair_weight*inner_drift^2-(1-inner_pair_weight)*outer_drift^2)"
    ] = "sqrt(1-inner_pair_weight*inner_drift^2-(1-inner_pair_weight)*outer_drift^2)"


class SymmetricMixtureCandidate(StrictModel):
    inner_pair_weight: float = Field(gt=0, lt=1)
    inner_drift: float = Field(ge=0, lt=1)
    outer_drift: float = Field(ge=0, lt=1)

    @model_validator(mode="after")
    def valid_unit_variance_parameterization(self) -> SymmetricMixtureCandidate:
        if self.inner_drift > self.outer_drift:
            raise ValueError("inner_drift must not exceed outer_drift")
        if self.thermal_variance <= 0:
            raise ValueError("drifts leave no positive thermal variance")
        return self

    @property
    def thermal_variance(self) -> float:
        return 1.0 - (
            self.inner_pair_weight * self.inner_drift**2
            + (1.0 - self.inner_pair_weight) * self.outer_drift**2
        )

    @property
    def thermal_sigma(self) -> float:
        return float(np.sqrt(self.thermal_variance))

    def distribution(self) -> GaussianMixture:
        inner_side_weight = self.inner_pair_weight / 2.0
        outer_side_weight = (1.0 - self.inner_pair_weight) / 2.0
        return GaussianMixture(
            components=(
                GaussianComponent(
                    weight=inner_side_weight,
                    drift=-self.inner_drift,
                    sigma=self.thermal_sigma,
                ),
                GaussianComponent(
                    weight=inner_side_weight,
                    drift=self.inner_drift,
                    sigma=self.thermal_sigma,
                ),
                GaussianComponent(
                    weight=outer_side_weight,
                    drift=-self.outer_drift,
                    sigma=self.thermal_sigma,
                ),
                GaussianComponent(
                    weight=outer_side_weight,
                    drift=self.outer_drift,
                    sigma=self.thermal_sigma,
                ),
            )
        )

    def distribution_hash(self) -> str:
        aggregated: dict[tuple[float, float], float] = {}
        for component in self.distribution().components:
            key = (round(component.drift, 12), round(component.sigma, 12))
            aggregated[key] = aggregated.get(key, 0.0) + component.weight
        payload = json.dumps(
            [
                {
                    "drift": drift,
                    "sigma": sigma,
                    "weight": round(weight, 12),
                }
                for (drift, sigma), weight in sorted(aggregated.items())
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class BlindedSearchRequest(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = "search_request_blinded_moment_sufficiency_v1"
    research_goal: str = (
        "Find a distribution with density=1, mean_velocity=0, and variance=1 whose "
        "dominant linear growth rate differs from the unit Maxwellian reference."
    )
    model_family: Literal["linearized_1d_electrostatic_vlasov_poisson"] = (
        "linearized_1d_electrostatic_vlasov_poisson"
    )
    wavenumber: float = Field(default=0.5, gt=0)
    reference_distribution: GaussianMixture = GaussianMixture(
        components=(GaussianComponent(weight=1.0, drift=0.0, sigma=1.0),)
    )
    target_moments: DistributionMoments = DistributionMoments(
        density=1.0,
        mean_velocity=0.0,
        variance=1.0,
    )
    moment_tolerance: float = Field(default=1e-10, gt=0)
    outcome_tolerance: float = Field(default=0.02, gt=0)
    candidate_space: SymmetricMixtureSearchSpace = SymmetricMixtureSearchSpace()
    evaluations_per_method: int = Field(default=8, ge=2, le=64)
    baseline_seed: int = Field(default=20260809, ge=0)
    comparison_methods: tuple[SearchMethod, ...] = (
        SearchMethod.AI,
        SearchMethod.GRID,
        SearchMethod.RANDOM,
        SearchMethod.LATIN_HYPERCUBE,
    )
    disclosure: Literal[
        "candidate grammar and bounds only; no prior candidate evaluations or planted parameters"
    ] = "candidate grammar and bounds only; no prior candidate evaluations or planted parameters"

    @model_validator(mode="after")
    def unique_comparison_methods(self) -> BlindedSearchRequest:
        if len(self.comparison_methods) != len(set(self.comparison_methods)):
            raise ValueError("comparison methods must be unique")
        if SearchMethod.AI not in self.comparison_methods:
            raise ValueError("the autonomy checkpoint requires an AI strategy")
        if abs(self.wavenumber - 0.5) > 1e-12:
            raise ValueError("the first blinded challenge is preregistered at k=0.5")
        return self


class CandidateSuggestion(StrictModel):
    parameters: SymmetricMixtureCandidate
    rationale: str = Field(min_length=1)


class AIStrategyDraft(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    candidates: tuple[CandidateSuggestion, ...] = Field(min_length=1)
    search_rationale: str = Field(min_length=1)


class SearchModelCallProvenance(StrictModel):
    request_id: str
    model: str
    route: ModelRoute
    route_reason: str
    finish_reason: str
    prompt_template_version: Literal["blinded_search_v1"] = "blinded_search_v1"
    prompt_hash: str
    output_schema_hash: str
    response_hash: str
    usage: dict[str, Any] = Field(default_factory=dict)
    admission_errors: tuple[str, ...] = ()
    attempt_number: int = Field(ge=1)
    created_at: datetime = Field(default_factory=utc_now)


class CandidateProposal(StrictModel):
    id: str
    ordinal: int = Field(ge=1)
    parameters: SymmetricMixtureCandidate
    rationale: str = Field(min_length=1)


class SearchStrategy(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    request_id: str
    method: SearchMethod
    generator: str
    proposals: tuple[CandidateProposal, ...] = Field(min_length=1)
    model_calls: tuple[SearchModelCallProvenance, ...] = ()

    @model_validator(mode="after")
    def coherent_strategy(self) -> SearchStrategy:
        if tuple(proposal.ordinal for proposal in self.proposals) != tuple(
            range(1, len(self.proposals) + 1)
        ):
            raise ValueError("proposal ordinals must be contiguous and one-based")
        if len({proposal.id for proposal in self.proposals}) != len(self.proposals):
            raise ValueError("candidate IDs must be unique")
        if self.method is SearchMethod.AI and not self.model_calls:
            raise ValueError("AI strategies require model-call provenance")
        if self.method is not SearchMethod.AI and self.model_calls:
            raise ValueError("baseline strategies cannot claim model-call provenance")
        return self


class ReferenceQualification(StrictModel):
    request_id: str
    moments: DistributionMoments
    mode: LinearMode
    qualified: bool


class CandidateEvaluation(StrictModel):
    request_id: str
    method: SearchMethod
    proposal: CandidateProposal
    outcome: CandidateOutcome
    moments: DistributionMoments | None = None
    mode: LinearMode | None = None
    reference_growth_rate: float | None = None
    outcome_separation: float | None = Field(default=None, ge=0)
    falsifies: bool = False
    failure_detail: str | None = None

    @model_validator(mode="after")
    def result_fields_match_outcome(self) -> CandidateEvaluation:
        successful_fields = (
            self.moments,
            self.mode,
            self.reference_growth_rate,
            self.outcome_separation,
        )
        if self.outcome is CandidateOutcome.VALID:
            if any(value is None for value in successful_fields):
                raise ValueError("valid evaluations require all scientific result fields")
            if self.failure_detail is not None:
                raise ValueError("valid evaluations cannot include a failure detail")
        elif not self.failure_detail:
            raise ValueError("failed evaluations require a failure detail")
        return self


class MethodSearchResult(StrictModel):
    method: SearchMethod
    evaluations: tuple[CandidateEvaluation, ...] = Field(min_length=1)
    first_falsifying_ordinal: int | None = Field(default=None, ge=1)
    best_candidate_id: str | None = None
    best_outcome_separation: float | None = Field(default=None, ge=0)


class BlindedSearchReport(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    request: BlindedSearchRequest
    reference: ReferenceQualification
    method_results: tuple[MethodSearchResult, ...]
    equal_evaluation_budget: bool
    confirmation_candidate_id: str | None = None
    confirmation_candidate: SymmetricMixtureCandidate | None = None
    selection_reason: str


class SearchStrategyRejected(ValueError):
    def __init__(
        self,
        errors: tuple[str, ...],
        model_calls: tuple[SearchModelCallProvenance, ...],
    ) -> None:
        super().__init__("search strategy rejected: " + "; ".join(errors))
        self.errors = errors
        self.model_calls = model_calls


class SearchCompletionClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResult: ...


def _canonical_candidate(
    inner_pair_weight: float,
    first_drift: float,
    second_drift: float,
) -> SymmetricMixtureCandidate:
    if first_drift <= second_drift:
        return SymmetricMixtureCandidate(
            inner_pair_weight=inner_pair_weight,
            inner_drift=first_drift,
            outer_drift=second_drift,
        )
    return SymmetricMixtureCandidate(
        inner_pair_weight=1.0 - inner_pair_weight,
        inner_drift=second_drift,
        outer_drift=first_drift,
    )


def validate_candidate(
    request: BlindedSearchRequest,
    candidate: SymmetricMixtureCandidate,
) -> tuple[str, ...]:
    space = request.candidate_space
    errors: list[str] = []
    checks = (
        ("inner_pair_weight", candidate.inner_pair_weight, space.inner_pair_weight),
        ("inner_drift", candidate.inner_drift, space.inner_drift),
        ("outer_drift", candidate.outer_drift, space.outer_drift),
    )
    for name, value, interval in checks:
        if value < interval.minimum - 1e-12 or value > interval.maximum + 1e-12:
            errors.append(f"{name} is outside the approved interval")
    candidate_moments = moments(candidate.distribution())
    for name, target in request.target_moments.model_dump().items():
        if abs(getattr(candidate_moments, name) - target) > request.moment_tolerance:
            errors.append(f"candidate does not satisfy target {name}")
    return tuple(errors)


def _proposal(
    request: BlindedSearchRequest,
    method: SearchMethod,
    ordinal: int,
    candidate: SymmetricMixtureCandidate,
    rationale: str,
) -> CandidateProposal:
    errors = validate_candidate(request, candidate)
    if errors:
        raise ValueError("; ".join(errors))
    identity = hashlib.sha256(
        f"{request.id}:{method.value}:{ordinal}:{candidate.distribution_hash()}".encode()
    ).hexdigest()[:16]
    return CandidateProposal(
        id=f"candidate_{method.value}_{identity}",
        ordinal=ordinal,
        parameters=candidate,
        rationale=rationale,
    )


def validate_strategy(
    request: BlindedSearchRequest,
    strategy: SearchStrategy,
) -> tuple[str, ...]:
    errors: list[str] = []
    if strategy.request_id != request.id:
        errors.append("strategy targets a different request")
    if strategy.method not in request.comparison_methods:
        errors.append("strategy method is outside the comparison contract")
    if len(strategy.proposals) != request.evaluations_per_method:
        errors.append("strategy does not use the exact evaluation budget")
    distribution_hashes: set[str] = set()
    for proposal in strategy.proposals:
        errors.extend(validate_candidate(request, proposal.parameters))
        fingerprint = proposal.parameters.distribution_hash()
        if fingerprint in distribution_hashes:
            errors.append("strategy contains a duplicate physical distribution")
        distribution_hashes.add(fingerprint)
    return tuple(dict.fromkeys(errors))


def admit_ai_strategy_draft(
    request: BlindedSearchRequest,
    draft: AIStrategyDraft,
    model_calls: tuple[SearchModelCallProvenance, ...],
    *,
    generator: str = "openai_compatible_model",
) -> SearchStrategy:
    proposals = tuple(
        _proposal(
            request,
            SearchMethod.AI,
            ordinal,
            suggestion.parameters,
            suggestion.rationale,
        )
        for ordinal, suggestion in enumerate(draft.candidates, start=1)
    )
    strategy = SearchStrategy(
        request_id=request.id,
        method=SearchMethod.AI,
        generator=generator,
        proposals=proposals,
        model_calls=model_calls,
    )
    errors = validate_strategy(request, strategy)
    if errors:
        raise ValueError("; ".join(errors))
    return strategy


def offline_ai_fixture_strategy(request: BlindedSearchRequest) -> SearchStrategy:
    """Deterministic CI fixture; this is not evidence of a live model call."""

    values = (
        (0.50, 0.85, 0.95),
        (0.50, 0.70, 0.90),
        (0.20, 0.10, 0.92),
        (0.80, 0.60, 0.94),
        (0.40, 0.30, 0.80),
        (0.60, 0.50, 0.85),
        (0.30, 0.20, 0.70),
        (0.70, 0.10, 0.60),
    )
    if request.evaluations_per_method != len(values):
        raise ValueError("offline AI fixture is defined only for an eight-evaluation budget")
    draft = AIStrategyDraft(
        candidates=tuple(
            CandidateSuggestion(
                parameters=SymmetricMixtureCandidate(
                    inner_pair_weight=weight,
                    inner_drift=inner,
                    outer_drift=outer,
                ),
                rationale="offline physics-guided CI fixture",
            )
            for weight, inner, outer in values
        ),
        search_rationale="exercise the blinded-search boundary without a network dependency",
    )
    provenance = SearchModelCallProvenance(
        request_id="offline_fixture_no_provider_request",
        model="offline-physics-heuristic-fixture",
        route=ModelRoute.DEFAULT,
        route_reason="deterministic CI fixture; no model was called",
        finish_reason="stop",
        prompt_hash="0" * 64,
        output_schema_hash="0" * 64,
        response_hash=hashlib.sha256(draft.model_dump_json().encode()).hexdigest(),
        usage={"total_tokens": 0},
        attempt_number=1,
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    return admit_ai_strategy_draft(
        request,
        draft,
        (provenance,),
        generator="offline_fixture_not_a_live_model",
    )


def offline_qualified_warpx_fixture_strategy(
    request: BlindedSearchRequest,
) -> SearchStrategy:
    """CI-only batch whose expected winner exactly matches the qualified WarpX scope."""

    values = (
        (0.50, 0.95, 0.95),
        (0.10, 0.00, 0.95),
        (0.10, 0.45, 0.95),
        (0.50, 0.80, 0.80),
        (0.50, 0.50, 0.95),
        (0.50, 0.60, 0.80),
        (0.90, 0.00, 0.70),
        (0.90, 0.20, 0.60),
    )
    if request.evaluations_per_method != len(values):
        raise ValueError("qualified WarpX fixture requires an eight-evaluation budget")
    draft = AIStrategyDraft(
        candidates=tuple(
            CandidateSuggestion(
                parameters=SymmetricMixtureCandidate(
                    inner_pair_weight=weight,
                    inner_drift=inner,
                    outer_drift=outer,
                ),
                rationale="offline qualified-WarpX integration fixture",
            )
            for weight, inner, outer in values
        ),
        search_rationale=(
            "exercise the qualified campaign boundary without claiming a live model call"
        ),
    )
    provenance = SearchModelCallProvenance(
        request_id="offline_qualified_warpx_fixture_no_provider_request",
        model="offline-qualified-warpx-fixture",
        route=ModelRoute.DEFAULT,
        route_reason="deterministic CI fixture; no model was called",
        finish_reason="stop",
        prompt_hash="0" * 64,
        output_schema_hash="0" * 64,
        response_hash=hashlib.sha256(draft.model_dump_json().encode()).hexdigest(),
        usage={"total_tokens": 0},
        attempt_number=1,
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
    )
    return admit_ai_strategy_draft(
        request,
        draft,
        (provenance,),
        generator="offline_qualified_warpx_fixture_not_a_live_model",
    )


class AISearchStrategyGenerator:
    def __init__(self, client: SearchCompletionClient, *, max_attempts: int = 2) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.client = client
        self.max_attempts = max_attempts

    @staticmethod
    def _messages(request: BlindedSearchRequest) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are selecting a bounded batch of candidate distributions for a "
                    "computational-physics search. Return exactly one JSON object matching "
                    "the supplied schema, with no Markdown. Use exactly the stated candidate "
                    "budget and order candidates intentionally. You have no evaluation "
                    "results, hidden benchmark parameters, or permission to change the "
                    "grammar. You propose candidates only; deterministic tools evaluate them."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "request": request.model_dump(mode="json"),
                        "output_schema": AIStrategyDraft.model_json_schema(),
                    },
                    sort_keys=True,
                ),
            },
        ]

    @staticmethod
    def _provenance(
        result: CompletionResult,
        messages: list[dict[str, str]],
        attempt_number: int,
    ) -> SearchModelCallProvenance:
        prompt = json.dumps(messages, sort_keys=True, separators=(",", ":"))
        schema = json.dumps(
            AIStrategyDraft.model_json_schema(),
            sort_keys=True,
            separators=(",", ":"),
        )
        return SearchModelCallProvenance(
            request_id=result.request_id,
            model=result.model,
            route=result.route,
            route_reason=result.route_reason,
            finish_reason=result.finish_reason,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            output_schema_hash=hashlib.sha256(schema.encode()).hexdigest(),
            response_hash=hashlib.sha256(result.content.encode()).hexdigest(),
            usage=result.usage,
            attempt_number=attempt_number,
        )

    def generate(
        self,
        request: BlindedSearchRequest,
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 16384,
    ) -> SearchStrategy:
        messages = self._messages(request)
        calls: list[SearchModelCallProvenance] = []
        last_errors: tuple[str, ...] = ("model returned no strategy",)
        attempt_limit = 1 if route is ModelRoute.ESCALATION else self.max_attempts
        for attempt_number in range(1, attempt_limit + 1):
            result = self.client.complete(
                messages,
                route=route,
                escalation_reason=escalation_reason,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            calls.append(self._provenance(result, messages, attempt_number))
            draft: AIStrategyDraft | None = None
            if result.finish_reason != "stop":
                last_errors = (f"incomplete completion: {result.finish_reason}",)
            else:
                try:
                    draft = AIStrategyDraft.model_validate_json(result.content)
                except ValidationError as error:
                    last_errors = (f"invalid strategy document: {error}",)
            if draft is not None:
                try:
                    strategy = admit_ai_strategy_draft(request, draft, tuple(calls))
                except (ValueError, ValidationError) as error:
                    last_errors = (f"invalid admitted strategy: {error}",)
                else:
                    return strategy
            calls[-1] = calls[-1].model_copy(update={"admission_errors": last_errors})
            messages.extend(
                (
                    {"role": "assistant", "content": result.content},
                    {
                        "role": "user",
                        "content": (
                            "The deterministic admission gate rejected the strategy for: "
                            + "; ".join(last_errors)
                            + ". Return a complete corrected JSON object only."
                        ),
                    },
                )
            )
        raise SearchStrategyRejected(last_errors, tuple(calls))


def _strategy_from_candidates(
    request: BlindedSearchRequest,
    method: SearchMethod,
    candidates: list[SymmetricMixtureCandidate],
    generator: str,
) -> SearchStrategy:
    proposals = tuple(
        _proposal(
            request,
            method,
            ordinal,
            candidate,
            f"preregistered {method.value} baseline candidate {ordinal}",
        )
        for ordinal, candidate in enumerate(candidates, start=1)
    )
    strategy = SearchStrategy(
        request_id=request.id,
        method=method,
        generator=generator,
        proposals=proposals,
    )
    errors = validate_strategy(request, strategy)
    if errors:
        raise RuntimeError("invalid deterministic baseline: " + "; ".join(errors))
    return strategy


def grid_strategy(request: BlindedSearchRequest) -> SearchStrategy:
    """Traverse a growing Cartesian lattice in declared coordinate order."""

    space = request.candidate_space
    candidates: list[SymmetricMixtureCandidate] = []
    seen: set[str] = set()
    resolution = 2
    while len(candidates) < request.evaluations_per_method:
        levels = np.linspace(0.0, 1.0, resolution)
        for weight_u, first_u, second_u in itertools.product(levels, repeat=3):
            candidate = _canonical_candidate(
                space.inner_pair_weight.map_unit(float(weight_u)),
                space.inner_drift.map_unit(float(first_u)),
                space.outer_drift.map_unit(float(second_u)),
            )
            fingerprint = candidate.distribution_hash()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            candidates.append(candidate)
            if len(candidates) == request.evaluations_per_method:
                break
        resolution += 1
    return _strategy_from_candidates(
        request,
        SearchMethod.GRID,
        candidates,
        "deterministic_cartesian_lattice",
    )


def random_strategy(request: BlindedSearchRequest) -> SearchStrategy:
    rng = np.random.default_rng(request.baseline_seed)
    space = request.candidate_space
    candidates: list[SymmetricMixtureCandidate] = []
    seen: set[str] = set()
    while len(candidates) < request.evaluations_per_method:
        unit = rng.random(3)
        candidate = _canonical_candidate(
            space.inner_pair_weight.map_unit(float(unit[0])),
            space.inner_drift.map_unit(float(unit[1])),
            space.outer_drift.map_unit(float(unit[2])),
        )
        fingerprint = candidate.distribution_hash()
        if fingerprint not in seen:
            seen.add(fingerprint)
            candidates.append(candidate)
    return _strategy_from_candidates(
        request,
        SearchMethod.RANDOM,
        candidates,
        f"numpy_pcg64_seed_{request.baseline_seed}",
    )


def latin_hypercube_strategy(request: BlindedSearchRequest) -> SearchStrategy:
    sampler = qmc.LatinHypercube(d=3, seed=request.baseline_seed)
    samples = sampler.random(request.evaluations_per_method)
    space = request.candidate_space
    candidates = [
        _canonical_candidate(
            space.inner_pair_weight.map_unit(float(unit[0])),
            space.inner_drift.map_unit(float(unit[1])),
            space.outer_drift.map_unit(float(unit[2])),
        )
        for unit in samples
    ]
    return _strategy_from_candidates(
        request,
        SearchMethod.LATIN_HYPERCUBE,
        candidates,
        f"scipy_latin_hypercube_seed_{request.baseline_seed}",
    )


def baseline_strategies(request: BlindedSearchRequest) -> tuple[SearchStrategy, ...]:
    factories = {
        SearchMethod.GRID: grid_strategy,
        SearchMethod.RANDOM: random_strategy,
        SearchMethod.LATIN_HYPERCUBE: latin_hypercube_strategy,
    }
    return tuple(
        factories[method](request)
        for method in request.comparison_methods
        if method is not SearchMethod.AI
    )


def qualify_reference(request: BlindedSearchRequest) -> ReferenceQualification:
    reference_moments = moments(request.reference_distribution)
    target = request.target_moments
    qualified = all(
        abs(getattr(reference_moments, name) - getattr(target, name))
        <= request.moment_tolerance
        for name in DistributionMoments.model_fields
    )
    mode = solve_modes(request.reference_distribution, wavenumber=request.wavenumber)[0]
    return ReferenceQualification(
        request_id=request.id,
        moments=reference_moments,
        mode=mode,
        qualified=qualified and mode.dielectric_residual <= 1e-8,
    )


def evaluate_candidate(
    request: BlindedSearchRequest,
    reference: ReferenceQualification,
    method: SearchMethod,
    proposal: CandidateProposal,
) -> CandidateEvaluation:
    try:
        candidate_moments = moments(proposal.parameters.distribution())
        candidate_mode = solve_modes(
            proposal.parameters.distribution(),
            wavenumber=request.wavenumber,
        )[0]
    except (RuntimeError, ValueError, FloatingPointError) as error:
        return CandidateEvaluation(
            request_id=request.id,
            method=method,
            proposal=proposal,
            outcome=CandidateOutcome.NUMERICAL_FAILURE,
            failure_detail=str(error),
        )
    moment_match = all(
        abs(getattr(candidate_moments, name) - getattr(request.target_moments, name))
        <= request.moment_tolerance
        for name in DistributionMoments.model_fields
    )
    separation = abs(candidate_mode.growth_rate - reference.mode.growth_rate)
    return CandidateEvaluation(
        request_id=request.id,
        method=method,
        proposal=proposal,
        outcome=CandidateOutcome.VALID,
        moments=candidate_moments,
        mode=candidate_mode,
        reference_growth_rate=reference.mode.growth_rate,
        outcome_separation=separation,
        falsifies=moment_match and separation > request.outcome_tolerance,
    )


def _method_result(
    method: SearchMethod,
    evaluations: tuple[CandidateEvaluation, ...],
) -> MethodSearchResult:
    valid = [
        evaluation
        for evaluation in evaluations
        if evaluation.outcome is CandidateOutcome.VALID
        and evaluation.outcome_separation is not None
    ]
    best = max(valid, key=lambda evaluation: evaluation.outcome_separation or -1.0, default=None)
    first = next(
        (evaluation.proposal.ordinal for evaluation in valid if evaluation.falsifies),
        None,
    )
    return MethodSearchResult(
        method=method,
        evaluations=evaluations,
        first_falsifying_ordinal=first,
        best_candidate_id=best.proposal.id if best else None,
        best_outcome_separation=best.outcome_separation if best else None,
    )


def build_search_report(
    request: BlindedSearchRequest,
    reference: ReferenceQualification,
    evaluations: dict[SearchMethod, tuple[CandidateEvaluation, ...]],
) -> BlindedSearchReport:
    results = tuple(
        _method_result(method, evaluations[method]) for method in request.comparison_methods
    )
    counts = {len(result.evaluations) for result in results}
    equal_budget = counts == {request.evaluations_per_method}
    ai_result = next(result for result in results if result.method is SearchMethod.AI)
    selected_evaluation: CandidateEvaluation | None = None
    if ai_result.first_falsifying_ordinal is not None:
        ai_valid_witnesses = [
            evaluation for evaluation in ai_result.evaluations if evaluation.falsifies
        ]
        selected_evaluation = max(
            ai_valid_witnesses,
            key=lambda evaluation: evaluation.outcome_separation or -1.0,
        )
        reason = "best falsifying AI candidate, frozen before independent confirmation"
    else:
        reason = "AI strategy found no falsifying candidate within the declared budget"
    return BlindedSearchReport(
        request=request,
        reference=reference,
        method_results=results,
        equal_evaluation_budget=equal_budget,
        confirmation_candidate_id=(
            selected_evaluation.proposal.id if selected_evaluation is not None else None
        ),
        confirmation_candidate=(
            selected_evaluation.proposal.parameters if selected_evaluation is not None else None
        ),
        selection_reason=reason,
    )


class SearchProjection:
    def __init__(self) -> None:
        self.request: BlindedSearchRequest | None = None
        self.reference: ReferenceQualification | None = None
        self.strategies: dict[SearchMethod, SearchStrategy] = {}
        self.evaluations: dict[SearchMethod, dict[int, CandidateEvaluation]] = {}
        self.report: BlindedSearchReport | None = None

    @classmethod
    def replay(cls, events: tuple[StoredEvent, ...]) -> SearchProjection:
        state = cls()
        for event in events:
            if event.event_type == "search_created":
                state.request = BlindedSearchRequest.model_validate(event.payload["request"])
            elif event.event_type == "reference_qualified":
                state.reference = ReferenceQualification.model_validate(event.payload["reference"])
            elif event.event_type == "search_strategy_admitted":
                strategy = SearchStrategy.model_validate(event.payload["strategy"])
                state.strategies[strategy.method] = strategy
            elif event.event_type == "candidate_evaluated":
                evaluation = CandidateEvaluation.model_validate(event.payload["evaluation"])
                state.evaluations.setdefault(evaluation.method, {})[
                    evaluation.proposal.ordinal
                ] = evaluation
            elif event.event_type == "search_completed":
                state.report = BlindedSearchReport.model_validate(event.payload["report"])
        return state


class BlindedSearchRunner:
    """Replayable evaluator; model calls occur before this boundary, never inside it."""

    def __init__(
        self,
        *,
        campaign_id: str,
        ledger: SQLiteEventLedger,
        request: BlindedSearchRequest,
        strategies: tuple[SearchStrategy, ...] = (),
    ) -> None:
        self.campaign_id = campaign_id
        self.ledger = ledger
        self.request = request
        self.supplied_strategies = {strategy.method: strategy for strategy in strategies}
        if len(self.supplied_strategies) != len(strategies):
            raise ValueError("only one strategy per method may be supplied")

    def _state(self) -> SearchProjection:
        return SearchProjection.replay(self.ledger.load(self.campaign_id))

    def _append(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, object],
        idempotency_suffix: str,
    ) -> None:
        self.ledger.append(
            campaign_id=self.campaign_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            idempotency_key=f"{self.campaign_id}:{idempotency_suffix}",
        )

    def run(self) -> BlindedSearchReport:
        state = self._state()
        if state.request is not None and state.request != self.request:
            raise ValueError("search campaign already exists with a different request")
        for method, recorded in state.strategies.items():
            supplied = self.supplied_strategies.get(method)
            if supplied is not None and supplied != recorded:
                raise ValueError(f"recorded {method.value} strategy differs from supplied strategy")
        if state.report is not None:
            return state.report

        if state.request is None:
            self._append(
                "search_created",
                "search",
                self.request.id,
                {"request": self.request.model_dump(mode="json")},
                "search-created",
            )
        state = self._state()

        if state.reference is None:
            reference = qualify_reference(self.request)
            if not reference.qualified:
                raise RuntimeError("reference distribution failed qualification")
            self._append(
                "reference_qualified",
                "reference",
                self.request.id,
                {"reference": reference.model_dump(mode="json")},
                "reference-qualified",
            )
        state = self._state()
        assert state.reference is not None

        for method in self.request.comparison_methods:
            if method in state.strategies:
                continue
            strategy = self.supplied_strategies.get(method)
            if strategy is None:
                raise RuntimeError(f"missing preregistered {method.value} strategy")
            errors = validate_strategy(self.request, strategy)
            if errors:
                raise ValueError("; ".join(errors))
            self._append(
                "search_strategy_admitted",
                "search_strategy",
                f"{self.request.id}:{method.value}",
                {"strategy": strategy.model_dump(mode="json")},
                f"strategy:{method.value}",
            )
        state = self._state()

        for method in self.request.comparison_methods:
            strategy = state.strategies[method]
            existing = state.evaluations.get(method, {})
            for proposal in strategy.proposals:
                if proposal.ordinal in existing:
                    continue
                evaluation = evaluate_candidate(
                    self.request,
                    state.reference,
                    method,
                    proposal,
                )
                self._append(
                    "candidate_evaluated",
                    "candidate",
                    proposal.id,
                    {"evaluation": evaluation.model_dump(mode="json")},
                    f"evaluation:{method.value}:{proposal.ordinal}",
                )
                state = self._state()
                existing = state.evaluations.get(method, {})

        state = self._state()
        ordered_evaluations = {
            method: tuple(
                state.evaluations[method][ordinal]
                for ordinal in range(1, self.request.evaluations_per_method + 1)
            )
            for method in self.request.comparison_methods
        }
        report = build_search_report(
            self.request,
            state.reference,
            ordered_evaluations,
        )
        self._append(
            "search_completed",
            "search",
            self.request.id,
            {"report": report.model_dump(mode="json")},
            "search-completed",
        )
        return self._state().report or report
