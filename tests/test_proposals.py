from __future__ import annotations

import json

import pytest

from conjecture_solver.adapters.fake import DeterministicKineticAdapter
from conjecture_solver.adapters.pic import ElectrostaticPICAdapter
from conjecture_solver.benchmarks.electrostatic_pic import (
    build_pic_experiment,
    build_pic_problem,
)
from conjecture_solver.benchmarks.kinetic_sufficiency import build_problem
from conjecture_solver.campaign import planted_experiment
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.llm import CompletionResult, ModelRoute
from conjecture_solver.models import HypothesisNode, HypothesisOrigin, PropositionClass
from conjecture_solver.proposals import (
    ProposalDraft,
    ProposalGenerator,
    ProposalRejected,
    pic_proposal_request,
    planted_proposal_request,
    record_admitted_proposal,
)


def valid_draft() -> ProposalDraft:
    hypothesis, observable = build_problem()
    ai_hypothesis = HypothesisNode.model_validate(
        {
            **hypothesis.model_dump(mode="json"),
            "origin": HypothesisOrigin.AI.value,
        }
    )
    return ProposalDraft(
        hypothesis=ai_hypothesis,
        observable=observable,
        experiment=planted_experiment(),
        rationale="A matched pair is a finite destructive witness.",
        declared_unknowns=("whether the two distributions have different growth rates",),
    )


def valid_pic_draft() -> ProposalDraft:
    hypothesis, observable = build_pic_problem()
    ai_hypothesis = HypothesisNode.model_validate(
        {
            **hypothesis.model_dump(mode="json"),
            "origin": HypothesisOrigin.AI.value,
        }
    )
    return ProposalDraft(
        hypothesis=ai_hypothesis,
        observable=observable,
        experiment=build_pic_experiment(),
        rationale="An independent PIC matched pair can destroy the sufficiency claim.",
        declared_unknowns=("whether the PIC envelope classifications differ",),
    )


class FakeCompletionClient:
    def __init__(self, contents: list[str], *, finish_reason: str = "stop") -> None:
        self.contents = contents
        self.finish_reason = finish_reason
        self.calls = 0

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResult:
        del messages, max_tokens, temperature
        index = min(self.calls, len(self.contents) - 1)
        self.calls += 1
        return CompletionResult(
            request_id=f"request_{self.calls}",
            model=("glm-5.2" if route is ModelRoute.ESCALATION else "deepseek-v4-flash-0731"),
            content=self.contents[index],
            finish_reason=self.finish_reason,
            usage={"total_tokens": 100},
            route=route,
            route_reason=escalation_reason or "default low-cost reasoning route",
        )


def generator(client: FakeCompletionClient, *, max_attempts: int = 2) -> ProposalGenerator:
    return ProposalGenerator(
        client=client,
        capabilities=DeterministicKineticAdapter().capabilities(),
        max_attempts=max_attempts,
    )


def test_valid_typed_proposal_is_admitted_with_hashed_provenance() -> None:
    content = valid_draft().model_dump_json()
    client = FakeCompletionClient([content])
    record = generator(client).generate(planted_proposal_request())

    assert record.validation.valid
    assert record.draft.hypothesis.formal_predicate is not None
    assert record.model_calls[0].model == "deepseek-v4-flash-0731"
    assert len(record.model_calls[0].prompt_hash) == 64
    assert len(record.model_calls[0].output_schema_hash) == 64
    assert len(record.model_calls[0].response_hash) == 64
    assert client.calls == 1


def test_only_admitted_proposal_is_recorded_idempotently() -> None:
    client = FakeCompletionClient([valid_draft().model_dump_json()])
    record = generator(client).generate(planted_proposal_request())

    with SQLiteEventLedger() as ledger:
        first = record_admitted_proposal(
            ledger,
            campaign_id="campaign_proposal_test",
            record=record,
        )
        replay = record_admitted_proposal(
            ledger,
            campaign_id="campaign_proposal_test",
            record=record,
        )

        assert first.sequence == replay.sequence
        assert len(ledger.load("campaign_proposal_test")) == 1
        assert ledger.verify_chain("campaign_proposal_test")
        stored = ledger.load("campaign_proposal_test")[0].payload["proposal_record"]
        assert stored["validation"]["valid"] is True
        assert "content" not in stored["model_calls"][0]


def test_invalid_json_gets_one_cheap_repair_attempt() -> None:
    client = FakeCompletionClient(["not-json", valid_draft().model_dump_json()])
    record = generator(client).generate(planted_proposal_request())

    assert len(record.model_calls) == 2
    assert all(call.route is ModelRoute.DEFAULT for call in record.model_calls)
    assert record.model_calls[1].attempt_number == 2
    assert "invalid proposal document" in record.model_calls[0].admission_errors[0]
    assert record.model_calls[1].admission_errors == ()


def test_unsupported_action_never_crosses_admission_gate() -> None:
    document = valid_draft().model_dump(mode="json")
    document["experiment"]["action_type"] = "launch_unapproved_warpx_job"
    content = json.dumps(document)
    client = FakeCompletionClient([content])

    with pytest.raises(ProposalRejected, match="outside the human-approved") as rejected:
        generator(client).generate(planted_proposal_request())

    assert len(rejected.value.model_calls) == 2
    assert any("action type" in error for error in rejected.value.errors)


def test_fixed_parameter_change_never_crosses_admission_gate() -> None:
    document = valid_draft().model_dump(mode="json")
    document["experiment"]["physical_parameters"]["wavenumber"] = 0.4
    client = FakeCompletionClient([json.dumps(document)])

    with pytest.raises(ProposalRejected) as rejected:
        generator(client, max_attempts=1).generate(planted_proposal_request())

    assert any("fixed parameter wavenumber" in error for error in rejected.value.errors)


def test_open_world_exhaustiveness_is_rejected_even_if_requested() -> None:
    document = valid_draft().model_dump(mode="json")
    document["hypothesis"]["proposition_class"] = PropositionClass.CAUSAL_EXHAUSTIVENESS.value
    document["hypothesis"]["formal_predicate"] = None
    request_document = planted_proposal_request().model_dump(mode="json")
    request_document["allowed_proposition_classes"] = [
        PropositionClass.CAUSAL_EXHAUSTIVENESS.value
    ]
    client = FakeCompletionClient([json.dumps(document)])

    with pytest.raises(ProposalRejected) as rejected:
        generator(client, max_attempts=1).generate(
            planted_proposal_request().__class__.model_validate(request_document)
        )

    assert any("causal-exhaustiveness" in error for error in rejected.value.errors)


def test_model_cannot_smuggle_a_claim_into_proposal_schema() -> None:
    document = valid_draft().model_dump(mode="json")
    document["claim"] = {"disposition": "supported_within_model"}
    client = FakeCompletionClient([json.dumps(document)])

    with pytest.raises(ProposalRejected, match="invalid proposal document"):
        generator(client, max_attempts=1).generate(planted_proposal_request())


def test_glm_route_and_reason_are_preserved_in_provenance() -> None:
    client = FakeCompletionClient([valid_draft().model_dump_json()])
    record = generator(client).generate(
        planted_proposal_request(),
        route=ModelRoute.ESCALATION,
        escalation_reason="default model failed two typed repair attempts",
    )

    assert record.model_calls[0].route is ModelRoute.ESCALATION
    assert record.model_calls[0].model == "glm-5.2"
    assert "failed two" in record.model_calls[0].route_reason


def test_glm_does_not_receive_automatic_repair_call() -> None:
    client = FakeCompletionClient(["not-json", valid_draft().model_dump_json()])
    with pytest.raises(ProposalRejected):
        generator(client).generate(
            planted_proposal_request(),
            route=ModelRoute.ESCALATION,
            escalation_reason="manual escalation after cheap route failed",
        )
    assert client.calls == 1


def test_selected_adapter_rejects_invalid_numerical_configuration() -> None:
    document = valid_pic_draft().model_dump(mode="json")
    document["experiment"]["numerical_parameters"]["unapproved_solver_knob"] = 1
    client = FakeCompletionClient([json.dumps(document)])
    pic_generator = ProposalGenerator(
        client=client,
        adapter=ElectrostaticPICAdapter(),
        max_attempts=1,
    )

    with pytest.raises(ProposalRejected) as rejected:
        pic_generator.generate(pic_proposal_request())

    assert any("adapter validation" in error for error in rejected.value.errors)


def test_model_cannot_change_human_fixed_numerical_parameter() -> None:
    document = valid_pic_draft().model_dump(mode="json")
    document["experiment"]["numerical_parameters"]["grid_cells"] = 128
    client = FakeCompletionClient([json.dumps(document)])
    pic_generator = ProposalGenerator(
        client=client,
        adapter=ElectrostaticPICAdapter(),
        max_attempts=1,
    )

    with pytest.raises(ProposalRejected) as rejected:
        pic_generator.generate(pic_proposal_request())

    assert any("fixed numerical parameter" in error for error in rejected.value.errors)


def test_observable_must_resolve_to_evidence_contract() -> None:
    document = valid_pic_draft().model_dump(mode="json")
    document["observable"]["id"] = "observable_unrelated"
    client = FakeCompletionClient([json.dumps(document)])
    pic_generator = ProposalGenerator(
        client=client,
        adapter=ElectrostaticPICAdapter(),
        max_attempts=1,
    )

    with pytest.raises(ProposalRejected) as rejected:
        pic_generator.generate(pic_proposal_request())

    assert any("observable does not match" in error for error in rejected.value.errors)


def test_model_cannot_rename_canonical_physics_coordinates() -> None:
    document = valid_pic_draft().model_dump(mode="json")
    renamed = ["rho_profile", "mean_velocity_profile", "variance_profile"]
    document["hypothesis"]["coordinates"] = renamed
    document["hypothesis"]["formal_predicate"]["matched_coordinates"] = renamed
    client = FakeCompletionClient([json.dumps(document)])
    pic_generator = ProposalGenerator(
        client=client,
        adapter=ElectrostaticPICAdapter(),
        max_attempts=1,
    )

    with pytest.raises(ProposalRejected) as rejected:
        pic_generator.generate(pic_proposal_request())

    assert any("canonical coordinates" in error for error in rejected.value.errors)
