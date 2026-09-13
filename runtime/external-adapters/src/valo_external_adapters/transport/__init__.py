"""Vendor-specific transport adapters (Kafka, NATS).

Delivery bindings only. These adapt a sealed canonical artifact to a transport
target with a signed envelope; they perform no I/O and create no authority.
"""

from .envelope import (
    Ed25519TransportSigner,
    SignedTransportEnvelope,
    TransportArtifactSigner,
    TransportKind,
    TransportPayloadValue,
    seal_transport_envelope,
    verify_transport_envelope,
)
from .kafka import KafkaTarget, build_kafka_envelope, kafka_producer_record
from .nats import NatsTarget, build_nats_envelope, nats_publish_message

__all__ = [
    "Ed25519TransportSigner",
    "KafkaTarget",
    "NatsTarget",
    "SignedTransportEnvelope",
    "TransportArtifactSigner",
    "TransportKind",
    "TransportPayloadValue",
    "build_kafka_envelope",
    "build_nats_envelope",
    "kafka_producer_record",
    "nats_publish_message",
    "seal_transport_envelope",
    "verify_transport_envelope",
]
