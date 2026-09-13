from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RetryPolicy(BaseModel):
    max_attempts: int = 1
    backoff_seconds: float = 0.0
    timeout_seconds: float | None = None
    retry_after_timeout: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check(self) -> RetryPolicy:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be >= 0")
        return self


class IdempotencyPolicy(BaseModel):
    require_key: bool = False
    key_source: str | None = None  # node input/output field used to derive the key
    verify_before_replay: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityRequirements(BaseModel):
    capability: str
    scope: list[str] = Field(default_factory=list)
    require_fresh_context: bool = True

    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRequirements(BaseModel):
    required_types: list[str] = Field(default_factory=list)
    minimum_status: str = "RECEIVED"  # e.g. ADMITTED, VERIFIED

    model_config = ConfigDict(extra="forbid", frozen=True)


class RightsRequirements(BaseModel):
    required_rights: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)


class NodePolicies(BaseModel):
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    idempotency: IdempotencyPolicy = Field(default_factory=IdempotencyPolicy)
    authority: AuthorityRequirements | None = None
    evidence: EvidenceRequirements | None = None
    rights: RightsRequirements | None = None
    purpose_requirement: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)
