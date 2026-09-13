from datetime import datetime, timedelta, timezone

import pytest

from valo_c_mcp import CMCPContractV1, CMCPInvocation, ProtocolStack, canonical_json


NOW = datetime(2026, 8, 14, 4, 0, tzinfo=timezone.utc)


def invocation(**patch):
    values = {
        "call_id": "call-1", "actor_id": "agent-7", "tenant_id": "tenant-a",
        "server_id": "stripe-mcp", "tool_name": "transfer_funds",
        "protocol_stack": ProtocolStack(transport="http", interaction_protocols=["mcp"]),
        "arguments": {"amount": 5000, "currency": "EUR"}, "target_resource": "account:acct-a",
        "purpose_ref": "purpose:invoice-payment", "authority_refs": ["authority:finance:v3"],
        "governed_state_refs": ["state:account:acct-a"], "provenance_refs": ["source:invoice:42"],
    }
    values.update(patch)
    return CMCPInvocation(**values)


def bind(value=None):
    return CMCPContractV1.bind(value or invocation(), gcop_contract_id="gcop:1", gcop_contract_hash="sha256:1", now=NOW, contract_id="cmcp:1")


def test_binding_is_deterministic_and_exact():
    first = bind(invocation(arguments={"currency": "EUR", "amount": 5000}))
    second = bind(invocation(arguments={"amount": 5000, "currency": "EUR"}))
    assert first.contract_hash == second.contract_hash
    assert first.verify(invocation(), now=NOW) == (True, "ok")


def test_tampering_and_expiry_fail_closed():
    contract = bind()
    assert contract.verify(invocation(arguments={"amount": 1}), now=NOW) == (False, "invocation_mismatch")
    assert contract.verify(invocation(), now=NOW + timedelta(seconds=301)) == (False, "expired")


def test_approval_requires_reference_and_protocol_duplicates_are_rejected():
    approval = invocation(human_approval_required=True)
    assert bind(approval).verify(approval, now=NOW) == (False, "missing_human_approval")
    with pytest.raises(ValueError, match="duplicate"):
        ProtocolStack(transport="http", interaction_protocols=["mcp", "mcp"])
