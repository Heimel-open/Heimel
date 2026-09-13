"""Canonical Factory Experience Memory boundary.

Experience memory is retrieval context and evidence only. It can help a worker or
reviewer find prior work, but it can never create, preserve, revive, or widen
runtime authority. REHT remains the final authorization boundary.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Iterable


AUTHORITY_EFFECT = "none"
ADAPTER_DEJA_VU = "deja-vu-local"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceBinding:
    repo: str
    commit_sha: str | None = None
    pr_number: int | None = None
    test_refs: tuple[str, ...] = ()
    receipt_refs: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    file_refs: tuple[str, ...] = ()

    @property
    def corroborated(self) -> bool:
        return bool(
            self.commit_sha
            or self.pr_number is not None
            or self.test_refs
            or self.receipt_refs
            or self.decision_refs
        )


@dataclass(frozen=True)
class ExperienceRecord:
    record_id: str
    adapter_id: str
    provider_id: str
    session_id: str
    source_ref: str
    source_digest: str
    content_digest: str
    observed_at_ns: int
    binding: EvidenceBinding
    valid_until_ns: int | None = None
    superseded_by: str | None = None
    authority_effect: str = AUTHORITY_EFFECT

    def __post_init__(self) -> None:
        if self.authority_effect != AUTHORITY_EFFECT:
            raise ValueError("experience memory cannot carry authority")
        for name in ("record_id", "adapter_id", "provider_id", "session_id"):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        for name in ("source_digest", "content_digest"):
            value = getattr(self, name)
            if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                raise ValueError(f"{name} must be a lowercase sha256 hex digest")


@dataclass(frozen=True)
class RecallAssessment:
    record_id: str
    state: str
    injectable: bool
    reasons: tuple[str, ...]
    authority_effect: str = AUTHORITY_EFFECT

    def __post_init__(self) -> None:
        if self.authority_effect != AUTHORITY_EFFECT:
            raise ValueError("recall assessment cannot carry authority")

    def as_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "state": self.state,
            "injectable": self.injectable,
            "reasons": list(self.reasons),
            "authority_effect": self.authority_effect,
        }


def assess_recall(
    record: ExperienceRecord,
    *,
    current_repo: str,
    now_ns: int | None = None,
) -> RecallAssessment:
    """Classify recalled experience without converting it into authority."""
    now = time.time_ns() if now_ns is None else now_ns

    if record.superseded_by:
        return RecallAssessment(
            record_id=record.record_id,
            state="superseded",
            injectable=False,
            reasons=(f"superseded_by:{record.superseded_by}",),
        )

    if record.valid_until_ns is not None and now >= record.valid_until_ns:
        return RecallAssessment(
            record_id=record.record_id,
            state="stale",
            injectable=False,
            reasons=("freshness_window_expired",),
        )

    if record.binding.repo != current_repo:
        return RecallAssessment(
            record_id=record.record_id,
            state="cross_repo_context",
            injectable=True,
            reasons=("repository_binding_differs", "independent_verification_required"),
        )

    if record.binding.corroborated:
        return RecallAssessment(
            record_id=record.record_id,
            state="corroborated_context",
            injectable=True,
            reasons=("artifact_or_evidence_binding_present",),
        )

    return RecallAssessment(
        record_id=record.record_id,
        state="raw_context",
        injectable=True,
        reasons=("transcript_only", "independent_verification_required"),
    )


def make_recall_receipt(
    *,
    query: str,
    adapter_id: str,
    assessments: Iterable[RecallAssessment],
    injected_context: str = "",
    created_at_ns: int | None = None,
) -> dict:
    """Emit a digest-only retrieval receipt; raw query/context are not persisted."""
    items = tuple(assessments)
    return {
        "schema": "valo.experience-recall-receipt.v1",
        "adapter_id": adapter_id,
        "query_digest": _digest(query),
        "injected_context_digest": _digest(injected_context),
        "created_at_ns": time.time_ns() if created_at_ns is None else created_at_ns,
        "matches": [item.as_dict() for item in items],
        "authority_effect": AUTHORITY_EFFECT,
    }


def deja_vu_record(
    *,
    record_id: str,
    provider_id: str,
    session_id: str,
    source_ref: str,
    source_material: str,
    recalled_context: str,
    observed_at_ns: int,
    repo: str,
    commit_sha: str | None = None,
    pr_number: int | None = None,
    test_refs: Iterable[str] = (),
    receipt_refs: Iterable[str] = (),
    decision_refs: Iterable[str] = (),
    file_refs: Iterable[str] = (),
    valid_until_ns: int | None = None,
    superseded_by: str | None = None,
) -> ExperienceRecord:
    """Normalize a Déjà Vu recall/blame result into the canonical record.

    The caller extracts fields from the optional Déjà Vu MCP/CLI integration.
    VALO deliberately does not depend on vendor-specific transcript storage or
    treat a recalled transcript as verified truth.
    """
    return ExperienceRecord(
        record_id=record_id,
        adapter_id=ADAPTER_DEJA_VU,
        provider_id=provider_id,
        session_id=session_id,
        source_ref=source_ref,
        source_digest=_digest(source_material),
        content_digest=_digest(recalled_context),
        observed_at_ns=observed_at_ns,
        binding=EvidenceBinding(
            repo=repo,
            commit_sha=commit_sha,
            pr_number=pr_number,
            test_refs=tuple(test_refs),
            receipt_refs=tuple(receipt_refs),
            decision_refs=tuple(decision_refs),
            file_refs=tuple(file_refs),
        ),
        valid_until_ns=valid_until_ns,
        superseded_by=superseded_by,
    )
