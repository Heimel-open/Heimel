from datetime import UTC, datetime

from valo_insurance_pack.contracts.assurance_profile import (
    ConsequenceClass,
    FailureOutcome,
)
from valo_insurance_pack.profiles.carrier_examples import (
    PROCUREMENT_HIGH_RISK,
    PROCUREMENT_HIGH_VALUE,
    PROCUREMENT_STANDARD,
    REFERENCE_PROFILES,
)


def test_standard_procurement_profile():
    p = PROCUREMENT_STANDARD
    assert p.profile_id == "carrier-profile-procurement-standard-v1"
    assert p.consequence_class == ConsequenceClass.MEDIUM
    assert p.failure_outcome == FailureOutcome.DEFER
    assert "entra_id" in p.required_authoritative_sources
    assert "erp_sap_budget" in p.required_authoritative_sources
    assert p.freshness_requirements["entra_id"] == 3600
    assert p.is_effective(datetime(2026, 6, 1, tzinfo=UTC))


def test_high_value_procurement_profile():
    p = PROCUREMENT_HIGH_VALUE
    assert p.profile_id == "carrier-profile-procurement-high-value-v1"
    assert p.consequence_class == ConsequenceClass.HIGH
    assert p.failure_outcome == FailureOutcome.STEP_UP
    assert set(p.required_authoritative_sources) == {
        "entra_id",
        "erp_sap_budget",
        "erp_sap_po_state",
    }
    assert p.freshness_requirements["erp_sap_po_state"] == 120


def test_high_risk_procurement_profile():
    p = PROCUREMENT_HIGH_RISK
    assert p.profile_id == "carrier-profile-procurement-high-risk-v1"
    assert p.consequence_class == ConsequenceClass.CRITICAL
    assert p.failure_outcome == FailureOutcome.DENY
    assert "compliance_dual_control" in p.required_authoritative_sources
    assert p.freshness_requirements["entra_id"] == 60


def test_reference_profiles_registry():
    assert len(REFERENCE_PROFILES) == 3
    for prof in REFERENCE_PROFILES.values():
        assert prof.digest.startswith("sha256:")
