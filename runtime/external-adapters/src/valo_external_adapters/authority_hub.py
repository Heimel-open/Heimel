from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import ProposedAction, canonical_digest


class IdentityVerification(StrEnum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class ExternalIdentityAssertion(BaseModel):
    """Verified identity evidence received from an external identity rail.

    Identity is evidence about who is present. It is never authority to act.
    Provider roles, groups, permissions, or approval flags are deliberately not
    represented as authority in this contract.
    """

    schema_version: Literal["external_identity_assertion.v1"] = (
        "external_identity_assertion.v1"
    )
    provider_id: str
    external_subject: str
    verification: IdentityVerification
    assurance_level: str
    evidence_ref: str
    issued_at: datetime
    valid_until: datetime
    claims_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_assertion(self) -> ExternalIdentityAssertion:
        required = (
            self.provider_id,
            self.external_subject,
            self.assurance_level,
            self.evidence_ref,
        )
        if any(not value for value in required):
            raise ValueError("identity assertion fields are required")
        if self.valid_until <= self.issued_at:
            raise ValueError("identity assertion must have a positive validity window")
        return self

    def is_usable(self, moment: datetime) -> bool:
        return (
            self.verification is IdentityVerification.VERIFIED
            and self.issued_at <= moment < self.valid_until
        )


class CanonicalIdentityBinding(BaseModel):
    """Explicit mapping from an external identity to a canonical Heimel actor."""

    schema_version: Literal["canonical_identity_binding.v1"] = (
        "canonical_identity_binding.v1"
    )
    actor_id: str
    provider_id: str
    external_subject: str
    assertion_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_ref: str
    bound_at: datetime
    valid_until: datetime
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityResolutionRequest(BaseModel):
    """Non-authoritative handoff from identity normalization to REHT/RACS.

    A consumer MUST resolve fresh authority independently at consequence time.
    This object cannot carry an ALLOW decision or clearance.
    """

    schema_version: Literal["authority_resolution_request.v1"] = (
        "authority_resolution_request.v1"
    )
    actor_id: str
    identity_binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_evidence_ref: str
    proposed_action: ProposedAction
    requested_at: datetime
    requires_fresh_authority: Literal[True] = True
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityHub:
    """Normalize identity evidence and hand it to the authority boundary.

    The hub intentionally has no authorize/allow method. Its output is only a
    request for a fresh authority decision by the governed consequence path.
    """

    @staticmethod
    def bind_identity(
        *,
        assertion: ExternalIdentityAssertion,
        actor_id: str,
        now: datetime,
    ) -> CanonicalIdentityBinding:
        if not actor_id:
            raise ValueError("canonical actor id is required")
        if not assertion.is_usable(now):
            raise ValueError("external identity assertion is not verified and fresh")

        assertion_digest = canonical_digest(assertion.model_dump(mode="json"))
        payload = {
            "actor_id": actor_id,
            "provider_id": assertion.provider_id,
            "external_subject": assertion.external_subject,
            "assertion_digest": assertion_digest,
            "evidence_ref": assertion.evidence_ref,
            "bound_at": now.isoformat(),
            "valid_until": assertion.valid_until.isoformat(),
            "authority_effect": "NO_AUTHORITY_CREATION",
            "can_issue_clearance": False,
        }
        return CanonicalIdentityBinding(
            actor_id=actor_id,
            provider_id=assertion.provider_id,
            external_subject=assertion.external_subject,
            assertion_digest=assertion_digest,
            evidence_ref=assertion.evidence_ref,
            bound_at=now,
            valid_until=assertion.valid_until,
            binding_digest=canonical_digest(payload),
        )

    @staticmethod
    def request_authority_resolution(
        *,
        binding: CanonicalIdentityBinding,
        proposed_action: ProposedAction,
        now: datetime,
    ) -> AuthorityResolutionRequest:
        if not (binding.bound_at <= now < binding.valid_until):
            raise ValueError("canonical identity binding is not fresh")
        return AuthorityResolutionRequest(
            actor_id=binding.actor_id,
            identity_binding_digest=binding.binding_digest,
            identity_evidence_ref=binding.evidence_ref,
            proposed_action=proposed_action,
            requested_at=now,
        )
