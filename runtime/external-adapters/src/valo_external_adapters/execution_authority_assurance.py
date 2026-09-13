from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .authority_projection import AuthorityStateReference
from .contracts import Authority, Delegation, ProposedAction, Purpose, canonical_digest

LEASE_SIGNATURE_DOMAIN = b"VALO-EXECUTION-AUTHORITY-LEASE-V1\x00"
REVOCATION_STATE_SIGNATURE_DOMAIN = b"VALO-REVOCATION-STATE-V1\x00"
REVOCATION_NOTICE_SIGNATURE_DOMAIN = b"VALO-REVOCATION-NOTICE-V1\x00"
REVOCATION_ACK_SIGNATURE_DOMAIN = b"VALO-REVOCATION-ACK-V1\x00"
BANK_ACCEPTANCE_SIGNATURE_DOMAIN = b"VALO-BANK-ACCEPTANCE-V1\x00"
SETTLEMENT_SIGNATURE_DOMAIN = b"VALO-SETTLEMENT-EVIDENCE-V1\x00"


class ExecutionArtifactSigner(Protocol):
    signer_id: str
    key_id: str
    algorithm: str

    def sign(self, payload: bytes) -> str: ...


@dataclass(frozen=True)
class Ed25519ExecutionArtifactSigner:
    signer_id: str
    key_id: str
    _private_key: Ed25519PrivateKey
    algorithm: str = "Ed25519"

    @classmethod
    def from_private_key_bytes(
        cls,
        *,
        signer_id: str,
        key_id: str,
        private_key_bytes: bytes,
    ) -> Ed25519ExecutionArtifactSigner:
        if not signer_id or not key_id:
            raise ValueError("signer_id and key_id are required")
        if len(private_key_bytes) != 32:
            raise ValueError("Ed25519 private key seed must be exactly 32 bytes")
        return cls(
            signer_id=signer_id,
            key_id=key_id,
            _private_key=Ed25519PrivateKey.from_private_bytes(private_key_bytes),
        )

    def sign(self, payload: bytes) -> str:
        if not payload:
            raise ValueError("signature payload must not be empty")
        return _b64url_encode(self._private_key.sign(payload))

    def public_key(self) -> Ed25519PublicKey:
        return self._private_key.public_key()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _signature_input(domain: bytes, digest: str) -> bytes:
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("signature digest must be a lowercase SHA-256 hex digest")
    return domain + digest.encode("ascii")


def _verify_signature(
    *,
    public_key: Ed25519PublicKey,
    domain: bytes,
    digest: str,
    signature: str,
) -> None:
    if not signature:
        raise ValueError("signature is required")
    try:
        public_key.verify(_b64url_decode(signature), _signature_input(domain, digest))
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("artifact signature verification failed") from exc


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _signed_model(
    model: BaseModel,
    *,
    digest_field: str,
    signature_field: str,
    domain: bytes,
    signer: ExecutionArtifactSigner,
) -> dict[str, object]:
    if signer.algorithm != "Ed25519":
        raise ValueError("unsupported signature algorithm")
    digest = model.computed_digest  # type: ignore[attr-defined]
    signature = signer.sign(_signature_input(domain, digest))
    return {
        **model.model_dump(mode="python"),
        digest_field: digest,
        signature_field: signature,
    }


class AuthorityLeaseBasis(BaseModel):
    """Authority state a short-lived execution lease may only attenuate."""

    schema_version: Literal["authority_lease_basis.v1"] = "authority_lease_basis.v1"
    executor_id: str
    authority: Authority
    delegations: tuple[Delegation, ...] = ()
    purpose: Purpose
    authority_state: AuthorityStateReference
    evaluated_at: datetime
    valid_until: datetime
    basis_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"basis_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_basis(self) -> AuthorityLeaseBasis:
        if not self.executor_id:
            raise ValueError("executor_id is required")
        _require_aware(self.evaluated_at, "evaluated_at")
        _require_aware(self.valid_until, "valid_until")
        if not self.authority.is_active(self.evaluated_at):
            raise ValueError("authority is not active at basis evaluation")
        if not self.purpose.validity.is_active_at(self.evaluated_at):
            raise ValueError("purpose is not active at basis evaluation")
        if not (
            self.authority_state.observed_at
            <= self.evaluated_at
            < self.authority_state.valid_until
        ):
            raise ValueError("authority state is not fresh at basis evaluation")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("authority lease basis requires a positive validity window")

        upper_bounds = [
            self.authority.validity.valid_until,
            self.purpose.validity.valid_until,
            self.authority_state.valid_until,
        ]
        if (
            self.purpose.permitted_actions
            and self.authority.capability not in self.purpose.permitted_actions
        ):
            raise ValueError("authority capability is outside purpose")
        if (
            self.authority.scope
            and self.purpose.scope
            and not set(self.purpose.scope).issubset(set(self.authority.scope))
        ):
            raise ValueError("purpose scope widens authority scope")

        if not self.delegations:
            if self.executor_id != self.authority.principal:
                raise ValueError("executor requires an explicit delegation chain")
        else:
            previous_actor = self.authority.principal
            effective_scope = set(self.authority.scope) if self.authority.scope else None
            for delegation in self.delegations:
                if delegation.authority_ref != self.authority.authority_id:
                    raise ValueError("delegation references another authority")
                if delegation.delegator != previous_actor:
                    raise ValueError("delegation chain is discontinuous")
                if not delegation.is_active(self.evaluated_at):
                    raise ValueError("delegation is not active at basis evaluation")
                if delegation.scope_reduction:
                    reduced_scope = set(delegation.scope_reduction)
                    if effective_scope is not None and not reduced_scope.issubset(
                        effective_scope
                    ):
                        raise ValueError("delegation scope widens parent authority")
                    effective_scope = reduced_scope
                if delegation.purpose_restriction and not {
                    self.purpose.purpose_id,
                    self.purpose.purpose_type,
                }.intersection(delegation.purpose_restriction):
                    raise ValueError("purpose is outside delegation restriction")
                upper_bounds.append(delegation.validity.valid_until)
                previous_actor = delegation.delegate
            if previous_actor != self.executor_id:
                raise ValueError("delegation chain does not terminate at executor")

        if self.valid_until > min(upper_bounds):
            raise ValueError("authority lease basis outlives an authoritative dependency")
        if self.basis_digest and self.basis_digest != self.computed_digest:
            raise ValueError("authority lease basis digest mismatch")
        return self


def seal_authority_lease_basis(
    *,
    executor_id: str,
    authority: Authority,
    delegations: tuple[Delegation, ...],
    purpose: Purpose,
    authority_state: AuthorityStateReference,
    evaluated_at: datetime,
) -> AuthorityLeaseBasis:
    upper_bounds = [
        authority.validity.valid_until,
        purpose.validity.valid_until,
        authority_state.valid_until,
        *(item.validity.valid_until for item in delegations),
    ]
    unsealed = AuthorityLeaseBasis(
        executor_id=executor_id,
        authority=authority,
        delegations=delegations,
        purpose=purpose,
        authority_state=authority_state,
        evaluated_at=evaluated_at,
        valid_until=min(upper_bounds),
    )
    return AuthorityLeaseBasis.model_validate(
        {**unsealed.model_dump(mode="python"), "basis_digest": unsealed.computed_digest}
    )


class RevocationNotice(BaseModel):
    schema_version: Literal["revocation_notice.v1"] = "revocation_notice.v1"
    notice_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope_id: str
    prior_epoch: int = Field(ge=0)
    new_epoch: int = Field(gt=0)
    revoked_refs: tuple[str, ...]
    effective_at: datetime
    issuer_id: str
    key_id: str
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signature: str = ""
    notice_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"signature", "notice_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_notice(self) -> RevocationNotice:
        if not self.scope_id or not self.issuer_id or not self.key_id:
            raise ValueError("revocation notice identity fields are required")
        if self.new_epoch != self.prior_epoch + 1:
            raise ValueError("revocation epoch must advance exactly once per notice")
        if not self.revoked_refs or len(set(self.revoked_refs)) != len(self.revoked_refs):
            raise ValueError("revoked_refs must be non-empty and unique")
        _require_aware(self.effective_at, "effective_at")
        if self.notice_digest and self.notice_digest != self.computed_digest:
            raise ValueError("revocation notice digest mismatch")
        return self


def issue_revocation_notice(
    *,
    scope_id: str,
    prior_epoch: int,
    revoked_refs: tuple[str, ...],
    effective_at: datetime,
    signer: ExecutionArtifactSigner,
) -> RevocationNotice:
    notice_id = canonical_digest(
        {
            "scope_id": scope_id,
            "prior_epoch": prior_epoch,
            "revoked_refs": sorted(revoked_refs),
            "effective_at": effective_at.isoformat(),
            "issuer_id": signer.signer_id,
        }
    )
    unsealed = RevocationNotice(
        notice_id=notice_id,
        scope_id=scope_id,
        prior_epoch=prior_epoch,
        new_epoch=prior_epoch + 1,
        revoked_refs=revoked_refs,
        effective_at=effective_at,
        issuer_id=signer.signer_id,
        key_id=signer.key_id,
    )
    return RevocationNotice.model_validate(
        _signed_model(
            unsealed,
            digest_field="notice_digest",
            signature_field="signature",
            domain=REVOCATION_NOTICE_SIGNATURE_DOMAIN,
            signer=signer,
        )
    )


def verify_revocation_notice(
    notice: RevocationNotice,
    *,
    public_key: Ed25519PublicKey,
) -> None:
    if notice.notice_digest != notice.computed_digest:
        raise ValueError("revocation notice is unsealed or tampered")
    _verify_signature(
        public_key=public_key,
        domain=REVOCATION_NOTICE_SIGNATURE_DOMAIN,
        digest=notice.notice_digest,
        signature=notice.signature,
    )


class RevocationEpochState(BaseModel):
    """Signed authoritative revocation epoch for one authority scope."""

    schema_version: Literal["revocation_epoch_state.v2"] = "revocation_epoch_state.v2"
    scope_id: str
    epoch: int = Field(ge=0)
    observed_at: datetime
    valid_until: datetime
    source_ref: str
    issuer_id: str
    key_id: str
    latest_notice_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signature: str = ""
    state_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"signature", "state_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_state(self) -> RevocationEpochState:
        if not self.scope_id or not self.source_ref or not self.issuer_id or not self.key_id:
            raise ValueError("revocation epoch state identity fields are required")
        _require_aware(self.observed_at, "observed_at")
        _require_aware(self.valid_until, "valid_until")
        if self.valid_until <= self.observed_at:
            raise ValueError("revocation epoch state requires a positive validity window")
        if self.epoch == 0 and self.latest_notice_digest is not None:
            raise ValueError("epoch zero cannot reference a revocation notice")
        if self.epoch > 0 and self.latest_notice_digest is None:
            raise ValueError("non-zero epoch requires the latest revocation notice digest")
        if self.state_digest and self.state_digest != self.computed_digest:
            raise ValueError("revocation epoch state digest mismatch")
        return self


def seal_revocation_epoch_state(
    *,
    scope_id: str,
    epoch: int,
    observed_at: datetime,
    valid_until: datetime,
    source_ref: str,
    signer: ExecutionArtifactSigner,
    latest_notice: RevocationNotice | None = None,
    notice_public_key: Ed25519PublicKey | None = None,
) -> RevocationEpochState:
    latest_notice_digest: str | None = None
    if epoch == 0:
        if latest_notice is not None:
            raise ValueError("epoch zero cannot be created from a revocation notice")
    else:
        if latest_notice is None or notice_public_key is None:
            raise ValueError("non-zero epoch requires a verified revocation notice")
        verify_revocation_notice(latest_notice, public_key=notice_public_key)
        if latest_notice.scope_id != scope_id:
            raise ValueError("revocation notice scope differs from epoch state")
        if latest_notice.new_epoch != epoch:
            raise ValueError("revocation notice does not produce requested epoch")
        if latest_notice.effective_at > observed_at:
            raise ValueError("revocation epoch cannot precede notice effectiveness")
        latest_notice_digest = latest_notice.notice_digest

    unsealed = RevocationEpochState(
        scope_id=scope_id,
        epoch=epoch,
        observed_at=observed_at,
        valid_until=valid_until,
        source_ref=source_ref,
        issuer_id=signer.signer_id,
        key_id=signer.key_id,
        latest_notice_digest=latest_notice_digest,
    )
    return RevocationEpochState.model_validate(
        _signed_model(
            unsealed,
            digest_field="state_digest",
            signature_field="signature",
            domain=REVOCATION_STATE_SIGNATURE_DOMAIN,
            signer=signer,
        )
    )


def verify_revocation_epoch_state(
    state: RevocationEpochState,
    *,
    public_key: Ed25519PublicKey,
) -> None:
    if state.state_digest != state.computed_digest:
        raise ValueError("revocation epoch state is unsealed or tampered")
    _verify_signature(
        public_key=public_key,
        domain=REVOCATION_STATE_SIGNATURE_DOMAIN,
        digest=state.state_digest,
        signature=state.signature,
    )


class RevocationAcknowledgement(BaseModel):
    """Execution node acknowledgement of one exact signed epoch state."""

    schema_version: Literal["revocation_ack.v2"] = "revocation_ack.v2"
    node_id: str
    scope_id: str
    epoch: int = Field(ge=0)
    source_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    acknowledged_at: datetime
    key_id: str
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signature: str = ""
    acknowledgement_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(
            mode="json",
            exclude={"signature", "acknowledgement_digest"},
        )

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_acknowledgement(self) -> RevocationAcknowledgement:
        if not self.node_id or not self.scope_id or not self.key_id:
            raise ValueError("revocation acknowledgement identity fields are required")
        _require_aware(self.acknowledged_at, "acknowledged_at")
        if (
            self.acknowledgement_digest
            and self.acknowledgement_digest != self.computed_digest
        ):
            raise ValueError("revocation acknowledgement digest mismatch")
        return self


def issue_revocation_acknowledgement(
    *,
    node_id: str,
    source_state: RevocationEpochState,
    source_public_key: Ed25519PublicKey,
    acknowledged_at: datetime,
    signer: ExecutionArtifactSigner,
) -> RevocationAcknowledgement:
    if signer.signer_id != node_id:
        raise ValueError("revocation acknowledgement signer must be the node")
    verify_revocation_epoch_state(source_state, public_key=source_public_key)
    if acknowledged_at < source_state.observed_at:
        raise ValueError("revocation state cannot be acknowledged before observation")
    if acknowledged_at >= source_state.valid_until:
        raise ValueError("expired revocation state cannot be acknowledged")
    unsealed = RevocationAcknowledgement(
        node_id=node_id,
        scope_id=source_state.scope_id,
        epoch=source_state.epoch,
        source_state_digest=source_state.state_digest,
        acknowledged_at=acknowledged_at,
        key_id=signer.key_id,
    )
    return RevocationAcknowledgement.model_validate(
        _signed_model(
            unsealed,
            digest_field="acknowledgement_digest",
            signature_field="signature",
            domain=REVOCATION_ACK_SIGNATURE_DOMAIN,
            signer=signer,
        )
    )


def verify_revocation_acknowledgement(
    acknowledgement: RevocationAcknowledgement,
    *,
    public_key: Ed25519PublicKey,
) -> None:
    if acknowledgement.acknowledgement_digest != acknowledgement.computed_digest:
        raise ValueError("revocation acknowledgement is unsealed or tampered")
    _verify_signature(
        public_key=public_key,
        domain=REVOCATION_ACK_SIGNATURE_DOMAIN,
        digest=acknowledgement.acknowledgement_digest,
        signature=acknowledgement.signature,
    )


class RevocationCheckpointStatus(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class RevocationCheckpoint(BaseModel):
    schema_version: Literal["revocation_checkpoint.v2"] = "revocation_checkpoint.v2"
    scope_id: str
    source_epoch: int = Field(ge=0)
    node_epoch: int | None = Field(default=None, ge=0)
    source_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    acknowledgement_digest: str | None = None
    checked_at: datetime
    valid_until: datetime | None
    status: RevocationCheckpointStatus
    failure_reasons: tuple[str, ...] = ()
    checkpoint_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"checkpoint_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_checkpoint(self) -> RevocationCheckpoint:
        _require_aware(self.checked_at, "checked_at")
        if self.status is RevocationCheckpointStatus.CURRENT:
            if self.failure_reasons:
                raise ValueError("CURRENT checkpoint cannot have failure reasons")
            if self.valid_until is None or self.valid_until <= self.checked_at:
                raise ValueError("CURRENT checkpoint requires a validity window")
        else:
            if not self.failure_reasons:
                raise ValueError("non-current checkpoint requires failure reasons")
            if self.valid_until is not None:
                raise ValueError("non-current checkpoint cannot claim a validity window")
        if self.checkpoint_digest and self.checkpoint_digest != self.computed_digest:
            raise ValueError("revocation checkpoint digest mismatch")
        return self


def assess_revocation_checkpoint(
    *,
    source_state: RevocationEpochState,
    source_public_key: Ed25519PublicKey,
    acknowledgement: RevocationAcknowledgement | None,
    node_public_key: Ed25519PublicKey | None,
    checked_at: datetime,
    max_sync_age_seconds: int,
) -> RevocationCheckpoint:
    if max_sync_age_seconds <= 0:
        raise ValueError("max_sync_age_seconds must be positive")
    _require_aware(checked_at, "checked_at")

    reasons: list[str] = []
    try:
        verify_revocation_epoch_state(source_state, public_key=source_public_key)
    except ValueError:
        reasons.append("REVOCATION_SOURCE_SIGNATURE_INVALID")

    sync_bound = source_state.observed_at + timedelta(seconds=max_sync_age_seconds)
    if checked_at < source_state.observed_at:
        reasons.append("REVOCATION_STATE_FROM_FUTURE")
    if checked_at >= source_state.valid_until:
        reasons.append("REVOCATION_STATE_EXPIRED")
    if checked_at >= sync_bound:
        reasons.append("REVOCATION_STATE_TOO_OLD")

    node_epoch: int | None = None
    acknowledgement_digest: str | None = None
    acknowledgement_bound: datetime | None = None
    if acknowledgement is None:
        reasons.append("MISSING_NODE_ACKNOWLEDGEMENT")
    else:
        node_epoch = acknowledgement.epoch
        acknowledgement_digest = acknowledgement.acknowledgement_digest
        if node_public_key is None:
            reasons.append("MISSING_NODE_VERIFICATION_KEY")
        else:
            try:
                verify_revocation_acknowledgement(
                    acknowledgement,
                    public_key=node_public_key,
                )
            except ValueError:
                reasons.append("ACKNOWLEDGEMENT_SIGNATURE_INVALID")
        if acknowledgement.scope_id != source_state.scope_id:
            reasons.append("ACKNOWLEDGEMENT_SCOPE_MISMATCH")
        if acknowledgement.source_state_digest != source_state.state_digest:
            reasons.append("ACKNOWLEDGEMENT_STATE_MISMATCH")
        if acknowledgement.acknowledged_at > checked_at:
            reasons.append("ACKNOWLEDGEMENT_FROM_FUTURE")
        acknowledgement_bound = acknowledgement.acknowledged_at + timedelta(
            seconds=max_sync_age_seconds
        )
        if checked_at >= acknowledgement_bound:
            reasons.append("ACKNOWLEDGEMENT_TOO_OLD")
        if acknowledgement.epoch < source_state.epoch:
            reasons.append("NODE_EPOCH_BEHIND")
        elif acknowledgement.epoch > source_state.epoch:
            reasons.append("SOURCE_EPOCH_BEHIND_NODE")

    reasons = list(dict.fromkeys(reasons))
    if not reasons:
        status = RevocationCheckpointStatus.CURRENT
    elif "NODE_EPOCH_BEHIND" in reasons:
        status = RevocationCheckpointStatus.STALE
    else:
        status = RevocationCheckpointStatus.UNKNOWN

    valid_until = None
    if status is RevocationCheckpointStatus.CURRENT:
        assert acknowledgement_bound is not None
        valid_until = min(source_state.valid_until, sync_bound, acknowledgement_bound)

    unsealed = RevocationCheckpoint(
        scope_id=source_state.scope_id,
        source_epoch=source_state.epoch,
        node_epoch=node_epoch,
        source_state_digest=source_state.state_digest,
        acknowledgement_digest=acknowledgement_digest,
        checked_at=checked_at,
        valid_until=valid_until,
        status=status,
        failure_reasons=tuple(reasons),
    )
    return RevocationCheckpoint.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "checkpoint_digest": unsealed.computed_digest,
        }
    )


class ExecutionAuthorityLease(BaseModel):
    schema_version: Literal["execution_authority_lease.v1"] = (
        "execution_authority_lease.v1"
    )
    lease_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    issuer_id: str
    key_id: str
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signature: str = ""
    basis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_id: str
    executor_id: str
    capability: str
    allowed_targets: tuple[str, ...]
    purpose_id: str
    audience: tuple[str, ...]
    constraints_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    delegation_chain_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_state_dependency_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    currency: str | None = None
    max_single_amount_minor: int | None = Field(default=None, gt=0)
    max_cumulative_amount_minor: int | None = Field(default=None, gt=0)
    max_actions: int | None = Field(default=None, gt=0)
    not_before: datetime
    expires_at: datetime
    revocation_scope_id: str
    revocation_epoch: int = Field(ge=0)
    revocation_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    nonce: str
    lease_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"signature", "lease_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_lease(self) -> ExecutionAuthorityLease:
        required = (
            self.issuer_id,
            self.key_id,
            self.authority_id,
            self.executor_id,
            self.capability,
            self.purpose_id,
            self.revocation_scope_id,
            self.nonce,
        )
        if any(not item for item in required):
            raise ValueError("execution authority lease identity fields are required")
        if not self.allowed_targets or len(set(self.allowed_targets)) != len(
            self.allowed_targets
        ):
            raise ValueError("allowed_targets must be non-empty and unique")
        if not self.audience or len(set(self.audience)) != len(self.audience):
            raise ValueError("audience must be non-empty and unique")
        _require_aware(self.not_before, "not_before")
        _require_aware(self.expires_at, "expires_at")
        if self.expires_at <= self.not_before:
            raise ValueError("execution authority lease requires a positive validity window")
        if self.max_single_amount_minor is not None and not self.currency:
            raise ValueError("financial lease limits require currency")
        if self.max_cumulative_amount_minor is not None:
            if not self.currency:
                raise ValueError("financial lease limits require currency")
            if (
                self.max_single_amount_minor is not None
                and self.max_cumulative_amount_minor < self.max_single_amount_minor
            ):
                raise ValueError("cumulative amount cannot be below single-action limit")
        if self.currency is not None and not self.currency.strip():
            raise ValueError("currency cannot be blank")
        if self.lease_digest and self.lease_digest != self.computed_digest:
            raise ValueError("execution authority lease digest mismatch")
        return self


def _effective_scope(basis: AuthorityLeaseBasis) -> set[str] | None:
    scope = set(basis.authority.scope) if basis.authority.scope else None
    if basis.purpose.scope:
        purpose_scope = set(basis.purpose.scope)
        scope = purpose_scope if scope is None else scope.intersection(purpose_scope)
    for delegation in basis.delegations:
        if delegation.scope_reduction:
            reduced = set(delegation.scope_reduction)
            scope = reduced if scope is None else scope.intersection(reduced)
    return scope


def issue_execution_authority_lease(
    *,
    basis: AuthorityLeaseBasis,
    revocation_state: RevocationEpochState,
    revocation_public_key: Ed25519PublicKey,
    signer: ExecutionArtifactSigner,
    allowed_targets: tuple[str, ...],
    audience: tuple[str, ...],
    issued_at: datetime,
    nonce: str,
    requested_expires_at: datetime | None = None,
    currency: str | None = None,
    max_single_amount_minor: int | None = None,
    max_cumulative_amount_minor: int | None = None,
    max_actions: int | None = None,
) -> ExecutionAuthorityLease:
    if basis.basis_digest != basis.computed_digest:
        raise ValueError("authority lease basis is unsealed or tampered")
    verify_revocation_epoch_state(revocation_state, public_key=revocation_public_key)
    if signer.algorithm != "Ed25519":
        raise ValueError("unsupported lease signature algorithm")
    if not nonce:
        raise ValueError("lease nonce is required")
    _require_aware(issued_at, "issued_at")
    if not (basis.evaluated_at <= issued_at < basis.valid_until):
        raise ValueError("authority lease basis is not current at issuance")
    if not (
        revocation_state.observed_at <= issued_at < revocation_state.valid_until
    ):
        raise ValueError("revocation epoch state is not current at issuance")

    effective_scope = _effective_scope(basis)
    if not allowed_targets:
        raise ValueError("lease must explicitly bound allowed targets")
    if effective_scope is not None and not set(allowed_targets).issubset(effective_scope):
        raise ValueError("lease targets widen principal authority")
    if not audience:
        raise ValueError("lease audience is required")

    expires_at = min(basis.valid_until, revocation_state.valid_until)
    if requested_expires_at is not None:
        _require_aware(requested_expires_at, "requested_expires_at")
        expires_at = min(expires_at, requested_expires_at)
    if expires_at <= issued_at:
        raise ValueError("execution authority lease has no usable validity window")

    lease_id = canonical_digest(
        {
            "basis_digest": basis.basis_digest,
            "issuer_id": signer.signer_id,
            "issued_at": issued_at.isoformat(),
            "nonce": nonce,
            "revocation_epoch": revocation_state.epoch,
            "revocation_state_digest": revocation_state.state_digest,
        }
    )
    unsealed = ExecutionAuthorityLease(
        lease_id=lease_id,
        issuer_id=signer.signer_id,
        key_id=signer.key_id,
        basis_digest=basis.basis_digest,
        authority_id=basis.authority.authority_id,
        executor_id=basis.executor_id,
        capability=basis.authority.capability,
        allowed_targets=allowed_targets,
        purpose_id=basis.purpose.purpose_id,
        audience=audience,
        constraints_digest=canonical_digest(basis.authority.constraints),
        delegation_chain_digest=canonical_digest(
            [item.model_dump(mode="json") for item in basis.delegations]
        ),
        authority_state_dependency_digest=basis.authority_state.dependency_digest,
        currency=currency,
        max_single_amount_minor=max_single_amount_minor,
        max_cumulative_amount_minor=max_cumulative_amount_minor,
        max_actions=max_actions,
        not_before=issued_at,
        expires_at=expires_at,
        revocation_scope_id=revocation_state.scope_id,
        revocation_epoch=revocation_state.epoch,
        revocation_state_digest=revocation_state.state_digest,
        nonce=nonce,
    )
    return ExecutionAuthorityLease.model_validate(
        _signed_model(
            unsealed,
            digest_field="lease_digest",
            signature_field="signature",
            domain=LEASE_SIGNATURE_DOMAIN,
            signer=signer,
        )
    )


def verify_execution_authority_lease(
    lease: ExecutionAuthorityLease,
    *,
    basis: AuthorityLeaseBasis,
    public_key: Ed25519PublicKey,
) -> None:
    if lease.lease_digest != lease.computed_digest:
        raise ValueError("execution authority lease is unsealed or tampered")
    if basis.basis_digest != basis.computed_digest:
        raise ValueError("authority lease basis is unsealed or tampered")
    if lease.basis_digest != basis.basis_digest:
        raise ValueError("execution authority lease basis mismatch")
    if lease.authority_id != basis.authority.authority_id:
        raise ValueError("execution authority lease authority mismatch")
    if lease.executor_id != basis.executor_id:
        raise ValueError("execution authority lease executor mismatch")
    if lease.capability != basis.authority.capability:
        raise ValueError("execution authority lease capability mismatch")
    if lease.purpose_id != basis.purpose.purpose_id:
        raise ValueError("execution authority lease purpose mismatch")
    if lease.constraints_digest != canonical_digest(basis.authority.constraints):
        raise ValueError("execution authority lease constraints mismatch")
    if lease.delegation_chain_digest != canonical_digest(
        [item.model_dump(mode="json") for item in basis.delegations]
    ):
        raise ValueError("execution authority lease delegation chain mismatch")
    if (
        lease.authority_state_dependency_digest
        != basis.authority_state.dependency_digest
    ):
        raise ValueError("execution authority lease authority-state mismatch")
    effective_scope = _effective_scope(basis)
    if effective_scope is not None and not set(lease.allowed_targets).issubset(
        effective_scope
    ):
        raise ValueError("execution authority lease widens principal scope")
    if lease.expires_at > basis.valid_until:
        raise ValueError("execution authority lease outlives principal basis")
    _verify_signature(
        public_key=public_key,
        domain=LEASE_SIGNATURE_DOMAIN,
        digest=lease.lease_digest,
        signature=lease.signature,
    )


class LeaseEvaluationDisposition(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class ExecutionLeaseEvaluation(BaseModel):
    schema_version: Literal["execution_lease_evaluation.v1"] = (
        "execution_lease_evaluation.v1"
    )
    lease_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    basis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    revocation_checkpoint_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_nonce: str
    endpoint_id: str
    evaluated_at: datetime
    valid_until: datetime | None
    disposition: LeaseEvaluationDisposition
    failure_reasons: tuple[str, ...] = ()
    evaluation_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    requires_fresh_reht: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"evaluation_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_evaluation(self) -> ExecutionLeaseEvaluation:
        _require_aware(self.evaluated_at, "evaluated_at")
        if self.disposition is LeaseEvaluationDisposition.ELIGIBLE:
            if self.failure_reasons:
                raise ValueError("ELIGIBLE lease evaluation cannot have failure reasons")
            if self.valid_until is None or self.valid_until <= self.evaluated_at:
                raise ValueError("ELIGIBLE lease evaluation requires a validity window")
        else:
            if not self.failure_reasons:
                raise ValueError("NOT_ELIGIBLE lease evaluation requires failure reasons")
            if self.valid_until is not None:
                raise ValueError("NOT_ELIGIBLE lease evaluation cannot claim validity")
        if self.evaluation_digest and self.evaluation_digest != self.computed_digest:
            raise ValueError("execution lease evaluation digest mismatch")
        return self


def evaluate_execution_authority_lease(
    *,
    lease: ExecutionAuthorityLease,
    basis: AuthorityLeaseBasis,
    lease_public_key: Ed25519PublicKey,
    checkpoint: RevocationCheckpoint,
    action: ProposedAction,
    endpoint_id: str,
    action_nonce: str,
    evaluated_at: datetime,
    amount_minor: int | None = None,
    cumulative_amount_minor_before: int = 0,
    actions_used_before: int = 0,
    seen_action_nonces: frozenset[str] = frozenset(),
) -> ExecutionLeaseEvaluation:
    _require_aware(evaluated_at, "evaluated_at")
    reasons: list[str] = []
    try:
        verify_execution_authority_lease(
            lease,
            basis=basis,
            public_key=lease_public_key,
        )
    except ValueError as exc:
        reasons.append(f"LEASE_INTEGRITY:{exc}")

    if checkpoint.checkpoint_digest != checkpoint.computed_digest:
        reasons.append("REVOCATION_CHECKPOINT_TAMPERED")
    if checkpoint.status is not RevocationCheckpointStatus.CURRENT:
        reasons.append(f"REVOCATION_{checkpoint.status.value}")
    if checkpoint.scope_id != lease.revocation_scope_id:
        reasons.append("REVOCATION_SCOPE_MISMATCH")
    if checkpoint.source_epoch != lease.revocation_epoch:
        reasons.append("LEASE_REVOCATION_EPOCH_MISMATCH")
    if checkpoint.node_epoch != checkpoint.source_epoch:
        reasons.append("NODE_REVOCATION_EPOCH_MISMATCH")
    if checkpoint.source_state_digest != lease.revocation_state_digest:
        reasons.append("LEASE_REVOCATION_STATE_MISMATCH")
    if checkpoint.valid_until is None or not (
        checkpoint.checked_at <= evaluated_at < checkpoint.valid_until
    ):
        reasons.append("REVOCATION_CHECKPOINT_NOT_FRESH")

    if not action_nonce:
        reasons.append("ACTION_NONCE_REQUIRED")
    elif action_nonce in seen_action_nonces:
        reasons.append("ACTION_NONCE_REPLAY")
    if not endpoint_id or endpoint_id not in lease.audience:
        reasons.append("ENDPOINT_OUTSIDE_LEASE_AUDIENCE")
    if not (lease.not_before <= evaluated_at < lease.expires_at):
        reasons.append("LEASE_NOT_ACTIVE")
    if action.capability != lease.capability:
        reasons.append("ACTION_CAPABILITY_OUTSIDE_LEASE")
    if action.target not in lease.allowed_targets:
        reasons.append("ACTION_TARGET_OUTSIDE_LEASE")
    if action.purpose_id != lease.purpose_id:
        reasons.append("ACTION_PURPOSE_OUTSIDE_LEASE")

    if amount_minor is not None and amount_minor < 0:
        reasons.append("NEGATIVE_ACTION_AMOUNT")
    financial_limits_present = (
        lease.max_single_amount_minor is not None
        or lease.max_cumulative_amount_minor is not None
    )
    if financial_limits_present and amount_minor is None:
        reasons.append("ACTION_AMOUNT_REQUIRED")
    if amount_minor is not None:
        if (
            lease.max_single_amount_minor is not None
            and amount_minor > lease.max_single_amount_minor
        ):
            reasons.append("SINGLE_ACTION_AMOUNT_EXCEEDED")
        if (
            lease.max_cumulative_amount_minor is not None
            and cumulative_amount_minor_before + amount_minor
            > lease.max_cumulative_amount_minor
        ):
            reasons.append("CUMULATIVE_AMOUNT_EXCEEDED")
    if lease.max_actions is not None and actions_used_before >= lease.max_actions:
        reasons.append("ACTION_COUNT_EXCEEDED")

    reasons = list(dict.fromkeys(reasons))
    disposition = (
        LeaseEvaluationDisposition.ELIGIBLE
        if not reasons
        else LeaseEvaluationDisposition.NOT_ELIGIBLE
    )
    valid_until = None
    if disposition is LeaseEvaluationDisposition.ELIGIBLE:
        assert checkpoint.valid_until is not None
        valid_until = min(lease.expires_at, basis.valid_until, checkpoint.valid_until)
        if valid_until <= evaluated_at:
            reasons.append("LEASE_EVALUATION_HAS_NO_VALIDITY")
            disposition = LeaseEvaluationDisposition.NOT_ELIGIBLE
            valid_until = None

    action_digest = canonical_digest(action.model_dump(mode="json"))
    unsealed = ExecutionLeaseEvaluation(
        lease_digest=lease.lease_digest,
        basis_digest=basis.basis_digest,
        revocation_checkpoint_digest=checkpoint.checkpoint_digest,
        action_id=action.action_id,
        action_digest=action_digest,
        action_nonce=action_nonce,
        endpoint_id=endpoint_id,
        evaluated_at=evaluated_at,
        valid_until=valid_until,
        disposition=disposition,
        failure_reasons=tuple(reasons),
    )
    return ExecutionLeaseEvaluation.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "evaluation_digest": unsealed.computed_digest,
        }
    )


class BankAcceptanceDisposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    STEP_UP = "STEP_UP"


class BankExecutionAcceptance(BaseModel):
    schema_version: Literal["bank_execution_acceptance.v1"] = (
        "bank_execution_acceptance.v1"
    )
    acceptance_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    bank_id: str
    key_id: str
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signature: str = ""
    customer_ref: str
    account_binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_ref: str
    lease_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    lease_evaluation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    revocation_checkpoint_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reht_decision_ref: str
    reht_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reht_disposition: str
    racs_decision_ref: str
    racs_decision_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    racs_disposition: str
    bank_policy_version: str
    aml_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    sanctions_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_at: datetime
    valid_until: datetime | None
    disposition: BankAcceptanceDisposition
    failure_reasons: tuple[str, ...] = ()
    acceptance_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"signature", "acceptance_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_acceptance(self) -> BankExecutionAcceptance:
        required = (
            self.bank_id,
            self.key_id,
            self.customer_ref,
            self.action_id,
            self.execution_ref,
            self.reht_decision_ref,
            self.reht_disposition,
            self.racs_decision_ref,
            self.racs_disposition,
            self.bank_policy_version,
        )
        if any(not item for item in required):
            raise ValueError("bank acceptance identity and decision fields are required")
        _require_aware(self.evaluated_at, "evaluated_at")
        if self.disposition is BankAcceptanceDisposition.ACCEPTED:
            if self.failure_reasons:
                raise ValueError("ACCEPTED bank decision cannot have failure reasons")
            if self.valid_until is None or self.valid_until <= self.evaluated_at:
                raise ValueError("ACCEPTED bank decision requires a validity window")
        else:
            if not self.failure_reasons:
                raise ValueError("non-accepted bank decision requires failure reasons")
            if self.valid_until is not None:
                raise ValueError("non-accepted bank decision cannot claim validity")
        if self.acceptance_digest and self.acceptance_digest != self.computed_digest:
            raise ValueError("bank acceptance digest mismatch")
        return self


def issue_bank_execution_acceptance(
    *,
    signer: ExecutionArtifactSigner,
    lease: ExecutionAuthorityLease,
    lease_evaluation: ExecutionLeaseEvaluation,
    action: ProposedAction,
    execution_ref: str,
    customer_ref: str,
    account_binding_digest: str,
    reht_decision_ref: str,
    reht_decision_digest: str,
    reht_disposition: str,
    racs_decision_ref: str,
    racs_decision_digest: str,
    racs_disposition: str,
    bank_policy_version: str,
    aml_state_digest: str,
    sanctions_state_digest: str,
    evaluated_at: datetime,
    requested_valid_until: datetime | None = None,
    disposition: BankAcceptanceDisposition = BankAcceptanceDisposition.ACCEPTED,
    failure_reasons: tuple[str, ...] = (),
) -> BankExecutionAcceptance:
    if lease.lease_digest != lease.computed_digest:
        raise ValueError("execution authority lease is unsealed or tampered")
    if lease_evaluation.evaluation_digest != lease_evaluation.computed_digest:
        raise ValueError("execution lease evaluation is unsealed or tampered")
    action_digest = canonical_digest(action.model_dump(mode="json"))
    if lease_evaluation.action_digest != action_digest:
        raise ValueError("bank acceptance action differs from lease evaluation")
    if lease_evaluation.lease_digest != lease.lease_digest:
        raise ValueError("bank acceptance lease binding mismatch")
    if disposition is BankAcceptanceDisposition.ACCEPTED:
        if lease_evaluation.disposition is not LeaseEvaluationDisposition.ELIGIBLE:
            raise ValueError("bank cannot accept an ineligible execution lease")
        if reht_disposition != "ALLOW":
            raise ValueError("bank acceptance requires REHT ALLOW")
        if racs_disposition not in {"ALLOW", "MODIFY"}:
            raise ValueError("bank acceptance requires RACS ALLOW or MODIFY")
        if failure_reasons:
            raise ValueError("accepted bank execution cannot carry failure reasons")
    elif not failure_reasons:
        raise ValueError("non-accepted bank execution requires failure reasons")

    valid_until = None
    if disposition is BankAcceptanceDisposition.ACCEPTED:
        if lease_evaluation.valid_until is None:
            raise ValueError("eligible lease evaluation has no validity window")
        valid_until = lease_evaluation.valid_until
        if requested_valid_until is not None:
            valid_until = min(valid_until, requested_valid_until)
        if valid_until <= evaluated_at:
            raise ValueError("bank acceptance has no usable validity window")

    acceptance_id = canonical_digest(
        {
            "bank_id": signer.signer_id,
            "action_digest": action_digest,
            "execution_ref": execution_ref,
            "lease_evaluation_digest": lease_evaluation.evaluation_digest,
            "evaluated_at": evaluated_at.isoformat(),
        }
    )
    unsealed = BankExecutionAcceptance(
        acceptance_id=acceptance_id,
        bank_id=signer.signer_id,
        key_id=signer.key_id,
        customer_ref=customer_ref,
        account_binding_digest=account_binding_digest,
        action_id=action.action_id,
        action_digest=action_digest,
        execution_ref=execution_ref,
        lease_digest=lease.lease_digest,
        lease_evaluation_digest=lease_evaluation.evaluation_digest,
        revocation_checkpoint_digest=lease_evaluation.revocation_checkpoint_digest,
        reht_decision_ref=reht_decision_ref,
        reht_decision_digest=reht_decision_digest,
        reht_disposition=reht_disposition,
        racs_decision_ref=racs_decision_ref,
        racs_decision_digest=racs_decision_digest,
        racs_disposition=racs_disposition,
        bank_policy_version=bank_policy_version,
        aml_state_digest=aml_state_digest,
        sanctions_state_digest=sanctions_state_digest,
        evaluated_at=evaluated_at,
        valid_until=valid_until,
        disposition=disposition,
        failure_reasons=failure_reasons,
    )
    return BankExecutionAcceptance.model_validate(
        _signed_model(
            unsealed,
            digest_field="acceptance_digest",
            signature_field="signature",
            domain=BANK_ACCEPTANCE_SIGNATURE_DOMAIN,
            signer=signer,
        )
    )


def verify_bank_execution_acceptance(
    acceptance: BankExecutionAcceptance,
    *,
    public_key: Ed25519PublicKey,
) -> None:
    if acceptance.acceptance_digest != acceptance.computed_digest:
        raise ValueError("bank execution acceptance is unsealed or tampered")
    _verify_signature(
        public_key=public_key,
        domain=BANK_ACCEPTANCE_SIGNATURE_DOMAIN,
        digest=acceptance.acceptance_digest,
        signature=acceptance.signature,
    )


class SettlementStatus(StrEnum):
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    REVERSED = "REVERSED"


class SettlementEvidence(BaseModel):
    schema_version: Literal["settlement_evidence.v1"] = "settlement_evidence.v1"
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    signer_id: str
    key_id: str
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signature: str = ""
    bank_id: str
    bank_acceptance_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_ref: str
    rail: str
    effect_ref: str | None
    status: SettlementStatus
    committed_at: datetime | None
    recorded_at: datetime
    external_receipt_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    settlement_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"signature", "settlement_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_settlement(self) -> SettlementEvidence:
        if not self.signer_id or not self.key_id or not self.bank_id:
            raise ValueError("settlement signer and bank identity are required")
        if not self.action_id or not self.execution_ref or not self.rail:
            raise ValueError("settlement action, execution and rail are required")
        _require_aware(self.recorded_at, "recorded_at")
        if self.committed_at is not None:
            _require_aware(self.committed_at, "committed_at")
        if self.status is SettlementStatus.COMMITTED:
            if self.effect_ref is None or self.committed_at is None:
                raise ValueError("committed settlement requires effect_ref and committed_at")
            if self.committed_at > self.recorded_at:
                raise ValueError("settlement cannot be recorded before commitment")
        if self.settlement_digest and self.settlement_digest != self.computed_digest:
            raise ValueError("settlement evidence digest mismatch")
        return self


def issue_settlement_evidence(
    *,
    signer: ExecutionArtifactSigner,
    bank_acceptance: BankExecutionAcceptance,
    bank_public_key: Ed25519PublicKey,
    action: ProposedAction,
    execution_ref: str,
    rail: str,
    effect_ref: str | None,
    status: SettlementStatus,
    committed_at: datetime | None,
    recorded_at: datetime,
    external_receipt_digest: str,
) -> SettlementEvidence:
    verify_bank_execution_acceptance(bank_acceptance, public_key=bank_public_key)
    action_digest = canonical_digest(action.model_dump(mode="json"))
    if bank_acceptance.action_digest != action_digest:
        raise ValueError("settlement action differs from bank acceptance")
    if bank_acceptance.execution_ref != execution_ref:
        raise ValueError("settlement execution_ref differs from bank acceptance")
    if status is SettlementStatus.COMMITTED:
        if bank_acceptance.disposition is not BankAcceptanceDisposition.ACCEPTED:
            raise ValueError("committed settlement requires bank acceptance")
        if bank_acceptance.valid_until is None or committed_at is None:
            raise ValueError("bank acceptance or commitment time is missing")
        if not (
            bank_acceptance.evaluated_at <= committed_at < bank_acceptance.valid_until
        ):
            raise ValueError("settlement commitment is outside bank acceptance window")

    settlement_id = canonical_digest(
        {
            "bank_acceptance_digest": bank_acceptance.acceptance_digest,
            "execution_ref": execution_ref,
            "rail": rail,
            "effect_ref": effect_ref,
            "status": status.value,
            "recorded_at": recorded_at.isoformat(),
        }
    )
    unsealed = SettlementEvidence(
        settlement_id=settlement_id,
        signer_id=signer.signer_id,
        key_id=signer.key_id,
        bank_id=bank_acceptance.bank_id,
        bank_acceptance_digest=bank_acceptance.acceptance_digest,
        action_id=action.action_id,
        action_digest=action_digest,
        execution_ref=execution_ref,
        rail=rail,
        effect_ref=effect_ref,
        status=status,
        committed_at=committed_at,
        recorded_at=recorded_at,
        external_receipt_digest=external_receipt_digest,
    )
    return SettlementEvidence.model_validate(
        _signed_model(
            unsealed,
            digest_field="settlement_digest",
            signature_field="signature",
            domain=SETTLEMENT_SIGNATURE_DOMAIN,
            signer=signer,
        )
    )


def verify_settlement_evidence(
    settlement: SettlementEvidence,
    *,
    public_key: Ed25519PublicKey,
) -> None:
    if settlement.settlement_digest != settlement.computed_digest:
        raise ValueError("settlement evidence is unsealed or tampered")
    _verify_signature(
        public_key=public_key,
        domain=SETTLEMENT_SIGNATURE_DOMAIN,
        digest=settlement.settlement_digest,
        signature=settlement.signature,
    )


class ExecutionAssuranceChain(BaseModel):
    schema_version: Literal["execution_assurance_chain.v1"] = (
        "execution_assurance_chain.v1"
    )
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_ref: str
    authority_basis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    lease_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    revocation_checkpoint_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    lease_evaluation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    bank_acceptance_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    settlement_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_evidence_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    sealed_at: datetime
    chain_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"chain_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_chain(self) -> ExecutionAssuranceChain:
        if not self.action_id or not self.execution_ref:
            raise ValueError("execution assurance chain identity is required")
        _require_aware(self.sealed_at, "sealed_at")
        if self.chain_digest and self.chain_digest != self.computed_digest:
            raise ValueError("execution assurance chain digest mismatch")
        return self


def seal_execution_assurance_chain(
    *,
    basis: AuthorityLeaseBasis,
    lease: ExecutionAuthorityLease,
    checkpoint: RevocationCheckpoint,
    lease_evaluation: ExecutionLeaseEvaluation,
    bank_acceptance: BankExecutionAcceptance,
    settlement: SettlementEvidence,
    sealed_at: datetime,
    outcome_evidence_digest: str | None = None,
) -> ExecutionAssuranceChain:
    if basis.basis_digest != basis.computed_digest:
        raise ValueError("authority lease basis is unsealed or tampered")
    if lease.lease_digest != lease.computed_digest:
        raise ValueError("execution authority lease is unsealed or tampered")
    if checkpoint.checkpoint_digest != checkpoint.computed_digest:
        raise ValueError("revocation checkpoint is unsealed or tampered")
    if lease_evaluation.evaluation_digest != lease_evaluation.computed_digest:
        raise ValueError("execution lease evaluation is unsealed or tampered")
    if bank_acceptance.acceptance_digest != bank_acceptance.computed_digest:
        raise ValueError("bank acceptance is unsealed or tampered")
    if settlement.settlement_digest != settlement.computed_digest:
        raise ValueError("settlement evidence is unsealed or tampered")

    if lease.basis_digest != basis.basis_digest:
        raise ValueError("lease does not bind the supplied authority basis")
    if lease_evaluation.lease_digest != lease.lease_digest:
        raise ValueError("lease evaluation does not bind the supplied lease")
    if lease_evaluation.revocation_checkpoint_digest != checkpoint.checkpoint_digest:
        raise ValueError("lease evaluation does not bind the revocation checkpoint")
    if bank_acceptance.lease_evaluation_digest != lease_evaluation.evaluation_digest:
        raise ValueError("bank acceptance does not bind the lease evaluation")
    if settlement.bank_acceptance_digest != bank_acceptance.acceptance_digest:
        raise ValueError("settlement does not bind the bank acceptance")
    if len(
        {
            lease_evaluation.action_digest,
            bank_acceptance.action_digest,
            settlement.action_digest,
        }
    ) != 1:
        raise ValueError("execution assurance chain action binding mismatch")
    if bank_acceptance.execution_ref != settlement.execution_ref:
        raise ValueError("execution assurance chain execution_ref mismatch")

    unsealed = ExecutionAssuranceChain(
        action_id=lease_evaluation.action_id,
        action_digest=lease_evaluation.action_digest,
        execution_ref=bank_acceptance.execution_ref,
        authority_basis_digest=basis.basis_digest,
        lease_digest=lease.lease_digest,
        revocation_checkpoint_digest=checkpoint.checkpoint_digest,
        lease_evaluation_digest=lease_evaluation.evaluation_digest,
        bank_acceptance_digest=bank_acceptance.acceptance_digest,
        settlement_digest=settlement.settlement_digest,
        outcome_evidence_digest=outcome_evidence_digest,
        sealed_at=sealed_at,
    )
    return ExecutionAssuranceChain.model_validate(
        {**unsealed.model_dump(mode="python"), "chain_digest": unsealed.computed_digest}
    )
