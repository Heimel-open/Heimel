"""Fail-closed intake for explicitly approved media signals."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from pydantic import Field, model_validator

from .linkedin_adapter import LinkedInDraftRequest, build_linkedin_opportunity_signal
from .models import Confidentiality, DigestRef, MediaChannel, StrictModel
from .shadow_loop import OpportunitySignal


class SignalSourceType(str, Enum):
    REPOSITORY_CHANGE = "repository_change"
    RESEARCH = "research"
    FOUNDER_NOTE = "founder_note"


class PublicUseApproval(StrictModel):
    approval_ref: DigestRef
    approved_by: str = Field(min_length=1)
    approved_at: datetime
    allowed_channels: List[MediaChannel] = Field(min_length=1)
    expires_at: Optional[datetime] = None
    revoked: bool = False

    @model_validator(mode="after")
    def validate_times(self) -> "PublicUseApproval":
        _require_aware(self.approved_at, "approved_at")
        if self.expires_at is not None:
            _require_aware(self.expires_at, "expires_at")
            if self.expires_at <= self.approved_at:
                raise ValueError("public-use approval expiry must follow approval time")
        return self


class ApprovedLinkedInSignal(StrictModel):
    source_type: SignalSourceType
    source_artifact_ref: DigestRef
    confidentiality: Confidentiality
    public_use_approval: PublicUseApproval
    draft: LinkedInDraftRequest

    @model_validator(mode="after")
    def validate_public_use_boundary(self) -> "ApprovedLinkedInSignal":
        _require_aware(self.draft.observed_at, "draft.observed_at")
        if self.confidentiality != Confidentiality.PUBLIC:
            raise ValueError("only explicitly public source material may enter media intake")
        if self.public_use_approval.revoked:
            raise ValueError("revoked public-use approval cannot enter media intake")
        if MediaChannel.LINKEDIN not in self.public_use_approval.allowed_channels:
            raise ValueError("public-use approval does not allow LinkedIn")
        if self.public_use_approval.approved_at > self.draft.observed_at:
            raise ValueError("draft signal predates public-use approval")
        if (
            self.public_use_approval.expires_at is not None
            and self.draft.observed_at > self.public_use_approval.expires_at
        ):
            raise ValueError("public-use approval expired before the draft signal")
        source_key = _ref_key(self.source_artifact_ref)
        if source_key not in {_ref_key(item) for item in self.draft.source_refs}:
            raise ValueError("draft must bind the exact approved source artifact")
        return self


def verify_approved_signal_artifacts(
    repo_root: Path,
    records: Iterable[ApprovedLinkedInSignal],
) -> None:
    """Verify every local source, approval and evidence artifact against its declared digest."""
    root = repo_root.resolve()
    verified = set()

    for record in records:
        refs = [
            record.source_artifact_ref,
            record.public_use_approval.approval_ref,
            *record.draft.source_refs,
            *(
                evidence_ref
                for claim in record.draft.claim_bindings
                for evidence_ref in claim.evidence_refs
            ),
        ]
        for ref in refs:
            key = (ref.ref, ref.digest_sha256)
            if key in verified:
                continue
            verified.add(key)

            candidate = (root / ref.ref).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"artifact ref escapes repository root: {ref.ref}") from exc
            if not candidate.is_file():
                raise ValueError(f"artifact ref is not a repository file: {ref.ref}")

            actual = sha256(candidate.read_bytes()).hexdigest()
            if actual != ref.digest_sha256:
                raise ValueError(
                    f"artifact digest mismatch for {ref.ref}: "
                    f"expected {ref.digest_sha256}, got {actual}"
                )


def intake_approved_linkedin_signals(
    records: Iterable[ApprovedLinkedInSignal],
) -> List[OpportunitySignal]:
    accepted: List[OpportunitySignal] = []
    seen_signal_ids = set()
    for record in records:
        signal_id = record.draft.signal_id
        if signal_id in seen_signal_ids:
            raise ValueError(f"duplicate approved signal ID: {signal_id}")
        seen_signal_ids.add(signal_id)
        accepted.append(build_linkedin_opportunity_signal(record.draft))
    return accepted


def _ref_key(value: DigestRef) -> Tuple[str, str, Optional[str]]:
    return (value.ref, value.digest_sha256, value.version)


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


__all__ = [
    "ApprovedLinkedInSignal",
    "PublicUseApproval",
    "SignalSourceType",
    "intake_approved_linkedin_signals",
    "verify_approved_signal_artifacts",
]
