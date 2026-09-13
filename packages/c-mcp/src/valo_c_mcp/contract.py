"""c-MCP v1 deterministic contract binding under a GCoP profile."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


CMCP_VERSION = "c-mcp/1"
TransportKind = Literal["http", "stdio", "sse", "websocket", "browser", "computer_use", "native", "other"]
InteractionProtocol = Literal["mcp", "a2a", "anp", "ag_ui", "api", "generated_code", "other"]
DomainProtocol = Literal["none", "ap2", "ucp", "other"]


class ProtocolStack(BaseModel):
    """Protocol layering; transport is not authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transport: TransportKind
    interaction_protocols: list[InteractionProtocol] = Field(min_length=1)
    domain_protocols: list[DomainProtocol] = Field(default_factory=lambda: ["none"])

    @field_validator("interaction_protocols", "domain_protocols")
    @classmethod
    def reject_duplicate_protocols(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate protocol values are not allowed")
        return value


def _normalise(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("naive_datetime")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, BaseModel):
        return _normalise(value.model_dump(mode="python"))
    if isinstance(value, dict):
        return {str(key): _normalise(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported_c_mcp_value:{type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


class CMCPInvocation(BaseModel):
    """Exact MCP invocation and governance context bound by the contract."""

    model_config = ConfigDict(extra="forbid")

    call_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    protocol_stack: ProtocolStack
    arguments: dict[str, Any] = Field(default_factory=dict)
    target_resource: str = Field(min_length=1)
    purpose_ref: str = Field(min_length=1)
    authority_refs: list[str] = Field(default_factory=list)
    governed_state_refs: list[str] = Field(default_factory=list)
    provenance_refs: list[str] = Field(default_factory=list)
    policy_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    delegation_chain: list[str] = Field(default_factory=list)
    execution_scope: dict[str, Any] = Field(default_factory=dict)
    allowed_effects: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    human_approval_required: bool = False
    human_approval_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CMCPContractV1(BaseModel):
    """Immutable c-MCP binding; verification never grants execution authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = CMCP_VERSION
    contract_id: str = Field(min_length=1)
    gcop_contract_id: str = Field(min_length=1)
    gcop_contract_hash: str = Field(min_length=1)
    invocation: CMCPInvocation
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime
    contract_hash: str

    @classmethod
    def bind(cls, invocation: CMCPInvocation, *, gcop_contract_id: str, gcop_contract_hash: str,
             ttl_seconds: int = 300, now: datetime | None = None, contract_id: str | None = None) -> "CMCPContractV1":
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds_must_be_positive")
        if not gcop_contract_id or not gcop_contract_hash:
            raise ValueError("gcop_binding_required")
        issued_at = now or datetime.now(timezone.utc)
        if issued_at.utcoffset() is None:
            raise ValueError("naive_datetime")
        issued_at = issued_at.astimezone(timezone.utc)
        payload = {
            "version": CMCP_VERSION,
            "contract_id": contract_id or f"cmcp:{uuid4()}",
            "gcop_contract_id": gcop_contract_id,
            "gcop_contract_hash": gcop_contract_hash,
            "invocation": invocation.model_dump(mode="python"),
            "issued_at": issued_at,
            "valid_from": issued_at,
            "valid_until": issued_at + timedelta(seconds=ttl_seconds),
        }
        return cls(**payload, contract_hash=cls._hash_payload(payload))

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        return f"sha256:{hashlib.sha256(canonical_json(payload).encode()).hexdigest()}"

    def expected_hash(self) -> str:
        return self._hash_payload(self.model_dump(mode="python", exclude={"contract_hash"}))

    def verify(self, invocation: CMCPInvocation, *, now: datetime | None = None) -> tuple[bool, str]:
        if self.version != CMCP_VERSION:
            return False, "unsupported_version"
        if not self.gcop_contract_id or not self.gcop_contract_hash:
            return False, "missing_gcop_binding"
        if any(value.utcoffset() is None for value in (self.issued_at, self.valid_from, self.valid_until)):
            return False, "naive_datetime"
        current = now or datetime.now(timezone.utc)
        if current.utcoffset() is None:
            return False, "naive_datetime"
        current = current.astimezone(timezone.utc)
        if self.valid_until <= self.valid_from:
            return False, "invalid_validity_window"
        if current < self.valid_from:
            return False, "not_yet_valid"
        if current > self.valid_until:
            return False, "expired"
        try:
            expected = self.expected_hash()
            bound = canonical_json(self.invocation)
            proposed = canonical_json(invocation)
        except (TypeError, ValueError):
            return False, "uncanonicalisable_contract"
        if not hmac.compare_digest(self.contract_hash, expected):
            return False, "contract_hash_mismatch"
        if not hmac.compare_digest(bound.encode(), proposed.encode()):
            return False, "invocation_mismatch"
        if invocation.human_approval_required and not invocation.human_approval_ref:
            return False, "missing_human_approval"
        return True, "ok"
