from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import utcnow


class IncidentPhase(str, Enum):
    OPEN = "OPEN"
    DIAGNOSING = "DIAGNOSING"
    REMEDIATION_PROPOSED = "REMEDIATION_PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTED = "EXECUTED"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class IncidentSeverity(str, Enum):
    UNKNOWN = "UNKNOWN"
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"
    SEV4 = "SEV4"


class IncidentPostState(str, Enum):
    MATCH = "MATCH"
    DIVERGED = "DIVERGED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class IncidentEvidenceRef(BaseModel):
    artifact_ref: str
    artifact_digest: str | None = None
    evidence_type: str

    model_config = ConfigDict(extra="forbid", frozen=True)


class IncidentState(BaseModel):
    """Deterministic operational state for one governed incident.

    Severity is independent of root cause. References are opaque evidence or
    execution artifacts owned by their source layers; Kernel only owns this
    lifecycle state.
    """

    incident_id: str
    tenant_id: str
    subject_ref: str
    phase: IncidentPhase = IncidentPhase.OPEN
    severity: IncidentSeverity = IncidentSeverity.UNKNOWN
    evidence_refs: tuple[IncidentEvidenceRef, ...] = Field(default_factory=tuple)
    remediation_ref: str | None = None
    authorization_ref: str | None = None
    execution_ref: str | None = None
    poststate_ref: str | None = None
    poststate_status: IncidentPostState | None = None
    root_cause_ref: str | None = None
    version: int = 1
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_phase_evidence(self) -> IncidentState:
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.phase in {
            IncidentPhase.REMEDIATION_PROPOSED,
            IncidentPhase.AUTHORIZED,
            IncidentPhase.EXECUTED,
            IncidentPhase.VERIFYING,
            IncidentPhase.RESOLVED,
        } and not self.remediation_ref:
            raise ValueError(f"{self.phase.value} requires remediation_ref")
        if self.phase in {
            IncidentPhase.AUTHORIZED,
            IncidentPhase.EXECUTED,
            IncidentPhase.VERIFYING,
            IncidentPhase.RESOLVED,
        } and not self.authorization_ref:
            raise ValueError(f"{self.phase.value} requires authorization_ref")
        if self.phase in {
            IncidentPhase.EXECUTED,
            IncidentPhase.VERIFYING,
            IncidentPhase.RESOLVED,
        } and not self.execution_ref:
            raise ValueError(f"{self.phase.value} requires execution_ref")
        if self.phase is IncidentPhase.RESOLVED:
            if not self.poststate_ref:
                raise ValueError("RESOLVED requires poststate_ref")
            if self.poststate_status is not IncidentPostState.MATCH:
                raise ValueError("RESOLVED requires matching verified post-state")
        return self


_ALLOWED_TRANSITIONS: dict[IncidentPhase, frozenset[IncidentPhase]] = {
    IncidentPhase.OPEN: frozenset({IncidentPhase.DIAGNOSING, IncidentPhase.ESCALATED}),
    IncidentPhase.DIAGNOSING: frozenset(
        {IncidentPhase.REMEDIATION_PROPOSED, IncidentPhase.ESCALATED}
    ),
    IncidentPhase.REMEDIATION_PROPOSED: frozenset(
        {IncidentPhase.AUTHORIZED, IncidentPhase.DIAGNOSING, IncidentPhase.ESCALATED}
    ),
    IncidentPhase.AUTHORIZED: frozenset(
        {IncidentPhase.EXECUTED, IncidentPhase.DIAGNOSING, IncidentPhase.ESCALATED}
    ),
    IncidentPhase.EXECUTED: frozenset(
        {IncidentPhase.VERIFYING, IncidentPhase.ESCALATED}
    ),
    IncidentPhase.VERIFYING: frozenset(
        {IncidentPhase.RESOLVED, IncidentPhase.DIAGNOSING, IncidentPhase.ESCALATED}
    ),
    IncidentPhase.ESCALATED: frozenset(
        {IncidentPhase.DIAGNOSING, IncidentPhase.REMEDIATION_PROPOSED}
    ),
    IncidentPhase.RESOLVED: frozenset(),
}


def transition_incident(
    state: IncidentState,
    next_phase: IncidentPhase,
    *,
    severity: IncidentSeverity | None = None,
    evidence_refs: tuple[IncidentEvidenceRef, ...] | None = None,
    remediation_ref: str | None = None,
    authorization_ref: str | None = None,
    execution_ref: str | None = None,
    poststate_ref: str | None = None,
    poststate_status: IncidentPostState | None = None,
    root_cause_ref: str | None = None,
    updated_at: datetime | None = None,
) -> IncidentState:
    """Return the next immutable incident state or fail closed on illegal flow."""

    if next_phase not in _ALLOWED_TRANSITIONS[state.phase]:
        raise ValueError(
            f"illegal incident transition {state.phase.value} -> {next_phase.value}"
        )
    update = {
        "phase": next_phase,
        "severity": severity if severity is not None else state.severity,
        "evidence_refs": evidence_refs if evidence_refs is not None else state.evidence_refs,
        "remediation_ref": remediation_ref if remediation_ref is not None else state.remediation_ref,
        "authorization_ref": authorization_ref if authorization_ref is not None else state.authorization_ref,
        "execution_ref": execution_ref if execution_ref is not None else state.execution_ref,
        "poststate_ref": poststate_ref if poststate_ref is not None else state.poststate_ref,
        "poststate_status": poststate_status if poststate_status is not None else state.poststate_status,
        "root_cause_ref": root_cause_ref if root_cause_ref is not None else state.root_cause_ref,
        "version": state.version + 1,
        "updated_at": updated_at or utcnow(),
    }
    return IncidentState.model_validate({**state.model_dump(), **update})
