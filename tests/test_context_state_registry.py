from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ActionType,
    ConsequenceClass,
    PurposeRecordRef,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.context_registry import (
    ActionChainContextRegistry,
    ContextStateEventKind,
    ContextStateRegistryError,
    ContextStateStatus,
)
from src.valo_platform.decision_governance.continuity import canonical_digest
from src.valo_platform.decision_governance.models import (
    ActionCaseStatus,
    ActionChainContext,
    ChainContextFact,
)
from src.valo_platform.operational_continuity.context_fingerprint_reader import (
    RegisteredContextDecisionFingerprintReader,
)
from src.valo_platform.operational_continuity.fingerprint_readers import (
    FingerprintOwnerReaderError,
)
from src.valo_platform.operational_continuity.fingerprint_snapshot import (
    DecisionFingerprintKind,
)
from src.valo_platform.operational_continuity.observers import ObservationBinding


NOW = datetime(2026, 8, 1, 17, 0, tzinfo=timezone.utc)


def context(*, supplier="supplier-1", amount=100.0):
    return ActionChainContext(
        entity_ids=[supplier],
        supplier_ids=[supplier],
        recipient_ids=[supplier],
        destination_ids=[f"account:{supplier}"],
        amount=amount,
        currency="NOK",
        source_document_fingerprints=["sha256:invoice"],
        system_record_fingerprints=["sha256:erp-record"],
        prior_case_refs=["case:verification"],
        prior_clearance_refs=["clearance:verification"],
        ordering_refs=["order:1"],
        derived_facts=[
            ChainContextFact(
                fact=f"{supplier} passed verification",
                source_ref="supplier-registry:1",
                source_fingerprint="sha256:supplier-registry",
                established_at=NOW - timedelta(hours=1),
            )
        ],
    )


def register(
    registry,
    *,
    version="1",
    value=None,
    occurred_at=None,
    effective_from=None,
):
    return registry.register(
        tenant_id="tenant-1",
        context_id="payment-chain-1",
        version=version,
        context=value or context(),
        established_by="workflow-orchestrator",
        authority_ref="authority:workflow-context",
        reason=f"register context version {version}",
        evidence_refs=(f"evidence:context:{version}",),
        effective_from=effective_from or NOW - timedelta(minutes=10),
        effective_until=NOW + timedelta(hours=1),
        occurred_at=occurred_at or NOW - timedelta(minutes=10),
    )


def action_case(registered, **updates):
    values = dict(
        case_id="case-1",
        tenant_id="tenant-1",
        environment="test",
        record_version=3,
        case_hash=canonical_digest({"case": "case-1"}),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.CLEARED,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-1",
            version="1",
            record_ref="purpose:tenant-1:purpose-1:1",
            fingerprint="sha256:purpose",
            established_by="board",
            authority_ref="board:1",
        ),
        purpose_binding_ref="purpose:tenant-1:purpose-1:1#sha256:purpose",
        mandate_ref="mandate:tenant-1:mandate-1:1",
        mandate_fingerprint="sha256:mandate",
        policy_refs=("policy:1",),
        policy_fingerprint="sha256:policy",
        evidence_refs=("evidence:1",),
        evidence_fingerprint=canonical_digest(["evidence:1"]),
        context_refs=(registered.source_ref,),
        context_fingerprint=registered.context_digest,
        state_refs=("state:1",),
        state_fingerprint=canonical_digest({"case": "case-1"}),
        action_class=ActionType.PROCESS_PAYMENT,
        consequence_class=ConsequenceClass.HIGH,
        clearance_ref="clearance-1",
        created_at=NOW - timedelta(minutes=20),
        updated_at=NOW - timedelta(minutes=1),
        submitted_at=NOW - timedelta(minutes=15),
        evaluated_at=NOW - timedelta(minutes=10),
        cleared_at=NOW - timedelta(minutes=9),
    )
    values.update(updates)
    return ActionCaseRecord(**values)


def binding(record):
    return ObservationBinding(
        tenant_id=record.tenant_id,
        action_case_id=record.case_id,
        action_case_hash=record.case_hash,
        clearance_ref=record.clearance_ref,
        observer_ref="runtime:commit-boundary",
    )


def reader(registry, registered, record=None):
    record = record or action_case(registered)
    return RegisteredContextDecisionFingerprintReader(
        action_case=record,
        registry=registry,
        context_id=registered.context_id,
        version=registered.version,
    ), record


def test_register_exact_context_version_and_resolve_unique_active():
    registry = ActionChainContextRegistry()
    registered = register(registry)

    assert registered.context_digest == context().finalized().fingerprint
    assert registered.source_ref == (
        "action-chain-context:tenant-1:payment-chain-1:1"
    )
    assert registered.status is ContextStateStatus.ACTIVE
    assert registered.is_active(NOW)
    assert registry.get_exact("tenant-1", "payment-chain-1", "1") == registered
    assert registry.resolve_active(
        "tenant-1", "payment-chain-1", at=NOW
    ) == registered
    assert registry.verify_chain("tenant-1", "payment-chain-1")
    events = registry.events("tenant-1", "payment-chain-1")
    assert len(events) == 1
    assert events[0].event_kind is ContextStateEventKind.REGISTERED
    assert events[0].previous_event_hash is None


def test_exact_version_overwrite_is_forbidden():
    registry = ActionChainContextRegistry()
    register(registry)

    with pytest.raises(ContextStateRegistryError, match="overwrite is forbidden"):
        register(registry)


def test_multiple_active_versions_fail_closed_until_explicit_supersession():
    registry = ActionChainContextRegistry()
    first = register(registry)
    second = register(
        registry,
        version="2",
        value=context(amount=125.0),
        occurred_at=NOW - timedelta(minutes=5),
        effective_from=NOW - timedelta(minutes=5),
    )

    with pytest.raises(ContextStateRegistryError, match="multiple active"):
        registry.resolve_active("tenant-1", "payment-chain-1", at=NOW)

    updated = registry.supersede(
        "tenant-1",
        "payment-chain-1",
        first.version,
        superseded_by_version=second.version,
        actor_ref="workflow-orchestrator",
        authority_ref="authority:workflow-context",
        reason="new invoice amount established",
        evidence_refs=("evidence:context:supersede",),
        occurred_at=NOW - timedelta(minutes=1),
    )

    assert updated.status is ContextStateStatus.SUPERSEDED
    assert updated.superseded_by_ref == second.source_ref
    assert not updated.is_active(NOW)
    assert registry.resolve_active(
        "tenant-1", "payment-chain-1", at=NOW
    ).version == "2"
    events = registry.events("tenant-1", "payment-chain-1")
    assert [event.event_kind for event in events] == [
        ContextStateEventKind.REGISTERED,
        ContextStateEventKind.REGISTERED,
        ContextStateEventKind.SUPERSEDED,
    ]
    assert events[1].previous_event_hash == events[0].event_hash
    assert events[2].previous_event_hash == events[1].event_hash


def test_revoke_removes_context_from_active_resolution():
    registry = ActionChainContextRegistry()
    registered = register(registry)

    revoked = registry.revoke(
        "tenant-1",
        "payment-chain-1",
        registered.version,
        actor_ref="risk-owner",
        authority_ref="authority:risk-owner",
        reason="source record invalidated",
        evidence_refs=("evidence:context:revocation",),
        occurred_at=NOW - timedelta(seconds=1),
    )

    assert revoked.status is ContextStateStatus.REVOKED
    assert not revoked.is_active(NOW)
    with pytest.raises(ContextStateRegistryError, match="no active"):
        registry.resolve_active("tenant-1", "payment-chain-1", at=NOW)


def test_reader_returns_exact_registered_context_with_event_evidence():
    registry = ActionChainContextRegistry()
    registered = register(registry)
    context_reader, record = reader(registry, registered)

    observation = context_reader.read(
        binding=binding(record),
        observed_at=NOW,
    )

    assert observation.kind is DecisionFingerprintKind.CONTEXT
    assert observation.fingerprint == registered.context_digest
    assert observation.source_ref == registered.source_ref
    assert registered.latest_event_hash in observation.evidence_refs
    assert registered.authority_ref in observation.evidence_refs
    assert registered.source_ref in observation.evidence_refs


def test_reader_fails_closed_on_overlap_revocation_supersession_and_unbound_ref():
    registry = ActionChainContextRegistry()
    first = register(registry)
    context_reader, record = reader(registry, first)
    register(
        registry,
        version="2",
        value=context(amount=125.0),
        occurred_at=NOW - timedelta(minutes=5),
        effective_from=NOW - timedelta(minutes=5),
    )
    with pytest.raises(FingerprintOwnerReaderError, match="active resolution"):
        context_reader.read(binding=binding(record), observed_at=NOW)

    other_registry = ActionChainContextRegistry()
    active = register(other_registry)
    unbound_record = action_case(
        active,
        context_refs=("action-chain-context:tenant-1:other:1",),
    )
    unbound_reader, _ = reader(other_registry, active, unbound_record)
    with pytest.raises(FingerprintOwnerReaderError, match="does not bind"):
        unbound_reader.read(binding=binding(unbound_record), observed_at=NOW)

    revoked_registry = ActionChainContextRegistry()
    revoked = register(revoked_registry)
    revoked_reader, revoked_record = reader(revoked_registry, revoked)
    revoked_registry.revoke(
        "tenant-1",
        "payment-chain-1",
        "1",
        actor_ref="risk-owner",
        authority_ref="authority:risk-owner",
        reason="invalidated",
        evidence_refs=("evidence:revoke",),
        occurred_at=NOW - timedelta(seconds=1),
    )
    with pytest.raises(FingerprintOwnerReaderError, match="active resolution"):
        revoked_reader.read(binding=binding(revoked_record), observed_at=NOW)


def test_reader_rejects_context_fingerprint_mismatch_and_cross_case_binding():
    registry = ActionChainContextRegistry()
    registered = register(registry)
    changed_record = action_case(
        registered,
        context_fingerprint="sha256:changed",
    )
    changed_reader, _ = reader(registry, registered, changed_record)
    with pytest.raises(FingerprintOwnerReaderError, match="fingerprint changed"):
        changed_reader.read(binding=binding(changed_record), observed_at=NOW)

    normal_reader, record = reader(registry, registered)
    with pytest.raises(FingerprintOwnerReaderError, match="snapshot binding"):
        normal_reader.read(
            binding=binding(record).model_copy(
                update={"action_case_id": "other-case"}
            ),
            observed_at=NOW,
        )


def test_event_chain_tampering_is_detected_before_read():
    registry = ActionChainContextRegistry()
    registered = register(registry)
    original = registry._events[("tenant-1", "payment-chain-1")][0]
    registry._events[("tenant-1", "payment-chain-1")][0] = original.model_copy(
        update={"event_hash": "sha256:tampered"}
    )

    with pytest.raises(ContextStateRegistryError, match="tampered"):
        registry.get_exact("tenant-1", "payment-chain-1", registered.version)


def test_registry_rejects_backward_event_time_and_invalid_effective_window():
    registry = ActionChainContextRegistry()
    register(registry, occurred_at=NOW - timedelta(minutes=5))

    with pytest.raises(ContextStateRegistryError, match="backwards"):
        register(
            registry,
            version="2",
            value=context(amount=125.0),
            occurred_at=NOW - timedelta(minutes=6),
        )

    with pytest.raises(ContextStateRegistryError, match="effective_until"):
        registry.register(
            tenant_id="tenant-1",
            context_id="other-context",
            version="1",
            context=context(),
            established_by="workflow-orchestrator",
            authority_ref="authority:workflow-context",
            reason="invalid window",
            evidence_refs=("evidence:context",),
            effective_from=NOW,
            effective_until=NOW,
            occurred_at=NOW,
        )
