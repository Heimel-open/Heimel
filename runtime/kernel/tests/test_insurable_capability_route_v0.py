from __future__ import annotations

import pytest

from valo_kernel.contracts.common import canonical_digest
from valo_kernel.kernel.insurable_route import (
    InsurabilityOutcome,
    RiskBand,
    assess_insurable_route,
    seal_insurable_route_evidence,
)


def _evidence(**overrides: object):
    values: dict[str, object] = {
        "route_evidence_digest": canonical_digest({"route": "PASS"}),
        "route_passed": True,
        "reht_evaluation_id": "reht-test-1",
        "consequence_authorized": True,
        "authority_fresh_at_consequence": True,
        "receipt_digest": canonical_digest({"receipt": "verified"}),
        "receipt_verified": True,
        "consequence_limit_minor_units": 50_000,
        "provider_trust_domain": "external",
        "execution_replayable": True,
        "state_integrity_verified": True,
    }
    values.update(overrides)
    return seal_insurable_route_evidence(**values)


def test_external_route_produces_deterministic_risk_signal() -> None:
    assessment = assess_insurable_route(_evidence())
    assert assessment.outcome is InsurabilityOutcome.ASSESSABLE
    assert assessment.risk_band is RiskBand.LOW
    assert assessment.risk_score == 15
    assert assessment.risk_factors == ("EXTERNAL_PROVIDER",)


def test_stale_authority_is_not_assessable() -> None:
    assessment = assess_insurable_route(
        _evidence(authority_fresh_at_consequence=False)
    )
    assert assessment.outcome is InsurabilityOutcome.NOT_ASSESSABLE
    assert assessment.risk_band is RiskBand.UNPRICED
    assert assessment.risk_score is None
    assert "AUTHORITY_NOT_FRESH" in assessment.blockers


def test_unbounded_consequence_is_not_assessable() -> None:
    assessment = assess_insurable_route(
        _evidence(consequence_limit_minor_units=None)
    )
    assert assessment.outcome is InsurabilityOutcome.NOT_ASSESSABLE
    assert "CONSEQUENCE_UNBOUNDED" in assessment.blockers


def test_tampered_evidence_fails_closed() -> None:
    evidence = _evidence()
    tampered = evidence.model_copy(update={"route_passed": False})
    with pytest.raises(ValueError, match="unsealed or tampered"):
        assess_insurable_route(tampered)
