from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import fsum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .memory_provider import canonical_digest


class IntegrityDecision(str, Enum):
    CONTINUE = "continue"
    REEVALUATE = "reevaluate"
    STEP_UP = "step_up"
    DENY = "deny"
    HALT = "halt"


class IntegrityTrigger(str, Enum):
    CHECKPOINT = "checkpoint"
    EXTERNAL_CHANGE = "external_change"
    TOOL_RESULT = "tool_result"
    OBJECTIVE_CHANGE = "objective_change"
    EVIDENCE_CHANGE = "evidence_change"
    AUTHORITY_CHANGE = "authority_change"
    POLICY_CHANGE = "policy_change"
    PRIVILEGE_CHANGE = "privilege_change"
    VERSION_CHANGE = "version_change"
    RISK_PHASE_CHANGE = "risk_phase_change"
    COMMIT_BOUNDARY = "commit_boundary"
    IRREVERSIBLE_BOUNDARY = "irreversible_boundary"
    TIMEOUT = "timeout"


CRITICAL_FIELDS = (
    "authority",
    "policy",
    "objective",
    "evidence",
    "tools",
    "environment",
)


class IntegrityProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str = Field(min_length=1)
    weights: Mapping[str, float]
    material_drift_threshold: float = Field(ge=0.0, le=1.0)
    baseline_validity_seconds: int = Field(gt=0)
    fail_closed: bool = True
    mandatory_boundary_revalidation: bool = True

    @model_validator(mode="after")
    def validate_weights(self) -> "IntegrityProfile":
        if not self.weights:
            raise ValueError("weights cannot be empty")
        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("weights must be non-negative")
        if sum(self.weights.values()) <= 0:
            raise ValueError("weights must have positive total")
        return self


class IntegrityState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    authority: str
    policy: str
    objective: str
    context: str
    evidence: str
    tools: str
    model_harness: str
    environment: str
    risk: str
    observed_at: datetime
    valid_until: datetime | None = None
    critical_validity: Mapping[str, bool] = {}

    @model_validator(mode="after")
    def validate_times(self) -> "IntegrityState":
        if self.valid_until is not None and self.valid_until < self.observed_at:
            raise ValueError("valid_until cannot precede observed_at")
        return self

    def payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return canonical_digest(self.payload())


class IntegrityBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    clearance_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    profile_id: str = Field(min_length=1)
    state: IntegrityState
    state_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    captured_at: datetime
    expires_at: datetime
    grants_authority: bool = False

    @model_validator(mode="after")
    def invariants(self) -> "IntegrityBaseline":
        if self.grants_authority:
            raise ValueError("integrity baseline cannot grant authority")
        if self.state_digest != self.state.digest():
            raise ValueError("baseline state digest mismatch")
        if self.expires_at <= self.captured_at:
            raise ValueError("baseline expiry must be after capture")
        return self


class IntegrityCheckpointReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    baseline_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    previous_checkpoint_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    trigger: IntegrityTrigger
    current_state_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    drift_score: float = Field(ge=0.0, le=1.0)
    changed_fields: tuple[str, ...]
    failed_invariants: tuple[str, ...]
    decision: IntegrityDecision
    revalidation_required: bool
    observed_at: datetime
    grants_authority: bool = False
    grants_clearance: bool = False

    @model_validator(mode="after")
    def separation(self) -> "IntegrityCheckpointReceipt":
        if self.grants_authority or self.grants_clearance:
            raise ValueError("integrity receipt cannot grant authority or clearance")
        if self.failed_invariants and self.decision is not IntegrityDecision.HALT:
            raise ValueError("critical invariant failure must HALT")
        return self

    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


@dataclass(frozen=True)
class IntegrityEvaluation:
    decision: IntegrityDecision
    drift_score: float
    changed_fields: tuple[str, ...]
    failed_invariants: tuple[str, ...]
    revalidation_required: bool


def capture_baseline(
    *,
    baseline_id: str,
    case_id: str,
    action_ref: str,
    clearance_digest: str,
    profile: IntegrityProfile,
    state: IntegrityState,
    captured_at: datetime | None = None,
) -> IntegrityBaseline:
    now = captured_at or datetime.now(timezone.utc)
    return IntegrityBaseline(
        baseline_id=baseline_id,
        case_id=case_id,
        action_ref=action_ref,
        clearance_digest=clearance_digest,
        profile_id=profile.profile_id,
        state=state,
        state_digest=state.digest(),
        captured_at=now,
        expires_at=now + timedelta(seconds=profile.baseline_validity_seconds),
    )


def _changed_fields(baseline: IntegrityState, current: IntegrityState) -> tuple[str, ...]:
    fields = (
        "authority",
        "policy",
        "objective",
        "context",
        "evidence",
        "tools",
        "model_harness",
        "environment",
        "risk",
    )
    return tuple(field for field in fields if getattr(baseline, field) != getattr(current, field))


def _failed_invariants(current: IntegrityState, now: datetime) -> tuple[str, ...]:
    failures = [name for name in CRITICAL_FIELDS if current.critical_validity.get(name) is False]
    if current.valid_until is not None and now > current.valid_until:
        failures.append("state_expired")
    return tuple(sorted(set(failures)))


def _drift_score(profile: IntegrityProfile, changed_fields: tuple[str, ...]) -> float:
    total = fsum(profile.weights.values())
    changed = fsum(profile.weights.get(field, 0.0) for field in changed_fields)
    return min(1.0, changed / total)


def evaluate_integrity(
    *,
    baseline: IntegrityBaseline,
    current: IntegrityState,
    profile: IntegrityProfile,
    trigger: IntegrityTrigger,
    now: datetime | None = None,
) -> IntegrityEvaluation:
    observed = now or datetime.now(timezone.utc)
    failures = _failed_invariants(current, observed)
    changed = _changed_fields(baseline.state, current)
    drift = _drift_score(profile, changed)

    if failures:
        return IntegrityEvaluation(IntegrityDecision.HALT, drift, changed, failures, True)

    baseline_expired = observed > baseline.expires_at
    mandatory_boundary = trigger in {
        IntegrityTrigger.COMMIT_BOUNDARY,
        IntegrityTrigger.IRREVERSIBLE_BOUNDARY,
        IntegrityTrigger.RISK_PHASE_CHANGE,
    }
    material = drift >= profile.material_drift_threshold
    revalidate = material or baseline_expired or (profile.mandatory_boundary_revalidation and mandatory_boundary)

    if revalidate:
        return IntegrityEvaluation(IntegrityDecision.REEVALUATE, drift, changed, (), True)
    return IntegrityEvaluation(IntegrityDecision.CONTINUE, drift, changed, (), False)


def emit_checkpoint_receipt(
    *,
    receipt_id: str,
    baseline: IntegrityBaseline,
    current: IntegrityState,
    profile: IntegrityProfile,
    trigger: IntegrityTrigger,
    previous_checkpoint_digest: str | None = None,
    observed_at: datetime | None = None,
) -> IntegrityCheckpointReceipt:
    now = observed_at or datetime.now(timezone.utc)
    evaluation = evaluate_integrity(
        baseline=baseline,
        current=current,
        profile=profile,
        trigger=trigger,
        now=now,
    )
    return IntegrityCheckpointReceipt(
        receipt_id=receipt_id,
        case_id=baseline.case_id,
        action_ref=baseline.action_ref,
        baseline_digest=canonical_digest(baseline.model_dump(mode="json")),
        previous_checkpoint_digest=previous_checkpoint_digest,
        trigger=trigger,
        current_state_digest=current.digest(),
        drift_score=evaluation.drift_score,
        changed_fields=evaluation.changed_fields,
        failed_invariants=evaluation.failed_invariants,
        decision=evaluation.decision,
        revalidation_required=evaluation.revalidation_required,
        observed_at=now,
    )


def verify_checkpoint_chain(receipts: tuple[IntegrityCheckpointReceipt, ...]) -> bool:
    previous: str | None = None
    for receipt in receipts:
        if receipt.previous_checkpoint_digest != previous:
            return False
        previous = receipt.digest()
    return True
