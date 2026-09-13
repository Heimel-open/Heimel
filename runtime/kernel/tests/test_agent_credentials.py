from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from valo_kernel.agent_credentials import (
    AgentCapabilityCredential,
    CapabilityConformance,
    CapabilityGateRequest,
    CredentialDisposition,
    assess_agent_capability,
    credential_digest,
    issue_agent_capability_credential,
    verify_agent_capability_credential,
)


NOW = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)


def _unsigned(*, issuer_id: str = "issuer:valo-lab", scope=("payments.read",)):
    return AgentCapabilityCredential(
        credential_id="cred:agent-7:payments-read:v1",
        issuer_id=issuer_id,
        subject_agent_id="agent:7",
        capability_id="payments.read",
        scope=scope,
        risk_class="bounded-low",
        issued_at=NOW,
        valid_from=NOW - timedelta(minutes=1),
        valid_until=NOW + timedelta(days=30),
        conformance=CapabilityConformance(
            capability_id="payments.read",
            test_suite="valo-payments-read-conformance",
            test_suite_version="0.1.0",
            passed=12,
            failed=0,
            evidence_digest="sha256:" + "a" * 64,
            evaluated_at=NOW,
        ),
    )


def _request(*, scope=("payments.read",), at=NOW):
    return CapabilityGateRequest(
        agent_id="agent:7",
        capability_id="payments.read",
        required_scope=scope,
        at=at,
    )


def test_signed_credential_verifies_and_is_stable():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)

    assert signed.signature is not None
    assert verify_agent_capability_credential(signed, private.public_key())
    assert credential_digest(signed) == credential_digest(signed)


def test_matching_trusted_credential_is_capability_admissible():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)

    decision = assess_agent_capability(
        _request(),
        (signed,),
        {"issuer:valo-lab": private.public_key()},
    )

    assert decision.disposition == CredentialDisposition.ADMISSIBLE
    assert decision.credential_id == signed.credential_id
    assert "authority remains independently required" in decision.reason


def test_unknown_issuer_fails_closed():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)

    decision = assess_agent_capability(_request(), (signed,), {})

    assert decision.disposition == CredentialDisposition.DENY


def test_revoked_credential_fails_closed():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)

    decision = assess_agent_capability(
        _request(),
        (signed,),
        {"issuer:valo-lab": private.public_key()},
        frozenset({signed.credential_id}),
    )

    assert decision.disposition == CredentialDisposition.DENY


def test_expired_credential_fails_closed():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)

    decision = assess_agent_capability(
        _request(at=NOW + timedelta(days=31)),
        (signed,),
        {"issuer:valo-lab": private.public_key()},
    )

    assert decision.disposition == CredentialDisposition.DENY


def test_scope_escalation_fails_closed():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)

    decision = assess_agent_capability(
        _request(scope=("payments.read", "payments.execute")),
        (signed,),
        {"issuer:valo-lab": private.public_key()},
    )

    assert decision.disposition == CredentialDisposition.DENY


def test_tampered_subject_fails_signature_verification():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)
    tampered = signed.model_copy(update={"subject_agent_id": "agent:attacker"})

    assert not verify_agent_capability_credential(tampered, private.public_key())


def test_wrong_agent_has_no_matching_credential():
    private = Ed25519PrivateKey.generate()
    signed = issue_agent_capability_credential(_unsigned(), private)
    request = CapabilityGateRequest(
        agent_id="agent:other",
        capability_id="payments.read",
        required_scope=("payments.read",),
        at=NOW,
    )

    decision = assess_agent_capability(
        request,
        (signed,),
        {"issuer:valo-lab": private.public_key()},
    )

    assert decision.disposition == CredentialDisposition.DENY
