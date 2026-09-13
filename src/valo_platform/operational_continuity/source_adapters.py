"""Read-only bridges from concrete platform sources into Operational Continuity.

The adapters observe policy, mandate, evidence and target-state sources and emit
attributed ContinuityTrigger evidence when source state no longer matches the
fingerprint frozen at decision time. They never evaluate materiality, issue
clearance, choose a RACS outcome or execute an action.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from services.evidence_store.store import EvidenceStore
from src.valo_platform.action_envelope.transition_models import TargetStateBinding
from src.valo_platform.content_operations.policy_profile import PublicationPolicyProfile
from src.valo_platform.decision_governance.continuity import (
    ContinuitySeverity,
    ContinuityTrigger,
    ContinuityTriggerKind,
    canonical_digest,
)
from src.valo_platform.decision_governance.registries import DecisionGovernanceRegistry

from .observers import FingerprintObserver, ObservationBinding


class SourceObservationError(ValueError):
    """Raised when an authoritative source cannot be observed deterministically."""


class ContinuitySourceDomain(str, Enum):
    POLICY = "policy"
    MANDATE = "mandate"
    EVIDENCE = "evidence"
    ASSET_STATE = "asset_state"


def _normalize_refs(values: Iterable[str | None] | None) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value)
                for value in (values or ())
                if value is not None and str(value)
            }
        )
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SourceObservationError(f"invalid evidence timestamp: {value!r}") from exc
    return _as_utc(parsed)


class ContinuitySourceObservation(BaseModel):
    """Digest-bound read-only observation of one concrete source."""

    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)

    domain: ContinuitySourceDomain
    source_ref: str
    expected_fingerprint: str
    current_fingerprint: str
    observed_at: datetime
    changed_fields: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    integrity_status: str = "verified"
    trigger: ContinuityTrigger | None = None
    observation_digest: str = ""

    @field_validator("changed_fields", "evidence_refs", mode="before")
    @classmethod
    def _sort_refs(cls, value: Iterable[str] | None) -> tuple[str, ...]:
        return _normalize_refs(value)

    @model_validator(mode="after")
    def _validate_observation(self) -> "ContinuitySourceObservation":
        changed = self.expected_fingerprint != self.current_fingerprint
        if changed != (self.trigger is not None):
            raise SourceObservationError(
                "trigger presence must exactly match source fingerprint drift"
            )
        if self.trigger is not None:
            if self.trigger.source_ref != self.source_ref:
                raise SourceObservationError("trigger source does not match observation")
            if self.trigger.previous_fingerprint != self.expected_fingerprint:
                raise SourceObservationError(
                    "trigger previous fingerprint does not match observation"
                )
            if self.trigger.current_fingerprint != self.current_fingerprint:
                raise SourceObservationError(
                    "trigger current fingerprint does not match observation"
                )
            if tuple(self.trigger.changed_fields) != self.changed_fields:
                raise SourceObservationError(
                    "trigger changed fields do not match observation"
                )
            if not set(self.evidence_refs).issubset(
                set(self.trigger.source_evidence_refs)
            ):
                raise SourceObservationError(
                    "trigger does not carry all source evidence references"
                )
        expected_digest = canonical_digest(
            self.model_dump(mode="json", exclude={"observation_digest"})
        )
        if self.observation_digest and self.observation_digest != expected_digest:
            raise SourceObservationError(
                "observation_digest does not match canonical observation"
            )
        if not self.observation_digest:
            object.__setattr__(self, "observation_digest", expected_digest)
        return self


class ContinuitySourceBundle(BaseModel):
    """Canonical bundle of source observations for one Action Case version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    binding: ObservationBinding
    observed_at: datetime
    observations: tuple[ContinuitySourceObservation, ...]
    bundle_digest: str = ""

    @field_validator("observations", mode="before")
    @classmethod
    def _sort_observations(
        cls,
        value: Sequence[ContinuitySourceObservation],
    ) -> tuple[ContinuitySourceObservation, ...]:
        return tuple(
            sorted(
                tuple(value),
                key=lambda item: (item.domain.value, item.source_ref),
            )
        )

    @model_validator(mode="after")
    def _validate_bundle(self) -> "ContinuitySourceBundle":
        keys = [(item.domain.value, item.source_ref) for item in self.observations]
        if len(keys) != len(set(keys)):
            raise SourceObservationError("duplicate continuity source observation")
        for item in self.observations:
            if item.observed_at > self.observed_at:
                raise SourceObservationError(
                    "source observation cannot be later than bundle timestamp"
                )
            trigger = item.trigger
            if trigger is None:
                continue
            actual = (
                trigger.tenant_id,
                trigger.action_case_id,
                trigger.action_case_hash,
                trigger.clearance_ref,
                trigger.observer_ref,
            )
            expected = (
                self.binding.tenant_id,
                self.binding.action_case_id,
                self.binding.action_case_hash,
                self.binding.clearance_ref,
                self.binding.observer_ref,
            )
            if actual != expected:
                raise SourceObservationError(
                    "source trigger does not match bundle binding"
                )
        expected_digest = canonical_digest(
            self.model_dump(mode="json", exclude={"bundle_digest"})
        )
        if self.bundle_digest and self.bundle_digest != expected_digest:
            raise SourceObservationError(
                "bundle_digest does not match canonical source bundle"
            )
        if not self.bundle_digest:
            object.__setattr__(self, "bundle_digest", expected_digest)
        return self

    @property
    def triggers(self) -> tuple[ContinuityTrigger, ...]:
        return tuple(
            item.trigger for item in self.observations if item.trigger is not None
        )

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        refs: set[str] = set()
        for item in self.observations:
            refs.update(item.evidence_refs)
        return tuple(sorted(refs))


def _observation(
    *,
    binding: ObservationBinding,
    domain: ContinuitySourceDomain,
    source_ref: str,
    trigger_kind: ContinuityTriggerKind,
    severity: ContinuitySeverity,
    expected_fingerprint: str,
    current_fingerprint: str,
    observed_at: datetime,
    changed_fields: Iterable[str],
    evidence_refs: Iterable[str],
    confidence: float = 1.0,
    freshness: float = 1.0,
    integrity_status: str = "verified",
) -> ContinuitySourceObservation:
    fields = _normalize_refs(changed_fields)
    evidence = _normalize_refs(evidence_refs)
    trigger = None
    if expected_fingerprint != current_fingerprint:
        trigger = FingerprintObserver(
            binding=binding,
            source_ref=source_ref,
            trigger_kind=trigger_kind,
            severity=severity,
        ).observe(
            previous_fingerprint=expected_fingerprint,
            current_fingerprint=current_fingerprint,
            observed_at=observed_at,
            changed_fields=fields,
            evidence_refs=evidence,
            confidence=confidence,
            freshness=freshness,
            integrity_status=integrity_status,
        )
    return ContinuitySourceObservation(
        domain=domain,
        source_ref=source_ref,
        expected_fingerprint=expected_fingerprint,
        current_fingerprint=current_fingerprint,
        observed_at=observed_at,
        changed_fields=fields if trigger is not None else (),
        evidence_refs=evidence,
        integrity_status=integrity_status,
        trigger=trigger,
    )


class PublicationPolicySourceAdapter:
    """Observe the exact digest and effective state of a publication policy."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        policy: PublicationPolicyProfile,
    ) -> None:
        if policy.tenant_id != binding.tenant_id:
            raise SourceObservationError("policy tenant does not match Action Case")
        self.binding = binding
        self.policy = policy
        self.source_ref = (
            f"publication-policy:{policy.tenant_id}:{policy.policy_id}:{policy.version}"
        )

    def fingerprint(self, *, observed_at: datetime) -> str:
        active = self.policy.is_active(_as_utc(observed_at))
        return canonical_digest(
            {
                "source_ref": self.source_ref,
                "policy_digest": self.policy.digest(),
                "active": active,
                "effective_from": self.policy.effective_from,
                "effective_until": self.policy.effective_until,
            }
        )

    def observe(
        self,
        *,
        expected_fingerprint: str,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        active = self.policy.is_active(_as_utc(observed_at))
        current = self.fingerprint(observed_at=observed_at)
        changed_fields: list[str] = []
        if current != expected_fingerprint:
            changed_fields.append("policy_digest_or_effective_state")
        if not active:
            changed_fields.append("policy_effective_window")
        return _observation(
            binding=self.binding,
            domain=ContinuitySourceDomain.POLICY,
            source_ref=self.source_ref,
            trigger_kind=ContinuityTriggerKind.POLICY_CHANGED,
            severity=(
                ContinuitySeverity.HIGH
                if not active
                else ContinuitySeverity.MEDIUM
            ),
            expected_fingerprint=expected_fingerprint,
            current_fingerprint=current,
            observed_at=observed_at,
            changed_fields=changed_fields,
            evidence_refs=(
                self.policy.authority_ref,
                self.policy.mandate_ref,
                self.source_ref,
            ),
        )


class MandateRegistrySourceAdapter:
    """Observe one mandate through the canonical DecisionGovernanceRegistry."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        registry: DecisionGovernanceRegistry,
        mandate_id: str,
    ) -> None:
        self.binding = binding
        self.registry = registry
        self.mandate_id = mandate_id
        self.source_ref = f"mandate:{binding.tenant_id}:{mandate_id}"

    def _state(self, *, observed_at: datetime) -> tuple[str, tuple[str, ...], bool]:
        mandate = self.registry.get_mandate(
            self.binding.tenant_id,
            self.mandate_id,
        )
        if mandate is None:
            return (
                canonical_digest(
                    {
                        "source_ref": self.source_ref,
                        "record_missing": True,
                    }
                ),
                (self.source_ref,),
                False,
            )
        fingerprint = mandate.fingerprint or mandate.compute_fingerprint()
        active = mandate.is_active(_as_utc(observed_at))
        current = canonical_digest(
            {
                "source_ref": self.source_ref,
                "record_fingerprint": fingerprint,
                "version": mandate.version,
                "status": mandate.status.value,
                "active": active,
                "effective_from": mandate.effective_from,
                "effective_until": mandate.effective_until,
            }
        )
        refs = _normalize_refs((*mandate.evidence_refs, self.source_ref))
        return current, refs, active

    def fingerprint(self, *, observed_at: datetime) -> str:
        current, _, _ = self._state(observed_at=observed_at)
        return current

    def observe(
        self,
        *,
        expected_fingerprint: str,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        current, evidence_refs, active = self._state(observed_at=observed_at)
        mandate = self.registry.get_mandate(
            self.binding.tenant_id,
            self.mandate_id,
        )
        changed_fields: list[str] = []
        if mandate is None:
            changed_fields.append("mandate_missing")
        else:
            if current != expected_fingerprint:
                changed_fields.append("mandate_record_or_status")
            if not active:
                changed_fields.append("mandate_active_state")
        return _observation(
            binding=self.binding,
            domain=ContinuitySourceDomain.MANDATE,
            source_ref=self.source_ref,
            trigger_kind=ContinuityTriggerKind.MANDATE_CHANGED,
            severity=ContinuitySeverity.HIGH,
            expected_fingerprint=expected_fingerprint,
            current_fingerprint=current,
            observed_at=observed_at,
            changed_fields=changed_fields,
            evidence_refs=evidence_refs,
        )


class EvidenceStoreSourceAdapter:
    """Observe required evidence rows from the append-only EvidenceStore."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        store: EvidenceStore,
        receipt_id: str,
        required_evidence_ids: Iterable[str],
        max_age: timedelta | None = None,
    ) -> None:
        if max_age is not None and max_age <= timedelta(0):
            raise SourceObservationError("max_age must be positive")
        self.binding = binding
        self.store = store
        self.receipt_id = receipt_id
        self.required_evidence_ids = _normalize_refs(required_evidence_ids)
        self.max_age = max_age
        self.source_ref = f"evidence-receipt:{binding.tenant_id}:{receipt_id}"

    def _state(
        self,
        *,
        observed_at: datetime,
    ) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        rows = self.store.find_by_receipt(
            self.binding.tenant_id,
            self.receipt_id,
        )
        normalized: list[dict[str, object]] = []
        for row in rows:
            evidence_id = str(row.get("evidence_id", ""))
            row_receipt = str(row.get("receipt_id", ""))
            row_tenant = str(row.get("tenant_id", ""))
            if not evidence_id:
                raise SourceObservationError("evidence row lacks evidence_id")
            if row_receipt != self.receipt_id or row_tenant != self.binding.tenant_id:
                raise SourceObservationError("evidence row source binding mismatch")
            normalized.append(
                {
                    "evidence_id": evidence_id,
                    "receipt_id": row_receipt,
                    "tenant_id": row_tenant,
                    "evidence_type": str(row.get("evidence_type", "")),
                    "payload": row.get("payload") or {},
                    "created_at": str(row.get("created_at", "")),
                }
            )
        normalized.sort(key=lambda row: (str(row["evidence_id"]), str(row["created_at"])))
        present = {str(row["evidence_id"]) for row in normalized}
        missing = tuple(
            item for item in self.required_evidence_ids if item not in present
        )
        expired: list[str] = []
        now = _as_utc(observed_at)
        if self.max_age is not None:
            for row in normalized:
                created_at = _parse_timestamp(str(row["created_at"]))
                if now - created_at > self.max_age:
                    expired.append(str(row["evidence_id"]))
        bundle_digest = canonical_digest(
            {
                "source_ref": self.source_ref,
                "required_evidence_ids": list(self.required_evidence_ids),
                "items": normalized,
            }
        )
        state_fingerprint = canonical_digest(
            {
                "bundle_digest": bundle_digest,
                "missing_required": list(missing),
                "expired_evidence": sorted(set(expired)),
                "max_age_seconds": (
                    self.max_age.total_seconds()
                    if self.max_age is not None
                    else None
                ),
            }
        )
        refs = _normalize_refs(
            (
                self.source_ref,
                *(f"evidence:{item}" for item in present),
            )
        )
        return state_fingerprint, refs, missing, tuple(sorted(set(expired)))

    def fingerprint(self, *, observed_at: datetime) -> str:
        current, _, _, _ = self._state(observed_at=observed_at)
        return current

    def observe(
        self,
        *,
        expected_fingerprint: str,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        current, refs, missing, expired = self._state(observed_at=observed_at)
        changed_fields: list[str] = []
        if missing:
            changed_fields.extend(f"missing:{item}" for item in missing)
        if expired:
            changed_fields.extend(f"expired:{item}" for item in expired)
        if current != expected_fingerprint and not changed_fields:
            changed_fields.append("evidence_bundle")
        trigger_kind = (
            ContinuityTriggerKind.EVIDENCE_EXPIRED
            if expired
            else ContinuityTriggerKind.EVIDENCE_CHANGED
        )
        return _observation(
            binding=self.binding,
            domain=ContinuitySourceDomain.EVIDENCE,
            source_ref=self.source_ref,
            trigger_kind=trigger_kind,
            severity=ContinuitySeverity.HIGH,
            expected_fingerprint=expected_fingerprint,
            current_fingerprint=current,
            observed_at=observed_at,
            changed_fields=changed_fields,
            evidence_refs=refs,
            freshness=0.0 if expired else 1.0,
        )


def target_state_fingerprint(binding: TargetStateBinding) -> str:
    """Return the canonical fingerprint for target identity and state, not read time."""

    return canonical_digest(
        binding.model_dump(mode="json", exclude={"observed_at"})
    )


class TargetStateSourceAdapter:
    """Observe the concrete target revision and state witness at commit time."""

    def __init__(
        self,
        *,
        binding: ObservationBinding,
        expected_state: TargetStateBinding,
    ) -> None:
        self.binding = binding
        self.expected_state = expected_state
        self.source_ref = (
            f"target-state:{expected_state.system_id}:{expected_state.object_id}"
        )

    def fingerprint(self, current_state: TargetStateBinding) -> str:
        return target_state_fingerprint(current_state)

    def observe(
        self,
        *,
        current_state: TargetStateBinding,
        observed_at: datetime,
    ) -> ContinuitySourceObservation:
        if current_state.system_id != self.expected_state.system_id:
            raise SourceObservationError("target system changed outside source binding")
        if current_state.object_id != self.expected_state.object_id:
            raise SourceObservationError("target object changed outside source binding")

        expected = target_state_fingerprint(self.expected_state)
        current = target_state_fingerprint(current_state)
        fields: list[str] = []
        for field_name in (
            "revision_type",
            "revision_value",
            "current_state_hash",
            "state_witness_ref",
        ):
            if getattr(self.expected_state, field_name) != getattr(
                current_state, field_name
            ):
                fields.append(field_name)
        evidence_refs = _normalize_refs(
            (
                self.source_ref,
                self.expected_state.state_witness_ref,
                current_state.state_witness_ref,
            )
        )
        return _observation(
            binding=self.binding,
            domain=ContinuitySourceDomain.ASSET_STATE,
            source_ref=self.source_ref,
            trigger_kind=ContinuityTriggerKind.ASSET_STATE_CHANGED,
            severity=ContinuitySeverity.MEDIUM,
            expected_fingerprint=expected,
            current_fingerprint=current,
            observed_at=observed_at,
            changed_fields=fields,
            evidence_refs=evidence_refs,
        )


def build_source_bundle(
    *,
    binding: ObservationBinding,
    observed_at: datetime,
    observations: Sequence[ContinuitySourceObservation],
) -> ContinuitySourceBundle:
    """Build one digest-bound source bundle without adding decision authority."""

    return ContinuitySourceBundle(
        binding=binding,
        observed_at=observed_at,
        observations=tuple(observations),
    )


__all__ = [
    "ContinuitySourceBundle",
    "ContinuitySourceDomain",
    "ContinuitySourceObservation",
    "EvidenceStoreSourceAdapter",
    "MandateRegistrySourceAdapter",
    "PublicationPolicySourceAdapter",
    "SourceObservationError",
    "TargetStateSourceAdapter",
    "build_source_bundle",
    "target_state_fingerprint",
]
