"""Provider-neutral behavioral evidence loop for VALO Factory.

Behavioral products are sensors and proposal generators. They never become
authority sources. Consequential execution remains bound to an exact reht
decision and a Veritas-backed execution receipt.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "behavioral-evidence-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class BehavioralEvidenceError(ValueError):
    pass


class AuthorityBindingError(BehavioralEvidenceError):
    pass


class OutcomeBindingError(BehavioralEvidenceError):
    pass


class LearningAdmissionError(BehavioralEvidenceError):
    pass


class ObservationMode(str, Enum):
    LIVE = "live"
    SHADOW = "shadow"
    REPLAY = "replay"


class ClaimKind(str, Enum):
    OBSERVED_FACT = "observed_fact"
    DERIVED_METRIC = "derived_metric"
    MODEL_EXPLANATION = "model_explanation"
    HYPOTHESIS = "hypothesis"
    EXPECTED_OUTCOME = "expected_outcome"
    VERIFIED_OUTCOME = "verified_outcome"


class PrivacyClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RedactionState(str, Enum):
    REDACTED = "redacted"
    TOKENIZED = "tokenized"
    SOURCE_CONTROLLED = "source_controlled"


class BehavioralAction(str, Enum):
    ANALYZE = "analyze"
    PROPOSE_BUILD_ORDER = "propose_build_order"
    PROPOSE_DATASET = "propose_dataset"
    OPEN_PR = "open_pr"
    MERGE = "merge"
    DEPLOY = "deploy"
    MUTATE_PRODUCTION = "mutate_production"
    TRAIN_MODEL = "train_model"
    PROMOTE_MODEL = "promote_model"


CONSEQUENTIAL_ACTIONS = frozenset(
    {
        BehavioralAction.MERGE,
        BehavioralAction.DEPLOY,
        BehavioralAction.MUTATE_PRODUCTION,
        BehavioralAction.TRAIN_MODEL,
        BehavioralAction.PROMOTE_MODEL,
    }
)
SENSOR_ALLOWED_ACTIONS = frozenset(
    {
        BehavioralAction.ANALYZE,
        BehavioralAction.PROPOSE_BUILD_ORDER,
        BehavioralAction.PROPOSE_DATASET,
        BehavioralAction.OPEN_PR,
    }
)


class OutcomeStatus(str, Enum):
    VERIFIED_IMPROVED = "verified_improved"
    VERIFIED_UNCHANGED = "verified_unchanged"
    VERIFIED_REGRESSED = "verified_regressed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


def _required(value: str, name: str) -> str:
    clean = str(value).strip()
    if not clean:
        raise BehavioralEvidenceError(f"{name} is required")
    return clean


def _time(value: str, name: str) -> datetime:
    clean = _required(value, name)
    try:
        parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BehavioralEvidenceError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise BehavioralEvidenceError(f"{name} must include a timezone")
    return parsed


def _digest(value: str, name: str) -> str:
    clean = _required(value, name)
    if not _SHA256.fullmatch(clean):
        raise BehavioralEvidenceError(f"{name} must be a lowercase SHA-256")
    return clean


def _refs(values: Sequence[str], name: str, required: bool = False) -> tuple[str, ...]:
    clean = tuple(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))
    if required and not clean:
        raise BehavioralEvidenceError(f"at least one {name} is required")
    return clean


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {f.name: _jsonable(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    return value


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PrivacyEnvelopeV1:
    tenant_id: str
    scope: str
    collection_purpose: str
    classification: PrivacyClass
    redaction_state: RedactionState
    retention_class: str
    residency: str
    rights_basis_ref: str
    training_reuse_allowed: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "tenant_id",
            "scope",
            "collection_purpose",
            "retention_class",
            "residency",
            "rights_basis_ref",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))


@dataclass(frozen=True)
class EvidenceRefV1:
    evidence_id: str
    source_type: str
    source_ref: str
    payload_digest: str
    observed_at: str
    captured_at: str
    privacy: PrivacyEnvelopeV1
    provenance_ref: str
    actor_ref: str = ""
    resource_ref: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_type", "source_ref", "provenance_ref"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "payload_digest", _digest(self.payload_digest, "payload_digest"))
        observed = _time(self.observed_at, "observed_at")
        captured = _time(self.captured_at, "captured_at")
        if observed > captured:
            raise BehavioralEvidenceError("observed_at cannot be after captured_at")
        object.__setattr__(
            self,
            "metadata",
            {str(k).strip(): str(v).strip() for k, v in self.metadata.items() if str(k).strip()},
        )

    @property
    def integrity_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class BehavioralObservationV1:
    observation_id: str
    event_type: str
    observed_condition: str
    evidence_refs: tuple[EvidenceRefV1, ...]
    mode: ObservationMode
    causal_predecessor_refs: tuple[str, ...] = ()
    actor_ref: str = ""
    resource_ref: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("observation_id", "event_type", "observed_condition"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if not self.evidence_refs:
            raise BehavioralEvidenceError("at least one evidence_ref is required")
        if len({e.privacy.tenant_id for e in self.evidence_refs}) != 1:
            raise BehavioralEvidenceError("one observation cannot mix tenants")
        if len({e.privacy.scope for e in self.evidence_refs}) != 1:
            raise BehavioralEvidenceError("one observation cannot mix scopes")
        object.__setattr__(
            self,
            "causal_predecessor_refs",
            _refs(self.causal_predecessor_refs, "causal_predecessor_ref"),
        )

    @property
    def integrity_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class BehaviorTraceV1:
    trace_id: str
    observation_ids: tuple[str, ...]
    mode: ObservationMode
    session_or_run_ref: str
    start_position_ref: str
    end_position_ref: str
    unresolved_gaps: tuple[str, ...] = ()
    complete: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("trace_id", "session_or_run_ref", "start_position_ref", "end_position_ref"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "observation_ids", _refs(self.observation_ids, "observation_id", True))
        object.__setattr__(self, "unresolved_gaps", _refs(self.unresolved_gaps, "unresolved_gap"))
        if self.complete and self.unresolved_gaps:
            raise BehavioralEvidenceError("complete trace cannot contain unresolved gaps")

    @property
    def trace_digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class BehaviorFindingV1:
    finding_id: str
    trace_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    claim_kind: ClaimKind
    observed_condition: str
    expected_condition_ref: str
    confidence: float
    contradictory_evidence_refs: tuple[str, ...]
    materiality: str
    generated_by: str
    reproducibility_ref: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "finding_id",
            "observed_condition",
            "expected_condition_ref",
            "materiality",
            "generated_by",
            "reproducibility_ref",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "trace_refs", _refs(self.trace_refs, "trace_ref"))
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, "evidence_ref"))
        object.__setattr__(
            self,
            "contradictory_evidence_refs",
            _refs(self.contradictory_evidence_refs, "contradictory_evidence_ref"),
        )
        if not self.trace_refs and not self.evidence_refs:
            raise BehavioralEvidenceError("finding must resolve to trace or evidence")
        if not 0 <= self.confidence <= 1:
            raise BehavioralEvidenceError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ImprovementCandidateV1:
    candidate_id: str
    finding_refs: tuple[str, ...]
    hypothesis: str
    proposed_change_type: str
    target_ref: str
    expected_outcome: str
    action_payload_digest: str
    requested_actions: tuple[BehavioralAction, ...]
    risk_class: str
    required_evaluation_refs: tuple[str, ...]
    owner_ref: str
    status: str = "proposed"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "candidate_id",
            "hypothesis",
            "proposed_change_type",
            "target_ref",
            "expected_outcome",
            "risk_class",
            "owner_ref",
            "status",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "finding_refs", _refs(self.finding_refs, "finding_ref", True))
        object.__setattr__(
            self,
            "required_evaluation_refs",
            _refs(self.required_evaluation_refs, "required_evaluation_ref", True),
        )
        if not self.requested_actions:
            raise BehavioralEvidenceError("at least one requested_action is required")
        object.__setattr__(self, "requested_actions", tuple(dict.fromkeys(self.requested_actions)))
        object.__setattr__(
            self,
            "action_payload_digest",
            _digest(self.action_payload_digest, "action_payload_digest"),
        )

    def requires_execution_authorization(self) -> bool:
        return any(a in CONSEQUENTIAL_ACTIONS for a in self.requested_actions)


@dataclass(frozen=True)
class AuthorizationBindingV1:
    authorization_id: str
    candidate_id: str
    action_payload_digest: str
    principal_ref: str
    mandate_ref: str
    reht_decision_ref: str
    authorized_state_ref: str
    authorized_at: str
    expires_at: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "authorization_id",
            "candidate_id",
            "principal_ref",
            "mandate_ref",
            "reht_decision_ref",
            "authorized_state_ref",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(
            self,
            "action_payload_digest",
            _digest(self.action_payload_digest, "action_payload_digest"),
        )
        if _time(self.expires_at, "expires_at") <= _time(self.authorized_at, "authorized_at"):
            raise AuthorityBindingError("expires_at must be after authorized_at")


@dataclass(frozen=True)
class ExecutionReceiptV1:
    receipt_id: str
    candidate_id: str
    action_payload_digest: str
    authorization_id: str
    executed_at: str
    result_artifact_ref: str
    veritas_receipt_ref: str
    deployment_ref: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "receipt_id",
            "candidate_id",
            "authorization_id",
            "result_artifact_ref",
            "veritas_receipt_ref",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(
            self,
            "action_payload_digest",
            _digest(self.action_payload_digest, "action_payload_digest"),
        )
        _time(self.executed_at, "executed_at")


@dataclass(frozen=True)
class OutcomeEvidenceV1:
    outcome_id: str
    candidate_id: str
    action_payload_digest: str
    authorization_id: str
    execution_receipt_id: str
    pre_evidence_refs: tuple[str, ...]
    post_evidence_refs: tuple[str, ...]
    expected_outcome: str
    observed_outcome: str
    comparison_method: str
    window_start: str
    window_end: str
    metric_name: str
    baseline_value: float | None
    observed_value: float | None
    causal_caveats: tuple[str, ...]
    status: OutcomeStatus
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "outcome_id",
            "candidate_id",
            "authorization_id",
            "execution_receipt_id",
            "expected_outcome",
            "observed_outcome",
            "comparison_method",
            "metric_name",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(
            self,
            "action_payload_digest",
            _digest(self.action_payload_digest, "action_payload_digest"),
        )
        object.__setattr__(self, "pre_evidence_refs", _refs(self.pre_evidence_refs, "pre_evidence_ref"))
        object.__setattr__(self, "post_evidence_refs", _refs(self.post_evidence_refs, "post_evidence_ref"))
        object.__setattr__(self, "causal_caveats", _refs(self.causal_caveats, "causal_caveat"))
        if _time(self.window_end, "window_end") <= _time(self.window_start, "window_start"):
            raise OutcomeBindingError("window_end must be after window_start")
        if self.status != OutcomeStatus.INSUFFICIENT_EVIDENCE:
            if not self.pre_evidence_refs or not self.post_evidence_refs:
                raise OutcomeBindingError("verified outcome requires pre and post evidence")
            if self.baseline_value is None or self.observed_value is None:
                raise OutcomeBindingError("verified outcome requires comparable metric values")


@dataclass(frozen=True)
class LearningProposalV1:
    proposal_id: str
    outcome_id: str
    purpose: str
    evidence_refs: tuple[str, ...]
    dataset_admission_ref: str = ""
    authority_effect: str = "none"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("proposal_id", "outcome_id", "purpose"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, "evidence_ref", True))
        if self.authority_effect != "none":
            raise LearningAdmissionError("learning cannot create or widen authority")
        if self.purpose == "model_training" and not self.dataset_admission_ref.strip():
            raise LearningAdmissionError("model training requires dataset admission")


class BehavioralSensorAdapter:
    """Normalize provider evidence and proposals without execution authority."""

    allowed_actions = SENSOR_ALLOWED_ACTIONS

    def __init__(self, source_type: str):
        self.source_type = _required(source_type, "source_type")

    def normalize_observation(
        self,
        *,
        observation_id: str,
        event_type: str,
        observed_condition: str,
        evidence_refs: Sequence[EvidenceRefV1],
        mode: ObservationMode,
        causal_predecessor_refs: Sequence[str] = (),
        actor_ref: str = "",
        resource_ref: str = "",
    ) -> BehavioralObservationV1:
        evidence = tuple(evidence_refs)
        if any(item.source_type != self.source_type for item in evidence):
            raise BehavioralEvidenceError(f"evidence must come from {self.source_type!r}")
        return BehavioralObservationV1(
            observation_id=observation_id,
            event_type=event_type,
            observed_condition=observed_condition,
            evidence_refs=evidence,
            mode=mode,
            causal_predecessor_refs=tuple(causal_predecessor_refs),
            actor_ref=actor_ref,
            resource_ref=resource_ref,
        )

    def propose_candidate(self, **values: Any) -> ImprovementCandidateV1:
        actions = tuple(values["requested_actions"])
        forbidden = set(actions) - self.allowed_actions
        if forbidden:
            names = ", ".join(sorted(a.value for a in forbidden))
            raise PermissionError(f"behavioral sensor cannot authorize: {names}")
        values["requested_actions"] = actions
        values["finding_refs"] = tuple(values["finding_refs"])
        values["required_evaluation_refs"] = tuple(values["required_evaluation_refs"])
        return ImprovementCandidateV1(**values)


def authority_boundary(candidate: ImprovementCandidateV1) -> str:
    return "REHT_REQUIRED" if candidate.requires_execution_authorization() else "FACTORY_VALIDATE"


class BehavioralEvidenceLoop:
    @staticmethod
    def validate_authorization(
        candidate: ImprovementCandidateV1,
        authorization: AuthorizationBindingV1,
        *,
        at_time: str,
    ) -> None:
        if candidate.candidate_id != authorization.candidate_id:
            raise AuthorityBindingError("authorization candidate mismatch")
        if candidate.action_payload_digest != authorization.action_payload_digest:
            raise AuthorityBindingError("authorization does not bind exact action")
        now = _time(at_time, "at_time")
        if now < _time(authorization.authorized_at, "authorized_at"):
            raise AuthorityBindingError("authorization is not active")
        if now > _time(authorization.expires_at, "expires_at"):
            raise AuthorityBindingError("authorization has expired")

    @classmethod
    def record_execution(
        cls,
        candidate: ImprovementCandidateV1,
        authorization: AuthorizationBindingV1,
        receipt: ExecutionReceiptV1,
    ) -> ExecutionReceiptV1:
        cls.validate_authorization(candidate, authorization, at_time=receipt.executed_at)
        if receipt.candidate_id != candidate.candidate_id:
            raise AuthorityBindingError("receipt candidate mismatch")
        if receipt.authorization_id != authorization.authorization_id:
            raise AuthorityBindingError("receipt authorization mismatch")
        if receipt.action_payload_digest != candidate.action_payload_digest:
            raise AuthorityBindingError("receipt does not bind exact action")
        return receipt

    @classmethod
    def verify_outcome(
        cls,
        candidate: ImprovementCandidateV1,
        authorization: AuthorizationBindingV1,
        receipt: ExecutionReceiptV1,
        outcome: OutcomeEvidenceV1,
    ) -> OutcomeEvidenceV1:
        cls.record_execution(candidate, authorization, receipt)
        if outcome.candidate_id != candidate.candidate_id:
            raise OutcomeBindingError("outcome candidate mismatch")
        if outcome.authorization_id != authorization.authorization_id:
            raise OutcomeBindingError("outcome authorization mismatch")
        if outcome.execution_receipt_id != receipt.receipt_id:
            raise OutcomeBindingError("outcome receipt mismatch")
        if outcome.action_payload_digest != candidate.action_payload_digest:
            raise OutcomeBindingError("outcome does not bind exact action")
        if outcome.expected_outcome != candidate.expected_outcome:
            raise OutcomeBindingError("expected outcome contract changed")
        return outcome

    @staticmethod
    def propose_learning(
        outcome: OutcomeEvidenceV1,
        *,
        proposal_id: str,
        purpose: str,
        dataset_admission_ref: str = "",
    ) -> LearningProposalV1:
        if outcome.status == OutcomeStatus.INSUFFICIENT_EVIDENCE:
            raise LearningAdmissionError("insufficient evidence cannot enter learning")
        return LearningProposalV1(
            proposal_id=proposal_id,
            outcome_id=outcome.outcome_id,
            purpose=purpose,
            evidence_refs=outcome.pre_evidence_refs + outcome.post_evidence_refs,
            dataset_admission_ref=dataset_admission_ref,
        )


def classify_outcome(
    *,
    baseline_value: float | None,
    observed_value: float | None,
    pre_evidence_refs: Sequence[str],
    post_evidence_refs: Sequence[str],
    lower_is_better: bool = False,
    minimum_improvement: float = 0,
) -> OutcomeStatus:
    if (
        baseline_value is None
        or observed_value is None
        or not _refs(pre_evidence_refs, "pre_evidence_ref")
        or not _refs(post_evidence_refs, "post_evidence_ref")
    ):
        return OutcomeStatus.INSUFFICIENT_EVIDENCE
    delta = baseline_value - observed_value if lower_is_better else observed_value - baseline_value
    if delta > minimum_improvement:
        return OutcomeStatus.VERIFIED_IMPROVED
    if delta < 0:
        return OutcomeStatus.VERIFIED_REGRESSED
    return OutcomeStatus.VERIFIED_UNCHANGED


__all__ = [
    "AuthorizationBindingV1",
    "AuthorityBindingError",
    "BehaviorFindingV1",
    "BehaviorTraceV1",
    "BehavioralAction",
    "BehavioralEvidenceError",
    "BehavioralEvidenceLoop",
    "BehavioralObservationV1",
    "BehavioralSensorAdapter",
    "ClaimKind",
    "EvidenceRefV1",
    "ExecutionReceiptV1",
    "ImprovementCandidateV1",
    "LearningAdmissionError",
    "LearningProposalV1",
    "ObservationMode",
    "OutcomeBindingError",
    "OutcomeEvidenceV1",
    "OutcomeStatus",
    "PrivacyClass",
    "PrivacyEnvelopeV1",
    "RedactionState",
    "authority_boundary",
    "canonical_digest",
    "classify_outcome",
]
