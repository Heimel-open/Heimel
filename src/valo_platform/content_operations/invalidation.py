"""Authoritative binding validity for governed content evaluations.

This module proves whether the inputs bound to an earlier evaluation remain
current. It records invalidation evidence only; it does not revoke or issue a
clearance and cannot execute a content mutation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import rfc8785
from pydantic import BaseModel, ConfigDict, field_validator

from .actions import ContentActionCase
from .content_policy import ContentPolicyProfile


class ContentBindingSnapshot(BaseModel):
    """Immutable authoritative inputs captured for one exact content action."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_payload_digest: str
    target_digest: str
    state_binding_digest: str
    content_snapshot_digest: str
    policy_digest: str
    mandate_fingerprint: str
    authority_fingerprint: str
    delegation_fingerprint: str | None = None
    context_fingerprint: str | None = None
    schema_version: str
    source_version_refs: tuple[str, ...]
    captured_at: datetime

    @field_validator(
        "action_payload_digest",
        "target_digest",
        "state_binding_digest",
        "content_snapshot_digest",
        "policy_digest",
        "mandate_fingerprint",
        "authority_fingerprint",
        "delegation_fingerprint",
        "context_fingerprint",
    )
    @classmethod
    def validate_digest(cls, value: str | None) -> str | None:
        if value is not None and not _is_sha256(value):
            raise ValueError("binding fingerprints must be lowercase sha256:<64 hex>")
        return value

    @classmethod
    def capture(
        cls,
        *,
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
        captured_at: datetime | None = None,
    ) -> "ContentBindingSnapshot":
        record = action_case.action_case
        return cls(
            action_payload_digest=action_case.digest(),
            target_digest=action_case.target_digest(),
            state_binding_digest=action_case.state_binding_digest(),
            content_snapshot_digest=action_case.content.content_snapshot_digest,
            policy_digest=policy.digest(),
            mandate_fingerprint=record.mandate_fingerprint,
            authority_fingerprint=policy.authority_fingerprint,
            delegation_fingerprint=record.delegation_fingerprint,
            context_fingerprint=record.context_fingerprint,
            schema_version=action_case.content.schema_version,
            source_version_refs=action_case.content.source_version_refs,
            captured_at=_as_utc(captured_at or datetime.now(timezone.utc)),
        )

    def binding_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"captured_at"})

    def digest(self) -> str:
        return _digest(self.binding_payload())


class ContentBindingObservation(BaseModel):
    """Later observation of the same authoritative binding dimensions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_payload_digest: str
    target_digest: str
    state_binding_digest: str
    content_snapshot_digest: str
    policy_digest: str
    mandate_fingerprint: str
    authority_fingerprint: str
    delegation_fingerprint: str | None = None
    context_fingerprint: str | None = None
    schema_version: str
    source_version_refs: tuple[str, ...]
    observed_at: datetime

    @field_validator(
        "action_payload_digest",
        "target_digest",
        "state_binding_digest",
        "content_snapshot_digest",
        "policy_digest",
        "mandate_fingerprint",
        "authority_fingerprint",
        "delegation_fingerprint",
        "context_fingerprint",
    )
    @classmethod
    def validate_digest(cls, value: str | None) -> str | None:
        if value is not None and not _is_sha256(value):
            raise ValueError("binding fingerprints must be lowercase sha256:<64 hex>")
        return value

    @classmethod
    def observe(
        cls,
        *,
        action_case: ContentActionCase,
        policy: ContentPolicyProfile,
        observed_at: datetime | None = None,
    ) -> "ContentBindingObservation":
        record = action_case.action_case
        return cls(
            action_payload_digest=action_case.digest(),
            target_digest=action_case.target_digest(),
            state_binding_digest=action_case.state_binding_digest(),
            content_snapshot_digest=action_case.content.content_snapshot_digest,
            policy_digest=policy.digest(),
            mandate_fingerprint=record.mandate_fingerprint,
            authority_fingerprint=policy.authority_fingerprint,
            delegation_fingerprint=record.delegation_fingerprint,
            context_fingerprint=record.context_fingerprint,
            schema_version=action_case.content.schema_version,
            source_version_refs=action_case.content.source_version_refs,
            observed_at=_as_utc(observed_at or datetime.now(timezone.utc)),
        )

    def binding_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"observed_at"})

    def digest(self) -> str:
        return _digest(self.binding_payload())


class ContentInvalidationEvidence(BaseModel):
    """Deterministic result of comparing captured and observed bindings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    snapshot_digest: str
    observation_digest: str
    invalidated_fields: tuple[str, ...]
    reasons: tuple[str, ...]
    checked_at: datetime


class ContentBindingValidator:
    """Compare bindings without exercising clearance or revocation authority."""

    _FIELDS = (
        "action_payload_digest",
        "target_digest",
        "state_binding_digest",
        "content_snapshot_digest",
        "policy_digest",
        "mandate_fingerprint",
        "authority_fingerprint",
        "delegation_fingerprint",
        "context_fingerprint",
        "schema_version",
        "source_version_refs",
    )

    def evaluate(
        self,
        *,
        snapshot: ContentBindingSnapshot,
        observation: ContentBindingObservation,
        now: datetime | None = None,
    ) -> ContentInvalidationEvidence:
        changed = tuple(
            field
            for field in self._FIELDS
            if getattr(snapshot, field) != getattr(observation, field)
        )
        reasons = tuple(_reason(field) for field in changed)
        return ContentInvalidationEvidence(
            valid=not changed,
            snapshot_digest=snapshot.digest(),
            observation_digest=observation.digest(),
            invalidated_fields=changed,
            reasons=reasons or ("all authoritative content bindings remain current",),
            checked_at=_as_utc(now or datetime.now(timezone.utc)),
        )


def _reason(field: str) -> str:
    descriptions = {
        "action_payload_digest": "content action payload changed after evaluation",
        "target_digest": "content target scope changed after evaluation",
        "state_binding_digest": "content state binding changed after evaluation",
        "content_snapshot_digest": "content snapshot changed after evaluation",
        "policy_digest": "content policy changed after evaluation",
        "mandate_fingerprint": "content mandate changed after evaluation",
        "authority_fingerprint": "content authority changed after evaluation",
        "delegation_fingerprint": "content delegation changed after evaluation",
        "context_fingerprint": "content context changed after evaluation",
        "schema_version": "content schema version changed after evaluation",
        "source_version_refs": "content source version changed after evaluation",
    }
    return descriptions[field]


def _is_sha256(value: str) -> bool:
    return len(value) == 71 and value.startswith("sha256:") and all(
        char in "0123456789abcdef" for char in value[7:]
    )


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
