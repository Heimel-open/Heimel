from __future__ import annotations

from datetime import UTC, datetime

from ..contracts.assurance_profile import (
    AssuranceProfileV1,
    ConsequenceClass,
    EffectivePeriod,
    FailureOutcome,
)

_EFFECTIVE_START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_EFFECTIVE_END = datetime(2028, 1, 1, 0, 0, 0, tzinfo=UTC)

PROCUREMENT_STANDARD = AssuranceProfileV1(
    profile_id="carrier-profile-procurement-standard-v1",
    insurer_reference="insurer:munich-re-autonomous-systems:2026",
    coverage_condition_ref="cond-procurement-std-v1",
    action_type="PROCUREMENT_ORDER_CREATE",
    consequence_class=ConsequenceClass.MEDIUM,
    required_authoritative_sources=["entra_id", "erp_sap_budget"],
    minimum_assurance_per_source={
        "entra_id": "OIDC_HARDWARE_MFA",
        "erp_sap_budget": "ERP_AUTHORITATIVE_API",
    },
    freshness_requirements={
        "entra_id": 3600,
        "erp_sap_budget": 1800,
    },
    revocation_visibility_requirements={
        "entra_id": "ONLINE_STATUS_CHECK",
        "erp_sap_budget": "TRANSACTION_CONSISTENT",
    },
    failure_outcome=FailureOutcome.DEFER,
    profile_version="1.0.0",
    effective_period=EffectivePeriod(
        effective_from=_EFFECTIVE_START,
        effective_until=_EFFECTIVE_END,
    ),
    metadata={
        "tier": "standard",
        "max_exposure_usd": 10000,
        "underwriting_pool": "standard-commercial-ops",
    },
)

PROCUREMENT_HIGH_VALUE = AssuranceProfileV1(
    profile_id="carrier-profile-procurement-high-value-v1",
    insurer_reference="insurer:swiss-re-agentic-liability:2026",
    coverage_condition_ref="cond-procurement-high-value-v1",
    action_type="PROCUREMENT_ORDER_CREATE",
    consequence_class=ConsequenceClass.HIGH,
    required_authoritative_sources=["entra_id", "erp_sap_budget", "erp_sap_po_state"],
    minimum_assurance_per_source={
        "entra_id": "OIDC_FIDO2_BOUND",
        "erp_sap_budget": "ERP_AUTHORITATIVE_API",
        "erp_sap_po_state": "ERP_COMMITTED_STATE",
    },
    freshness_requirements={
        "entra_id": 300,
        "erp_sap_budget": 300,
        "erp_sap_po_state": 120,
    },
    revocation_visibility_requirements={
        "entra_id": "REALTIME_ACTIVE",
        "erp_sap_budget": "TRANSACTION_CONSISTENT",
        "erp_sap_po_state": "VERSION_PINNED",
    },
    failure_outcome=FailureOutcome.STEP_UP,
    profile_version="1.0.0",
    effective_period=EffectivePeriod(
        effective_from=_EFFECTIVE_START,
        effective_until=_EFFECTIVE_END,
    ),
    metadata={
        "tier": "high_value",
        "max_exposure_usd": 500000,
        "underwriting_pool": "high-value-procurement-liability",
    },
)

PROCUREMENT_HIGH_RISK = AssuranceProfileV1(
    profile_id="carrier-profile-procurement-high-risk-v1",
    insurer_reference="insurer:lloyds-autonomous-underwriting:2026",
    coverage_condition_ref="cond-procurement-high-risk-v1",
    action_type="PROCUREMENT_ORDER_CREATE",
    consequence_class=ConsequenceClass.CRITICAL,
    required_authoritative_sources=[
        "entra_id",
        "erp_sap_budget",
        "erp_sap_po_state",
        "compliance_dual_control",
    ],
    minimum_assurance_per_source={
        "entra_id": "OIDC_FIDO2_BOUND",
        "erp_sap_budget": "ERP_AUTHORITATIVE_API",
        "erp_sap_po_state": "VERSION_PINNED",
        "compliance_dual_control": "FOUR_EYES_ATTESTATION",
    },
    freshness_requirements={
        "entra_id": 60,
        "erp_sap_budget": 60,
        "erp_sap_po_state": 60,
        "compliance_dual_control": 120,
    },
    revocation_visibility_requirements={
        "entra_id": "REALTIME_ACTIVE",
        "erp_sap_budget": "TRANSACTION_CONSISTENT",
        "erp_sap_po_state": "EVENT_STREAM_CURSOR",
        "compliance_dual_control": "CRYPTOGRAPHIC_SIGN_OFF",
    },
    failure_outcome=FailureOutcome.DENY,
    profile_version="1.0.0",
    effective_period=EffectivePeriod(
        effective_from=_EFFECTIVE_START,
        effective_until=_EFFECTIVE_END,
    ),
    metadata={
        "tier": "critical_high_risk",
        "max_exposure_usd": 10000000,
        "underwriting_pool": "critical-risk-syndicate",
    },
)

REFERENCE_PROFILES = {
    "PROCUREMENT_STANDARD": PROCUREMENT_STANDARD,
    "PROCUREMENT_HIGH_VALUE": PROCUREMENT_HIGH_VALUE,
    "PROCUREMENT_HIGH_RISK": PROCUREMENT_HIGH_RISK,
}
