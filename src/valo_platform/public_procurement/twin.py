from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..memory_provider import canonical_digest


TWIN_VIEW_VERSION = "0.1.0"


class ProcurementTwinRole(str, Enum):
    BUYER = "buyer"
    APPROVER = "approver"
    AUDITOR = "auditor"


class ProcurementLifecycleStage(str, Enum):
    NEEDS_PLAN = "needs_plan"
    PROCEDURE = "procedure"
    ELIGIBILITY = "eligibility"
    EVALUATION = "evaluation"
    AWARD = "award"
    CONTRACT = "contract"
    MODIFICATION = "modification"
    PAYMENT = "payment"
    PERFORMANCE = "performance"
    PUBLICATION = "publication"
    CLOSED = "closed"


class ProcurementTraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    event_id: str = Field(min_length=1)
    stage: ProcurementLifecycleStage
    object_ref: str = Field(min_length=1)
    status: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    occurred_at: datetime
    actor_ref: str | None = None
    action_case_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    clearance_ref: str | None = None
    execution_receipt_ref: str | None = None
    outcome_receipt_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    pending_action: str | None = None
    attention_required: bool = False
    protected_details: Mapping[str, str] = Field(default_factory=dict)
    event_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False

    @model_validator(mode="after")
    def verify_event(self) -> "ProcurementTraceEvent":
        if self.grants_authority:
            raise ValueError("Twin trace event cannot grant authority")
        if self.event_digest != procurement_trace_event_digest(self):
            raise ValueError("event_digest mismatch")
        return self


class ProcurementTwinEventView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    event_id: str = Field(min_length=1)
    stage: ProcurementLifecycleStage
    object_ref: str = Field(min_length=1)
    status: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    occurred_at: datetime
    actor_ref: str | None = None
    action_case_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    clearance_ref: str | None = None
    execution_receipt_ref: str | None = None
    outcome_receipt_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    pending_action: str | None = None
    attention_required: bool = False
    protected_details: Mapping[str, str] = Field(default_factory=dict)
    source_event_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ProcurementTwinSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    twin_view_version: str = TWIN_VIEW_VERSION
    tenant_id: str = Field(min_length=1)
    procedure_ref: str = Field(min_length=1)
    role: ProcurementTwinRole
    as_of: datetime
    current_stage: ProcurementLifecycleStage
    events: tuple[ProcurementTwinEventView, ...]
    pending_actions: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    receipt_refs: tuple[str, ...] = ()
    attention_count: int = Field(ge=0)
    snapshot_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    read_only: bool = True
    grants_authority: bool = False

    @model_validator(mode="after")
    def verify_snapshot(self) -> "ProcurementTwinSnapshot":
        if not self.read_only:
            raise ValueError("Twin procurement snapshot must be read-only")
        if self.grants_authority:
            raise ValueError("Twin procurement snapshot cannot grant authority")
        if not self.events:
            raise ValueError("Twin procurement snapshot requires events")
        expected_sequences = tuple(range(1, len(self.events) + 1))
        if tuple(event.sequence for event in self.events) != expected_sequences:
            raise ValueError("Twin events must be contiguous and ordered")
        if any(_as_utc(event.occurred_at) > _as_utc(self.as_of) for event in self.events):
            raise ValueError("Twin snapshot cannot include events after as_of")
        if self.current_stage is not self.events[-1].stage:
            raise ValueError("current_stage must match latest visible event")
        if self.attention_count != sum(event.attention_required for event in self.events):
            raise ValueError("attention_count mismatch")
        if self.snapshot_digest != procurement_twin_snapshot_digest(self):
            raise ValueError("snapshot_digest mismatch")
        return self


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def procurement_trace_event_digest(event: ProcurementTraceEvent) -> str:
    return canonical_digest(event.model_dump(mode="json", exclude={"event_digest"}))


def procurement_twin_snapshot_digest(snapshot: ProcurementTwinSnapshot) -> str:
    return canonical_digest(
        snapshot.model_dump(mode="json", exclude={"snapshot_digest", "as_of"})
    )


def build_procurement_trace_event(
    *,
    sequence: int,
    event_id: str,
    stage: ProcurementLifecycleStage,
    object_ref: str,
    status: str,
    summary: str,
    occurred_at: datetime,
    actor_ref: str | None = None,
    action_case_digest: str | None = None,
    clearance_ref: str | None = None,
    execution_receipt_ref: str | None = None,
    outcome_receipt_ref: str | None = None,
    evidence_refs: tuple[str, ...] = (),
    evidence_gaps: tuple[str, ...] = (),
    pending_action: str | None = None,
    attention_required: bool = False,
    protected_details: Mapping[str, str] | None = None,
) -> ProcurementTraceEvent:
    payload = {
        "sequence": sequence,
        "event_id": event_id,
        "stage": stage,
        "object_ref": object_ref,
        "status": status,
        "summary": summary,
        "occurred_at": _as_utc(occurred_at),
        "actor_ref": actor_ref,
        "action_case_digest": action_case_digest,
        "clearance_ref": clearance_ref,
        "execution_receipt_ref": execution_receipt_ref,
        "outcome_receipt_ref": outcome_receipt_ref,
        "evidence_refs": tuple(sorted(set(evidence_refs))),
        "evidence_gaps": tuple(sorted(set(evidence_gaps))),
        "pending_action": pending_action,
        "attention_required": attention_required,
        "protected_details": dict(protected_details or {}),
        "grants_authority": False,
    }
    provisional = ProcurementTraceEvent.model_construct(
        **payload,
        event_digest="sha256:" + "0" * 64,
    )
    return ProcurementTraceEvent(
        **payload,
        event_digest=procurement_trace_event_digest(provisional),
    )


def _event_view(event: ProcurementTraceEvent, role: ProcurementTwinRole) -> ProcurementTwinEventView:
    if role is ProcurementTwinRole.BUYER:
        actor_ref = event.actor_ref
        evidence_refs = event.evidence_refs
        evidence_gaps = event.evidence_gaps
        pending_action = event.pending_action
        protected_details = dict(event.protected_details)
    elif role is ProcurementTwinRole.APPROVER:
        actor_ref = event.actor_ref
        evidence_refs = event.evidence_refs
        evidence_gaps = event.evidence_gaps
        pending_action = event.pending_action
        protected_details = {}
    else:
        actor_ref = None
        evidence_refs = ()
        evidence_gaps = ()
        pending_action = None
        protected_details = {}

    return ProcurementTwinEventView(
        sequence=event.sequence,
        event_id=event.event_id,
        stage=event.stage,
        object_ref=event.object_ref,
        status=event.status,
        summary=event.summary,
        occurred_at=event.occurred_at,
        actor_ref=actor_ref,
        action_case_digest=event.action_case_digest,
        clearance_ref=event.clearance_ref,
        execution_receipt_ref=event.execution_receipt_ref,
        outcome_receipt_ref=event.outcome_receipt_ref,
        evidence_refs=evidence_refs,
        evidence_gaps=evidence_gaps,
        pending_action=pending_action,
        attention_required=event.attention_required,
        protected_details=protected_details,
        source_event_digest=event.event_digest,
    )


def build_procurement_twin_snapshot(
    *,
    tenant_id: str,
    procedure_ref: str,
    role: ProcurementTwinRole,
    events: tuple[ProcurementTraceEvent, ...],
    as_of: datetime,
) -> ProcurementTwinSnapshot:
    if not events:
        raise ValueError("events cannot be empty")
    cutoff = _as_utc(as_of)
    visible = tuple(event for event in events if _as_utc(event.occurred_at) <= cutoff)
    if not visible:
        raise ValueError("no trace events exist at or before as_of")
    ordered = tuple(sorted(visible, key=lambda item: (item.sequence, item.event_id)))
    if tuple(event.sequence for event in ordered) != tuple(range(1, len(ordered) + 1)):
        raise ValueError("trace events must be contiguous")

    views = tuple(_event_view(event, role) for event in ordered)
    pending_actions = tuple(
        sorted({event.pending_action for event in views if event.pending_action})
    )
    evidence_gaps = tuple(
        sorted({gap for event in views for gap in event.evidence_gaps})
    )
    receipt_refs = tuple(
        sorted(
            {
                receipt
                for event in views
                for receipt in (
                    event.clearance_ref,
                    event.execution_receipt_ref,
                    event.outcome_receipt_ref,
                )
                if receipt
            }
        )
    )
    payload = {
        "twin_view_version": TWIN_VIEW_VERSION,
        "tenant_id": tenant_id,
        "procedure_ref": procedure_ref,
        "role": role,
        "as_of": cutoff,
        "current_stage": views[-1].stage,
        "events": views,
        "pending_actions": pending_actions,
        "evidence_gaps": evidence_gaps,
        "receipt_refs": receipt_refs,
        "attention_count": sum(event.attention_required for event in views),
        "read_only": True,
        "grants_authority": False,
    }
    provisional = ProcurementTwinSnapshot.model_construct(
        **payload,
        snapshot_digest="sha256:" + "0" * 64,
    )
    return ProcurementTwinSnapshot(
        **payload,
        snapshot_digest=procurement_twin_snapshot_digest(provisional),
    )
