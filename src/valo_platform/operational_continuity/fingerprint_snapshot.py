"""Attributed current decision fingerprints for Operational Continuity.

There is deliberately no global fingerprint truth registry. The five canonical
commit fingerprints are read from their owning domains through explicit readers,
bound to one Action Case and checkpoint, and frozen into a tamper-evident
snapshot.

The snapshot is evidence only. It neither evaluates materiality nor grants
clearance or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.valo_platform.decision_governance.continuity import (
    ContinuityIntegrityStatus,
    canonical_digest,
    canonical_fingerprint_digest,
)

from .observers import ObservationBinding


class DecisionFingerprintSnapshotError(ValueError):
    """Raised when current fingerprint evidence is incomplete or untrustworthy."""


class DecisionFingerprintKind(str, Enum):
    AUTHORITY = "authority"
    POLICY = "policy"
    CONTEXT = "context"
    STATE = "state"
    EVIDENCE = "evidence"


_REQUIRED_KINDS = frozenset(DecisionFingerprintKind)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise DecisionFingerprintSnapshotError(
            "current fingerprint times must be timezone-aware"
        )
    return value.astimezone(timezone.utc)


def _normalize_refs(values: Iterable[str] | None) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in (values or ()) if str(value)}))


def _observation_sort_key(value: Any) -> str:
    if isinstance(value, DecisionFingerprintObservation):
        return value.kind.value
    if isinstance(value, Mapping):
        kind = value.get("kind")
        if isinstance(kind, DecisionFingerprintKind):
            return kind.value
        return str(kind or "")
    return ""


class DecisionFingerprintObservation(BaseModel):
    """One attributed, digest-bound read from a decision-state owner."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)

    binding: ObservationBinding
    kind: DecisionFingerprintKind
    fingerprint: str
    source_ref: str
    reader_ref: str
    evidence_refs: tuple[str, ...] = ()
    observed_at: datetime
    integrity_status: ContinuityIntegrityStatus = ContinuityIntegrityStatus.VERIFIED
    observation_digest: str = ""

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _sort_refs(cls, value: Iterable[str] | None) -> tuple[str, ...]:
        return _normalize_refs(value)

    @model_validator(mode="after")
    def _validate_observation(self) -> "DecisionFingerprintObservation":
        _as_utc(self.observed_at)
        if not self.fingerprint:
            raise DecisionFingerprintSnapshotError(
                f"{self.kind.value} fingerprint is missing"
            )
        if not self.source_ref or not self.reader_ref:
            raise DecisionFingerprintSnapshotError(
                f"{self.kind.value} fingerprint requires source and reader attribution"
            )
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"observation_digest"})
        )
        if self.observation_digest and self.observation_digest != expected:
            raise DecisionFingerprintSnapshotError(
                f"{self.kind.value} observation digest mismatch"
            )
        if not self.observation_digest:
            object.__setattr__(self, "observation_digest", expected)
        return self


class CurrentDecisionFingerprintSnapshot(BaseModel):
    """Exactly one verified observation for every canonical commit fingerprint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    binding: ObservationBinding
    observed_at: datetime
    observations: tuple[DecisionFingerprintObservation, ...]
    fingerprint_digest: str = ""
    snapshot_digest: str = ""

    @field_validator("observations", mode="before")
    @classmethod
    def _sort_observations(
        cls,
        value: Sequence[DecisionFingerprintObservation | Mapping[str, Any]],
    ) -> tuple[DecisionFingerprintObservation | Mapping[str, Any], ...]:
        return tuple(sorted(tuple(value), key=_observation_sort_key))

    @model_validator(mode="after")
    def _validate_snapshot(self) -> "CurrentDecisionFingerprintSnapshot":
        observed_at = _as_utc(self.observed_at)
        kinds = [item.kind for item in self.observations]
        if len(kinds) != len(set(kinds)):
            raise DecisionFingerprintSnapshotError(
                "duplicate current decision fingerprint kind"
            )
        actual = set(kinds)
        if actual != _REQUIRED_KINDS:
            missing = sorted(kind.value for kind in _REQUIRED_KINDS - actual)
            extra = sorted(kind.value for kind in actual - _REQUIRED_KINDS)
            raise DecisionFingerprintSnapshotError(
                f"current fingerprint coverage mismatch; missing={missing}; extra={extra}"
            )
        for item in self.observations:
            if item.binding != self.binding:
                raise DecisionFingerprintSnapshotError(
                    f"{item.kind.value} fingerprint binding mismatch"
                )
            if _as_utc(item.observed_at) > observed_at:
                raise DecisionFingerprintSnapshotError(
                    f"{item.kind.value} fingerprint observation is from the future"
                )
            if item.integrity_status != ContinuityIntegrityStatus.VERIFIED:
                raise DecisionFingerprintSnapshotError(
                    f"{item.kind.value} fingerprint integrity is not verified"
                )
        expected_fingerprint_digest = canonical_fingerprint_digest(self.as_mapping())
        if (
            self.fingerprint_digest
            and self.fingerprint_digest != expected_fingerprint_digest
        ):
            raise DecisionFingerprintSnapshotError(
                "current fingerprint aggregate digest mismatch"
            )
        if not self.fingerprint_digest:
            object.__setattr__(
                self,
                "fingerprint_digest",
                expected_fingerprint_digest,
            )
        expected_snapshot_digest = canonical_digest(
            self.model_dump(mode="json", exclude={"snapshot_digest"})
        )
        if self.snapshot_digest and self.snapshot_digest != expected_snapshot_digest:
            raise DecisionFingerprintSnapshotError(
                "current fingerprint snapshot digest mismatch"
            )
        if not self.snapshot_digest:
            object.__setattr__(self, "snapshot_digest", expected_snapshot_digest)
        return self

    def as_mapping(self) -> dict[str, str]:
        return {item.kind.value: item.fingerprint for item in self.observations}

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        refs: set[str] = set()
        for item in self.observations:
            refs.update(item.evidence_refs)
        return tuple(sorted(refs))

    @property
    def evidence_ref(self) -> str:
        return f"current-decision-fingerprints:{self.snapshot_digest}"


class DecisionFingerprintReader(Protocol):
    """Read one canonical fingerprint from its legitimate owning domain."""

    kind: DecisionFingerprintKind

    def read(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> DecisionFingerprintObservation:
        ...


class CurrentDecisionFingerprintProvider(Protocol):
    """Build one exact attributed snapshot for a commit checkpoint."""

    def snapshot(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> CurrentDecisionFingerprintSnapshot:
        ...


@dataclass(frozen=True)
class CallableDecisionFingerprintReader:
    """Adapt a concrete domain reader without accepting an unstructured mapping."""

    kind: DecisionFingerprintKind
    reader: Callable[
        [ObservationBinding, datetime],
        DecisionFingerprintObservation,
    ]

    def read(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> DecisionFingerprintObservation:
        return self.reader(binding, observed_at)


class CompositeCurrentDecisionFingerprintProvider:
    """Require exactly five explicitly attributed domain readers."""

    def __init__(self, readers: Sequence[DecisionFingerprintReader]) -> None:
        indexed: dict[DecisionFingerprintKind, DecisionFingerprintReader] = {}
        for reader in readers:
            if reader.kind in indexed:
                raise DecisionFingerprintSnapshotError(
                    f"duplicate current fingerprint reader: {reader.kind.value}"
                )
            indexed[reader.kind] = reader
        actual = set(indexed)
        if actual != _REQUIRED_KINDS:
            missing = sorted(kind.value for kind in _REQUIRED_KINDS - actual)
            extra = sorted(kind.value for kind in actual - _REQUIRED_KINDS)
            raise DecisionFingerprintSnapshotError(
                f"current fingerprint reader coverage mismatch; missing={missing}; extra={extra}"
            )
        self._readers = indexed

    def snapshot(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> CurrentDecisionFingerprintSnapshot:
        observed_at = _as_utc(observed_at)
        observations: list[DecisionFingerprintObservation] = []
        for kind in sorted(_REQUIRED_KINDS, key=lambda item: item.value):
            reader = self._readers[kind]
            try:
                observation = reader.read(
                    binding=binding,
                    observed_at=observed_at,
                )
            except Exception as exc:
                raise DecisionFingerprintSnapshotError(
                    f"current fingerprint read failed: {kind.value}"
                ) from exc
            if not isinstance(observation, DecisionFingerprintObservation):
                raise DecisionFingerprintSnapshotError(
                    f"current fingerprint reader returned invalid type: {kind.value}"
                )
            if observation.kind != kind:
                raise DecisionFingerprintSnapshotError(
                    f"current fingerprint reader kind mismatch: {kind.value}"
                )
            observations.append(observation)
        return CurrentDecisionFingerprintSnapshot(
            binding=binding,
            observed_at=observed_at,
            observations=tuple(observations),
        )


__all__ = [
    "CallableDecisionFingerprintReader",
    "CompositeCurrentDecisionFingerprintProvider",
    "CurrentDecisionFingerprintProvider",
    "CurrentDecisionFingerprintSnapshot",
    "DecisionFingerprintKind",
    "DecisionFingerprintObservation",
    "DecisionFingerprintReader",
    "DecisionFingerprintSnapshotError",
]
