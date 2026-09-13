"""Provider-neutral peripheral contracts for relAIon / PAIOS.

This module is intentionally standard-library only.  External providers are
replaceable adapters; provider-native payloads are never canonical personal
state.  They must first be normalized into envelopes and pass explicit
admissibility checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable


class EvidenceStage(str, Enum):
    RAW = "raw_observation"
    VALIDATED = "validated_observation"
    INFERRED_EVENT = "inferred_event"
    CORRELATION = "correlation"
    HYPOTHESIS = "hypothesis"
    SUPPORTED_CLAIM = "supported_claim"
    CANONICAL = "canonical_durable_state"


class AdmissibilityStatus(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"


@dataclass(frozen=True)
class SourceRef:
    provider: str
    adapter: str
    device_id: str | None = None
    model: str | None = None
    version: str | None = None

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.provider.strip():
            errors.append("source.provider is required")
        if not self.adapter.strip():
            errors.append("source.adapter is required")
        return tuple(errors)


@dataclass(frozen=True)
class ObservationEnvelope:
    observation_id: str
    subject_id: str
    observed_at: datetime
    received_at: datetime
    modality: str
    source: SourceRef
    payload: Mapping[str, Any]
    provenance: Mapping[str, Any]
    confidence: float | None = None
    mandate_id: str | None = None
    purpose: str | None = None
    integrity_ref: str | None = None
    stage: EvidenceStage = EvidenceStage.RAW

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = list(self.source.validate())
        if not self.observation_id.strip():
            errors.append("observation_id is required")
        if not self.subject_id.strip():
            errors.append("subject_id is required")
        if not self.modality.strip():
            errors.append("modality is required")
        if self.observed_at.tzinfo is None or self.received_at.tzinfo is None:
            errors.append("timestamps must be timezone-aware")
        if self.received_at < self.observed_at:
            errors.append("received_at cannot precede observed_at")
        if not self.provenance:
            errors.append("provenance is required")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            errors.append("confidence must be between 0 and 1")
        if self.stage is not EvidenceStage.RAW:
            errors.append("adapter output must enter as RAW evidence")
        return tuple(errors)


@dataclass(frozen=True)
class EvidenceEnvelope:
    observation_id: str
    stage: EvidenceStage
    confidence: float | None
    provenance: Mapping[str, Any]
    support_refs: tuple[str, ...] = ()
    conflict_refs: tuple[str, ...] = ()
    rationale: str | None = None

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.observation_id.strip():
            errors.append("observation_id is required")
        if not self.provenance:
            errors.append("provenance is required")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            errors.append("confidence must be between 0 and 1")
        if self.stage is EvidenceStage.CANONICAL and not self.support_refs:
            errors.append("canonical promotion requires supporting evidence")
        return tuple(errors)


@dataclass(frozen=True)
class CapabilityEnvelope:
    capability: str
    subject_id: str
    mandate_id: str
    purpose: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    consequence_class: str = "none"

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        for name, value in (
            ("capability", self.capability),
            ("subject_id", self.subject_id),
            ("mandate_id", self.mandate_id),
            ("purpose", self.purpose),
        ):
            if not value.strip():
                errors.append(f"{name} is required")
        return tuple(errors)


@dataclass(frozen=True)
class EffectEnvelope:
    capability: str
    mandate_id: str
    effect_type: str
    target: str
    consequence_class: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        for name, value in (
            ("capability", self.capability),
            ("mandate_id", self.mandate_id),
            ("effect_type", self.effect_type),
            ("target", self.target),
            ("consequence_class", self.consequence_class),
        ):
            if not value.strip():
                errors.append(f"{name} is required")
        return tuple(errors)


@dataclass(frozen=True)
class AdmissionResult:
    status: AdmissibilityStatus
    reasons: tuple[str, ...]
    observation: ObservationEnvelope | None = None

    @property
    def admitted(self) -> bool:
        return self.status is AdmissibilityStatus.GREEN


@runtime_checkable
class ObservationAdapter(Protocol):
    """Narrow-waist contract implemented by any inbound provider adapter."""

    adapter_name: str

    def normalize(self, payload: Mapping[str, Any]) -> ObservationEnvelope:
        ...


@runtime_checkable
class CapabilityAdapter(Protocol):
    """Narrow-waist contract implemented by any outbound capability adapter."""

    adapter_name: str

    def translate(self, request: CapabilityEnvelope) -> Mapping[str, Any]:
        ...


def admit_observation(observation: ObservationEnvelope) -> AdmissionResult:
    """Fail-closed structural admission for normalized observations.

    GREEN here means the envelope is structurally admissible as *raw evidence*.
    It does not mean the observation is true and it does not promote anything to
    canonical durable state.
    """

    errors = observation.validate()
    if errors:
        return AdmissionResult(AdmissibilityStatus.RED, errors, observation)

    reasons: list[str] = []
    if observation.confidence is None:
        reasons.append("source confidence absent; retain uncertainty")
    if observation.mandate_id is None or observation.purpose is None:
        reasons.append("no mandate/purpose attached; observation may be retained but not disclosed to capabilities")

    status = AdmissibilityStatus.AMBER if reasons else AdmissibilityStatus.GREEN
    return AdmissionResult(status, tuple(reasons), observation)


def assert_adapter_conformance(adapter: object) -> None:
    """Fail closed if an inbound adapter does not implement the common contract."""

    if not isinstance(adapter, ObservationAdapter):
        raise TypeError("adapter does not conform to ObservationAdapter")
    if not getattr(adapter, "adapter_name", "").strip():
        raise TypeError("adapter_name is required")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
