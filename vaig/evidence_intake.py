"""Exact upstream evidence intake for VAIG.

Verification Factory and Harness own verification. VAIG only validates that the
exact, versioned artifacts required for one intended use are present, current,
compatible and unresolved-free enough for runtime evaluation.

A digest proves binding, not truth. This module never grants execution authority.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ClaimDisposition(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONFLICTED = "CONFLICTED"
    UNSUPPORTED = "UNSUPPORTED"
    STALE = "STALE"
    UNTRACEABLE = "UNTRACEABLE"
    UNKNOWN = "UNKNOWN"


class ClaimMateriality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CriterionKind(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    POLICY = "POLICY"
    SEMANTIC = "SEMANTIC"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class EvidenceIntakeState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    VALID = "VALID"
    CONSTRAINED = "CONSTRAINED"
    MISSING = "MISSING"
    MISMATCHED = "MISMATCHED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"
    USE_PROHIBITED = "USE_PROHIBITED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTED = "CONFLICTED"


@dataclass(frozen=True)
class VersionedArtifactRef:
    """Narrow mirror of Verification Factory VersionedRef."""

    artifact_id: str
    version: str
    reference: str
    digest: str

    def __post_init__(self) -> None:
        for name in ("artifact_id", "version", "reference"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        _require_digest(self.digest, "digest")

    def binding_key(self) -> Tuple[str, str, str]:
        return self.artifact_id, self.version, self.digest


@dataclass(frozen=True)
class ClaimAdmissibilityBinding:
    """Exact claim-admissibility result produced upstream."""

    admissibility_ref: VersionedArtifactRef
    case_id: str
    claim_id: str
    disposition: ClaimDisposition
    materiality: ClaimMateriality
    permissible_uses: Tuple[str, ...] = ()
    prohibited_uses: Tuple[str, ...] = ()
    unresolved_conflicts: Tuple[str, ...] = ()
    limitations: Tuple[str, ...] = ()
    policy_ref: Optional[VersionedArtifactRef] = None
    decided_at: Optional[datetime] = None
    invalidated_at: Optional[datetime] = None
    invalidation_ref: Optional[VersionedArtifactRef] = None

    def __post_init__(self) -> None:
        if not self.case_id or not self.claim_id:
            raise ValueError("case_id and claim_id are required")
        _require_aware(self.decided_at, "decided_at")
        _require_aware(self.invalidated_at, "invalidated_at")
        if self.invalidated_at and not self.invalidation_ref:
            raise ValueError("invalidated claim admissibility requires invalidation_ref")


@dataclass(frozen=True)
class EvidencePackageBinding:
    """Narrow runtime binding to an exact upstream EvidencePackage."""

    package_id: str
    case_id: str
    package_version: str
    package_digest: str
    admissibility_refs: Tuple[VersionedArtifactRef, ...]
    unresolved_questions: Tuple[str, ...] = ()
    contradictions: Tuple[str, ...] = ()
    permissible_uses: Tuple[str, ...] = ()
    prohibited_uses: Tuple[str, ...] = ()
    created_at: Optional[datetime] = None
    invalidated_at: Optional[datetime] = None
    invalidation_ref: Optional[VersionedArtifactRef] = None

    def __post_init__(self) -> None:
        for name in ("package_id", "case_id", "package_version"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        _require_digest(self.package_digest, "package_digest")
        _require_aware(self.created_at, "created_at")
        _require_aware(self.invalidated_at, "invalidated_at")
        if self.invalidated_at and not self.invalidation_ref:
            raise ValueError("invalidated EvidencePackage requires invalidation_ref")
        keys = [ref.binding_key() for ref in self.admissibility_refs]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate admissibility reference")

    @property
    def ref(self) -> VersionedArtifactRef:
        return VersionedArtifactRef(
            artifact_id=self.package_id,
            version=self.package_version,
            reference=f"evidence-package:{self.package_id}:{self.package_version}",
            digest=self.package_digest,
        )


@dataclass(frozen=True)
class CriterionVerificationBinding:
    """Exact criterion result extracted from a NodeVerificationBundle."""

    criterion_id: str
    binding_fingerprint: str
    kind: CriterionKind
    blocking: bool
    status: str
    verifier_id: Optional[str] = None
    verifier_version: Optional[str] = None
    evidence_digest: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.criterion_id or not self.status:
            raise ValueError("criterion_id and status are required")
        _require_digest(self.binding_fingerprint, "binding_fingerprint")
        if self.evidence_digest is not None:
            _require_digest(self.evidence_digest, "evidence_digest")

    @property
    def succeeded(self) -> bool:
        return self.status.upper() == "SUCCEEDED"


@dataclass(frozen=True)
class WorkflowVerificationBinding:
    """Narrow mirror of an exact Harness NodeVerificationBundle."""

    bundle_fingerprint: str
    workflow_fingerprint: str
    node_fingerprint: str
    workflow_state_fingerprint: str
    accepted: bool
    criteria: Tuple[CriterionVerificationBinding, ...] = ()
    unresolved_criteria: Tuple[str, ...] = ()
    invalidated_at: Optional[datetime] = None
    invalidation_ref: Optional[VersionedArtifactRef] = None

    def __post_init__(self) -> None:
        for name in (
            "bundle_fingerprint",
            "workflow_fingerprint",
            "node_fingerprint",
            "workflow_state_fingerprint",
        ):
            _require_digest(getattr(self, name), name)
        _require_aware(self.invalidated_at, "invalidated_at")
        if self.invalidated_at and not self.invalidation_ref:
            raise ValueError("invalidated workflow verification requires invalidation_ref")
        ids = [item.criterion_id for item in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate workflow criterion")


@dataclass(frozen=True)
class EvidenceIntakeRequest:
    """Exact artifact and intended-use binding required by one VAIG evaluation."""

    required: bool
    intended_use: str
    expected_case_id: Optional[str] = None
    expected_package_id: Optional[str] = None
    expected_package_version: Optional[str] = None
    expected_package_digest: Optional[str] = None
    max_package_age_seconds: Optional[int] = None
    workflow_required: bool = False
    expected_workflow_fingerprint: Optional[str] = None
    expected_node_fingerprint: Optional[str] = None
    expected_workflow_state_fingerprint: Optional[str] = None

    def __post_init__(self) -> None:
        if self.required and not self.intended_use.strip():
            raise ValueError("required evidence intake requires intended_use")
        if self.max_package_age_seconds is not None and self.max_package_age_seconds < 0:
            raise ValueError("max_package_age_seconds cannot be negative")
        for name in (
            "expected_package_digest",
            "expected_workflow_fingerprint",
            "expected_node_fingerprint",
            "expected_workflow_state_fingerprint",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_digest(value, name)


@dataclass(frozen=True)
class EvidenceIntakePolicy:
    """VAIG policy for consuming, never rewriting, upstream findings."""

    version: str = "evidence-intake-v1"
    require_supported_for: Tuple[ClaimMateriality, ...] = (
        ClaimMateriality.MEDIUM,
        ClaimMateriality.HIGH,
        ClaimMateriality.CRITICAL,
    )
    low_materiality_allowed: Tuple[ClaimDisposition, ...] = (
        ClaimDisposition.SUPPORTED,
        ClaimDisposition.PARTIALLY_SUPPORTED,
    )
    block_on_package_questions: bool = True
    block_on_package_contradictions: bool = True


@dataclass(frozen=True)
class EvidenceIntakeAssessment:
    state: EvidenceIntakeState
    policy_version: str
    package_ref: Optional[VersionedArtifactRef] = None
    intended_use: str = ""
    evaluated_claim_refs: Tuple[str, ...] = ()
    blocking_claim_refs: Tuple[str, ...] = ()
    constrained_claim_refs: Tuple[str, ...] = ()
    workflow_bundle_fingerprint: Optional[str] = None
    blocking_reasons: Tuple[str, ...] = ()
    constraints: Tuple[str, ...] = ()

    @property
    def blocks_consequential_action(self) -> bool:
        return self.state not in {
            EvidenceIntakeState.NOT_REQUIRED,
            EvidenceIntakeState.VALID,
        }

    @property
    def requires_human_review(self) -> bool:
        return self.blocks_consequential_action

    @property
    def evidence_valid(self) -> bool:
        """Legacy compatibility signal derived from typed intake only."""

        return self.state in {
            EvidenceIntakeState.NOT_REQUIRED,
            EvidenceIntakeState.VALID,
        }

    @property
    def claims_substantiated(self) -> bool:
        """Legacy compatibility signal; never accepted as caller truth."""

        return (
            self.evidence_valid
            and not self.blocking_claim_refs
            and not self.constrained_claim_refs
        )

    def to_audit_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["state"] = self.state.value
        payload["execution_authority"] = False
        payload["requires_reht_clearance"] = True
        return payload


def assess_evidence_intake(
    request: EvidenceIntakeRequest,
    package: Optional[EvidencePackageBinding] = None,
    admissibility_records: Sequence[ClaimAdmissibilityBinding] = (),
    workflow_verification: Optional[WorkflowVerificationBinding] = None,
    policy: Optional[EvidenceIntakePolicy] = None,
    now: Optional[datetime] = None,
) -> EvidenceIntakeAssessment:
    """Validate exact upstream artifacts for one intended use."""

    selected = policy or EvidenceIntakePolicy()
    current_time = now or datetime.now(timezone.utc)
    _require_aware(current_time, "now")

    if (
        not request.required
        and package is None
        and not admissibility_records
        and workflow_verification is None
    ):
        return EvidenceIntakeAssessment(
            state=EvidenceIntakeState.NOT_REQUIRED,
            policy_version=selected.version,
            intended_use=request.intended_use,
        )

    if package is None:
        return _assessment(
            EvidenceIntakeState.MISSING,
            selected,
            request,
            reasons=("Required EvidencePackage is missing.",),
        )

    package_ref = package.ref
    mismatches = _package_mismatches(request, package)
    if mismatches:
        return _assessment(
            EvidenceIntakeState.MISMATCHED,
            selected,
            request,
            package_ref=package_ref,
            reasons=mismatches,
        )

    if package.invalidated_at is not None:
        return _assessment(
            EvidenceIntakeState.INVALIDATED,
            selected,
            request,
            package_ref=package_ref,
            reasons=("EvidencePackage has been invalidated.",),
        )

    if request.max_package_age_seconds is not None:
        if package.created_at is None:
            return _assessment(
                EvidenceIntakeState.UNVERIFIED,
                selected,
                request,
                package_ref=package_ref,
                reasons=("EvidencePackage creation time is missing.",),
            )
        age_seconds = (current_time - package.created_at).total_seconds()
        if age_seconds < 0:
            return _assessment(
                EvidenceIntakeState.MISMATCHED,
                selected,
                request,
                package_ref=package_ref,
                reasons=("EvidencePackage creation time is in the future.",),
            )
        if age_seconds > request.max_package_age_seconds:
            return _assessment(
                EvidenceIntakeState.STALE,
                selected,
                request,
                package_ref=package_ref,
                reasons=("EvidencePackage exceeds its permitted age.",),
            )

    use_reasons = _use_mismatch(
        request.intended_use,
        package.permissible_uses,
        package.prohibited_uses,
        "EvidencePackage",
    )
    if use_reasons:
        return _assessment(
            EvidenceIntakeState.USE_PROHIBITED,
            selected,
            request,
            package_ref=package_ref,
            reasons=use_reasons,
        )

    expected_refs = {ref.binding_key(): ref for ref in package.admissibility_refs}
    supplied = {record.admissibility_ref.binding_key(): record for record in admissibility_records}
    missing_refs = tuple(sorted(
        ref.artifact_id for key, ref in expected_refs.items() if key not in supplied
    ))
    unexpected_refs = tuple(sorted(
        record.admissibility_ref.artifact_id
        for key, record in supplied.items()
        if key not in expected_refs
    ))
    if not expected_refs:
        return _assessment(
            EvidenceIntakeState.UNVERIFIED,
            selected,
            request,
            package_ref=package_ref,
            reasons=("EvidencePackage contains no claim-admissibility references.",),
        )
    if missing_refs or unexpected_refs:
        reasons = []
        if missing_refs:
            reasons.append("Missing exact admissibility records: " + ", ".join(missing_refs))
        if unexpected_refs:
            reasons.append("Unbound admissibility records supplied: " + ", ".join(unexpected_refs))
        return _assessment(
            EvidenceIntakeState.MISMATCHED,
            selected,
            request,
            package_ref=package_ref,
            reasons=tuple(reasons),
        )

    evaluated = []
    blocked = []
    constrained = []
    claim_reasons = []
    claim_constraints = []

    for key in sorted(expected_refs):
        record = supplied[key]
        evaluated.append(record.admissibility_ref.artifact_id)
        if record.case_id != package.case_id:
            blocked.append(record.admissibility_ref.artifact_id)
            claim_reasons.append(
                f"Claim {record.claim_id} is bound to a different case."
            )
            continue
        if record.invalidated_at is not None:
            blocked.append(record.admissibility_ref.artifact_id)
            claim_reasons.append(f"Claim {record.claim_id} admissibility is invalidated.")
            continue
        use_problem = _use_mismatch(
            request.intended_use,
            record.permissible_uses,
            record.prohibited_uses,
            f"Claim {record.claim_id}",
        )
        if use_problem:
            blocked.append(record.admissibility_ref.artifact_id)
            claim_reasons.extend(use_problem)
            continue
        if record.unresolved_conflicts:
            blocked.append(record.admissibility_ref.artifact_id)
            claim_reasons.append(f"Claim {record.claim_id} has unresolved conflicts.")
            continue

        disposition = record.disposition
        if disposition in {
            ClaimDisposition.CONFLICTED,
            ClaimDisposition.UNSUPPORTED,
            ClaimDisposition.STALE,
            ClaimDisposition.UNTRACEABLE,
            ClaimDisposition.UNKNOWN,
        }:
            blocked.append(record.admissibility_ref.artifact_id)
            claim_reasons.append(
                f"Claim {record.claim_id} disposition is {disposition.value}."
            )
            continue

        if (
            record.materiality in selected.require_supported_for
            and disposition is not ClaimDisposition.SUPPORTED
        ):
            blocked.append(record.admissibility_ref.artifact_id)
            claim_reasons.append(
                f"{record.materiality.value} claim {record.claim_id} requires SUPPORTED."
            )
            continue

        if (
            record.materiality is ClaimMateriality.LOW
            and disposition not in selected.low_materiality_allowed
        ):
            blocked.append(record.admissibility_ref.artifact_id)
            claim_reasons.append(
                f"LOW claim {record.claim_id} has inadmissible disposition {disposition.value}."
            )
            continue

        if disposition is ClaimDisposition.PARTIALLY_SUPPORTED or record.limitations:
            constrained.append(record.admissibility_ref.artifact_id)
            claim_constraints.append(
                f"Claim {record.claim_id} is limited or only partially supported."
            )

    workflow_reasons = _workflow_reasons(request, workflow_verification)
    if workflow_reasons:
        return _assessment(
            EvidenceIntakeState.UNVERIFIED,
            selected,
            request,
            package_ref=package_ref,
            evaluated=tuple(evaluated),
            blocked=tuple(sorted(set(blocked))),
            constrained=tuple(sorted(set(constrained))),
            workflow=workflow_verification,
            reasons=tuple(claim_reasons) + workflow_reasons,
            constraints=tuple(claim_constraints),
        )

    if blocked:
        state = (
            EvidenceIntakeState.CONFLICTED
            if package.contradictions
            or any("CONFLICTED" in reason or "conflict" in reason.lower() for reason in claim_reasons)
            else EvidenceIntakeState.UNVERIFIED
        )
        return _assessment(
            state,
            selected,
            request,
            package_ref=package_ref,
            evaluated=tuple(evaluated),
            blocked=tuple(sorted(set(blocked))),
            constrained=tuple(sorted(set(constrained))),
            workflow=workflow_verification,
            reasons=tuple(claim_reasons),
            constraints=tuple(claim_constraints),
        )

    package_reasons = []
    package_constraints = list(claim_constraints)
    if package.contradictions and selected.block_on_package_contradictions:
        package_reasons.append("EvidencePackage contains unresolved contradictions.")
    if package.unresolved_questions:
        if selected.block_on_package_questions:
            package_constraints.append("EvidencePackage contains unresolved questions.")
        else:
            package_constraints.append("Unresolved package questions are retained as limitations.")

    if package_reasons:
        return _assessment(
            EvidenceIntakeState.CONFLICTED,
            selected,
            request,
            package_ref=package_ref,
            evaluated=tuple(evaluated),
            constrained=tuple(sorted(set(constrained))),
            workflow=workflow_verification,
            reasons=tuple(package_reasons),
            constraints=tuple(package_constraints),
        )

    if constrained or package_constraints:
        return _assessment(
            EvidenceIntakeState.CONSTRAINED,
            selected,
            request,
            package_ref=package_ref,
            evaluated=tuple(evaluated),
            constrained=tuple(sorted(set(constrained))),
            workflow=workflow_verification,
            constraints=tuple(package_constraints),
        )

    return _assessment(
        EvidenceIntakeState.VALID,
        selected,
        request,
        package_ref=package_ref,
        evaluated=tuple(evaluated),
        workflow=workflow_verification,
    )


def _package_mismatches(
    request: EvidenceIntakeRequest,
    package: EvidencePackageBinding,
) -> Tuple[str, ...]:
    checks = (
        ("case_id", request.expected_case_id, package.case_id),
        ("package_id", request.expected_package_id, package.package_id),
        ("package_version", request.expected_package_version, package.package_version),
        ("package_digest", request.expected_package_digest, package.package_digest),
    )
    return tuple(
        f"EvidencePackage {name} does not match the requested binding."
        for name, expected, actual in checks
        if expected is not None and expected != actual
    )


def _workflow_reasons(
    request: EvidenceIntakeRequest,
    workflow: Optional[WorkflowVerificationBinding],
) -> Tuple[str, ...]:
    if not request.workflow_required and workflow is None:
        return ()
    if workflow is None:
        return ("Required NodeVerificationBundle is missing.",)
    if workflow.invalidated_at is not None:
        return ("NodeVerificationBundle has been invalidated.",)

    reasons = []
    checks = (
        ("workflow", request.expected_workflow_fingerprint, workflow.workflow_fingerprint),
        ("node", request.expected_node_fingerprint, workflow.node_fingerprint),
        (
            "workflow state",
            request.expected_workflow_state_fingerprint,
            workflow.workflow_state_fingerprint,
        ),
    )
    for label, expected, actual in checks:
        if expected is not None and expected != actual:
            reasons.append(f"NodeVerificationBundle {label} fingerprint mismatch.")
    if not workflow.accepted:
        reasons.append("NodeVerificationBundle is not accepted.")
    if workflow.unresolved_criteria:
        reasons.append("NodeVerificationBundle has unresolved criteria.")
    for criterion in workflow.criteria:
        if criterion.kind is CriterionKind.DETERMINISTIC and not criterion.succeeded:
            reasons.append(
                f"Deterministic criterion {criterion.criterion_id} did not succeed."
            )
        elif criterion.blocking and not criterion.succeeded:
            reasons.append(
                f"Blocking criterion {criterion.criterion_id} did not succeed."
            )
    return tuple(reasons)


def _use_mismatch(
    intended_use: str,
    permissible: Iterable[str],
    prohibited: Iterable[str],
    subject: str,
) -> Tuple[str, ...]:
    allowed = set(permissible)
    denied = set(prohibited)
    reasons = []
    if intended_use in denied:
        reasons.append(f"{subject} explicitly prohibits intended use {intended_use}.")
    if allowed and intended_use not in allowed:
        reasons.append(f"{subject} does not permit intended use {intended_use}.")
    return tuple(reasons)


def _assessment(
    state: EvidenceIntakeState,
    policy: EvidenceIntakePolicy,
    request: EvidenceIntakeRequest,
    package_ref: Optional[VersionedArtifactRef] = None,
    evaluated: Tuple[str, ...] = (),
    blocked: Tuple[str, ...] = (),
    constrained: Tuple[str, ...] = (),
    workflow: Optional[WorkflowVerificationBinding] = None,
    reasons: Tuple[str, ...] = (),
    constraints: Tuple[str, ...] = (),
) -> EvidenceIntakeAssessment:
    return EvidenceIntakeAssessment(
        state=state,
        policy_version=policy.version,
        package_ref=package_ref,
        intended_use=request.intended_use,
        evaluated_claim_refs=evaluated,
        blocking_claim_refs=blocked,
        constrained_claim_refs=constrained,
        workflow_bundle_fingerprint=(
            workflow.bundle_fingerprint if workflow is not None else None
        ),
        blocking_reasons=reasons,
        constraints=constraints,
    )


def _require_digest(value: str, name: str) -> None:
    if not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{name} must be sha256:<64 lowercase hex>")


def _require_aware(value: Optional[datetime], name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware")


__all__ = [
    "ClaimDisposition",
    "ClaimMateriality",
    "CriterionKind",
    "EvidenceIntakeState",
    "VersionedArtifactRef",
    "ClaimAdmissibilityBinding",
    "EvidencePackageBinding",
    "CriterionVerificationBinding",
    "WorkflowVerificationBinding",
    "EvidenceIntakeRequest",
    "EvidenceIntakePolicy",
    "EvidenceIntakeAssessment",
    "assess_evidence_intake",
]
