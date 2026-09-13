from datetime import UTC, datetime, timedelta

import pytest

from valo_kernel.mobile_capability_adapter import (
    MobileCapabilityRequest,
    MobilePlatform,
    invoke_governed_mobile_capability,
)
from valo_kernel.windows_capability_adapter import (
    AuthorizationDisposition,
    CommitAuthorization,
)


def _request(platform: MobilePlatform) -> MobileCapabilityRequest:
    return MobileCapabilityRequest(
        request_id="mobile-1",
        actor_id="mobile-agent",
        principal_id="user-1",
        platform=platform,
        capability_id="calendar.write",
        provider_id=f"{platform.value}.calendar",
        target="calendar://event/123",
        purpose="schedule approved meeting",
        mandate_ref="mandate:calendar:1",
        parameters={"title": "VALO review"},
        device_context={"device_id": "device-1", "foreground": True},
        requested_at="2026-09-03T15:00:00Z",
    )


@pytest.mark.parametrize(
    "platform",
    [
        MobilePlatform.ANDROID,
        MobilePlatform.IOS,
        MobilePlatform.IPADOS,
        MobilePlatform.HARMONYOS,
        MobilePlatform.OPENHARMONY,
    ],
)
def test_mobile_allow_invokes_provider(platform: MobilePlatform):
    request = _request(platform)
    effect = request.to_effect_request()
    commit_time = datetime(2026, 9, 3, 15, 0, tzinfo=UTC)
    calls = []

    def authorize(effect_request, at):
        return CommitAuthorization(
            decision_id="decision-allow",
            disposition=AuthorizationDisposition.ALLOW,
            effect_digest=effect_request.effect_digest,
            evaluated_at=at,
            valid_until=at + timedelta(seconds=5),
            reasons=("AUTHORIZED",),
            authority_ref="authority:1",
        )

    def provider(effect_request):
        calls.append(effect_request)
        return {"ok": True}

    receipt = invoke_governed_mobile_capability(
        request,
        authorize=authorize,
        provider_invoke=provider,
        commit_time=commit_time,
    )

    assert receipt.invoked is True
    assert len(calls) == 1
    assert effect.capability_id.startswith(f"mobile:{platform.value}:")


@pytest.mark.parametrize("disposition", [AuthorizationDisposition.DENY, AuthorizationDisposition.ESCALATE])
def test_mobile_non_allow_never_invokes_provider(disposition):
    request = _request(MobilePlatform.ANDROID)
    commit_time = datetime(2026, 9, 3, 15, 0, tzinfo=UTC)
    invoked = False

    def authorize(effect_request, at):
        return CommitAuthorization(
            decision_id="decision-block",
            disposition=disposition,
            effect_digest=effect_request.effect_digest,
            evaluated_at=at,
            valid_until=at + timedelta(seconds=5),
            reasons=("NOT_AUTHORIZED",),
            authority_ref="authority:1",
        )

    def provider(_effect_request):
        nonlocal invoked
        invoked = True
        return {"ok": True}

    receipt = invoke_governed_mobile_capability(
        request,
        authorize=authorize,
        provider_invoke=provider,
        commit_time=commit_time,
    )

    assert receipt.invoked is False
    assert invoked is False
