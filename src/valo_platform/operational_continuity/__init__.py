"""Operational Continuity observation, runtime and replay helpers.

These components produce evidence and deterministic validity decisions only.
VAIG evaluates, REHT owns clearance validity and RACS remains the enforcement
vocabulary.
"""

from .commit_integration import (
    RevalidatedActionCaseCommitBinding,
    authorize_revalidated_action_case_commit,
    verify_revalidated_action_case_commit_binding,
)
from .context_fingerprint_reader import (
    RegisteredContextDecisionFingerprintReader,
)
from .fingerprint_readers import (
    AuthorityRegistryDecisionFingerprintReader,
    EvidenceStoreDecisionFingerprintReader,
    FingerprintOwnerReaderError,
    RegisteredPolicyDecisionFingerprintReader,
    SQLiteActionCaseStateDecisionFingerprintReader,
    build_canonical_owner_fingerprint_provider,
)
from .fingerprint_snapshot import (
    CallableDecisionFingerprintReader,
    CompositeCurrentDecisionFingerprintProvider,
    CurrentDecisionFingerprintProvider,
    CurrentDecisionFingerprintSnapshot,
    DecisionFingerprintKind,
    DecisionFingerprintObservation,
    DecisionFingerprintReader,
    DecisionFingerprintSnapshotError,
)
from .observers import (
    DeadlineObserver,
    FingerprintObserver,
    ManualObservationAdapter,
    ObservationBinding,
    SafetyStopObserver,
)
from .receipt_replay import (
    ContinuityReceiptRecord,
    ContinuityReplayResult,
    build_continuity_receipt_record,
    replay_continuity_receipt,
    verify_continuity_receipt_chain,
)
from .registered_policy_source import (
    RegisteredPublicationPolicySourceAdapter,
    capture_registered_policy_baseline,
)
from .revalidation import (
    ContinuityCurrentFingerprints,
    ContinuityRevalidationRequest,
    ContinuityRevalidationResult,
    build_revalidation_request,
    evaluate_revalidation_request,
    validate_vaig_assessment,
)
from .runtime import (
    CallableVaigContinuityAssessmentPort,
    LiveContinuityRevalidation,
    OperationalContinuityRuntime,
    OperationalContinuityRuntimeError,
    RuntimeContinuitySource,
    RuntimeContinuitySourceHandle,
    VaigContinuityAssessmentPort,
    evidence_runtime_source,
    mandate_runtime_source,
    publication_policy_runtime_source,
    registered_policy_runtime_source,
    target_state_runtime_source,
)
from .source_adapters import (
    ContinuitySourceBundle,
    ContinuitySourceDomain,
    ContinuitySourceObservation,
    EvidenceStoreSourceAdapter,
    MandateRegistrySourceAdapter,
    PublicationPolicySourceAdapter,
    SourceObservationError,
    TargetStateSourceAdapter,
    build_source_bundle,
    target_state_fingerprint,
)
from .source_baselines import (
    ContinuitySourceBaseline,
    ContinuitySourceBaselineEntry,
    build_source_baseline,
    capture_evidence_baseline,
    capture_mandate_baseline,
    capture_policy_baseline,
    capture_target_state_baseline,
)
from .vaig_http import (
    VaigContinuityClientError,
    VaigHttpContinuityAssessmentPort,
)

__all__ = [
    "AuthorityRegistryDecisionFingerprintReader",
    "CallableDecisionFingerprintReader",
    "CallableVaigContinuityAssessmentPort",
    "CompositeCurrentDecisionFingerprintProvider",
    "ContinuityCurrentFingerprints",
    "ContinuityReceiptRecord",
    "ContinuityReplayResult",
    "ContinuityRevalidationRequest",
    "ContinuityRevalidationResult",
    "ContinuitySourceBaseline",
    "ContinuitySourceBaselineEntry",
    "ContinuitySourceBundle",
    "ContinuitySourceDomain",
    "ContinuitySourceObservation",
    "CurrentDecisionFingerprintProvider",
    "CurrentDecisionFingerprintSnapshot",
    "DeadlineObserver",
    "DecisionFingerprintKind",
    "DecisionFingerprintObservation",
    "DecisionFingerprintReader",
    "DecisionFingerprintSnapshotError",
    "EvidenceStoreDecisionFingerprintReader",
    "EvidenceStoreSourceAdapter",
    "FingerprintObserver",
    "FingerprintOwnerReaderError",
    "LiveContinuityRevalidation",
    "MandateRegistrySourceAdapter",
    "ManualObservationAdapter",
    "ObservationBinding",
    "OperationalContinuityRuntime",
    "OperationalContinuityRuntimeError",
    "PublicationPolicySourceAdapter",
    "RegisteredContextDecisionFingerprintReader",
    "RegisteredPolicyDecisionFingerprintReader",
    "RegisteredPublicationPolicySourceAdapter",
    "RevalidatedActionCaseCommitBinding",
    "RuntimeContinuitySource",
    "RuntimeContinuitySourceHandle",
    "SQLiteActionCaseStateDecisionFingerprintReader",
    "SafetyStopObserver",
    "SourceObservationError",
    "TargetStateSourceAdapter",
    "VaigContinuityAssessmentPort",
    "VaigContinuityClientError",
    "VaigHttpContinuityAssessmentPort",
    "authorize_revalidated_action_case_commit",
    "build_canonical_owner_fingerprint_provider",
    "build_continuity_receipt_record",
    "build_revalidation_request",
    "build_source_baseline",
    "build_source_bundle",
    "capture_evidence_baseline",
    "capture_mandate_baseline",
    "capture_policy_baseline",
    "capture_registered_policy_baseline",
    "capture_target_state_baseline",
    "evaluate_revalidation_request",
    "evidence_runtime_source",
    "mandate_runtime_source",
    "publication_policy_runtime_source",
    "registered_policy_runtime_source",
    "replay_continuity_receipt",
    "target_state_fingerprint",
    "target_state_runtime_source",
    "validate_vaig_assessment",
    "verify_continuity_receipt_chain",
    "verify_revalidated_action_case_commit_binding",
]
