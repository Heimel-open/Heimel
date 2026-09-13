from dataclasses import replace

from valo_mal import (
    FederationRequest,
    SignedPolicyPack,
    TrustRoot,
    canonical_digest,
    evaluate_import,
)


def fixtures():
    payload = {"region": "eu-north", "rules": ["deny-unknown"]}
    root = TrustRoot(
        "root-1", "issuer-a", "fp", ("tenant-b",), ("model-admissibility",), 1, 100
    )
    pack = SignedPolicyPack(
        "pack-1", "issuer-a", "tenant-a", "model-admissibility", "1.0.0",
        payload, canonical_digest(payload), "sig", "root-1", 1, 80,
    )
    request = FederationRequest(
        "tenant-b", "model-admissibility", "eu-north", 50, "nonce-1"
    )
    return root, pack, request


def test_valid_pack_requires_local_review_not_activation():
    root, pack, request = fixtures()
    result = evaluate_import(pack, request, [root], set())
    assert result.decision == "IMPORT_FOR_LOCAL_REVIEW"
    assert result.imported_pack_digest == pack.payload_digest


def test_cross_tenant_without_trust_is_rejected():
    root, pack, request = fixtures()
    result = evaluate_import(replace(pack, issuer="other"), request, [root], set())
    assert result.decision == "REJECT"
    assert "ISSUER_MISMATCH" in result.reasons


def test_replay_and_tampering_fail_closed():
    root, pack, request = fixtures()
    replay = evaluate_import(pack, request, [root], {request.import_nonce})
    tampered = evaluate_import(
        replace(pack, payload={"region": "eu-north", "rules": ["allow-all"]}),
        request,
        [root],
        set(),
    )
    assert "IMPORT_REPLAY" in replay.reasons
    assert "PAYLOAD_DIGEST_MISMATCH" in tampered.reasons
