"""Canonical ExternalExecutionBinding reference implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionAuthorityLeaseStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class ProviderResponseStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    REQUIRES_REVOCATION_CHECK = "REQUIRES_REVOCATION_CHECK"


@dataclass(frozen=True)
class ExecutionAuthorityLease:
    lease_id: str
    authority_digest: str
    status: ExecutionAuthorityLeaseStatus = ExecutionAuthorityLeaseStatus.PENDING
    not_after: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RevocationCheckpoint:
    checkpoint_id: str
    evaluated_at: str
    revoked: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class LeaseEvaluation:
    lease: ExecutionAuthorityLease
    checkpoint: RevocationCheckpoint
    approved: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class ActionDigest:
    action_id: str
    digest: str
    canonical_boundary: str
    execution_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalExecutionBinding:
    action_digest: ActionDigest
    lease_evaluation: LeaseEvaluation
    provider_response: dict[str, Any] = field(default_factory=dict)
    provider_response_status: ProviderResponseStatus = ProviderResponseStatus.REQUIRES_REVOCATION_CHECK
    settlement: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def binding_approved(self) -> bool:
        return (
            self.lease_evaluation.approved
            and self.provider_response_status == ProviderResponseStatus.ACCEPTED
            and self.settlement is False
        )
