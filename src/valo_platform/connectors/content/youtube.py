"""Clearance-bound YouTube publication connector.

This adapter delegates all authorization enforcement to the canonical
``BoundedConnectorBoundary``. It adds only publication-specific digest binding,
an injected transport, and postcondition verification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from src.valo_platform.action_envelope.bounded_connector import (
    BoundedConnectorBoundary,
    ConnectorBoundaryError,
    ConnectorExecutionResult,
    IndeterminateProviderFailure,
    ProviderResult,
)
from src.valo_platform.content_operations.publication import PublicationActionCase

from .protocol import (
    PublicationDryRun,
    PublicationMutationRequest,
    PublicationMutationResult,
    PublicationTransport,
)


class YouTubePublicationConnector:
    """Execute an exact YouTube mutation through a verified CommitToken."""

    PROVIDER = "youtube"
    CONNECTOR_ID = "connector.content.youtube"
    CAPABILITY = "content.publish"

    def __init__(self, boundary: BoundedConnectorBoundary) -> None:
        self._boundary = boundary

    def dry_run(self, action_case: PublicationActionCase) -> PublicationDryRun:
        """Return exact bindings without consuming clearance or calling a transport."""

        self._require_provider(action_case)
        return PublicationDryRun.from_action_case(action_case)

    def execute(
        self,
        *,
        action_case: PublicationActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        transport: PublicationTransport,
        receipt_id: str,
        now: datetime | None = None,
    ) -> ConnectorExecutionResult:
        """Publish only when the canonical boundary verifies every exact binding."""

        self._require_provider(action_case)
        if signed_commit_token is None:
            raise ConnectorBoundaryError("signed CommitToken is required for publication")
        self._require_case_binding(signed_commit_token, action_case)

        publication = action_case.publication
        payload_digest = action_case.digest()
        target_digest = action_case.target_digest()

        def mutation(execution_id: str) -> ProviderResult:
            request = PublicationMutationRequest(
                execution_id=execution_id,
                action_id=action_case.action_case.case_id,
                tenant_id=publication.tenant_id,
                provider=publication.provider,
                account_ref=publication.account_ref,
                channel_ref=publication.channel_ref,
                payload_digest=payload_digest,
                target_digest=target_digest,
                idempotency_key=publication.idempotency_key,
                payload=action_case.canonical_payload(),
            )
            observed = transport.publish(request)
            self._verify_postcondition(observed, action_case)
            response = dict(observed.response)
            response.update(
                {
                    "provider": observed.provider,
                    "account_ref": observed.account_ref,
                    "channel_ref": observed.channel_ref,
                    "privacy_status": observed.privacy_status.value,
                }
            )
            return ProviderResult(
                provider_reference=observed.provider_reference,
                response=response,
            )

        return self._boundary.execute(
            signed_commit_token=signed_commit_token,
            connector_id=self.CONNECTOR_ID,
            capability=self.CAPABILITY,
            target_digest=target_digest,
            payload_digest=payload_digest,
            mutation=mutation,
            receipt_id=receipt_id,
            now=now,
        )

    @classmethod
    def _require_provider(cls, action_case: PublicationActionCase) -> None:
        if action_case.publication.provider != cls.PROVIDER:
            raise ConnectorBoundaryError(
                f"YouTube connector cannot execute provider '{action_case.publication.provider}'"
            )

    @staticmethod
    def _require_case_binding(
        signed_commit_token: Mapping[str, Any],
        action_case: PublicationActionCase,
    ) -> None:
        """Reject obvious cross-case use before token consumption and mutation."""

        payload = signed_commit_token.get("payload")
        if not isinstance(payload, Mapping):
            raise ConnectorBoundaryError("CommitToken payload is missing")
        expected = {
            "tenant_id": action_case.action_case.tenant_id,
            "action_id": action_case.action_case.case_id,
            "case_hash": action_case.action_case.case_hash,
        }
        for field, value in expected.items():
            if payload.get(field) != value:
                raise ConnectorBoundaryError(f"CommitToken {field} does not bind publication case")

    @classmethod
    def _verify_postcondition(
        cls,
        observed: PublicationMutationResult,
        action_case: PublicationActionCase,
    ) -> None:
        """Verify the provider reports the exact cleared destination and visibility.

        A mismatch is indeterminate rather than a definite failure because the
        external effect may already have occurred and requires reconciliation.
        """

        publication = action_case.publication
        expected = (
            cls.PROVIDER,
            publication.account_ref,
            publication.channel_ref,
            publication.privacy_status,
        )
        actual = (
            observed.provider,
            observed.account_ref,
            observed.channel_ref,
            observed.privacy_status,
        )
        if actual != expected:
            raise IndeterminateProviderFailure(
                "provider postcondition does not match cleared publication target"
            )
