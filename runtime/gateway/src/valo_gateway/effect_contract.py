from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .claims_instrumentation import Status, VerificationResult
from .contracts.models import canonical_digest


class ConsequenceOperation(str, Enum):
    PAYMENT_RELEASE = "PAYMENT_RELEASE"
    VENDOR_BANK_CHANGE = "VENDOR_BANK_CHANGE"
    INVOICE_CREATE = "INVOICE_CREATE"
    INVOICE_APPROVE = "INVOICE_APPROVE"
    JOURNAL_POST = "JOURNAL_POST"
    CREDIT_NOTE_ISSUE = "CREDIT_NOTE_ISSUE"
    VENDOR_CREATE = "VENDOR_CREATE"
    USER_PRIVILEGE_GRANT = "USER_PRIVILEGE_GRANT"
    USER_PRIVILEGE_REVOKE = "USER_PRIVILEGE_REVOKE"
    CONTRACT_SIGN = "CONTRACT_SIGN"
    CLINICAL_ORDER_CREATE = "CLINICAL_ORDER_CREATE"
    MEDICATION_PRESCRIBE = "MEDICATION_PRESCRIBE"
    CLINICAL_RECORD_WRITE = "CLINICAL_RECORD_WRITE"
    HEALTHCARE_CLAIM_SUBMIT = "HEALTHCARE_CLAIM_SUBMIT"
    INSURANCE_BIND = "INSURANCE_BIND"
    INSURANCE_CLAIM_PAY = "INSURANCE_CLAIM_PAY"
    CREDIT_APPROVE = "CREDIT_APPROVE"
    TRADE_SUBMIT = "TRADE_SUBMIT"
    TRADE_CANCEL = "TRADE_CANCEL"
    REGULATORY_FILE = "REGULATORY_FILE"
    COMMUNICATION_SEND = "COMMUNICATION_SEND"
    CRM_COMMIT = "CRM_COMMIT"
    PHYSICAL_ACTUATE = "PHYSICAL_ACTUATE"
    DEPLOYMENT_APPLY = "DEPLOYMENT_APPLY"


class RepresentationIntegrity(str, Enum):
    VERIFIED = "VERIFIED"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"


class CompensationPolicy(str, Enum):
    NONE = "NONE"
    MANUAL = "MANUAL"
    AUTOMATIC_REVERSAL = "AUTOMATIC_REVERSAL"


class EffectLifecycleState(str, Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"


class AuthorityRequirement(BaseModel):
    authority_type: str = Field(min_length=1)
    evidence_ref: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityComposition(BaseModel):
    requirements: tuple[AuthorityRequirement, ...]
    mode: str = "ALL"
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_composition(self) -> AuthorityComposition:
        if self.mode != "ALL":
            raise ValueError("authority composition is fail-closed ALL in v1")
        if not self.requirements:
            raise ValueError("at least one authority requirement is required")
        types = [item.authority_type for item in self.requirements]
        if len(types) != len(set(types)):
            raise ValueError("authority requirement types must be unique")
        return self

    def assert_satisfied(self, evidence_refs: Iterable[str]) -> None:
        supplied = set(evidence_refs)
        missing = [r.authority_type for r in self.requirements if r.evidence_ref not in supplied]
        if missing:
            raise PermissionError(f"missing required authority evidence: {missing}")


class ReadProvenance(BaseModel):
    source_ref: str = Field(min_length=1)
    source_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    observed_at: datetime
    valid_until: datetime
    representation_integrity: RepresentationIntegrity
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> ReadProvenance:
        if self.observed_at.utcoffset() is None or self.valid_until.utcoffset() is None:
            raise ValueError("read provenance timestamps must be timezone-aware")
        if self.valid_until <= self.observed_at:
            raise ValueError("read provenance valid_until must be after observed_at")
        return self

    def assert_usable(self, now: datetime) -> None:
        if self.representation_integrity is not RepresentationIntegrity.VERIFIED:
            raise PermissionError("consequence-bearing read integrity is not VERIFIED")
        if not self.observed_at <= now < self.valid_until:
            raise PermissionError("consequence-bearing read is stale")


class EffectTargetBinding(BaseModel):
    provider: str = Field(min_length=1)
    tenant: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    credential_authority_ref: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdapterCapabilityManifest(BaseModel):
    adapter_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    operations: frozenset[ConsequenceOperation]
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_operations(self) -> AdapterCapabilityManifest:
        if not self.operations:
            raise ValueError("adapter manifest must declare at least one operation")
        return self

    def assert_operation(self, operation: str | ConsequenceOperation) -> ConsequenceOperation:
        try:
            canonical = ConsequenceOperation(operation)
        except ValueError as exc:
            raise PermissionError(f"unknown consequence operation: {operation}") from exc
        if canonical not in self.operations:
            raise PermissionError(f"operation {canonical.value} is not declared by adapter {self.adapter_id}")
        return canonical


class ClaimRequirement(BaseModel):
    claim_id: str = Field(min_length=1)
    required_status: Status = Status.SUPPORTED
    model_config = ConfigDict(extra="forbid", frozen=True)


class IdempotencyBinding(BaseModel):
    effect_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    parameters_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    model_config = ConfigDict(extra="forbid", frozen=True)

    def assert_same_effect(self, other: IdempotencyBinding) -> None:
        if self.idempotency_key != other.idempotency_key:
            return
        if self != other:
            raise PermissionError("idempotency key reuse conflicts with an existing effect")


class ProviderCallbackEvidence(BaseModel):
    provider: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    event_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    signature_ref: str = Field(min_length=1)
    verified: bool
    observed_at: datetime
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_time(self) -> ProviderCallbackEvidence:
        if self.observed_at.utcoffset() is None:
            raise ValueError("callback observed_at must be timezone-aware")
        return self

    def assert_verified(self, *, provider: str, correlation_id: str) -> None:
        if not self.verified:
            raise PermissionError("provider callback signature is not verified")
        if self.provider != provider or self.correlation_id != correlation_id:
            raise PermissionError("provider callback does not bind the expected effect")


class EffectContract(BaseModel):
    effect_type: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    tenant: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    operation: ConsequenceOperation
    parameters_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority_requirements: AuthorityComposition
    constraints: dict[str, Any] = Field(default_factory=dict)
    freshness: datetime
    idempotency_key: str = Field(min_length=1)
    completion_criteria: tuple[str, ...]
    required_evidence: tuple[str, ...]
    compensation_policy: CompensationPolicy
    credential_authority_ref: str = Field(min_length=1)
    claim_requirements: tuple[ClaimRequirement, ...] = ()
    read_provenance: tuple[ReadProvenance, ...] = ()
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_contract(self) -> EffectContract:
        if self.freshness.utcoffset() is None:
            raise ValueError("freshness must be timezone-aware")
        if not self.completion_criteria:
            raise ValueError("completion criteria are required")
        if not self.required_evidence:
            raise ValueError("required evidence is required")
        return self

    @property
    def target_binding(self) -> EffectTargetBinding:
        return EffectTargetBinding(provider=self.provider, tenant=self.tenant, environment=self.environment, resource=self.resource, credential_authority_ref=self.credential_authority_ref)

    @property
    def digest(self) -> str:
        return "sha256:" + canonical_digest(self.model_dump(mode="json"))

    def assert_parameters(self, parameters: Mapping[str, Any]) -> None:
        actual = "sha256:" + canonical_digest(dict(parameters))
        if actual != self.parameters_digest:
            raise PermissionError("effect parameters do not match effect contract")

    def assert_fresh(self, now: datetime) -> None:
        if now >= self.freshness:
            raise PermissionError("effect contract is stale")
        for provenance in self.read_provenance:
            provenance.assert_usable(now)

    def assert_claims(self, claims: Mapping[str, VerificationResult]) -> None:
        self.assert_claim_statuses({key: value.status for key, value in claims.items()})

    def assert_claim_statuses(self, claims: Mapping[str, Status | str]) -> None:
        for requirement in self.claim_requirements:
            raw = claims.get(requirement.claim_id)
            if raw is None:
                raise PermissionError(f"missing required claim evidence: {requirement.claim_id}")
            try:
                status = raw if isinstance(raw, Status) else Status(raw)
            except ValueError as exc:
                raise PermissionError(f"invalid claim status for {requirement.claim_id}") from exc
            if status is not requirement.required_status:
                raise PermissionError(f"claim {requirement.claim_id} is {status.value}; required {requirement.required_status.value}")

    def assert_target(self, target: EffectTargetBinding) -> None:
        if target != self.target_binding:
            raise PermissionError("effect target binding mismatch")


class AsyncEffectRecord(BaseModel):
    effect_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    state: EffectLifecycleState = EffectLifecycleState.REQUESTED
    provider_receipt_ref: str | None = None
    model_config = ConfigDict(extra="forbid", frozen=True)

    def transition(self, state: EffectLifecycleState, *, provider_receipt_ref: str | None = None, callback: ProviderCallbackEvidence | None = None, provider: str | None = None) -> AsyncEffectRecord:
        allowed = {
            EffectLifecycleState.REQUESTED: {EffectLifecycleState.ACCEPTED, EffectLifecycleState.FAILED},
            EffectLifecycleState.ACCEPTED: {EffectLifecycleState.PROCESSING, EffectLifecycleState.COMPLETED, EffectLifecycleState.FAILED},
            EffectLifecycleState.PROCESSING: {EffectLifecycleState.COMPLETED, EffectLifecycleState.FAILED},
            EffectLifecycleState.COMPLETED: {EffectLifecycleState.COMPENSATED},
            EffectLifecycleState.FAILED: set(),
            EffectLifecycleState.COMPENSATED: set(),
        }
        if state not in allowed[self.state]:
            raise ValueError(f"invalid async effect transition: {self.state.value} -> {state.value}")
        if callback is not None:
            if provider is None:
                raise ValueError("provider is required when callback evidence is supplied")
            callback.assert_verified(provider=provider, correlation_id=self.correlation_id)
        if state in {EffectLifecycleState.COMPLETED, EffectLifecycleState.COMPENSATED} and not (provider_receipt_ref or callback):
            raise ValueError("terminal successful transition requires provider receipt evidence")
        receipt_ref = provider_receipt_ref or (callback.signature_ref if callback else None) or self.provider_receipt_ref
        return self.model_copy(update={"state": state, "provider_receipt_ref": receipt_ref})


def parameters_digest(parameters: Mapping[str, Any]) -> str:
    return "sha256:" + canonical_digest(dict(parameters))


__all__ = [
    "AdapterCapabilityManifest",
    "AsyncEffectRecord",
    "AuthorityComposition",
    "AuthorityRequirement",
    "ClaimRequirement",
    "CompensationPolicy",
    "ConsequenceOperation",
    "EffectContract",
    "EffectLifecycleState",
    "EffectTargetBinding",
    "IdempotencyBinding",
    "ProviderCallbackEvidence",
    "ReadProvenance",
    "RepresentationIntegrity",
    "parameters_digest",
]
