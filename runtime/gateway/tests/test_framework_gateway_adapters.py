from datetime import UTC, datetime, timedelta

import pytest

from valo_gateway import (
    ActionEnvelope,
    AuthorityEnvelope,
    AuthoritySource,
    Clearance,
    Decision,
    DecisionContract,
    RuntimeControlPlane,
    ValoGateway,
    issue_execution_permit,
)
from valo_gateway.integrations.frameworks import (
    AnthropicGatewayAdapter,
    AutoGenGatewayAdapter,
    CrewAIGatewayAdapter,
    GoogleADKGatewayAdapter,
    HTTPWebhookGatewayAdapter,
    MCPGatewayAdapter,
    OpenAIGatewayAdapter,
    SemanticKernelGatewayAdapter,
)
from valo_gateway.integrations.langgraph import LangGraphAuthorization
from valo_gateway.tool_adapters import GitHubEffectTool

NOW = datetime(2026, 9, 14, 4, 30, tzinfo=UTC)


class InMemoryPermitStore:
    def __init__(self) -> None:
        self._consumed: set[str] = set()

    def consume_once(self, permit_id: str, consumed_at: datetime) -> bool:
        del consumed_at
        if permit_id in self._consumed:
            return False
        self._consumed.add(permit_id)
        return True


class Authorizer:
    def __init__(self, decision: Decision = Decision.ALLOW) -> None:
        self.decision = decision
        self.authority = AuthorityEnvelope(
            principal_id="human:owner",
            actor_id="agent:framework",
            source=AuthoritySource.INTERNAL,
            issuer="heimel-test",
            issued_at=NOW,
            valid_until=NOW + timedelta(minutes=5),
            capability_grants=["provider_call"],
            resource_scope=["repo:acme/x"],
        )

    def authorize(self, *, action: ActionEnvelope, evidence=None):
        del evidence
        clearance = Clearance(
            action_digest=action.digest,
            authority_envelope_id=self.authority.envelope_id,
            decision_contract=DecisionContract(
                decision=self.decision,
                principal_id=self.authority.principal_id,
                actor_id=self.authority.actor_id,
                action_type=action.action_type,
                target=action.target,
            ),
            decided_at=NOW,
            valid_until=NOW + timedelta(seconds=30),
            reht_ref="reht:fresh:framework-test",
        )
        permit = None
        if self.decision is Decision.ALLOW:
            permit = issue_execution_permit(
                clearance=clearance,
                authority=self.authority,
                action=action,
                expires_at=NOW + timedelta(seconds=10),
                now=NOW,
            )
        return LangGraphAuthorization(
            decision=self.decision,
            authority=self.authority,
            clearance=clearance,
            permit=permit,
        )


def _action_factory(authority):
    def make(call):
        return ActionEnvelope(
            action_type="provider_call",
            target="repo:acme/x",
            parameters={"operation": call.name, **call.arguments},
            context_digest=f"{call.provider}:{call.call_id or 'none'}",
            policy_digest="policy:providers:v1",
            authority_envelope_id=authority.envelope_id,
        )
    return make


@pytest.mark.parametrize(
    ("adapter_type", "payload", "expected"),
    [
        (MCPGatewayAdapter, {"id": 1, "method": "tools/call", "params": {"name": "issue.create", "arguments": {"title": "x"}}}, "issue.create"),
        (OpenAIGatewayAdapter, {"id": "a", "function": {"name": "issue.create", "arguments": '{"title":"x"}'}}, "issue.create"),
        (AnthropicGatewayAdapter, {"type": "tool_use", "id": "a", "name": "issue.create", "input": {"title": "x"}}, "issue.create"),
        (GoogleADKGatewayAdapter, {"functionCall": {"id": "a", "name": "issue.create", "args": {"title": "x"}}}, "issue.create"),
        (SemanticKernelGatewayAdapter, {"id": "a", "plugin_name": "github", "function_name": "issue.create", "arguments": {"title": "x"}}, "github.issue.create"),
        (CrewAIGatewayAdapter, {"id": "a", "tool": "issue.create", "tool_input": {"title": "x"}}, "issue.create"),
        (AutoGenGatewayAdapter, {"id": "a", "function": {"name": "issue.create", "arguments": {"title": "x"}}}, "issue.create"),
        (HTTPWebhookGatewayAdapter, {"id": "a", "effect": "issue.create", "parameters": {"title": "x"}}, "issue.create"),
    ],
)
def test_framework_decoders_are_dependency_free(adapter_type, payload, expected):
    authorizer = Authorizer()
    adapter = adapter_type(
        authorizer=authorizer,
        gateway=ValoGateway(control_plane=RuntimeControlPlane(), permit_store=InMemoryPermitStore()),
        action_factory=_action_factory(authorizer.authority),
        binding_resolver=lambda action: {},
    )
    assert adapter.decode(payload).name == expected


def test_openai_effect_executes_only_through_gateway():
    calls = []
    authorizer = Authorizer()
    tool = GitHubEffectTool(
        lambda operation, parameters: calls.append((operation, parameters)) or {"ok": True}
    )
    adapter = OpenAIGatewayAdapter(
        authorizer=authorizer,
        gateway=ValoGateway(control_plane=RuntimeControlPlane(), permit_store=InMemoryPermitStore()),
        action_factory=_action_factory(authorizer.authority),
        binding_resolver=lambda action: {"executor_id": "provider:github", "tool": tool, "now": NOW},
    )

    with pytest.raises(PermissionError, match="NO_DIRECT_EFFECT_PATH"):
        tool.invoke({"operation": "issue.create", "title": "x"})

    result = adapter.execute(
        {"id": "call-1", "function": {"name": "issue.create", "arguments": '{"title":"x"}'}}
    )

    assert calls == [("issue.create", {"title": "x"})]
    assert result.execution is not None
    assert result.execution.response == {"ok": True}


def test_deny_has_null_effect():
    calls = []
    authorizer = Authorizer(Decision.DENY)
    tool = GitHubEffectTool(lambda operation, parameters: calls.append((operation, parameters)))
    adapter = OpenAIGatewayAdapter(
        authorizer=authorizer,
        gateway=ValoGateway(control_plane=RuntimeControlPlane(), permit_store=InMemoryPermitStore()),
        action_factory=_action_factory(authorizer.authority),
        binding_resolver=lambda action: {"executor_id": "provider:github", "tool": tool, "now": NOW},
    )

    result = adapter.execute(
        {"id": "call-2", "function": {"name": "issue.create", "arguments": "{}"}}
    )

    assert result.authorization.decision is Decision.DENY
    assert result.execution is None
    assert calls == []
