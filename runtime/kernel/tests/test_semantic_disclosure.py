from __future__ import annotations

from datetime import timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from valo_kernel import EntityType, ProposedAction, utcnow
from valo_kernel.contracts.semantic_disclosure import (
    ExecutionBoundaryDisclosureContext,
    ExecutionBoundaryKey,
)
from valo_kernel.kernel.errors import FailClosedError
from valo_kernel.kernel.semantic_disclosure import (
    bind_sealed_workspace_execution,
    disclose_consequence_action,
    seal_consequence_action,
)

from .conftest import entity_event
from .test_workspace import _candidate, _register_purpose, _workspace


def _boundary_key(now):
    private_key = X25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        Encoding.Raw,
        PrivateFormat.Raw,
        NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    import base64

    descriptor = ExecutionBoundaryKey(
        key_ref="boundary-key:reht-1",
        boundary_id="reht-boundary-1",
        public_key_b64=base64.b64encode(public_bytes).decode("ascii"),
        valid_from=now - timedelta(seconds=1),
        valid_until=now + timedelta(minutes=10),
    )
    return descriptor, private_bytes


def _action() -> ProposedAction:
    return ProposedAction(
        action_id="payment-1",
        capability="PAY",
        target="account:secret-beneficiary-847",
        purpose_id="invoice-991",
        parameters={"amount": 8420, "currency": "EUR", "routing": "SECRET-ROUTE"},
        declared_effects=("transfer_funds",),
    )


def _context(envelope, now):
    return ExecutionBoundaryDisclosureContext(
        disclosure_id="disclosure-1",
        boundary_id=envelope.recipient_boundary_id,
        key_ref=envelope.recipient_key_ref,
        tenant_id=envelope.tenant_id,
        work_unit_id=envelope.work_unit_id,
        workspace_id=envelope.workspace_id,
        reht_evaluation_id="reht-eval-1",
        fresh_state_root="a" * 64,
        fresh_authority_digest="b" * 64,
        fresh_evidence_digest="c" * 64,
        disclosed_at=now,
    )


def test_consequence_semantics_cross_boundary_only_as_ciphertext() -> None:
    now = utcnow()
    boundary_key, private_key = _boundary_key(now)
    action = _action()

    envelope = seal_consequence_action(
        action,
        boundary_key,
        tenant_id="tenant-a",
        work_unit_id="work-1",
        workspace_id="workspace-1",
        sealed_at=now,
        valid_until=now + timedelta(minutes=5),
    )

    serialized = envelope.model_dump_json()
    assert "secret-beneficiary-847" not in serialized
    assert "SECRET-ROUTE" not in serialized
    assert envelope.envelope_digest == envelope.computed_digest
    assert envelope.unseal_effect == "NO_EXECUTION_EFFECT"

    disclosed = disclose_consequence_action(
        envelope,
        _context(envelope, now + timedelta(seconds=1)),
        boundary_private_key=private_key,
    )

    assert disclosed.action == action
    assert disclosed.execution_effect == "NONE"
    assert disclosed.can_issue_clearance is False


def test_wrong_boundary_fails_closed_before_disclosure() -> None:
    now = utcnow()
    boundary_key, private_key = _boundary_key(now)
    envelope = seal_consequence_action(
        _action(),
        boundary_key,
        tenant_id="tenant-a",
        work_unit_id="work-1",
        workspace_id="workspace-1",
        sealed_at=now,
        valid_until=now + timedelta(minutes=5),
    )
    context = _context(envelope, now + timedelta(seconds=1)).model_copy(
        update={"boundary_id": "not-reht-boundary"}
    )

    with pytest.raises(FailClosedError, match="wrong boundary"):
        disclose_consequence_action(
            envelope,
            context,
            boundary_private_key=private_key,
        )


def test_wrong_private_key_cannot_disclose() -> None:
    now = utcnow()
    boundary_key, _private_key = _boundary_key(now)
    _other_descriptor, other_private_key = _boundary_key(now)
    envelope = seal_consequence_action(
        _action(),
        boundary_key,
        tenant_id="tenant-a",
        work_unit_id="work-1",
        workspace_id="workspace-1",
        sealed_at=now,
        valid_until=now + timedelta(minutes=5),
    )

    with pytest.raises(FailClosedError, match="cryptographic verification"):
        disclose_consequence_action(
            envelope,
            _context(envelope, now + timedelta(seconds=1)),
            boundary_private_key=other_private_key,
        )


def test_disclosure_after_validity_window_fails_closed() -> None:
    now = utcnow()
    boundary_key, private_key = _boundary_key(now)
    envelope = seal_consequence_action(
        _action(),
        boundary_key,
        tenant_id="tenant-a",
        work_unit_id="work-1",
        workspace_id="workspace-1",
        sealed_at=now,
        valid_until=now + timedelta(seconds=2),
    )

    with pytest.raises(FailClosedError, match="window has expired"):
        disclose_consequence_action(
            envelope,
            _context(envelope, now + timedelta(seconds=2)),
            boundary_private_key=private_key,
        )


def test_tampered_envelope_fails_closed() -> None:
    now = utcnow()
    boundary_key, private_key = _boundary_key(now)
    envelope = seal_consequence_action(
        _action(),
        boundary_key,
        tenant_id="tenant-a",
        work_unit_id="work-1",
        workspace_id="workspace-1",
        sealed_at=now,
        valid_until=now + timedelta(minutes=5),
    )
    tampered = envelope.model_copy(update={"ciphertext_b64": envelope.ciphertext_b64[:-4] + "AAAA"})

    with pytest.raises(FailClosedError, match="tampered"):
        disclose_consequence_action(
            tampered,
            _context(envelope, now + timedelta(seconds=1)),
            boundary_private_key=private_key,
        )


@pytest.fixture
def governed_engine(engine):
    engine.append(
        entity_event(
            "tenant-a",
            "job-1",
            entity_type=EntityType.JOB,
            state="READY",
        )
    )
    _register_purpose(engine)
    return engine


def test_pass_conformance_can_emit_sealed_execution_binding(governed_engine) -> None:
    now = utcnow()
    workspace = _workspace(governed_engine, moment=now)
    candidate = _candidate(workspace)
    from valo_kernel import evaluate_candidate_conformance

    report = evaluate_candidate_conformance(
        workspace,
        candidate,
        governed_engine.state(),
        moment=now + timedelta(milliseconds=1),
    )
    boundary_key, private_key = _boundary_key(now)

    binding = bind_sealed_workspace_execution(
        workspace,
        candidate,
        report,
        action_id="action-1",
        recipient_key=boundary_key,
    )

    assert binding.binding_digest == binding.computed_digest
    assert binding.plaintext_action_exposed is False
    assert '"target":"job-1"' not in binding.model_dump_json()

    context = ExecutionBoundaryDisclosureContext(
        disclosure_id="disclosure-binding-1",
        boundary_id=boundary_key.boundary_id,
        key_ref=boundary_key.key_ref,
        tenant_id=binding.tenant_id,
        work_unit_id=binding.work_unit_id,
        workspace_id=binding.workspace_id,
        reht_evaluation_id="reht-eval-binding-1",
        fresh_state_root=governed_engine.state().root_hash(),
        fresh_authority_digest="d" * 64,
        fresh_evidence_digest="e" * 64,
        disclosed_at=now + timedelta(seconds=1),
    )
    disclosed = disclose_consequence_action(
        binding.sealed_action,
        context,
        boundary_private_key=private_key,
    )
    assert disclosed.action.action_id == "action-1"
    assert disclosed.execution_effect == "NONE"
