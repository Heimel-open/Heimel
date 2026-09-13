"""
VAIG — VALO AI Integrity Gateway
Runtime governance layer for LLM inference. Apache 2.0.

Quick start:
    from vaig import VAIGEnsemble
    vaig = VAIGEnsemble()
    result = vaig.evaluate(prompt, response)
    print(result)

Full stack (L1–L8):
    from vaig import VAIGOrchestrator, RecoveryManager, CAKM, CouncilQueue, DeltaBoxSandbox
    orch = VAIGOrchestrator()
    result = orch.evaluate(prompt, response, session_id="sess-abc")
"""

from vaig.aggregation import (
    AggregationMode,
    AggregationPolicy,
    AggregationResult,
    aggregate_instrument_results,
)
from vaig.evidence_intake import (
    ClaimAdmissibilityBinding,
    ClaimDisposition,
    ClaimMateriality,
    CriterionKind,
    CriterionVerificationBinding,
    EvidenceIntakeAssessment,
    EvidenceIntakePolicy,
    EvidenceIntakeRequest,
    EvidenceIntakeState,
    EvidencePackageBinding,
    VersionedArtifactRef,
    WorkflowVerificationBinding,
    assess_evidence_intake,
)
from vaig.model_signals import ModelSignalBundle
from vaig.ensemble import VAIGEnsemble, ValidationResult, DistrustLevel
from vaig.evaluation_report import (
    EvaluationReport,
    InstrumentSlotReport,
    ReportDisposition,
    build_evaluation_report,
)
from vaig.orchestrator import VAIGOrchestrator, OrchestratorResult
from vaig.worm import WORMLog
from vaig.recovery import RecoveryManager, RecoveryAction
from vaig.cakm import CAKM, AlertLevel
from vaig.council import CouncilQueue, CouncilItem
from vaig.skjaersilden import Skjaersilden
from vaig.delta_sandbox import DeltaBoxSandbox, CheckpointNotFoundError
from vaig.epistemic_underdetermination import (
    AlternativeHypothesis,
    EpistemicState,
    EpistemicUnderdeterminationGate,
    UnderdeterminationAssessment,
    UnderdeterminationInputError,
    UnderdeterminationKind,
)
from vaig.analytic_tradecraft import (
    AnalyticTradecraftAssessment,
    AnalyticTradecraftGate,
    AnalyticTradecraftInputError,
    AssumptionAssessment,
    AssumptionStatus,
    ClaimCredibility,
    EvidenceAssessment,
    EvidenceDisposition,
    EvidenceItem,
    ExpectedObservation,
    HypothesisAssessment,
    KeyAssumption,
    PurposeRisk,
    TradecraftState,
    evidence_item_from_package,
)
from vaig.reflection_components import (
    ConfidenceCalibration,
    CounterfactualExplorer,
    CounterfactualScenario,
    EvidenceGap,
    EvidenceGapDetector,
    PolicyAmbiguity,
    PolicyAmbiguityDetector,
    SageReferral,
)
from vaig.reflective_inquiry import (
    ReflectiveInquiryEngine,
    ReflectiveInquiryResult,
    ReflectionOutcome,
)
from vaig.transition_risk import (
    AITransitionRiskEvaluator,
    AssessmentStatus,
    CompositePolicy,
    EvidencePolicy,
    EvidenceSignal,
    RiskAssessment,
    TransitionRiskInputError,
)
from vaig._version import __version__

__all__ = [
    "AggregationMode", "AggregationPolicy", "AggregationResult",
    "aggregate_instrument_results", "ModelSignalBundle",
    "ClaimAdmissibilityBinding", "ClaimDisposition", "ClaimMateriality",
    "CriterionKind", "CriterionVerificationBinding",
    "EvidenceIntakeAssessment", "EvidenceIntakePolicy",
    "EvidenceIntakeRequest", "EvidenceIntakeState",
    "EvidencePackageBinding", "VersionedArtifactRef",
    "WorkflowVerificationBinding", "assess_evidence_intake",
    "VAIGEnsemble", "VAIGOrchestrator",
    "ValidationResult", "OrchestratorResult",
    "EvaluationReport", "InstrumentSlotReport", "ReportDisposition",
    "build_evaluation_report",
    "DistrustLevel", "WORMLog",
    "RecoveryManager", "RecoveryAction",
    "CAKM", "AlertLevel",
    "CouncilQueue", "CouncilItem",
    "Skjaersilden",
    "DeltaBoxSandbox", "CheckpointNotFoundError",
    "AlternativeHypothesis", "EpistemicState",
    "EpistemicUnderdeterminationGate", "UnderdeterminationAssessment",
    "UnderdeterminationInputError", "UnderdeterminationKind",
    "AnalyticTradecraftAssessment", "AnalyticTradecraftGate",
    "AnalyticTradecraftInputError", "AssumptionAssessment",
    "AssumptionStatus", "ClaimCredibility", "EvidenceAssessment",
    "EvidenceDisposition", "EvidenceItem", "ExpectedObservation",
    "HypothesisAssessment", "KeyAssumption", "PurposeRisk",
    "TradecraftState", "evidence_item_from_package",
    "ConfidenceCalibration", "CounterfactualExplorer",
    "CounterfactualScenario", "EvidenceGap",
    "EvidenceGapDetector", "PolicyAmbiguity",
    "PolicyAmbiguityDetector", "SageReferral",
    "ReflectiveInquiryEngine", "ReflectiveInquiryResult",
    "ReflectionOutcome",
    "AITransitionRiskEvaluator", "AssessmentStatus", "CompositePolicy",
    "EvidencePolicy", "EvidenceSignal", "RiskAssessment",
    "TransitionRiskInputError",
]
