"""Append-only version registry for governed publication policies.

The registry preserves exact policy versions and status transitions. It does not
interpret policy, issue clearance or execute publication. Active resolution is
fail-closed when no version or more than one version is eligible.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Sequence

import rfc8785
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .policy_profile import PublicationPolicyProfile


class PublicationPolicyRegistryError(ValueError):
    """Raised when policy registry integrity or resolution fails."""


class PublicationPolicyRegistryEventType(str, Enum):
    REGISTERED = "registered"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


class PublicationPolicyRegistryStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise PublicationPolicyRegistryError("registry times must be timezone-aware")
    return value.astimezone(timezone.utc)


def _normalize_refs(values: Iterable[str] | None) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip()
                for value in (values or ())
                if str(value).strip()
            }
        )
    )


def _digest(value: Any) -> str:
    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")
    else:
        payload = value
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


class PublicationPolicyRegistryEvent(BaseModel):
    """One immutable transition in the status history of an exact policy version."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)

    event_id: str
    tenant_id: str
    policy_id: str
    version: str
    profile_digest: str
    event_type: PublicationPolicyRegistryEventType
    actor_ref: str
    authority_ref: str
    reason: str
    evidence_refs: tuple[str, ...] = ()
    replacement_version: str | None = None
    sequence: int
    occurred_at: datetime
    previous_event_hash: str
    event_hash: str = ""

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _sort_refs(cls, value: Iterable[str] | None) -> tuple[str, ...]:
        return _normalize_refs(value)

    @model_validator(mode="after")
    def _validate_event(self) -> "PublicationPolicyRegistryEvent":
        _as_utc(self.occurred_at)
        if self.sequence < 0:
            raise PublicationPolicyRegistryError("event sequence must be non-negative")
        if (
            not self.actor_ref.strip()
            or not self.authority_ref.strip()
            or not self.reason.strip()
        ):
            raise PublicationPolicyRegistryError(
                "registry event requires actor, authority and reason"
            )
        if self.event_type == PublicationPolicyRegistryEventType.SUPERSEDED:
            if not self.replacement_version:
                raise PublicationPolicyRegistryError(
                    "supersession requires replacement_version"
                )
            if self.replacement_version == self.version:
                raise PublicationPolicyRegistryError(
                    "a policy version cannot supersede itself"
                )
        elif self.replacement_version is not None:
            raise PublicationPolicyRegistryError(
                "replacement_version is valid only for supersession"
            )
        expected = _digest(self.model_dump(mode="json", exclude={"event_hash"}))
        if self.event_hash and self.event_hash != expected:
            raise PublicationPolicyRegistryError(
                "event_hash does not match canonical registry event"
            )
        if not self.event_hash:
            object.__setattr__(self, "event_hash", expected)
        return self


class RegisteredPublicationPolicy(BaseModel):
    """Verified current snapshot of one exact registered policy version."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)

    profile: PublicationPolicyProfile
    profile_digest: str
    status: PublicationPolicyRegistryStatus
    registered_at: datetime
    status_changed_at: datetime
    event_hashes: tuple[str, ...]
    latest_event_hash: str
    replacement_version: str | None = None
    snapshot_digest: str = ""

    @field_validator("event_hashes", mode="before")
    @classmethod
    def _event_hash_tuple(cls, value: Sequence[str]) -> tuple[str, ...]:
        return tuple(value)

    @model_validator(mode="after")
    def _validate_snapshot(self) -> "RegisteredPublicationPolicy":
        _as_utc(self.registered_at)
        _as_utc(self.status_changed_at)
        if self.profile.digest() != self.profile_digest:
            raise PublicationPolicyRegistryError(
                "profile digest does not match registered profile"
            )
        if not self.event_hashes:
            raise PublicationPolicyRegistryError(
                "registered policy requires an event chain"
            )
        if self.latest_event_hash != self.event_hashes[-1]:
            raise PublicationPolicyRegistryError(
                "latest event hash does not match event chain"
            )
        if self.status == PublicationPolicyRegistryStatus.SUPERSEDED:
            if not self.replacement_version:
                raise PublicationPolicyRegistryError(
                    "superseded policy requires replacement version"
                )
        elif self.replacement_version is not None:
            raise PublicationPolicyRegistryError(
                "replacement version is valid only for superseded policy"
            )
        expected = _digest(self.model_dump(mode="json", exclude={"snapshot_digest"}))
        if self.snapshot_digest and self.snapshot_digest != expected:
            raise PublicationPolicyRegistryError(
                "snapshot_digest does not match registered policy"
            )
        if not self.snapshot_digest:
            object.__setattr__(self, "snapshot_digest", expected)
        return self

    @property
    def tenant_id(self) -> str:
        return self.profile.tenant_id

    @property
    def policy_id(self) -> str:
        return self.profile.policy_id

    @property
    def version(self) -> str:
        return self.profile.version

    def is_active(self, at: datetime) -> bool:
        return (
            self.status == PublicationPolicyRegistryStatus.ACTIVE
            and self.profile.is_active(_as_utc(at))
        )


class PublicationPolicyRegistry:
    """In-memory append-only registry for exact publication policy versions."""

    GENESIS_HASH = "sha256:" + "0" * 64

    def __init__(self) -> None:
        self._profiles: dict[tuple[str, str, str], PublicationPolicyProfile] = {}
        self._events: dict[
            tuple[str, str, str], list[PublicationPolicyRegistryEvent]
        ] = {}

    @staticmethod
    def _key(tenant_id: str, policy_id: str, version: str) -> tuple[str, str, str]:
        if not tenant_id or not policy_id or not version:
            raise PublicationPolicyRegistryError(
                "tenant_id, policy_id and version are required"
            )
        return tenant_id, policy_id, version

    def register(
        self,
        profile: PublicationPolicyProfile,
        *,
        actor_ref: str,
        authority_ref: str,
        reason: str,
        occurred_at: datetime,
        evidence_refs: Iterable[str] = (),
    ) -> RegisteredPublicationPolicy:
        key = self._key(profile.tenant_id, profile.policy_id, profile.version)
        if key in self._profiles:
            raise PublicationPolicyRegistryError(
                "exact publication policy version is already registered"
            )
        if authority_ref != profile.authority_ref:
            raise PublicationPolicyRegistryError(
                "registration authority does not match policy authority"
            )
        occurred_at = _as_utc(occurred_at)
        event = self._event(
            profile=profile,
            event_type=PublicationPolicyRegistryEventType.REGISTERED,
            actor_ref=actor_ref,
            authority_ref=authority_ref,
            reason=reason,
            occurred_at=occurred_at,
            evidence_refs=evidence_refs,
            replacement_version=None,
            sequence=0,
            previous_event_hash=self.GENESIS_HASH,
        )
        self._profiles[key] = profile
        self._events[key] = [event]
        return self.get_exact(*key)

    def revoke(
        self,
        tenant_id: str,
        policy_id: str,
        version: str,
        *,
        actor_ref: str,
        authority_ref: str,
        reason: str,
        occurred_at: datetime,
        evidence_refs: Iterable[str] = (),
    ) -> RegisteredPublicationPolicy:
        key = self._key(tenant_id, policy_id, version)
        profile = self._require_profile(key)
        current = self.get_exact(*key)
        if current.status != PublicationPolicyRegistryStatus.ACTIVE:
            raise PublicationPolicyRegistryError(
                "only an active policy version may be revoked"
            )
        self._require_transition_authority(profile, authority_ref)
        self._append_transition(
            key=key,
            event_type=PublicationPolicyRegistryEventType.REVOKED,
            actor_ref=actor_ref,
            authority_ref=authority_ref,
            reason=reason,
            occurred_at=occurred_at,
            evidence_refs=evidence_refs,
            replacement_version=None,
        )
        return self.get_exact(*key)

    def supersede(
        self,
        tenant_id: str,
        policy_id: str,
        version: str,
        *,
        replacement_version: str,
        actor_ref: str,
        authority_ref: str,
        reason: str,
        occurred_at: datetime,
        evidence_refs: Iterable[str] = (),
    ) -> RegisteredPublicationPolicy:
        key = self._key(tenant_id, policy_id, version)
        profile = self._require_profile(key)
        current = self.get_exact(*key)
        if current.status != PublicationPolicyRegistryStatus.ACTIVE:
            raise PublicationPolicyRegistryError(
                "only an active policy version may be superseded"
            )
        replacement_key = self._key(tenant_id, policy_id, replacement_version)
        replacement = self._require_profile(replacement_key)
        replacement_state = self.get_exact(*replacement_key)
        if replacement_state.status != PublicationPolicyRegistryStatus.ACTIVE:
            raise PublicationPolicyRegistryError(
                "replacement policy version must be active"
            )
        if replacement.authority_ref != profile.authority_ref:
            raise PublicationPolicyRegistryError(
                "replacement policy authority must match superseded policy"
            )
        self._require_transition_authority(profile, authority_ref)
        self._append_transition(
            key=key,
            event_type=PublicationPolicyRegistryEventType.SUPERSEDED,
            actor_ref=actor_ref,
            authority_ref=authority_ref,
            reason=reason,
            occurred_at=occurred_at,
            evidence_refs=evidence_refs,
            replacement_version=replacement_version,
        )
        return self.get_exact(*key)

    def get_exact(
        self,
        tenant_id: str,
        policy_id: str,
        version: str,
    ) -> RegisteredPublicationPolicy:
        key = self._key(tenant_id, policy_id, version)
        profile = self._require_profile(key)
        events = tuple(self._events[key])
        if not self.verify_chain(tenant_id, policy_id, version):
            raise PublicationPolicyRegistryError(
                "publication policy registry chain verification failed"
            )
        latest = events[-1]
        status = {
            PublicationPolicyRegistryEventType.REGISTERED: (
                PublicationPolicyRegistryStatus.ACTIVE
            ),
            PublicationPolicyRegistryEventType.REVOKED: (
                PublicationPolicyRegistryStatus.REVOKED
            ),
            PublicationPolicyRegistryEventType.SUPERSEDED: (
                PublicationPolicyRegistryStatus.SUPERSEDED
            ),
        }[latest.event_type]
        return RegisteredPublicationPolicy(
            profile=profile,
            profile_digest=profile.digest(),
            status=status,
            registered_at=events[0].occurred_at,
            status_changed_at=latest.occurred_at,
            event_hashes=tuple(event.event_hash for event in events),
            latest_event_hash=latest.event_hash,
            replacement_version=latest.replacement_version,
        )

    def resolve_active(
        self,
        tenant_id: str,
        policy_id: str,
        *,
        at: datetime,
    ) -> RegisteredPublicationPolicy:
        at = _as_utc(at)
        candidates = [
            self.get_exact(*key)
            for key in sorted(self._profiles)
            if key[0] == tenant_id and key[1] == policy_id
        ]
        active = [candidate for candidate in candidates if candidate.is_active(at)]
        if not active:
            raise PublicationPolicyRegistryError(
                "no active registered publication policy version"
            )
        if len(active) > 1:
            versions = ",".join(candidate.version for candidate in active)
            raise PublicationPolicyRegistryError(
                "ambiguous active publication policy versions: " + versions
            )
        return active[0]

    def list_versions(
        self,
        tenant_id: str,
        policy_id: str,
    ) -> tuple[RegisteredPublicationPolicy, ...]:
        return tuple(
            self.get_exact(*key)
            for key in sorted(self._profiles)
            if key[0] == tenant_id and key[1] == policy_id
        )

    def event_chain(
        self,
        tenant_id: str,
        policy_id: str,
        version: str,
    ) -> tuple[PublicationPolicyRegistryEvent, ...]:
        key = self._key(tenant_id, policy_id, version)
        self._require_profile(key)
        return tuple(self._events[key])

    def verify_chain(
        self,
        tenant_id: str,
        policy_id: str,
        version: str,
    ) -> bool:
        key = self._key(tenant_id, policy_id, version)
        profile = self._profiles.get(key)
        events = self._events.get(key)
        if profile is None or not events:
            return False
        previous_hash = self.GENESIS_HASH
        for sequence, event in enumerate(events):
            if event.sequence != sequence:
                return False
            if event.previous_event_hash != previous_hash:
                return False
            if event.tenant_id != tenant_id:
                return False
            if event.policy_id != policy_id or event.version != version:
                return False
            if event.profile_digest != profile.digest():
                return False
            expected_hash = _digest(
                event.model_dump(mode="json", exclude={"event_hash"})
            )
            if event.event_hash != expected_hash:
                return False
            previous_hash = event.event_hash
        return True

    def _require_profile(
        self,
        key: tuple[str, str, str],
    ) -> PublicationPolicyProfile:
        profile = self._profiles.get(key)
        if profile is None:
            raise PublicationPolicyRegistryError(
                "publication policy version is not registered"
            )
        return profile

    @staticmethod
    def _require_transition_authority(
        profile: PublicationPolicyProfile,
        authority_ref: str,
    ) -> None:
        if authority_ref != profile.authority_ref:
            raise PublicationPolicyRegistryError(
                "transition authority does not match policy authority"
            )

    def _append_transition(
        self,
        *,
        key: tuple[str, str, str],
        event_type: PublicationPolicyRegistryEventType,
        actor_ref: str,
        authority_ref: str,
        reason: str,
        occurred_at: datetime,
        evidence_refs: Iterable[str],
        replacement_version: str | None,
    ) -> None:
        profile = self._require_profile(key)
        events = self._events[key]
        occurred_at = _as_utc(occurred_at)
        if occurred_at < events[-1].occurred_at:
            raise PublicationPolicyRegistryError(
                "registry transition cannot precede the latest event"
            )
        event = self._event(
            profile=profile,
            event_type=event_type,
            actor_ref=actor_ref,
            authority_ref=authority_ref,
            reason=reason,
            occurred_at=occurred_at,
            evidence_refs=evidence_refs,
            replacement_version=replacement_version,
            sequence=len(events),
            previous_event_hash=events[-1].event_hash,
        )
        events.append(event)

    @staticmethod
    def _event(
        *,
        profile: PublicationPolicyProfile,
        event_type: PublicationPolicyRegistryEventType,
        actor_ref: str,
        authority_ref: str,
        reason: str,
        occurred_at: datetime,
        evidence_refs: Iterable[str],
        replacement_version: str | None,
        sequence: int,
        previous_event_hash: str,
    ) -> PublicationPolicyRegistryEvent:
        event_id = (
            f"publication-policy-event:{profile.tenant_id}:{profile.policy_id}:"
            f"{profile.version}:{sequence}"
        )
        return PublicationPolicyRegistryEvent(
            event_id=event_id,
            tenant_id=profile.tenant_id,
            policy_id=profile.policy_id,
            version=profile.version,
            profile_digest=profile.digest(),
            event_type=event_type,
            actor_ref=actor_ref,
            authority_ref=authority_ref,
            reason=reason,
            evidence_refs=tuple(evidence_refs),
            replacement_version=replacement_version,
            sequence=sequence,
            occurred_at=occurred_at,
            previous_event_hash=previous_event_hash,
        )


__all__ = [
    "PublicationPolicyRegistry",
    "PublicationPolicyRegistryError",
    "PublicationPolicyRegistryEvent",
    "PublicationPolicyRegistryEventType",
    "PublicationPolicyRegistryStatus",
    "RegisteredPublicationPolicy",
]
