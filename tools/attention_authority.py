from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import FrozenSet, Tuple


class SubjectKind(str, Enum):
    HUMAN = "human"
    MODEL = "model"
    ORGANIZATION = "organization"


class EvidenceKind(str, Enum):
    CREDENTIAL = "credential"
    OUTCOME = "outcome"
    PROVENANCE = "provenance"
    CHALLENGE = "challenge"
    CORRECTION = "correction"


class AuthorityStatus(str, Enum):
    PROVEN = "PROVEN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    kind: EvidenceKind
    observed_at: datetime
    scope: FrozenSet[str]
    relevance: float = 1.0

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise ValueError("evidence_id is required")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if not 0.0 <= self.relevance <= 1.0:
            raise ValueError("relevance must be between 0 and 1")


@dataclass(frozen=True)
class DemonstratedCapability:
    capability_id: str
    outcome: str
    gcu_scope: str
    constraints: FrozenSet[str]
    quality: float
    cost: float
    error_rate: float
    stability: float
    evidence_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.capability_id or not self.outcome or not self.gcu_scope:
            raise ValueError("capability_id, outcome and gcu_scope are required")
        if not self.constraints:
            raise ValueError("constraints are required")
        if not self.evidence_ids:
            raise ValueError("demonstrated capability requires evidence")
        for name, value in (
            ("quality", self.quality),
            ("error_rate", self.error_rate),
            ("stability", self.stability),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.cost < 0:
            raise ValueError("cost cannot be negative")


@dataclass(frozen=True)
class BoundedClaim:
    claim_id: str
    gcu_scope: str
    required_capability: str
    provenance_evidence_ids: Tuple[str, ...]
    supporting_evidence_ids: Tuple[str, ...]
    challenge_evidence_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.claim_id or not self.gcu_scope or not self.required_capability:
            raise ValueError("claim_id, gcu_scope and required_capability are required")


@dataclass(frozen=True)
class SubjectAuthority:
    subject_id: str
    subject_kind: SubjectKind
    credentials: Tuple[str, ...]
    capabilities: Tuple[DemonstratedCapability, ...]


@dataclass(frozen=True)
class AttentionAuthorityResult:
    status: AuthorityStatus
    subject_id: str
    claim_id: str
    decisive_evidence_ids: Tuple[str, ...]
    reasons: Tuple[str, ...]

    @property
    def proven(self) -> bool:
        return self.status is AuthorityStatus.PROVEN


def evaluate_attention_authority(
    *,
    subject: SubjectAuthority,
    claim: BoundedClaim,
    evidence: Tuple[EvidenceRecord, ...],
    now: datetime | None = None,
    max_evidence_age: timedelta = timedelta(days=365),
    min_relevance: float = 0.6,
) -> AttentionAuthorityResult:
    """Evaluate claim-specific attention authority from demonstrated outcomes.

    Credentials are context only. They are never decisive evidence.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    evidence_by_id = {item.evidence_id: item for item in evidence}

    capabilities = tuple(
        capability
        for capability in subject.capabilities
        if capability.capability_id == claim.required_capability
        and capability.gcu_scope == claim.gcu_scope
    )
    if not capabilities:
        return AttentionAuthorityResult(
            AuthorityStatus.OUT_OF_SCOPE,
            subject.subject_id,
            claim.claim_id,
            (),
            ("no demonstrated capability matches this claim and GCU scope",),
        )

    required_ids = set(claim.provenance_evidence_ids) | set(claim.supporting_evidence_ids)
    for capability in capabilities:
        required_ids.update(capability.evidence_ids)

    missing = sorted(required_ids - evidence_by_id.keys())
    if missing:
        return AttentionAuthorityResult(
            AuthorityStatus.INSUFFICIENT_EVIDENCE,
            subject.subject_id,
            claim.claim_id,
            (),
            tuple(f"missing evidence: {item}" for item in missing),
        )

    decisive = tuple(
        evidence_by_id[evidence_id]
        for evidence_id in sorted(required_ids)
        if evidence_by_id[evidence_id].kind is not EvidenceKind.CREDENTIAL
    )
    if not decisive:
        return AttentionAuthorityResult(
            AuthorityStatus.INSUFFICIENT_EVIDENCE,
            subject.subject_id,
            claim.claim_id,
            (),
            ("credentials alone cannot establish attention authority",),
        )

    if not any(item.kind is EvidenceKind.OUTCOME for item in decisive):
        return AttentionAuthorityResult(
            AuthorityStatus.INSUFFICIENT_EVIDENCE,
            subject.subject_id,
            claim.claim_id,
            tuple(item.evidence_id for item in decisive),
            ("no outcome evidence supports the demonstrated capability",),
        )
    if not any(item.kind is EvidenceKind.PROVENANCE for item in decisive):
        return AttentionAuthorityResult(
            AuthorityStatus.INSUFFICIENT_EVIDENCE,
            subject.subject_id,
            claim.claim_id,
            tuple(item.evidence_id for item in decisive),
            ("claim provenance is not evidenced",),
        )

    irrelevant = tuple(
        item.evidence_id
        for item in decisive
        if claim.gcu_scope not in item.scope or item.relevance < min_relevance
    )
    if irrelevant:
        return AttentionAuthorityResult(
            AuthorityStatus.OUT_OF_SCOPE,
            subject.subject_id,
            claim.claim_id,
            tuple(item.evidence_id for item in decisive),
            tuple(f"evidence is not relevant enough: {item}" for item in irrelevant),
        )

    stale = tuple(
        item.evidence_id for item in decisive if now - item.observed_at > max_evidence_age
    )
    if stale:
        return AttentionAuthorityResult(
            AuthorityStatus.STALE_EVIDENCE,
            subject.subject_id,
            claim.claim_id,
            tuple(item.evidence_id for item in decisive),
            tuple(f"evidence is stale: {item}" for item in stale),
        )

    return AttentionAuthorityResult(
        AuthorityStatus.PROVEN,
        subject.subject_id,
        claim.claim_id,
        tuple(item.evidence_id for item in decisive),
        ("provenance + demonstrated capability + claim evidence",),
    )
