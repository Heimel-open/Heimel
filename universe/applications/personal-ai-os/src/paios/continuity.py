"""Portable continuity and Home/Travel merge checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from paios.peripherals import AdmissibilityStatus, EvidenceEnvelope, EvidenceStage


class BranchKind(str, Enum):
    HOME = "home"
    TRAVEL = "travel"


@dataclass(frozen=True)
class ContinuityCheckpoint:
    checkpoint_id: str
    relaion_id: str
    branch_id: str
    created_at: datetime
    state_root: str
    lineage_root: str
    signer: str
    signature_ref: str

    def __init__(
        self,
        checkpoint_id: str = "",
        relaion_id: str = "",
        branch_id: str = "",
        created_at: datetime = None,
        state_root: str = "",
        lineage_root: str = "",
        signer: str = "",
        signature_ref: str = "",
        relygon_id: str = "",
    ) -> None:
        object.__setattr__(self, "checkpoint_id", checkpoint_id)
        object.__setattr__(self, "relaion_id", relaion_id or relygon_id)
        object.__setattr__(self, "branch_id", branch_id)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "state_root", state_root)
        object.__setattr__(self, "lineage_root", lineage_root)
        object.__setattr__(self, "signer", signer)
        object.__setattr__(self, "signature_ref", signature_ref)

    @property
    def relygon_id(self) -> str:
        return self.relaion_id

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        for name, value in (
            ("checkpoint_id", self.checkpoint_id),
            ("relaion_id", self.relaion_id),
            ("branch_id", self.branch_id),
            ("state_root", self.state_root),
            ("lineage_root", self.lineage_root),
            ("signer", self.signer),
            ("signature_ref", self.signature_ref),
        ):
            if not value.strip():
                errors.append(f"{name} is required")
        if self.created_at.tzinfo is None:
            errors.append("created_at must be timezone-aware")
        return tuple(errors)


@dataclass(frozen=True)
class ContinuityBranch:
    branch_id: str
    relaion_id: str
    kind: BranchKind
    parent_checkpoint_id: str
    lineage_root: str
    created_at: datetime
    head_state_root: str
    evidence: tuple[EvidenceEnvelope, ...] = ()
    mandate_ids: tuple[str, ...] = ()
    integrity_refs: tuple[str, ...] = ()
    compromise_flags: tuple[str, ...] = ()
    disclosed_scopes: tuple[str, ...] = ()

    def __init__(
        self,
        branch_id: str = "",
        relaion_id: str = "",
        kind: BranchKind = BranchKind.HOME,
        parent_checkpoint_id: str = "",
        lineage_root: str = "",
        created_at: datetime = None,
        head_state_root: str = "",
        evidence: tuple[EvidenceEnvelope, ...] = (),
        mandate_ids: tuple[str, ...] = (),
        integrity_refs: tuple[str, ...] = (),
        compromise_flags: tuple[str, ...] = (),
        disclosed_scopes: tuple[str, ...] = (),
        relygon_id: str = "",
    ) -> None:
        object.__setattr__(self, "branch_id", branch_id)
        object.__setattr__(self, "relaion_id", relaion_id or relygon_id)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "parent_checkpoint_id", parent_checkpoint_id)
        object.__setattr__(self, "lineage_root", lineage_root)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "head_state_root", head_state_root)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "mandate_ids", mandate_ids)
        object.__setattr__(self, "integrity_refs", integrity_refs)
        object.__setattr__(self, "compromise_flags", compromise_flags)
        object.__setattr__(self, "disclosed_scopes", disclosed_scopes)

    @property
    def relygon_id(self) -> str:
        return self.relaion_id

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        for name, value in (
            ("branch_id", self.branch_id),
            ("relaion_id", self.relaion_id),
            ("parent_checkpoint_id", self.parent_checkpoint_id),
            ("lineage_root", self.lineage_root),
            ("head_state_root", self.head_state_root),
        ):
            if not value.strip():
                errors.append(f"{name} is required")
        if self.created_at.tzinfo is None:
            errors.append("created_at must be timezone-aware")
        return tuple(errors)


@dataclass(frozen=True)
class MergePolicy:
    allowed_travel_scopes: frozenset[str] = frozenset()
    require_integrity_ref: bool = True
    allow_amber: bool = True


@dataclass(frozen=True)
class MergeAssessment:
    status: AdmissibilityStatus
    reasons: tuple[str, ...]
    safe_evidence: tuple[EvidenceEnvelope, ...] = ()
    quarantined_evidence: tuple[EvidenceEnvelope, ...] = ()

    @property
    def mergeable(self) -> bool:
        return self.status in (AdmissibilityStatus.GREEN, AdmissibilityStatus.AMBER)


class ContinuityMergeError(RuntimeError):
    pass


def _evidence_key(item: EvidenceEnvelope) -> tuple[str, str]:
    return (item.observation_id, item.stage.value)


def assess_return_merge(
    home: ContinuityBranch,
    travel: ContinuityBranch,
    checkpoint: ContinuityCheckpoint,
    *,
    policy: MergePolicy | None = None,
) -> MergeAssessment:
    policy = policy or MergePolicy()
    red: list[str] = []
    amber: list[str] = []

    for prefix, errors in (
        ("checkpoint", checkpoint.validate()),
        ("home", home.validate()),
        ("travel", travel.validate()),
    ):
        red.extend(f"{prefix}: {error}" for error in errors)

    if home.kind is not BranchKind.HOME:
        red.append("home branch must have kind HOME")
    if travel.kind is not BranchKind.TRAVEL:
        red.append("returning branch must have kind TRAVEL")
    if home.relaion_id != checkpoint.relaion_id or travel.relaion_id != checkpoint.relaion_id:
        red.append("relaion identity mismatch")
    if travel.parent_checkpoint_id != checkpoint.checkpoint_id:
        red.append("travel branch is not a descendant of the expected checkpoint")
    if travel.lineage_root != checkpoint.lineage_root:
        red.append("travel lineage root does not match checkpoint")
    if checkpoint.created_at > travel.created_at:
        red.append("travel branch predates its parent checkpoint")
    if travel.compromise_flags:
        red.append("travel branch reports compromise indicators: " + ", ".join(travel.compromise_flags))
    if policy.require_integrity_ref and not travel.integrity_refs:
        red.append("travel branch has no integrity reference")

    unauthorized_scopes = set(travel.disclosed_scopes) - set(policy.allowed_travel_scopes)
    if unauthorized_scopes:
        red.append("travel branch disclosed state outside allowed scope: " + ", ".join(sorted(unauthorized_scopes)))

    safe_by_key: dict[tuple[str, str], EvidenceEnvelope] = {}
    quarantined: list[EvidenceEnvelope] = []
    conflicted: set[tuple[str, str]] = set()

    for item in (*home.evidence, *travel.evidence):
        errors = item.validate()
        if errors:
            quarantined.append(item)
            amber.append(f"invalid evidence {item.observation_id}: " + "; ".join(errors))
            continue
        if item.stage is EvidenceStage.CANONICAL:
            quarantined.append(item)
            amber.append(f"return merge cannot import canonical evidence directly: {item.observation_id}")
            continue

        key = _evidence_key(item)
        if key in conflicted:
            quarantined.append(item)
            continue

        previous = safe_by_key.get(key)
        if previous is None:
            safe_by_key[key] = item
        elif previous != item:
            safe_by_key.pop(key)
            conflicted.add(key)
            quarantined.extend((previous, item))
            amber.append(f"conflicting evidence for {item.observation_id} at stage {item.stage.value}")

    safe = tuple(safe_by_key.values())
    quarantined_tuple = tuple(quarantined)

    if red:
        return MergeAssessment(AdmissibilityStatus.RED, tuple(red + amber), (), tuple((*safe, *quarantined_tuple)))
    if amber and not policy.allow_amber:
        return MergeAssessment(AdmissibilityStatus.RED, tuple(amber), (), tuple((*safe, *quarantined_tuple)))
    if amber:
        return MergeAssessment(AdmissibilityStatus.AMBER, tuple(amber), safe, quarantined_tuple)
    return MergeAssessment(AdmissibilityStatus.GREEN, (), safe, ())


def canonicalize_merge(assessment: MergeAssessment) -> tuple[EvidenceEnvelope, ...]:
    if assessment.status is AdmissibilityStatus.RED:
        raise ContinuityMergeError("RED merge assessment cannot mutate canonical state")
    return assessment.safe_evidence
