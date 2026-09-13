from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any, TypeVar

SCHEMA_VERSION = "vwsf-v1"
PACK_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*:[A-Za-z][A-Za-z0-9_.-]*$")
EnumT = TypeVar("EnumT", bound=Enum)


def utcnow() -> datetime:
    return datetime.now(UTC)


def canonical_bytes(value: Any) -> bytes:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode()
    return raw


def canonical_digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def normalize_extensible_type(
    value: Any,
    core_enum: type[EnumT],
    *,
    label: str,
) -> EnumT | str:
    if isinstance(value, core_enum):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a core enum or namespaced pack type")
    try:
        return core_enum(value)
    except ValueError:
        if not PACK_TYPE_PATTERN.fullmatch(value):
            raise ValueError(
                f"custom {label} must be namespaced as '<pack>:<Type>'"
            ) from None
        return value


class TruthStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    ASSERTED = "ASSERTED"
    INFERRED = "INFERRED"
    CONFLICTED = "CONFLICTED"
    STALE = "STALE"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


EXECUTION_SAFE_TRUTH = frozenset({TruthStatus.CONFIRMED})


class EvidenceStatus(str, Enum):
    RECEIVED = "RECEIVED"
    UNVERIFIED = "UNVERIFIED"
    ADMITTED = "ADMITTED"
    CONTRADICTED = "CONTRADICTED"
    QUARANTINED = "QUARANTINED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class ResourceState(str, Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    RESERVED = "RESERVED"
    ALLOCATED = "ALLOCATED"
    CONSUMED = "CONSUMED"
    UNAVAILABLE = "UNAVAILABLE"


class ExecutionPhase(str, Enum):
    INTENDED = "INTENDED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTION_REQUESTED = "EXECUTION_REQUESTED"
    EXECUTION_OBSERVED = "EXECUTION_OBSERVED"
    EFFECT_VERIFIED = "EFFECT_VERIFIED"


class EntityType(str, Enum):
    PERSON = "Person"
    ORGANIZATION = "Organization"
    LEGAL_ENTITY = "LegalEntity"
    AGENT = "Agent"
    SERVICE_IDENTITY = "ServiceIdentity"
    LOCATION = "Location"
    ASSET = "Asset"
    ACCOUNT = "Account"
    CASE = "Case"
    JOB = "Job"
    CONTRACT = "Contract"
    RESOURCE = "Resource"


class RelationType(str, Enum):
    EMPLOYED_BY = "EMPLOYED_BY"
    REPRESENTS = "REPRESENTS"
    OWNS = "OWNS"
    BELONGS_TO = "BELONGS_TO"
    REPORTS_TO = "REPORTS_TO"
    CONTRACTED_BY = "CONTRACTED_BY"
    AUTHORIZED_FOR = "AUTHORIZED_FOR"
    RESPONSIBLE_FOR = "RESPONSIBLE_FOR"
    LOCATED_AT = "LOCATED_AT"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"
