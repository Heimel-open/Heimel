from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from .windows_capability_adapter import (
    CommitAuthorization,
    EffectRequest,
    InvocationReceipt,
    WindowsCapabilitySurface,
    invoke_governed_windows_capability,
)


class MobilePlatform(StrEnum):
    ANDROID = "android"
    IOS = "ios"
    IPADOS = "ipados"
    HARMONYOS = "harmonyos"
    OPENHARMONY = "openharmony"


class MobileCapabilityRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    actor_id: str
    principal_id: str
    platform: MobilePlatform
    capability_id: str
    provider_id: str
    target: str
    purpose: str
    mandate_ref: str
    parameters: dict[str, Any] = {}
    device_context: dict[str, Any] = {}
    requested_at: str

    def to_effect_request(self) -> EffectRequest:
        return EffectRequest(
            request_id=self.request_id,
            actor_id=self.actor_id,
            principal_id=self.principal_id,
            surface=WindowsCapabilitySurface.APP_ACTION,
            capability_id=f"mobile:{self.platform.value}:{self.capability_id}",
            provider_id=self.provider_id,
            target=self.target,
            purpose=self.purpose,
            mandate_ref=self.mandate_ref,
            parameters={
                "mobile_parameters": self.parameters,
                "device_context": self.device_context,
            },
            requested_at=self.requested_at,
        )


Authorize = Callable[[EffectRequest, Any], CommitAuthorization]
ProviderInvoke = Callable[[EffectRequest], Any]


def invoke_governed_mobile_capability(
    request: MobileCapabilityRequest,
    *,
    authorize: Authorize,
    provider_invoke: ProviderInvoke,
    commit_time: Any,
) -> InvocationReceipt:
    """Route any mobile effect through the same commit-time Handlingsrett gate.

    OS permissions, app intents, background entitlements and device discovery are
    capability-enabling facts only. They are not authority to execute an effect.
    """

    return invoke_governed_windows_capability(
        request=request.to_effect_request(),
        authorize=authorize,
        provider_invoke=provider_invoke,
        commit_time=commit_time,
    )
