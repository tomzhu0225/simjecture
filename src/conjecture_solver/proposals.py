"""Typed, deterministic admission gate for model-generated research proposals."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import Field, ValidationError, model_validator

from .adapters.base import CapabilityManifest, SimulatorAdapter
from .ledger import SQLiteEventLedger, StoredEvent
from .llm import CompletionResult, ModelRoute
from .models import (
    ExperimentSpec,
    HypothesisNode,
    HypothesisOrigin,
    ObservableSpec,
    PropositionClass,
    StrictModel,
    new_id,
    utc_now,
)


class ProposalRequest(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    id: str = Field(default_factory=lambda: new_id("proposal_request"))
    research_goal: str = Field(min_length=1)
    allowed_model_families: tuple[str, ...] = Field(min_length=1)
    allowed_action_types: tuple[str, ...] = Field(min_length=1)
    allowed_proposition_classes: tuple[PropositionClass, ...] = Field(min_length=1)
    required_coordinates: tuple[str, ...] = Field(min_length=1)
    allowed_observable_kinds: tuple[str, ...] = Field(min_length=1)
    available_diagnostics: tuple[str, ...] = Field(min_length=1)
    required_diagnostics: tuple[str, ...] = ()
    fixed_parameters: dict[str, float | int | str] = Field(default_factory=dict)
    fixed_numerical_parameters: dict[str, float | int | str] = Field(default_factory=dict)
    additional_constraints: tuple[str, ...] = ()

    @model_validator(mode="after")
    def required_diagnostics_must_be_available(self) -> ProposalRequest:
        if not set(self.required_diagnostics).issubset(self.available_diagnostics):
            raise ValueError("required diagnostics must be included in available diagnostics")
        return self


def planted_proposal_request() -> ProposalRequest:
    """Human-approved envelope for the first live proposal experiment."""

    return ProposalRequest(
        id="proposal_request_kinetic_sufficiency_v1",
        research_goal=(
            "Propose a finite matched-pair test of whether low-order velocity moments "
            "suffice to predict the dominant linear growth rate."
        ),
        allowed_model_families=("linearized_1d_electrostatic_vlasov_poisson",),
        allowed_action_types=("kinetic_sufficiency",),
        allowed_proposition_classes=(PropositionClass.PREDICTIVE_SUFFICIENCY,),
        required_coordinates=("density", "mean_velocity", "variance"),
        allowed_observable_kinds=("dominant_linear_growth_rate",),
        available_diagnostics=("dominant_linear_mode", "distribution_moments"),
        required_diagnostics=("dominant_linear_mode", "distribution_moments"),
        fixed_parameters={"wavenumber": 0.5},
        additional_constraints=(
            "use a declarative proposition, not a research question",
            "include a typed matched-pair formal predicate",
            "label the origin as ai or mixed",
        ),
    )


def pic_proposal_request() -> ProposalRequest:
    """Human-approved envelope for a live proposal targeting the PIC adapter."""

    return ProposalRequest(
        id="proposal_request_electrostatic_pic_v1",
        research_goal=(
            "Propose a finite matched-pair PIC test of whether density, mean velocity, "
            "and variance suffice to predict the effective fundamental-mode growth rate."
        ),
        allowed_model_families=("electrostatic_1d_pic_vlasov_poisson",),
        allowed_action_types=("kinetic_sufficiency",),
        allowed_proposition_classes=(PropositionClass.PREDICTIVE_SUFFICIENCY,),
        required_coordinates=("density", "mean_velocity", "variance"),
        allowed_observable_kinds=("effective_fundamental_growth_rate",),
        available_diagnostics=(
            "dominant_linear_mode",
            "distribution_moments",
            "energy_conservation",
            "gauss_residual",
        ),
        required_diagnostics=(
            "dominant_linear_mode",
            "distribution_moments",
            "energy_conservation",
            "gauss_residual",
        ),
        fixed_parameters={
            "wavenumber": 0.5,
            "perturbation_amplitude": 0.01,
            "stream_drift": 0.9,
        },
        fixed_numerical_parameters={
            "grid_cells": 64,
            "velocity_beams": 256,
            "particles_per_beam": 64,
            "time_step": 0.05,
            "final_time": 20.0,
            "diagnostic_interval": 0.5,
            "seed": 7,
        },
        additional_constraints=(
            "use exactly one hypothesis",
            "use action_type kinetic_sufficiency",
            "use a declarative proposition and typed matched-pair formal predicate",
            "set numerical parameters grid_cells=64, velocity_beams=256, "
            "particles_per_beam=64, time_step=0.05, final_time=20.0, "
            "diagnostic_interval=0.5, and seed=7",
            "require all four available diagnostics",
            "label the hypothesis origin as ai or mixed",
        ),
    )


class ProposalDraft(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    hypothesis: HypothesisNode
    observable: ObservableSpec
    experiment: ExperimentSpec
    rationale: str = Field(min_length=1)
    declared_unknowns: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def forbid_model_from_claiming_human_origin(self) -> ProposalDraft:
        if self.hypothesis.origin is HypothesisOrigin.HUMAN:
            raise ValueError("a model-generated proposal cannot claim human origin")
        return self


class ProposalValidation(StrictModel):
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ModelCallProvenance(StrictModel):
    request_id: str
    model: str
    route: ModelRoute
    route_reason: str
    finish_reason: str
    prompt_template_version: Literal["proposal_v1"] = "proposal_v1"
    prompt_hash: str
    output_schema_hash: str
    response_hash: str
    usage: dict[str, Any] = Field(default_factory=dict)
    admission_errors: tuple[str, ...] = ()
    attempt_number: int = Field(ge=1)
    created_at: datetime = Field(default_factory=utc_now)


class ProposalRecord(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    request: ProposalRequest
    draft: ProposalDraft
    validation: ProposalValidation
    model_calls: tuple[ModelCallProvenance, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def only_admitted_proposals_become_records(self) -> ProposalRecord:
        if not self.validation.valid or self.validation.errors:
            raise ValueError("a proposal record requires a successful admission decision")
        return self


class ProposalRejected(ValueError):
    def __init__(
        self,
        errors: tuple[str, ...],
        model_calls: tuple[ModelCallProvenance, ...],
    ) -> None:
        super().__init__("proposal rejected: " + "; ".join(errors))
        self.errors = errors
        self.model_calls = model_calls


def record_admitted_proposal(
    ledger: SQLiteEventLedger,
    *,
    campaign_id: str,
    record: ProposalRecord,
) -> StoredEvent:
    """Commit a validated proposal without granting it execution authority."""

    return ledger.append(
        campaign_id=campaign_id,
        event_type="proposal_admitted",
        aggregate_type="proposal",
        aggregate_id=record.request.id,
        payload={"proposal_record": record.model_dump(mode="json")},
        idempotency_key=f"{campaign_id}:proposal:{record.request.id}",
    ).event


class CompletionClient(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResult: ...


def validate_proposal(
    request: ProposalRequest,
    draft: ProposalDraft,
    capabilities: CapabilityManifest,
) -> ProposalValidation:
    errors: list[str] = []
    warnings: list[str] = []
    hypothesis = draft.hypothesis
    experiment = draft.experiment
    observable = draft.observable

    if hypothesis.proposition_class not in request.allowed_proposition_classes:
        errors.append("proposition class is outside the human-approved request")
    if hypothesis.domain.model_family not in request.allowed_model_families:
        errors.append("model family is outside the human-approved request")
    if hypothesis.domain.model_family not in capabilities.supported_models:
        errors.append("adapter does not support the proposed model family")
    if hypothesis.coordinates != request.required_coordinates:
        errors.append("hypothesis coordinates do not match the required canonical coordinates")
    if not set(hypothesis.coordinates).issubset(capabilities.supported_coordinates):
        errors.append("adapter does not support every proposed coordinate")
    if observable.semantic_kind not in request.allowed_observable_kinds:
        errors.append("observable semantic kind is outside the human-approved request")
    if observable.semantic_kind not in capabilities.supported_observable_kinds:
        errors.append("adapter does not support the observable semantic kind")
    if experiment.action_type not in request.allowed_action_types:
        errors.append("action type is outside the human-approved request")
    if experiment.action_type not in capabilities.supported_actions:
        errors.append("adapter does not support the proposed action type")
    if hypothesis.id not in experiment.hypothesis_ids:
        errors.append("experiment does not reference the proposed hypothesis")
    if hypothesis.evidence_contract.primary_observable_id != observable.id:
        errors.append("proposal observable does not match the hypothesis evidence contract")
    if abs(hypothesis.evidence_contract.primary_tolerance - observable.tolerance) > 1e-15:
        errors.append("proposal observable tolerance does not match the evidence contract")

    requested_diagnostics = set(experiment.required_diagnostics)
    if not requested_diagnostics.issubset(request.available_diagnostics):
        errors.append("experiment requests diagnostics outside the approved set")
    if not requested_diagnostics.issubset(capabilities.supported_diagnostics):
        errors.append("adapter does not support every required diagnostic")
    if not set(request.required_diagnostics).issubset(requested_diagnostics):
        errors.append("experiment omitted a human-required diagnostic")

    for name, fixed_value in request.fixed_parameters.items():
        if hypothesis.domain.fixed_parameters.get(name) != fixed_value:
            errors.append(f"hypothesis domain changed fixed parameter {name}")
        if experiment.physical_parameters.get(name) != fixed_value:
            errors.append(f"experiment changed fixed parameter {name}")
    for name, fixed_value in request.fixed_numerical_parameters.items():
        if experiment.numerical_parameters.get(name) != fixed_value:
            errors.append(f"experiment changed fixed numerical parameter {name}")

    if hypothesis.formal_predicate is None:
        errors.append("initial AI proposals require a typed formal predicate")
    if hypothesis.proposition_class is PropositionClass.CAUSAL_EXHAUSTIVENESS:
        errors.append("open-world causal-exhaustiveness claims are not admitted initially")
    if len(experiment.hypothesis_ids) > 1:
        warnings.append("the initial slice is optimized for one hypothesis per experiment")

    return ProposalValidation(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))


class ProposalGenerator:
    def __init__(
        self,
        *,
        client: CompletionClient,
        capabilities: CapabilityManifest | None = None,
        adapter: SimulatorAdapter | None = None,
        max_attempts: int = 2,
        max_escalation_attempts: int = 1,
    ) -> None:
        if max_attempts < 1 or max_escalation_attempts < 1:
            raise ValueError("attempt limits must be positive")
        if capabilities is None and adapter is None:
            raise ValueError("proposal generation requires capabilities or an adapter")
        self.client = client
        self.adapter = adapter
        if capabilities is not None:
            self.capabilities = capabilities
        else:
            assert adapter is not None
            self.capabilities = adapter.capabilities()
        self.max_attempts = max_attempts
        self.max_escalation_attempts = max_escalation_attempts

    @staticmethod
    def _initial_messages(request: ProposalRequest) -> list[dict[str, str]]:
        schema = ProposalDraft.model_json_schema()
        return [
            {
                "role": "system",
                "content": (
                    "You propose a falsifiable computational-physics test inside a "
                    "human-approved capability envelope. Return exactly one JSON object "
                    "matching the supplied schema: no Markdown and no commentary. You may "
                    "propose only; do not claim evidence, confirmation, or job execution."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "request": request.model_dump(mode="json"),
                        "output_schema": schema,
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
    ) -> ModelCallProvenance:
        prompt = json.dumps(messages, sort_keys=True, separators=(",", ":"))
        output_schema = json.dumps(
            ProposalDraft.model_json_schema(),
            sort_keys=True,
            separators=(",", ":"),
        )
        return ModelCallProvenance(
            request_id=result.request_id,
            model=result.model,
            route=result.route,
            route_reason=result.route_reason,
            finish_reason=result.finish_reason,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            output_schema_hash=hashlib.sha256(output_schema.encode()).hexdigest(),
            response_hash=hashlib.sha256(result.content.encode()).hexdigest(),
            usage=result.usage,
            attempt_number=attempt_number,
        )

    def generate(
        self,
        request: ProposalRequest,
        *,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
        max_tokens: int = 16384,
    ) -> ProposalRecord:
        messages = self._initial_messages(request)
        calls: list[ModelCallProvenance] = []
        last_errors: tuple[str, ...] = ("model returned no proposal",)

        attempt_limit = (
            self.max_escalation_attempts
            if route is ModelRoute.ESCALATION
            else self.max_attempts
        )
        for attempt_number in range(1, attempt_limit + 1):
            result = self.client.complete(
                messages,
                route=route,
                escalation_reason=escalation_reason,
                max_tokens=max_tokens,
                temperature=0.0,
            )
            calls.append(self._provenance(result, messages, attempt_number))
            if result.finish_reason != "stop":
                last_errors = (f"incomplete completion: {result.finish_reason}",)
            else:
                try:
                    document = json.loads(result.content)
                    draft = ProposalDraft.model_validate(document)
                except (json.JSONDecodeError, ValidationError) as error:
                    last_errors = (f"invalid proposal document: {error}",)
                else:
                    validation = validate_proposal(request, draft, self.capabilities)
                    if validation.valid and self.adapter is not None:
                        adapter_validation = self.adapter.validate(draft.experiment)
                        validation = ProposalValidation(
                            valid=adapter_validation.valid,
                            errors=tuple(
                                f"adapter validation: {error}"
                                for error in adapter_validation.errors
                            ),
                            warnings=(*validation.warnings, *adapter_validation.warnings),
                        )
                    if validation.valid:
                        return ProposalRecord(
                            request=request,
                            draft=draft,
                            validation=validation,
                            model_calls=tuple(calls),
                        )
                    last_errors = validation.errors

            calls[-1] = calls[-1].model_copy(update={"admission_errors": last_errors})

            messages.extend(
                (
                    {"role": "assistant", "content": result.content},
                    {
                        "role": "user",
                        "content": (
                            "The deterministic admission gate rejected the proposal for: "
                            + "; ".join(last_errors)
                            + ". Return a corrected JSON object only."
                        ),
                    },
                )
            )

        raise ProposalRejected(last_errors, tuple(calls))
