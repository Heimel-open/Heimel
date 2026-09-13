from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .memory_lifecycle import MemoryContextItem, MemorySession, consequentially_usable
from .memory_provider import MemoryRecord, canonical_digest


class MemoryAdmissionReason(str, Enum):
    ADMITTED = "admitted"
    STALE = "stale"
    NOT_VALIDATED = "not_validated"
    AUTHORITATIVE_FLAG = "authoritative_flag"
    SNAPSHOT_MISMATCH = "snapshot_mismatch"
    BRANCH_MISMATCH = "branch_mismatch"
    PRINCIPAL_MISMATCH = "principal_mismatch"
    AGENT_MISMATCH = "agent_mismatch"
    SESSION_MISMATCH = "session_mismatch"


class MemoryUseEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    provider_ref: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: str = Field(min_length=1)
    stale: bool
    admitted: bool
    reason: MemoryAdmissionReason

    @model_validator(mode="after")
    def admission_is_consistent(self) -> "MemoryUseEntry":
        if self.admitted != (self.reason is MemoryAdmissionReason.ADMITTED):
            raise ValueError("admitted must correspond exactly to reason=admitted")
        return self


class MemoryUseEvidence(BaseModel):
    """Immutable evidence describing memory considered for one governed action.

    This object is context evidence only. It is not an authority object, a REHT
    clearance, an execution receipt, or permission to promote memory into SOL.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    created_at: datetime
    entries: tuple[MemoryUseEntry, ...]
    admitted_memory_ids: tuple[str, ...]
    evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False
    grants_clearance: bool = False
    promotes_to_sol: bool = False

    @model_validator(mode="after")
    def invariants(self) -> "MemoryUseEvidence":
        if self.grants_authority or self.grants_clearance or self.promotes_to_sol:
            raise ValueError("memory evidence cannot grant authority, clearance or SOL promotion")
        expected_ids = tuple(entry.memory_id for entry in self.entries if entry.admitted)
        if self.admitted_memory_ids != expected_ids:
            raise ValueError("admitted_memory_ids must preserve admitted entry order")
        if self.evidence_digest != evidence_digest(self):
            raise ValueError("evidence_digest does not match canonical evidence payload")
        return self


@dataclass(frozen=True)
class MemoryReplayResult:
    valid: bool
    expected_digest: str
    observed_digest: str
    errors: tuple[str, ...] = ()


def _entry_reason(
    item: MemoryContextItem,
    session: MemorySession,
    *,
    principal_id: str,
) -> MemoryAdmissionReason:
    record = item.record
    if item.authoritative:
        return MemoryAdmissionReason.AUTHORITATIVE_FLAG
    if record.branch != session.branch:
        return MemoryAdmissionReason.BRANCH_MISMATCH
    if record.snapshot_id != session.snapshot_id:
        return MemoryAdmissionReason.SNAPSHOT_MISMATCH
    if record.principal_id != principal_id:
        return MemoryAdmissionReason.PRINCIPAL_MISMATCH
    if record.agent_id != session.agent_id:
        return MemoryAdmissionReason.AGENT_MISMATCH
    if record.session_id != session.session_id:
        return MemoryAdmissionReason.SESSION_MISMATCH
    if item.stale:
        return MemoryAdmissionReason.STALE
    if not consequentially_usable(item):
        return MemoryAdmissionReason.NOT_VALIDATED
    return MemoryAdmissionReason.ADMITTED


def _entry(item: MemoryContextItem, session: MemorySession, *, principal_id: str) -> MemoryUseEntry:
    reason = _entry_reason(item, session, principal_id=principal_id)
    record = item.record
    return MemoryUseEntry(
        memory_id=record.memory_id,
        provider=record.provider,
        provider_ref=record.provider_ref,
        branch=record.branch,
        snapshot_id=record.snapshot_id,
        content_digest=record.content_digest,
        status=record.status.value,
        stale=item.stale,
        admitted=reason is MemoryAdmissionReason.ADMITTED,
        reason=reason,
    )


def _digest_payload(evidence: MemoryUseEvidence) -> dict[str, object]:
    return evidence.model_dump(
        mode="json",
        exclude={"evidence_digest"},
    )


def evidence_digest(evidence: MemoryUseEvidence) -> str:
    return canonical_digest(_digest_payload(evidence))


def build_memory_use_evidence(
    *,
    evidence_id: str,
    action_ref: str,
    principal_id: str,
    session: MemorySession,
    context: Sequence[MemoryContextItem],
    created_at: datetime | None = None,
) -> MemoryUseEvidence:
    entries = tuple(_entry(item, session, principal_id=principal_id) for item in context)
    admitted_ids = tuple(entry.memory_id for entry in entries if entry.admitted)
    timestamp = created_at or datetime.now(timezone.utc)

    provisional = MemoryUseEvidence.model_construct(
        evidence_id=evidence_id,
        action_ref=action_ref,
        principal_id=principal_id,
        agent_id=session.agent_id,
        session_id=session.session_id,
        task_id=session.task_id,
        branch=session.branch,
        snapshot_id=session.snapshot_id,
        created_at=timestamp,
        entries=entries,
        admitted_memory_ids=admitted_ids,
        evidence_digest="sha256:" + "0" * 64,
        grants_authority=False,
        grants_clearance=False,
        promotes_to_sol=False,
    )
    return MemoryUseEvidence(**{
        **provisional.model_dump(),
        "evidence_digest": evidence_digest(provisional),
    })


def admitted_records(
    evidence: MemoryUseEvidence,
    records: Iterable[MemoryRecord],
) -> tuple[MemoryRecord, ...]:
    by_id = {record.memory_id: record for record in records}
    selected: list[MemoryRecord] = []
    for entry in evidence.entries:
        if not entry.admitted:
            continue
        record = by_id.get(entry.memory_id)
        if record is None:
            raise ValueError(f"admitted memory missing during materialization: {entry.memory_id}")
        if record.content_digest != entry.content_digest:
            raise ValueError(f"memory digest changed after admission: {entry.memory_id}")
        selected.append(record)
    return tuple(selected)


def verify_memory_replay(
    expected: MemoryUseEvidence,
    observed: MemoryUseEvidence,
) -> MemoryReplayResult:
    errors: list[str] = []
    if expected.action_ref != observed.action_ref:
        errors.append("action_ref mismatch")
    if expected.snapshot_id != observed.snapshot_id:
        errors.append("snapshot_id mismatch")
    if expected.branch != observed.branch:
        errors.append("branch mismatch")
    if expected.admitted_memory_ids != observed.admitted_memory_ids:
        errors.append("admitted memory set or order mismatch")
    if expected.entries != observed.entries:
        errors.append("memory evidence entries mismatch")
    if expected.evidence_digest != evidence_digest(expected):
        errors.append("expected evidence digest is invalid")
    if observed.evidence_digest != evidence_digest(observed):
        errors.append("observed evidence digest is invalid")
    if expected.evidence_digest != observed.evidence_digest:
        errors.append("evidence digest mismatch")
    return MemoryReplayResult(
        valid=not errors,
        expected_digest=expected.evidence_digest,
        observed_digest=observed.evidence_digest,
        errors=tuple(errors),
    )
