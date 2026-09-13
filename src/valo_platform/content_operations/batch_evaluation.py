"""Aggregate-effect evaluation for governed content batches.

Batch evaluation preserves every member outcome and may only maintain or
increase restriction. It does not issue clearance or execute content changes.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Sequence

import rfc8785
from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.action_envelope.models import ActionDecision

from .actions import ContentActionCase, ContentMateriality
from .content_policy import (
    ContentPolicyEvaluation,
    ContentPolicyProfile,
    ContentRiskEvidence,
    materiality_score,
)


_DECISION_ORDER = {
    ActionDecision.ALLOW: 0,
    ActionDecision.MODIFY: 1,
    ActionDecision.STEP_UP: 2,
    ActionDecision.DEFER: 3,
    ActionDecision.DENY: 4,
    ActionDecision.HALT: 5,
}


class ContentBatchEvaluation(BaseModel):
    """Deterministic aggregate recommendation bound to ordered members."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    decision: ActionDecision
    batch_digest: str
    member_payload_digests: tuple[str, ...] = Field(min_length=1)
    member_decisions: tuple[ActionDecision, ...] = Field(min_length=1)
    policy_digest: str
    tenant_id: str
    mandate_ref: str
    mandate_fingerprint: str
    unique_record_ids: tuple[str, ...]
    markets: tuple[str, ...]
    jurisdictions: tuple[str, ...]
    locales: tuple[str, ...]
    channels: tuple[str, ...]
    audiences: tuple[str, ...]
    total_batch_size: int = Field(ge=1)
    maximum_materiality: ContentMateriality
    cumulative_materiality_score: int = Field(ge=0)
    high_risk_domain_count: int = Field(ge=0)
    reasons: tuple[str, ...]
    required_approver_roles: tuple[str, ...] = ()
    evaluated_at: datetime


class ContentBatchEvaluator:
    """Evaluate aggregate effect without weakening any item recommendation."""

    def evaluate(
        self,
        *,
        action_cases: Sequence[ContentActionCase],
        item_evaluations: Sequence[ContentPolicyEvaluation],
        risk_evidence: Sequence[ContentRiskEvidence],
        policy: ContentPolicyProfile,
        now: datetime | None = None,
    ) -> ContentBatchEvaluation:
        if not action_cases:
            raise ValueError("content batch requires at least one Action Case")
        if not (
            len(action_cases) == len(item_evaluations) == len(risk_evidence)
        ):
            raise ValueError(
                "action cases, item evaluations and risk evidence must align"
            )

        policy_digest = policy.digest()
        for action_case, evaluation in zip(action_cases, item_evaluations):
            if evaluation.payload_digest != action_case.digest():
                raise ValueError("item evaluation does not bind its Action Case")
            if evaluation.policy_digest != policy_digest:
                raise ValueError("item evaluation does not bind the batch policy")

        member_decisions = tuple(item.decision for item in item_evaluations)
        decision = max(member_decisions, key=_DECISION_ORDER.__getitem__)
        reasons = [
            f"member {index} requires {item.decision.value}"
            for index, item in enumerate(item_evaluations)
            if item.decision is not ActionDecision.ALLOW
        ]

        tenants = {case.content.tenant_id for case in action_cases}
        mandates = {case.content.delegated_mandate_ref for case in action_cases}
        mandate_fingerprints = {
            case.action_case.mandate_fingerprint for case in action_cases
        }
        if len(tenants) != 1:
            decision = _more_restrictive(decision, ActionDecision.DENY)
            reasons.append("batch members span multiple tenants")
        if len(mandates) != 1 or len(mandate_fingerprints) != 1:
            decision = _more_restrictive(decision, ActionDecision.DENY)
            reasons.append("batch members do not share one mandate binding")

        unique_records = tuple(
            sorted({record for case in action_cases for record in case.content.record_ids})
        )
        markets = tuple(sorted({case.content.market for case in action_cases}))
        jurisdictions = tuple(
            sorted(
                {
                    jurisdiction
                    for case in action_cases
                    for jurisdiction in case.content.jurisdictions
                }
            )
        )
        locales = tuple(
            sorted({locale for case in action_cases for locale in case.content.locales})
        )
        channels = tuple(
            sorted({channel for case in action_cases for channel in case.content.channels})
        )
        audiences = tuple(
            sorted(
                {
                    audience
                    for case in action_cases
                    for audience in case.content.affected_audiences
                }
            )
        )
        total_batch_size = sum(case.content.batch_size for case in action_cases)
        materialities = tuple(case.content.materiality for case in action_cases)
        maximum_materiality = max(materialities, key=materiality_score)
        cumulative_materiality = sum(materiality_score(item) for item in materialities)
        high_risk_domain_count = sum(
            len(evidence.risk_domains) for evidence in risk_evidence
        )

        aggregate_reasons: list[str] = []
        if total_batch_size > policy.max_batch_size:
            aggregate_reasons.append("aggregate batch size exceeds policy threshold")
        if len(markets) > policy.max_unique_markets:
            aggregate_reasons.append("aggregate market scope exceeds policy threshold")
        if len(locales) > policy.max_unique_locales:
            aggregate_reasons.append("aggregate locale scope exceeds policy threshold")
        if len(audiences) > policy.max_audience_count:
            aggregate_reasons.append("aggregate audience scope exceeds policy threshold")
        if cumulative_materiality > policy.max_cumulative_materiality_score:
            aggregate_reasons.append(
                "cumulative content materiality exceeds policy threshold"
            )
        if high_risk_domain_count:
            aggregate_reasons.append("batch contains high-risk content domains")

        if aggregate_reasons:
            decision = _more_restrictive(decision, ActionDecision.STEP_UP)
            reasons.extend(aggregate_reasons)

        member_digests = tuple(case.digest() for case in action_cases)
        batch_digest = _batch_digest(member_digests, policy_digest)
        required_roles = tuple(
            sorted(
                {
                    role
                    for item in item_evaluations
                    for role in item.required_approver_roles
                }
                | (
                    set(policy.required_approver_roles)
                    if _DECISION_ORDER[decision]
                    >= _DECISION_ORDER[ActionDecision.STEP_UP]
                    else set()
                )
            )
        )

        return ContentBatchEvaluation(
            decision=decision,
            batch_digest=batch_digest,
            member_payload_digests=member_digests,
            member_decisions=member_decisions,
            policy_digest=policy_digest,
            tenant_id=next(iter(tenants)) if len(tenants) == 1 else "mixed",
            mandate_ref=next(iter(mandates)) if len(mandates) == 1 else "mixed",
            mandate_fingerprint=(
                next(iter(mandate_fingerprints))
                if len(mandate_fingerprints) == 1
                else "mixed"
            ),
            unique_record_ids=unique_records,
            markets=markets,
            jurisdictions=jurisdictions,
            locales=locales,
            channels=channels,
            audiences=audiences,
            total_batch_size=total_batch_size,
            maximum_materiality=maximum_materiality,
            cumulative_materiality_score=cumulative_materiality,
            high_risk_domain_count=high_risk_domain_count,
            reasons=tuple(reasons or ["all members remain inside aggregate policy"]),
            required_approver_roles=required_roles,
            evaluated_at=_as_utc(now or datetime.now(timezone.utc)),
        )


def _more_restrictive(
    current: ActionDecision, candidate: ActionDecision
) -> ActionDecision:
    if _DECISION_ORDER[candidate] > _DECISION_ORDER[current]:
        return candidate
    return current


def _batch_digest(member_digests: tuple[str, ...], policy_digest: str) -> str:
    encoded = rfc8785.dumps(
        {
            "member_payload_digests": member_digests,
            "policy_digest": policy_digest,
        }
    )
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
