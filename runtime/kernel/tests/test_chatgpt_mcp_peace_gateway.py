from datetime import datetime, timedelta, timezone

from valo_kernel.integrations.chatgpt_mcp import (
    ChatGPTMcpContext,
    invoke_governed_chatgpt_mcp_action,
    normalize_chatgpt_mcp_action,
)
from valo_kernel.windows_capability_adapter import AuthorizationDisposition, CommitAuthorization


def _allow(request, at):
    return CommitAuthorization(
        decision_id="allow-chatgpt-mcp",
        disposition=AuthorizationDisposition.ALLOW,
        effect_digest=request.effect_digest,
        evaluated_at=at,
        valid_until=at + timedelta(seconds=5),
        reasons=("TEST_ALLOW",),
        authority_ref="test:fresh-authority",
    )


def _deny(request, at):
    return CommitAuthorization(
        decision_id="deny-chatgpt-mcp",
        disposition=AuthorizationDisposition.DENY,
        effect_digest=request.effect_digest,
        evaluated_at=at,
        valid_until=at,
        reasons=("TEST_DENY",),
        authority_ref="test:fresh-authority",
    )


def _request(at, *, confirmed=True, arguments=None):
    return normalize_chatgpt_mcp_action(
        request_id="cgpt-mcp-1",
        actor_id="chatgpt",
        principal_id="user-1",
        server_id="crm.example",
        tool_name="update_contact",
        arguments=arguments or {"contact_id": "42", "status": "active"},
        purpose="update requested contact",
        mandate_ref="interactive:user-request",
        chatgpt=ChatGPTMcpContext(
            app_id="crm-app",
            workspace_id="workspace-1",
            frozen_tool_snapshot="snapshot-v7",
            action_enabled=True,
            user_confirmed=confirmed,
            conversation_ref="conversation-9",
        ),
        requested_at=at,
    )


def test_chatgpt_confirmation_does_not_bypass_fresh_deny():
    at = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
    request = _request(at, confirmed=True)
    calls = []

    receipt = invoke_governed_chatgpt_mcp_action(
        request=request,
        authorize=_deny,
        invoke=lambda server, tool, args: calls.append((server, tool, args)),
        commit_time=at,
    )

    assert receipt.invoked is False
    assert receipt.disposition == AuthorizationDisposition.DENY
    assert calls == []


def test_chatgpt_workspace_action_enablement_does_not_mint_authority():
    at = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
    request = _request(at)
    calls = []

    receipt = invoke_governed_chatgpt_mcp_action(
        request=request,
        authorize=_deny,
        invoke=lambda server, tool, args: calls.append((server, tool, args)),
        commit_time=at,
    )

    assert request.parameters["chatgpt_context"]["action_enabled"] is True
    assert receipt.invoked is False
    assert calls == []


def test_fresh_allow_invokes_exact_original_mcp_arguments_once():
    at = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
    arguments = {"contact_id": "42", "status": "active"}
    request = _request(at, arguments=arguments)
    calls = []

    receipt = invoke_governed_chatgpt_mcp_action(
        request=request,
        authorize=_allow,
        invoke=lambda server, tool, args: calls.append((server, tool, args)) or {"ok": True},
        commit_time=at,
    )

    assert receipt.invoked is True
    assert calls == [("crm.example", "update_contact", arguments)]
    assert receipt.provider_result_digest
    assert receipt.receipt_digest


def test_changing_chatgpt_context_changes_effect_digest():
    at = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
    confirmed = _request(at, confirmed=True)
    unconfirmed = _request(at, confirmed=False)

    assert confirmed.effect_digest != unconfirmed.effect_digest


def test_mismatched_authorization_never_reaches_provider():
    at = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
    request = _request(at)
    calls = []

    def mismatched(req, when):
        return CommitAuthorization(
            decision_id="wrong-effect",
            disposition=AuthorizationDisposition.ALLOW,
            effect_digest="not-the-request-digest",
            evaluated_at=when,
            valid_until=when + timedelta(seconds=5),
            authority_ref="test:wrong-binding",
        )

    receipt = invoke_governed_chatgpt_mcp_action(
        request=request,
        authorize=mismatched,
        invoke=lambda server, tool, args: calls.append((server, tool, args)),
        commit_time=at,
    )

    assert receipt.invoked is False
    assert calls == []
    assert receipt.reasons == ("AUTHORIZATION_EFFECT_MISMATCH",)
