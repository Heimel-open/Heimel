from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import canonical_digest


class RequirementStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    HOLD = "HOLD"
    MISSING = "MISSING"


class ReplayOutcome(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    INVALIDATED = "INVALIDATED"


def _sorted_unique(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} cannot contain blank references")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
    return tuple(sorted(values))


class BurdenRecord(BaseModel):
    """Domain-neutral consequence burden ledger entry.

    A burden record makes exposure inspectable and replayable. It never grants
    authority, issues clearance, or determines whether an action may execute.
    """

    schema_version: Literal["kernel_burden_record.v1"] = "kernel_burden_record.v1"
    burden_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    consequence_ref: str = Field(min_length=1)
    burden_type: str = Field(min_length=1)
    measurement_unit: str = Field(min_length=1)
    measurement_period: str = Field(min_length=1)
    quantity: Decimal | None = None
    lower_bound: Decimal | None = None
    upper_bound: Decimal | None = None
    responsible_bearer_ref: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    source_refs: tuple[str, ...] = ()
    assumption_refs: tuple[str, ...] = ()
    enforcement_ref: str = Field(min_length=1)
    update_cadence: str | None = None
    recorded_at: datetime
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute: Literal[False] = False
    burden_digest: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("evidence_refs", "source_refs", "assumption_refs")
    @classmethod
    def normalize_refs(cls, values: tuple[str, ...], info) -> tuple[str, ...]:
        return _sorted_unique(values, info.field_name)

    @model_validator(mode="after")
    def validate_burden(self) -> BurdenRecord:
        point = self.quantity is not None
        range_present = self.lower_bound is not None or self.upper_bound is not None
        if point == range_present:
            raise ValueError("burden requires either quantity or lower/upper bounds")
        if range_present:
            if self.lower_bound is None or self.upper_bound is None:
                raise ValueError("burden range requires both lower_bound and upper_bound")
            if self.lower_bound > self.upper_bound:
                raise ValueError("burden lower_bound cannot exceed upper_bound")
        payload = self.model_dump(mode="python", exclude={"burden_digest"})
        if canonical_digest(payload) != self.burden_digest:
            raise ValueError("burden digest mismatch")
        return self


class ReplayRequirement(BaseModel):
    schema_version: Literal["kernel_replay_requirement.v1"] = (
        "kernel_replay_requirement.v1"
    )
    requirement_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    hard_requirement: bool = True
    status: RequirementStatus
    evidence_refs: tuple[str, ...] = ()
    assumption_refs: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("evidence_refs", "assumption_refs", "reason_codes")
    @classmethod
    def normalize_refs(cls, values: tuple[str, ...], info) -> tuple[str, ...]:
        return _sorted_unique(values, info.field_name)

    @model_validator(mode="after")
    def validate_requirement(self) -> ReplayRequirement:
        if self.status == RequirementStatus.PASS and not self.evidence_refs:
            raise ValueError("PASS replay requirement requires evidence")
        if self.status != RequirementStatus.PASS and not self.reason_codes:
            raise ValueError("non-PASS replay requirement requires reason_codes")
        return self


class ReplayRecord(BaseModel):
    """Reconstructable record for a governed boundary/object decision.

    Replay here means deterministic reconstruction from pinned state, evidence,
    assumptions and requirement results. It does not mean token-by-token model
    replay.
    """

    schema_version: Literal["kernel_replay_record.v1"] = "kernel_replay_record.v1"
    replay_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    version_ref: str = Field(min_length=1)
    boundary_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requirements: tuple[ReplayRequirement, ...] = Field(min_length=1)
    burden_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    assumptions_declared: bool
    assumption_refs: tuple[str, ...] = ()
    failures_declared: bool
    failed_requirement_ids: tuple[str, ...] = ()
    changes_declared: bool
    change_log_refs: tuple[str, ...] = ()
    created_at: datetime
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute: Literal[False] = False
    replay_digest: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator(
        "burden_refs",
        "evidence_refs",
        "assumption_refs",
        "failed_requirement_ids",
        "change_log_refs",
    )
    @classmethod
    def normalize_refs(cls, values: tuple[str, ...], info) -> tuple[str, ...]:
        return _sorted_unique(values, info.field_name)

    @model_validator(mode="after")
    def validate_replay(self) -> ReplayRecord:
        requirement_ids = tuple(item.requirement_id for item in self.requirements)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("replay requirement ids must be unique")
        non_pass = tuple(
            sorted(
                item.requirement_id
                for item in self.requirements
                if item.status != RequirementStatus.PASS
            )
        )
        if self.failures_declared and self.failed_requirement_ids != non_pass:
            raise ValueError("declared failed requirements do not match requirement statuses")
        if not self.failures_declared and self.failed_requirement_ids:
            raise ValueError("failed requirements cannot be listed when failures are undeclared")
        payload = self.model_dump(mode="python", exclude={"replay_digest"})
        if canonical_digest(payload) != self.replay_digest:
            raise ValueError("replay digest mismatch")
        return self


class ChangeTrigger(BaseModel):
    schema_version: Literal["kernel_replay_change_trigger.v1"] = (
        "kernel_replay_change_trigger.v1"
    )
    trigger_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    prior_replay_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    prior_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    new_state_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    material: bool
    changed_refs: tuple[str, ...] = Field(min_length=1)
    affected_requirement_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    observed_at: datetime
    trigger_digest: str
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("changed_refs", "affected_requirement_ids", "evidence_refs")
    @classmethod
    def normalize_refs(cls, values: tuple[str, ...], info) -> tuple[str, ...]:
        return _sorted_unique(values, info.field_name)

    @model_validator(mode="after")
    def validate_trigger(self) -> ChangeTrigger:
        if self.prior_state_digest == self.new_state_digest:
            raise ValueError("change trigger requires a changed state digest")
        if self.material and not self.affected_requirement_ids:
            raise ValueError("material change requires affected_requirement_ids")
        payload = self.model_dump(mode="python", exclude={"trigger_digest"})
        if canonical_digest(payload) != self.trigger_digest:
            raise ValueError("change trigger digest mismatch")
        return self


class ReplayAssessment(BaseModel):
    schema_version: Literal["kernel_replay_assessment.v1"] = (
        "kernel_replay_assessment.v1"
    )
    replay_id: str
    outcome: ReplayOutcome
    blocking_requirement_ids: tuple[str, ...] = ()
    invalidating_trigger_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    evaluated_at: datetime
    can_rely_on_replay: bool
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


def seal_burden_record(**values) -> BurdenRecord:
    payload = {
        "schema_version": "kernel_burden_record.v1",
        "quantity": None,
        "lower_bound": None,
        "upper_bound": None,
        "source_refs": (),
        "assumption_refs": (),
        "update_cadence": None,
        "authority_effect": "NO_AUTHORITY_CREATION",
        "can_issue_clearance": False,
        "can_execute": False,
        **values,
    }
    for field in ("evidence_refs", "source_refs", "assumption_refs"):
        payload[field] = _sorted_unique(tuple(payload[field]), field)
    return BurdenRecord(**payload, burden_digest=canonical_digest(payload))


def seal_replay_record(**values) -> ReplayRecord:
    payload = {
        "schema_version": "kernel_replay_record.v1",
        "burden_refs": (),
        "assumption_refs": (),
        "failed_requirement_ids": (),
        "change_log_refs": (),
        "assumptions_declared": True,
        "failures_declared": True,
        "changes_declared": True,
        "authority_effect": "NO_AUTHORITY_CREATION",
        "can_issue_clearance": False,
        "can_execute": False,
        **values,
    }
    requirements = tuple(
        item if isinstance(item, ReplayRequirement) else ReplayRequirement.model_validate(item)
        for item in payload["requirements"]
    )
    if payload["failures_declared"] and "failed_requirement_ids" not in values:
        payload["failed_requirement_ids"] = tuple(
            sorted(
                item.requirement_id
                for item in requirements
                if item.status != RequirementStatus.PASS
            )
        )
    for field in (
        "burden_refs",
        "evidence_refs",
        "assumption_refs",
        "failed_requirement_ids",
        "change_log_refs",
    ):
        payload[field] = _sorted_unique(tuple(payload[field]), field)
    payload["requirements"] = tuple(
        item.model_dump(mode="python") for item in requirements
    )
    return ReplayRecord(**payload, replay_digest=canonical_digest(payload))


def seal_change_trigger(**values) -> ChangeTrigger:
    payload = {
        "schema_version": "kernel_replay_change_trigger.v1",
        "affected_requirement_ids": (),
        "authority_effect": "NO_AUTHORITY_CREATION",
        "can_issue_clearance": False,
        "can_execute": False,
        **values,
    }
    for field in ("changed_refs", "affected_requirement_ids", "evidence_refs"):
        payload[field] = _sorted_unique(tuple(payload[field]), field)
    return ChangeTrigger(**payload, trigger_digest=canonical_digest(payload))


def assess_replay(
    record: ReplayRecord,
    *,
    change_triggers: tuple[ChangeTrigger, ...] = (),
    evaluated_at: datetime,
) -> ReplayAssessment:
    blocking = tuple(
        sorted(
            item.requirement_id
            for item in record.requirements
            if item.hard_requirement and item.status != RequirementStatus.PASS
        )
    )
    invalidating = tuple(
        sorted(
            trigger.trigger_id
            for trigger in change_triggers
            if trigger.material
            and trigger.tenant_id == record.tenant_id
            and trigger.subject_ref == record.subject_ref
            and trigger.prior_replay_digest == record.replay_digest
            and trigger.observed_at >= record.created_at
        )
    )

    reasons: list[str] = []
    if invalidating:
        reasons.append("MATERIAL_CHANGE_INVALIDATED_REPLAY")
    if blocking:
        reasons.append("HARD_REQUIREMENT_NOT_PASS")
    if not record.assumptions_declared:
        reasons.append("ASSUMPTIONS_UNDECLARED")
    if not record.failures_declared:
        reasons.append("FAILURE_LIST_UNDECLARED")
    if not record.changes_declared:
        reasons.append("CHANGE_LOG_UNDECLARED")

    if invalidating:
        outcome = ReplayOutcome.INVALIDATED
    elif reasons:
        outcome = ReplayOutcome.INCOMPLETE
    else:
        outcome = ReplayOutcome.COMPLETE

    return ReplayAssessment(
        replay_id=record.replay_id,
        outcome=outcome,
        blocking_requirement_ids=blocking,
        invalidating_trigger_ids=invalidating,
        reason_codes=tuple(sorted(reasons)),
        evaluated_at=evaluated_at,
        can_rely_on_replay=outcome == ReplayOutcome.COMPLETE,
    )
