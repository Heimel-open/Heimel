from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from valo_platform.action_envelope.models import (
    ActionConstraint,
    ActionDecision,
    ClearanceState,
    ConsequenceClass,
    GovernanceClearance,
    Reversibility,
)

from ..memory_provider import canonical_digest
from .clearance_profiles import (
    AssessmentDisposition,
    ProcurementClearanceAssessment,
    ProcurementClearanceProfile,
    ProcurementProfileId,
    assess_procurement_action_case,
)
from .models import CommitActionType, ProcurementActionCase


RUNTIME_VERSION = "0.1.0"
PROCUREMENT_COMMIT_DIGEST_CONSTRAINT = "procurement_commit_digest"


class ProcurementRuntimeError(RuntimeError):
    pass


class ProcurementIntegrityState(str, Enum):
    CURRENT = "current"
    REVALIDATION_REQUIRED = "revalidation_required"
    EXPIRED = "expired"


class ProcurementClearanceRequest(BaseModel):
    """Immutable, tenant-bound evidence package submitted to REHT.

    The request binds one procurement Action Case to one profile and one exact
    external commit. It never constitutes clearance or execution authority.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_version: str = RUNTIME_VERSION
    tenant_id: str = Field(min_length=1)
    environment_id: str = Field(min_length=1)
    profile_id: ProcurementProfileId
    profile_version: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    case_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    commit_type: CommitActionType
    commit_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    commit_payload_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_system: str = Field(min_length=1)
    resource_ref: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    consequence_class: ConsequenceClass
    reversibility: Reversibility
    authority_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    context_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority_refs: tuple[str, ...]
    policy_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    assessment: ProcurementClearanceAssessment
    prepared_at: datetime
    grants_authority: bool = False

    @model_validator(mode="after")
    def preserve_request_boundary(self) -> "ProcurementClearanceRequest":
        if self.grants_authority:
            raise ValueError("procurement clearance request cannot grant authority")
        if (
            self.assessment.profile_id != self.profile_id
            or self.assessment.profile_version != self.profile_version
            or self.assessment.case_id != self.case_id
        ):
            raise ValueError("assessment binding does not match clearance request")
        if self.request_digest != procurement_clearance_request_digest(self):
            raise ValueError("request_digest does not match canonical request payload")
        return self


class ProcurementConstraintBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    constraint_id: str = Field(min_length=1)
    constraint_type: str = Field(min_length=1)
    value: Any
    reason: str | None = None
    constraint_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def verify_digest(self) -> "ProcurementConstraintBinding":
        payload = self.model_dump(mode="json", exclude={"constraint_digest"})
        if self.constraint_digest != canonical_digest(payload):
            raise ValueError("constraint_digest mismatch")
        return self


class ProcurementClearanceBinding(BaseModel):
    """Verified reference to an externally issued canonical REHT clearance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_version: str = RUNTIME_VERSION
    request: ProcurementClearanceRequest
    clearance_id: str = Field(min_length=1)
    decision: ActionDecision
    clearance_state: ClearanceState
    valid_from: datetime
    valid_until: datetime
    constraints: tuple[ProcurementConstraintBinding, ...] = ()
    clearance_receipt_ref: str | None = None
    clearance_snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    executable: bool
    bound_at: datetime
    binding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False

    @model_validator(mode="after")
    def preserve_clearance_boundary(self) -> "ProcurementClearanceBinding":
        if self.grants_authority:
            raise ValueError("procurement binding cannot grant authority")
        expected = (
            self.clearance_state is ClearanceState.ACTIVE
            and self.decision in {ActionDecision.ALLOW, ActionDecision.MODIFY}
            and self.request.assessment.disposition is AssessmentDisposition.READY_FOR_REHT
            and _as_utc(self.valid_from) <= _as_utc(self.bound_at) < _as_utc(self.valid_until)
        )
        if self.executable != expected:
            raise ValueError("executable flag does not match bound clearance")
        if self.binding_digest != procurement_clearance_binding_digest(self):
            raise ValueError("binding_digest mismatch")
        return self


class ProcurementContinuousIntegrityEvent(BaseModel):
    """Evidence stating whether the bound clearance remains current."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1)
    binding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    current_request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    changed_fields: tuple[str, ...] = ()
    triggered_changes: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    observed_at: datetime
    state: ProcurementIntegrityState
    revalidation_required: bool
    event_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False

    @model_validator(mode="after")
    def evidence_only(self) -> "ProcurementContinuousIntegrityEvent":
        if self.grants_authority:
            raise ValueError("continuous integrity event cannot grant authority")
        if self.revalidation_required != (self.state is not ProcurementIntegrityState.CURRENT):
            raise ValueError("revalidation flag does not match integrity state")
        if self.event_digest != procurement_integrity_event_digest(self):
            raise ValueError("event_digest mismatch")
        return self


class RacsBoundProcurementCommit(BaseModel):
    """Exact commit payload prepared for canonical RACS/Core enforcement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_version: str = RUNTIME_VERSION
    tenant_id: str = Field(min_length=1)
    environment_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clearance_id: str = Field(min_length=1)
    clearance_binding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clearance_decision: ActionDecision
    commit_type: CommitActionType
    commit_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_system: str = Field(min_length=1)
    resource_ref: str = Field(min_length=1)
    payload_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1)
    constraints: tuple[ProcurementConstraintBinding, ...] = ()
    prepared_at: datetime
    commit_binding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False
    executed: bool = False

    @model_validator(mode="after")
    def preserve_enforcement_boundary(self) -> "RacsBoundProcurementCommit":
        if self.grants_authority:
            raise ValueError("RACS-bound commit cannot grant authority")
        if self.executed:
            raise ValueError("adapter cannot claim execution")
        if self.clearance_decision not in {ActionDecision.ALLOW, ActionDecision.MODIFY}:
            raise ValueError("RACS-bound commit requires ALLOW or MODIFY clearance")
        if self.commit_binding_digest != racs_procurement_commit_digest(self):
            raise ValueError("commit_binding_digest mismatch")
        return self


class ProcurementReceiptBinding(BaseModel):
    """References into the canonical receipt chain, not a second receipt model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clearance_id: str = Field(min_length=1)
    clearance_receipt_ref: str | None = None
    execution_receipt_ref: str | None = None
    outcome_receipt_ref: str | None = None
    receipt_binding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False

    @model_validator(mode="after")
    def references_only(self) -> "ProcurementReceiptBinding":
        if self.grants_authority:
            raise ValueError("receipt binding cannot grant authority")
        if self.receipt_binding_digest != procurement_receipt_binding_digest(self):
            raise ValueError("receipt_binding_digest mismatch")
        return self


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _profile_ref(profile: ProcurementClearanceProfile) -> str:
    return f"procurement-profile:{profile.profile_id.value}:{profile.profile_version}"


def _authority_refs(action_case: ProcurementActionCase) -> tuple[str, ...]:
    refs = [action_case.mandate_ref]
    if action_case.authority.delegation_ref:
        refs.append(action_case.authority.delegation_ref)
    refs.extend(action_case.authority.evidence_refs)
    return tuple(sorted(set(refs)))


def _evidence_payload(action_case: ProcurementActionCase) -> list[dict[str, Any]]:
    return sorted(
        (item.model_dump(mode="json") for item in action_case.evidence_refs),
        key=lambda item: item["evidence_id"],
    )


def _consequence_class(action_case: ProcurementActionCase) -> ConsequenceClass:
    return {
        "low": ConsequenceClass.C1_LOW,
        "medium": ConsequenceClass.C2_MEDIUM,
        "high": ConsequenceClass.C3_HIGH,
        "critical": ConsequenceClass.C4_CRITICAL,
    }[action_case.risk_level.value]


def _reversibility(action_case: ProcurementActionCase) -> Reversibility:
    return Reversibility.REVERSIBLE if action_case.reversible else Reversibility.IRREVERSIBLE


def procurement_clearance_request_digest(request: ProcurementClearanceRequest) -> str:
    return canonical_digest(
        request.model_dump(mode="json", exclude={"request_digest", "prepared_at"})
    )


def procurement_clearance_binding_digest(binding: ProcurementClearanceBinding) -> str:
    return canonical_digest(binding.model_dump(mode="json", exclude={"binding_digest"}))


def procurement_integrity_event_digest(event: ProcurementContinuousIntegrityEvent) -> str:
    return canonical_digest(event.model_dump(mode="json", exclude={"event_digest"}))


def racs_procurement_commit_digest(commit: RacsBoundProcurementCommit) -> str:
    return canonical_digest(commit.model_dump(mode="json", exclude={"commit_binding_digest"}))


def procurement_receipt_binding_digest(binding: ProcurementReceiptBinding) -> str:
    return canonical_digest(binding.model_dump(mode="json", exclude={"receipt_binding_digest"}))


def prepare_procurement_clearance_request(
    *,
    tenant_id: str,
    environment_id: str,
    action_case: ProcurementActionCase,
    profile: ProcurementClearanceProfile,
    observed_at: datetime,
    changed_fields: tuple[str, ...] = (),
) -> ProcurementClearanceRequest:
    assessment = assess_procurement_action_case(
        action_case=action_case,
        profile=profile,
        observed_at=observed_at,
        changed_fields=changed_fields,
    )
    policy_refs = tuple(
        sorted(
            {
                action_case.policy_version,
                _profile_ref(profile),
                *action_case.criteria_versions,
            }
        )
    )
    payload = {
        "runtime_version": RUNTIME_VERSION,
        "tenant_id": tenant_id,
        "environment_id": environment_id,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "case_id": action_case.case_id,
        "action_ref": action_case.action_ref,
        "case_digest": action_case.case_digest,
        "commit_type": action_case.requested_commit.action_type,
        "commit_digest": canonical_digest(action_case.requested_commit.model_dump(mode="json")),
        "commit_payload_digest": action_case.requested_commit.payload_digest,
        "target_system": action_case.requested_commit.target_system,
        "resource_ref": action_case.requested_commit.resource_ref,
        "idempotency_key": action_case.requested_commit.idempotency_key,
        "consequence_class": _consequence_class(action_case),
        "reversibility": _reversibility(action_case),
        "authority_fingerprint": canonical_digest(action_case.authority.model_dump(mode="json")),
        "policy_fingerprint": canonical_digest(
            {
                "policy_refs": list(policy_refs),
                "profile_id": profile.profile_id.value,
                "profile_version": profile.profile_version,
            }
        ),
        "context_fingerprint": canonical_digest(
            {
                "environment_id": environment_id,
                "procedure_ref": action_case.procedure_ref,
                "contract_ref": action_case.contract_ref,
                "operator_ref": action_case.operator_ref,
                "current_state_digest": action_case.current_state_digest,
            }
        ),
        "evidence_fingerprint": canonical_digest(_evidence_payload(action_case)),
        "authority_refs": _authority_refs(action_case),
        "policy_refs": policy_refs,
        "evidence_refs": tuple(sorted(item.evidence_id for item in action_case.evidence_refs)),
        "assessment": assessment,
        "prepared_at": _as_utc(observed_at),
        "grants_authority": False,
    }
    provisional = ProcurementClearanceRequest.model_construct(
        **payload,
        request_digest="sha256:" + "0" * 64,
    )
    return ProcurementClearanceRequest(
        **payload,
        request_digest=procurement_clearance_request_digest(provisional),
    )


def _constraint_binding(constraint: ActionConstraint) -> ProcurementConstraintBinding:
    payload = {
        "constraint_id": constraint.constraint_id,
        "constraint_type": constraint.constraint_type,
        "value": constraint.value,
        "reason": constraint.reason,
    }
    return ProcurementConstraintBinding(
        **payload,
        constraint_digest=canonical_digest(payload),
    )


def bind_reht_clearance(
    *,
    request: ProcurementClearanceRequest,
    clearance: GovernanceClearance,
    observed_at: datetime,
) -> ProcurementClearanceBinding:
    now = _as_utc(observed_at)
    valid_from = _as_utc(clearance.valid_from)
    valid_until = _as_utc(clearance.valid_until)

    exact_checks = (
        (clearance.tenant_id == request.tenant_id, "CLEARANCE_TENANT_MISMATCH"),
        (clearance.action_id == request.case_id, "CLEARANCE_ACTION_CASE_MISMATCH"),
        (clearance.state is ClearanceState.ACTIVE, "CLEARANCE_NOT_ACTIVE"),
        (valid_from <= now < valid_until, "CLEARANCE_OUTSIDE_VALIDITY_WINDOW"),
        (clearance.state_fingerprint == request.request_digest, "CLEARANCE_REQUEST_DIGEST_MISMATCH"),
        (clearance.authority_fingerprint == request.authority_fingerprint, "CLEARANCE_AUTHORITY_FINGERPRINT_MISMATCH"),
        (clearance.policy_fingerprint == request.policy_fingerprint, "CLEARANCE_POLICY_FINGERPRINT_MISMATCH"),
        (clearance.context_fingerprint == request.context_fingerprint, "CLEARANCE_CONTEXT_FINGERPRINT_MISMATCH"),
        (clearance.evidence_fingerprint == request.evidence_fingerprint, "CLEARANCE_EVIDENCE_FINGERPRINT_MISMATCH"),
        (clearance.consequence_class == request.consequence_class, "CLEARANCE_CONSEQUENCE_CLASS_MISMATCH"),
        (clearance.reversibility == request.reversibility, "CLEARANCE_REVERSIBILITY_MISMATCH"),
        (set(request.authority_refs).issubset(set(clearance.authority_refs)), "CLEARANCE_AUTHORITY_REFS_INCOMPLETE"),
        (set(request.policy_refs).issubset(set(clearance.policy_refs)), "CLEARANCE_POLICY_REFS_INCOMPLETE"),
        (set(request.evidence_refs).issubset(set(clearance.evidence_refs)), "CLEARANCE_EVIDENCE_REFS_INCOMPLETE"),
        (clearance.idempotency_key == request.idempotency_key, "CLEARANCE_IDEMPOTENCY_MISMATCH"),
    )
    for valid, code in exact_checks:
        if not valid:
            raise ProcurementRuntimeError(code)

    commit_constraints = [
        item
        for item in clearance.constraints
        if item.constraint_type == PROCUREMENT_COMMIT_DIGEST_CONSTRAINT
    ]
    if len(commit_constraints) != 1:
        raise ProcurementRuntimeError("CLEARANCE_COMMIT_DIGEST_CONSTRAINT_REQUIRED")
    if commit_constraints[0].value != request.commit_digest:
        raise ProcurementRuntimeError("CLEARANCE_COMMIT_DIGEST_MISMATCH")

    permissive = clearance.decision in {ActionDecision.ALLOW, ActionDecision.MODIFY}
    if request.assessment.disposition is not AssessmentDisposition.READY_FOR_REHT and permissive:
        raise ProcurementRuntimeError("PERMISSIVE_CLEARANCE_FOR_NON_READY_REQUEST")

    constraints = tuple(_constraint_binding(item) for item in clearance.constraints)
    payload = {
        "runtime_version": RUNTIME_VERSION,
        "request": request,
        "clearance_id": clearance.clearance_id,
        "decision": clearance.decision,
        "clearance_state": clearance.state,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "constraints": constraints,
        "clearance_receipt_ref": clearance.receipt_ref,
        "clearance_snapshot_digest": canonical_digest(clearance.model_dump(mode="json")),
        "executable": request.assessment.disposition is AssessmentDisposition.READY_FOR_REHT and permissive,
        "bound_at": now,
        "grants_authority": False,
    }
    provisional = ProcurementClearanceBinding.model_construct(
        **payload,
        binding_digest="sha256:" + "0" * 64,
    )
    return ProcurementClearanceBinding(
        **payload,
        binding_digest=procurement_clearance_binding_digest(provisional),
    )


def evaluate_procurement_continuous_integrity(
    *,
    binding: ProcurementClearanceBinding,
    current_action_case: ProcurementActionCase,
    profile: ProcurementClearanceProfile,
    observed_at: datetime,
    changed_fields: tuple[str, ...] = (),
) -> ProcurementContinuousIntegrityEvent:
    current = prepare_procurement_clearance_request(
        tenant_id=binding.request.tenant_id,
        environment_id=binding.request.environment_id,
        action_case=current_action_case,
        profile=profile,
        observed_at=observed_at,
        changed_fields=changed_fields,
    )
    now = _as_utc(observed_at)
    reasons: list[str] = []
    if current.request_digest != binding.request.request_digest:
        reasons.append("REQUEST_DIGEST_CHANGED")
    if current.commit_digest != binding.request.commit_digest:
        reasons.append("COMMIT_DIGEST_CHANGED")
    if current.assessment.triggered_changes:
        reasons.append("MATERIAL_CHANGE_TRIGGERED")
    if current.assessment.stale_evidence:
        reasons.append("EVIDENCE_STALE")
    if current.assessment.missing_evidence:
        reasons.append("EVIDENCE_MISSING")
    if current.assessment.missing_context:
        reasons.append("CONTEXT_MISSING")
    if now >= _as_utc(binding.valid_until):
        reasons.append("CLEARANCE_EXPIRED")

    state = (
        ProcurementIntegrityState.EXPIRED
        if "CLEARANCE_EXPIRED" in reasons
        else ProcurementIntegrityState.REVALIDATION_REQUIRED
        if reasons
        else ProcurementIntegrityState.CURRENT
    )
    payload = {
        "event_id": f"procurement-integrity:{binding.clearance_id}:{current.request_digest}",
        "binding_digest": binding.binding_digest,
        "baseline_request_digest": binding.request.request_digest,
        "current_request_digest": current.request_digest,
        "changed_fields": tuple(sorted(set(changed_fields))),
        "triggered_changes": current.assessment.triggered_changes,
        "reasons": tuple(sorted(set(reasons))),
        "observed_at": now,
        "state": state,
        "revalidation_required": state is not ProcurementIntegrityState.CURRENT,
        "grants_authority": False,
    }
    provisional = ProcurementContinuousIntegrityEvent.model_construct(
        **payload,
        event_digest="sha256:" + "0" * 64,
    )
    return ProcurementContinuousIntegrityEvent(
        **payload,
        event_digest=procurement_integrity_event_digest(provisional),
    )


def build_racs_bound_procurement_commit(
    *,
    binding: ProcurementClearanceBinding,
    integrity_event: ProcurementContinuousIntegrityEvent,
    observed_at: datetime,
) -> RacsBoundProcurementCommit:
    now = _as_utc(observed_at)
    if not binding.executable:
        raise ProcurementRuntimeError("CLEARANCE_NOT_EXECUTABLE")
    if not (_as_utc(binding.valid_from) <= now < _as_utc(binding.valid_until)):
        raise ProcurementRuntimeError("CLEARANCE_EXPIRED_BEFORE_COMMIT")
    if integrity_event.binding_digest != binding.binding_digest:
        raise ProcurementRuntimeError("INTEGRITY_EVENT_BINDING_MISMATCH")
    if integrity_event.current_request_digest != binding.request.request_digest:
        raise ProcurementRuntimeError("INTEGRITY_EVENT_REQUEST_MISMATCH")
    if integrity_event.revalidation_required:
        raise ProcurementRuntimeError("REVALIDATION_REQUIRED_BEFORE_COMMIT")

    request = binding.request
    payload = {
        "runtime_version": RUNTIME_VERSION,
        "tenant_id": request.tenant_id,
        "environment_id": request.environment_id,
        "case_id": request.case_id,
        "request_digest": request.request_digest,
        "clearance_id": binding.clearance_id,
        "clearance_binding_digest": binding.binding_digest,
        "clearance_decision": binding.decision,
        "commit_type": request.commit_type,
        "commit_digest": request.commit_digest,
        "target_system": request.target_system,
        "resource_ref": request.resource_ref,
        "payload_digest": request.commit_payload_digest,
        "idempotency_key": request.idempotency_key,
        "constraints": binding.constraints,
        "prepared_at": now,
        "grants_authority": False,
        "executed": False,
    }
    provisional = RacsBoundProcurementCommit.model_construct(
        **payload,
        commit_binding_digest="sha256:" + "0" * 64,
    )
    return RacsBoundProcurementCommit(
        **payload,
        commit_binding_digest=racs_procurement_commit_digest(provisional),
    )


def bind_procurement_receipt_refs(
    *,
    binding: ProcurementClearanceBinding,
    execution_receipt_ref: str | None = None,
    outcome_receipt_ref: str | None = None,
) -> ProcurementReceiptBinding:
    payload = {
        "case_id": binding.request.case_id,
        "request_digest": binding.request.request_digest,
        "clearance_id": binding.clearance_id,
        "clearance_receipt_ref": binding.clearance_receipt_ref,
        "execution_receipt_ref": execution_receipt_ref,
        "outcome_receipt_ref": outcome_receipt_ref,
        "grants_authority": False,
    }
    provisional = ProcurementReceiptBinding.model_construct(
        **payload,
        receipt_binding_digest="sha256:" + "0" * 64,
    )
    return ProcurementReceiptBinding(
        **payload,
        receipt_binding_digest=procurement_receipt_binding_digest(provisional),
    )
