"""Adapter from governed-media candidates to the existing Approval Queue."""

from __future__ import annotations

from typing import Any, List, Protocol

from pydantic import Field

from .models import CandidateType, HandlingMode, PublicationCandidate, StrictModel
from .shadow_loop import DailyShadowQueue


class ApprovalQueuePort(Protocol):
    def enqueue(self, **kwargs: Any) -> Any:
        ...


class ApprovalQueueBinding(StrictModel):
    approval_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    approved_artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action_type: str = Field(min_length=1)
    handling_mode: HandlingMode
    publication_authority_granted: bool = False


def enqueue_publication_candidate(
    candidate: PublicationCandidate,
    queue: ApprovalQueuePort,
    actor_id: str,
    tenant_id: str,
) -> ApprovalQueueBinding:
    if candidate.handling_mode == HandlingMode.BLOCKED:
        raise ValueError("blocked candidates cannot enter the approval queue")

    action_type = (
        "governed_media_post_review"
        if candidate.candidate_type == CandidateType.POST
        else "governed_media_comment_review"
    )
    evidence_ids = _candidate_evidence_ids(candidate)
    risk_tier = "L3" if candidate.handling_mode == HandlingMode.DIRECT_HUMAN else "L2"

    approval = queue.enqueue(
        action_id=candidate.candidate_id,
        execution_id=f"shadow:{candidate.candidate_id}",
        action_type=action_type,
        actor_id=actor_id,
        tenant_id=tenant_id,
        decision="defer",
        reason=(
            f"{candidate.why_now} | objective={candidate.relationship_objective} | "
            f"handling={candidate.handling_mode.value}"
        ),
        evidence_ids=evidence_ids,
        signal_ids=candidate.source_signal_ids,
        policy_id="governed-media-shadow/v1",
        connector=None,
        risk_tier=risk_tier,
        receipt_reference=None,
        actor_role="founding_creator",
        actor_authority_level=1,
    )
    approval_id = getattr(approval, "approval_id", None)
    if not approval_id:
        raise ValueError("approval queue did not return an approval_id")

    return ApprovalQueueBinding(
        approval_id=approval_id,
        candidate_id=candidate.candidate_id,
        approved_artifact_digest=candidate.variant.rendered_content_digest,
        action_type=action_type,
        handling_mode=candidate.handling_mode,
        publication_authority_granted=False,
    )


def enqueue_daily_shadow_queue(
    daily_queue: DailyShadowQueue,
    queue: ApprovalQueuePort,
    actor_id: str,
    tenant_id: str,
) -> List[ApprovalQueueBinding]:
    candidates = daily_queue.post_candidates + daily_queue.comment_candidates
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("daily queue contains duplicate candidate IDs")
    return [
        enqueue_publication_candidate(candidate, queue, actor_id, tenant_id)
        for candidate in candidates
    ]


def _candidate_evidence_ids(candidate: PublicationCandidate) -> List[str]:
    refs = [source.ref for source in candidate.variant.source_refs]
    for claim in candidate.variant.claim_bindings:
        refs.extend(evidence.ref for evidence in claim.evidence_refs)
    return list(dict.fromkeys(refs))


__all__ = [
    "ApprovalQueueBinding",
    "ApprovalQueuePort",
    "enqueue_daily_shadow_queue",
    "enqueue_publication_candidate",
]
