"""Operational Continuity adapter for registered publication policies."""

from __future__ import annotations

from datetime import datetime, timezone

from src.valo_platform.content_operations.policy_registry import (
    PublicationPolicyRegistry,
    PublicationPolicyRegistryError,
    PublicationPolicyRegistryStatus,
    RegisteredPublicationPolicy,
)
from src.valo_platform.decision_governance.continuity import (
    ContinuitySeverity,
    ContinuityTriggerKind,
    canonical_digest,
)

from .observers import FingerprintObserver, ObservationBinding
from .source_adapters import (
    ContinuitySourceDomain,
    ContinuitySourceObservation,
    SourceObservationError,
)
from .source_baselines import ContinuitySourceBaselineEntry


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise SourceObservationError("registered policy observation time must be aware")
    return value.astimezone(timezone.utc)


class RegisteredPublicationPolicySourceAdapter:
    """Observe one exact policy version through its append-only registry."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        registry: PublicationPolicyRegistry,
        policy_id: str,
        version: str,
    ) -> None:
        if not policy_id or not version:
            raise SourceObservationError("policy_id and version are required")
        self.binding = binding
        self.registry = registry
        self.policy_id = policy_id
        self.version = version
        self.source_ref = (
            f"publication-policy-registry:{binding.tenant_id}:{policy_id}:{version}"
        )

    def _snapshot(self) -> RegisteredPublicationPolicy:
        snapshot = self.registry.get_exact(
            self.binding.tenant_id,
            self.policy_id,
            self.version,
        )
        if snapshot.tenant_id != self.binding.tenant_id:
            raise SourceObservationError(
                "registered policy tenant does not match Action Case"
            )
        return snapshot

    def _state(
        self,
        *,
        observed_at: datetime,
    ) -> tuple[str, tuple[str, ...], bool, str, str]:
        observed_at = _as_utc(observed_at)
        try:
            snapshot = self._snapshot()
        except PublicationPolicyRegistryError as exc:
            current = canonical_digest(
                {
                    "source_ref": self.source_ref,
                    "registry_integrity": "failed",
                    "error": str(exc),
                }
            )
            return current, (self.source_ref,), False, "invalid", "failed"

        active = snapshot.is_active(observed_at)
        current = canonical_digest(
            {
                "source_ref": self.source_ref,
                "snapshot_digest": snapshot.snapshot_digest,
                "profile_digest": snapshot.profile_digest,
                "registry_status": snapshot.status.value,
                "active": active,
                "latest_event_hash": snapshot.latest_event_hash,
                "replacement_version": snapshot.replacement_version,
                "effective_from": snapshot.profile.effective_from,
                "effective_until": snapshot.profile.effective_until,
            }
        )
        event_refs = tuple(
            event.event_id
            for event in self.registry.event_chain(
                self.binding.tenant_id,
                self.policy_id,
                self.version,
            )
        )
        evidence_refs = tuple(
            sorted(
                {
                    self.source_ref,
                    snapshot.profile.authority_ref,
                    snapshot.profile.mandate_ref,
                    *event_refs,
                }
            )
        )
        return current, evidence_refs, active, snapshot.status.value, "verified"

    def fingerprint(self, *, observed_at: datetime) -> str:
        current, _, _, _, _ = self._state(observed_at=observed_at)
        return current

    def observe(
        self,
        *,
        expected_fingerprint: str,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        current, evidence_refs, active, status, integrity = self._state(
            observed_at=observed_at
        )
        changed_fields: list[str] = []
        if current != expected_fingerprint:
            changed_fields.append("registered_policy_snapshot")
        if status != PublicationPolicyRegistryStatus.ACTIVE.value:
            changed_fields.append(f"registry_status:{status}")
        if not active:
            changed_fields.append("policy_effective_or_registry_state")
        if integrity != "verified":
            changed_fields.append("registry_integrity")

        trigger = None
        if current != expected_fingerprint:
            trigger = FingerprintObserver(
                binding=self.binding,
                source_ref=self.source_ref,
                trigger_kind=ContinuityTriggerKind.POLICY_CHANGED,
                severity=ContinuitySeverity.HIGH,
            ).observe(
                previous_fingerprint=expected_fingerprint,
                current_fingerprint=current,
                observed_at=_as_utc(observed_at),
                changed_fields=tuple(sorted(set(changed_fields))),
                evidence_refs=evidence_refs,
                confidence=1.0,
                freshness=1.0 if integrity == "verified" else 0.0,
                integrity_status=integrity,
            )

        return ContinuitySourceObservation(
            domain=ContinuitySourceDomain.POLICY,
            source_ref=self.source_ref,
            expected_fingerprint=expected_fingerprint,
            current_fingerprint=current,
            observed_at=_as_utc(observed_at),
            changed_fields=(
                tuple(sorted(set(changed_fields))) if trigger is not None else ()
            ),
            evidence_refs=evidence_refs,
            integrity_status=integrity,
            trigger=trigger,
        )


def capture_registered_policy_baseline(
    adapter: RegisteredPublicationPolicySourceAdapter,
    *,
    captured_at: datetime,
) -> ContinuitySourceBaselineEntry:
    """Freeze only a chain-valid, active, exact registered policy version."""

    captured_at = _as_utc(captured_at)
    try:
        snapshot = adapter._snapshot()
    except PublicationPolicyRegistryError as exc:
        raise SourceObservationError(
            "cannot baseline an invalid registered policy"
        ) from exc
    if snapshot.status != PublicationPolicyRegistryStatus.ACTIVE:
        raise SourceObservationError(
            "cannot baseline a non-active registered policy"
        )
    if not snapshot.profile.is_active(captured_at):
        raise SourceObservationError(
            "cannot baseline a registered policy outside its effective window"
        )
    fingerprint, evidence_refs, active, _, integrity = adapter._state(
        observed_at=captured_at
    )
    if not active or integrity != "verified":
        raise SourceObservationError(
            "cannot baseline an invalid registered policy source"
        )
    return ContinuitySourceBaselineEntry(
        domain=ContinuitySourceDomain.POLICY,
        source_ref=adapter.source_ref,
        fingerprint=fingerprint,
        evidence_refs=evidence_refs,
        captured_at=captured_at,
    )


__all__ = [
    "RegisteredPublicationPolicySourceAdapter",
    "capture_registered_policy_baseline",
]
