"""Fail-closed baseline capture for concrete Operational Continuity sources.

A baseline is the exact source state frozen at decision time. Capturing an
already-invalid source as the reference state would make later continuity checks
meaningless, so inactive policy/mandate and missing or expired evidence fail
before a baseline can be created.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.valo_platform.decision_governance.continuity import canonical_digest

from .observers import ObservationBinding
from .source_adapters import (
    ContinuitySourceDomain,
    EvidenceStoreSourceAdapter,
    MandateRegistrySourceAdapter,
    PublicationPolicySourceAdapter,
    SourceObservationError,
    TargetStateSourceAdapter,
    target_state_fingerprint,
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise SourceObservationError("baseline timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _normalize_refs(values: Iterable[str | None]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value)
                for value in values
                if value is not None and str(value)
            }
        )
    )


class ContinuitySourceBaselineEntry(BaseModel):
    """One validated source fingerprint frozen at decision time."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)

    domain: ContinuitySourceDomain
    source_ref: str
    fingerprint: str
    evidence_refs: tuple[str, ...] = ()
    captured_at: datetime
    entry_digest: str = ""

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _sort_refs(cls, value: Iterable[str | None]) -> tuple[str, ...]:
        return _normalize_refs(value)

    @model_validator(mode="after")
    def _bind_digest(self) -> "ContinuitySourceBaselineEntry":
        _as_utc(self.captured_at)
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"entry_digest"})
        )
        if self.entry_digest and self.entry_digest != expected:
            raise SourceObservationError(
                "baseline entry digest does not match canonical content"
            )
        if not self.entry_digest:
            object.__setattr__(self, "entry_digest", expected)
        return self


class ContinuitySourceBaseline(BaseModel):
    """Deterministic baseline bundle for one exact Action Case and clearance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    binding: ObservationBinding
    captured_at: datetime
    entries: tuple[ContinuitySourceBaselineEntry, ...]
    baseline_digest: str = ""

    @field_validator("entries", mode="before")
    @classmethod
    def _sort_entries(
        cls,
        value: Sequence[ContinuitySourceBaselineEntry],
    ) -> tuple[ContinuitySourceBaselineEntry, ...]:
        return tuple(
            sorted(
                tuple(value),
                key=lambda entry: (entry.domain.value, entry.source_ref),
            )
        )

    @model_validator(mode="after")
    def _validate_baseline(self) -> "ContinuitySourceBaseline":
        _as_utc(self.captured_at)
        keys = [(entry.domain.value, entry.source_ref) for entry in self.entries]
        if len(keys) != len(set(keys)):
            raise SourceObservationError("duplicate source baseline entry")
        for entry in self.entries:
            if entry.captured_at > self.captured_at:
                raise SourceObservationError(
                    "baseline entry cannot be newer than baseline bundle"
                )
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"baseline_digest"})
        )
        if self.baseline_digest and self.baseline_digest != expected:
            raise SourceObservationError(
                "baseline digest does not match canonical content"
            )
        if not self.baseline_digest:
            object.__setattr__(self, "baseline_digest", expected)
        return self

    def fingerprint_for(
        self,
        domain: ContinuitySourceDomain,
        source_ref: str,
    ) -> str:
        for entry in self.entries:
            if entry.domain == domain and entry.source_ref == source_ref:
                return entry.fingerprint
        raise SourceObservationError(
            f"source baseline is missing {domain.value}:{source_ref}"
        )



def capture_policy_baseline(
    adapter: PublicationPolicySourceAdapter,
    *,
    captured_at: datetime,
) -> ContinuitySourceBaselineEntry:
    captured_at = _as_utc(captured_at)
    if not adapter.policy.is_active(captured_at):
        raise SourceObservationError("cannot baseline an inactive policy")
    return ContinuitySourceBaselineEntry(
        domain=ContinuitySourceDomain.POLICY,
        source_ref=adapter.source_ref,
        fingerprint=adapter.fingerprint(observed_at=captured_at),
        evidence_refs=(
            adapter.policy.authority_ref,
            adapter.policy.mandate_ref,
            adapter.source_ref,
        ),
        captured_at=captured_at,
    )



def capture_mandate_baseline(
    adapter: MandateRegistrySourceAdapter,
    *,
    captured_at: datetime,
) -> ContinuitySourceBaselineEntry:
    captured_at = _as_utc(captured_at)
    mandate = adapter.registry.get_mandate(
        adapter.binding.tenant_id,
        adapter.mandate_id,
    )
    if mandate is None:
        raise SourceObservationError("cannot baseline a missing mandate")
    if not mandate.is_active(captured_at):
        raise SourceObservationError("cannot baseline an inactive mandate")
    return ContinuitySourceBaselineEntry(
        domain=ContinuitySourceDomain.MANDATE,
        source_ref=adapter.source_ref,
        fingerprint=adapter.fingerprint(observed_at=captured_at),
        evidence_refs=(*mandate.evidence_refs, adapter.source_ref),
        captured_at=captured_at,
    )



def capture_evidence_baseline(
    adapter: EvidenceStoreSourceAdapter,
    *,
    captured_at: datetime,
) -> ContinuitySourceBaselineEntry:
    captured_at = _as_utc(captured_at)
    fingerprint, refs, missing, expired = adapter._state(observed_at=captured_at)
    if missing:
        raise SourceObservationError(
            "cannot baseline missing required evidence: " + ",".join(missing)
        )
    if expired:
        raise SourceObservationError(
            "cannot baseline expired evidence: " + ",".join(expired)
        )
    return ContinuitySourceBaselineEntry(
        domain=ContinuitySourceDomain.EVIDENCE,
        source_ref=adapter.source_ref,
        fingerprint=fingerprint,
        evidence_refs=refs,
        captured_at=captured_at,
    )



def capture_target_state_baseline(
    adapter: TargetStateSourceAdapter,
    *,
    captured_at: datetime,
) -> ContinuitySourceBaselineEntry:
    captured_at = _as_utc(captured_at)
    state = adapter.expected_state
    if state.observed_at > captured_at:
        raise SourceObservationError(
            "target-state observation cannot be from the future"
        )
    return ContinuitySourceBaselineEntry(
        domain=ContinuitySourceDomain.ASSET_STATE,
        source_ref=adapter.source_ref,
        fingerprint=target_state_fingerprint(state),
        evidence_refs=(adapter.source_ref, state.state_witness_ref),
        captured_at=captured_at,
    )



def build_source_baseline(
    *,
    binding: ObservationBinding,
    captured_at: datetime,
    entries: Sequence[ContinuitySourceBaselineEntry],
) -> ContinuitySourceBaseline:
    """Freeze one canonical source baseline without granting authority."""

    return ContinuitySourceBaseline(
        binding=binding,
        captured_at=_as_utc(captured_at),
        entries=tuple(entries),
    )


__all__ = [
    "ContinuitySourceBaseline",
    "ContinuitySourceBaselineEntry",
    "build_source_baseline",
    "capture_evidence_baseline",
    "capture_mandate_baseline",
    "capture_policy_baseline",
    "capture_target_state_baseline",
]
