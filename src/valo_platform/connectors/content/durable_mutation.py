"""Durable execution and reconciliation adapters for governed content mutation.

This module composes canonical execution infrastructure only. It does not create a
parallel journal, state machine, ExecutionReceipt, OutcomeReceipt, clearance, or
provider client.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from src.valo_platform.action_envelope.bounded_connector import ConnectorBoundaryError
from src.valo_platform.action_envelope.durable_execution import (
    DurableConnectorExecutor,
    DurableExecutionResult,
)
from src.valo_platform.action_envelope.execution_journal import (
    ExecutionRecord,
    SQLiteExecutionJournal,
)
from src.valo_platform.action_envelope.reconciliation import (
    ProviderObservation,
    ProviderReconciliationService,
    ProviderResolution,
    ReconciliationError,
    ReconciliationResult,
)
from src.valo_platform.content_operations.actions import ContentActionCase
from src.valo_platform.content_operations.continuous_integrity import (
    ContentIntegrityBaselineBinding,
    ContentIntegrityCheckpointResult,
)
from src.valo_platform.memory_provider import canonical_digest

from .mutation import ClearedContentMutationConnector
from .protocol import ContentMutationTransport


class DurableContentMutationExecutor:
    """Execute an exact content mutation through the canonical durable lifecycle."""

    def __init__(
        self,
        *,
        connector: ClearedContentMutationConnector,
        durable_executor: DurableConnectorExecutor,
    ) -> None:
        self._connector = connector
        self._durable = durable_executor

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
    ) -> DurableExecutionResult:
        """Prepare fail-closed, then reserve and execute through canonical runtime."""

        plan = self._connector.prepare(
            action_case=action_case,
            signed_commit_token=signed_commit_token,
            integrity_baseline=integrity_baseline,
            integrity_checkpoint=integrity_checkpoint,
            transport=transport,
        )
        if signed_commit_token is None:
            raise ConnectorBoundaryError("signed CommitToken is required")
        return self._durable.execute(
            signed_commit_token=signed_commit_token,
            connector_id=plan.connector_id,
            capability=plan.capability,
            target_digest=plan.target_digest,
            payload_digest=plan.payload_digest,
            mutation=plan.mutation,
            receipt_id=receipt_id,
            idempotency_key=plan.idempotency_key,
            now=now,
        )

    def require_reconciliation(self, execution_id: str) -> ExecutionRecord:
        """Mark restart-recovered or indeterminate work for provider lookup only."""

        return self._durable.require_reconciliation(execution_id)


class ContentMutationReconciliationAdapter:
    """Bind canonical provider reconciliation to one exact cleared content action."""

    def __init__(
        self,
        *,
        journal: SQLiteExecutionJournal,
        reconciliation_service: ProviderReconciliationService,
        connector_id: str,
    ) -> None:
        if not connector_id or not connector_id.strip():
            raise ValueError("connector_id is required")
        self._journal = journal
        self._service = reconciliation_service
        self._connector_id = connector_id.strip()

    def reconcile(
        self,
        *,
        execution_id: str,
        action_case: ContentActionCase,
        integrity_baseline: ContentIntegrityBaselineBinding,
        outcome_receipt_id: str,
        observation_window: Mapping[str, Any],
        attribution_score: float,
        confidence: float,
        counterfactual_ref: str | None = None,
    ) -> ReconciliationResult:
        """Resolve provider effect without accepting a token or mutation transport."""

        self._validate_binding(
            execution_id=execution_id,
            action_case=action_case,
            baseline=integrity_baseline,
        )
        baseline_payload = integrity_baseline.integrity_baseline.model_dump(mode="json")
        baseline_ref = (
            "integrity-baseline:"
            + integrity_baseline.integrity_baseline.baseline_id
            + ":"
            + canonical_digest(baseline_payload)[7:23]
        )
        expected_effect = self.expected_effect(action_case)
        return self._service.reconcile(
            execution_id,
            outcome_receipt_id=outcome_receipt_id,
            observation_window=observation_window,
            expected_effect=expected_effect,
            baseline_ref=baseline_ref,
            counterfactual_ref=counterfactual_ref,
            attribution_score=attribution_score,
            confidence=confidence,
            observation_verifier=self._verify_observed_effect,
        )

    @staticmethod
    def expected_effect(action_case: ContentActionCase) -> dict[str, Any]:
        """Return the exact reference-only effect cleared for this action."""

        if action_case.is_observation:
            raise ReconciliationError("observation action has no mutation effect")
        content = action_case.content
        if content.proposed_change is None:
            raise ReconciliationError("mutation action is missing proposed change")
        return {
            "tenant_id": content.tenant_id,
            "action_id": action_case.action_case.case_id,
            "content_system": content.content_system,
            "workspace_ref": content.workspace_ref,
            "project_ref": content.project_ref,
            "dataset_ref": content.dataset_ref,
            "operation": content.operation.value,
            "record_ids": list(content.record_ids),
            "schema_version": content.schema_version,
            "source_version_refs": list(content.source_version_refs),
            "target_version_refs": list(content.target_version_refs),
            "proposed_change_ref": content.proposed_change.change_ref,
            "proposed_change_digest": content.proposed_change.digest,
            "payload_digest": action_case.digest(),
            "target_digest": action_case.target_digest(),
            "state_binding_digest": action_case.state_binding_digest(),
        }

    @staticmethod
    def _verify_observed_effect(
        observation: ProviderObservation,
        expected_effect: Mapping[str, Any],
    ) -> None:
        """Fail closed unless provider evidence binds the exact cleared content effect."""

        if observation.resolution is ProviderResolution.UNKNOWN:
            return
        observed = observation.observed_effect
        scalar_fields = (
            "content_system",
            "project_ref",
            "dataset_ref",
            "operation",
            "proposed_change_digest",
        )
        for field in scalar_fields:
            if observed.get(field) != expected_effect.get(field):
                raise ReconciliationError(
                    f"provider observation {field} does not bind cleared content effect"
                )
        collection_fields = ("record_ids", "source_version_refs")
        for field in collection_fields:
            expected = tuple(sorted(expected_effect.get(field, ())))
            actual = tuple(sorted(observed.get(field, ())))
            if actual != expected:
                raise ReconciliationError(
                    f"provider observation {field} does not bind cleared content effect"
                )
        if observation.resolution in {
            ProviderResolution.CONFIRMED_SUCCEEDED,
            ProviderResolution.CONFIRMED_REVERSED,
        }:
            current = tuple(observed.get("current_version_refs", ()))
            if not current:
                raise ReconciliationError(
                    "confirmed provider effect requires current version references"
                )
            explicit_targets = tuple(sorted(expected_effect.get("target_version_refs", ())))
            if explicit_targets and tuple(sorted(current)) != explicit_targets:
                raise ReconciliationError(
                    "provider current versions do not match cleared target versions"
                )

    def _validate_binding(
        self,
        *,
        execution_id: str,
        action_case: ContentActionCase,
        baseline: ContentIntegrityBaselineBinding,
    ) -> None:
        content = action_case.content
        expected_baseline = (
            content.tenant_id,
            action_case.action_case.case_id,
            action_case.digest(),
        )
        if (baseline.tenant_id, baseline.case_id, baseline.action_ref) != expected_baseline:
            raise ReconciliationError(
                "integrity baseline does not bind reconciliation action"
            )
        record = self._journal.get(execution_id)
        expected_record = (
            content.tenant_id,
            self._connector_id,
            content.operation.value,
            action_case.target_digest(),
            action_case.digest(),
            content.idempotency_key,
        )
        actual_record = (
            record.tenant_id,
            record.connector_id,
            record.capability,
            record.target_digest,
            record.payload_digest,
            record.idempotency_key,
        )
        if actual_record != expected_record:
            raise ReconciliationError(
                "execution journal does not bind the cleared content action"
            )
