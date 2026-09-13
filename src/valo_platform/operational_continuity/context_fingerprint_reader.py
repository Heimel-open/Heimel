"""Operational Continuity reader for exact registered ActionChainContext state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.valo_platform.decision_governance.action_case import ActionCaseRecord
from src.valo_platform.decision_governance.context_registry import (
    ActionChainContextRegistry,
    ContextStateRegistryError,
)

from .fingerprint_readers import FingerprintOwnerReaderError
from .fingerprint_snapshot import (
    DecisionFingerprintKind,
    DecisionFingerprintObservation,
)
from .observers import ObservationBinding


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise FingerprintOwnerReaderError(
            "context fingerprint read time must be timezone-aware"
        )
    return value.astimezone(timezone.utc)


def _require_binding(
    action_case: ActionCaseRecord,
    binding: ObservationBinding,
) -> None:
    actual = (
        action_case.tenant_id,
        action_case.case_id,
        action_case.case_hash,
        action_case.clearance_ref,
    )
    expected = (
        binding.tenant_id,
        binding.action_case_id,
        binding.action_case_hash,
        binding.clearance_ref,
    )
    if actual != expected:
        raise FingerprintOwnerReaderError(
            "configured Action Case does not match context snapshot binding"
        )


@dataclass(frozen=True)
class RegisteredContextDecisionFingerprintReader:
    """Read one exact, uniquely active context version from its append-only owner."""

    action_case: ActionCaseRecord
    registry: ActionChainContextRegistry
    context_id: str
    version: str
    reader_ref: str = "action-chain-context-registry:fingerprint-reader:1"
    kind: DecisionFingerprintKind = DecisionFingerprintKind.CONTEXT

    @property
    def context_ref(self) -> str:
        return self.registry.source_ref(
            self.action_case.tenant_id,
            self.context_id,
            self.version,
        )

    def read(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> DecisionFingerprintObservation:
        observed_at = _as_utc(observed_at)
        _require_binding(self.action_case, binding)
        if self.action_case.context_fingerprint is None:
            raise FingerprintOwnerReaderError(
                "Action Case does not carry a canonical context fingerprint"
            )
        if self.context_ref not in set(self.action_case.context_refs):
            raise FingerprintOwnerReaderError(
                "Action Case does not bind the exact registered context version"
            )
        try:
            registered = self.registry.get_exact(
                binding.tenant_id,
                self.context_id,
                self.version,
            )
            unique_active = self.registry.resolve_active(
                binding.tenant_id,
                self.context_id,
                at=observed_at,
            )
            lifecycle_events = self.registry.events(
                binding.tenant_id,
                self.context_id,
            )
        except ContextStateRegistryError as exc:
            raise FingerprintOwnerReaderError(
                "registered context lookup, active resolution or chain verification failed"
            ) from exc
        if unique_active.version != self.version:
            raise FingerprintOwnerReaderError(
                "pinned context version is not the unique active version"
            )
        if not registered.is_active(observed_at):
            raise FingerprintOwnerReaderError(
                "registered context version is not active"
            )
        if registered.context_digest != self.action_case.context_fingerprint:
            raise FingerprintOwnerReaderError(
                "registered context fingerprint changed"
            )
        lifecycle_event_hashes = {
            event.event_hash for event in lifecycle_events
        }
        lifecycle_evidence_refs = {
            evidence_ref
            for event in lifecycle_events
            for evidence_ref in event.evidence_refs
        }
        evidence_refs = tuple(
            sorted(
                {
                    self.context_ref,
                    registered.authority_ref,
                    registered.latest_event_hash,
                    *registered.event_hashes,
                    *registered.evidence_refs,
                    *lifecycle_event_hashes,
                    *lifecycle_evidence_refs,
                }
            )
        )
        return DecisionFingerprintObservation(
            binding=binding,
            kind=self.kind,
            fingerprint=registered.context_digest,
            source_ref=self.context_ref,
            reader_ref=self.reader_ref,
            evidence_refs=evidence_refs,
            observed_at=observed_at,
        )


__all__ = ["RegisteredContextDecisionFingerprintReader"]
