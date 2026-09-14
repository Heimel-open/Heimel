"""AutoGen GuardrailProvider compatibility and consequence-time conformance."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from valo_gateway import (
    ActionEnvelope,
    AuthorityEnvelope,
    AuthoritySource,
    AutoGenGatewayAdapter,
    AutoGenGuardrailDecision,
    AutoGenGuardrailProviderAdapter,
    Clearance,
    ControlEvent,
    ControlEventType,
    Decision,
    DecisionContract,
    RuntimeControlPlane,
    ValoGateway,
    issue_execution_permit,
)
from valo_gateway.integrations.langgraph import LangGraphAuthorization
from valo_gateway.tool_adapters import GitHubEffectTool

NOW = datetime(2026, 9, 14, 4, 30, tzinfo=UTC)


class PermitStore:
    def __init__(self) -> None:
        self.consumed: set[str] = set()

    def consume_once(self, permit_id: str, consumed_at: datetime) -> bool:
        del consumed_at
        if permit_id in self.consumed:
            return False
        self.consumed.add(permit_id)
        return True


class Authorizer:
    def __init__(self) -> None:
        self.authority = AuthorityEnvelope(
            principal_id="human:owner",
            actor_id="agent:autogen",
            source=AuthoritySource.INTERNAL,
            issuer="heimel-conformance",
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
                decision=Decision.ALLOW,
                principal_id=self.authority.principal_id,
                actor_id=self.authority.actor_id,
                action_type=action.action_type,
                target=action.target,
            ),
            decided_at=NOW,
            valid_until=NOW + timedelta(seconds=30),
            reht_ref="reht:autogen-conformance",
        )
        return LangGraphAuthorization(
            decision=Decision.ALLOW,
            authority=self.authority,
            clearance=clearance,
            permit=issue_execution_permit(
                clearance=clearance,
                authority=self.authority,
                action=action,
                expires_at=NOW + timedelta(seconds=10),
                now=NOW,
            ),
        )


def _adapter(calls: list[tuple[str, dict[str, object]]], control_plane):
    authorizer = Authorizer()

    def action_factory(call):
        return ActionEnvelope(
            action_type="provider_call",
            target="repo:acme/x",
            parameters={"operation": call.name, **call.arguments},
            context_digest=f"{call.provider}:{call.call_id or 'none'}",
            policy_digest="policy:autogen-conformance:v1",
            authority_envelope_id=authorizer.authority.envelope_id,
        )

    tool = GitHubEffectTool(
        lambda operation, parameters: calls.append((operation, parameters))
        or {"ok": True}
    )
    gateway = ValoGateway(
        control_plane=control_plane,
        permit_store=PermitStore(),
    )
    return (
        authorizer,
        AutoGenGuardrailProviderAdapter(
            AutoGenGatewayAdapter(
                authorizer=authorizer,
                gateway=gateway,
                action_factory=action_factory,
                binding_resolver=lambda action: {
                    "executor_id": "provider:github",
                    "tool": tool,
                    "control_plane": control_plane,
                    "now": NOW,
                },
            )
        ),
    )


def test_autogen_guardrail_allow_is_not_authority_after_consequence_revocation():
    calls: list[tuple[str, dict[str, object]]] = []
    control_plane = RuntimeControlPlane()
    authorizer, provider = _adapter(calls, control_plane)

    admission = asyncio.run(
        provider.evaluate(
            tool_name="issue.create",
            args={"title": "x"},
            agent_name="assistant",
            call_id="call-1",
        )
    )
    assert admission.decision is AutoGenGuardrailDecision.ALLOW

    control_plane.apply(
        # The stale AutoGen approval must not survive this final boundary.
        ControlEvent(
            event_type=ControlEventType.REVOKE_AUTHORITY,
            issuer_id="operator",
            reason="conformance test",
            authority_envelope_id=authorizer.authority.envelope_id,
        )
    )

    with pytest.raises(ValueError, match="revocation or HALT"):
        provider.execute(
            tool_name="issue.create",
            args={"title": "x"},
            call_id="call-1",
            admission=admission,
        )
    assert calls == []
