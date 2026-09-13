"""Public hardened boundary for Sanity canary operations.

The implementation module keeps composition logic focused. This boundary narrows all
operator-supplied references before persistence and requires the latest registered
preflight before execution delegation.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Mapping, Sequence

from src.valo_platform.content_operations.actions import ContentActionCase

from .protocol import ContentMutationTransport
from .sanity_operations import (
    SanityCanaryOperationsError,
    SanityCanaryOperationsRunner as _BaseRunner,
    SanityCanaryOperationsState,
    SanityCanaryOperationsStateError,
    SanityCanaryPreflightResult,
    SanityRollbackPlan,
    SQLiteSanityCanaryOperationsStateStore as _BaseOperationsStore,
    VerifiedSanityCanaryBundle,
)


_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


def _require_ref(value: str, field: str) -> str:
    if not isinstance(value, str) or not _REF_RE.fullmatch(value):
        raise SanityCanaryOperationsError(
            f"{field} must be an opaque reference without whitespace or control data"
        )
    return value


def _reason_ref(reason: str) -> str:
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2048:
        raise SanityCanaryOperationsStateError("HALT reason is missing or oversized")
    return "halt-reason:sha256:" + hashlib.sha256(
        reason.encode("utf-8")
    ).hexdigest()[:32]


class SQLiteSanityCanaryOperationsStateStore(_BaseOperationsStore):
    """Persist only opaque actor references and digested HALT reasons."""

    def activate(
        self,
        verified: VerifiedSanityCanaryBundle,
        *,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return super().activate(
            verified,
            actor_ref=_require_ref(actor_ref, "actor_ref"),
            now=now,
        )

    def halt(
        self,
        *,
        profile_id: str,
        expected_profile_digest: str,
        actor_ref: str,
        reason: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return super().halt(
            profile_id=_require_ref(profile_id, "profile_id"),
            expected_profile_digest=expected_profile_digest,
            actor_ref=_require_ref(actor_ref, "actor_ref"),
            reason=_reason_ref(reason),
            now=now,
        )

    def record_preflight(
        self,
        *,
        profile_id: str,
        profile_digest: str,
        activation_epoch: int,
        preflight_ref: str,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return super().record_preflight(
            profile_id=_require_ref(profile_id, "profile_id"),
            profile_digest=profile_digest,
            activation_epoch=activation_epoch,
            preflight_ref=_require_ref(preflight_ref, "preflight_ref"),
            actor_ref=_require_ref(actor_ref, "actor_ref"),
            now=now,
        )


class SanityCanaryOperationsRunner(_BaseRunner):
    """Require sanitized operator refs and the latest active preflight."""

    operations_store: SQLiteSanityCanaryOperationsStateStore

    def register_activation(
        self,
        *,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return super().register_activation(
            actor_ref=_require_ref(actor_ref, "actor_ref"),
            now=now,
        )

    def preflight(
        self,
        *,
        action_case: ContentActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        integrity_baseline: Any,
        integrity_checkpoint: Any,
        transport: ContentMutationTransport,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryPreflightResult:
        return super().preflight(
            action_case=action_case,
            signed_commit_token=signed_commit_token,
            integrity_baseline=integrity_baseline,
            integrity_checkpoint=integrity_checkpoint,
            transport=transport,
            actor_ref=_require_ref(actor_ref, "actor_ref"),
            now=now,
        )

    def execute(
        self,
        *,
        preflight: SanityCanaryPreflightResult,
        action_case: ContentActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        integrity_baseline: Any,
        integrity_checkpoint: Any,
        transport: ContentMutationTransport,
        receipt_id: str,
        now: datetime | None = None,
    ) -> Any:
        active = self.operations_store.require_operational(self.verified_bundle)
        if active.last_preflight_ref != preflight.reference:
            raise SanityCanaryOperationsError(
                "execution requires the latest registered preflight"
            )
        return super().execute(
            preflight=preflight,
            action_case=action_case,
            signed_commit_token=signed_commit_token,
            integrity_baseline=integrity_baseline,
            integrity_checkpoint=integrity_checkpoint,
            transport=transport,
            receipt_id=_require_ref(receipt_id, "receipt_id"),
            now=now,
        )

    def halt(
        self,
        *,
        actor_ref: str,
        reason: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return super().halt(
            actor_ref=_require_ref(actor_ref, "actor_ref"),
            reason=reason,
            now=now,
        )

    def resume(
        self,
        verified_new_bundle: VerifiedSanityCanaryBundle,
        *,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return super().resume(
            verified_new_bundle,
            actor_ref=_require_ref(actor_ref, "actor_ref"),
            now=now,
        )

    def rollback_plan(
        self,
        *,
        execution_id: str,
        expected_current_revisions: Sequence[str],
        rollback_change_ref: str,
        rollback_change_digest: str,
        requested_by: str,
        now: datetime | None = None,
    ) -> SanityRollbackPlan:
        _require_ref(execution_id, "execution_id")
        _require_ref(rollback_change_ref, "rollback_change_ref")
        _require_ref(requested_by, "requested_by")
        for revision in expected_current_revisions:
            _require_ref(revision, "expected_current_revision")
        return super().rollback_plan(
            execution_id=execution_id,
            expected_current_revisions=expected_current_revisions,
            rollback_change_ref=rollback_change_ref,
            rollback_change_digest=rollback_change_digest,
            requested_by=requested_by,
            now=now,
        )
