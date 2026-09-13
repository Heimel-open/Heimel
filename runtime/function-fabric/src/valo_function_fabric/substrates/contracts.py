from __future__ import annotations

import json
import re
from enum import Enum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contracts.common import RiskClass


class OperationClass(str, Enum):
    OBSERVE = "OBSERVE"
    MUTATE = "MUTATE"
    FINANCIAL = "FINANCIAL"
    PRODUCTION = "PRODUCTION"


class CapabilityStability(str, Enum):
    STABLE = "STABLE"
    EXPERIMENTAL = "EXPERIMENTAL"


class SurfaceKind(str, Enum):
    MANIFEST = "MANIFEST"
    CLI = "CLI"
    MCP = "MCP"
    SKILL = "SKILL"
    PROGRAMMATIC = "PROGRAMMATIC"


class CredentialReference(BaseModel):
    """Reference to a credential location. Secret values are never part of the contract."""

    env_var: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_env_var(self) -> CredentialReference:
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", self.env_var):
            raise ValueError("env_var must be an environment-variable name, never a secret value")
        return self


class ExternalCapability(BaseModel):
    """Governed binding to one capability on an external programmable substrate."""

    capability_id: str
    provider: str
    description: str
    operation_class: OperationClass
    stability: CapabilityStability = CapabilityStability.STABLE
    risk_class: RiskClass
    authority_capability: str
    scope_keys: tuple[str, ...] = ()
    provider_argv_prefix: tuple[str, ...]
    external_effects: tuple[str, ...] = ()
    requires_reht: bool = True
    requires_step_up: bool = False
    verify_external_effect: bool = False
    source_url: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def read_only(self) -> bool:
        return self.operation_class == OperationClass.OBSERVE

    @model_validator(mode="after")
    def validate_governance(self) -> ExternalCapability:
        if not self.capability_id or "@" in self.capability_id:
            raise ValueError("capability_id must be non-empty and must not contain '@'")
        if not self.provider_argv_prefix:
            raise ValueError("provider_argv_prefix is required")
        if not self.authority_capability:
            raise ValueError("authority_capability is required for external execution")
        if not self.requires_reht:
            raise ValueError("external capabilities may not bypass REHT")
        if self.read_only and self.external_effects:
            raise ValueError("OBSERVE capabilities cannot declare external effects")
        if not self.read_only and not self.external_effects:
            raise ValueError("mutating capabilities must declare external effects")
        if not self.read_only and not self.verify_external_effect:
            raise ValueError("mutating capabilities require external effect verification")
        high_risk = self.risk_class in {
            RiskClass.R3_FINANCIAL_LEGAL,
            RiskClass.R4_RIGHTS_IMPACTING,
            RiskClass.R5_SAFETY_CRITICAL,
        }
        if (
            self.operation_class in {OperationClass.FINANCIAL, OperationClass.PRODUCTION}
            or high_risk
            or self.stability == CapabilityStability.EXPERIMENTAL
        ) and not self.requires_step_up:
            raise ValueError("sensitive external capabilities require step-up")
        return self


class SurfaceProjection(BaseModel):
    """Generated descriptor for one agent-facing surface.

    This is metadata, not an alternate execution path. All surfaces resolve back
    to the same ExternalCapability and therefore the same REHT requirement.
    Programmatic calling is composition-only and cannot enable direct execution.
    """

    kind: SurfaceKind
    capability_id: str
    name: str
    provider_argv_prefix: tuple[str, ...]
    read_only: bool
    authority_capability: str
    scope_keys: tuple[str, ...]
    requires_reht: bool
    requires_step_up: bool
    verify_external_effect: bool
    source_manifest_hash: str
    direct_execution: bool = False
    state_recheck_required: bool = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_surface_governance(self) -> SurfaceProjection:
        if self.direct_execution:
            raise ValueError("agent-facing surfaces cannot execute external capabilities directly")
        if not self.requires_reht:
            raise ValueError("agent-facing surfaces cannot bypass REHT")
        if self.kind == SurfaceKind.PROGRAMMATIC and not self.state_recheck_required:
            raise ValueError("programmatic calling requires execution-time state re-check")
        return self


class ExternalSubstrate(BaseModel):
    """One programmable external business system and its governed capabilities."""

    schema_version: str = "valo.external-substrate.v1"
    provider: str
    manifest_command: tuple[str, ...]
    mcp_registration_command: tuple[str, ...]
    skill_generation_command: tuple[str, ...]
    credential: CredentialReference
    capabilities: tuple[ExternalCapability, ...] = Field(default_factory=tuple)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_capabilities(self) -> ExternalSubstrate:
        ids = [cap.capability_id for cap in self.capabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("capability_id values must be unique")
        if any(cap.provider != self.provider for cap in self.capabilities):
            raise ValueError("every capability provider must match substrate provider")
        return self

    def capability(self, capability_id: str) -> ExternalCapability:
        for capability in self.capabilities:
            if capability.capability_id == capability_id:
                return capability
        raise KeyError(capability_id)

    def machine_manifest(self) -> dict[str, object]:
        capabilities = [
            cap.model_dump(mode="json")
            for cap in sorted(self.capabilities, key=lambda item: item.capability_id)
        ]
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "discovery": {
                "manifest": list(self.manifest_command),
                "mcp_registration": list(self.mcp_registration_command),
                "skill_generation": list(self.skill_generation_command),
            },
            "credential": self.credential.model_dump(mode="json"),
            "capabilities": capabilities,
        }

    @property
    def manifest_hash(self) -> str:
        raw = json.dumps(
            self.machine_manifest(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        return sha256(raw).hexdigest()

    def project(self, capability_id: str) -> tuple[SurfaceProjection, ...]:
        capability = self.capability(capability_id)
        manifest_hash = self.manifest_hash
        names = {
            SurfaceKind.MANIFEST: capability.capability_id,
            SurfaceKind.CLI: " ".join(capability.provider_argv_prefix),
            SurfaceKind.MCP: _surface_name(capability.capability_id),
            SurfaceKind.SKILL: capability.capability_id,
            SurfaceKind.PROGRAMMATIC: _surface_name(capability.capability_id),
        }
        return tuple(
            SurfaceProjection(
                kind=kind,
                capability_id=capability.capability_id,
                name=names[kind],
                provider_argv_prefix=capability.provider_argv_prefix,
                read_only=capability.read_only,
                authority_capability=capability.authority_capability,
                scope_keys=capability.scope_keys,
                requires_reht=capability.requires_reht,
                requires_step_up=capability.requires_step_up,
                verify_external_effect=capability.verify_external_effect,
                source_manifest_hash=manifest_hash,
            )
            for kind in SurfaceKind
        )


def _surface_name(capability_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", capability_id)
