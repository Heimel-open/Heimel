from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..utils.crypto import iso_format, sha256_digest, utcnow


class PolicyBindingV1(BaseModel):
    """Cryptographic binding linking policy condition to execution and Veritas outcome.

    Policy condition -> AssuranceProfile version -> Action -> REHT clearance ->
    RACS decision -> Execution receipt -> Veritas outcome.

    CRITICAL INVARIANT: Zero claim decisions at runtime. Pure cryptographic linking.
    """

    binding_id: str = Field(default_factory=lambda: f"bind-{uuid4()}")
    policy_condition_ref: str
    profile_version_ref: str
    profile_digest: str
    action_digest: str
    reht_clearance_ref: str
    reht_clearance_digest: str
    racs_decision_ref: str
    racs_decision_digest: str
    execution_receipt_ref: str
    execution_receipt_digest: str
    veritas_outcome_ref: str
    veritas_outcome_digest: str
    bound_at: datetime = Field(default_factory=utcnow)
    binding_hash: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def populate_hash(self) -> PolicyBindingV1:
        computed = self.compute_hash()
        if self.binding_hash is None:
            object.__setattr__(self, "binding_hash", computed)
        elif self.binding_hash != computed:
            raise ValueError("binding_hash does not match computed digest")
        return self

    def compute_hash(self) -> str:
        """Deterministic sha256 hash of the complete policy binding chain."""
        payload = {
            "policy_condition_ref": self.policy_condition_ref,
            "profile_version_ref": self.profile_version_ref,
            "profile_digest": self.profile_digest,
            "action_digest": self.action_digest,
            "reht_clearance_ref": self.reht_clearance_ref,
            "reht_clearance_digest": self.reht_clearance_digest,
            "racs_decision_ref": self.racs_decision_ref,
            "racs_decision_digest": self.racs_decision_digest,
            "execution_receipt_ref": self.execution_receipt_ref,
            "execution_receipt_digest": self.execution_receipt_digest,
            "veritas_outcome_ref": self.veritas_outcome_ref,
            "veritas_outcome_digest": self.veritas_outcome_digest,
            "bound_at": iso_format(self.bound_at),
        }
        return sha256_digest(payload)

    def to_payload(self) -> dict[str, Any]:
        """Return canonical dictionary."""
        return {
            "binding_id": self.binding_id,
            "policy_condition_ref": self.policy_condition_ref,
            "profile_version_ref": self.profile_version_ref,
            "profile_digest": self.profile_digest,
            "action_digest": self.action_digest,
            "reht_clearance_ref": self.reht_clearance_ref,
            "reht_clearance_digest": self.reht_clearance_digest,
            "racs_decision_ref": self.racs_decision_ref,
            "racs_decision_digest": self.racs_decision_digest,
            "execution_receipt_ref": self.execution_receipt_ref,
            "execution_receipt_digest": self.execution_receipt_digest,
            "veritas_outcome_ref": self.veritas_outcome_ref,
            "veritas_outcome_digest": self.veritas_outcome_digest,
            "bound_at": iso_format(self.bound_at),
            "binding_hash": self.binding_hash or self.compute_hash(),
        }
