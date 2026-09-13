"""Continuous Integrity adapter for governed content actions.

This module maps exact content bindings into the canonical Continuous Integrity
runtime. It does not evaluate admissibility, issue clearance, execute a content
mutation, or create a second checkpoint receipt type.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.valo_platform.continuous_integrity import (
    IntegrityBaseline,
    IntegrityCheckpointReceipt,
    IntegrityDecision,
    IntegrityProfile,
    IntegrityState,
    IntegrityTrigger,
    capture_baseline as capture_integrity_baseline,
    emit_checkpoint_receipt,
)
from src.valo_platform.memory_provider import canonical_digest

from .actions import ContentActionCase
from .content_policy import ContentPolicyProfile
from .invalidation import (
    ContentBindingObservation,
    ContentBindingSnapshot,
    ContentBindingValidator,
    ContentInvalidationEvidence,
)


_CLEARANCE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_ADAPTER_VERSION = "content-integrity-adapter.v1"
_ADAPTER_VERSION_DIGEST = "sha256:" + hashlib.sha256(
    _ADAPTER_VERSION.encode("utf-8")
).hexdigest()


class ContentIntegrityError(ValueError):
    """Fail-closed content-to-integrity binding error."""


class ContentIntegrityBaselineBinding(BaseModel):
    """Reference-only link between a content binding and canonical baseline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    action_ref: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    binding_snapshot: ContentBindingSnapshot
    integrity_baseline: IntegrityBaseline
    grants_authority: Literal[False] = False
    grants_clearance: Literal[False] = False
    production_writes: Literal[0] = 0

    @model_validator(mode="after")
    def validate_links(self) -> "ContentIntegrityBaselineBinding":
        baseline = self.integrity_baseline
        if baseline.case_id != self.case_id:
            raise ValueError("content baseline case does not match integrity baseline")
        if baseline.action_ref != self.action_ref:
            raise ValueError("content action does not match integrity baseline")
        if self.binding_snapshot.action_payload_digest != self.action_ref:
            raise ValueError("content snapshot does not bind the baseline action")
        return self


class ContentIntegrityCheckpointResult(BaseModel):
    """Link content invalidation evidence to a canonical checkpoint receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    action_ref: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    binding_observation: ContentBindingObservation
    invalidation_evidence: ContentInvalidationEvidence
    checkpoint_receipt: IntegrityCheckpointReceipt
    grants_authority: Literal[False] = False
    grants_clearance: Literal[False] = False
    production_writes: Literal[0] = 0

    @model_validator(mode="after")
    def validate_result(self) -> "ContentIntegrityCheckpointResult":
        receipt = self.checkpoint_receipt
        if receipt.case_id != self.case_id or receipt.action_ref != self.action_ref:
            raise ValueError("checkpoint receipt is not bound to the content baseline")
        if (
            not self.invalidation_evidence.valid
            and receipt.decision is IntegrityDecision.CONTINUE
        ):
            raise ValueError("invalid content binding cannot continue")
        return self


def default_content_integrity_profile(
    *,
    profile_id: str = "content-integrity.v1",
    baseline_validity_seconds: int = 300,
) -> IntegrityProfile:
    """Conservative profile where one changed dimension requires revalidation."""

    return IntegrityProfile(
        profile_id=profile_id,
        weights={
            "authority": 1.0,
            "policy": 1.0,
            "objective": 1.0,
            "context": 1.0,
            "evidence": 1.0,
            "tools": 1.0,
            "model_harness": 1.0,
            "environment": 1.0,
            "risk": 1.0,
        },
        material_drift_threshold=0.10,
        baseline_validity_seconds=baseline_validity_seconds,
        fail_closed=True,
        mandatory_boundary_revalidation=True,
    )


class ContentContinuousIntegrityAdapter:
    """Compose content binding evidence with canonical Continuous Integrity."""

    def __init__(self, validator: ContentBindingValidator | None = None) -> None:
        self._validator = validator or ContentBindingValidator()

    def capture_baseline(
        self,
        *,
        baseline_id: str,
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
        clearance_digest: str,
        profile: IntegrityProfile,
        captured_at: datetime | None = None,
        critical_validity: Mapping[str, bool] | None = None,
    ) -> ContentIntegrityBaselineBinding:
        """Capture a clearance-bound content baseline without issuing clearance."""

        self._validate_scope(action_case=action_case, policy=policy)
        if action_case.is_observation:
            raise ContentIntegrityError(
                "observation action cannot capture a clearance-bound mutation baseline"
            )
        if not _CLEARANCE_DIGEST.fullmatch(clearance_digest):
            raise ContentIntegrityError(
                "clearance_digest must be lowercase sha256:<64 hex>"
            )

        now = _as_utc(captured_at or datetime.now(timezone.utc))
        snapshot = ContentBindingSnapshot.capture(
            action_case=action_case,
            policy=policy,
            captured_at=now,
        )
        state = self._integrity_state(
            binding=snapshot,
            action_case=action_case,
            observed_at=now,
            critical_validity=critical_validity,
        )
        baseline = capture_integrity_baseline(
            baseline_id=baseline_id,
            case_id=action_case.action_case.case_id,
            action_ref=action_case.digest(),
            clearance_digest=clearance_digest,
            profile=profile,
            state=state,
            captured_at=now,
        )
        return ContentIntegrityBaselineBinding(
            tenant_id=action_case.content.tenant_id,
            case_id=action_case.action_case.case_id,
            action_ref=action_case.digest(),
            binding_snapshot=snapshot,
            integrity_baseline=baseline,
        )

    def checkpoint(
        self,
        *,
        receipt_id: str,
        baseline: ContentIntegrityBaselineBinding,
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
        profile: IntegrityProfile,
        trigger: IntegrityTrigger,
        previous_checkpoint_digest: str | None = None,
        observed_at: datetime | None = None,
        critical_validity: Mapping[str, bool] | None = None,
    ) -> ContentIntegrityCheckpointResult:
        """Observe current bindings and emit one canonical checkpoint receipt."""

        self._validate_scope(action_case=action_case, policy=policy)
        if action_case.action_case.case_id != baseline.case_id:
            raise ContentIntegrityError("cross-case checkpoint is forbidden")
        if action_case.content.tenant_id != baseline.tenant_id:
            raise ContentIntegrityError("cross-tenant checkpoint is forbidden")
        if profile.profile_id != baseline.integrity_baseline.profile_id:
            raise ContentIntegrityError("integrity profile does not match baseline")

        now = _as_utc(observed_at or datetime.now(timezone.utc))
        observation = ContentBindingObservation.observe(
            action_case=action_case,
            policy=policy,
            observed_at=now,
        )
        invalidation = self._validator.evaluate(
            snapshot=baseline.binding_snapshot,
            observation=observation,
            now=now,
        )
        current_state = self._integrity_state(
            binding=observation,
            action_case=action_case,
            observed_at=now,
            critical_validity=critical_validity,
        )
        receipt = emit_checkpoint_receipt(
            receipt_id=receipt_id,
            baseline=baseline.integrity_baseline,
            current=current_state,
            profile=profile,
            trigger=trigger,
            previous_checkpoint_digest=previous_checkpoint_digest,
            observed_at=now,
        )
        if not invalidation.valid and receipt.decision is IntegrityDecision.CONTINUE:
            raise ContentIntegrityError(
                "integrity profile permitted invalid content binding to continue"
            )

        return ContentIntegrityCheckpointResult(
            tenant_id=baseline.tenant_id,
            case_id=baseline.case_id,
            action_ref=baseline.action_ref,
            binding_observation=observation,
            invalidation_evidence=invalidation,
            checkpoint_receipt=receipt,
        )

    @staticmethod
    def _validate_scope(
        *,
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
    ) -> None:
        if action_case.content.tenant_id != action_case.action_case.tenant_id:
            raise ContentIntegrityError("content and Action Case tenant mismatch")
        if policy.tenant_id != action_case.content.tenant_id:
            raise ContentIntegrityError("content policy tenant mismatch")

    @staticmethod
    def _integrity_state(
        *,
        binding: ContentBindingSnapshot | ContentBindingObservation,
        action_case: ContentActionCase,
        observed_at: datetime,
        critical_validity: Mapping[str, bool] | None,
    ) -> IntegrityState:
        content = action_case.content
        record = action_case.action_case
        return IntegrityState(
            authority=canonical_digest(
                {
                    "authority_fingerprint": binding.authority_fingerprint,
                    "delegation_fingerprint": binding.delegation_fingerprint,
                }
            ),
            policy=binding.policy_digest,
            objective=canonical_digest(
                {
                    "mandate_fingerprint": binding.mandate_fingerprint,
                    "action_payload_digest": binding.action_payload_digest,
                }
            ),
            context=canonical_digest(
                {
                    "context_fingerprint": binding.context_fingerprint,
                    "target_digest": binding.target_digest,
                    "schema_version": binding.schema_version,
                }
            ),
            evidence=canonical_digest(
                {
                    "content_snapshot_digest": binding.content_snapshot_digest,
                    "state_binding_digest": binding.state_binding_digest,
                    "source_version_refs": binding.source_version_refs,
                    "evidence_fingerprint": record.evidence_fingerprint,
                }
            ),
            tools=canonical_digest(
                {
                    "content_system": content.content_system,
                    "operation": content.operation.value,
                }
            ),
            model_harness=_ADAPTER_VERSION_DIGEST,
            environment=canonical_digest(
                {
                    "tenant_id": content.tenant_id,
                    "workspace_ref": content.workspace_ref,
                    "project_ref": content.project_ref,
                    "dataset_ref": content.dataset_ref,
                }
            ),
            risk=canonical_digest(
                {
                    "operation": content.operation.value,
                    "materiality": content.materiality.value,
                    "batch_id": content.batch_id,
                    "batch_size": content.batch_size,
                    "reversibility": content.reversibility.value,
                    "approval_requirement": content.approval_requirement.value,
                }
            ),
            observed_at=observed_at,
            critical_validity=dict(critical_validity or {}),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ContentIntegrityError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
