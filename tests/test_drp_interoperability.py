from datetime import UTC, datetime, timedelta

from valo_kernel.contracts.drp import (
    DrpActionDescriptor,
    DrpDelegationReceipt,
    DrpReauthPolicy,
    DrpScope,
    DrpTimeWindow,
    DrpVerificationEvidence,
)
from valo_kernel.kernel.drp_adapter import assess_drp_receipt

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
AUTHORITY_COMMITMENT = "1" * 64


def _action(operation: str = "read", resource: str = "calendar") -> DrpActionDescriptor:
    return DrpActionDescriptor(operation=operation, resource=resource)


def _receipt(
    marker: str = "a",
    *,
    allowed: tuple[DrpActionDescriptor, ...] | None = None,
    denied: tuple[DrpActionDescriptor, ...] = (),
    boundaries: tuple[str, ...] = ("deny:delete:*",),
    parent_receipt_id: str | None = None,
    authority_commitment: str | None = AUTHORITY_COMMITMENT,
    reauth_policy: DrpReauthPolicy | None = None,
    not_before: datetime | None = None,
    not_after: datetime | None = None,
) -> DrpDelegationReceipt:
    return DrpDelegationReceipt(
        receipt_id=f"rec_{marker * 64}",
        schema_version="1.0",
        time_window=DrpTimeWindow(
            not_before=not_before or NOW - timedelta(minutes=5),
            not_after=not_after or NOW + timedelta(hours=1),
        ),
        public_key={"kty": "OKP", "crv": "Ed25519", "x": "test"},
        scope=DrpScope(allowed_actions=allowed or (_action(),), denied_actions=denied),
        boundaries=boundaries,
        operator_instructions_hash=f"sha256:{'2' * 64}",
        canonical_payload="canonical-payload",
        signature="signature",
        parent_receipt_id=parent_receipt_id,
        orchestrator_signature="orchestrator-signature" if parent_receipt_id else None,
        authority_state_commitment=authority_commitment,
        reauth_policy=reauth_policy,
    )


def _verified(
    receipt: DrpDelegationReceipt,
    *,
    revoked: bool = False,
    revocation_checked: bool = True,
    orchestrator_binding_verified: bool | None = None,
) -> DrpVerificationEvidence:
    return DrpVerificationEvidence(
        receipt_id=receipt.receipt_id,
        signature_verified=True,
        canonical_payload_verified=True,
        log_anchor_verified=True,
        revocation_checked=revocation_checked,
        revoked=revoked,
        orchestrator_binding_verified=orchestrator_binding_verified,
    )


def test_verified_root_receipt_is_only_admissible_evidence() -> None:
    receipt = _receipt()
    result = assess_drp_receipt(
        receipt=receipt,
        verification=_verified(receipt),
        action=_action(),
        evaluated_at=NOW,
        current_authority_state_commitment=AUTHORITY_COMMITMENT,
    )

    assert result.admissible_as_evidence is True
    assert result.reasons == ()
    assert result.authority_state_match is True
    assert result.requires_reht is True
    assert result.can_issue_clearance is False
    assert result.authority_effect == "NO_AUTHORITY_CREATION"


def test_authority_drift_fails_closed_even_when_drp_policy_says_reauth() -> None:
    receipt = _receipt(
        reauth_policy=DrpReauthPolicy(on_authority_state_drift="reauth")
    )
    result = assess_drp_receipt(
        receipt=receipt,
        verification=_verified(receipt),
        action=_action(),
        evaluated_at=NOW,
        current_authority_state_commitment="9" * 64,
    )

    assert result.admissible_as_evidence is False
    assert "AUTHORITY_STATE_DRIFT" in result.reasons
    assert result.authority_state_match is False


def test_boundary_denial_fails_closed() -> None:
    receipt = _receipt(
        allowed=(_action("delete", "calendar"),),
        boundaries=("deny:delete:*",),
    )
    result = assess_drp_receipt(
        receipt=receipt,
        verification=_verified(receipt),
        action=_action("delete", "calendar"),
        evaluated_at=NOW,
        current_authority_state_commitment=AUTHORITY_COMMITMENT,
    )

    assert result.admissible_as_evidence is False
    assert "ACTION_BOUNDARY_DENIED" in result.reasons


def test_subreceipt_must_strictly_attenuate_parent_scope() -> None:
    parent = _receipt("a", allowed=(_action("read", "*"),))
    child = _receipt(
        "b",
        allowed=(_action("read", "*"),),
        parent_receipt_id=parent.receipt_id,
    )
    result = assess_drp_receipt(
        receipt=child,
        verification=_verified(child, orchestrator_binding_verified=True),
        action=_action("read", "calendar"),
        evaluated_at=NOW,
        current_authority_state_commitment=AUTHORITY_COMMITMENT,
        parent_receipt=parent,
        parent_verification=_verified(parent),
    )

    assert result.admissible_as_evidence is False
    assert "SCOPE_NOT_STRICT_SUBSET" in result.reasons


def test_parent_denials_and_boundaries_must_survive_delegation() -> None:
    parent = _receipt(
        "a",
        allowed=(_action("read", "*"),),
        denied=(_action("read", "secrets"),),
        boundaries=("deny:delete:*", "deny:write:ledger"),
    )
    child = _receipt(
        "b",
        allowed=(_action("read", "calendar"),),
        denied=(),
        boundaries=("deny:delete:*",),
        parent_receipt_id=parent.receipt_id,
    )
    result = assess_drp_receipt(
        receipt=child,
        verification=_verified(child, orchestrator_binding_verified=True),
        action=_action("read", "calendar"),
        evaluated_at=NOW,
        current_authority_state_commitment=AUTHORITY_COMMITMENT,
        parent_receipt=parent,
        parent_verification=_verified(parent),
    )

    assert result.admissible_as_evidence is False
    assert "PARENT_DENIAL_DROPPED" in result.reasons
    assert "PARENT_BOUNDARY_DROPPED" in result.reasons


def test_revoked_ancestor_invalidates_descendant_evidence() -> None:
    receipt = _receipt()
    ancestor = _receipt("c")
    result = assess_drp_receipt(
        receipt=receipt,
        verification=_verified(receipt),
        action=_action(),
        evaluated_at=NOW,
        current_authority_state_commitment=AUTHORITY_COMMITMENT,
        ancestor_verifications=(_verified(ancestor, revoked=True),),
    )

    assert result.admissible_as_evidence is False
    assert "ANCESTOR_REVOKED" in result.reasons


def test_unchecked_revocation_is_not_admissible_for_governed_execution() -> None:
    receipt = _receipt()
    result = assess_drp_receipt(
        receipt=receipt,
        verification=_verified(receipt, revocation_checked=False),
        action=_action(),
        evaluated_at=NOW,
        current_authority_state_commitment=AUTHORITY_COMMITMENT,
    )

    assert result.admissible_as_evidence is False
    assert "REVOCATION_UNCHECKED" in result.reasons
