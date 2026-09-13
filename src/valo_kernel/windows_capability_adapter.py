from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .contracts.common import canonical_digest


class WindowsCapabilitySurface(StrEnum):
    MCP = "MCP"
    APP_ACTION = "APP_ACTION"


class AuthorizationDisposition(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


class EffectRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    actor_id: str
    principal_id: str
    surface: WindowsCapabilitySurface
    capability_id: str
    provider_id: str
    target: str
    purpose: str
    mandate_ref: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime

    @property
    def effect_digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))


class CommitAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    decision_id: str
    disposition: AuthorizationDisposition
    effect_digest: str
    evaluated_at: datetime
    valid_until: datetime
    reasons: tuple[str, ...] = ()
    authority_ref: str | None = None

    def is_current(self, at: datetime) -> bool:
        return self.evaluated_at <= at <= self.valid_until


class InvocationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    effect_digest: str
    decision_id: str
    disposition: AuthorizationDisposition
    invoked: bool
    committed_at: datetime
    provider_result_digest: str | None = None
    reasons: tuple[str, ...] = ()
    receipt_digest: str


Authorize = Callable[[EffectRequest, datetime], CommitAuthorization]
ProviderInvoke = Callable[[EffectRequest], Any]


def _receipt(
    *,
    request: EffectRequest,
    decision: CommitAuthorization,
    committed_at: datetime,
    invoked: bool,
    provider_result_digest: str | None = None,
    reasons: tuple[str, ...] = (),
) -> InvocationReceipt:
    payload = {
        "request_id": request.request_id,
        "effect_digest": request.effect_digest,
        "decision_id": decision.decision_id,
        "disposition": decision.disposition.value,
        "invoked": invoked,
        "committed_at": committed_at.isoformat(),
        "provider_result_digest": provider_result_digest,
        "reasons": list(reasons),
    }
    return InvocationReceipt(
        **payload,
        receipt_digest=canonical_digest(payload),
    )


def _authorization_unavailable(
    *, request: EffectRequest, commit_time: datetime
) -> CommitAuthorization:
    return CommitAuthorization(
        decision_id=canonical_digest(
            {
                "kind": "authorization-unavailable",
                "request_id": request.request_id,
                "effect_digest": request.effect_digest,
                "commit_time": commit_time.isoformat(),
            }
        ),
        disposition=AuthorizationDisposition.DENY,
        effect_digest=request.effect_digest,
        evaluated_at=commit_time,
        valid_until=commit_time,
        reasons=("AUTHORIZATION_UNAVAILABLE",),
    )


def invoke_governed_windows_capability(
    *,
    request: EffectRequest,
    authorize: Authorize,
    provider_invoke: ProviderInvoke,
    commit_time: datetime,
) -> InvocationReceipt:
    """Authorize the exact effect at consequence time, then invoke once.

    Discovery, registration, OS ACLs, MCP connectivity and App Action visibility
    are deliberately not treated as authority. The provider is unreachable from
    this path until a fresh authorization for the exact effect returns ALLOW.
    """

    try:
        decision = authorize(request, commit_time)
    except Exception:
        decision = _authorization_unavailable(request=request, commit_time=commit_time)
        return _receipt(
            request=request,
            decision=decision,
            committed_at=commit_time,
            invoked=False,
            reasons=decision.reasons,
        )

    if decision.effect_digest != request.effect_digest:
        return _receipt(
            request=request,
            decision=decision,
            committed_at=commit_time,
            invoked=False,
            reasons=("AUTHORIZATION_EFFECT_MISMATCH",),
        )

    if not decision.is_current(commit_time):
        return _receipt(
            request=request,
            decision=decision,
            committed_at=commit_time,
            invoked=False,
            reasons=("AUTHORIZATION_STALE",),
        )

    if decision.disposition is not AuthorizationDisposition.ALLOW:
        return _receipt(
            request=request,
            decision=decision,
            committed_at=commit_time,
            invoked=False,
            reasons=decision.reasons or (f"AUTHORIZATION_{decision.disposition.value}",),
        )

    result = provider_invoke(request)
    result_digest = canonical_digest(result)
    return _receipt(
        request=request,
        decision=decision,
        committed_at=commit_time,
        invoked=True,
        provider_result_digest=result_digest,
    )
