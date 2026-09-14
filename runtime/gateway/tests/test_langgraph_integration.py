from datetime import UTC, datetime, timedelta

import pytest

from valo_gateway import (
    ActionEnvelope,
    AuthorityEnvelope,
    AuthoritySource,
    Clearance,
    Decision,
    DecisionContract,
    ValoGateway,
    issue_execution_permit,
)
from valo_gateway.integrations.langgraph import (
    AUTHORITY_DECISION_KEY,
    EFFECT_RESULT_KEY,
    PERMIT_KEY,
    LangGraphAuthorization,
    LangGraphGatewayAdapter,
)
from valo_gateway.tool_adapters import FunctionTool


NOW = datetime(2026, 9, 14, 4, 0, tzinfo=UTC)


class InMemoryPermitStore:
    def __init__(self) -> None:
        self._consumed: set[str] = set()

    def consume_once(self, permit_id: str, consumed_at: datetime) -> bool:
        del consumed_at
        if permit_id in self._consumed:
            return False
        self._consumed.add(permit_id)
        return True


class TestAuthorizer:
    def __init__(self, *, escalate_without_evidence: bool = False) -> None:
        self.escalate_without_evidence = escalate_without_evidence
        self.calls: list[object] = []
        self.authority = AuthorityEnvelope(
            principal_id="human:owner",
            actor_id="agent:langgraph",
            source=AuthoritySource.INTERNAL,
            issuer="heimel-test",
            issued_at=NOW,
            valid_until=NOW + timedelta(minutes=5),
            capability_grants=["transfer_funds"],
            resource_scope=["acct:xyz"],
        )

    def authorize(self, *, action: ActionEnvelope, evidence=None):
        self.calls.append(evidence)
        decision = (
            Decision.ESCALATE
            if self.escalate_without_evidence and evidence is None
            else Decision.ALLOW
        )
        clearance = Clearance(
            action_digest=action.digest,
            authority_envelope_id=self.authority.envelope_id,
            decision_contract=DecisionContract(
                decision=decision,
                principal_id=self.authority.principal_id,
                actor_id=self.authority.actor_id,
                action_type=action.action_type,
                target=action.target,
            ),
            decided_at=NOW,
            valid_until=NOW + timedelta(seconds=30),
            reht_ref="reht:fresh:langgraph-test",
        )
        permit = None
        if decision is Decision.ALLOW:
            permit = issue_execution_permit(
                clearance=clearance,
                authority=self.authority,
                action=action,
                expires_at=NOW + timedelta(seconds=10),
                now=NOW,
            )
        return LangGraphAuthorization(
            decision=decision,
            authority=self.authority,
            clearance=clearance,
            permit=permit,
        )


def _action(authority_id: str, amount: int = 45_000) -> ActionEnvelope:
    return ActionEnvelope(
        action_type="transfer_funds",
        target="acct:xyz",
        parameters={"amount": amount, "purpose": "vendor_payment"},
        context_digest="langgraph:thread:42",
        policy_digest="policy:payments:v1",
        authority_envelope_id=authority_id,
    )


def _adapter(authorizer: TestAuthorizer, calls: list[tuple[int, str]]):
    tool = FunctionTool(
        "bank-transfer",
        lambda amount, purpose: calls.append((amount, purpose)) or {"accepted": True},
    )
    return LangGraphGatewayAdapter(
        authorizer=authorizer,
        gateway=ValoGateway(permit_store=InMemoryPermitStore()),
        binding_resolver=lambda action: {
            "executor_id": "tool:bank-transfer",
            "tool": tool,
            "now": NOW,
        },
    )


def test_langgraph_adapter_authorizes_and_executes_only_through_gateway():
    calls = []
    authorizer = TestAuthorizer()
    adapter = _adapter(authorizer, calls)
    state = adapter.proposal_update(_action(authorizer.authority.envelope_id))
    state.update(adapter.authorization_node(state))

    assert adapter.route_after_authorization(state) == "ALLOW"
    state.update(adapter.gateway_node(state))

    assert calls == [(45_000, "vendor_payment")]
    assert state[PERMIT_KEY] is None
    assert state[EFFECT_RESULT_KEY].receipt.status.value == "succeeded"


def test_mutating_effect_after_proposal_binding_fails_before_authorization():
    calls = []
    authorizer = TestAuthorizer()
    adapter = _adapter(authorizer, calls)
    state = adapter.proposal_update(_action(authorizer.authority.envelope_id))
    state["proposed_effect"] = _action(authorizer.authority.envelope_id, amount=50_000)

    with pytest.raises(ValueError, match="changed after graph binding"):
        adapter.authorization_node(state)

    assert calls == []


def test_human_approval_is_evidence_and_forces_fresh_reauthorization():
    calls = []
    authorizer = TestAuthorizer(escalate_without_evidence=True)
    adapter = _adapter(authorizer, calls)
    state = adapter.proposal_update(_action(authorizer.authority.envelope_id))
    state.update(adapter.authorization_node(state))

    assert state[AUTHORITY_DECISION_KEY] == "ESCALATE"
    assert state[PERMIT_KEY] is None

    evidence = {"approved": True, "actor": "human:owner"}
    state.update(adapter.human_evidence_update(evidence))
    assert state[AUTHORITY_DECISION_KEY] is None
    state.update(adapter.authorization_node(state))

    assert state[AUTHORITY_DECISION_KEY] == "ALLOW"
    assert authorizer.calls == [None, evidence]
    state.update(adapter.gateway_node(state))
    assert calls == [(45_000, "vendor_payment")]


def test_checkpointed_allow_cannot_replay_consumed_permit():
    calls = []
    authorizer = TestAuthorizer()
    permit_store = InMemoryPermitStore()
    tool = FunctionTool(
        "bank-transfer",
        lambda amount, purpose: calls.append((amount, purpose)) or {"accepted": True},
    )
    adapter = LangGraphGatewayAdapter(
        authorizer=authorizer,
        gateway=ValoGateway(permit_store=permit_store),
        binding_resolver=lambda action: {
            "executor_id": "tool:bank-transfer",
            "tool": tool,
            "now": NOW,
        },
    )
    state = adapter.proposal_update(_action(authorizer.authority.envelope_id))
    state.update(adapter.authorization_node(state))
    checkpoint = dict(state)

    adapter.gateway_node(state)
    with pytest.raises(ValueError, match="already consumed"):
        adapter.gateway_node(checkpoint)

    assert calls == [(45_000, "vendor_payment")]


def test_binding_resolver_cannot_override_governed_objects():
    authorizer = TestAuthorizer()
    adapter = LangGraphGatewayAdapter(
        authorizer=authorizer,
        gateway=ValoGateway(permit_store=InMemoryPermitStore()),
        binding_resolver=lambda action: {
            "executor_id": "tool:x",
            "permit": "forged",
        },
    )
    state = adapter.proposal_update(_action(authorizer.authority.envelope_id))
    state.update(adapter.authorization_node(state))

    with pytest.raises(ValueError, match="cannot override governed bindings"):
        adapter.gateway_node(state)
