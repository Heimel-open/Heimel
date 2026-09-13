from datetime import timedelta

import pytest

from valo_insurance_pack.contracts.assurance_profile import (
    AssuranceProfileV1,
    ConsequenceClass,
    EffectivePeriod,
    FailureOutcome,
)
from valo_insurance_pack.contracts.assurance_strength import (
    AssuranceCapability,
    is_assurance_strength_satisfied,
    resolve_capabilities,
    resolve_evidence_capabilities,
)
from valo_insurance_pack.contracts.evaluation import (
    AssuranceResult,
    CommitAssuranceEvaluationV1,
)
from valo_insurance_pack.contracts.policy_binding import PolicyBindingV1
from valo_insurance_pack.contracts.source_evidence import (
    ChangedSinceStatus,
    RevocationVisibilityStatus,
    SourceAssuranceEvidenceV1,
)
from valo_insurance_pack.utils.crypto import utcnow


def test_assurance_profile_lifecycle():
    now = utcnow()
    period = EffectivePeriod(
        effective_from=now - timedelta(days=1),
        effective_until=now + timedelta(days=365),
    )
    profile = AssuranceProfileV1(
        profile_id="prof-1",
        insurer_reference="carrier:test",
        coverage_condition_ref="cond-1",
        action_type="PO_CREATE",
        consequence_class=ConsequenceClass.HIGH,
        required_authoritative_sources=["entra", "sap"],
        failure_outcome=FailureOutcome.STEP_UP,
        effective_period=period,
    )
    assert profile.is_effective(now)
    assert profile.digest.startswith("sha256:")
    assert profile.consequence_class == ConsequenceClass.HIGH


def test_assurance_profile_invalid_period():
    now = utcnow()
    with pytest.raises(
        ValueError, match="effective_until must be strictly after effective_from"
    ):
        EffectivePeriod(
            effective_from=now,
            effective_until=now - timedelta(seconds=1),
        )


def test_source_evidence_defaults_fail_closed():
    """P0 test: Evidence defaults to UNKNOWN for revocation and changed_since (no assumed active/unchanged)."""
    now = utcnow()
    ev = SourceAssuranceEvidenceV1(
        source_id="test_src",
        subject="res:1",
        observed_at=now,
    )
    assert ev.revocation_visibility == RevocationVisibilityStatus.UNKNOWN
    assert ev.changed_since_status == ChangedSinceStatus.UNKNOWN
    assert not ev.is_active(now)  # UNKNOWN is not active


def test_source_evidence_supplied_digest_validation():
    """P0 test: Ingested evidence_digest must strictly match computed digest."""
    now = utcnow()
    valid_ev = SourceAssuranceEvidenceV1(
        source_id="test_src",
        subject="res:1",
        observed_at=now,
        revocation_visibility=RevocationVisibilityStatus.ACTIVE,
        changed_since_status=ChangedSinceStatus.UNCHANGED,
    )
    correct_digest = valid_ev.compute_digest()

    # Re-instantiating with the correct digest succeeds
    ev_with_digest = SourceAssuranceEvidenceV1(
        source_id="test_src",
        subject="res:1",
        observed_at=now,
        revocation_visibility=RevocationVisibilityStatus.ACTIVE,
        changed_since_status=ChangedSinceStatus.UNCHANGED,
        evidence_digest=correct_digest,
    )
    assert ev_with_digest.evidence_digest == correct_digest

    # Re-instantiating with forged/tampered digest fails closed at ingest
    with pytest.raises(ValueError, match="evidence_digest mismatch"):
        SourceAssuranceEvidenceV1(
            source_id="test_src",
            subject="res:1",
            observed_at=now,
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            evidence_digest="sha256:0000000000000000000000000000000000000000000000000000000000000000",
        )


def test_source_evidence_hashing_and_freshness():
    now = utcnow()
    ev = SourceAssuranceEvidenceV1(
        source_id="entra_id",
        subject="user:alice",
        observed_at=now - timedelta(seconds=50),
        source_version="1.2.0",
        valid_until=now + timedelta(hours=1),
        changed_since_status=ChangedSinceStatus.UNCHANGED,
        revocation_visibility=RevocationVisibilityStatus.ACTIVE,
        attestation_type="OIDC_TOKEN",
        provenance={"issuer": "https://login.microsoftonline.com"},
    )
    assert ev.evidence_digest is not None
    assert ev.evidence_digest.startswith("sha256:")
    assert ev.is_fresh(now, max_age_seconds=60)
    assert not ev.is_fresh(now, max_age_seconds=30)
    assert ev.is_active(now)


def test_assurance_strength_capability_subsumption():
    """P1 test: satisfaction is capability-set subsumption, never a linear ranking."""
    # Superset mechanisms satisfy weaker minima within the same property domain
    assert is_assurance_strength_satisfied("VERSION_PINNED", "BASIC_TIMESTAMP")
    assert is_assurance_strength_satisfied("EVENT_STREAM_CURSOR", "VERSION_PINNED")
    assert is_assurance_strength_satisfied(
        "CRYPTOGRAPHIC_HSM", "CRYPTOGRAPHIC_SIGN_OFF"
    )

    # Different properties do NOT falsely rank: FIDO2 proves identity/hardware,
    # not version pinning; four-eyes proves dual control, not event continuity.
    assert not is_assurance_strength_satisfied("OIDC_FIDO2_BOUND", "VERSION_PINNED")
    assert not is_assurance_strength_satisfied("OIDC_FIDO2_BOUND", "BASIC_TIMESTAMP")
    assert not is_assurance_strength_satisfied(
        "FOUR_EYES_ATTESTATION", "EVENT_STREAM_CURSOR"
    )
    assert not is_assurance_strength_satisfied("BASIC_TIMESTAMP", "OIDC_FIDO2_BOUND")
    assert not is_assurance_strength_satisfied("UNVERIFIED", "BASIC_TIMESTAMP")


def test_assurance_capability_semantics():
    """P1 test: mechanisms resolve to explicit capability sets; subsets satisfy."""
    assert resolve_capabilities("BASIC_TIMESTAMP") == frozenset(
        {AssuranceCapability.FRESHNESS_OBSERVED}
    )
    assert resolve_capabilities("VERSION_PINNED") == frozenset(
        {AssuranceCapability.FRESHNESS_OBSERVED, AssuranceCapability.VERSION_BOUND}
    )
    assert resolve_capabilities("EVENT_STREAM_CURSOR") >= resolve_capabilities(
        "VERSION_PINNED"
    )
    # FIDO2 and event continuity are incomparable property sets
    assert not (
        resolve_capabilities("OIDC_FIDO2_BOUND")
        >= resolve_capabilities("EVENT_STREAM_CURSOR")
    )
    assert not (
        resolve_capabilities("EVENT_STREAM_CURSOR")
        >= resolve_capabilities("OIDC_FIDO2_BOUND")
    )

    # A capability name resolves to its singleton set
    assert resolve_capabilities("HARDWARE_BOUND") == frozenset(
        {AssuranceCapability.HARDWARE_BOUND}
    )


def test_assurance_mechanisms_combine():
    """P1 test: mechanisms combine (union) to cover a required capability set."""
    required = resolve_capabilities("EVENT_STREAM_CURSOR")

    # FIDO2 alone does not cover event-continuity requirements
    fido2_only = frozenset(resolve_capabilities("OIDC_FIDO2_BOUND"))
    assert not required <= fido2_only

    # A source evidence may declare multiple mechanisms that jointly satisfy
    evidence = SourceAssuranceEvidenceV1(
        source_id="compliance_gate",
        subject="audit:901",
        observed_at=utcnow(),
        attestation_type="OIDC_FIDO2_BOUND",
        provenance={"strength": "EVENT_STREAM_CURSOR"},
    )
    combined = resolve_evidence_capabilities(evidence)
    assert required <= combined


def test_assurance_unknown_mechanism_fails_closed():
    """Unknown mechanisms cannot self-declare strength: they fail closed."""
    assert resolve_capabilities("OIDC_FIDO2_BOUND") == frozenset(
        {
            AssuranceCapability.IDENTITY_BOUND,
            AssuranceCapability.HARDWARE_BOUND,
        }
    )
    assert resolve_capabilities("MY_CUSTOM_MECHANISM") == frozenset()
    assert resolve_capabilities(None) == frozenset()

    # An unknown mechanism never satisfies a declared minimum, even if the
    # names are identical — there is no proof of capability.
    assert not is_assurance_strength_satisfied(
        "MY_CUSTOM_MECHANISM", "MY_CUSTOM_MECHANISM"
    )
    assert not is_assurance_strength_satisfied("MY_CUSTOM_MECHANISM", "BASIC_TIMESTAMP")


def test_evaluation_digest():
    now = utcnow()
    eval_obj = CommitAssuranceEvaluationV1(
        action_ref="act-123",
        profile_ref="prof-1:1.0.0:hash",
        assurance_result=AssuranceResult.SATISFIED,
        evaluated_at=now,
    )
    assert eval_obj.evaluation_digest is not None
    assert eval_obj.is_satisfied


def test_policy_binding_integrity():
    now = utcnow()
    binding = PolicyBindingV1(
        policy_condition_ref="cond-test",
        profile_version_ref="prof-1:1.0.0",
        profile_digest="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        action_digest="sha256:2222222222222222222222222222222222222222222222222222222222222222",
        reht_clearance_ref="clr-1",
        reht_clearance_digest="sha256:3333333333333333333333333333333333333333333333333333333333333333",
        racs_decision_ref="racs-1",
        racs_decision_digest="sha256:4444444444444444444444444444444444444444444444444444444444444444",
        execution_receipt_ref="rec-1",
        execution_receipt_digest="sha256:5555555555555555555555555555555555555555555555555555555555555555",
        veritas_outcome_ref="ver-1",
        veritas_outcome_digest="sha256:6666666666666666666666666666666666666666666666666666666666666666",
        bound_at=now,
    )
    assert binding.binding_hash is not None
    assert binding.binding_hash.startswith("sha256:")
