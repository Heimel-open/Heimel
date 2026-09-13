import sys
from datetime import UTC, datetime, timedelta

import pytest

# Ensure dependency paths are present if running tests standalone.
for path in [
    "/home/njaal/reht/src",
    "/home/njaal/valo-gateway/src",
    "/home/njaal/Veritas/src",
    "/home/njaal/Racs/reference/python",
]:
    if path not in sys.path:
        sys.path.insert(0, path)

# The real-chain integration test exercises sibling repositories (reht,
# valo-gateway, Veritas, RACS). On CI runners those are not installed, so the
# module skips cleanly instead of failing collection.
pytest.importorskip("reht", reason="reht not installed; skipping real-chain test")
pytest.importorskip(
    "valo_gateway", reason="valo-gateway not installed; skipping real-chain test"
)
pytest.importorskip("veritas", reason="Veritas not installed; skipping real-chain test")
pytest.importorskip(
    "racs_clearance", reason="RACS not installed; skipping real-chain test"
)

from racs_canonical import sha256_digest as racs_sha256_digest
from racs_clearance import (
    ClearanceError,
    GovernanceClearanceIssuer,
    GovernanceClearanceVerifier,
)
from racs_crypto import generate_keypair, load_private_key, sign_artifact
from reht.issuance import RehtIssuer
from valo_gateway.contracts.models import (
    ActionEnvelope,
    AuthorityEnvelope,
    AuthoritySource,
    Clearance,
    Decision,
    DecisionContract,
    issue_execution_permit,
    utcnow,
)
from valo_gateway.gateway.core import ValoGateway
from valo_gateway.veritas_handoff import build_veritas_execution_observation
from veritas.service import VeritasChainService
from veritas.worm import WORMLog

from examples.mock_erp import MockErpSapTool
from valo_insurance_pack.claims.builder import ClaimsEvidencePackBuilder
from valo_insurance_pack.claims.verifier import verify_claims_evidence_pack
from valo_insurance_pack.contracts.source_evidence import (
    ChangedSinceStatus,
    RevocationVisibilityStatus,
    SourceAssuranceEvidenceV1,
)
from valo_insurance_pack.evaluation.evaluator import evaluate_commit_assurance
from valo_insurance_pack.profiles.carrier_examples import PROCUREMENT_HIGH_VALUE


def _racs_ts(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_racs_stack(*, tenant_id: str, trust_domain: str):
    """Return (issuer, verifier, registry, private_key_pem) backed by a fresh Ed25519 keypair."""
    priv_pem, pub_pem = generate_keypair()
    issuer_id = "reht-clearance-issuer-1"
    issuer = GovernanceClearanceIssuer(
        issuer_id=issuer_id,
        tenant_id=tenant_id,
        trust_domain=trust_domain,
        private_key=load_private_key(priv_pem),
        key_id="key-1",
    )
    registry = {
        issuer_id: {
            "issuer_id": issuer_id,
            "issuer_role": "REHT_CLEARANCE_ISSUER",
            "tenant_scope": tenant_id,
            "trust_domain": trust_domain,
            "allowed_artifact_types": ["GovernanceClearance"],
            "key_id": "key-1",
            "algorithm": "Ed25519",
            "public_key": pub_pem.decode("utf-8"),
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": "2028-01-01T00:00:00Z",
            "revocation_status": "ACTIVE",
            "registry_version": "1",
        }
    }
    return issuer, GovernanceClearanceVerifier(registry), registry, priv_pem


def _racs_clearance_payload(
    *,
    decision: str,
    clearance_ref: str,
    action,
    authority,
    evidence_ref: str,
    now: datetime,
) -> dict:
    """Build a RACS GovernanceClearance payload bound to the (real) reht decision."""
    digest = lambda value: racs_sha256_digest(value)
    return {
        "clearance_id": f"clr-racs-{clearance_ref}",
        "action_id": action.action_type,
        "action_envelope_digest": "sha256:" + action.digest,
        "tenant_id": "tenant-corp-real",
        "decision": decision,
        "admissibility_state": "ADMISSIBLE",
        "authority_digest": digest(authority.envelope_id),
        "delegation_chain_digest": digest("chain:root"),
        "policy_digest": action.policy_digest,
        "evidence_digest": evidence_ref,
        "purpose_digest": digest("purpose:procurement"),
        "state_digest": digest("state:PO-REAL-7701"),
        "target_digest": digest(action.target),
        "payload_digest": digest("payload:racs"),
        "connector_id": "erp:sap",
        "capability": "procurement:create",
        "consequence_class": "HIGH",
        "reversibility": "COMPENSATABLE",
        "valid_from": _racs_ts(now - timedelta(minutes=1)),
        "valid_until": _racs_ts(now + timedelta(minutes=10)),
        "replay_nonce": "nonce-" + "b" * 16,
        "idempotency_key": "idem-" + "c" * 8,
        "revocation_registry_ref": "rev-reg-1",
        "evaluator_refs": [evidence_ref],
        "admissibility_determination_ref": f"reht-determination-{clearance_ref}",
        "admissibility_determination_digest": digest("determination:reht"),
    }


def _authority_envelope(now: datetime) -> AuthorityEnvelope:
    return AuthorityEnvelope(
        envelope_id="auth-env-real-1001",
        principal_id="principal:procurement-dir",
        actor_id="agent:procurement-worker-9",
        source=AuthoritySource.AAP,
        issuer="https://issuer.valo.internal",
        capability_grants=["procurement:create", "erp:sap:write", "PROCUREMENT_ORDER_CREATE"],
        resource_scope=["erp:sap/po/create"],
        purpose_scope=["procurement"],
        issued_at=now - timedelta(minutes=10),
        valid_until=now + timedelta(hours=2),
    )


def _action_envelope(authority: AuthorityEnvelope, now: datetime) -> ActionEnvelope:
    return ActionEnvelope(
        action_type="PROCUREMENT_ORDER_CREATE",
        target="erp:sap/po/create",
        parameters={
            "po_number": "PO-REAL-7701",
            "amount": 250000,
            "vendor": "SUPPLIER-BETA",
        },
        context_digest="sha256:0000000000000000000000000000000000000000000000000000000000000000",
        policy_digest="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        authority_envelope_id=authority.envelope_id,
    )


def _source_evidences(now: datetime) -> list[SourceAssuranceEvidenceV1]:
    """Load-bearing source evidences, explicitly active and unchanged."""
    return [
        SourceAssuranceEvidenceV1(
            source_id="entra_id",
            subject="principal:procurement-dir",
            observed_at=now - timedelta(seconds=30),
            source_version="entra-v2",
            attestation_type="OIDC_FIDO2_BOUND",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={"assurance_level": "OIDC_FIDO2_BOUND"},
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_budget",
            subject="budget:cc-procure-2026",
            observed_at=now - timedelta(seconds=60),
            source_version="sap-erp-2026",
            attestation_type="ERP_AUTHORITATIVE_API",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={"assurance_level": "ERP_AUTHORITATIVE_API"},
        ),
        SourceAssuranceEvidenceV1(
            source_id="erp_sap_po_state",
            subject="po:PO-REAL-7701",
            observed_at=now - timedelta(seconds=45),
            source_version="po-draft-v1",
            attestation_type="ERP_COMMITTED_STATE",
            revocation_visibility=RevocationVisibilityStatus.ACTIVE,
            changed_since_status=ChangedSinceStatus.UNCHANGED,
            provenance={"assurance_level": "ERP_COMMITTED_STATE"},
        ),
    ]


def _signed_racs_clearance(issuer, *, decision, clearance_ref, action, authority, now):
    """Issue a signed GovernanceClearance artifact for the given reht decision."""
    return issuer.issue(
        _racs_clearance_payload(
            decision=decision,
            clearance_ref=clearance_ref,
            action=action,
            authority=authority,
            evidence_ref="sha256:" + "a" * 64,
            now=now,
        )
    )


def test_real_chain_integration_with_actual_reht_racs_gateway_and_veritas():
    """P1 test: real reht engine -> signed RACS clearance verification -> Gateway PEP -> Veritas WORM."""
    now = utcnow()
    profile = PROCUREMENT_HIGH_VALUE

    authority = _authority_envelope(now)
    action = _action_envelope(authority, now)
    sources = _source_evidences(now)

    # 1. Commit-time Assurance Evaluation
    assurance_eval = evaluate_commit_assurance(
        profile=profile,
        action=action,
        source_evidences=sources,
        now=now,
    )
    assert assurance_eval.is_satisfied

    # 2. Execute actual REHT Engine Authorization (sole authorization boundary)
    reht_engine = RehtIssuer()
    execution_context = {
        "authority": [
            {
                "capability": "procurement:create",
                "status": "ACTIVE",
                "scope": ["erp:sap/po/create"],
            }
        ]
    }
    action_contract = {
        "target": action.target,
        "capability": "procurement:create",
    }
    reht_decision = reht_engine.authorize(execution_context, action_contract)
    assert reht_decision.decision == "ALLOW"

    # 3. RACS: issue a signed GovernanceClearance bound to the real reht decision,
    #    then fail-closed verify it with the RACS reference implementation.
    racs_issuer, racs_verifier, _registry, _priv = _build_racs_stack(
        tenant_id="tenant-corp-real", trust_domain="valo-trust-real"
    )
    racs_payload = _racs_clearance_payload(
        decision=reht_decision.decision,
        clearance_ref=reht_decision.clearance_ref,
        action=action,
        authority=authority,
        evidence_ref=assurance_eval.evidence_refs[0],
        now=now,
    )
    racs_artifact = racs_issuer.issue(racs_payload)
    racs_verifier.verify(racs_artifact)  # must not raise
    racs_clearance_digest = racs_artifact["payload_digest"]

    # 4. Build Clearance bound to the real REHT decision AND the RACS attestation
    clearance = Clearance(
        clearance_id="clr-real-9001",
        action_digest=action.digest,
        authority_envelope_id=authority.envelope_id,
        decision_contract=DecisionContract(
            decision=Decision.ALLOW,
            principal_id=authority.principal_id,
            actor_id=authority.actor_id,
            action_type=action.action_type,
            target=action.target,
            constraints={"max_amount": 500000},
        ),
        decided_at=now,
        valid_until=now + timedelta(minutes=10),
        reht_ref=(
            f"reht-decision-{reht_decision.clearance_ref}"
            f"|racs-clearance-{racs_clearance_digest}"
        ),
        evidence_refs=assurance_eval.evidence_refs + [racs_clearance_digest],
        policy_refs=[profile.coverage_condition_ref],
    )

    # 5. Gateway Issues and Consumes Permit (PEP Enforcement)
    permit = issue_execution_permit(
        clearance=clearance,
        authority=authority,
        action=action,
        expires_at=now + timedelta(minutes=5),
        now=now,
    )

    tool = MockErpSapTool()
    gw = ValoGateway()
    exec_result = gw.execute(
        authority=authority,
        clearance=clearance,
        permit=permit,
        action=action,
        executor_id=authority.actor_id,
        tool=tool,
        arguments=action.parameters,
        now=now,
    )
    assert exec_result.receipt.status.value == "succeeded"
    assert "PO-REAL-7701" in tool.committed_pos

    # 6. Real Veritas Attestation Service (write-once WORM log)
    veritas_handoff_payload = build_veritas_execution_observation(
        authority=authority,
        clearance=clearance,
        action=action,
        result=exec_result,
    )

    worm = WORMLog()
    veritas_service = VeritasChainService(worm=worm)
    worm_entry_id = veritas_service.store_gateway_execution_observation(
        veritas_handoff_payload,
        tenant_id="tenant-corp-real",
    )
    assert worm_entry_id is not None
    assert len(worm.read_all()) == 1

    # 7. Assemble ClaimsEvidencePackV1 binding the RACS decision artifact
    builder = ClaimsEvidencePackBuilder(
        policy_reference="pol-procurement-real-2026",
        coverage_condition_ref=profile.coverage_condition_ref,
        active_assurance_profile=profile,
    )
    builder.set_action(action)
    builder.set_source_evidences(sources)
    builder.set_evaluation(assurance_eval)
    builder.set_reht_clearance(clearance)
    builder.set_racs_decision(
        {
            "decision": clearance.decision_contract.decision.value,
            "decision_id": racs_artifact["artifact_id"],
            "racs_clearance_digest": racs_clearance_digest,
        }
    )
    builder.set_effect_receipt(exec_result.receipt)
    builder.set_veritas_verification(veritas_handoff_payload)

    pack = builder.build(now=now)

    # 8. Verify Claims Evidence Pack Offline
    report = verify_claims_evidence_pack(pack)
    assert report.is_valid
    assert len(report.errors) == 0


def test_bypass_attempts_yield_zero_consequence():
    """Negative P1 test: forging a path around reht/RACS/Gateway produces null effect."""
    now = utcnow()
    authority = _authority_envelope(now)
    action = _action_envelope(authority, now)
    tool = MockErpSapTool()

    # 1. RACS fail-closed: a locally constructed (unsigned, unknown-issuer)
    #    clearance artifact MUST be rejected by the RACS verifier.
    _, racs_verifier, _, _ = _build_racs_stack(
        tenant_id="tenant-corp-real", trust_domain="valo-trust-real"
    )
    forged_artifact = {
        "artifact_type": "GovernanceClearance",
        "schema_version": "0.2.0",
        "profile_id": "racs-platform-0.2",
        "artifact_id": "clr-forged",
        "tenant_id": "tenant-corp-real",
        "trust_domain": "valo-trust-real",
        "issuer_id": "attacker-self-signed",
        "issuer_role": "REHT_CLEARANCE_ISSUER",
        "issued_at": _racs_ts(now),
        "expires_at": _racs_ts(now + timedelta(minutes=10)),
        "payload": _racs_clearance_payload(
            decision="ALLOW",
            clearance_ref="clr-forged",
            action=action,
            authority=authority,
            evidence_ref="sha256:" + "a" * 64,
            now=now,
        ),
        "payload_digest": "sha256:" + "0" * 64,
        "canonicalization": "RACS-JCS-1",
        "signature": {"algorithm": "Ed25519", "key_id": "key-x", "value": ""},
    }
    with pytest.raises(ClearanceError):
        racs_verifier.verify(forged_artifact)
    assert len(tool.committed_pos) == 0

    # 2. Gateway PEP fail-closed: a forged clearance bound to a DIFFERENT action
    #    can never mint a permit, so the consequence tool is never reached.
    forged_clearance = Clearance(
        clearance_id="clr-forged-0001",
        action_digest="sha256:ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        authority_envelope_id=authority.envelope_id,
        decision_contract=DecisionContract(
            decision=Decision.ALLOW,
            principal_id=authority.principal_id,
            actor_id=authority.actor_id,
            action_type="PO_CREATE",
            target="erp:sap/po/delete",
        ),
        decided_at=now,
        valid_until=now + timedelta(minutes=5),
        reht_ref="self-signed-no-reht-no-racs",
        evidence_refs=[],
    )
    with pytest.raises(ValueError):
        issue_execution_permit(
            clearance=forged_clearance,
            authority=authority,
            action=action,
            expires_at=now + timedelta(minutes=5),
            now=now,
        )
    assert len(tool.committed_pos) == 0
    assert len(tool.invocations) == 0


def test_racs_rejects_forged_signature():
    """RACS verifier rejects an artifact signed by a different (attacker) key."""
    now = utcnow()
    authority = _authority_envelope(now)
    action = _action_envelope(authority, now)
    _issuer, verifier, _, _ = _build_racs_stack(
        tenant_id="tenant-corp-real", trust_domain="valo-trust-real"
    )

    attacker_priv, _ = generate_keypair()
    attacker = GovernanceClearanceIssuer(
        issuer_id="reht-clearance-issuer-1",
        tenant_id="tenant-corp-real",
        trust_domain="valo-trust-real",
        private_key=load_private_key(attacker_priv),
        key_id="key-1",
    )
    forged = _signed_racs_clearance(
        attacker,
        decision="ALLOW",
        clearance_ref="clr-fsig",
        action=action,
        authority=authority,
        now=now,
    )
    with pytest.raises(ClearanceError, match="signature invalid"):
        verifier.verify(forged)


def test_racs_rejects_wrong_issuer_role():
    """RACS verifier rejects an artifact whose issuer_role is not REHT_CLEARANCE_ISSUER."""
    now = utcnow()
    authority = _authority_envelope(now)
    action = _action_envelope(authority, now)
    issuer, verifier, _, _ = _build_racs_stack(
        tenant_id="tenant-corp-real", trust_domain="valo-trust-real"
    )

    artifact = _signed_racs_clearance(
        issuer,
        decision="ALLOW",
        clearance_ref="clr-role",
        action=action,
        authority=authority,
        now=now,
    )
    artifact = {**artifact, "issuer_role": "SOME_OTHER_ROLE"}
    with pytest.raises(ClearanceError, match="issuer_role is not REHT_CLEARANCE_ISSUER"):
        verifier.verify(artifact)


def test_racs_rejects_expired_clearance():
    """RACS verifier rejects a correctly-signed but expired GovernanceClearance."""
    now = utcnow()
    authority = _authority_envelope(now)
    action = _action_envelope(authority, now)
    issuer, verifier, _, priv_pem = _build_racs_stack(
        tenant_id="tenant-corp-real", trust_domain="valo-trust-real"
    )

    artifact = _signed_racs_clearance(
        issuer,
        decision="ALLOW",
        clearance_ref="clr-expired",
        action=action,
        authority=authority,
        now=now,
    )
    artifact = {**artifact, "expires_at": _racs_ts(now - timedelta(seconds=5))}
    # Re-sign so the expired envelope carries a valid signature
    sign_artifact(artifact, load_private_key(priv_pem))
    with pytest.raises(ClearanceError, match="clearance expired"):
        verifier.verify(artifact)


def test_racs_rejects_tampered_action_digest():
    """RACS verifier rejects a correctly-signed artifact with a tampered action digest."""
    now = utcnow()
    authority = _authority_envelope(now)
    action = _action_envelope(authority, now)
    issuer, verifier, _, _ = _build_racs_stack(
        tenant_id="tenant-corp-real", trust_domain="valo-trust-real"
    )

    artifact = _signed_racs_clearance(
        issuer,
        decision="ALLOW",
        clearance_ref="clr-tamper",
        action=action,
        authority=authority,
        now=now,
    )
    artifact["payload"]["action_envelope_digest"] = "sha256:" + "9" * 64
    with pytest.raises(ClearanceError, match="payload digest mismatch"):
        verifier.verify(artifact)


def test_valid_racs_artifact_with_stale_reht_binding_yields_no_effect():
    """A valid RACS clearance bound to a stale (expired) REHT decision can never mint a permit."""
    now = utcnow()
    authority = _authority_envelope(now)
    action = _action_envelope(authority, now)
    issuer, verifier, _, _ = _build_racs_stack(
        tenant_id="tenant-corp-real", trust_domain="valo-trust-real"
    )

    # The RACS artifact itself verifies fine...
    artifact = _signed_racs_clearance(
        issuer,
        decision="ALLOW",
        clearance_ref="clr-stale",
        action=action,
        authority=authority,
        now=now,
    )
    verifier.verify(artifact)

    # ...but the underlying REHT decision it binds to has already expired.
    stale_clearance = Clearance(
        clearance_id="clr-stale-1",
        action_digest=action.digest,
        authority_envelope_id=authority.envelope_id,
        decision_contract=DecisionContract(
            decision=Decision.ALLOW,
            principal_id=authority.principal_id,
            actor_id=authority.actor_id,
            action_type=action.action_type,
            target=action.target,
        ),
        decided_at=now - timedelta(hours=2),
        valid_until=now - timedelta(hours=1),
        reht_ref=(
            "reht-decision-stale"
            f"|racs-clearance-{artifact['payload_digest']}"
        ),
        evidence_refs=["sha256:" + "a" * 64, artifact["payload_digest"]],
    )
    tool = MockErpSapTool()
    with pytest.raises(ValueError, match="clearance decision cannot issue an execution permit"):
        issue_execution_permit(
            clearance=stale_clearance,
            authority=authority,
            action=action,
            expires_at=now + timedelta(minutes=5),
            now=now,
        )
    assert len(tool.committed_pos) == 0
    assert len(tool.invocations) == 0
