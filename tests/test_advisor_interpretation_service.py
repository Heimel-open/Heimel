import pytest

from src.valo_platform.advisor_fabric import (
    AdvisorAuthorityBoundary,
    AdvisorConsentBasis,
    AdvisorContextGateway,
    AdvisorContextPackage,
    AdvisorContextRef,
    AdvisorContextScope,
    AdvisorInterpretationService,
    AdvisorMemoryPolicy,
    AdvisorMemoryRef,
    AdvisorRecommendationType,
)


def _package() -> AdvisorContextPackage:
    return AdvisorContextGateway().build_package(
        package_id="pkg-interpret-1",
        role="cfo",
        context_refs=[
            AdvisorContextRef(
                ref_id="ctx-1",
                source_type="scout_signal",
                scope=AdvisorContextScope.TENANT,
                consent_basis=AdvisorConsentBasis.CUSTOMER_CONSENT,
                source_ref="scout:signal:spend-drift",
                evidence_refs=["evidence:spend-drift"],
            ),
            AdvisorContextRef(
                ref_id="ctx-2",
                source_type="baro_evidence",
                scope=AdvisorContextScope.TENANT,
                consent_basis=AdvisorConsentBasis.INTERNAL_OPERATIONAL,
                source_ref="baro:evidence:renewals",
                evidence_refs=["evidence:renewals", "evidence:spend-drift"],
            ),
        ],
        memory_refs=[
            AdvisorMemoryRef(
                ref_id="mem-1",
                scope=AdvisorContextScope.TENANT,
                memory_policy=AdvisorMemoryPolicy.TENANT_SCOPED,
                source_ref="enterprise-memory:cfo",
                evidence_refs=["memory:budget-history"],
            )
        ],
        limitations=["Historical budget memory is incomplete."],
    )


def test_interpretation_collects_evidence_and_lineage() -> None:
    interpretation = AdvisorInterpretationService().interpret(
        interpretation_id="interp-cfo-1",
        context_package=_package(),
        stance="Spend drift appears concentrated in renewal-heavy vendors.",
        confidence=0.74,
        limitations=["Supplier categories need normalization."],
        questions_for_human=["Should committed but unsigned renewals be included?"],
    )

    assert interpretation.advisor_id == "advisor-cfo"
    assert interpretation.lineage_id == "pkg-interpret-1"
    assert interpretation.source_evidence_refs == [
        "evidence:spend-drift",
        "evidence:renewals",
        "memory:budget-history",
    ]
    assert interpretation.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY
    assert "Historical budget memory is incomplete." in interpretation.limitations


def test_briefing_recommendation_is_non_binding() -> None:
    service = AdvisorInterpretationService()
    interpretation = service.interpret(
        interpretation_id="interp-cfo-2",
        context_package=_package(),
        stance="Budget exposure needs review.",
        confidence=0.68,
    )

    briefing = service.briefing(
        recommendation_id="brief-cfo-1",
        interpretation=interpretation,
        statement="Review vendor renewal concentration before next budget lock.",
        rationale="The same evidence appears in Scout and BARO context.",
        risk_notes=["This is not an approval, denial or clearance."],
    )

    assert briefing.recommendation_type == AdvisorRecommendationType.BRIEFING
    assert briefing.requires_action_case is False
    assert briefing.source_interpretation_refs == ["interp-cfo-2"]
    assert briefing.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY


def test_interpretation_rejects_mismatched_profile_package() -> None:
    package = _package().model_copy(update={"advisor_id": "advisor-ciso"})

    with pytest.raises(ValueError, match="advisor does not match registered profile"):
        AdvisorInterpretationService().interpret(
            interpretation_id="interp-bad",
            context_package=package,
            stance="Mismatched package.",
            confidence=0.5,
        )


def test_interpretation_service_does_not_expose_execution_authority_fields() -> None:
    interpretation = AdvisorInterpretationService().interpret(
        interpretation_id="interp-cfo-3",
        context_package=_package(),
        stance="Advisory-only stance.",
        confidence=0.5,
    )
    dumped = interpretation.model_dump()

    for forbidden in (
        "clearance_id",
        "permit_id",
        "decision",
        "authorized",
        "can_execute",
        "allowed_to_execute",
        "execution_authorized",
    ):
        assert forbidden not in dumped
