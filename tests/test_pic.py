from __future__ import annotations

import pytest

from conjecture_solver.adapters.base import SimulatorAdapter
from conjecture_solver.adapters.pic import (
    DeterministicPICScheduler,
    ElectrostaticPICAdapter,
)
from conjecture_solver.benchmarks.electrostatic_pic import (
    PICConfig,
    PICDistribution,
    build_pic_experiment,
    build_pic_problem,
    run_pic_case,
    run_pic_sufficiency_benchmark,
)
from conjecture_solver.campaign import CampaignRunner
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.llm import CompletionResult, ModelRoute
from conjecture_solver.models import (
    ClaimDisposition,
    HypothesisNode,
    HypothesisOrigin,
)
from conjecture_solver.proposals import (
    ProposalDraft,
    ProposalGenerator,
    pic_proposal_request,
    record_admitted_proposal,
)


def changed_config(**changes: float | int) -> PICConfig:
    baseline = PICConfig().model_dump(mode="json")
    return PICConfig.model_validate({**baseline, **changes})


def test_independent_pic_reproduces_opposite_stability_classes() -> None:
    result = run_pic_sufficiency_benchmark()

    assert result.moments_match
    assert result.maxwellian.initial_moments.mean_velocity == pytest.approx(0.0, abs=1e-14)
    assert result.two_stream.initial_moments.mean_velocity == pytest.approx(0.0, abs=1e-14)
    assert result.maxwellian.initial_moments.variance == pytest.approx(1.0, abs=1e-14)
    assert result.two_stream.initial_moments.variance == pytest.approx(1.0, abs=1e-14)
    assert result.maxwellian.classification == "damped"
    assert result.two_stream.classification == "unstable"
    assert result.maxwellian.effective_growth_rate < 0
    assert result.two_stream.effective_growth_rate > 0
    assert result.hypothesis_falsified


def test_pic_passes_energy_and_gauss_law_validity_checks() -> None:
    result = run_pic_sufficiency_benchmark()
    for case in (result.maxwellian, result.two_stream):
        assert case.validity_passed
        assert case.relative_energy_drift < 1e-4
        assert case.maximum_gauss_residual < 1e-12
        assert len(case.trace.times) == 41


@pytest.mark.parametrize("seed", [1, 19])
def test_quiet_start_seed_changes_preserve_the_conclusion(seed: int) -> None:
    result = run_pic_sufficiency_benchmark(changed_config(seed=seed))
    assert result.maxwellian.classification == "damped"
    assert result.two_stream.classification == "unstable"
    assert result.hypothesis_falsified


def test_velocity_resolution_refinement_preserves_the_conclusion() -> None:
    coarse = run_pic_sufficiency_benchmark(changed_config(velocity_beams=192))
    fine = run_pic_sufficiency_benchmark(changed_config(velocity_beams=384))

    assert coarse.maxwellian.classification == fine.maxwellian.classification == "damped"
    assert coarse.two_stream.classification == fine.two_stream.classification == "unstable"
    assert coarse.hypothesis_falsified and fine.hypothesis_falsified
    assert fine.maxwellian.particle_count > coarse.maxwellian.particle_count


def test_pic_case_replay_is_bitwise_deterministic() -> None:
    config = changed_config(seed=31)
    first = run_pic_case(PICDistribution.SYMMETRIC_TWO_STREAM, config)
    replay = run_pic_case(PICDistribution.SYMMETRIC_TWO_STREAM, config)
    assert first == replay


def test_pic_adapter_runs_through_recoverable_campaign() -> None:
    hypothesis, _ = build_pic_problem()
    experiment = build_pic_experiment()
    scheduler = DeterministicPICScheduler()
    adapter = ElectrostaticPICAdapter(scheduler)
    assert isinstance(adapter, SimulatorAdapter)

    with SQLiteEventLedger() as ledger:
        package = CampaignRunner(
            campaign_id="campaign_pic_test",
            ledger=ledger,
            adapter=adapter,
            hypothesis=hypothesis,
            experiment=experiment,
        ).run()
        replayed = CampaignRunner(
            campaign_id="campaign_pic_test",
            ledger=ledger,
            adapter=ElectrostaticPICAdapter(scheduler),
            hypothesis=hypothesis,
            experiment=experiment,
        ).run()

        assert package.claim.disposition is ClaimDisposition.REFUTED_WITHIN_MODEL
        assert package.normalized_result.observables["hypothesis_falsified"] is True
        assert package.package_hash == replayed.package_hash
        assert scheduler.jobs and adapter.submitted_job_count == 1
        assert ledger.verify_chain("campaign_pic_test")


class OfflinePICProposalClient:
    def __init__(self, content: str) -> None:
        self.content = content

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResult:
        del messages, escalation_reason, max_tokens, temperature
        return CompletionResult(
            request_id="offline_pic_proposal",
            model="deepseek-v4-flash-0731-fixture",
            content=self.content,
            finish_reason="stop",
            usage={"total_tokens": 0},
            route=route,
            route_reason="offline deterministic CI fixture",
        )


def test_typed_proposal_to_pic_discovery_closes_offline_loop() -> None:
    hypothesis, observable = build_pic_problem()
    ai_hypothesis = HypothesisNode.model_validate(
        {
            **hypothesis.model_dump(mode="json"),
            "origin": HypothesisOrigin.AI.value,
        }
    )
    experiment = build_pic_experiment()
    draft = ProposalDraft(
        hypothesis=ai_hypothesis,
        observable=observable,
        experiment=experiment,
        rationale="Test a finite matched pair with an independent numerical method.",
        declared_unknowns=("opposite PIC stability classification",),
    )
    scheduler = DeterministicPICScheduler()
    adapter = ElectrostaticPICAdapter(scheduler)
    proposal = ProposalGenerator(
        client=OfflinePICProposalClient(draft.model_dump_json()),
        adapter=adapter,
    ).generate(pic_proposal_request())

    with SQLiteEventLedger() as ledger:
        record_admitted_proposal(
            ledger,
            campaign_id="campaign_ai_pic_test",
            record=proposal,
        )
        package = CampaignRunner(
            campaign_id="campaign_ai_pic_test",
            ledger=ledger,
            adapter=adapter,
            hypothesis=ai_hypothesis,
            experiment=experiment,
        ).run()
        events = ledger.load("campaign_ai_pic_test")

        assert events[0].event_type == "proposal_admitted"
        assert package.claim.disposition is ClaimDisposition.REFUTED_WITHIN_MODEL
        assert package.hypothesis.origin is HypothesisOrigin.AI
        assert package.verify_hash()
