from datetime import datetime, timedelta, timezone

import pytest

from valo_kernel.windows_capability_adapter import (
    AuthorizationDisposition,
    CommitAuthorization,
    EffectRequest,
    WindowsCapabilitySurface,
    invoke_governed_windows_capability,
)


NOW = datetime(2026, 9, 3, 13, 45, tzinfo=timezone.utc)


def _request() -> EffectRequest:
    return EffectRequest(
        request_id="req-1",
        actor_id="agent-1",
        principal_id="person-1",
        surface=WindowsCapabilitySurface.APP_ACTION,
        capability_id="files.write",
        provider_id="windows.app-actions",
        target="file:///documents/report.txt",
        purpose="update-report",
        mandate_ref="mandate-7",
        parameters={"content": "updated"},
        requested_at=NOW - timedelta(seconds=5),
    )


def _decision(
    request: EffectRequest,
    disposition: AuthorizationDisposition,
    *,
    effect_digest: str | None = None,
    evaluated_at: datetime | None = None,
    valid_until: datetime | None = None,
) -> CommitAuthorization:
    return CommitAuthorization(
        decision_id=f"decision-{disposition.value.lower()}",
        disposition=disposition,
        effect_digest=effect_digest or request.effect_digest,
        evaluated_at=evaluated_at or NOW,
        valid_until=valid_until or NOW + timedelta(seconds=30),
        reasons=() if disposition is AuthorizationDisposition.ALLOW else ("POLICY",),
        authority_ref="authority-1",
    )


def test_allow_invokes_provider_once_and_emits_receipt() -> None:
    request = _request()
    calls: list[str] = []

    receipt = invoke_governed_windows_capability(
        request=request,
        authorize=lambda req, at: _decision(req, AuthorizationDisposition.ALLOW),
        provider_invoke=lambda req: calls.append(req.request_id) or {"ok": True},
        commit_time=NOW,
    )

    assert calls == ["req-1"]
    assert receipt.invoked is True
    assert receipt.disposition is AuthorizationDisposition.ALLOW
    assert receipt.provider_result_digest is not None
    assert receipt.receipt_digest


@pytest.mark.parametrize(
    "disposition",
    [AuthorizationDisposition.DENY, AuthorizationDisposition.ESCALATE],
)
def test_non_allow_never_reaches_provider(disposition: AuthorizationDisposition) -> None:
    request = _request()
    called = False

    def provider(_: EffectRequest) -> dict[str, bool]:
        nonlocal called
        called = True
        return {"ok": True}

    receipt = invoke_governed_windows_capability(
        request=request,
        authorize=lambda req, at: _decision(req, disposition),
        provider_invoke=provider,
        commit_time=NOW,
    )

    assert called is False
    assert receipt.invoked is False
    assert receipt.disposition is disposition


def test_stale_authorization_fails_closed() -> None:
    request = _request()
    called = False

    def provider(_: EffectRequest) -> None:
        nonlocal called
        called = True

    receipt = invoke_governed_windows_capability(
        request=request,
        authorize=lambda req, at: _decision(
            req,
            AuthorizationDisposition.ALLOW,
            evaluated_at=NOW - timedelta(minutes=2),
            valid_until=NOW - timedelta(seconds=1),
        ),
        provider_invoke=provider,
        commit_time=NOW,
    )

    assert called is False
    assert receipt.invoked is False
    assert receipt.reasons == ("AUTHORIZATION_STALE",)


def test_authorization_for_different_effect_fails_closed() -> None:
    request = _request()
    called = False

    def provider(_: EffectRequest) -> None:
        nonlocal called
        called = True

    receipt = invoke_governed_windows_capability(
        request=request,
        authorize=lambda req, at: _decision(
            req,
            AuthorizationDisposition.ALLOW,
            effect_digest="sha256:not-this-effect",
        ),
        provider_invoke=provider,
        commit_time=NOW,
    )

    assert called is False
    assert receipt.invoked is False
    assert receipt.reasons == ("AUTHORIZATION_EFFECT_MISMATCH",)


def test_unavailable_authority_fails_closed_with_receipt() -> None:
    request = _request()
    called = False

    def authorize(_: EffectRequest, __: datetime) -> CommitAuthorization:
        raise RuntimeError("authority store unavailable")

    def provider(_: EffectRequest) -> None:
        nonlocal called
        called = True

    receipt = invoke_governed_windows_capability(
        request=request,
        authorize=authorize,
        provider_invoke=provider,
        commit_time=NOW,
    )

    assert called is False
    assert receipt.invoked is False
    assert receipt.disposition is AuthorizationDisposition.DENY
    assert receipt.reasons == ("AUTHORIZATION_UNAVAILABLE",)
    assert receipt.receipt_digest


def test_authorizer_receives_exact_commit_time() -> None:
    request = _request()
    observed: list[datetime] = []

    def authorize(req: EffectRequest, at: datetime) -> CommitAuthorization:
        observed.append(at)
        return _decision(req, AuthorizationDisposition.ALLOW)

    invoke_governed_windows_capability(
        request=request,
        authorize=authorize,
        provider_invoke=lambda req: {"ok": True},
        commit_time=NOW,
    )

    assert observed == [NOW]
