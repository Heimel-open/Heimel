from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_external_adapters.authority_hub import (
    AuthorityHub,
    ExternalIdentityAssertion,
    IdentityVerification,
)
from valo_external_adapters.contracts import ProposedAction, canonical_digest

NOW = datetime(2026, 9, 15, 6, 0, tzinfo=UTC)


def _assertion(**overrides):
    values = {
        "provider_id": "scrive:eid",
        "external_subject": "dk:pid:123",
        "verification": IdentityVerification.VERIFIED,
        "assurance_level": "substantial",
        "evidence_ref": "evidence:scrive:session-1",
        "issued_at": NOW - timedelta(minutes=1),
        "valid_until": NOW + timedelta(minutes=4),
        "claims_digest": canonical_digest({"subject": "dk:pid:123"}),
    }
    values.update(overrides)
    return ExternalIdentityAssertion(**values)


def _action():
    return ProposedAction(
        action_id="action:pay-1",
        capability="PAY",
        target="account:merchant-7",
        purpose_id="purpose:invoice-9",
        parameters={"amount": "100.00", "currency": "DKK"},
        declared_effects=("TRANSFER_VALUE",),
    )


def test_verified_identity_produces_only_non_authoritative_reht_handoff():
    binding = AuthorityHub.bind_identity(
        assertion=_assertion(),
        actor_id="actor:pleo-user-42",
        now=NOW,
    )
    request = AuthorityHub.request_authority_resolution(
        binding=binding,
        proposed_action=_action(),
        now=NOW,
    )

    assert binding.authority_effect == "NO_AUTHORITY_CREATION"
    assert binding.can_issue_clearance is False
    assert request.requires_fresh_authority is True
    assert request.authority_effect == "NO_AUTHORITY_CREATION"
    assert request.can_issue_clearance is False
    assert not hasattr(request, "decision")
    assert not hasattr(request, "clearance")
    assert not hasattr(request, "authority")


def test_identity_provider_cannot_smuggle_roles_or_permissions_into_contract():
    payload = _assertion().model_dump(mode="python")
    payload["roles"] = ["admin"]
    payload["permissions"] = ["PAY"]

    with pytest.raises(ValidationError):
        ExternalIdentityAssertion.model_validate(payload)


def test_rejected_unknown_and_expired_identity_fail_closed_before_handoff():
    for assertion in (
        _assertion(verification=IdentityVerification.REJECTED),
        _assertion(verification=IdentityVerification.UNKNOWN),
        _assertion(valid_until=NOW),
    ):
        with pytest.raises(ValueError, match="not verified and fresh"):
            AuthorityHub.bind_identity(
                assertion=assertion,
                actor_id="actor:pleo-user-42",
                now=NOW,
            )


def test_stale_canonical_binding_cannot_reach_authority_resolution():
    binding = AuthorityHub.bind_identity(
        assertion=_assertion(valid_until=NOW + timedelta(seconds=1)),
        actor_id="actor:pleo-user-42",
        now=NOW,
    )

    with pytest.raises(ValueError, match="binding is not fresh"):
        AuthorityHub.request_authority_resolution(
            binding=binding,
            proposed_action=_action(),
            now=NOW + timedelta(seconds=1),
        )


def test_identity_assertion_requires_closed_schema():
    with pytest.raises(ValidationError):
        _assertion(unmapped_provider_field="must-not-pass")
