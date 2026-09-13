from datetime import datetime, timedelta, timezone

from valo_kernel.browser_capability_bridge import BrowserEffectRequest, invoke_governed_browser_effect
from valo_kernel.mcp_capability_bridge import invoke_governed_mcp_tool, normalize_mcp_tool_call
from valo_kernel.windows_capability_adapter import AuthorizationDisposition, CommitAuthorization


def _allow(request, at):
    return CommitAuthorization(
        decision_id="allow-1",
        disposition=AuthorizationDisposition.ALLOW,
        effect_digest=request.effect_digest,
        evaluated_at=at,
        valid_until=at + timedelta(seconds=5),
        reasons=("TEST_ALLOW",),
        authority_ref="test:authority",
    )


def _deny(request, at):
    return CommitAuthorization(
        decision_id="deny-1",
        disposition=AuthorizationDisposition.DENY,
        effect_digest=request.effect_digest,
        evaluated_at=at,
        valid_until=at,
        reasons=("TEST_DENY",),
        authority_ref="test:authority",
    )


def test_mcp_deny_never_reaches_tool_provider():
    at = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    request = normalize_mcp_tool_call(
        request_id="mcp-1",
        actor_id="agent",
        principal_id="user",
        server_id="filesystem",
        tool_name="write_file",
        arguments={"path": "x.txt", "content": "blocked"},
        purpose="test",
        mandate_ref="test:mandate",
        requested_at=at,
    )
    calls = []

    receipt = invoke_governed_mcp_tool(
        request=request,
        authorize=_deny,
        invoke=lambda server, tool, args: calls.append((server, tool, args)),
        commit_time=at,
    )

    assert receipt.invoked is False
    assert receipt.disposition == AuthorizationDisposition.DENY
    assert calls == []


def test_mcp_allow_invokes_exact_tool_once():
    at = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    request = normalize_mcp_tool_call(
        request_id="mcp-2",
        actor_id="agent",
        principal_id="user",
        server_id="calendar",
        tool_name="create_event",
        arguments={"title": "Demo"},
        purpose="create requested event",
        mandate_ref="user:interactive",
        requested_at=at,
    )
    calls = []

    receipt = invoke_governed_mcp_tool(
        request=request,
        authorize=_allow,
        invoke=lambda server, tool, args: calls.append((server, tool, args)) or {"ok": True},
        commit_time=at,
    )

    assert receipt.invoked is True
    assert calls == [("calendar", "create_event", {"title": "Demo"})]


def test_browser_deny_never_reaches_browser_provider():
    at = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    request = BrowserEffectRequest(
        request_id="browser-1",
        actor_id="browser-extension",
        principal_id="user",
        capability_id="browser:submit-form",
        target="https://example.test/form",
        purpose="submit form",
        mandate_ref="browser:interactive",
        parameters={"field": "value"},
        browser_context={"tab_id": 1},
        requested_at=at,
    )
    calls = []

    receipt = invoke_governed_browser_effect(
        request=request,
        authorize=_deny,
        invoke=lambda req: calls.append(req),
        commit_time=at,
    )

    assert receipt.invoked is False
    assert receipt.disposition == AuthorizationDisposition.DENY
    assert calls == []


def test_browser_allow_invokes_once_and_carries_context_into_effect_digest():
    at = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)
    request = BrowserEffectRequest(
        request_id="browser-2",
        actor_id="browser-extension",
        principal_id="user",
        capability_id="browser:navigate",
        target="https://example.test/next",
        purpose="navigate",
        mandate_ref="browser:interactive",
        browser_context={"tab_id": 7, "url": "https://example.test/start"},
        requested_at=at,
    )
    calls = []

    receipt = invoke_governed_browser_effect(
        request=request,
        authorize=_allow,
        invoke=lambda req: calls.append(req) or {"navigated": True},
        commit_time=at,
    )

    assert receipt.invoked is True
    assert len(calls) == 1
    assert receipt.effect_digest
