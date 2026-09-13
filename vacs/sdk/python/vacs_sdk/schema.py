from dataclasses import dataclass, field
from time import time
from typing import Any

from .decision import VACSDecision, VACSStatus


@dataclass
class DelegationScope:
    allowed_tools: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    max_risk: float = 0.5
    max_amount: float | None = None
    requires_human_over: float | None = None


@dataclass
class AuthorityToken:
    issuer: str
    subject_agent: str
    tenant_id: str
    authority_id: str
    scope: DelegationScope
    issued_at: int
    expires_at: int
    revoked: bool = False
    claims: dict[str, Any] = field(default_factory=dict)

    def expired(self) -> bool:
        return int(time()) >= self.expires_at


@dataclass
class ExecutionRequest:
    agent_id: str
    tenant_id: str
    tool: str
    action: str
    risk_score: float = 0.0
    amount: float | None = None
    evidence_hash: str | None = None
    premise_authority: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    valid: bool
    status: VACSStatus
    decision: VACSDecision
    reason: str | None = None
    token: AuthorityToken | None = None


@dataclass
class Receipt:
    receipt_id: str
    timestamp: int
    request_hash: str
    decision: VACSDecision
    status: VACSStatus
    reason: str | None
    previous_hash: str | None
    receipt_hash: str
