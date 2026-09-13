"""Strict publication action contract for governed content operations.

This module defines the immutable payload that must be cleared before an
external publication mutation. It prepares deterministic bindings only. It
does not evaluate, clear, authorize, or execute an action.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Any

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.action_envelope.models import ActionType
from src.valo_platform.decision_governance.action_case import ActionCaseRecord


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _validate_sha256(value: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("digest must be lowercase sha256:<64 hex>")
    return value


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


class PublicationPrivacy(str, Enum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class PublicationRollback(str, Enum):
    UNPUBLISH = "unpublish"
    DELETE = "delete"
    NONE = "none"


class PublicationArtifact(BaseModel):
    """Immutable reference to an exact media artefact."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    artifact_ref: str = Field(min_length=1)
    digest: str
    media_type: str | None = None

    @field_validator("digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value)


class PublicationAction(BaseModel):
    """Exact external publication mutation proposed for clearance."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    tenant_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    delegated_mandate_ref: str = Field(min_length=1)

    provider: str = Field(min_length=1)
    account_ref: str = Field(min_length=1)
    channel_ref: str = Field(min_length=1)

    video: PublicationArtifact
    title: str = Field(min_length=1)
    description: str = ""
    tags: tuple[str, ...] = ()
    language: str = Field(min_length=1)
    audiences: tuple[str, ...] = Field(min_length=1)
    jurisdictions: tuple[str, ...] = Field(min_length=1)
    privacy_status: PublicationPrivacy
    scheduled_for: datetime | None = None
    made_for_kids: bool

    captions: tuple[PublicationArtifact, ...] = ()
    thumbnail: PublicationArtifact | None = None

    source_refs: tuple[str, ...] = Field(min_length=1)
    claim_evidence_refs: tuple[str, ...] = Field(min_length=1)
    rights_evidence_refs: tuple[str, ...] = Field(min_length=1)
    policy_refs: tuple[str, ...] = Field(min_length=1)
    policy_snapshot_digest: str

    rollback_capability: PublicationRollback
    idempotency_key: str = Field(min_length=1)

    @field_validator(
        "tags",
        "audiences",
        "jurisdictions",
        "source_refs",
        "claim_evidence_refs",
        "rights_evidence_refs",
        "policy_refs",
        mode="before",
    )
    @classmethod
    def normalize_string_collections(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            raw = [value]
        else:
            raw = list(value)
        normalized: set[str] = set()
        for item in raw:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("string collections may contain only non-empty strings")
            normalized.add(item.strip())
        return tuple(sorted(normalized))

    @field_validator("policy_snapshot_digest")
    @classmethod
    def validate_policy_digest(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("scheduled_for")
    @classmethod
    def require_aware_schedule(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("scheduled_for must be timezone-aware")
        return value

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        """Digest every publication field that may affect the external mutation."""

        return _digest(self.canonical_payload())

    def target_digest(self) -> str:
        """Digest only the exact destination identity."""

        return _digest(
            {
                "tenant_id": self.tenant_id,
                "provider": self.provider,
                "account_ref": self.account_ref,
                "channel_ref": self.channel_ref,
            }
        )


class PublicationActionCase(BaseModel):
    """Publication-specific composition over the canonical Action Case record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action_case: ActionCaseRecord
    publication: PublicationAction

    @model_validator(mode="after")
    def validate_canonical_bindings(self) -> "PublicationActionCase":
        if self.action_case.action_class != ActionType.EXTERNAL_PUBLICATION:
            raise ValueError(
                "publication contract requires ActionType.EXTERNAL_PUBLICATION"
            )
        if self.action_case.tenant_id != self.publication.tenant_id:
            raise ValueError("publication tenant does not match canonical Action Case")
        _validate_sha256(self.action_case.case_hash)

        bound_evidence = set(self.publication.source_refs)
        bound_evidence.update(self.publication.claim_evidence_refs)
        bound_evidence.update(self.publication.rights_evidence_refs)
        missing = set(self.action_case.evidence_refs) - bound_evidence
        if missing:
            raise ValueError(
                "publication payload does not bind canonical Action Case evidence: "
                + ", ".join(sorted(missing))
            )
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "action_case_ref": {
                "case_id": self.action_case.case_id,
                "tenant_id": self.action_case.tenant_id,
                "case_hash": self.action_case.case_hash,
                "record_version": self.action_case.record_version,
            },
            "publication": self.publication.canonical_payload(),
        }

    def digest(self) -> str:
        """Exact payload digest to bind into a CommitToken."""

        return _digest(self.canonical_payload())

    def target_digest(self) -> str:
        return self.publication.target_digest()
