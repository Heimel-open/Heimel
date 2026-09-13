from datetime import timedelta

import pytest

from valo_insurance_pack.claims.builder import ClaimsEvidencePackBuilder
from valo_insurance_pack.claims.verifier import verify_claims_evidence_pack
from valo_insurance_pack.contracts.assurance_profile import (
    AssuranceProfileV1,
    ConsequenceClass,
    EffectivePeriod,
    FailureOutcome,
)
from valo_insurance_pack.contracts.source_evidence import (
    ChangedSinceStatus,
    RevocationVisibilityStatus,
    SourceAssuranceEvidenceV1,
)
from valo_insurance_pack.evaluation.evaluator import evaluate_commit_assurance
from valo_insurance_pack.utils.crypto import utcnow


@pytest.fixture
def valid_bundle():
    now = utcnow()
    profile = AssuranceProfileV1(
        profile_id="prof-claims-1",
        insurer_reference="carrier:zurich",
        coverage_condition_ref="cond-zurich-101",
        action_type="PO_CREATE",
        consequence_class=ConsequenceClass.MEDIUM,
        required_authoritative_sources=["entra_id"],
        failure_outcome=FailureOutcome.DENY,
        effective_period=EffectivePeriod(
            effective_from=now - timedelta(days=1),
            effective_until=now + timedelta(days=365),
        ),
    )
    action = {"action_type": "PO_CREATE", "target": "erp:sap/po", "amount": 1000}
    sources = [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="user:alice",
            observed_at=now - timedelta(seconds=10),
            attestation_type="OIDC_MFA",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
        )
    ]
    eval_res = evaluate_commit_assurance(
        profile=profile,
        action=action,
        source_evidences=sources,
        reht_clearance_ref="clr-999",
        racs_decision_ref="racs-999",
        now=now,
    )
    clearance = {
        "clearance_id": "clr-999",
        "status": "ALLOW",
        "decision_contract": {"decision": "ALLOW"},
    }
    racs_dec = {"decision_id": "racs-999", "verdict": "ALLOW"}
    receipt = {
        "execution_id": "exec-999",
        "permit_id": "permit-999",
        "status": "succeeded",
    }
    veritas_obs = {
        "package_id": "obs-999",
        "execution_id": "exec-999",
        "worm_sequence": 42,
    }

    builder = ClaimsEvidencePackBuilder(
        policy_reference="pol-test-1",
        coverage_condition_ref="cond-zurich-101",
        active_assurance_profile=profile,
    )
    builder.set_action(action)
    builder.set_source_evidences(sources)
    builder.set_evaluation(eval_res)
    builder.set_reht_clearance(clearance)
    builder.set_racs_decision(racs_dec)
    builder.set_effect_receipt(receipt)
    builder.set_veritas_verification(veritas_obs)

    pack = builder.build(now=now)
    return pack


def test_claims_evidence_pack_verification(valid_bundle):
    report = verify_claims_evidence_pack(valid_bundle)
    assert report.is_valid
    assert len(report.errors) == 0
    assert report.policy_reference == "pol-test-1"


def test_claims_evidence_pack_tamper_detection(valid_bundle):
    pack_dict = valid_bundle.model_dump(mode="json")
    # Tamper with action amount
    pack_dict["exact_action"]["amount"] = 9999999
    report = verify_claims_evidence_pack(pack_dict)
    assert not report.is_valid
    assert any("action_digest_mismatch" in e for e in report.errors)


def test_claims_evidence_pack_tamper_receipt(valid_bundle):
    pack_dict = valid_bundle.model_dump(mode="json")
    # Tamper with receipt status
    pack_dict["effect_receipt"]["status"] = "failed"
    report = verify_claims_evidence_pack(pack_dict)
    assert not report.is_valid
    assert any("receipt_digest_mismatch" in e for e in report.errors)


def test_claims_evidence_pack_tamper_bundle_seal(valid_bundle):
    """P1 test: the top-level pack_digest seal is re-verified."""
    # pack_id is bound only by pack_digest
    tampered_id = valid_bundle.model_copy(update={"pack_id": "claim-pack-TAMPERED"})
    report = verify_claims_evidence_pack(tampered_id)
    assert not report.is_valid
    assert any("pack_digest_mismatch" in e for e in report.errors)

    # generated_at is bound only by pack_digest
    tampered_time = valid_bundle.model_copy(
        update={"generated_at": utcnow() - timedelta(days=30)}
    )
    report = verify_claims_evidence_pack(tampered_time)
    assert not report.is_valid
    assert any("pack_digest_mismatch" in e for e in report.errors)


def test_claims_evidence_pack_json_export_and_parse(valid_bundle):
    json_str = valid_bundle.to_json()
    report = verify_claims_evidence_pack(json_str)
    assert report.is_valid


def test_builder_rejects_non_serializable_objects():
    """P1 test: non-serializable evidence objects fail loudly instead of degrading."""
    now = utcnow()
    profile = AssuranceProfileV1(
        profile_id="prof-claims-1",
        insurer_reference="carrier:zurich",
        coverage_condition_ref="cond-zurich-101",
        action_type="PO_CREATE",
        consequence_class=ConsequenceClass.MEDIUM,
        required_authoritative_sources=["entra_id"],
        failure_outcome=FailureOutcome.DENY,
        effective_period=EffectivePeriod(
            effective_from=now - timedelta(days=1),
            effective_until=now + timedelta(days=365),
        ),
    )
    builder = ClaimsEvidencePackBuilder(
        policy_reference="pol-test-1",
        coverage_condition_ref="cond-zurich-101",
        active_assurance_profile=profile,
    )
    with pytest.raises(ValueError, match="cannot bind non-serializable object"):
        builder.set_reht_clearance(object())
