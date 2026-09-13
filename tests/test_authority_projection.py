from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.authority_projection import (
    AuthorityStateReference,
    ExecutionEndpoint,
    PrincipalAuthoritySemantics,
    project_authority_to_endpoints,
    seal_principal_authority_semantics,
)
from valo_kernel.contracts import (
    Authority,
    Delegation,
    ProposedAction,
    Purpose,
    TimeWindow,
)


def _fixture(now: datetime):
    authority = Authority(
        authority_id="authority:treasury-pay",
        principal="cfo",
        capability="PAY",
        scope=["vendor:456"],
        constraints={"max_amount_eur": "500000"},
        basis="board-resolution:2026-08",
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=2),
        ),
        delegable=True,
    )
    delegation = Delegation(
        delegation_id="delegation:cfo:treasury-agent",
        delegator="cfo",
        delegate="treasury-agent",
        authority_ref=authority.authority_id,
        scope_reduction=["vendor:456"],
        purpose_restriction=["purpose:pay-approved-invoice"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=30),
            valid_until=now + timedelta(hours=1),
        ),
    )
    purpose = Purpose(
        purpose_id="purpose:pay-approved-invoice",
        purpose_type="payment",
        scope=["vendor:456"],
        basis="invoice:789",
        permitted_data=["invoice:789"],
        permitted_actions=["PAY"],
        validity=TimeWindow(
            valid_from=now - timedelta(hours=1),
            valid_until=now + timedelta(hours=3),
        ),
    )
    action = ProposedAction(
        action_id="payment:789",
        capability="PAY",
        target="vendor:456",
        purpose_id=purpose.purpose_id,
        parameters={"amount": "340000", "currency": "EUR"},
        declared_effects=("MOVE_FUNDS",),
    )
    state = AuthorityStateReference(
        tenant_id="acme",
        state_root="a" * 64,
        dependency_digest="b" * 64,
        observed_at=now - timedelta(seconds=5),
        valid_until=now + timedelta(minutes=30),
    )
    return authority, delegation, purpose, action, state


def test_one_principal_authority_semantics_projects_unchanged_to_many_rails():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, delegation, purpose, action, state = _fixture(now)
    semantics = seal_principal_authority_semantics(
        executor_id="treasury-agent",
        authority=authority,
        delegations=(delegation,),
        purpose=purpose,
        proposed_action=action,
        authority_state=state,
        evaluated_at=now,
    )

    endpoints = (
        ExecutionEndpoint(
            endpoint_id="bank-a:sepa",
            adapter_id="adapter:bank-a",
            rail_type="SEPA",
            enforcement_ref="bank-a/payment-initiation",
        ),
        ExecutionEndpoint(
            endpoint_id="bank-b:swift",
            adapter_id="adapter:bank-b",
            rail_type="SWIFT",
            enforcement_ref="bank-b/corporate-payments",
        ),
        ExecutionEndpoint(
            endpoint_id="psp:card",
            adapter_id="adapter:card-network",
            rail_type="CARD",
            enforcement_ref="psp/agent-payment",
        ),
        ExecutionEndpoint(
            endpoint_id="wallet:stablecoin",
            adapter_id="adapter:stablecoin-wallet",
            rail_type="STABLECOIN",
            enforcement_ref="wallet/transfer",
        ),
    )
    projections = project_authority_to_endpoints(
        semantics=semantics,
        endpoints=endpoints,
        projected_at=now + timedelta(seconds=1),
    )

    assert len(projections) == 4
    assert {item.semantics.semantics_digest for item in projections} == {
        semantics.semantics_digest
    }
    assert len({item.projection_digest for item in projections}) == 4
    assert {item.endpoint.endpoint_id for item in projections} == {
        item.endpoint_id for item in endpoints
    }
    assert all(item.authority_effect == "NO_AUTHORITY_CREATION" for item in projections)
    assert all(item.can_issue_clearance is False for item in projections)


def test_semantics_expiry_is_bounded_by_freshest_short_dependency():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, delegation, purpose, action, state = _fixture(now)
    semantics = seal_principal_authority_semantics(
        executor_id="treasury-agent",
        authority=authority,
        delegations=(delegation,),
        purpose=purpose,
        proposed_action=action,
        authority_state=state,
        evaluated_at=now,
    )
    assert semantics.valid_until == state.valid_until


def test_executor_cannot_inherit_authority_without_explicit_delegation():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, _, purpose, action, state = _fixture(now)
    with pytest.raises(ValidationError, match="explicit delegation chain"):
        seal_principal_authority_semantics(
            executor_id="treasury-agent",
            authority=authority,
            delegations=(),
            purpose=purpose,
            proposed_action=action,
            authority_state=state,
            evaluated_at=now,
        )


def test_revoked_delegation_fails_closed():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, delegation, purpose, action, state = _fixture(now)
    revoked = Delegation.model_validate(
        {
            **delegation.model_dump(mode="python"),
            "revoked_at": now - timedelta(seconds=1),
            "revocation_ref": "revocation:42",
        }
    )
    with pytest.raises(ValidationError, match="delegation is not active"):
        seal_principal_authority_semantics(
            executor_id="treasury-agent",
            authority=authority,
            delegations=(revoked,),
            purpose=purpose,
            proposed_action=action,
            authority_state=state,
            evaluated_at=now,
        )


def test_stale_authority_state_fails_closed():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, delegation, purpose, action, _ = _fixture(now)
    stale = AuthorityStateReference(
        tenant_id="acme",
        state_root="a" * 64,
        dependency_digest="b" * 64,
        observed_at=now - timedelta(minutes=2),
        valid_until=now - timedelta(seconds=1),
    )
    with pytest.raises(ValidationError, match="authority state is not fresh"):
        seal_principal_authority_semantics(
            executor_id="treasury-agent",
            authority=authority,
            delegations=(delegation,),
            purpose=purpose,
            proposed_action=action,
            authority_state=stale,
            evaluated_at=now,
        )


def test_wrong_purpose_or_target_cannot_be_projected():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, delegation, purpose, action, state = _fixture(now)
    wrong_action = ProposedAction(
        action_id=action.action_id,
        capability=action.capability,
        target="vendor:999",
        purpose_id=action.purpose_id,
        parameters=action.parameters,
        declared_effects=action.declared_effects,
    )
    with pytest.raises(ValidationError, match="outside authority scope"):
        seal_principal_authority_semantics(
            executor_id="treasury-agent",
            authority=authority,
            delegations=(delegation,),
            purpose=purpose,
            proposed_action=wrong_action,
            authority_state=state,
            evaluated_at=now,
        )


def test_projection_exposes_only_opaque_state_binding_not_authority_payload_state():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, delegation, purpose, action, state = _fixture(now)
    semantics = seal_principal_authority_semantics(
        executor_id="treasury-agent",
        authority=authority,
        delegations=(delegation,),
        purpose=purpose,
        proposed_action=action,
        authority_state=state,
        evaluated_at=now,
    )
    payload = semantics.model_dump(mode="json")
    assert set(payload["authority_state"]) == {
        "schema_version",
        "tenant_id",
        "state_root",
        "dependency_digest",
        "observed_at",
        "valid_until",
    }
    assert "payload" not in payload["authority_state"]


def test_tampered_semantics_digest_is_rejected():
    now = datetime(2026, 8, 16, 9, 0, tzinfo=UTC)
    authority, delegation, purpose, action, state = _fixture(now)
    sealed = seal_principal_authority_semantics(
        executor_id="treasury-agent",
        authority=authority,
        delegations=(delegation,),
        purpose=purpose,
        proposed_action=action,
        authority_state=state,
        evaluated_at=now,
    )
    with pytest.raises(ValidationError, match="semantics digest mismatch"):
        PrincipalAuthoritySemantics.model_validate(
            {**sealed.model_dump(mode="python"), "semantics_digest": "0" * 64}
        )
