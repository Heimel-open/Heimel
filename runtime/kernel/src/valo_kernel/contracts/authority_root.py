from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import canonical_digest


class AuthorityRootBinding(BaseModel):
    schema_version: Literal["authority_root_binding.v1"] = "authority_root_binding.v1"
    root_id: str
    principal_id: str
    identity_artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    governance_artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    recovery_plan_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    credential_epoch: int = Field(ge=0)
    principal_is_authority_root: Literal[True] = True
    credentials_rotatable: Literal[True] = True
    compute_location_confers_authority: Literal[False] = False
    hardware_endorsement_confers_authority: Literal[False] = False
    provider_account_confers_authority: Literal[False] = False
    model_identity_confers_authority: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    root_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"root_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_root(self) -> AuthorityRootBinding:
        if not self.root_id or not self.principal_id:
            raise ValueError("authority root identity and principal are required")
        if self.root_digest and self.root_digest != self.computed_digest:
            raise ValueError("authority root binding digest mismatch")
        return self
