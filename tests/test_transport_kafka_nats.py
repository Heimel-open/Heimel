from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from valo_external_adapters.transport import (
    Ed25519TransportSigner,
    KafkaTarget,
    NatsTarget,
    TransportKind,
    build_kafka_envelope,
    build_nats_envelope,
    kafka_producer_record,
    nats_publish_message,
    verify_transport_envelope,
)


def _signer() -> Ed25519TransportSigner:
    return Ed25519TransportSigner.from_private_key_bytes(
        signer_id="transport-signer",
        key_id="key-1",
        private_key_bytes=Ed25519PrivateKey.generate().private_bytes_raw(),
    )


def _now() -> datetime:
    return datetime(2026, 8, 16, 15, 0, 0, tzinfo=timezone.utc)


def test_kafka_envelope_seals_and_verifies():
    signer = _signer()
    target = KafkaTarget(topic="payments.authorized", key="action:1001")
    envelope = build_kafka_envelope(
        target=target,
        artifact_ref="external_provider_request:abc",
        artifact_digest="a" * 64,
        signer=signer,
        nonce="nonce-kafka-1",
        signed_at=_now(),
    )
    assert envelope.transport is TransportKind.KAFKA
    assert envelope.envelope_digest == envelope.computed_digest
    verify_transport_envelope(envelope=envelope, public_key=signer.public_key)
    record = kafka_producer_record(envelope)
    assert record["topic"] == "payments.authorized"
    assert record["key"] == "action:1001"


def test_kafka_payload_cannot_be_tampered_after_seal():
    signer = _signer()
    target = KafkaTarget(topic="payments.authorized", key="action:1001")
    envelope = build_kafka_envelope(
        target=target,
        artifact_ref="external_provider_request:abc",
        artifact_digest="a" * 64,
        signer=signer,
        nonce="nonce-kafka-2",
        signed_at=_now(),
    )
    # Tamper the sealed artifact digest in place; this must make the envelope
    # fail verification because envelope_digest no longer matches.
    tampered = envelope.model_copy(update={"artifact_digest": "b" * 64})
    try:
        verify_transport_envelope(envelope=tampered, public_key=signer.public_key)
    except ValueError:
        return
    raise AssertionError("tampered envelope should fail verification")


def test_nats_envelope_seals_and_verifies():
    signer = _signer()
    target = NatsTarget(subject="exec.authorized", stream="EXEC", durable="worker-1")
    envelope = build_nats_envelope(
        target=target,
        artifact_ref="external_provider_request:def",
        artifact_digest="c" * 64,
        signer=signer,
        nonce="nonce-nats-1",
        signed_at=_now(),
        reply_to="exec.replies",
    )
    assert envelope.transport is TransportKind.NATS
    assert envelope.envelope_digest == envelope.computed_digest
    verify_transport_envelope(envelope=envelope, public_key=signer.public_key)
    message = nats_publish_message(envelope)
    assert message["subject"] == "exec.authorized"
    assert message["stream"] == "EXEC"
    assert message["reply_to"] == "exec.replies"


def test_wrong_key_fails_verification():
    signer = _signer()
    other = _signer()
    target = KafkaTarget(topic="payments.authorized", key="action:1001")
    envelope = build_kafka_envelope(
        target=target,
        artifact_ref="external_provider_request:abc",
        artifact_digest="a" * 64,
        signer=signer,
        nonce="nonce-kafka-3",
        signed_at=_now(),
    )
    try:
        verify_transport_envelope(envelope=envelope, public_key=other.public_key)
    except ValueError:
        return
    raise AssertionError("verification with wrong key must fail")


def test_transport_envelope_has_no_authority_effect():
    signer = _signer()
    target = NatsTarget(subject="exec.authorized")
    envelope = build_nats_envelope(
        target=target,
        artifact_ref="external_provider_request:def",
        artifact_digest="c" * 64,
        signer=signer,
        nonce="nonce-nats-2",
        signed_at=_now(),
    )
    assert envelope.authority_effect == "NO_AUTHORITY_CREATION"
    assert envelope.can_issue_clearance is False
    assert envelope.can_create_authority is False


def test_kafka_requires_topic_and_key():
    with __import__("pytest").raises(ValueError):
        KafkaTarget(topic="", key="")
    with __import__("pytest").raises(ValueError):
        KafkaTarget(topic="payments", key="")


def test_nats_requires_subject():
    with __import__("pytest").raises(ValueError):
        NatsTarget(subject="")
