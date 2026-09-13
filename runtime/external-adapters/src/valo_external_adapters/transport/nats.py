"""NATS transport adapter — vendor-specific target binding.

Binds a sealed canonical artifact to a NATS subject (optionally a JetStream
stream/durable) with a signed envelope. This is a *delivery binding only*: it
constructs the signed ``SignedTransportEnvelope`` and returns the publish
fields. It performs no I/O and creates no authority.
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

NATS_SIGNATURE_DOMAIN = b"VALO-NATS-TARGET-V1\x00"


class NatsTarget(BaseModel):
    """Resolved NATS delivery target (subject + optional JetStream binding)."""

    schema_version: Literal["nats_target.v1"] = "nats_target.v1"
    subject: str
    stream: str = ""
    durable: str = ""
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_target(self) -> NatsTarget:
        if not self.subject or not self.subject.strip():
            raise ValueError("nats subject is required")
        return self


def _require_nonempty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} is required")


def build_nats_envelope(
    *,
    target: NatsTarget,
    artifact_ref: str,
    artifact_digest: str,
    signer: TransportArtifactSigner,
    nonce: str,
    signed_at: datetime,
    reply_to: str | None = None,
) -> SignedTransportEnvelope:
    """Seal a signed NATS delivery envelope for one canonical artifact.

    The enclosed ``artifact_ref``/``artifact_digest`` are opaque to the transport
    layer — NATS cannot alter, re-author or execute the artifact.
    """
    _require_nonempty(artifact_ref, "artifact_ref")
    transport_payload: dict[str, TransportPayloadValue] = {
        "subject": target.subject,
        "stream": target.stream,
        "durable": target.durable,
    }
    if reply_to is not None:
        transport_payload["reply_to"] = reply_to
    return seal_transport_envelope(
        transport=TransportKind.NATS,
        target=target.subject,
        artifact_ref=artifact_ref,
        artifact_digest=artifact_digest,
        transport_payload=transport_payload,
        signer=signer,
        nonce=nonce,
        signed_at=signed_at,
    )


def nats_publish_message(
    envelope: SignedTransportEnvelope,
) -> dict[str, object]:
    """Render the NATS publish fields from a verified envelope.

    Does not perform I/O. Caller performs the actual publish with their own
    client. Returns the subject and serialised message dict.
    """
    if envelope.transport is not TransportKind.NATS:
        raise ValueError("envelope is not a NATS envelope")
    return {
        "subject": envelope.target,
        "stream": envelope.transport_payload.get("stream", ""),
        "durable": envelope.transport_payload.get("durable", ""),
        "reply_to": envelope.transport_payload.get("reply_to"),
        "message": envelope.model_dump(mode="json", exclude={"transport_signature"}),
    }
