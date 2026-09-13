"""Canonical pre-commit Operational Continuity revalidation orchestration.

The request binds the original decision basis, the validated source baseline,
complete current source observations and current authoritative fingerprints.
It produces evidence for VAIG and then calls the existing REHT-owned evaluator.
It never creates a GovernanceClearance or executes an action.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from src.valo_platform.action_envelope.models import ClearanceState
from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityContractError,
    ContinuityDecision,
    ContinuityImpactAssessment,
    ContinuityIntegrityStatus,
    ContinuitySeverity,
    ContinuityTrigger,
    ContinuityTriggerKind,
    canonical_digest,
    canonical_fingerprint_digest,
    require_same_binding,
)
from src.valo_platform.decision_governance.continuity_evaluator import (
    evaluate_operational_continuity,
)

from .source_adapters import ContinuitySourceBundle, SourceObservationError
from .source_baselines import ContinuitySourceBaseline


_REQUIRED_FINGERPRINT_NAMES = (
    "authority",
    "policy",
    "context",
    "state",
    "evidence",
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ContinuityContractError("revalidation times must be timezone-aware")
    return value.astimezone(timezone.utc)


def _normalize_refs(values: Iterable[str] | None) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in (values or ()) if str(value)}))


class ContinuityCurrentFingerprints(BaseModel):
    """Exact current fingerprints consumed by the commit-boundary evaluator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    authority: str
    policy: str
    context: str
    state: str
    evidence: str
    fingerprint_digest: str = ""

    @model_validator(mode="after")
    def _validate_fingerprints(self) -> "ContinuityCurrentFingerprints":
        values = self.as_mapping()
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ContinuityContractError(
                "current fingerprints are missing: " + ",".join(missing)
            )
        expected = canonical_fingerprint_digest(values)
        if self.fingerprint_digest and self.fingerprint_digest != expected:
            raise ContinuityContractError(
                "fingerprint_digest does not match current fingerprints"
            )
        if not self.fingerprint_digest:
            object.__setattr__(self, "fingerprint_digest", expected)
        return self

    def as_mapping(self) -> dict[str, str]:
        return {
            "authority": self.authority,
            "policy": self.policy,
            "context": self.context,
            "state": self.state,
            "evidence": self.evidence,
        }

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, str | None],
    ) -> "ContinuityCurrentFingerprints":
        unknown = sorted(set(values) - set(_REQUIRED_FINGERPRINT_NAMES))
        if unknown:
            raise ContinuityContractError(
                "unknown canonical current fingerprints: " + ",".join(unknown)
            )
        missing = [name for name in _REQUIRED_FINGERPRINT_NAMES if not values.get(name)]
        if missing:
            raise ContinuityContractError(
                "current fingerprints are missing: " + ",".join(missing)
            )
        return cls(**{name: str(values[name]) for name in _REQUIRED_FINGERPRINT_NAMES})


class ContinuityRevalidationRequest(BaseModel):
    """Evidence-bound request submitted to VAIG before REHT re-evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str
    requester_ref: str
    basis: ContinuityBasisSnapshot
    source_baseline: ContinuitySourceBaseline
    source_bundle: ContinuitySourceBundle
    current_fingerprints: ContinuityCurrentFingerprints
    triggers: tuple[ContinuityTrigger, ...]
    evidence_refs: tuple[str, ...]
    requested_at: datetime
    request_digest: str = ""

    @field_validator("triggers", mode="before")
    @classmethod
    def _sort_triggers(
        cls,
        value: Sequence[ContinuityTrigger],
    ) -> tuple[ContinuityTrigger, ...]:
        return tuple(sorted(tuple(value), key=lambda trigger: trigger.trigger_id))

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _sort_evidence_refs(cls, value: Iterable[str] | None) -> tuple[str, ...]:
        return _normalize_refs(value)

    @model_validator(mode="after")
    def _validate_request(self) -> "ContinuityRevalidationRequest":
        _as_utc(self.requested_at)
        if not self.request_id or not self.requester_ref:
            raise ContinuityContractError(
                "revalidation request requires request and requester identity"
            )
        _validate_request_binding(
            self.basis,
            self.source_baseline,
            self.source_bundle,
        )
        _validate_source_coverage(self.source_baseline, self.source_bundle)
        if self.source_baseline.captured_at > self.basis.observed_at:
            raise ContinuityContractError(
                "source baseline cannot be newer than the decision basis"
            )
        if self.source_bundle.observed_at < self.source_baseline.captured_at:
            raise ContinuityContractError(
                "source observations cannot predate the source baseline"
            )
        if self.source_bundle.observed_at > self.requested_at:
            raise ContinuityContractError(
                "source observations cannot be newer than the request"
            )
        if not self.triggers:
            raise ContinuityContractError(
                "revalidation request requires drift or checkpoint evidence"
            )
        expected_trigger_refs = {
            trigger.trigger_id for trigger in self.source_bundle.triggers
        }
        supplied_trigger_refs = {trigger.trigger_id for trigger in self.triggers}
        if expected_trigger_refs:
            if supplied_trigger_refs != expected_trigger_refs:
                raise ContinuityContractError(
                    "revalidation trigger set does not match source bundle"
                )
        else:
            if len(self.triggers) != 1:
                raise ContinuityContractError(
                    "stable revalidation requires one checkpoint trigger"
                )
            checkpoint = self.triggers[0]
            if checkpoint.trigger_kind != ContinuityTriggerKind.REVALIDATION_CHECKPOINT:
                raise ContinuityContractError(
                    "stable revalidation requires REVALIDATION_CHECKPOINT"
                )
        binding = _basis_binding(self.basis)
        for trigger in self.triggers:
            actual = (
                trigger.tenant_id,
                trigger.action_case_id,
                trigger.action_case_hash,
                trigger.clearance_ref,
            )
            if actual != binding:
                raise ContinuityContractError(
                    "revalidation trigger binding mismatch"
                )
        required_evidence = set(self.source_bundle.evidence_refs)
        for entry in self.source_baseline.entries:
            required_evidence.update(entry.evidence_refs)
        if not required_evidence.issubset(set(self.evidence_refs)):
            raise ContinuityContractError(
                "revalidation request omits source evidence references"
            )
        expected_digest = canonical_digest(
            self.model_dump(mode="json", exclude={"request_digest"})
        )
        if self.request_digest and self.request_digest != expected_digest:
            raise ContinuityContractError(
                "request_digest does not match revalidation request"
            )
        if not self.request_digest:
            object.__setattr__(self, "request_digest", expected_digest)
        return self

    @property
    def evidence_ref(self) -> str:
        return f"continuity-revalidation-request:{self.request_digest}"


class ContinuityRevalidationResult(BaseModel):
    """Bound output of VAIG assessment followed by REHT continuity decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_ref: str
    request_digest: str
    assessment_ref: str
    assessment_digest: str
    decision: ContinuityDecision
    completed_at: datetime
    result_digest: str = ""

    @model_validator(mode="after")
    def _validate_result(self) -> "ContinuityRevalidationResult":
        _as_utc(self.completed_at)
        expected = canonical_digest(
            self.model_dump(mode="json", exclude={"result_digest"})
        )
        if self.result_digest and self.result_digest != expected:
            raise ContinuityContractError(
                "result_digest does not match revalidation result"
            )
        if not self.result_digest:
            object.__setattr__(self, "result_digest", expected)
        return self


def _basis_binding(basis: ContinuityBasisSnapshot) -> tuple[str, str, str, str]:
    return (
        basis.tenant_id,
        basis.action_case_id,
        basis.action_case_hash,
        basis.clearance_ref,
    )


def _source_binding(value: ContinuitySourceBaseline | ContinuitySourceBundle) -> tuple[str, str, str, str]:
    binding = value.binding
    return (
        binding.tenant_id,
        binding.action_case_id,
        binding.action_case_hash,
        binding.clearance_ref,
    )


def _validate_request_binding(
    basis: ContinuityBasisSnapshot,
    baseline: ContinuitySourceBaseline,
    bundle: ContinuitySourceBundle,
) -> None:
    expected = _basis_binding(basis)
    if _source_binding(baseline) != expected:
        raise ContinuityContractError(
            "source baseline does not match decision basis binding"
        )
    if _source_binding(bundle) != expected:
        raise ContinuityContractError(
            "source bundle does not match decision basis binding"
        )
    if baseline.binding.observer_ref != bundle.binding.observer_ref:
        raise ContinuityContractError(
            "source baseline and bundle observer binding mismatch"
        )


def _validate_source_coverage(
    baseline: ContinuitySourceBaseline,
    bundle: ContinuitySourceBundle,
) -> None:
    baseline_by_key = {
        (entry.domain.value, entry.source_ref): entry for entry in baseline.entries
    }
    observations_by_key = {
        (observation.domain.value, observation.source_ref): observation
        for observation in bundle.observations
    }
    if set(baseline_by_key) != set(observations_by_key):
        missing = sorted(set(baseline_by_key) - set(observations_by_key))
        extra = sorted(set(observations_by_key) - set(baseline_by_key))
        raise ContinuityContractError(
            f"incomplete source revalidation coverage; missing={missing}; extra={extra}"
        )
    for key, entry in baseline_by_key.items():
        observation = observations_by_key[key]
        if observation.expected_fingerprint != entry.fingerprint:
            raise ContinuityContractError(
                f"source observation is not bound to baseline fingerprint: {key}"
            )


def _checkpoint_integrity(bundle: ContinuitySourceBundle) -> ContinuityIntegrityStatus:
    statuses: list[ContinuityIntegrityStatus] = []
    for observation in bundle.observations:
        try:
            statuses.append(ContinuityIntegrityStatus(observation.integrity_status))
        except ValueError:
            statuses.append(ContinuityIntegrityStatus.UNKNOWN)
    if any(status == ContinuityIntegrityStatus.FAILED for status in statuses):
        return ContinuityIntegrityStatus.FAILED
    if any(status == ContinuityIntegrityStatus.UNKNOWN for status in statuses):
        return ContinuityIntegrityStatus.UNKNOWN
    if any(status == ContinuityIntegrityStatus.UNVERIFIED for status in statuses):
        return ContinuityIntegrityStatus.UNVERIFIED
    return ContinuityIntegrityStatus.VERIFIED


def _source_state_digest(
    baseline: ContinuitySourceBaseline,
    bundle: ContinuitySourceBundle,
    *,
    current: bool,
) -> str:
    baseline_by_key = {
        (entry.domain.value, entry.source_ref): entry for entry in baseline.entries
    }
    values: dict[str, str] = {}
    for observation in bundle.observations:
        key = (observation.domain.value, observation.source_ref)
        values[f"{key[0]}:{key[1]}"] = (
            observation.current_fingerprint
            if current
            else baseline_by_key[key].fingerprint
        )
    return canonical_digest(values)


def _build_checkpoint_trigger(
    *,
    basis: ContinuityBasisSnapshot,
    baseline: ContinuitySourceBaseline,
    bundle: ContinuitySourceBundle,
) -> ContinuityTrigger:
    previous = _source_state_digest(baseline, bundle, current=False)
    current = _source_state_digest(baseline, bundle, current=True)
    if previous != current:
        raise ContinuityContractError(
            "checkpoint trigger cannot represent source drift"
        )
    integrity = _checkpoint_integrity(bundle)
    evidence_refs = set(bundle.evidence_refs)
    for entry in baseline.entries:
        evidence_refs.update(entry.evidence_refs)
    return ContinuityTrigger(
        trigger_id=(
            f"revalidation-checkpoint:{basis.action_case_id}:"
            f"{bundle.bundle_digest}"
        ),
        tenant_id=basis.tenant_id,
        action_case_id=basis.action_case_id,
        action_case_hash=basis.action_case_hash,
        clearance_ref=basis.clearance_ref,
        trigger_kind=ContinuityTriggerKind.REVALIDATION_CHECKPOINT,
        severity=ContinuitySeverity.INFO,
        source_ref=f"continuity-source-bundle:{bundle.bundle_digest}",
        observer_ref=bundle.binding.observer_ref,
        observed_at=bundle.observed_at,
        previous_fingerprint=previous,
        current_fingerprint=current,
        changed_fields=(),
        source_evidence_refs=tuple(sorted(evidence_refs)),
        confidence=1.0,
        freshness=(
            1.0 if integrity == ContinuityIntegrityStatus.VERIFIED else 0.0
        ),
        integrity_status=integrity,
    )


def build_revalidation_request(
    *,
    request_id: str,
    requester_ref: str,
    basis: ContinuityBasisSnapshot,
    source_baseline: ContinuitySourceBaseline,
    source_bundle: ContinuitySourceBundle,
    current_fingerprints: Mapping[str, str | None] | ContinuityCurrentFingerprints,
    requested_at: datetime,
) -> ContinuityRevalidationRequest:
    """Build a complete request, adding a checkpoint only when no source drift exists."""

    _validate_request_binding(basis, source_baseline, source_bundle)
    _validate_source_coverage(source_baseline, source_bundle)
    fingerprints = (
        current_fingerprints
        if isinstance(current_fingerprints, ContinuityCurrentFingerprints)
        else ContinuityCurrentFingerprints.from_mapping(current_fingerprints)
    )
    triggers = source_bundle.triggers
    if not triggers:
        triggers = (
            _build_checkpoint_trigger(
                basis=basis,
                baseline=source_baseline,
                bundle=source_bundle,
            ),
        )
    evidence_refs = set(source_bundle.evidence_refs)
    for entry in source_baseline.entries:
        evidence_refs.update(entry.evidence_refs)
    return ContinuityRevalidationRequest(
        request_id=request_id,
        requester_ref=requester_ref,
        basis=basis,
        source_baseline=source_baseline,
        source_bundle=source_bundle,
        current_fingerprints=fingerprints,
        triggers=triggers,
        evidence_refs=tuple(sorted(evidence_refs)),
        requested_at=_as_utc(requested_at),
    )


def validate_vaig_assessment(
    request: ContinuityRevalidationRequest,
    assessment: ContinuityImpactAssessment,
) -> None:
    """Require VAIG output to bind the exact request, triggers and evidence."""

    require_same_binding(request.basis, request.triggers, assessment)
    if set(assessment.trigger_refs) != {
        trigger.trigger_id for trigger in request.triggers
    }:
        raise ContinuityContractError(
            "VAIG assessment trigger set does not match revalidation request"
        )
    if request.evidence_ref not in set(assessment.evidence_refs):
        raise ContinuityContractError(
            "VAIG assessment does not reference the revalidation request"
        )
    if assessment.assessed_at < request.requested_at:
        raise ContinuityContractError(
            "VAIG assessment cannot predate the revalidation request"
        )


def evaluate_revalidation_request(
    *,
    request: ContinuityRevalidationRequest,
    assessment: ContinuityImpactAssessment,
    clearance_state: ClearanceState,
    now: datetime,
    decider_ref: str,
    decision_authority_ref: str,
    decision_ttl: timedelta = timedelta(minutes=5),
) -> ContinuityRevalidationResult:
    """Validate VAIG evidence and invoke the canonical REHT continuity evaluator."""

    now = _as_utc(now)
    validate_vaig_assessment(request, assessment)
    decision = evaluate_operational_continuity(
        basis=request.basis,
        triggers=request.triggers,
        assessment=assessment,
        current_fingerprints=request.current_fingerprints.as_mapping(),
        clearance_state=clearance_state,
        now=now,
        decider_ref=decider_ref,
        decision_authority_ref=decision_authority_ref,
        decision_ttl=decision_ttl,
    )
    return ContinuityRevalidationResult(
        request_ref=request.evidence_ref,
        request_digest=request.request_digest,
        assessment_ref=assessment.assessment_id,
        assessment_digest=assessment.assessment_digest,
        decision=decision,
        completed_at=now,
    )


__all__ = [
    "ContinuityCurrentFingerprints",
    "ContinuityRevalidationRequest",
    "ContinuityRevalidationResult",
    "build_revalidation_request",
    "evaluate_revalidation_request",
    "validate_vaig_assessment",
]
