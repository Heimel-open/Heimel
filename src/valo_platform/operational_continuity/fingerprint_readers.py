"""Concrete owner readers for current Operational Continuity fingerprints.

The readers query existing authoritative stores. They do not create a new truth
registry and never fall back to the frozen values carried by an Action Case.

Implemented owners:
- authority: DecisionGovernanceRegistry purpose/mandate/delegation records;
- policy: exact append-only PublicationPolicyRegistry version;
- evidence: append-only EvidenceStore through EvidenceStoreSourceAdapter;
- state: latest persisted ActionCaseRecord from SQLite decision governance.

Context deliberately remains an explicit required reader because the repository
does not yet contain one canonical current-context owner.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from src.valo_platform.content_operations.policy_registry import (
    PublicationPolicyRegistry,
    PublicationPolicyRegistryError,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.continuity import (
    ContinuityIntegrityStatus,
    canonical_digest,
)
from src.valo_platform.decision_governance.registries import (
    DecisionGovernanceRegistry,
)
from src.valo_platform.decision_governance.store import (
    SQLiteDecisionGovernanceStore,
)

from .fingerprint_snapshot import (
    CompositeCurrentDecisionFingerprintProvider,
    CurrentDecisionFingerprintProvider,
    DecisionFingerprintKind,
    DecisionFingerprintObservation,
    DecisionFingerprintReader,
    DecisionFingerprintSnapshotError,
)
from .observers import ObservationBinding
from .source_adapters import EvidenceStoreSourceAdapter


class FingerprintOwnerReaderError(DecisionFingerprintSnapshotError):
    """Raised when an authoritative owner cannot prove current state."""


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise FingerprintOwnerReaderError(
            "fingerprint owner read time must be timezone-aware"
        )
    return value.astimezone(timezone.utc)


def _normalized_refs(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if str(value)}))


def _require_action_case_binding(
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
            "configured Action Case does not match fingerprint snapshot binding"
        )


def _parse_ref(
    value: str,
    *,
    prefix: str,
    parts: int,
) -> tuple[str, ...]:
    parsed = tuple(value.split(":"))
    if len(parsed) != parts or parsed[0] != prefix or any(not item for item in parsed):
        raise FingerprintOwnerReaderError(
            f"malformed canonical {prefix} reference"
        )
    return parsed


@dataclass(frozen=True)
class AuthorityRegistryDecisionFingerprintReader:
    """Read the pinned purpose/mandate/delegation from their canonical registry."""

    action_case: ActionCaseRecord
    registry: DecisionGovernanceRegistry
    reader_ref: str = "decision-governance-registry:authority-reader:1"
    kind: DecisionFingerprintKind = DecisionFingerprintKind.AUTHORITY

    def read(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> DecisionFingerprintObservation:
        observed_at = _as_utc(observed_at)
        _require_action_case_binding(self.action_case, binding)

        purpose_ref = self.action_case.purpose_record_ref
        purpose = self.registry.get_purpose(
            binding.tenant_id,
            purpose_ref.purpose_id,
            purpose_ref.version,
        )
        if purpose is None:
            raise FingerprintOwnerReaderError("pinned purpose record is missing")
        if not purpose.is_active(observed_at):
            raise FingerprintOwnerReaderError("pinned purpose record is not active")
        purpose_fingerprint = purpose.fingerprint or purpose.compute_fingerprint()
        if purpose_fingerprint != purpose_ref.fingerprint:
            raise FingerprintOwnerReaderError("pinned purpose fingerprint changed")
        if purpose.to_ref().record_ref != purpose_ref.record_ref:
            raise FingerprintOwnerReaderError("pinned purpose reference changed")

        _, mandate_tenant, mandate_id, mandate_version = _parse_ref(
            self.action_case.mandate_ref,
            prefix="mandate",
            parts=4,
        )
        if mandate_tenant != binding.tenant_id:
            raise FingerprintOwnerReaderError("mandate reference crosses tenant boundary")
        mandate = self.registry.get_mandate(binding.tenant_id, mandate_id)
        if mandate is None:
            raise FingerprintOwnerReaderError("pinned mandate record is missing")
        if mandate.version != mandate_version:
            raise FingerprintOwnerReaderError("pinned mandate version changed")
        if not mandate.is_active(observed_at):
            raise FingerprintOwnerReaderError("pinned mandate record is not active")
        mandate_fingerprint = mandate.fingerprint or mandate.compute_fingerprint()
        if mandate_fingerprint != self.action_case.mandate_fingerprint:
            raise FingerprintOwnerReaderError("pinned mandate fingerprint changed")
        if (
            mandate.purpose_id != purpose.purpose_id
            or mandate.purpose_version != purpose.version
        ):
            raise FingerprintOwnerReaderError(
                "pinned mandate no longer binds the pinned purpose"
            )

        evidence_refs: set[str] = {
            purpose_ref.record_ref,
            self.action_case.mandate_ref,
            *purpose.evidence_refs,
            *mandate.evidence_refs,
        }
        source_ref = self.action_case.mandate_ref
        fingerprint = mandate_fingerprint

        if self.action_case.delegation_ref is not None:
            if self.action_case.delegation_fingerprint is None:
                raise FingerprintOwnerReaderError(
                    "pinned delegation reference lacks fingerprint"
                )
            _, delegation_tenant, delegation_id = _parse_ref(
                self.action_case.delegation_ref,
                prefix="delegation",
                parts=3,
            )
            if delegation_tenant != binding.tenant_id:
                raise FingerprintOwnerReaderError(
                    "delegation reference crosses tenant boundary"
                )
            delegation = self.registry.delegations.get(
                (binding.tenant_id, delegation_id)
            )
            if delegation is None:
                raise FingerprintOwnerReaderError(
                    "pinned delegation record is missing"
                )
            if not delegation.is_active(observed_at):
                raise FingerprintOwnerReaderError(
                    "pinned delegation record is not active"
                )
            if delegation.mandate_id != mandate.mandate_id:
                raise FingerprintOwnerReaderError(
                    "pinned delegation no longer binds the mandate"
                )
            delegation_fingerprint = (
                delegation.fingerprint or delegation.compute_fingerprint()
            )
            if delegation_fingerprint != self.action_case.delegation_fingerprint:
                raise FingerprintOwnerReaderError(
                    "pinned delegation fingerprint changed"
                )
            fingerprint = delegation_fingerprint
            source_ref = self.action_case.delegation_ref
            evidence_refs.update(delegation.evidence_refs)
            evidence_refs.add(self.action_case.delegation_ref)

        return DecisionFingerprintObservation(
            binding=binding,
            kind=self.kind,
            fingerprint=fingerprint,
            source_ref=source_ref,
            reader_ref=self.reader_ref,
            evidence_refs=_normalized_refs(evidence_refs),
            observed_at=observed_at,
        )


@dataclass(frozen=True)
class RegisteredPolicyDecisionFingerprintReader:
    """Read one exact active policy version from the append-only registry."""

    action_case: ActionCaseRecord
    registry: PublicationPolicyRegistry
    policy_id: str
    version: str
    reader_ref: str = "publication-policy-registry:fingerprint-reader:1"
    kind: DecisionFingerprintKind = DecisionFingerprintKind.POLICY

    @property
    def policy_ref(self) -> str:
        return (
            f"publication-policy-registry:{self.action_case.tenant_id}:"
            f"{self.policy_id}:{self.version}"
        )

    def read(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> DecisionFingerprintObservation:
        observed_at = _as_utc(observed_at)
        _require_action_case_binding(self.action_case, binding)
        if self.action_case.policy_fingerprint is None:
            raise FingerprintOwnerReaderError(
                "Action Case does not carry a canonical policy fingerprint"
            )
        if self.policy_ref not in set(self.action_case.policy_refs):
            raise FingerprintOwnerReaderError(
                "Action Case does not bind the exact registered policy version"
            )
        try:
            registered = self.registry.get_exact(
                binding.tenant_id,
                self.policy_id,
                self.version,
            )
        except PublicationPolicyRegistryError as exc:
            raise FingerprintOwnerReaderError(
                "registered policy lookup or chain verification failed"
            ) from exc
        if not registered.is_active(observed_at):
            raise FingerprintOwnerReaderError(
                "registered policy version is not active"
            )
        if registered.profile_digest != self.action_case.policy_fingerprint:
            raise FingerprintOwnerReaderError(
                "registered policy fingerprint changed"
            )
        evidence_refs = _normalized_refs(
            (
                self.policy_ref,
                registered.profile.authority_ref,
                registered.profile.mandate_ref,
                *registered.event_hashes,
            )
        )
        return DecisionFingerprintObservation(
            binding=binding,
            kind=self.kind,
            fingerprint=registered.profile_digest,
            source_ref=self.policy_ref,
            reader_ref=self.reader_ref,
            evidence_refs=evidence_refs,
            observed_at=observed_at,
        )


@dataclass(frozen=True)
class EvidenceStoreDecisionFingerprintReader:
    """Verify exact Action Case evidence refs through the append-only store."""

    action_case: ActionCaseRecord
    adapter: EvidenceStoreSourceAdapter
    expected_source_fingerprint: str
    reader_ref: str = "evidence-store:fingerprint-reader:1"
    kind: DecisionFingerprintKind = DecisionFingerprintKind.EVIDENCE

    def read(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> DecisionFingerprintObservation:
        observed_at = _as_utc(observed_at)
        _require_action_case_binding(self.action_case, binding)
        if self.adapter.binding != binding:
            raise FingerprintOwnerReaderError(
                "evidence adapter binding does not match Action Case"
            )
        canonical_refs = _normalized_refs(self.action_case.evidence_refs)
        expected_refs = _normalized_refs(
            f"evidence:{item}" for item in self.adapter.required_evidence_ids
        )
        if canonical_refs != expected_refs:
            raise FingerprintOwnerReaderError(
                "Action Case evidence refs do not exactly match EvidenceStore ids"
            )
        fingerprint = canonical_digest(list(canonical_refs))
        if fingerprint != self.action_case.evidence_fingerprint:
            raise FingerprintOwnerReaderError(
                "Action Case evidence fingerprint is not the canonical refs digest"
            )
        try:
            source_observation = self.adapter.observe(
                expected_fingerprint=self.expected_source_fingerprint,
                observed_at=observed_at,
            )
        except Exception as exc:
            raise FingerprintOwnerReaderError(
                "EvidenceStore current-state verification failed"
            ) from exc
        if source_observation.integrity_status != "verified":
            raise FingerprintOwnerReaderError(
                "EvidenceStore observation integrity is not verified"
            )
        changed_fields = set(source_observation.changed_fields)
        if any(
            field.startswith("missing:") or field.startswith("expired:")
            for field in changed_fields
        ):
            raise FingerprintOwnerReaderError(
                "required Action Case evidence is missing or expired"
            )
        evidence_refs = _normalized_refs(
            (
                source_observation.source_ref,
                source_observation.observation_digest,
                *source_observation.evidence_refs,
                *canonical_refs,
            )
        )
        return DecisionFingerprintObservation(
            binding=binding,
            kind=self.kind,
            fingerprint=fingerprint,
            source_ref=source_observation.source_ref,
            reader_ref=self.reader_ref,
            evidence_refs=evidence_refs,
            observed_at=observed_at,
        )


_EXECUTABLE_STATES = {
    ActionCaseLifecycleState.CLEARED,
    ActionCaseLifecycleState.CONSTRAINED,
}


@dataclass(frozen=True)
class SQLiteActionCaseStateDecisionFingerprintReader:
    """Read the latest immutable ActionCaseRecord from durable SQLite state."""

    action_case: ActionCaseRecord
    store: SQLiteDecisionGovernanceStore
    reader_ref: str = "decision-governance-store:action-case-state-reader:1"
    kind: DecisionFingerprintKind = DecisionFingerprintKind.STATE

    def _latest_record(self, binding: ObservationBinding) -> ActionCaseRecord:
        try:
            with sqlite3.connect(
                self.store.database_path,
                timeout=30,
            ) as connection:
                row = connection.execute(
                    """
                    SELECT payload
                    FROM decision_governance_artifacts
                    WHERE tenant_id = ?
                      AND artifact_type = 'action_case_record'
                      AND artifact_id = ?
                    ORDER BY CAST(artifact_version AS INTEGER) DESC
                    LIMIT 1
                    """,
                    (binding.tenant_id, binding.action_case_id),
                ).fetchone()
        except sqlite3.Error as exc:
            raise FingerprintOwnerReaderError(
                "current Action Case record lookup failed"
            ) from exc
        if row is None:
            raise FingerprintOwnerReaderError(
                "current Action Case record is missing"
            )
        try:
            return ActionCaseRecord.model_validate_json(row[0])
        except Exception as exc:
            raise FingerprintOwnerReaderError(
                "current Action Case record is invalid"
            ) from exc

    def read(
        self,
        *,
        binding: ObservationBinding,
        observed_at: datetime,
    ) -> DecisionFingerprintObservation:
        observed_at = _as_utc(observed_at)
        _require_action_case_binding(self.action_case, binding)
        current = self._latest_record(binding)
        if current.tenant_id != binding.tenant_id or current.case_id != binding.action_case_id:
            raise FingerprintOwnerReaderError(
                "current Action Case record crosses binding"
            )
        if current.lifecycle_state not in _EXECUTABLE_STATES:
            raise FingerprintOwnerReaderError(
                "current Action Case lifecycle is not executable"
            )
        if current.clearance_ref != binding.clearance_ref:
            raise FingerprintOwnerReaderError(
                "current Action Case no longer binds the clearance"
            )
        if current.updated_at > observed_at:
            raise FingerprintOwnerReaderError(
                "current Action Case record is from the future"
            )
        evidence_ref = (
            f"action-case-record:{current.tenant_id}:{current.case_id}:"
            f"v{current.record_version}:{current.case_hash}"
        )
        return DecisionFingerprintObservation(
            binding=binding,
            kind=self.kind,
            fingerprint=current.case_hash,
            source_ref=evidence_ref,
            reader_ref=self.reader_ref,
            evidence_refs=(evidence_ref, current.clearance_ref),
            observed_at=observed_at,
        )


def build_canonical_owner_fingerprint_provider(
    *,
    authority_reader: AuthorityRegistryDecisionFingerprintReader,
    policy_reader: RegisteredPolicyDecisionFingerprintReader,
    context_reader: DecisionFingerprintReader,
    state_reader: SQLiteActionCaseStateDecisionFingerprintReader,
    evidence_reader: EvidenceStoreDecisionFingerprintReader,
) -> CurrentDecisionFingerprintProvider:
    """Build the exact five-reader provider; context has no implicit fallback."""

    if context_reader.kind != DecisionFingerprintKind.CONTEXT:
        raise FingerprintOwnerReaderError(
            "canonical provider requires an explicit context owner reader"
        )
    return CompositeCurrentDecisionFingerprintProvider(
        (
            authority_reader,
            policy_reader,
            context_reader,
            state_reader,
            evidence_reader,
        )
    )


__all__ = [
    "AuthorityRegistryDecisionFingerprintReader",
    "EvidenceStoreDecisionFingerprintReader",
    "FingerprintOwnerReaderError",
    "RegisteredPolicyDecisionFingerprintReader",
    "SQLiteActionCaseStateDecisionFingerprintReader",
    "build_canonical_owner_fingerprint_provider",
]
