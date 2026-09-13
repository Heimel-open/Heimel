import pytest

from vaig.analytic_tradecraft import (
    AnalyticTradecraftGate,
    AnalyticTradecraftInputError,
    AssumptionStatus,
    ClaimCredibility,
    EvidenceDisposition,
    EvidenceItem,
    ExpectedObservation,
    KeyAssumption,
    PurposeRisk,
    TradecraftState,
    evidence_item_from_package,
)
from vaig.evidence_intake import (
    EvidenceIntakeState,
    EvidencePackageBinding,
    VersionedArtifactRef,
)
from vaig.epistemic_underdetermination import AlternativeHypothesis


def alternative(alternative_id, viable=True):
    return AlternativeHypothesis(
        alternative_id=alternative_id,
        claim="Explanation {}".format(alternative_id),
        viable=viable,
    )


def _digest(seed):
    return "sha256:" + seed * 64


def package(
    package_id="pkg1",
    case_id="case1",
    version="1",
    digest=None,
    invalidated_at=None,
):
    return EvidencePackageBinding(
        package_id=package_id,
        case_id=case_id,
        package_version=version,
        package_digest=digest or _digest("a"),
        admissibility_refs=(
            VersionedArtifactRef(
                artifact_id="claim1",
                version="1",
                reference="claim:claim1:1",
                digest=_digest("b"),
            ),
        ),
        invalidated_at=invalidated_at,
        invalidation_ref=(
            VersionedArtifactRef(
                artifact_id="invalidation1",
                version="1",
                reference="invalidation:invalidation1:1",
                digest=_digest("c"),
            )
            if invalidated_at is not None
            else None
        ),
    )


def evidence(
    evidence_id,
    *,
    supports=(),
    contradicts=(),
    provenance_known=True,
    first_appearance_identifiable=True,
    manipulation_suspected=False,
    credibility=ClaimCredibility.MEDIUM,
    corroboration=1,
    purpose_risk=PurposeRisk.LOW,
    package_ref=None,
    intake_state=None,
):
    if package_ref is not None:
        return evidence_item_from_package(
            evidence_id=evidence_id,
            claim="Claim {}".format(evidence_id),
            package=package_ref,
            intake_state=intake_state,
            claim_credibility=credibility,
            purpose_risk=purpose_risk,
            supports_hypotheses=tuple(supports),
            contradicts_hypotheses=tuple(contradicts),
        )
    return EvidenceItem(
        evidence_id=evidence_id,
        claim="Claim {}".format(evidence_id),
        provenance_known=provenance_known,
        first_appearance_identifiable=first_appearance_identifiable,
        manipulation_suspected=manipulation_suspected,
        claim_credibility=credibility,
        independent_corroboration_count=corroboration,
        purpose_risk=purpose_risk,
        supports_hypotheses=tuple(supports),
        contradicts_hypotheses=tuple(contradicts),
    )


def test_unknown_provenance_is_discarded_and_no_citable_evidence_fails_closed():
    result = AnalyticTradecraftGate().assess(
        evidence=(
            evidence(
                "e1",
                supports=("h1",),
                provenance_known=False,
            ),
        ),
        alternatives=(alternative("h1"),),
    )

    assert result.state == TradecraftState.INSUFFICIENT
    assert result.evidence[0].disposition == EvidenceDisposition.DISCARD
    assert result.blocks_consequential_action is True
    assert result.requires_human_review is True
    assert result.execution_authority is False
    assert result.requires_reht_clearance is True


def test_uncorroborated_or_high_influence_risk_evidence_is_background_only():
    result = AnalyticTradecraftGate().assess(
        evidence=(
            evidence("e1", supports=("h1",), corroboration=0),
            evidence(
                "e2",
                supports=("h1",),
                purpose_risk=PurposeRisk.HIGH,
            ),
        ),
        alternatives=(alternative("h1"),),
    )

    assert result.state == TradecraftState.INSUFFICIENT
    assert [item.disposition for item in result.evidence] == [
        EvidenceDisposition.BACKGROUND,
        EvidenceDisposition.BACKGROUND,
    ]


def test_ach_ranking_selects_the_uniquely_least_contradicted_hypothesis():
    result = AnalyticTradecraftGate().assess(
        evidence=(
            evidence("e1", supports=("h2",), contradicts=("h1",)),
            evidence("e2", supports=("h2",)),
        ),
        alternatives=(alternative("h1"), alternative("h2")),
    )

    assert result.state == TradecraftState.SUFFICIENT
    assert result.least_contradicted_hypotheses == ("h2",)
    assert result.discriminating_evidence_refs == ("e1", "e2")
    assert result.hypotheses[0].contradiction_count == 1
    assert result.hypotheses[1].contradiction_count == 0


def test_equal_least_contradicted_hypotheses_remain_constrained():
    result = AnalyticTradecraftGate().assess(
        evidence=(
            evidence("e1", supports=("h1", "h2")),
        ),
        alternatives=(alternative("h1"), alternative("h2")),
    )

    assert result.state == TradecraftState.CONSTRAINED
    assert result.least_contradicted_hypotheses == ("h1", "h2")
    assert result.requires_human_review is True
    assert result.blocks_consequential_action is False


def test_unsupported_collapse_assumption_blocks_high_consequence_case():
    # High-consequence evaluation requires an upstream EvidencePackage binding
    # (#141): use evidence_item_from_package so the consequential path is taken.
    result = AnalyticTradecraftGate().assess(
        evidence=(
            evidence(
                "e1",
                supports=("h1",),
                package_ref=package(),
            ),
        ),
        alternatives=(alternative("h1"),),
        assumptions=(
            KeyAssumption(
                assumption_id="a1",
                statement="The source clock is correctly synchronized.",
                supporting_evidence_refs=("missing",),
                collapse_if_false=True,
            ),
        ),
        high_consequence=True,
    )

    assert result.state == TradecraftState.INSUFFICIENT
    assert result.assumptions[0].status == AssumptionStatus.HIGH_RISK
    assert result.blocks_consequential_action is True


def test_high_consequence_without_package_binding_fails_closed():
    # #141.7: an exact upstream EvidencePackage binding is mandatory for
    # consequential evaluation; locally-asserted source truth is not enough.
    result = AnalyticTradecraftGate().assess(
        evidence=(evidence("e1", supports=("h1",)),),
        alternatives=(alternative("h1"),),
        high_consequence=True,
    )
    assert result.state == TradecraftState.INSUFFICIENT
    assert result.blocks_consequential_action is True
    assert any(
        "EvidencePackage binding" in r for r in result.rationale
    )


def test_invalidated_package_is_discarded_fail_closed():
    from datetime import datetime, timezone

    pkg = package(invalidated_at=datetime(2026, 8, 1, tzinfo=timezone.utc))
    result = AnalyticTradecraftGate().assess(
        evidence=(evidence("e1", supports=("h1",), package_ref=pkg),),
        alternatives=(alternative("h1"),),
    )
    assert result.evidence[0].disposition == EvidenceDisposition.DISCARD
    assert result.evidence[0].package_binding_key == ("pkg1", "1", _digest("a"))


def test_stale_or_unverified_intake_state_is_discarded():
    for state in (
        EvidenceIntakeState.STALE,
        EvidenceIntakeState.UNVERIFIED,
        EvidenceIntakeState.MISMATCHED,
        EvidenceIntakeState.INVALIDATED,
    ):
        result = AnalyticTradecraftGate().assess(
            evidence=(
                evidence(
                    "e1",
                    supports=("h1",),
                    package_ref=package(),
                    intake_state=state,
                ),
            ),
            alternatives=(alternative("h1"),),
        )
        assert result.evidence[0].disposition == EvidenceDisposition.DISCARD, state


def test_admissible_package_is_cited_and_binds_exact_ref():
    result = AnalyticTradecraftGate().assess(
        evidence=(evidence("e1", supports=("h1",), package_ref=package()),),
        alternatives=(alternative("h1"),),
    )
    assert result.evidence[0].disposition == EvidenceDisposition.CITE
    assert result.evidence[0].package_binding_key == ("pkg1", "1", _digest("a"))
    # Exact ref is surfaced in serialized assessment (#141.8 readiness).
    serialized: dict = dict(result.to_dict())
    assert serialized["evidence"][0]["package_binding_key"] == [
        "pkg1", "1", _digest("a"),
    ]


def test_missing_expected_observation_is_explicit_and_constrained():
    result = AnalyticTradecraftGate().assess(
        evidence=(evidence("e1", supports=("h1",)),),
        alternatives=(alternative("h1"),),
        expected_observations=(
            ExpectedObservation(
                observation_id="o1",
                description="A signed callback record should exist.",
                hypothesis_ids=("h1",),
                observed=False,
            ),
        ),
    )

    assert result.state == TradecraftState.CONSTRAINED
    assert result.missing_expected_observations == ("o1",)


def test_unknown_hypothesis_reference_fails_closed():
    with pytest.raises(AnalyticTradecraftInputError, match="Unknown hypothesis"):
        AnalyticTradecraftGate().assess(
            evidence=(evidence("e1", supports=("unknown",)),),
            alternatives=(alternative("h1"),),
        )


def test_serialization_preserves_authority_boundary():
    result = AnalyticTradecraftGate().assess(
        evidence=(evidence("e1", supports=("h1",)),),
        alternatives=(alternative("h1"),),
    ).to_dict()

    assert result["state"] == "SUFFICIENT"
    assert result["execution_authority"] is False
    assert result["requires_reht_clearance"] is True
