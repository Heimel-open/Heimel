"""Controlled shadow pilot for the 2026 Future Newsrooms Study.

The pilot demonstrates how a commercially supported industry report can remain
useful as market context while being restricted from causal, effectiveness or
autonomous-publication claims. It binds supplied metadata only; it is not a
substitute for archiving and verifying the full report and supporting records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.verification_factory import (
    AcquisitionEvidence,
    BiasDimension,
    BiasSignal,
    ClaimKind,
    ClaimMateriality,
    ClaimRecord,
    CommissioningProfile,
    ContentOriginKind,
    ContentOriginProfile,
    DerivationMode,
    DisclosureStatus,
    FundingAndControlProfile,
    InfluenceActor,
    InfluenceLink,
    InfluenceRole,
    ProductionStage,
    RealityEvidence,
    RelationshipEvidenceLevel,
    SourceIntegrityAssessment,
    SourceProfile,
    SourceType,
    VerificationCase,
    VerificationWorkOrder,
    VersionedRef,
)

from .evaluator import evaluate_newsroom_shadow
from .models import (
    NewsroomActionType,
    NewsroomGovernanceInputs,
    NewsroomRiskTier,
    NewsroomShadowEvaluation,
)


STUDY_URL = "https://info.arcxp.com/newsroom-study-2026"
AUDIENCERS_URL = (
    "https://theaudiencers.com/navigating-the-community-era-key-takeaways-"
    "from-the-2026-future-newsrooms-study/"
)


def _ref(
    artifact_id: str,
    value: object,
    *,
    version: str = "v1",
    reference: Optional[str] = None,
) -> VersionedRef:
    return VersionedRef(
        artifact_id=artifact_id,
        version=version,
        reference=reference or f"valo://pilot/future-newsroom/{artifact_id}/{version}",
        digest=canonical_digest(value),
    )


@dataclass(frozen=True)
class FutureNewsroomPilotCase:
    """All inputs and outputs for one replayable shadow case."""

    case: VerificationCase
    source_profiles: List[SourceProfile]
    source_integrity: Dict[str, SourceIntegrityAssessment]
    claim: ClaimRecord
    evidence: List[RealityEvidence]
    work_order: VerificationWorkOrder
    governance_inputs: NewsroomGovernanceInputs
    evaluation: NewsroomShadowEvaluation


def build_future_newsroom_pilot(
    *,
    human_review_completed: bool = True,
    now: Optional[datetime] = None,
) -> FutureNewsroomPilotCase:
    """Build the first Governed Newsroom source-integrity shadow case.

    The selected claim is deliberately narrow: the study provides an industry
    signal that newsroom AI adoption barriers are substantially organizational.
    It does not establish causality, intervention effectiveness or a requirement
    to purchase any particular governance product.
    """

    now = now or datetime.now(timezone.utc)
    case_id = "future-newsroom-study-2026"
    claim_id = "claim-organisational-ai-barriers"
    source_id = "future-newsroom-study-2026-report"

    source_metadata = {
        "title": "Future Newsrooms Study 2026",
        "study_url": STUDY_URL,
        "reported_sample": 448,
        "reported_countries": 86,
        "reported_signals": {
            "skills_gap_percent": 61,
            "cultural_resistance_percent": 52,
            "unclear_use_cases_percent": 45,
            "audience_need_first_percent": 21,
            "single_channel_first_percent": 64,
        },
        "producer_refs": ["FT Strategies", "WAN-IFRA"],
        "supporter_refs": ["Arc XP"],
        "limitations": [
            "Recruitment and self-selection require assessment",
            "Funding terms and publication-control rights are not established by the supplied metadata",
            "AI production disclosure is not established by the supplied metadata",
            "The study is an industry benchmark, not causal proof",
        ],
    }
    acquisition_ref = _ref(
        "future-newsroom-study-metadata",
        source_metadata,
        reference=STUDY_URL,
    )

    source_profile = SourceProfile(
        source_id=source_id,
        source_type=SourceType.SECONDARY_ANALYSIS,
        canonical_ref=acquisition_ref,
        title="Future Newsrooms Study 2026",
        publisher_or_producer="FT Strategies / WAN-IFRA",
        author_or_actor_refs=["FT Strategies", "WAN-IFRA"],
        independence_group="future-newsroom-study-production-chain",
        evidence_distance=1,
        method_transparent=False,
        reproducible=None,
        domain_competence_refs=[
            "FT Strategies newsroom transformation",
            "WAN-IFRA media industry network",
        ],
        incentive_flags=[
            "commercial-advisory-interest",
            "newsroom-technology-market-interest",
            "industry-network-selection",
        ],
        commissioning=CommissioningProfile(
            commissioned_by=None,
            paid_by=None,
            beneficiary_refs=["Arc XP", "FT Strategies", "WAN-IFRA"],
            requested_scope=[
                "future newsroom priorities",
                "AI adoption and operating-model barriers",
            ],
            omitted_scope=[
                "independent causal evaluation of governance interventions",
                "independent product effectiveness comparison",
            ],
            desired_outcome_disclosed=None,
            publication_controlled_by=None,
            conflict_disclosures=[
                "Arc XP support is publicly associated with the study",
            ],
            disclosure_complete=False,
        ),
        profile_asserted_by="baro-shadow-pilot",
        profile_verified_by="human-method-reviewer",
        profile_verified_at=now if human_review_completed else None,
        caveats=[
            "Use as industry context only until full report, survey instrument, raw distributions and support terms are archived and verified",
        ],
    )

    acquisition = AcquisitionEvidence(
        source_id=source_id,
        adapter_id="governed-newsroom.supplied-metadata",
        adapter_version="v1",
        endpoint_ref=STUDY_URL,
        operation_name="register_supplied_source_metadata",
        request_ref=_ref(
            "future-newsroom-study-registration-request",
            {"source_url": STUDY_URL, "purpose": "shadow-pilot"},
        ),
        raw_response_ref=acquisition_ref,
        raw_response_digest=acquisition_ref.digest,
        captured_at=now,
        derivation_mode=DerivationMode.RAW,
        limitations=[
            "The pilot binds supplied metadata and citations; the complete report PDF and survey materials must be archived separately",
        ],
    )

    funding_and_control = FundingAndControlProfile(
        source_id=source_id,
        commissioner_status=DisclosureStatus.UNKNOWN,
        payer_status=DisclosureStatus.PARTIAL,
        mandate_status=DisclosureStatus.PARTIAL,
        publication_control_status=DisclosureStatus.UNKNOWN,
        commissioner_refs=[],
        ultimate_funder_refs=["Arc XP: support disclosed, financial terms unknown"],
        producer_refs=["FT Strategies", "WAN-IFRA"],
        author_refs=["FT Strategies", "WAN-IFRA"],
        beneficiary_refs=["Arc XP", "FT Strategies", "WAN-IFRA"],
        affected_interest_refs=[
            "newsrooms considering AI transformation",
            "journalists and editors affected by AI workflow changes",
        ],
        requested_scope=[
            "future newsroom organization, production and audience priorities",
        ],
        omitted_scope=[
            "independent causal testing",
            "governance product comparison",
            "measured effect of execution-boundary controls",
        ],
        desired_outcome_disclosed=None,
        unresolved_questions=[
            "Who formally commissioned the study?",
            "What financial or in-kind support did Arc XP provide?",
            "Did any supporter hold edit, delay or veto rights?",
            "Was generative AI used in research, analysis, drafting, translation or graphics?",
            "Are the survey instrument, response distributions and non-response analysis available?",
        ],
    )

    content_origin = ContentOriginProfile(
        source_id=source_id,
        origin_kind=ContentOriginKind.UNKNOWN,
        disclosure_status=DisclosureStatus.UNKNOWN,
        production_stages=[
            ProductionStage.RESEARCH,
            ProductionStage.ANALYSIS,
            ProductionStage.DRAFTING,
            ProductionStage.EDITING,
            ProductionStage.DATA,
        ],
        root_source_refs=[source_id],
        primary_sources_verified=False,
        limitations=[
            "No AI-use declaration was present in the supplied metadata",
            "Unknown origin must not be converted into a positive AI-authorship claim",
        ],
    )

    actors = [
        InfluenceActor(
            actor_id="ft-strategies",
            role=InfluenceRole.PRODUCER,
            name="FT Strategies",
        ),
        InfluenceActor(
            actor_id="wan-ifra",
            role=InfluenceRole.PRODUCER,
            name="WAN-IFRA",
        ),
        InfluenceActor(
            actor_id="arc-xp",
            role=InfluenceRole.BENEFICIARY,
            name="Arc XP",
        ),
    ]
    study_support_ref = _ref(
        "future-newsroom-study-support-disclosure",
        {
            "study": "Future Newsrooms Study 2026",
            "supporter": "Arc XP",
            "financial_terms": "unknown",
        },
        reference=STUDY_URL,
    )
    influence_links = [
        InfluenceLink(
            from_actor_id="arc-xp",
            to_actor_id="ft-strategies",
            relationship="supported study production or distribution; exact terms unknown",
            evidence_level=RelationshipEvidenceLevel.DOCUMENTARY,
            evidence_refs=[study_support_ref],
            limitations=["Support disclosure does not establish editorial control"],
        ),
        InfluenceLink(
            from_actor_id="ft-strategies",
            to_actor_id="newsroom-market",
            relationship="offers transformation and advisory services relevant to the study topic",
            evidence_level=RelationshipEvidenceLevel.CORROBORATED_INFERENCE,
            unresolved=True,
            limitations=["Commercial relevance does not establish manipulation or falsity"],
        ),
    ]

    recruitment_ref = _ref(
        "future-newsroom-study-recruitment-note",
        {
            "reported_channels": [
                "email outreach",
                "LinkedIn promotion",
                "direct invitations",
            ],
            "risk": "network and self-selection bias",
        },
        reference=STUDY_URL,
    )
    commercial_context_ref = _ref(
        "future-newsroom-study-commercial-context",
        {
            "producer": "FT Strategies",
            "supporter": "Arc XP",
            "relevance": "both operate in markets affected by newsroom transformation and technology investment",
        },
        reference=STUDY_URL,
    )
    bias_signals = [
        BiasSignal(
            signal_id="bias-recruitment-self-selection",
            source_id=source_id,
            dimension=BiasDimension.SAMPLE,
            description=(
                "Recruitment through industry networks, email, LinkedIn and direct "
                "invitations can create network and self-selection bias"
            ),
            affected_claim_refs=[claim_id],
            evidence_level=RelationshipEvidenceLevel.DOCUMENTARY,
            evidence_refs=[recruitment_ref],
            counterevidence_refs=[],
            unresolved=True,
            limitations=[
                "The direction and magnitude of selection bias cannot be estimated without full sampling and response data",
            ],
        ),
        BiasSignal(
            signal_id="bias-commercial-interest",
            source_id=source_id,
            dimension=BiasDimension.COMMERCIAL_INTEREST,
            description=(
                "The producer and supporting technology vendor have legitimate "
                "commercial interests in newsroom transformation"
            ),
            affected_claim_refs=[claim_id],
            evidence_level=RelationshipEvidenceLevel.CORROBORATED_INFERENCE,
            evidence_refs=[commercial_context_ref],
            counterevidence_refs=[study_support_ref],
            unresolved=True,
            limitations=[
                "Commercial interest constrains use and review; it does not make the reported responses false",
            ],
        ),
    ]

    counterinterpretation_ref = _ref(
        "future-newsroom-study-counterinterpretation",
        {
            "interpretation": (
                "The reported barriers may partly reflect the networks and leaders "
                "most motivated to respond, rather than the full global newsroom population"
            ),
            "status": "credible alternative requiring sampling data",
        },
    )
    source_assessment = SourceIntegrityAssessment(
        source_id=source_id,
        acquisition=acquisition,
        funding_and_control=funding_and_control,
        content_origin=content_origin,
        influence_actors=actors,
        influence_links=influence_links,
        bias_signals=bias_signals,
        strongest_counterinterpretation_refs=[counterinterpretation_ref],
        unresolved_questions=funding_and_control.unresolved_questions,
        permissible_uses=[
            "industry-context",
            "market-signal",
        ],
        prohibited_uses=[
            "sole-basis-for-causal-claim",
            "sole-basis-for-product-effectiveness-claim",
            "sole-basis-for-autonomous-publication",
        ],
        assessed_by="baro-shadow-pilot",
        assessed_at=now,
    )

    purpose_ref = _ref(
        "future-newsroom-pilot-purpose",
        {
            "purpose": "evaluate report as market context for VALO Governed Newsroom",
            "not_purpose": [
                "prove VALO effectiveness",
                "prove causal newsroom outcomes",
                "authorize publication",
            ],
        },
    )
    case = VerificationCase(
        case_id=case_id,
        tenant_id="valo-research",
        purpose_ref=purpose_ref,
        owner_id="governed-newsroom-product-owner",
        intended_use="industry-context",
        consequence_class="material",
        artifact_refs=[acquisition_ref],
        created_at=now,
        updated_at=now,
    )

    claim_statement = (
        "The study provides an industry signal that important barriers to newsroom "
        "AI adoption are organizational, including skills, culture and unclear use cases."
    )
    claim = ClaimRecord(
        claim_id=claim_id,
        case_id=case_id,
        artifact_ref=acquisition_ref,
        statement_digest=canonical_digest(claim_statement),
        claim_kind=ClaimKind.INTERPRETATION,
        materiality=ClaimMateriality.HIGH,
        intended_uses=["industry-context", "market-signal"],
        prohibited_uses=[
            "causal-proof",
            "product-effectiveness-proof",
            "autonomous-publication-basis",
        ],
        source_refs=[source_id],
        required_evidence_types=["published-study", "methodology-disclosure"],
        required_independent_roots=1,
        primary_source_required=False,
        created_at=now,
    )

    evidence = [
        RealityEvidence(
            evidence_id="evidence-future-newsroom-study",
            case_id=case_id,
            claim_id=claim_id,
            source_id=source_id,
            evidence_type="published-industry-study",
            observation_ref=acquisition_ref,
            content_digest=acquisition_ref.digest,
            independence_group=source_profile.independence_group,
            captured_at=now,
            quality_flags=[
                "SELF_SELECTION_REVIEW",
                "COMMISSIONING_DISCLOSURE_INCOMPLETE",
                "AI_ORIGIN_UNKNOWN",
            ],
            unresolved=True,
        )
    ]

    policy_ref = _ref(
        "governed-newsroom-market-context-policy",
        {
            "policy": "market-context-v1",
            "required_independent_roots": 1,
            "primary_source_required": False,
            "human_review_for_material_use": True,
            "prohibited": [
                "causal proof from descriptive survey",
                "effectiveness claim without pilot evidence",
            ],
        },
    )
    work_order = VerificationWorkOrder(
        work_order_id="work-order-future-newsroom-study",
        case_id=case_id,
        claim_id=claim_id,
        policy_ref=policy_ref,
        required_verifier_ids=[
            "source_integrity.funding_control.v1",
            "source_integrity.sample_selection.v1",
            "source_integrity.ai_origin.v1",
            "report_integrity.causal_overreach.v1",
        ],
        required_evidence_types=["published-study", "methodology-disclosure"],
        required_independent_roots=1,
        primary_source_required=False,
        accountable_reviewer_roles=[
            "responsible-editor",
            "research-method-reviewer",
        ],
        timeout_seconds=300,
        escalation_route="editorial-source-integrity-review",
        permissible_uses=["industry-context", "market-signal"],
        prohibited_uses=[
            "causal-proof",
            "product-effectiveness-proof",
            "autonomous-publication-basis",
        ],
        created_at=now,
    )

    governance_inputs = NewsroomGovernanceInputs(
        sol_context_ref=_ref(
            "sol-newsroom-market-context",
            {
                "context": "VALO Governed Newsroom product and market assessment",
                "history": "Future Newsroom Study selected as first source-integrity shadow case",
            },
        ),
        mal_model_admissibility_ref=_ref(
            "mal-newsroom-pilot",
            {
                "allowed": ["deterministic parsing", "advisory semantic review"],
                "prohibited": ["autonomous publication", "AI-authorship allegation"],
                "status": "shadow-only",
            },
        ),
        proposed_artifact_ref=_ref(
            "future-newsroom-market-reference",
            {
                "claim": claim_statement,
                "required_disclosures": [
                    "industry survey",
                    "commercial support",
                    "sampling limitations",
                    "unknown AI origin",
                    "not causal proof",
                ],
            },
        ),
        publication_authority_ref=_ref(
            "future-newsroom-publication-authority",
            {
                "authority": "responsible editor",
                "mode": "shadow-only",
                "execution_authorized": False,
            },
        ),
        action_type=NewsroomActionType.RESEARCH_USE,
        risk_tier=NewsroomRiskTier.MATERIAL,
        accountable_editor_id="responsible-editor-shadow",
        human_review_completed=human_review_completed,
    )

    evaluation = evaluate_newsroom_shadow(
        case=case,
        source_profiles=[source_profile],
        source_integrity={source_id: source_assessment},
        claim=claim,
        evidence=evidence,
        work_order=work_order,
        governance_inputs=governance_inputs,
        now=now,
    )

    return FutureNewsroomPilotCase(
        case=case,
        source_profiles=[source_profile],
        source_integrity={source_id: source_assessment},
        claim=claim,
        evidence=evidence,
        work_order=work_order,
        governance_inputs=governance_inputs,
        evaluation=evaluation,
    )


__all__ = [
    "AUDIENCERS_URL",
    "STUDY_URL",
    "FutureNewsroomPilotCase",
    "build_future_newsroom_pilot",
]
