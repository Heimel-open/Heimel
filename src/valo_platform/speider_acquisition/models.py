"""Typed collection-only contracts for governed Speider acquisition.

These models carry acquisition facts and provenance. They deliberately contain no
analysis, risk, admissibility, authorization, or governance-decision fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActorLifecycleState(str, Enum):
    PROPOSED = "PROPOSED"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class ProviderRunState(str, Enum):
    """Collection execution state only; never a governance decision."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True)
class CostEstimate:
    amount_usd: float
    is_hard_ceiling: bool
    basis: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RegistryExecutionGrant:
    token: str
    request_id: str
    registry_entry_ref: str
    actor_id: str
    actor_version: str
    source_identifier: str
    tenant_id: str
    expires_at: str


@dataclass(frozen=True)
class ProviderRunHandle:
    provider_name: str
    run_id: str
    actor_id: str
    actor_version: str
    started_at: str
    dataset_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderRunStatus:
    handle: ProviderRunHandle
    state: ProviderRunState
    checked_at: str
    dataset_ref: str | None
    cost_metadata: dict[str, Any]
    execution_metadata: dict[str, Any] = field(default_factory=dict)
    collection_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunFrequencyLimit:
    max_runs: int
    window_seconds: int


@dataclass(frozen=True)
class RetentionRule:
    max_days: int
    deletion_required: bool
    storage_class: str = "tenant-controlled"


@dataclass(frozen=True)
class ActorLifecycleTransition:
    registry_entry_id: str
    from_state: ActorLifecycleState
    to_state: ActorLifecycleState
    changed_by: str
    authority_ref: str
    reason: str
    changed_at: str


@dataclass(frozen=True)
class ActorRegistryEntry:
    registry_entry_id: str
    actor_id: str
    human_readable_name: str
    pinned_version: str
    permitted_sources: tuple[str, ...]
    allowed_input_schema: dict[str, Any]
    expected_output_schema: dict[str, Any]
    legal_constraints: tuple[str, ...]
    contractual_constraints: tuple[str, ...]
    run_frequency_limit: RunFrequencyLimit
    max_cost_usd: float
    resource_limits: dict[str, Any]
    retention_rule: RetentionRule
    provenance_requirements: tuple[str, ...]
    quality_metrics: dict[str, Any]
    failure_metrics: dict[str, Any]
    owner: str
    approval_authority: str
    review_date: str
    permitted_tenant_ids: tuple[str, ...]
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    lifecycle_state: ActorLifecycleState = ActorLifecycleState.PROPOSED
    revoked_at: str | None = None
    revocation_authority_ref: str | None = None

    @property
    def is_revoked(self) -> bool:
        return (
            self.lifecycle_state is ActorLifecycleState.REVOKED
            or self.revoked_at is not None
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["lifecycle_state"] = self.lifecycle_state.value
        return value


@dataclass(frozen=True)
class AcquisitionRequest:
    request_id: str
    registry_entry_ref: str
    actor_id: str
    actor_version: str
    requested_source: str
    source_platform: str
    actor_input: dict[str, Any]
    purpose: str
    tenant_id: str
    organizational_context: str
    requester_id: str
    authority_ref: str
    cost_ceiling_usd: float
    timeout_seconds: int
    deadline_at: str
    correlation_id: str
    requested_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RawAcquisitionRecord:
    """Uninterpreted provider result and stable references before normalization."""

    actor_id: str
    actor_version: str
    run_id: str
    dataset_ref: str
    source_identifier: str
    source_platform: str
    retrieved_at: str
    executed_at: str
    payload: Any
    cost_metadata: dict[str, Any]
    collection_errors: tuple[str, ...] = ()
    execution_metadata: dict[str, Any] = field(default_factory=dict)
    provider_name: str = "apify"

    @property
    def raw_payload(self) -> Any:
        return self.payload


@dataclass(frozen=True)
class ProvenanceStep:
    stage: str
    timestamp: str
    evidence: dict[str, Any]
    evidence_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcquisitionEvent:
    acquisition_id: str
    request_id: str
    registry_entry_ref: str
    actor_id: str
    actor_version: str
    provider_name: str
    provider_run_id: str
    dataset_reference: str
    source_url_or_identifier: str
    source_platform: str
    retrieval_timestamp: str
    actor_execution_timestamp: str
    normalized_payload: Any
    payload_reference: str | None
    content_hash: str
    schema_version: str
    provenance_chain: tuple[ProvenanceStep, ...]
    quality_indicators: dict[str, Any]
    collection_errors: tuple[str, ...]
    cost_metadata: dict[str, Any]
    correlation_id: str
    tenant_id: str
    organizational_context: str
    request_input_hash: str
    raw_payload_reference: str
    raw_payload_hash: str
    normalized_payload_hash: str
    normalization_changed: bool
    collection_integrity_confidence: float
    retention_rule: RetentionRule
    emitted_at: str = field(default_factory=utc_now_iso)

    @property
    def apify_run_id(self) -> str | None:
        """Compatibility reference for Apify-backed events."""
        return self.provider_run_id if self.provider_name == "apify" else None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["provenance_chain"] = [step.to_dict() for step in self.provenance_chain]
        if self.provider_name == "apify":
            value["apify_run_id"] = self.provider_run_id
        return value
