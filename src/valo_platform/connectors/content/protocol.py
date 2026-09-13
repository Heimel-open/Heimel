"""Provider-neutral contracts for governed content connectors.

Publication transports receive an already-cleared mutation request. Shadow
transports expose observation, preview, and deterministic simulation only.
Conditional mutation transports receive one exact compare-and-set request. No
contract in this module evaluates policy or manufactures governance clearance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping, Protocol

if TYPE_CHECKING:
    from src.valo_platform.content_operations.actions import (
        ContentActionCase,
        ContentOperation,
    )
    from src.valo_platform.content_operations.publication import (
        PublicationActionCase,
        PublicationPrivacy,
    )


@dataclass(frozen=True)
class PublicationMutationRequest:
    """Exact publication request handed to an injected provider transport."""

    execution_id: str
    action_id: str
    tenant_id: str
    provider: str
    account_ref: str
    channel_ref: str
    payload_digest: str
    target_digest: str
    idempotency_key: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class PublicationMutationResult:
    """Observed provider result used for postcondition verification."""

    provider_reference: str
    provider: str
    account_ref: str
    channel_ref: str
    privacy_status: PublicationPrivacy
    response: Mapping[str, Any]


class PublicationTransport(Protocol):
    """Injected provider transport. Implementations perform one mutation only."""

    def publish(self, request: PublicationMutationRequest) -> PublicationMutationResult:
        """Perform the exact publication mutation and return observed state."""


@dataclass(frozen=True)
class PublicationDryRun:
    """Network-free preview of the exact action and destination bindings."""

    action_id: str
    tenant_id: str
    provider: str
    account_ref: str
    channel_ref: str
    privacy_status: PublicationPrivacy
    payload_digest: str
    target_digest: str
    idempotency_key: str

    @classmethod
    def from_action_case(cls, action_case: PublicationActionCase) -> "PublicationDryRun":
        publication = action_case.publication
        return cls(
            action_id=action_case.action_case.case_id,
            tenant_id=publication.tenant_id,
            provider=publication.provider,
            account_ref=publication.account_ref,
            channel_ref=publication.channel_ref,
            privacy_status=publication.privacy_status,
            payload_digest=action_case.digest(),
            target_digest=action_case.target_digest(),
            idempotency_key=publication.idempotency_key,
        )


@dataclass(frozen=True)
class ContentShadowRequest:
    """Reference-only request for CMS observation or dry-run simulation."""

    action_id: str
    tenant_id: str
    operation: ContentOperation
    content_system: str
    workspace_ref: str
    project_ref: str
    dataset_ref: str
    record_ids: tuple[str, ...]
    schema_version: str
    source_version_refs: tuple[str, ...]
    payload_digest: str
    target_digest: str
    state_binding_digest: str

    @classmethod
    def from_action_case(cls, action_case: ContentActionCase) -> "ContentShadowRequest":
        content = action_case.content
        return cls(
            action_id=action_case.action_case.case_id,
            tenant_id=content.tenant_id,
            operation=content.operation,
            content_system=content.content_system,
            workspace_ref=content.workspace_ref,
            project_ref=content.project_ref,
            dataset_ref=content.dataset_ref,
            record_ids=content.record_ids,
            schema_version=content.schema_version,
            source_version_refs=content.source_version_refs,
            payload_digest=action_case.digest(),
            target_digest=action_case.target_digest(),
            state_binding_digest=action_case.state_binding_digest(),
        )


@dataclass(frozen=True)
class ContentShadowResult:
    """Reference-only provider observation or simulated postcondition."""

    operation: str
    status: str
    schema_digest: str
    record_version_refs: tuple[str, ...]
    snapshot_digest: str
    result_refs: tuple[str, ...] = ()
    would_mutate: bool = False


class ContentShadowTransport(Protocol):
    """Provider-neutral observation and simulation surface with no write method."""

    def inspect_schema(self, request: ContentShadowRequest) -> ContentShadowResult:
        """Return the observed schema binding."""

    def fetch_metadata(self, request: ContentShadowRequest) -> ContentShadowResult:
        """Return record identifiers, versions, and metadata references."""

    def observe_current_state(self, request: ContentShadowRequest) -> ContentShadowResult:
        """Return the current snapshot binding without copying raw content."""

    def preview(self, request: ContentShadowRequest) -> ContentShadowResult:
        """Preview the exact proposal without changing external state."""

    def simulate(self, request: ContentShadowRequest) -> ContentShadowResult:
        """Simulate the proposed mutation without executing it."""


@dataclass(frozen=True)
class ContentMutationRequest:
    """Exact reference-only compare-and-set request for one cleared mutation."""

    execution_id: str
    action_id: str
    tenant_id: str
    content_system: str
    workspace_ref: str
    project_ref: str
    dataset_ref: str
    operation: ContentOperation
    record_ids: tuple[str, ...]
    schema_version: str
    source_version_refs: tuple[str, ...]
    target_version_refs: tuple[str, ...]
    content_snapshot_digest: str
    payload_digest: str
    target_digest: str
    state_binding_digest: str
    proposed_change_ref: str
    proposed_change_digest: str
    idempotency_key: str

    @classmethod
    def from_action_case(
        cls,
        *,
        execution_id: str,
        action_case: ContentActionCase,
    ) -> "ContentMutationRequest":
        content = action_case.content
        if action_case.is_observation:
            raise ValueError("observation action cannot form a mutation request")
        if content.proposed_change is None or content.idempotency_key is None:
            raise ValueError("mutation action requires change and idempotency bindings")
        return cls(
            execution_id=execution_id,
            action_id=action_case.action_case.case_id,
            tenant_id=content.tenant_id,
            content_system=content.content_system,
            workspace_ref=content.workspace_ref,
            project_ref=content.project_ref,
            dataset_ref=content.dataset_ref,
            operation=content.operation,
            record_ids=content.record_ids,
            schema_version=content.schema_version,
            source_version_refs=content.source_version_refs,
            target_version_refs=content.target_version_refs,
            content_snapshot_digest=content.content_snapshot_digest,
            payload_digest=action_case.digest(),
            target_digest=action_case.target_digest(),
            state_binding_digest=action_case.state_binding_digest(),
            proposed_change_ref=content.proposed_change.change_ref,
            proposed_change_digest=content.proposed_change.digest,
            idempotency_key=content.idempotency_key,
        )


@dataclass(frozen=True)
class ContentMutationResult:
    """Reference-only provider observation after a conditional mutation."""

    provider_reference: str
    content_system: str
    project_ref: str
    dataset_ref: str
    operation: ContentOperation
    record_ids: tuple[str, ...]
    schema_version: str
    previous_version_refs: tuple[str, ...]
    current_version_refs: tuple[str, ...]
    observed_snapshot_digest: str
    applied_payload_digest: str
    applied_target_digest: str
    applied_state_binding_digest: str
    response: Mapping[str, Any]


class ContentMutationTransport(Protocol):
    """Injected compare-and-set mutation surface with no authority semantics."""

    def mutate_if_current(
        self, request: ContentMutationRequest
    ) -> ContentMutationResult:
        """Mutate once only if exact schema, version and snapshot bindings hold."""
