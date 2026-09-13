from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..utils.crypto import iso_format, sha256_digest, utcnow
from .assurance_strength import AssuranceCapability


class ConsequenceClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FailureOutcome(str, Enum):
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    DEFER = "DEFER"
    HALT = "HALT"


class EffectivePeriod(BaseModel):
    effective_from: datetime
    effective_until: datetime
    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_period(self) -> EffectivePeriod:
        if self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be strictly after effective_from")
        return self

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or utcnow()
        return self.effective_from <= now < self.effective_until


class AssuranceProfileV1(BaseModel):
    """Carrier-defined machine-readable assurance contract.

    CRITICAL INVARIANT: The profile is input to assurance evaluation.
    It NEVER grants execution authority.
    """

    profile_id: str
    insurer_reference: str
    coverage_condition_ref: str
    action_type: str
    consequence_class: ConsequenceClass
    required_authoritative_sources: list[str] = Field(min_length=1)
    minimum_assurance_per_source: dict[str, str] = Field(default_factory=dict)
    required_capabilities_per_source: dict[
        str, list[AssuranceCapability]
    ] = Field(default_factory=dict)
    freshness_requirements: dict[str, int] = Field(default_factory=dict)
    revocation_visibility_requirements: dict[str, str] = Field(default_factory=dict)
    failure_outcome: FailureOutcome = FailureOutcome.DENY
    profile_version: str = "1.0.0"
    effective_period: EffectivePeriod
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_profile(self) -> AssuranceProfileV1:
        if not self.profile_id or not self.profile_id.strip():
            raise ValueError("profile_id cannot be empty")
        if not self.insurer_reference or not self.insurer_reference.strip():
            raise ValueError("insurer_reference cannot be empty")
        if not self.coverage_condition_ref or not self.coverage_condition_ref.strip():
            raise ValueError("coverage_condition_ref cannot be empty")
        if not self.action_type or not self.action_type.strip():
            raise ValueError("action_type cannot be empty")
        for src in self.required_authoritative_sources:
            if not src or not src.strip():
                raise ValueError(
                    "required authoritative sources cannot contain blank entries"
                )
        return self

    @property
    def digest(self) -> str:
        """Deterministic cryptographic digest of this assurance profile."""
        payload = self.model_dump(mode="json")
        return sha256_digest(payload)

    def is_effective(self, now: datetime | None = None) -> bool:
        """Check whether the profile is within its effective operational window."""
        return self.effective_period.is_active(now)

    def to_payload(self) -> dict[str, Any]:
        """Return canonical serializable dictionary."""
        return {
            "profile_id": self.profile_id,
            "insurer_reference": self.insurer_reference,
            "coverage_condition_ref": self.coverage_condition_ref,
            "action_type": self.action_type,
            "consequence_class": self.consequence_class.value,
            "required_authoritative_sources": list(self.required_authoritative_sources),
            "minimum_assurance_per_source": dict(self.minimum_assurance_per_source),
            "required_capabilities_per_source": {
                k: [c.value for c in v]
                for k, v in self.required_capabilities_per_source.items()
            },
            "freshness_requirements": dict(self.freshness_requirements),
            "revocation_visibility_requirements": dict(
                self.revocation_visibility_requirements
            ),
            "failure_outcome": self.failure_outcome.value,
            "profile_version": self.profile_version,
            "effective_period": {
                "effective_from": iso_format(self.effective_period.effective_from),
                "effective_until": iso_format(self.effective_period.effective_until),
            },
            "metadata": dict(self.metadata),
            "profile_digest": self.digest,
        }
