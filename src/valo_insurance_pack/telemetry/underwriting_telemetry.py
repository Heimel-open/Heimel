from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..contracts.assurance_profile import ConsequenceClass
from ..contracts.evaluation import AssuranceResult, CommitAssuranceEvaluationV1
from ..contracts.source_evidence import SourceAssuranceEvidenceV1
from ..utils.crypto import iso_format, utcnow


class UnderwritingTelemetrySnapshot(BaseModel):
    """Deterministic aggregation of technical assurance signals.

    CRITICAL INVARIANT: No premium pricing, no actuarial decisions, and no risk
    underwriting decisions are made in VALO. This telemetry provides pure technical
    observability for external carriers and underwriters.
    """

    total_evaluations: int
    clearance_rate: float
    step_up_rate: float
    defer_rate: float
    deny_rate: float
    halt_rate: float
    missing_evidence_rate: float
    stale_evidence_rate: float
    revoked_evidence_rate: float
    source_assurance_strength: dict[str, dict[str, int]] = Field(default_factory=dict)
    control_effectiveness_score: float
    consequence_exposure: dict[str, int] = Field(default_factory=dict)
    profile_version_distribution: dict[str, int] = Field(default_factory=dict)
    incidents_correlated_to_assurance_state: list[dict[str, Any]] = Field(
        default_factory=list
    )
    generated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(extra="forbid", frozen=True)


class UnderwritingTelemetryCollector:
    """Thread-safe collector and aggregator of machine-underwriting signals."""

    def __init__(self) -> None:
        self._evaluations: list[CommitAssuranceEvaluationV1] = []
        self._source_evidence_records: list[tuple[str, SourceAssuranceEvidenceV1]] = []
        self._incidents: list[dict[str, Any]] = []

    def record_evaluation(
        self,
        evaluation: CommitAssuranceEvaluationV1,
        *,
        source_evidences: list[SourceAssuranceEvidenceV1] | None = None,
    ) -> None:
        """Record a commit-time assurance evaluation and associated evidence."""
        self._evaluations.append(evaluation)
        if source_evidences:
            for ev in source_evidences:
                self._source_evidence_records.append((evaluation.evaluation_id, ev))

    def record_incident(
        self,
        *,
        incident_id: str,
        action_ref: str,
        evaluation_id: str | None = None,
        severity: str = "MEDIUM",
        details: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        """Record an incident or anomaly linked to an action / assurance evaluation."""
        self._incidents.append(
            {
                "incident_id": incident_id,
                "action_ref": action_ref,
                "evaluation_id": evaluation_id,
                "severity": severity,
                "details": details or {},
                "occurred_at": iso_format(occurred_at or utcnow()),
            }
        )

    def snapshot(self, now: datetime | None = None) -> UnderwritingTelemetrySnapshot:
        """Compute aggregate underwriting metrics across all recorded evaluations."""
        now = now or utcnow()
        total = len(self._evaluations)
        if total == 0:
            return UnderwritingTelemetrySnapshot(
                total_evaluations=0,
                clearance_rate=0.0,
                step_up_rate=0.0,
                defer_rate=0.0,
                deny_rate=0.0,
                halt_rate=0.0,
                missing_evidence_rate=0.0,
                stale_evidence_rate=0.0,
                revoked_evidence_rate=0.0,
                source_assurance_strength={},
                control_effectiveness_score=1.0,
                consequence_exposure={
                    ConsequenceClass.LOW.value: 0,
                    ConsequenceClass.MEDIUM.value: 0,
                    ConsequenceClass.HIGH.value: 0,
                    ConsequenceClass.CRITICAL.value: 0,
                },
                profile_version_distribution={},
                incidents_correlated_to_assurance_state=list(self._incidents),
                generated_at=now,
            )

        satisfied_count = sum(
            1
            for e in self._evaluations
            if e.assurance_result == AssuranceResult.SATISFIED
        )
        step_up_count = sum(
            1
            for e in self._evaluations
            if e.assurance_result == AssuranceResult.STEP_UP_REQUIRED
        )
        defer_count = sum(
            1
            for e in self._evaluations
            if e.assurance_result == AssuranceResult.DEFERRED
        )
        deny_count = sum(
            1 for e in self._evaluations if e.assurance_result == AssuranceResult.UNMET
        )
        halt_count = sum(
            1 for e in self._evaluations if e.assurance_result == AssuranceResult.HALTED
        )

        missing_evidence_count = sum(
            1
            for e in self._evaluations
            if any("missing_required_source" in u for u in e.unmet_requirements)
        )
        stale_evidence_count = sum(
            1
            for e in self._evaluations
            if any(
                "stale_evidence" in u or "expired_evidence" in u
                for u in e.unmet_requirements
            )
        )
        revoked_evidence_count = sum(
            1
            for e in self._evaluations
            if any(
                "revoked_or_unverified_evidence" in u
                for u in e.unmet_requirements
            )
        )

        consequence_exposure: dict[str, int] = defaultdict(int)
        profile_distribution: dict[str, int] = defaultdict(int)

        for e in self._evaluations:
            consequence_exposure[e.consequence_class] += 1
            profile_distribution[e.profile_ref] += 1

        # Source assurance strength distribution
        source_strength: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for _, ev in self._source_evidence_records:
            strength = ev.provenance.get("assurance_level") or ev.attestation_type
            source_strength[ev.source_id][strength] += 1

        # Control effectiveness: fraction of non-conforming evaluation attempts that were successfully blocked
        flawed_attempts = total - satisfied_count
        blocked_attempts = step_up_count + defer_count + deny_count + halt_count
        control_effectiveness = (
            (blocked_attempts / flawed_attempts) if flawed_attempts > 0 else 1.0
        )

        return UnderwritingTelemetrySnapshot(
            total_evaluations=total,
            clearance_rate=round(satisfied_count / total, 4),
            step_up_rate=round(step_up_count / total, 4),
            defer_rate=round(defer_count / total, 4),
            deny_rate=round(deny_count / total, 4),
            halt_rate=round(halt_count / total, 4),
            missing_evidence_rate=round(missing_evidence_count / total, 4),
            stale_evidence_rate=round(stale_evidence_count / total, 4),
            revoked_evidence_rate=round(revoked_evidence_count / total, 4),
            source_assurance_strength={k: dict(v) for k, v in source_strength.items()},
            control_effectiveness_score=round(control_effectiveness, 4),
            consequence_exposure=dict(consequence_exposure),
            profile_version_distribution=dict(profile_distribution),
            incidents_correlated_to_assurance_state=list(self._incidents),
            generated_at=now,
        )
