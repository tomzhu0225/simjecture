"""Registered handlers for the first multi-action scientific campaign."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from pydantic import ValidationError

from .adapters.base import SimulatorAdapter
from .benchmarks.electrostatic_pic import PICNumericalConfig
from .benchmarks.kinetic_sufficiency import build_problem
from .confirmation import (
    PICConfirmationDesign,
    PICConfirmationRunner,
    confirmation_design_from_search,
)
from .models import Claim, ClaimDisposition, EvidenceRole, RunEvidence
from .orchestration import (
    ActionContext,
    ActionExecution,
    ActionExecutionError,
    ActionFailureKind,
    ActionHandler,
    ActionOrigin,
    CampaignAction,
    CampaignActionGraph,
    CampaignBudget,
)
from .outbox import OutboxCrashPoint
from .search import (
    BlindedSearchReport,
    BlindedSearchRequest,
    BlindedSearchRunner,
    SearchStrategy,
    baseline_strategies,
)
from .warpx_confirmation import (
    InjectedWarpXConfirmationCrash,
    QualifiedWarpXInstrument,
    WarpXConfirmationCrashPoint,
    WarpXConfirmationDesign,
    WarpXConfirmationDisposition,
    WarpXConfirmationReport,
    WarpXConfirmationRunner,
    default_warpx_confirmation_design,
)

BLINDED_SEARCH_ACTION = "blinded_analytic_search"
PIC_CONFIRMATION_ACTION = "frozen_pic_confirmation"
QUALIFIED_WARPX_CONFIRMATION_ACTION = "qualified_warpx_confirmation"


def _hash_output(output: dict[str, object]) -> str:
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class BlindedSearchActionHandler:
    def execute(
        self,
        context: ActionContext,
        action: CampaignAction,
        dependencies: dict[str, ActionExecution],
    ) -> ActionExecution:
        if dependencies:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                "blinded search action must not receive dependency outputs",
            )
        try:
            request = BlindedSearchRequest.model_validate(action.payload["request"])
            strategies = tuple(
                SearchStrategy.model_validate(strategy) for strategy in action.payload["strategies"]
            )
        except (KeyError, TypeError, ValidationError) as error:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                f"invalid blinded-search payload: {error}",
            ) from error
        expected_units = request.evaluations_per_method * len(request.comparison_methods)
        if abs(action.budget_units - expected_units) > 1e-12:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                "search budget units must equal the number of candidate evaluations",
            )
        try:
            report = BlindedSearchRunner(
                campaign_id=context.campaign_id,
                ledger=context.ledger,
                request=request,
                strategies=strategies,
            ).run()
        except ValueError as error:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                f"blinded search was rejected: {error}",
            ) from error
        output: dict[str, object] = {"search_report": report.model_dump(mode="json")}
        return ActionExecution(
            action_id=action.id,
            evidence_eligible=report.confirmation_candidate_id is not None,
            output=output,
            output_hash=_hash_output(output),
        )


class PICConfirmationActionHandler:
    def execute(
        self,
        context: ActionContext,
        action: CampaignAction,
        dependencies: dict[str, ActionExecution],
    ) -> ActionExecution:
        source_action_id = action.payload.get("source_action_id")
        if not isinstance(source_action_id, str) or source_action_id not in dependencies:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                "confirmation source_action_id must name a completed dependency",
            )
        try:
            search_report = BlindedSearchReport.model_validate(
                dependencies[source_action_id].output["search_report"]
            )
            design = confirmation_design_from_search(search_report)
            design = PICConfirmationDesign.model_validate(
                {
                    **design.model_dump(mode="json"),
                    "seeds": action.payload["seeds"],
                    "velocity_beams": action.payload["velocity_beams"],
                    "base_config": action.payload["base_config"],
                }
            )
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                f"invalid PIC confirmation payload: {error}",
            ) from error
        expected_units = 2 * len(design.configurations())
        if abs(action.budget_units - expected_units) > 1e-12:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                "confirmation budget units must equal the number of PIC case executions",
            )
        report = PICConfirmationRunner(
            campaign_id=context.campaign_id,
            ledger=context.ledger,
            design=design,
        ).run()
        output: dict[str, object] = {"confirmation_report": report.model_dump(mode="json")}
        return ActionExecution(
            action_id=action.id,
            evidence_eligible=all(attempt.eligible for attempt in report.attempts),
            output=output,
            output_hash=_hash_output(output),
        )


def _warpx_evidence_and_claim(
    context: ActionContext,
    report: WarpXConfirmationReport,
) -> tuple[tuple[RunEvidence, ...], Claim]:
    hypothesis, _ = build_problem()
    evidence: list[RunEvidence] = []
    group = f"warpx_picmi_qualified_{report.design.qualification_hash[:16]}"
    for attempt in report.attempts:
        observables = attempt.normalized_result.observables
        identity = hashlib.sha256(
            f"{context.campaign_id}:{attempt.resolution_id}:{attempt.seed}".encode()
        ).hexdigest()[:20]
        evidence.append(
            RunEvidence(
                id=f"evidence_{identity}",
                source_attempt_id=(
                    f"attempt_warpx_confirmation_{attempt.resolution_id}_seed_{attempt.seed}_v1"
                ),
                role=EvidenceRole.CONFIRMATION,
                eligible=attempt.confirmed,
                eligibility_reason=(
                    "fresh qualified WarpX pair passed every preregistered confirmation gate"
                    if attempt.confirmed
                    else "WarpX pair failed one or more preregistered confirmation gates"
                ),
                observable_values={
                    "maxwellian_growth_rate": float(observables["maxwellian_growth_rate"]),
                    "two_stream_growth_rate": float(observables["two_stream_growth_rate"]),
                    "outcome_separation": float(observables["outcome_separation"]),
                },
                independence_group=group,
                artifact_hashes=attempt.normalized_result.artifact_hashes,
            )
        )
    for failure in report.failures:
        identity = hashlib.sha256(
            f"{context.campaign_id}:{failure.resolution_id}:{failure.seed}".encode()
        ).hexdigest()[:20]
        evidence.append(
            RunEvidence(
                id=f"evidence_{identity}",
                source_attempt_id=f"attempt_{failure.experiment_id.removeprefix('experiment_')}",
                role=EvidenceRole.CONFIRMATION,
                eligible=False,
                eligibility_reason=(
                    f"{failure.kind.value} execution failure is not physical evidence: "
                    f"{failure.detail}"
                ),
                observable_values={},
                independence_group=group,
            )
        )
    completed_event = next(
        event
        for event in reversed(context.ledger.load(context.campaign_id))
        if event.event_type == "qualified_warpx_confirmation_completed"
    )
    refuted = report.disposition is WarpXConfirmationDisposition.CONFIRMED
    evidence_ids = tuple(item.id for item in evidence)
    claim = Claim(
        id=f"claim_{hashlib.sha256(context.campaign_id.encode()).hexdigest()[:20]}",
        hypothesis_id=hypothesis.id,
        statement=(
            "The low-order-moment predictive-sufficiency hypothesis is independently "
            "refuted by the qualified WarpX confirmation matrix."
            if refuted
            else "The qualified WarpX confirmation matrix did not resolve the hypothesis."
        ),
        disposition=(
            ClaimDisposition.REFUTED_WITHIN_MODEL if refuted else ClaimDisposition.UNRESOLVED
        ),
        scope=(
            "the registered one-dimensional electrostatic WarpX/PICMI model at "
            "k lambda_D = 0.5 and the frozen qualified parameter envelope"
        ),
        evidence_ids=evidence_ids,
        limitations=(
            "all confirmation attempts share one WarpX implementation and estimator family",
            "the result does not establish sufficiency or insufficiency outside the "
            "qualified scope",
            "finite seeds and two resolutions bound, but do not eliminate, sampling uncertainty",
        ),
        created_at=datetime.fromisoformat(completed_event.created_at),
    )
    return tuple(evidence), claim


class QualifiedWarpXConfirmationActionHandler:
    def __init__(
        self,
        *,
        instrument: QualifiedWarpXInstrument,
        adapter: SimulatorAdapter,
        crash_at: WarpXConfirmationCrashPoint | None = None,
        crash_ordinal: int | None = None,
        outbox_crash_at: OutboxCrashPoint | None = None,
    ) -> None:
        self.instrument = instrument
        self.adapter = adapter
        self.crash_at = crash_at
        self.crash_ordinal = crash_ordinal
        self.outbox_crash_at = outbox_crash_at

    def execute(
        self,
        context: ActionContext,
        action: CampaignAction,
        dependencies: dict[str, ActionExecution],
    ) -> ActionExecution:
        source_action_id = action.payload.get("source_action_id")
        if not isinstance(source_action_id, str) or source_action_id not in dependencies:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                "WarpX confirmation source_action_id must name a completed dependency",
            )
        try:
            if action.payload["instrument_id"] != self.instrument.id:
                raise ValueError("action names a different registered instrument")
            if action.payload["qualification_hash"] != self.instrument.qualification_hash:
                raise ValueError("action qualification hash differs from the instrument")
            search_report = BlindedSearchReport.model_validate(
                dependencies[source_action_id].output["search_report"]
            )
            design = WarpXConfirmationDesign.model_validate(action.payload["design"])
            if search_report.confirmation_candidate is None:
                raise ValueError("analytic discovery did not freeze a confirmation candidate")
            if search_report.confirmation_candidate != design.physical.candidate:
                raise ValueError(
                    "frozen analytic candidate is outside the exact qualified WarpX scope"
                )
            expected_units = 2 * len(design.seeds) * len(design.resolutions)
            if abs(action.budget_units - expected_units) > 1e-12:
                raise ValueError(
                    "WarpX budget units must equal the paired case executions in the matrix"
                )
            report = WarpXConfirmationRunner(
                campaign_id=context.campaign_id,
                ledger=context.ledger,
                instrument=self.instrument,
                adapter=self.adapter,
                design=design,
                control=context.control,
                crash_at=self.crash_at,
                crash_ordinal=self.crash_ordinal,
                outbox_crash_at=self.outbox_crash_at,
            ).run()
        except (KeyError, TypeError, ValueError, ValidationError) as error:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                f"invalid qualified WarpX confirmation action: {error}",
            ) from error
        except InjectedWarpXConfirmationCrash:
            raise
        evidence, claim = _warpx_evidence_and_claim(context, report)
        output: dict[str, object] = {
            "instrument_id": self.instrument.id,
            "qualification_hash": self.instrument.qualification_hash,
            "confirmation_report": report.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "claim": claim.model_dump(mode="json"),
        }
        return ActionExecution(
            action_id=action.id,
            evidence_eligible=(
                report.disposition is WarpXConfirmationDisposition.CONFIRMED
                and bool(evidence)
                and all(item.eligible for item in evidence)
            ),
            output=output,
            output_hash=_hash_output(output),
            artifact_hashes=tuple(
                artifact for item in evidence for artifact in item.artifact_hashes
            ),
        )


def blinded_campaign_handlers() -> dict[str, ActionHandler]:
    return {
        BLINDED_SEARCH_ACTION: BlindedSearchActionHandler(),
        PIC_CONFIRMATION_ACTION: PICConfirmationActionHandler(),
    }


def qualified_warpx_campaign_handlers(
    *,
    instrument: QualifiedWarpXInstrument,
    adapter: SimulatorAdapter,
    crash_at: WarpXConfirmationCrashPoint | None = None,
    crash_ordinal: int | None = None,
    outbox_crash_at: OutboxCrashPoint | None = None,
) -> dict[str, ActionHandler]:
    return {
        BLINDED_SEARCH_ACTION: BlindedSearchActionHandler(),
        QUALIFIED_WARPX_CONFIRMATION_ACTION: QualifiedWarpXConfirmationActionHandler(
            instrument=instrument,
            adapter=adapter,
            crash_at=crash_at,
            crash_ordinal=crash_ordinal,
            outbox_crash_at=outbox_crash_at,
        ),
    }


def build_qualified_warpx_campaign_graph(
    request: BlindedSearchRequest,
    ai_strategy: SearchStrategy,
    instrument: QualifiedWarpXInstrument,
) -> CampaignActionGraph:
    strategies = (ai_strategy, *baseline_strategies(request))
    analytic_evaluations = request.evaluations_per_method * len(request.comparison_methods)
    design = default_warpx_confirmation_design(instrument.qualification)
    warpx_case_executions = 2 * len(design.seeds) * len(design.resolutions)
    discovery = CampaignAction(
        id="action_blinded_analytic_discovery_v1",
        action_type=BLINDED_SEARCH_ACTION,
        purpose="select and analytically evaluate a blinded matched-moment candidate batch",
        evidence_role=EvidenceRole.DISCOVERY,
        independence_group="analytic_gaussian_mixture_dispersion_solver_v1",
        origin=ActionOrigin.MIXED,
        budget_units=float(analytic_evaluations),
        payload={
            "request": request.model_dump(mode="json"),
            "strategies": [strategy.model_dump(mode="json") for strategy in strategies],
        },
    )
    confirmation = CampaignAction(
        id="action_qualified_warpx_confirmation_v1",
        action_type=QUALIFIED_WARPX_CONFIRMATION_ACTION,
        purpose=(
            "test the frozen analytic witness using the registered qualified WarpX "
            "instrument on fresh seeds and two resolutions"
        ),
        dependencies=(discovery.id,),
        evidence_role=EvidenceRole.CONFIRMATION,
        independence_group=f"qualified_warpx_{instrument.qualification_hash[:16]}",
        origin=ActionOrigin.DETERMINISTIC,
        budget_units=float(warpx_case_executions),
        payload={
            "source_action_id": discovery.id,
            "instrument_id": instrument.id,
            "qualification_hash": instrument.qualification_hash,
            "design": design.model_dump(mode="json"),
        },
    )
    return CampaignActionGraph(
        id="action_graph_blinded_qualified_warpx_confirmation_v1",
        actions=(discovery, confirmation),
        budget=CampaignBudget(
            total_units=float(analytic_evaluations + warpx_case_executions),
            unit_name="physics_case_evaluation",
        ),
    )


def build_blinded_multi_action_graph(
    request: BlindedSearchRequest,
    ai_strategy: SearchStrategy,
) -> CampaignActionGraph:
    strategies = (ai_strategy, *baseline_strategies(request))
    analytic_evaluations = request.evaluations_per_method * len(request.comparison_methods)
    seeds = (1, 7, 19)
    velocity_beams = (192, 384)
    pic_case_executions = 2 * len(seeds) * len(velocity_beams)
    discovery = CampaignAction(
        id="action_blinded_analytic_discovery_v1",
        action_type=BLINDED_SEARCH_ACTION,
        purpose="select and analytically evaluate a blinded matched-moment candidate batch",
        evidence_role=EvidenceRole.DISCOVERY,
        independence_group="analytic_gaussian_mixture_dispersion_solver_v1",
        origin=ActionOrigin.MIXED,
        budget_units=float(analytic_evaluations),
        payload={
            "request": request.model_dump(mode="json"),
            "strategies": [strategy.model_dump(mode="json") for strategy in strategies],
        },
    )
    confirmation = CampaignAction(
        id="action_frozen_pic_confirmation_v1",
        action_type=PIC_CONFIRMATION_ACTION,
        purpose="confirm the frozen AI witness with fresh independent PIC attempts",
        dependencies=(discovery.id,),
        evidence_role=EvidenceRole.CONFIRMATION,
        independence_group="electrostatic_pic_inverse_cdf_quiet_start_v1",
        origin=ActionOrigin.DETERMINISTIC,
        budget_units=float(pic_case_executions),
        payload={
            "source_action_id": discovery.id,
            "seeds": list(seeds),
            "velocity_beams": list(velocity_beams),
            "base_config": PICNumericalConfig().model_dump(mode="json"),
        },
    )
    return CampaignActionGraph(
        id="action_graph_blinded_discovery_confirmation_v1",
        actions=(discovery, confirmation),
        budget=CampaignBudget(
            total_units=float(analytic_evaluations + pic_case_executions),
            unit_name="physics_case_evaluation",
        ),
    )
