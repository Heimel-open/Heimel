"""LogRocket Galileo adapter over the shared Behavioral Evidence Loop.

Galileo is an external behavioral sensor. It may normalize evidence, create
findings and propose bounded Factory work. It never owns execution authority,
receipts or outcome truth.
"""
from __future__ import annotations

from typing import Mapping, Sequence

from lib.behavioral_evidence_loop import (
    AuthorizationBindingV1,
    BehaviorFindingV1,
    BehavioralAction,
    BehavioralEvidenceLoop,
    BehavioralObservationV1,
    BehavioralSensorAdapter,
    ClaimKind,
    EvidenceRefV1,
    ExecutionReceiptV1,
    ImprovementCandidateV1,
    ObservationMode,
    OutcomeEvidenceV1,
    PrivacyEnvelopeV1,
    authority_boundary,
    classify_outcome,
)

SOURCE = "logrocket_galileo"


class LogRocketGalileoAdapter(BehavioralSensorAdapter):
    """Normalize Galileo evidence without creating execution authority."""

    allowed_actions = frozenset(
        {BehavioralAction.ANALYZE, BehavioralAction.PROPOSE_BUILD_ORDER}
    )

    def __init__(self) -> None:
        super().__init__(SOURCE)

    def normalize_funnel_insight(
        self,
        *,
        evidence_id: str,
        insight_id: str,
        summary: str,
        session_refs: Sequence[str],
        payload_digest: str,
        observed_at: str,
        captured_at: str,
        privacy: PrivacyEnvelopeV1,
        provenance_ref: str,
        mode: ObservationMode = ObservationMode.LIVE,
        observation_id: str | None = None,
        funnel_ref: str | None = None,
        step_ref: str | None = None,
        metadata: Mapping[str, str] | None = None,
    ) -> BehavioralObservationV1:
        sessions = _clean_refs(session_refs)
        if not sessions:
            raise ValueError("at least one supporting session_ref is required")
        if not insight_id.strip():
            raise ValueError("insight_id is required")
        if not summary.strip():
            raise ValueError("summary is required")

        merged_metadata = dict(metadata or {})
        merged_metadata["insight_id"] = insight_id.strip()
        merged_metadata["session_refs"] = ",".join(sessions)
        if funnel_ref and funnel_ref.strip():
            merged_metadata["funnel_ref"] = funnel_ref.strip()
        if step_ref and step_ref.strip():
            merged_metadata["step_ref"] = step_ref.strip()

        evidence = EvidenceRefV1(
            evidence_id=evidence_id,
            source_type=SOURCE,
            source_ref=f"galileo:{insight_id.strip()}",
            payload_digest=payload_digest,
            observed_at=observed_at,
            captured_at=captured_at,
            privacy=privacy,
            provenance_ref=provenance_ref,
            resource_ref=_resource_ref(funnel_ref, step_ref),
            metadata=merged_metadata,
        )
        return self.normalize_observation(
            observation_id=observation_id or f"obs:{evidence_id}",
            event_type="funnel_non_conversion_pattern",
            observed_condition=summary,
            evidence_refs=(evidence,),
            mode=mode,
            resource_ref=_resource_ref(funnel_ref, step_ref),
        )

    def build_finding(
        self,
        *,
        finding_id: str,
        observation: BehavioralObservationV1,
        expected_condition_ref: str,
        confidence: float,
        materiality: str,
        reproducibility_ref: str,
        contradictory_evidence_refs: Sequence[str] = (),
    ) -> BehaviorFindingV1:
        if any(item.source_type != SOURCE for item in observation.evidence_refs):
            raise ValueError(f"expected observation evidence source {SOURCE!r}")
        return BehaviorFindingV1(
            finding_id=finding_id,
            trace_refs=(),
            evidence_refs=tuple(item.evidence_id for item in observation.evidence_refs),
            claim_kind=ClaimKind.MODEL_EXPLANATION,
            observed_condition=observation.observed_condition,
            expected_condition_ref=expected_condition_ref,
            confidence=confidence,
            contradictory_evidence_refs=tuple(contradictory_evidence_refs),
            materiality=materiality,
            generated_by=SOURCE,
            reproducibility_ref=reproducibility_ref,
        )

    def build_candidate(
        self,
        *,
        candidate_id: str,
        finding: BehaviorFindingV1,
        hypothesis: str,
        candidate_change: str,
        target_ref: str,
        expected_outcome: str,
        action_payload_digest: str,
        validation_refs: Sequence[str],
        owner_ref: str,
        risk_class: str = "medium",
        requested_actions: Sequence[BehavioralAction] = (
            BehavioralAction.PROPOSE_BUILD_ORDER,
        ),
    ) -> ImprovementCandidateV1:
        if finding.generated_by != SOURCE:
            raise ValueError(f"expected finding source {SOURCE!r}")
        return self.propose_candidate(
            candidate_id=candidate_id,
            finding_refs=(finding.finding_id,),
            hypothesis=hypothesis,
            proposed_change_type=candidate_change,
            target_ref=target_ref,
            expected_outcome=expected_outcome,
            action_payload_digest=action_payload_digest,
            requested_actions=tuple(requested_actions),
            risk_class=risk_class,
            required_evaluation_refs=tuple(validation_refs),
            owner_ref=owner_ref,
        )

    def build_outcome_evidence(
        self,
        *,
        outcome_id: str,
        candidate: ImprovementCandidateV1,
        authorization: AuthorizationBindingV1,
        receipt: ExecutionReceiptV1,
        pre_evidence_refs: Sequence[str],
        post_evidence_refs: Sequence[str],
        observed_outcome: str,
        comparison_method: str,
        window_start: str,
        window_end: str,
        metric_name: str,
        baseline_value: float | None,
        observed_value: float | None,
        lower_is_better: bool = False,
        minimum_improvement: float = 0,
        causal_caveats: Sequence[str] = (),
    ) -> OutcomeEvidenceV1:
        """Create receipt-bound outcome evidence and validate the full chain."""

        status = classify_outcome(
            baseline_value=baseline_value,
            observed_value=observed_value,
            pre_evidence_refs=pre_evidence_refs,
            post_evidence_refs=post_evidence_refs,
            lower_is_better=lower_is_better,
            minimum_improvement=minimum_improvement,
        )
        outcome = OutcomeEvidenceV1(
            outcome_id=outcome_id,
            candidate_id=candidate.candidate_id,
            action_payload_digest=candidate.action_payload_digest,
            authorization_id=authorization.authorization_id,
            execution_receipt_id=receipt.receipt_id,
            pre_evidence_refs=tuple(pre_evidence_refs),
            post_evidence_refs=tuple(post_evidence_refs),
            expected_outcome=candidate.expected_outcome,
            observed_outcome=observed_outcome,
            comparison_method=comparison_method,
            window_start=window_start,
            window_end=window_end,
            metric_name=metric_name,
            baseline_value=baseline_value,
            observed_value=observed_value,
            causal_caveats=tuple(causal_caveats),
            status=status,
        )
        return BehavioralEvidenceLoop.verify_outcome(
            candidate, authorization, receipt, outcome
        )


def execution_boundary(candidate: ImprovementCandidateV1) -> str:
    """Compatibility name for the shared authority boundary."""

    return authority_boundary(candidate)


def _clean_refs(refs: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(ref).strip() for ref in refs if str(ref).strip()))


def _resource_ref(funnel_ref: str | None, step_ref: str | None) -> str:
    funnel = funnel_ref.strip() if funnel_ref and funnel_ref.strip() else ""
    step = step_ref.strip() if step_ref and step_ref.strip() else ""
    if funnel and step:
        return f"funnel:{funnel}/step:{step}"
    if funnel:
        return f"funnel:{funnel}"
    if step:
        return f"step:{step}"
    return ""


__all__ = [
    "SOURCE",
    "LogRocketGalileoAdapter",
    "execution_boundary",
]
