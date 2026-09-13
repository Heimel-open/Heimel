"""Tests for CSRD/ESRS Slice 5 evidence quality (VAIG, #1492)."""

from __future__ import annotations

from vaig.sustainability import (
    CalculationReproducibility,
    EvidenceQualityEvaluator,
    EvidenceQualityState,
    GreenwashingRisk,
    GreenwashingRiskEvaluator,
)


def test_sufficient_evidence_passes():
    e = EvidenceQualityEvaluator()
    state = e.evaluate(has_source=True, has_source_digest=True, missing_critical_sources=[],
                       conflicts=[], has_method=True, has_owner=True)
    assert state == EvidenceQualityState.SUFFICIENT
    assert e.can_pass_gate(state) is True


def test_missing_critical_source_cannot_pass():
    e = EvidenceQualityEvaluator()
    state = e.evaluate(has_source=True, has_source_digest=True,
                       missing_critical_sources=["scope-3"], conflicts=[],
                       has_method=True, has_owner=True)
    assert state == EvidenceQualityState.INSUFFICIENT
    assert e.can_pass_gate(state) is False


def test_conflicting_evidence():
    e = EvidenceQualityEvaluator()
    state = e.evaluate(has_source=True, has_source_digest=True, missing_critical_sources=[],
                       conflicts=["c1"], has_method=True, has_owner=True)
    assert state == EvidenceQualityState.CONFLICTING


def test_underdetermined_without_digest():
    e = EvidenceQualityEvaluator()
    state = e.evaluate(has_source=True, has_source_digest=False, missing_critical_sources=[],
                       conflicts=[], has_method=True, has_owner=True)
    assert state == EvidenceQualityState.UNDERDETERMINED


def test_constrained_without_method_or_owner():
    e = EvidenceQualityEvaluator()
    state = e.evaluate(has_source=True, has_source_digest=True, missing_critical_sources=[],
                       conflicts=[], has_method=False, has_owner=True)
    assert state == EvidenceQualityState.CONSTRAINED


def test_no_compliant_output():
    e = EvidenceQualityEvaluator()
    cases = [
        {
            "has_source": True, "has_source_digest": True, "missing_critical_sources": [],
            "conflicts": [], "has_method": True, "has_owner": True,
        },
        {
            "has_source": False, "has_source_digest": False, "missing_critical_sources": [],
            "conflicts": [], "has_method": False, "has_owner": False,
        },
    ]
    for kwargs in cases:
        assert e.evaluate(**kwargs).value != "COMPLIANT"


def test_calculation_reproducibility():
    r = CalculationReproducibility()
    assert r.evaluate(has_recipe=True, has_inputs=True, method_version_matches=True, factors_match=True) == EvidenceQualityState.SUFFICIENT
    assert r.evaluate(has_recipe=True, has_inputs=True, method_version_matches=False, factors_match=True) == EvidenceQualityState.CONSTRAINED
    assert r.evaluate(has_recipe=False, has_inputs=True, method_version_matches=True, factors_match=True) == EvidenceQualityState.UNDERDETERMINED


def test_greenwashing_risk():
    g = GreenwashingRiskEvaluator()
    assert g.evaluate(claims_compliance=True, has_external_assurance=False, source_backs_claim=True) == GreenwashingRisk.HIGH
    assert g.evaluate(claims_compliance=False, has_external_assurance=False, source_backs_claim=True) == GreenwashingRisk.LOW
    assert g.evaluate(claims_compliance=False, has_external_assurance=False, source_backs_claim=False) == GreenwashingRisk.MEDIUM
