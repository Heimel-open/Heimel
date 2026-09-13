from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from .windows_capability_adapter import (
    CommitAuthorization,
    EffectRequest,
    InvocationReceipt,
    invoke_governed_windows_capability,
)


class BrowserEffectRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    actor_id: str
    principal_id: str
    capability_id: str
    provider_id: str = "browser"
    target: str
    purpose: str
    mandate_ref: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    browser_context: dict[str, Any] = Field(default_factory=dict)


Authorize = Callable[[EffectRequest, datetime], CommitAuthorization]
BrowserInvoke = Callable[[BrowserEffectRequest], Any]


def normalize_browser_effect(request: BrowserEffectRequest) -> EffectRequest:
    return EffectRequest(
        request_id=request.request_id,
        actor_id=request.actor_id,
        principal_id=request.principal_id,
        surface="APP_ACTION",
        capability_id=request.capability_id,
        provider_id=request.provider_id,
        target=request.target,
        purpose=request.purpose,
        mandate_ref=request.mandate_ref,
        parameters={
            **request.parameters,
            "_browser_context": request.browser_context,
        },
        requested_at=request.requested_at,
    )


def invoke_governed_browser_effect(
    *,
    request: BrowserEffectRequest,
    authorize: Authorize,
    invoke: BrowserInvoke,
    commit_time: datetime,
) -> InvocationReceipt:
    normalized = normalize_browser_effect(request)

    def provider(_: EffectRequest) -> Any:
        return invoke(request)

    return invoke_governed_windows_capability(
        request=normalized,
        authorize=authorize,
        provider_invoke=provider,
        commit_time=commit_time,
    )
