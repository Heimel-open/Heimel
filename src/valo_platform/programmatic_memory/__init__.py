"""Programmatic memory and governed skill evolution.

The complete event stream is retained and searched on demand. No full-history prompt
injection is provided. Skills are evidence-bound candidates and never carry execution
authority.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Iterable, Optional

from pydantic import BaseModel, Field


ZERO_HASH = "0" * 64


def _hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(payload).hexdigest()


class EvidenceEventV1(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}")
    tenant_id: str
    session_id: str
    sequence: int = Field(ge=0)
    event_type: str
    payload: dict[str, Any]
    source_refs: list[str] = Field(default_factory=list)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_hash: str = ZERO_HASH
    payload_hash: str = ""
    event_hash: str = ""
    schema_version: str = "evidence_event_v1"

    def sealed(self, previous_hash: str) -> "EvidenceEventV1":
        data = self.model_copy(deep=True)
        data.previous_hash = previous_hash
        data.payload_hash = _hash(
            {
                "tenant_id": data.tenant_id,
                "session_id": data.session_id,
                "sequence": data.sequence,
                "event_type": data.event_type,
                "payload": data.payload,
                "source_refs": data.source_refs,
                "observed_at": data.observed_at.isoformat(),
            }
        )
        data.event_hash = _hash(
            [data.event_id, data.previous_hash, data.payload_hash, data.schema_version]
        )
        return data


class FrozenEvidenceSnapshot(BaseModel):
    snapshot_id: str
    tenant_id: str
    from_sequence: int
    to_sequence: int
    event_hashes: list[str]
    head_hash: str
    created_at: datetime
    snapshot_hash: str
    schema_version: str = "frozen_evidence_snapshot_v1"


class AppendOnlyEvidenceLog:
    """In-memory reference store with append-only and replay invariants."""

    def __init__(self) -> None:
        self._events: list[EvidenceEventV1] = []

    def append(self, event: EvidenceEventV1) -> EvidenceEventV1:
        expected_sequence = len(self._events)
        if event.sequence != expected_sequence:
            raise ValueError(f"expected sequence {expected_sequence}, got {event.sequence}")
        previous = self._events[-1].event_hash if self._events else ZERO_HASH
        sealed = event.sealed(previous)
        self._events.append(sealed)
        return sealed

    def events(self) -> tuple[EvidenceEventV1, ...]:
        return tuple(event.model_copy(deep=True) for event in self._events)

    def search(
        self,
        query: str = "",
        *,
        event_types: Optional[set[str]] = None,
        predicate: Optional[Callable[[EvidenceEventV1], bool]] = None,
        limit: int = 50,
    ) -> list[EvidenceEventV1]:
        """Search stored artifacts without injecting the full log into context."""

        needle = query.casefold()
        result: list[EvidenceEventV1] = []
        for event in reversed(self._events):
            if event_types and event.event_type not in event_types:
                continue
            if predicate and not predicate(event):
                continue
            if needle:
                haystack = json.dumps(event.payload, sort_keys=True, default=str).casefold()
                if needle not in haystack and needle not in event.event_type.casefold():
                    continue
            result.append(event.model_copy(deep=True))
            if len(result) >= limit:
                break
        return result

    def verify(self) -> bool:
        previous = ZERO_HASH
        for sequence, event in enumerate(self._events):
            if event.sequence != sequence:
                return False
            expected = event.sealed(previous)
            if expected.payload_hash != event.payload_hash or expected.event_hash != event.event_hash:
                return False
            previous = event.event_hash
        return True

    def freeze(self, tenant_id: str, start: int = 0, end: Optional[int] = None) -> FrozenEvidenceSnapshot:
        end = len(self._events) if end is None else end
        selected = self._events[start:end]
        if not selected:
            raise ValueError("cannot freeze an empty evidence range")
        if any(event.tenant_id != tenant_id for event in selected):
            raise PermissionError("snapshot cannot cross tenant boundaries")
        hashes = [event.event_hash for event in selected]
        now = datetime.now(timezone.utc)
        snapshot_id = f"snap_{uuid.uuid4().hex[:16]}"
        snapshot_hash = _hash(
            [snapshot_id, tenant_id, start, end - 1, hashes, hashes[-1]]
        )
        return FrozenEvidenceSnapshot(
            snapshot_id=snapshot_id,
            tenant_id=tenant_id,
            from_sequence=start,
            to_sequence=end - 1,
            event_hashes=hashes,
            head_hash=hashes[-1],
            created_at=now,
            snapshot_hash=snapshot_hash,
        )


class SkillLifecycle(str, Enum):
    CANDIDATE = "candidate"
    SHADOW = "shadow"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class SkillCardV1(BaseModel):
    skill_id: str = Field(default_factory=lambda: f"skill_{uuid.uuid4().hex[:16]}")
    name: str
    version: str
    lifecycle: SkillLifecycle = SkillLifecycle.CANDIDATE
    procedure_ref: str
    evidence_snapshot_ref: str
    evidence_hashes: list[str]
    applicability: list[str]
    exclusions: list[str]
    verification_rules: list[str]
    reliability_estimate: float = Field(ge=0.0, le=1.0)
    consequence_ceiling: str
    authority_requirements: list[str]
    admission_receipt_ref: str
    promotion_receipt_ref: Optional[str] = None
    retirement_receipt_ref: Optional[str] = None
    schema_version: str = "skill_card_v1"

    def content_hash(self) -> str:
        return _hash(self.model_dump(exclude={"promotion_receipt_ref", "retirement_receipt_ref"}))


class SkillRegistry:
    """Governed lifecycle registry. Invocation still requires REHT clearance."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillCardV1] = {}

    def register(self, card: SkillCardV1) -> SkillCardV1:
        if not card.admission_receipt_ref:
            raise ValueError("skill candidate requires a memory admission receipt")
        if not card.evidence_snapshot_ref or not card.evidence_hashes:
            raise ValueError("skill candidate requires frozen evidence")
        if not card.applicability or not card.verification_rules:
            raise ValueError("skill boundaries and verification rules are mandatory")
        self._skills[card.skill_id] = card.model_copy(deep=True)
        return self.get(card.skill_id)

    def promote_to_shadow(self, skill_id: str, receipt_ref: str) -> SkillCardV1:
        return self._transition(skill_id, {SkillLifecycle.CANDIDATE}, SkillLifecycle.SHADOW, receipt_ref)

    def activate(
        self,
        skill_id: str,
        *,
        human_approval_ref: str,
        verification_passed: bool,
        promotion_receipt_ref: str,
    ) -> SkillCardV1:
        if not human_approval_ref:
            raise PermissionError("active skills require explicit human approval")
        if not verification_passed:
            raise PermissionError("active skills require passed verification")
        return self._transition(
            skill_id,
            {SkillLifecycle.SHADOW},
            SkillLifecycle.ACTIVE,
            promotion_receipt_ref,
        )

    def suspend(self, skill_id: str, receipt_ref: str) -> SkillCardV1:
        return self._transition(
            skill_id,
            {SkillLifecycle.ACTIVE, SkillLifecycle.SHADOW},
            SkillLifecycle.SUSPENDED,
            receipt_ref,
        )

    def retire(self, skill_id: str, receipt_ref: str) -> SkillCardV1:
        card = self._transition(
            skill_id,
            {
                SkillLifecycle.CANDIDATE,
                SkillLifecycle.SHADOW,
                SkillLifecycle.ACTIVE,
                SkillLifecycle.SUSPENDED,
            },
            SkillLifecycle.RETIRED,
            receipt_ref,
        )
        stored = self._skills[skill_id]
        stored.retirement_receipt_ref = receipt_ref
        return self.get(skill_id)

    def request_invocation(self, skill_id: str, authority_ref: str, reht_clearance_ref: str) -> SkillCardV1:
        card = self.get(skill_id)
        if card.lifecycle != SkillLifecycle.ACTIVE:
            raise PermissionError("only active skills may be proposed for invocation")
        if not authority_ref or not reht_clearance_ref:
            raise PermissionError("skill invocation requires authority and REHT clearance")
        return card

    def get(self, skill_id: str) -> SkillCardV1:
        if skill_id not in self._skills:
            raise KeyError(skill_id)
        return self._skills[skill_id].model_copy(deep=True)

    def _transition(
        self,
        skill_id: str,
        allowed: set[SkillLifecycle],
        target: SkillLifecycle,
        receipt_ref: str,
    ) -> SkillCardV1:
        if not receipt_ref:
            raise ValueError("lifecycle transition requires a receipt")
        card = self.get(skill_id)
        if card.lifecycle not in allowed:
            raise ValueError(f"invalid skill transition {card.lifecycle.value} -> {target.value}")
        card.lifecycle = target
        card.promotion_receipt_ref = receipt_ref
        self._skills[skill_id] = card
        return self.get(skill_id)


__all__ = [
    "AppendOnlyEvidenceLog",
    "EvidenceEventV1",
    "FrozenEvidenceSnapshot",
    "SkillCardV1",
    "SkillLifecycle",
    "SkillRegistry",
]
