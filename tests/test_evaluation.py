from datetime import timedelta

import pytest

from valo_insurance_pack.contracts.assurance_profile import (
    AssuranceProfileV1,
    ConsequenceClass,
    EffectivePeriod,
    FailureOutcome,
)
from valo_insurance_pack.contracts.assurance_strength import AssuranceCapability
from valo_insurance_pack.contracts.evaluation import (
    AssuranceResult,
)
from valo_insurance_pack.contracts.source_evidence import (
    ChangedSinceStatus,
    RevocationVisibilityStatus,
    SourceAssuranceEvidenceV1,
)
from valo_insurance_pack.evaluation.evaluator import evaluate_commit_assurance
from valo_insurance_pack.utils.crypto import utcnow


@pytest.fixture
def base_profile():
    now = utcnow()
    return AssuranceProfileV1(
        profile_id="prof-procure-1",
        insurer_reference="carrier:test",
        coverage_condition_ref="cond-procure-1",
        action_type="PROCUREMENT_ORDER_CREATE",
        consequence_class=ConsequenceClass.HIGH,
        required_authoritative_sources=["entra_id", "erp_sap_budget"],
        freshness_requirements={"entra_id": 300, "erp_sap_budget": 300},
        revocation_visibility_requirements={"entra_id": "REALTIME_ACTIVE"},
        minimum_assurance_per_source={"entra_id": "OIDC_FIDO2_BOUND"},
        failure_outcome=FailureOutcome.STEP_UP,
        profile_version="1.0.0",
        effective_period=EffectivePeriod(
            effective_from=now - timedelta(days=1),
            effective_until=now + timedelta(days=365),
        ),
    )


def test_evaluate_commit_assurance_satisfied(base_profile):
    now = utcnow()
    action = {
        "action_type": "PROCUREMENT_ORDER_CREATE",
        "target": "erp:sap/po/create",
        "parameters": {"po_number": "PO-101", "amount": 5000},
    }
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=20),
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-4001",
            observed_at=now - timedelta(seconds=40),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]
    res = evaluate_commit_assurance(
        profile=base_profile,
        action=action,
        source_evidences=sources,
        now=now,
    )
    assert res.is_satisfied
    assert res.assurance_result == AssuranceResult.SATISFIED
    assert len(res.unmet_requirements) == 0


def test_evaluate_commit_assurance_missing_source(base_profile):
    now = utcnow()
    action = {"action_type": "PROCUREMENT_ORDER_CREATE"}
    # Only entra_id provided, erp_sap_budget missing
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=20),
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        )
    ]
    res = evaluate_commit_assurance(
        profile=base_profile,
        action=action,
        source_evidences=sources,
        now=now,
    )
    assert not res.is_satisfied
    assert res.assurance_result == AssuranceResult.STEP_UP_REQUIRED
    assert any("missing_required_source" in u for u in res.unmet_requirements)


def test_evaluate_commit_assurance_unknown_observability_fails_closed(base_profile):
    """P0 test: Evidence with default UNKNOWN status fails closed."""
    now = utcnow()
    action = {"action_type": "PROCUREMENT_ORDER_CREATE"}
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=20),
            attestation_type="OIDC_FIDO2_BOUND",
            # Defaults to UNKNOWN for revocation and continuity
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-4001",
            observed_at=now - timedelta(seconds=20),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]
    res = evaluate_commit_assurance(
        profile=base_profile,
        action=action,
        source_evidences=sources,
        now=now,
    )
    assert not res.is_satisfied
    assert any(
        "revoked_or_unverified_evidence" in u or "evidence_unconfirmed_or_drifted" in u
        for u in res.unmet_requirements
    )


def test_evaluate_commit_assurance_stale_evidence(base_profile):
    now = utcnow()
    action = {"action_type": "PROCUREMENT_ORDER_CREATE"}
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=500),  # Stale (> 300s)
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-4001",
            observed_at=now - timedelta(seconds=20),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]
    res = evaluate_commit_assurance(
        profile=base_profile,
        action=action,
        source_evidences=sources,
        now=now,
    )
    assert not res.is_satisfied
    assert any("stale_evidence" in u for u in res.unmet_requirements)


def test_evaluate_commit_assurance_revoked_evidence(base_profile):
    now = utcnow()
    action = {"action_type": "PROCUREMENT_ORDER_CREATE"}
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=20),
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.REVOKED,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-4001",
            observed_at=now - timedelta(seconds=20),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]
    res = evaluate_commit_assurance(
        profile=base_profile,
        action=action,
        source_evidences=sources,
        now=now,
    )
    assert not res.is_satisfied
    assert any("revoked_or_unverified_evidence" in u for u in res.unmet_requirements)


def test_evaluate_commit_assurance_duplicate_source_rejected(base_profile):
    """P1 test: two evidence records for the same source are rejected, not silently deduped."""
    now = utcnow()
    action = {"action_type": "PROCUREMENT_ORDER_CREATE"}
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=20),
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=20),
            attestation_type="OIDC_HARDWARE_MFA",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
    ]
    with pytest.raises(ValueError, match="duplicate source evidence"):
        evaluate_commit_assurance(
            profile=base_profile,
            action=action,
            source_evidences=sources,
            now=now,
        )


def test_evaluate_commit_assurance_evidence_drift(base_profile):
    now = utcnow()
    action = {"action_type": "PROCUREMENT_ORDER_CREATE"}
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=20),
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-4001",
            observed_at=now - timedelta(seconds=20),
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.CHANGED,
        ),
    ]
    res = evaluate_commit_assurance(
        profile=base_profile,
        action=action,
        source_evidences=sources,
        now=now,
    )
    assert not res.is_satisfied
    assert any("evidence_drift_or_unconfirmed" in u for u in res.unmet_requirements)


def test_evaluate_commit_assurance_stronger_meets_weaker_minimum():
    """P1 test: capability-superset mechanism satisfies weaker minimum without any REHT change."""
    now = utcnow()
    profile = AssuranceProfileV1(
        profile_id="prof-hierarchical",
        insurer_reference="carrier:test",
        coverage_condition_ref="cond-1",
        action_type="PO_CREATE",
        consequence_class=ConsequenceClass.HIGH,
        required_authoritative_sources=["compliance_gate"],
        minimum_assurance_per_source={"compliance_gate": "VERSION_PINNED"},
        failure_outcome=FailureOutcome.DENY,
        effective_period=EffectivePeriod(
            effective_from=now - timedelta(days=1),
            effective_until=now + timedelta(days=365),
        ),
    )
    # EVENT_STREAM_CURSOR has a strict superset of VERSION_PINNED's capabilities
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="compliance_gate",
            subject="audit:901",
            observed_at=now,
            attestation_type="EVENT_STREAM_CURSOR",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        )
    ]
    res = evaluate_commit_assurance(
        profile=profile,
        action={"action_type": "PO_CREATE"},
        source_evidences=sources,
        now=now,
    )
    assert res.is_satisfied


def test_evaluate_commit_assurance_cross_property_mechanism_fails_closed():
    """P1 test: FOUR_EYES proves dual control, not version pinning -> fails closed."""
    now = utcnow()
    profile = AssuranceProfileV1(
        profile_id="prof-cross-property",
        insurer_reference="carrier:test",
        coverage_condition_ref="cond-1",
        action_type="PO_CREATE",
        consequence_class=ConsequenceClass.HIGH,
        required_authoritative_sources=["compliance_gate"],
        minimum_assurance_per_source={"compliance_gate": "VERSION_PINNED"},
        failure_outcome=FailureOutcome.DENY,
        effective_period=EffectivePeriod(
            effective_from=now - timedelta(days=1),
            effective_until=now + timedelta(days=365),
        ),
    )
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="compliance_gate",
            subject="audit:901",
            observed_at=now,
            attestation_type="FOUR_EYES_ATTESTATION",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        )
    ]
    res = evaluate_commit_assurance(
        profile=profile,
        action={"action_type": "PO_CREATE"},
        source_evidences=sources,
        now=now,
    )
    assert not res.is_satisfied
    assert any(
        "insufficient_assurance_capabilities" in u
        for u in res.unmet_requirements
    )


def test_evaluate_commit_assurance_explicit_capability_set_requirement():
    """P1 test: profile requires an explicit capability set, satisfied only by superset."""
    now = utcnow()
    profile = AssuranceProfileV1(
        profile_id="prof-cap-set",
        insurer_reference="carrier:test",
        coverage_condition_ref="cond-1",
        action_type="PO_CREATE",
        consequence_class=ConsequenceClass.HIGH,
        required_authoritative_sources=["compliance_gate"],
        required_capabilities_per_source={
            "compliance_gate": [
                AssuranceCapability.FRESHNESS_OBSERVED,
                AssuranceCapability.CHANGE_VISIBILITY,
            ]
        },
        failure_outcome=FailureOutcome.DENY,
        effective_period=EffectivePeriod(
            effective_from=now - timedelta(days=1),
            effective_until=now + timedelta(days=365),
        ),
    )

    def evidence(attestation: str, **extra):
        return SourceAssuranceEvidenceV1(
            source_id="compliance_gate",
            subject="audit:901",
            observed_at=now,
            attestation_type=attestation,
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            **extra,
        )

    # BASIC_TIMESTAMP lacks change visibility -> unmet
    res = evaluate_commit_assurance(
        profile=profile,
        action={"action_type": "PO_CREATE"},
        source_evidences=[evidence("BASIC_TIMESTAMP")],
        now=now,
    )
    assert not res.is_satisfied

    # EVENT_STREAM_CURSOR covers both required capabilities -> satisfied
    res = evaluate_commit_assurance(
        profile=profile,
        action={"action_type": "PO_CREATE"},
        source_evidences=[evidence("EVENT_STREAM_CURSOR")],
        now=now,
    )
    assert res.is_satisfied

    # Combination: FIDO2 + event continuity jointly cover the requirement
    res = evaluate_commit_assurance(
        profile=profile,
        action={"action_type": "PO_CREATE"},
        source_evidences=[
            evidence(
                "OIDC_FIDO2_BOUND",
                provenance={"strength": "EVENT_STREAM_CURSOR"},
            )
        ],
        now=now,
    )
    assert res.is_satisfied
