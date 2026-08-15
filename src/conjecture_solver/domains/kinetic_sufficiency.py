"""Analytic kinetic-sufficiency domain proving the plugin boundary is reusable."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from ..benchmarks.kinetic_sufficiency import (
    DistributionMoments,
    GaussianComponent,
    GaussianMixture,
    KineticCaseResult,
    build_problem,
    classify_mode,
    moments,
    solve_modes,
)
from ..ledger import SQLiteEventLedger
from ..models import (
    Claim,
    ClaimDisposition,
    EvidenceRole,
    HypothesisNode,
    ObservableSpec,
    PropositionClass,
    RunEvidence,
    StrictModel,
    utc_now,
)
from ..orchestration import (
    ActionContext,
    ActionExecution,
    ActionExecutionError,
    ActionFailureKind,
    ActionHandler,
    ActionOrigin,
    CampaignAction,
    CampaignActionGraph,
    CampaignBudget,
    MultiActionCampaignRunner,
)
from ..semantics import MatchedObservation, SufficiencyWitness, evaluate_predictive_sufficiency
from .base import DomainPluginMetadata, DomainRunSummary, DomainTemplateSummary

KINETIC_SUFFICIENCY_MODEL = "linearized_1d_electrostatic_vlasov_poisson"
KINETIC_SUFFICIENCY_ACTION = "kinetic_sufficiency_autonomous_solve"
KINETIC_SUFFICIENCY_OUTPUT = "kinetic_sufficiency_discovery_package"


def _canonical_hash(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class KineticSufficiencyHypothesisInput(StrictModel):
    """A bounded matched-pair hypothesis accepted by the analytic plugin."""

    schema_version: Literal["0.1.0"] = "0.1.0"
    hypothesis: HypothesisNode
    observable: ObservableSpec
    wavenumber: float = Field(gt=0)
    left_name: str = Field(min_length=1)
    left_distribution: GaussianMixture
    right_name: str = Field(min_length=1)
    right_distribution: GaussianMixture
    residual_tolerance: float = Field(default=1e-8, gt=0, le=1e-4)

    @model_validator(mode="after")
    def admitted_contract(self) -> KineticSufficiencyHypothesisInput:
        hypothesis = self.hypothesis
        formal = hypothesis.formal_predicate
        checks = {
            "predictive_sufficiency_proposition": (
                hypothesis.proposition_class is PropositionClass.PREDICTIVE_SUFFICIENCY
            ),
            "installed_model_family": (hypothesis.domain.model_family == KINETIC_SUFFICIENCY_MODEL),
            "matched_moment_coordinates": (
                hypothesis.coordinates == ("density", "mean_velocity", "variance")
            ),
            "formal_predicate_present": formal is not None,
            "observable_round_trip": (
                hypothesis.evidence_contract.primary_observable_id == self.observable.id
            ),
            "domain_wavenumber_round_trip": (
                abs(
                    float(hypothesis.domain.fixed_parameters.get("wavenumber", -1.0))
                    - self.wavenumber
                )
                <= 1e-12
            ),
            "distinct_case_names": self.left_name != self.right_name,
        }
        if formal is not None:
            checks["formal_observable_round_trip"] = (
                formal.outcome_observable_id == self.observable.id
            )
            checks["formal_coordinate_round_trip"] = (
                formal.matched_coordinates == hypothesis.coordinates
            )
        left = moments(self.left_distribution)
        right = moments(self.right_distribution)
        coordinate_tolerance = formal.coordinate_tolerance if formal is not None else 0.0
        checks["input_pair_matches_declared_coordinates"] = all(
            abs(getattr(left, coordinate) - getattr(right, coordinate)) <= coordinate_tolerance
            for coordinate in hypothesis.coordinates
        )
        failed = sorted(name for name, passed in checks.items() if not passed)
        if failed:
            raise ValueError(
                "kinetic-sufficiency hypothesis is outside the installed contract: "
                + ", ".join(failed)
            )
        return self

    @property
    def input_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json"))


def default_kinetic_sufficiency_hypothesis_input() -> KineticSufficiencyHypothesisInput:
    hypothesis, observable = build_problem()
    drift = 0.9
    component_sigma = float((1.0 - drift**2) ** 0.5)
    return KineticSufficiencyHypothesisInput(
        hypothesis=hypothesis,
        observable=observable,
        wavenumber=0.5,
        left_name="unit_variance_maxwellian",
        left_distribution=GaussianMixture(
            components=(GaussianComponent(weight=1.0, drift=0.0, sigma=1.0),)
        ),
        right_name="matched_moment_symmetric_two_stream",
        right_distribution=GaussianMixture(
            components=(
                GaussianComponent(weight=0.5, drift=-drift, sigma=component_sigma),
                GaussianComponent(weight=0.5, drift=drift, sigma=component_sigma),
            )
        ),
    )


class KineticSufficiencySolveResult(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    input_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    left: KineticCaseResult
    right: KineticCaseResult
    moments_match: bool
    qualification_checks: dict[str, bool]
    qualified: bool
    witness: SufficiencyWitness

    @model_validator(mode="after")
    def coherent_result(self) -> KineticSufficiencySolveResult:
        if not self.qualification_checks:
            raise ValueError("analytic qualification must declare checks")
        if self.qualified != all(self.qualification_checks.values()):
            raise ValueError("analytic qualification must equal all declared checks")
        if self.witness.coordinates_match != self.moments_match:
            raise ValueError("witness coordinate decision differs from the measured moments")
        return self


class KineticSufficiencyDiscoveryPackage(StrictModel):
    schema_version: Literal["0.1.0"] = "0.1.0"
    domain_plugin: Literal["kinetic-sufficiency"] = "kinetic-sufficiency"
    domain_plugin_version: Literal["1.0.0"] = "1.0.0"
    campaign_id: str
    hypothesis_input: KineticSufficiencyHypothesisInput
    result: KineticSufficiencySolveResult
    evidence: tuple[RunEvidence, RunEvidence]
    claim: Claim
    authorized_analysis_units: Literal[1] = 1
    consumed_analysis_units: Literal[1] = 1
    provenance_event_hashes: tuple[str, ...] = Field(min_length=1)
    generated_at: datetime
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def coherent_package(self) -> KineticSufficiencyDiscoveryPackage:
        if self.result.input_hash != self.hypothesis_input.input_hash:
            raise ValueError("kinetic result belongs to another hypothesis input")
        if self.result.witness.hypothesis_id != self.hypothesis_input.hypothesis.id:
            raise ValueError("kinetic witness names another hypothesis")
        if self.claim.hypothesis_id != self.hypothesis_input.hypothesis.id:
            raise ValueError("kinetic claim names another hypothesis")
        if self.claim.evidence_ids != tuple(item.id for item in self.evidence):
            raise ValueError("kinetic claim must cite exactly the matched-pair evidence")
        expected = (
            ClaimDisposition.REFUTED_WITHIN_MODEL
            if self.result.qualified and self.result.witness.falsifies
            else ClaimDisposition.UNRESOLVED
        )
        if self.claim.disposition is not expected:
            raise ValueError("kinetic claim disposition does not follow its witness")
        if self.package_hash != self.calculated_hash():
            raise ValueError("kinetic discovery package hash does not match its content")
        return self

    def calculated_hash(self) -> str:
        return _canonical_hash(self.model_dump(mode="json", exclude={"package_hash"}))

    def verify_hash(self) -> bool:
        return self.package_hash == self.calculated_hash()

    @classmethod
    def create(cls, **values: object) -> KineticSufficiencyDiscoveryPackage:
        provisional = cls.model_construct(package_hash="0" * 64, **values)
        return cls.model_validate(
            {
                **provisional.model_dump(mode="json", exclude={"package_hash"}),
                "package_hash": provisional.calculated_hash(),
            }
        )

    def write(self, output_directory: str | Path) -> Path:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        path = output / "kinetic_sufficiency_discovery_package.json"
        temporary = output / ".kinetic_sufficiency_discovery_package.json.tmp"
        temporary.write_text(self.model_dump_json(indent=2) + "\n")
        os.replace(temporary, path)
        return path

    @classmethod
    def read_verified(cls, path: str | Path) -> KineticSufficiencyDiscoveryPackage:
        package = cls.model_validate_json(Path(path).read_text())
        if not package.verify_hash():
            raise ValueError("kinetic discovery package failed hash verification")
        return package


def _coordinates(value: DistributionMoments) -> dict[str, float]:
    return {
        "density": value.density,
        "mean_velocity": value.mean_velocity,
        "variance": value.variance,
    }


def solve_kinetic_sufficiency(
    hypothesis_input: KineticSufficiencyHypothesisInput,
) -> KineticSufficiencySolveResult:
    left_moments = moments(hypothesis_input.left_distribution)
    right_moments = moments(hypothesis_input.right_distribution)
    left_mode = solve_modes(
        hypothesis_input.left_distribution,
        wavenumber=hypothesis_input.wavenumber,
        residual_tolerance=hypothesis_input.residual_tolerance,
    )[0]
    right_mode = solve_modes(
        hypothesis_input.right_distribution,
        wavenumber=hypothesis_input.wavenumber,
        residual_tolerance=hypothesis_input.residual_tolerance,
    )[0]
    left_id = f"evidence_{hypothesis_input.input_hash[:16]}_left"
    right_id = f"evidence_{hypothesis_input.input_hash[:16]}_right"
    formal = hypothesis_input.hypothesis.formal_predicate
    if formal is None:  # protected by input admission, retained for static narrowing
        raise ValueError("matched-pair hypothesis requires a formal predicate")
    witness = evaluate_predictive_sufficiency(
        hypothesis_input.hypothesis,
        MatchedObservation(
            evidence_id=left_id,
            coordinates=_coordinates(left_moments),
            outcome=left_mode.growth_rate,
            outcome_uncertainty=left_mode.dielectric_residual,
        ),
        MatchedObservation(
            evidence_id=right_id,
            coordinates=_coordinates(right_moments),
            outcome=right_mode.growth_rate,
            outcome_uncertainty=right_mode.dielectric_residual,
        ),
        coordinate_atol=formal.coordinate_tolerance,
    )
    checks = {
        "left_dielectric_root_residual": (
            left_mode.dielectric_residual <= hypothesis_input.residual_tolerance
        ),
        "right_dielectric_root_residual": (
            right_mode.dielectric_residual <= hypothesis_input.residual_tolerance
        ),
        "declared_coordinates_match": witness.coordinates_match,
    }
    return KineticSufficiencySolveResult(
        input_hash=hypothesis_input.input_hash,
        left=KineticCaseResult(
            name=hypothesis_input.left_name,
            distribution=hypothesis_input.left_distribution,
            moments=left_moments,
            mode=left_mode,
            classification=classify_mode(left_mode),
        ),
        right=KineticCaseResult(
            name=hypothesis_input.right_name,
            distribution=hypothesis_input.right_distribution,
            moments=right_moments,
            mode=right_mode,
            classification=classify_mode(right_mode),
        ),
        moments_match=witness.coordinates_match,
        qualification_checks=checks,
        qualified=all(checks.values()),
        witness=witness,
    )


class KineticSufficiencySolveActionHandler:
    def execute(
        self,
        context: ActionContext,
        action: CampaignAction,
        dependencies: dict[str, ActionExecution],
    ) -> ActionExecution:
        if dependencies:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                "bounded kinetic solve must not receive dependency outputs",
            )
        try:
            hypothesis_input = KineticSufficiencyHypothesisInput.model_validate(
                action.payload["hypothesis_input"]
            )
            result = solve_kinetic_sufficiency(hypothesis_input)
        except (KeyError, TypeError, ValueError) as error:
            raise ActionExecutionError(
                ActionFailureKind.SPECIFICATION,
                f"invalid autonomous kinetic-sufficiency solve: {error}",
            ) from error
        eligible = result.qualified
        evidence = (
            RunEvidence(
                id=result.witness.left_evidence_id,
                source_attempt_id=f"analytic_{hypothesis_input.input_hash[:16]}",
                role=EvidenceRole.CONFIRMATION,
                eligible=eligible,
                eligibility_reason=(
                    "validated analytic dielectric root from a preregistered matched pair"
                    if eligible
                    else "analytic root or matched-coordinate qualification failed"
                ),
                observable_values={hypothesis_input.observable.id: result.left.mode.growth_rate},
                uncertainties={
                    hypothesis_input.observable.id: result.left.mode.dielectric_residual
                },
                independence_group=f"kinetic_pair_{hypothesis_input.input_hash[:16]}_left",
            ),
            RunEvidence(
                id=result.witness.right_evidence_id,
                source_attempt_id=f"analytic_{hypothesis_input.input_hash[:16]}",
                role=EvidenceRole.CONFIRMATION,
                eligible=eligible,
                eligibility_reason=(
                    "validated analytic dielectric root from a preregistered matched pair"
                    if eligible
                    else "analytic root or matched-coordinate qualification failed"
                ),
                observable_values={hypothesis_input.observable.id: result.right.mode.growth_rate},
                uncertainties={
                    hypothesis_input.observable.id: result.right.mode.dielectric_residual
                },
                independence_group=f"kinetic_pair_{hypothesis_input.input_hash[:16]}_right",
            ),
        )
        disposition = (
            ClaimDisposition.REFUTED_WITHIN_MODEL
            if eligible and result.witness.falsifies
            else ClaimDisposition.UNRESOLVED
        )
        claim = Claim(
            id=f"claim_{hypothesis_input.input_hash[:20]}",
            hypothesis_id=hypothesis_input.hypothesis.id,
            statement=(
                "The declared matched pair refutes predictive sufficiency within the "
                "installed linear kinetic model."
                if disposition is ClaimDisposition.REFUTED_WITHIN_MODEL
                else "The declared finite matched pair does not resolve predictive sufficiency."
            ),
            disposition=disposition,
            scope=hypothesis_input.hypothesis.domain.description,
            evidence_ids=tuple(item.id for item in evidence),
            limitations=(
                "A finite matched pair can refute but cannot establish a universal "
                "predictive-sufficiency proposition.",
                "The analytic instrument is restricted to Gaussian-mixture equilibria.",
            ),
        )
        events = context.ledger.load(context.campaign_id)
        package = KineticSufficiencyDiscoveryPackage.create(
            campaign_id=context.campaign_id,
            hypothesis_input=hypothesis_input,
            result=result,
            evidence=evidence,
            claim=claim,
            provenance_event_hashes=tuple(event.event_hash for event in events),
            generated_at=utc_now(),
        )
        output: dict[str, object] = {KINETIC_SUFFICIENCY_OUTPUT: package.model_dump(mode="json")}
        return ActionExecution(
            action_id=action.id,
            evidence_eligible=eligible,
            output=output,
            output_hash=_canonical_hash(output),
        )


def build_kinetic_sufficiency_solve_graph(
    hypothesis_input: KineticSufficiencyHypothesisInput,
) -> CampaignActionGraph:
    action = CampaignAction(
        id="action_kinetic_sufficiency_autonomous_solve_v1",
        action_type=KINETIC_SUFFICIENCY_ACTION,
        purpose=(
            "evaluate a preregistered matched pair with a qualified analytic "
            "dielectric-root instrument and export a self-verifying package"
        ),
        evidence_role=EvidenceRole.DISCOVERY,
        independence_group="bounded_kinetic_sufficiency_solver_v1",
        origin=ActionOrigin.DETERMINISTIC,
        budget_units=1.0,
        payload={"hypothesis_input": hypothesis_input.model_dump(mode="json")},
    )
    return CampaignActionGraph(
        id="action_graph_kinetic_sufficiency_autonomous_solve_v1",
        actions=(action,),
        budget=CampaignBudget(total_units=1.0, unit_name="analytic_matched_pair_evaluation"),
    )


def kinetic_sufficiency_solve_handlers() -> dict[str, ActionHandler]:
    return {KINETIC_SUFFICIENCY_ACTION: KineticSufficiencySolveActionHandler()}


class KineticSufficiencyDomainPlugin:
    metadata = DomainPluginMetadata(
        name="kinetic-sufficiency",
        version="1.0.0",
        description="Matched-moment linear Vlasov-Poisson predictive sufficiency",
        hypothesis_schema="KineticSufficiencyHypothesisInput",
        package_schema="KineticSufficiencyDiscoveryPackage",
        model_families=(KINETIC_SUFFICIENCY_MODEL,),
        proposition_classes=(PropositionClass.PREDICTIVE_SUFFICIENCY,),
    )

    def configure_solve_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("hypothesis")
        parser.add_argument("--campaign-id", default="campaign_kinetic_sufficiency_autonomous_v1")
        parser.add_argument("--ledger", default="kinetic_sufficiency_autonomous.sqlite3")
        parser.add_argument("--output", default="artifacts/kinetic_sufficiency_autonomous")

    def configure_template_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--output", default="kinetic_sufficiency_hypothesis.json")

    def solve(self, args: argparse.Namespace) -> DomainRunSummary:
        hypothesis_input = KineticSufficiencyHypothesisInput.model_validate_json(
            Path(args.hypothesis).read_text()
        )
        graph = build_kinetic_sufficiency_solve_graph(hypothesis_input)
        with SQLiteEventLedger(args.ledger) as ledger:
            report = MultiActionCampaignRunner(
                campaign_id=args.campaign_id,
                ledger=ledger,
                graph=graph,
                handlers=kinetic_sufficiency_solve_handlers(),
            ).run()
            action = report.action_states[0]
            if action.execution is None:
                detail = (
                    action.failure.detail if action.failure is not None else action.block_reason
                )
                raise RuntimeError(
                    f"autonomous kinetic-sufficiency action did not complete: {detail}"
                )
            package = KineticSufficiencyDiscoveryPackage.model_validate(
                action.execution.output[KINETIC_SUFFICIENCY_OUTPUT]
            )
            path = package.write(args.output)
            if not ledger.verify_chain(args.campaign_id):
                raise RuntimeError(
                    "autonomous kinetic-sufficiency ledger hash chain failed verification"
                )
        return DomainRunSummary(
            domain=self.metadata.name,
            campaign_id=args.campaign_id,
            disposition=package.claim.disposition.value,
            package_hash=package.package_hash,
            package_path=str(path),
            metrics={
                "qualified": package.result.qualified,
                "moments_match": package.result.moments_match,
                "outcome_separation": package.result.witness.outcome_separation,
                "authorized_analysis_units": package.authorized_analysis_units,
                "consumed_analysis_units": package.consumed_analysis_units,
            },
        )

    def write_template(self, args: argparse.Namespace) -> DomainTemplateSummary:
        template = default_kinetic_sufficiency_hypothesis_input()
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(template.model_dump_json(indent=2) + "\n")
        os.replace(temporary, path)
        return DomainTemplateSummary(
            domain=self.metadata.name,
            template_path=str(path),
            metrics={"authorized_analysis_units": 1},
        )

    def recognizes_package(self, payload: dict[str, Any]) -> bool:
        return payload.get("domain_plugin") == self.metadata.name

    def read_verified_package(self, path: str | Path) -> KineticSufficiencyDiscoveryPackage:
        return KineticSufficiencyDiscoveryPackage.read_verified(path)
