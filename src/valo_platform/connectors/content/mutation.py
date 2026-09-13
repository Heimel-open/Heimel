"""Provider-neutral cleared content mutation connector.

The connector composes existing boundaries only:

- Continuous Integrity proves the exact content binding is still current.
- RACS ``BoundedConnectorBoundary`` verifies and consumes the CommitToken.
- An injected transport performs one compare-and-set provider mutation.
- The canonical boundary emits the signed execution receipt.

This module does not evaluate policy, issue clearance, mint tokens, or implement a
live provider client.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

from src.valo_platform.action_envelope.bounded_connector import (
    BoundedConnectorBoundary,
    ConnectorBoundaryError,
    ConnectorExecutionResult,
    IndeterminateProviderFailure,
    ProviderResult,
)
from src.valo_platform.continuous_integrity import IntegrityDecision
from src.valo_platform.content_operations.actions import ContentActionCase
from src.valo_platform.content_operations.continuous_integrity import (
    ContentIntegrityBaselineBinding,
    ContentIntegrityCheckpointResult,
)
from src.valo_platform.memory_provider import canonical_digest

from .protocol import (
    ContentMutationRequest,
    ContentMutationResult,
    ContentMutationTransport,
)


@dataclass(frozen=True)
class PreparedContentMutation:
    """Side-effect-free exact mutation plan for direct or durable execution."""

    action_id: str
    tenant_id: str
    connector_id: str
    capability: str
    target_digest: str
    payload_digest: str
    idempotency_key: str
    mutation: Callable[[str], ProviderResult]


class ClearedContentMutationConnector:
    """Execute one exact content mutation through canonical integrity and RACS."""

    def __init__(
        self,
        *,
        boundary: BoundedConnectorBoundary,
        connector_id: str,
        content_system: str,
    ) -> None:
        if not connector_id or not connector_id.strip():
            raise ValueError("connector_id is required")
        if not content_system or not content_system.strip():
            raise ValueError("content_system is required")
        self._boundary = boundary
        self.connector_id = connector_id.strip()
        self.content_system = content_system.strip()

    def prepare(
        self,
        *,
        action_case: ContentActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        integrity_baseline: ContentIntegrityBaselineBinding | None,
        integrity_checkpoint: ContentIntegrityCheckpointResult | None,
        transport: ContentMutationTransport,
    ) -> PreparedContentMutation:
        """Validate exact bindings and construct one side-effect-free mutation plan."""

        self._require_action(action_case)
        if signed_commit_token is None:
            raise ConnectorBoundaryError("signed CommitToken is required for content mutation")
        if integrity_baseline is None:
            raise ConnectorBoundaryError("content integrity baseline is required")
        if integrity_checkpoint is None:
            raise ConnectorBoundaryError("fresh content integrity checkpoint is required")

        self._require_integrity(
            action_case=action_case,
            baseline=integrity_baseline,
            checkpoint=integrity_checkpoint,
        )
        self._require_token_case_and_clearance(
            signed_commit_token=signed_commit_token,
            action_case=action_case,
            baseline=integrity_baseline,
        )

        content = action_case.content
        if content.idempotency_key is None:
            raise ConnectorBoundaryError("content mutation idempotency key is required")
        payload_digest = action_case.digest()
        target_digest = action_case.target_digest()
        capability = content.operation.value

        def mutation(execution_id: str) -> ProviderResult:
            request = ContentMutationRequest.from_action_case(
                execution_id=execution_id,
                action_case=action_case,
            )
            observed = transport.mutate_if_current(request)
            self._verify_postcondition(observed=observed, request=request)
            response = dict(observed.response)
            response.update(
                {
                    "content_system": observed.content_system,
                    "project_ref": observed.project_ref,
                    "dataset_ref": observed.dataset_ref,
                    "operation": observed.operation.value,
                    "record_ids": list(observed.record_ids),
                    "previous_version_refs": list(observed.previous_version_refs),
                    "current_version_refs": list(observed.current_version_refs),
                    "observed_snapshot_digest": observed.observed_snapshot_digest,
                }
            )
            return ProviderResult(
                provider_reference=observed.provider_reference,
                response=response,
            )

        return PreparedContentMutation(
            action_id=action_case.action_case.case_id,
            tenant_id=content.tenant_id,
            connector_id=self.connector_id,
            capability=capability,
            target_digest=target_digest,
            payload_digest=payload_digest,
            idempotency_key=content.idempotency_key,
            mutation=mutation,
        )

    def execute(
        self,
        *,
        action_case: ContentActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        integrity_baseline: ContentIntegrityBaselineBinding | None,
        integrity_checkpoint: ContentIntegrityCheckpointResult | None,
        transport: ContentMutationTransport,
        receipt_id: str,
        now: datetime | None = None,
    ) -> ConnectorExecutionResult:
        """Execute after exact content, integrity and CommitToken binding checks."""

        plan = self.prepare(
            action_case=action_case,
            signed_commit_token=signed_commit_token,
            integrity_baseline=integrity_baseline,
            integrity_checkpoint=integrity_checkpoint,
            transport=transport,
        )
        assert signed_commit_token is not None
        return self._boundary.execute(
            signed_commit_token=signed_commit_token,
            connector_id=plan.connector_id,
            capability=plan.capability,
            target_digest=plan.target_digest,
            payload_digest=plan.payload_digest,
            mutation=plan.mutation,
            receipt_id=receipt_id,
            now=now,
        )

    def _require_action(self, action_case: ContentActionCase) -> None:
        if action_case.is_observation:
            raise ConnectorBoundaryError("observation action cannot enter mutation path")
        if action_case.content.content_system != self.content_system:
            raise ConnectorBoundaryError(
                "content action is outside the connector content-system scope"
            )

    @staticmethod
    def _require_integrity(
        *,
        action_case: ContentActionCase,
        baseline: ContentIntegrityBaselineBinding,
        checkpoint: ContentIntegrityCheckpointResult,
    ) -> None:
        expected = (
            action_case.content.tenant_id,
            action_case.action_case.case_id,
            action_case.digest(),
        )
        if (baseline.tenant_id, baseline.case_id, baseline.action_ref) != expected:
            raise ConnectorBoundaryError("integrity baseline does not bind content action")
        if (checkpoint.tenant_id, checkpoint.case_id, checkpoint.action_ref) != expected:
            raise ConnectorBoundaryError("integrity checkpoint does not bind content action")
        if not checkpoint.invalidation_evidence.valid:
            raise ConnectorBoundaryError("content binding was invalidated before mutation")
        receipt = checkpoint.checkpoint_receipt
        if receipt.decision is not IntegrityDecision.CONTINUE:
            raise ConnectorBoundaryError(
                f"content integrity checkpoint requires {receipt.decision.value}"
            )
        if receipt.revalidation_required:
            raise ConnectorBoundaryError("content integrity checkpoint requires revalidation")
        baseline_digest = canonical_digest(
            baseline.integrity_baseline.model_dump(mode="json")
        )
        if receipt.baseline_digest != baseline_digest:
            raise ConnectorBoundaryError("integrity checkpoint baseline digest mismatch")
        if checkpoint.binding_observation.action_payload_digest != action_case.digest():
            raise ConnectorBoundaryError("integrity observation action digest mismatch")
        if (
            checkpoint.binding_observation.state_binding_digest
            != action_case.state_binding_digest()
        ):
            raise ConnectorBoundaryError("integrity observation state binding mismatch")

    @staticmethod
    def _require_token_case_and_clearance(
        *,
        signed_commit_token: Mapping[str, Any],
        action_case: ContentActionCase,
        baseline: ContentIntegrityBaselineBinding,
    ) -> None:
        payload = signed_commit_token.get("payload")
        if not isinstance(payload, Mapping):
            raise ConnectorBoundaryError("CommitToken payload is missing")
        expected = {
            "tenant_id": action_case.action_case.tenant_id,
            "action_id": action_case.action_case.case_id,
            "case_hash": action_case.action_case.case_hash,
            "clearance_digest": baseline.integrity_baseline.clearance_digest,
        }
        for field, value in expected.items():
            if payload.get(field) != value:
                raise ConnectorBoundaryError(
                    f"CommitToken {field} does not bind content mutation"
                )

    @staticmethod
    def _verify_postcondition(
        *,
        observed: ContentMutationResult,
        request: ContentMutationRequest,
    ) -> None:
        """Verify exact postconditions after the external effect may have occurred."""

        expected = (
            request.content_system,
            request.project_ref,
            request.dataset_ref,
            request.operation,
            tuple(sorted(request.record_ids)),
            request.schema_version,
            tuple(sorted(request.source_version_refs)),
            request.payload_digest,
            request.target_digest,
            request.state_binding_digest,
        )
        actual = (
            observed.content_system,
            observed.project_ref,
            observed.dataset_ref,
            observed.operation,
            tuple(sorted(observed.record_ids)),
            observed.schema_version,
            tuple(sorted(observed.previous_version_refs)),
            observed.applied_payload_digest,
            observed.applied_target_digest,
            observed.applied_state_binding_digest,
        )
        if actual != expected:
            raise IndeterminateProviderFailure(
                "provider postcondition does not match cleared content mutation"
            )
        if request.target_version_refs and tuple(
            sorted(observed.current_version_refs)
        ) != tuple(sorted(request.target_version_refs)):
            raise IndeterminateProviderFailure(
                "provider target versions do not match cleared content mutation"
            )
        if not observed.provider_reference:
            raise IndeterminateProviderFailure(
                "provider reference missing after content mutation"
            )
