"""Kafka transport adapter — vendor-specific target binding.

Binds a sealed canonical artifact to a Kafka topic + key with a signed
envelope. This is a *delivery binding only*: it constructs the signed
``SignedTransportEnvelope`` and returns the producer record fields. It performs
no I/O and creates no authority.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .envelope import (
    SignedTransportEnvelope,
    TransportArtifactSigner,
    TransportKind,
    TransportPayloadValue,
    seal_transport_envelope,
)

KAFKA_SIGNATURE_DOMAIN = b"VALO-KAFKA-TARGET-V1\x00"


class KafkaTarget(BaseModel):
    """Resolved Kafka delivery target (topic + partition key)."""

    schema_version: Literal["kafka_target.v1"] = "kafka_target.v1"
    topic: str
    key: str
    partition_key: str = ""
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_target(self) -> KafkaTarget:
        if not self.topic or not self.topic.strip():
            raise ValueError("kafka topic is required")
        if not self.key or not self.key.strip():
            raise ValueError("kafka key is required")
        return self


def _require_nonempty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


def build_kafka_envelope(
    *,
    target: KafkaTarget,
    artifact_ref: str,
    artifact_digest: str,
    signer: TransportArtifactSigner,
    nonce: str,
    signed_at: datetime,
    headers: dict[str, str] | None = None,
) -> SignedTransportEnvelope:
    """Seal a signed Kafka delivery envelope for one canonical artifact.

    The enclosed ``artifact_ref``/``artifact_digest`` are opaque to the transport
    layer — Kafka cannot alter, re-author or execute the artifact.
    """
    _require_nonempty(artifact_ref, "artifact_ref")
    transport_payload: dict[str, TransportPayloadValue] = {
        "topic": target.topic,
        "key": target.key,
        "partition_key": target.partition_key,
    }
    if headers:
        for name, value in headers.items():
            if not name.strip():
                raise ValueError("kafka header name must not be blank")
            transport_payload[f"header:{name}"] = value
    return seal_transport_envelope(
        transport=TransportKind.KAFKA,
        target=target.topic,
        artifact_ref=artifact_ref,
        artifact_digest=artifact_digest,
        transport_payload=transport_payload,
        signer=signer,
        nonce=nonce,
        signed_at=signed_at,
    )


def kafka_producer_record(
    envelope: SignedTransportEnvelope,
) -> dict[str, object]:
    """Render the Kafka producer record fields from a verified envelope.

    Does not perform I/O. Caller performs the actual produce with their own
    client. Returns the topic, key and serialised value dict.
    """
    if envelope.transport is not TransportKind.KAFKA:
        raise ValueError("envelope is not a Kafka envelope")
    return {
        "topic": envelope.target,
        "key": envelope.transport_payload.get("key", ""),
        "partition_key": envelope.transport_payload.get("partition_key", ""),
        "value": envelope.model_dump(mode="json", exclude={"transport_signature"}),
        "headers": {
            k[len("header:") :]: str(v)
            for k, v in envelope.transport_payload.items()
            if k.startswith("header:")
        },
    }
