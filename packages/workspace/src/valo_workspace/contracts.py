"""Bounded workspace contracts; none of these types grant execution authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Literal, Mapping

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _canonical_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def canonical_digest(value: Any) -> str:
    return f"sha256:{sha256(rfc8785.dumps(_canonical_value(value))).hexdigest()}"


def _aware(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value


def _unique(values: list[str], label: str) -> list[str]:
    if any(not value.strip() for value in values):
        raise ValueError(f"{label} must not contain blank values")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must contain unique values")
    return values


class ResourceLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    cpu_millis: int = Field(gt=0)
    memory_mb: int = Field(gt=0)
    wall_time_seconds: int = Field(gt=0)


class ExposurePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    filesystem_roots: tuple[str, ...] = ()
    network_endpoints: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()

    @field_validator("filesystem_roots", "network_endpoints", "tools")
    @classmethod
    def validate_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(list(value), "exposure values")
        return value


class GovernedWorkspaceContract(BaseModel):
    """A bounded workspace description, never an execution grant."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    spec_version: Literal["valo.governed-workspace/v1"] = "valo.governed-workspace/v1"
    workspace_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    worker_id: str = Field(min_length=1)
    governed_state_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    presented_capabilities: tuple[str, ...] = ()
    exposure: ExposurePolicy
    resources: ResourceLimits
    isolation: Literal["process", "container", "vm", "wasm", "provider-defined"]
    valid_from: datetime
    valid_until: datetime
    require_runtime_digest: bool = True
    require_return_provenance: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("governed_state_refs", "provenance_refs", "presented_capabilities")
    @classmethod
    def validate_refs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(list(value), "workspace references")
        return value

    @field_validator("valid_from", "valid_until")
    @classmethod
    def validate_time(cls, value: datetime) -> datetime:
        return _aware(value, "workspace validity timestamp")

    @model_validator(mode="after")
    def validate_window(self) -> "GovernedWorkspaceContract":
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        return self


class WorkspaceDeliveryEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    spec_version: Literal["valo.governed-workspace-delivery/v1"] = (
        "valo.governed-workspace-delivery/v1"
    )
    workspace_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)
    runtime_digest: str | None = None
    realized_isolation: Literal[
        "process", "container", "vm", "wasm", "provider-defined"
    ]
    filesystem_roots: tuple[str, ...] = ()
    network_endpoints: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    presented_capabilities: tuple[str, ...] = ()
    delivered_at: datetime
    expires_at: datetime
    hidden_retries_enabled: bool = False
    return_provenance_supported: bool = True
    evidence_refs: tuple[str, ...] = ()

    @field_validator("delivered_at", "expires_at")
    @classmethod
    def validate_time(cls, value: datetime) -> datetime:
        return _aware(value, "delivery timestamp")


@dataclass(frozen=True)
class ConformanceResult:
    conformant: bool
    violations: tuple[str, ...]


def verify_delivery(
    contract: GovernedWorkspaceContract,
    evidence: WorkspaceDeliveryEvidence,
    *,
    now: datetime | None = None,
) -> ConformanceResult:
    """Check for scope widening; this never authorizes execution."""

    current = _aware(now or datetime.now(timezone.utc), "verification time")
    violations: list[str] = []
    checks: tuple[tuple[bool, str], ...] = (
        (evidence.workspace_id != contract.workspace_id, "workspace_id_mismatch"),
        (evidence.realized_isolation != contract.isolation, "isolation_mismatch"),
        (
            not set(evidence.filesystem_roots).issubset(
                contract.exposure.filesystem_roots
            ),
            "filesystem_scope_widened",
        ),
        (
            not set(evidence.network_endpoints).issubset(
                contract.exposure.network_endpoints
            ),
            "network_scope_widened",
        ),
        (
            not set(evidence.tools).issubset(contract.exposure.tools),
            "tool_scope_widened",
        ),
        (
            not set(evidence.presented_capabilities).issubset(
                contract.presented_capabilities
            ),
            "capability_scope_widened",
        ),
        (
            contract.require_runtime_digest and not evidence.runtime_digest,
            "runtime_digest_missing",
        ),
        (
            contract.require_return_provenance
            and not evidence.return_provenance_supported,
            "return_provenance_not_supported",
        ),
        (evidence.hidden_retries_enabled, "hidden_retries_enabled"),
        (evidence.delivered_at < contract.valid_from, "delivered_before_valid_from"),
        (evidence.delivered_at >= contract.valid_until, "delivered_outside_validity"),
        (evidence.expires_at > contract.valid_until, "delivery_lifetime_widened"),
        (current >= contract.valid_until, "contract_expired"),
        (current >= evidence.expires_at, "delivery_expired"),
    )
    violations.extend(reason for failed, reason in checks if failed)
    return ConformanceResult(not violations, tuple(violations))
