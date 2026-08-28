"""Generate stable public JSON Schemas for typed boundary objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from pydantic import BaseModel

from .adapters.base import CapabilityManifest, NormalizedResult
from .adapters.warpx import (
    WarpXCalibrationPoint,
    WarpXCaseSummary,
    WarpXCompiledCase,
    WarpXExecutionProfile,
    WarpXNumericalConfig,
    WarpXPairSummary,
    WarpXPhysicalConfig,
    WarpXPhysicsQualificationRecord,
    WarpXQualificationRecord,
    WarpXQualifiedScope,
)
from .autonomous_research import (
    CandidateResult,
    ObservablePrediction,
    ProposedToolCall,
    ResearchBudget,
    ResearchCampaignReport,
    ResearchConclusion,
    ResearchDecision,
    ResearchEvidencePolicy,
    ResearchHypothesis,
    ResearchObservation,
    ResearchProblemContract,
    ResearchRelation,
    ResearchToolManifest,
    ResearchToolResult,
)
from .benchmarks.electrostatic_pic import (
    PICCaseResult,
    PICConfig,
    PICMixtureCaseResult,
    PICNumericalConfig,
    PICSufficiencyResult,
)
from .benchmarks.kinetic_sufficiency import KineticSufficiencyResult
from .confirmation import (
    PICConfirmationAttempt,
    PICConfirmationDesign,
    PICConfirmationReport,
)
from .control import ControlDirective
from .discovery import DiscoveryPackage
from .domains.base import (
    DomainDiagnosisSummary,
    DomainEvolutionSummary,
    DomainPluginMetadata,
    DomainRunSummary,
    DomainTemplateSummary,
)
from .domains.kinetic_sufficiency import (
    KineticSufficiencyDiscoveryPackage,
    KineticSufficiencyHypothesisInput,
    KineticSufficiencySolveResult,
)
from .engineering import (
    EngineeringAdjudicationRecord,
    EngineeringCheck,
    EngineeringCheckResult,
    EngineeringContract,
    EngineeringDiffReview,
    EngineeringHoldoutContract,
    EngineeringPatchRecord,
)
from .engineering_agent import (
    EngineeringAgentAttempt,
    EngineeringAgentConfig,
    EngineeringAgentReport,
    EngineeringFileEdit,
    EngineeringPatchProposal,
)
from .lifecycle import CampaignState, LifecycleEvent
from .models import (
    AttemptRecord,
    CampaignCheckpoint,
    Claim,
    DecisionRecord,
    ExperimentSpec,
    HumanIntervention,
    HypothesisNode,
    MatchedPairFormalPredicate,
    RunEvidence,
)
from .mvp_guidance import MVPGuidedCommissioningSpec
from .orchestration import (
    ActionExecution,
    ActionFailureRecord,
    CampaignAction,
    CampaignActionGraph,
    CampaignActionState,
    CampaignBudget,
    MultiActionCampaignReport,
)
from .outbox import DispatchAttempt, ExternalReceipt, OutboxIntent
from .parameters import (
    NumericalAssessment,
    NumericalDiagnostics,
    NumericalGate,
    ParameterSpace,
    ReferenceQualification,
    RunPlan,
)
from .proposals import (
    ModelCallProvenance,
    ProposalDraft,
    ProposalRecord,
    ProposalRequest,
    ProposalValidation,
)
from .research_tools import SubprocessResearchToolConfig
from .search import (
    AIStrategyDraft,
    BlindedSearchReport,
    BlindedSearchRequest,
    CandidateEvaluation,
    SearchStrategy,
    SymmetricMixtureCandidate,
)
from .warpx_campaign import QualifiedWarpXCampaignPackage
from .warpx_confirmation import (
    QualifiedWarpXInstrument,
    WarpXConfirmationAttempt,
    WarpXConfirmationDesign,
    WarpXConfirmationFailure,
    WarpXConfirmationReport,
    WarpXConfirmationResolution,
)

ModelType: TypeAlias = type[BaseModel]

PUBLIC_MODELS: tuple[ModelType, ...] = (
    ResearchHypothesis,
    ResearchRelation,
    ResearchBudget,
    ResearchEvidencePolicy,
    ResearchProblemContract,
    ResearchToolManifest,
    ObservablePrediction,
    ProposedToolCall,
    CandidateResult,
    ResearchConclusion,
    ResearchDecision,
    ResearchToolResult,
    ResearchObservation,
    ResearchCampaignReport,
    SubprocessResearchToolConfig,
    MVPGuidedCommissioningSpec,
    HypothesisNode,
    MatchedPairFormalPredicate,
    ExperimentSpec,
    AttemptRecord,
    RunEvidence,
    Claim,
    DecisionRecord,
    CampaignCheckpoint,
    HumanIntervention,
    CampaignState,
    LifecycleEvent,
    CapabilityManifest,
    NormalizedResult,
    KineticSufficiencyResult,
    DiscoveryPackage,
    DomainPluginMetadata,
    DomainRunSummary,
    DomainTemplateSummary,
    DomainEvolutionSummary,
    DomainDiagnosisSummary,
    KineticSufficiencyHypothesisInput,
    KineticSufficiencySolveResult,
    KineticSufficiencyDiscoveryPackage,
    EngineeringCheck,
    EngineeringCheckResult,
    EngineeringContract,
    EngineeringHoldoutContract,
    EngineeringPatchRecord,
    EngineeringDiffReview,
    EngineeringAdjudicationRecord,
    EngineeringFileEdit,
    EngineeringPatchProposal,
    EngineeringAgentAttempt,
    EngineeringAgentReport,
    EngineeringAgentConfig,
    ProposalRequest,
    ProposalDraft,
    ProposalValidation,
    ModelCallProvenance,
    ProposalRecord,
    ParameterSpace,
    ReferenceQualification,
    RunPlan,
    NumericalDiagnostics,
    NumericalGate,
    NumericalAssessment,
    ControlDirective,
    PICConfig,
    PICNumericalConfig,
    PICCaseResult,
    PICMixtureCaseResult,
    PICSufficiencyResult,
    SymmetricMixtureCandidate,
    BlindedSearchRequest,
    AIStrategyDraft,
    SearchStrategy,
    CandidateEvaluation,
    BlindedSearchReport,
    PICConfirmationDesign,
    PICConfirmationAttempt,
    PICConfirmationReport,
    CampaignAction,
    CampaignBudget,
    CampaignActionGraph,
    ActionExecution,
    ActionFailureRecord,
    CampaignActionState,
    MultiActionCampaignReport,
    OutboxIntent,
    DispatchAttempt,
    ExternalReceipt,
    WarpXExecutionProfile,
    WarpXPhysicalConfig,
    WarpXNumericalConfig,
    WarpXCompiledCase,
    WarpXCaseSummary,
    WarpXPairSummary,
    WarpXQualificationRecord,
    WarpXQualifiedScope,
    WarpXCalibrationPoint,
    WarpXPhysicsQualificationRecord,
    QualifiedWarpXInstrument,
    WarpXConfirmationResolution,
    WarpXConfirmationDesign,
    WarpXConfirmationAttempt,
    WarpXConfirmationFailure,
    WarpXConfirmationReport,
    QualifiedWarpXCampaignPackage,
)


def rendered_schemas() -> dict[str, str]:
    return {
        model.__name__: json.dumps(
            model.model_json_schema(),
            indent=2,
            sort_keys=True,
        )
        + "\n"
        for model in PUBLIC_MODELS
    }


def export_schemas(output: Path, *, check: bool = False) -> list[str]:
    rendered = rendered_schemas()
    mismatches: list[str] = []
    if not check:
        output.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        path = output / f"{name}.schema.json"
        if check:
            if not path.exists() or path.read_text() != content:
                mismatches.append(str(path))
        else:
            path.write_text(content)
    return mismatches
