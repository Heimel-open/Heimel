from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_kernel.contracts.responsibility import (
    EffectResponsibilityEvidence,
    ExecutionResponsibilityBinding,
    ResponsibilityAssignment,
    ResponsibilityRole,
    seal_effect_responsibility_evidence,
    seal_execution_responsibility_binding,
)


def _assignments() -> tuple[ResponsibilityAssignment, ...]:
    return (
        ResponsibilityAssignment(
            role=ResponsibilityRole.PRINCIPAL,
            actor_ref="org:acme",
            basis_refs=("corporate-authority:acme",),
        ),
        ResponsibilityAssignment(
            role=ResponsibilityRole.AUTHORITY_SOURCE,
            actor_ref="board:acme",
            basis_refs=("board-resolution:2026-08",),
        ),
        ResponsibilityAssignment(
            role=ResponsibilityRole.STATE_PROVIDER,
            actor_ref="erp:acme",
            basis_refs=("budget-ledger:v42",),
            evidence_refs=("evidence:budget:v42",),
        ),
        ResponsibilityAssignment(
            role=ResponsibilityRole.AUTHORIZATION_EVALUATOR,
            actor_ref="reht:boundary",
            basis_refs=("reht-contract:v1",),
        ),
        ResponsibilityAssignment(
            role=ResponsibilityRole.DISPOSITION_ISSUER,
            actor_ref="racs:contract",
            basis_refs=("racs-contract:v1",),
        ),
        ResponsibilityAssignment(
            role=ResponsibilityRole.ENFORCEMENT_OWNER,
            actor_ref="bank:pep",
            basis_refs=("bank-control:payments",),
            regulatory_refs=("payment-services-regime",),
        ),
        ResponsibilityAssignment(
            role=ResponsibilityRole.EXECUTION_PROVIDER,
            actor_ref="bank:settlement",
            basis_refs=("account-agreement:acme",),
            contractual_refs=("banking-contract:acme",),
        ),
    )


def _binding(now: datetime) -> ExecutionResponsibilityBinding:
    return seal_execution_responsibility_binding(
        binding_id="responsibility:payment:1001",
        tenant_id="acme",
        action_ref="payment:1001",
        authority_ref="authority:treasury",
        delegation_refs=("delegation:cfo:treasury-agent",),
        purpose_ref="purpose:supplier-payment",
        authority_state_ref="authority-state:abc123",
        state_root="a" * 64,
        decision_ref="reht-decision:1001",
        disposition_ref="racs-disposition:1001",
        clearance_ref="clearance:1001",
        assignments=_assignments(),
        bound_at=now,
    )


def test_binding_seals_required_responsibility_roles_and_is_deterministic():
    now = datetime(2026, 8, 16, 13, 45, tzinfo=UTC)
    first = _binding(now)
    second = _binding(now)

    assert first.binding_digest == second.binding_digest
    assert first.legal_liability_determined is False
    assert first.authority_effect == "NO_AUTHORITY_CREATION"
    assert first.can_issue_clearance is False
    assert first.can_issue_disposition is False


def test_multiple_state_providers_are_allowed():
    now = datetime(2026, 8, 16, 13, 45, tzinfo=UTC)
    assignments = _assignments() + (
        ResponsibilityAssignment(
            role=ResponsibilityRole.STATE_PROVIDER,
            actor_ref="iam:acme",
            basis_refs=("identity-state:v9",),
            evidence_refs=("evidence:identity:v9",),
        ),
    )
    binding = seal_execution_responsibility_binding(
        binding_id="responsibility:payment:1001",
        tenant_id="acme",
        action_ref="payment:1001",
        authority_ref="authority:treasury",
        purpose_ref="purpose:supplier-payment",
        authority_state_ref="authority-state:abc123",
        state_root="a" * 64,
        decision_ref="reht-decision:1001",
        disposition_ref="racs-disposition:1001",
        clearance_ref="clearance:1001",
        assignments=assignments,
        bound_at=now,
    )
    assert len(
        [
            item
            for item in binding.assignments
            if item.role is ResponsibilityRole.STATE_PROVIDER
        ]
    ) == 2


def test_missing_required_role_fails_closed():
    now = datetime(2026, 8, 16, 13, 45, tzinfo=UTC)
    assignments = tuple(
        item
        for item in _assignments()
        if item.role is not ResponsibilityRole.ENFORCEMENT_OWNER
    ) + (
        ResponsibilityAssignment(
            role="banking:ExecutionObserver",
            actor_ref="observer:bank",
            basis_refs=("observer-contract:1",),
        ),
    )
    with pytest.raises(ValidationError, match="missing required responsibility roles"):
        seal_execution_responsibility_binding(
            binding_id="responsibility:payment:1001",
            tenant_id="acme",
            action_ref="payment:1001",
            authority_ref="authority:treasury",
            purpose_ref="purpose:supplier-payment",
            authority_state_ref="authority-state:abc123",
            state_root="a" * 64,
            decision_ref="reht-decision:1001",
            disposition_ref="racs-disposition:1001",
            clearance_ref="clearance:1001",
            assignments=assignments,
            bound_at=now,
        )


def test_duplicate_singleton_role_fails_closed():
    now = datetime(2026, 8, 16, 13, 45, tzinfo=UTC)
    assignments = _assignments() + (
        ResponsibilityAssignment(
            role=ResponsibilityRole.PRINCIPAL,
            actor_ref="org:other",
            basis_refs=("other-basis",),
        ),
    )
    with pytest.raises(ValidationError, match="duplicate singleton responsibility role"):
        seal_execution_responsibility_binding(
            binding_id="responsibility:payment:1001",
            tenant_id="acme",
            action_ref="payment:1001",
            authority_ref="authority:treasury",
            purpose_ref="purpose:supplier-payment",
            authority_state_ref="authority-state:abc123",
            state_root="a" * 64,
            decision_ref="reht-decision:1001",
            disposition_ref="racs-disposition:1001",
            clearance_ref="clearance:1001",
            assignments=assignments,
            bound_at=now,
        )


def test_assignment_requires_explicit_basis():
    with pytest.raises(ValidationError):
        ResponsibilityAssignment(
            role=ResponsibilityRole.PRINCIPAL,
            actor_ref="org:acme",
            basis_refs=(),
        )


def test_namespaced_domain_role_is_extensible_but_not_a_core_substitute():
    custom = ResponsibilityAssignment(
        role="banking:SettlementSponsor",
        actor_ref="bank:sponsor",
        basis_refs=("sponsorship-agreement:1",),
    )
    assert custom.role == "banking:SettlementSponsor"

    with pytest.raises(ValidationError, match="missing required responsibility roles"):
        seal_execution_responsibility_binding(
            binding_id="responsibility:payment:1001",
            tenant_id="acme",
            action_ref="payment:1001",
            authority_ref="authority:treasury",
            purpose_ref="purpose:supplier-payment",
            authority_state_ref="authority-state:abc123",
            state_root="a" * 64,
            decision_ref="reht-decision:1001",
            disposition_ref="racs-disposition:1001",
            clearance_ref="clearance:1001",
            assignments=(custom,) * 7,
            bound_at=datetime(2026, 8, 16, 13, 45, tzinfo=UTC),
        )


def test_tampered_binding_digest_is_rejected():
    binding = _binding(datetime(2026, 8, 16, 13, 45, tzinfo=UTC))
    with pytest.raises(ValidationError, match="responsibility binding digest mismatch"):
        ExecutionResponsibilityBinding.model_validate(
            {
                **binding.model_dump(mode="python"),
                "binding_digest": "0" * 64,
            }
        )


def test_contract_cannot_claim_to_determine_legal_liability():
    binding = _binding(datetime(2026, 8, 16, 13, 45, tzinfo=UTC))
    with pytest.raises(ValidationError):
        ExecutionResponsibilityBinding.model_validate(
            {
                **binding.model_dump(mode="python"),
                "legal_liability_determined": True,
            }
        )


def test_effect_evidence_binds_exact_pre_effect_responsibility_digest():
    now = datetime(2026, 8, 16, 13, 45, tzinfo=UTC)
    binding = _binding(now)
    evidence = seal_effect_responsibility_evidence(
        evidence_id="responsibility-effect:1001",
        binding=binding,
        effect_ref="effect:payment:1001",
        receipt_ref="veritas:receipt:1001",
        verifier_ref="veritas",
        evidence_refs=("bank:settlement-confirmation:1001",),
        observed_at=now + timedelta(milliseconds=9),
    )

    assert evidence.responsibility_binding_digest == binding.binding_digest
    assert evidence.action_ref == binding.action_ref
    assert evidence.decision_ref == binding.decision_ref
    assert evidence.disposition_ref == binding.disposition_ref
    assert evidence.clearance_ref == binding.clearance_ref
    assert evidence.legal_liability_determined is False


def test_effect_evidence_tampering_is_rejected():
    now = datetime(2026, 8, 16, 13, 45, tzinfo=UTC)
    evidence = seal_effect_responsibility_evidence(
        evidence_id="responsibility-effect:1001",
        binding=_binding(now),
        effect_ref="effect:payment:1001",
        receipt_ref="veritas:receipt:1001",
        verifier_ref="veritas",
        evidence_refs=("bank:settlement-confirmation:1001",),
        observed_at=now + timedelta(milliseconds=9),
    )
    with pytest.raises(ValidationError, match="effect responsibility digest mismatch"):
        EffectResponsibilityEvidence.model_validate(
            {
                **evidence.model_dump(mode="python"),
                "effect_ref": "effect:payment:9999",
            }
        )
