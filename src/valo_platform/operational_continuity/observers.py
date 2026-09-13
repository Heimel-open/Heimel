"""Bounded Operational Continuity observer adapters.

Observers translate attributed state observations into ContinuityTrigger
evidence. They never evaluate materiality, issue clearance, choose a RACS
outcome, or execute an action.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from pydantic import BaseModel, ConfigDict

from src.valo_platform.decision_governance.continuity import (
    ContinuitySeverity,
    ContinuityTrigger,
    ContinuityTriggerKind,
    canonical_digest,
)


class ObservationBinding(BaseModel):
    """Exact Action Case and clearance binding for one observer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: str
    action_case_id: str
    action_case_hash: str
    clearance_ref: str
    observer_ref: str


def _normalized_refs(values: Iterable[str] | None) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in (values or ()) if str(value)}))


def _trigger_id(payload: dict[str, object]) -> str:
    return "trigger:" + canonical_digest(payload).split(":", 1)[1][:24]


class FingerprintObserver:
    """Emit an attributed trigger when one authoritative fingerprint changes."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        source_ref: str,
        trigger_kind: ContinuityTriggerKind,
        severity: ContinuitySeverity = ContinuitySeverity.MEDIUM,
    ) -> None:
        self.binding = binding
        self.source_ref = source_ref
        self.trigger_kind = trigger_kind
        self.severity = severity

    def observe(
        self,
        *,
        previous_fingerprint: str,
        current_fingerprint: str,
        observed_at: datetime,
        changed_fields: Iterable[str],
        evidence_refs: Iterable[str],
        confidence: float = 1.0,
        freshness: float = 1.0,
        integrity_status: str = "verified",
    ) -> ContinuityTrigger:
        fields = _normalized_refs(changed_fields)
        evidence = _normalized_refs(evidence_refs)
        identity_payload = {
            "binding": self.binding.model_dump(mode="json"),
            "source_ref": self.source_ref,
            "trigger_kind": self.trigger_kind.value,
            "severity": self.severity.value,
            "previous_fingerprint": previous_fingerprint,
            "current_fingerprint": current_fingerprint,
            "changed_fields": list(fields),
            "evidence_refs": list(evidence),
            "observed_at": observed_at,
        }
        return ContinuityTrigger(
            trigger_id=_trigger_id(identity_payload),
            tenant_id=self.binding.tenant_id,
            action_case_id=self.binding.action_case_id,
            action_case_hash=self.binding.action_case_hash,
            clearance_ref=self.binding.clearance_ref,
            trigger_kind=self.trigger_kind,
            severity=self.severity,
            source_ref=self.source_ref,
            observer_ref=self.binding.observer_ref,
            observed_at=observed_at,
            previous_fingerprint=previous_fingerprint,
            current_fingerprint=current_fingerprint,
            changed_fields=fields,
            source_evidence_refs=evidence,
            confidence=confidence,
            freshness=freshness,
            integrity_status=integrity_status,
        )


class DeadlineObserver:
    """Emit a time-window trigger only after the bound validity deadline."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        source_ref: str,
    ) -> None:
        self.binding = binding
        self.source_ref = source_ref

    def observe(
        self,
        *,
        valid_until: datetime,
        observed_at: datetime,
        evidence_refs: Iterable[str] = (),
    ) -> ContinuityTrigger | None:
        if observed_at < valid_until:
            return None
        evidence = _normalized_refs(evidence_refs)
        identity_payload = {
            "binding": self.binding.model_dump(mode="json"),
            "source_ref": self.source_ref,
            "trigger_kind": ContinuityTriggerKind.TIME_WINDOW_EXPIRED.value,
            "valid_until": valid_until,
            "observed_at": observed_at,
            "evidence_refs": list(evidence),
        }
        return ContinuityTrigger(
            trigger_id=_trigger_id(identity_payload),
            tenant_id=self.binding.tenant_id,
            action_case_id=self.binding.action_case_id,
            action_case_hash=self.binding.action_case_hash,
            clearance_ref=self.binding.clearance_ref,
            trigger_kind=ContinuityTriggerKind.TIME_WINDOW_EXPIRED,
            severity=ContinuitySeverity.HIGH,
            source_ref=self.source_ref,
            observer_ref=self.binding.observer_ref,
            observed_at=observed_at,
            changed_fields=("valid_until",),
            source_evidence_refs=evidence,
            confidence=1.0,
            freshness=1.0,
            integrity_status="verified",
        )


class SafetyStopObserver:
    """Translate an explicit active stop condition into a critical trigger."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        source_ref: str,
    ) -> None:
        self.binding = binding
        self.source_ref = source_ref

    def observe(
        self,
        *,
        stop_active: bool,
        previous_fingerprint: str,
        current_fingerprint: str,
        observed_at: datetime,
        evidence_refs: Iterable[str],
        integrity_status: str = "verified",
    ) -> ContinuityTrigger | None:
        if not stop_active:
            return None
        observer = FingerprintObserver(
            binding=self.binding,
            source_ref=self.source_ref,
            trigger_kind=ContinuityTriggerKind.EXTERNAL_CONDITION_CHANGED,
            severity=ContinuitySeverity.CRITICAL,
        )
        return observer.observe(
            previous_fingerprint=previous_fingerprint,
            current_fingerprint=current_fingerprint,
            observed_at=observed_at,
            changed_fields=("explicit_stop_condition",),
            evidence_refs=evidence_refs,
            confidence=1.0,
            freshness=1.0,
            integrity_status=integrity_status,
        )


class ManualObservationAdapter:
    """Create an attributed manual-review request without granting authority."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        source_ref: str,
    ) -> None:
        self.binding = binding
        self.source_ref = source_ref

    def observe(
        self,
        *,
        observed_at: datetime,
        evidence_refs: Iterable[str],
        confidence: float = 1.0,
        freshness: float = 1.0,
        integrity_status: str = "verified",
    ) -> ContinuityTrigger:
        evidence = _normalized_refs(evidence_refs)
        identity_payload = {
            "binding": self.binding.model_dump(mode="json"),
            "source_ref": self.source_ref,
            "trigger_kind": ContinuityTriggerKind.MANUAL_REVIEW_REQUESTED.value,
            "observed_at": observed_at,
            "evidence_refs": list(evidence),
        }
        return ContinuityTrigger(
            trigger_id=_trigger_id(identity_payload),
            tenant_id=self.binding.tenant_id,
            action_case_id=self.binding.action_case_id,
            action_case_hash=self.binding.action_case_hash,
            clearance_ref=self.binding.clearance_ref,
            trigger_kind=ContinuityTriggerKind.MANUAL_REVIEW_REQUESTED,
            severity=ContinuitySeverity.MEDIUM,
            source_ref=self.source_ref,
            observer_ref=self.binding.observer_ref,
            observed_at=observed_at,
            changed_fields=("manual_review",),
            source_evidence_refs=evidence,
            confidence=confidence,
            freshness=freshness,
            integrity_status=integrity_status,
        )


__all__ = [
    "DeadlineObserver",
    "FingerprintObserver",
    "ManualObservationAdapter",
    "ObservationBinding",
    "SafetyStopObserver",
]
