import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ActionType,
    ActorRole,
    ConsequenceClass,
    Reversibility,
)
from src.valo_platform.decision_governance.context_registry import (
    ContextStateEventKind,
    ContextStateRegistryError,
    ContextStateStatus,
)
from src.valo_platform.decision_governance.context_sqlite_registry import (
    SQLiteActionChainContextRegistry,
)
from src.valo_platform.decision_governance.models import (
    ActionCase,
    ActionCaseStatus,
    ActionChainContext,
    ChainContextFact,
    DecisionGovernanceError,
    DelegationGrant,
    MandateRecord,
    PurposeRecord,
)
from src.valo_platform.decision_governance.registered_context_action_case import (
    RegisteredContextActionClearanceService,
)
from src.valo_platform.decision_governance.registries import (
    DecisionGovernanceRegistry,
)
from src.valo_platform.decision_governance.store import (
    SQLiteDecisionGovernanceStore,
)


NOW = datetime.now(timezone.utc)


def context(*, amount=100.0):
    return ActionChainContext(
        entity_ids=["supplier-1"],
        supplier_ids=["supplier-1"],
        recipient_ids=["supplier-1"],
        destination_ids=["account:supplier-1"],
        amount=amount,
        currency="NOK",
        source_document_fingerprints=["sha256:invoice"],
        system_record_fingerprints=["sha256:erp-record"],
        prior_case_refs=["case:verification"],
        prior_clearance_refs=["clearance:verification"],
        ordering_refs=["order:1"],
        derived_facts=[
            ChainContextFact(
                fact="supplier-1 passed verification",
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


def governance_registry():
    registry = DecisionGovernanceRegistry()
    registry.register_purpose(
        PurposeRecord(
            purpose_id="purpose-1",
            version="1",
            tenant_id="tenant-1",
            statement="Generate supplier report",
            established_by="board",
            authority_ref="board:1",
            evidence_refs=["evidence:purpose"],
            effective_from=NOW - timedelta(days=1),
            effective_until=NOW + timedelta(days=1),
        )
    )
    registry.register_mandate(
        MandateRecord(
            mandate_id="mandate-1",
            version="1",
            tenant_id="tenant-1",
            purpose_id="purpose-1",
            purpose_version="1",
            holder_id="security-lead",
            action_types=[ActionType.GENERATE_REPORT],
            max_consequence_class=ConsequenceClass.HIGH,
            established_by="security-lead",
            authority_ref="authority:mandate",
            evidence_refs=["evidence:mandate"],
            effective_from=NOW - timedelta(days=1),
            effective_until=NOW + timedelta(days=1),
        )
    )
    registry.register_delegation(
        DelegationGrant(
            delegation_id="delegation-1",
            tenant_id="tenant-1",
            mandate_id="mandate-1",
            grantor_id="security-lead",
            grantee_id="agent-1",
            action_types=[ActionType.GENERATE_REPORT],
            max_consequence_class=ConsequenceClass.MEDIUM,
            evidence_refs=["evidence:delegation"],
            issued_at=NOW - timedelta(hours=1),
            effective_until=NOW + timedelta(hours=1),
        )
    )
    return registry


def action_case(*, case_id="case-1", amount=100.0):
    return ActionCase(
        case_id=case_id,
        tenant_id="tenant-1",
        actor_id="agent-1",
        actor_role=ActorRole.AUTOMATION,
        action_type=ActionType.GENERATE_REPORT,
        proposed_action="Generate supplier risk report",
        target_entity_id="supplier-1",
        target_entity_type="supplier",
        purpose_id="purpose-1",
        purpose_version="1",
        mandate_id="mandate-1",
        selected_means=["analysis"],
        objective="Identify supplier risk",
        assumptions=["source records are current"],
        evidence_refs=["evidence:contract"],
        alternatives=[{"ref": "alternative:manual-review"}],
        uncertainty=0.2,
        strongest_counterargument="Manual review may find more context.",
        falsification_conditions=["source records are stale"],
        consequence_class=ConsequenceClass.MEDIUM,
        reversibility=Reversibility.REVERSIBLE,
        status=ActionCaseStatus.DRAFT,
        chain_context=context(amount=amount),
    )


def clearance_service(tmp_path, context_registry):
    return RegisteredContextActionClearanceService(
        tenant_id="tenant-1",
        environment="test",
        registry=governance_registry(),
        store=SQLiteDecisionGovernanceStore(tmp_path / "governance.sqlite3"),
        context_registry=context_registry,
    )


def test_registration_and_exact_record_survive_process_restart(tmp_path):
    path = tmp_path / "context.sqlite3"
    first = SQLiteActionChainContextRegistry(path)
    registered = register(first)

    reopened = SQLiteActionChainContextRegistry(path)
    loaded = reopened.get_exact("tenant-1", "payment-chain-1", "1")

    assert loaded == registered
    assert reopened.resolve_active(
        "tenant-1", "payment-chain-1", at=NOW
    ) == registered
    assert reopened.verify_chain("tenant-1", "payment-chain-1")
    assert reopened.events("tenant-1", "payment-chain-1")[0].event_kind is (
        ContextStateEventKind.REGISTERED
    )
    assert reopened.record_history(
        "tenant-1", "payment-chain-1", "1"
    ) == (registered,)


def test_two_registry_instances_cannot_overwrite_exact_version(tmp_path):
    path = tmp_path / "context.sqlite3"
    first = SQLiteActionChainContextRegistry(path)
    second = SQLiteActionChainContextRegistry(path)
    register(first)

    with pytest.raises(ContextStateRegistryError, match="overwrite is forbidden"):
        register(second)

    assert len(first.events("tenant-1", "payment-chain-1")) == 1


def test_supersession_and_record_history_are_durable(tmp_path):
    path = tmp_path / "context.sqlite3"
    registry = SQLiteActionChainContextRegistry(path)
    first = register(registry)
    second = register(
        registry,
        version="2",
        value=context(amount=125.0),
        occurred_at=NOW - timedelta(minutes=5),
        effective_from=NOW - timedelta(minutes=5),
    )
    updated = registry.supersede(
        "tenant-1",
        "payment-chain-1",
        first.version,
        superseded_by_version=second.version,
        actor_ref="workflow-orchestrator",
        authority_ref="authority:workflow-context",
        reason="payment amount changed",
        evidence_refs=("evidence:context:supersede",),
        occurred_at=NOW - timedelta(seconds=1),
    )

    reopened = SQLiteActionChainContextRegistry(path)
    assert reopened.get_exact(
        "tenant-1", "payment-chain-1", "1"
    ).status is ContextStateStatus.SUPERSEDED
    assert reopened.resolve_active(
        "tenant-1", "payment-chain-1", at=NOW
    ).version == "2"
    history = reopened.record_history(
        "tenant-1", "payment-chain-1", "1"
    )
    assert len(history) == 2
    assert history[0].status is ContextStateStatus.ACTIVE
    assert history[1] == updated
    assert [event.event_kind for event in reopened.events(
        "tenant-1", "payment-chain-1"
    )] == [
        ContextStateEventKind.REGISTERED,
        ContextStateEventKind.REGISTERED,
        ContextStateEventKind.SUPERSEDED,
    ]


def test_revocation_and_snapshot_history_survive_restart(tmp_path):
    path = tmp_path / "context.sqlite3"
    registry = SQLiteActionChainContextRegistry(path)
    registered = register(registry)
    revoked = registry.revoke(
        "tenant-1",
        "payment-chain-1",
        registered.version,
        actor_ref="risk-owner",
        authority_ref="authority:risk-owner",
        reason="source record invalidated",
        evidence_refs=("evidence:context:revoke",),
        occurred_at=NOW - timedelta(seconds=1),
    )

    reopened = SQLiteActionChainContextRegistry(path)
    assert reopened.get_exact(
        "tenant-1", "payment-chain-1", "1"
    ) == revoked
    with pytest.raises(ContextStateRegistryError, match="no active"):
        reopened.resolve_active("tenant-1", "payment-chain-1", at=NOW)
    history = reopened.record_history(
        "tenant-1", "payment-chain-1", "1"
    )
    assert [item.status for item in history] == [
        ContextStateStatus.ACTIVE,
        ContextStateStatus.REVOKED,
    ]


def test_failed_transition_rolls_back_event_and_record_snapshot(tmp_path):
    path = tmp_path / "context.sqlite3"
    registry = SQLiteActionChainContextRegistry(path)
    register(registry)
    before_events = registry.events("tenant-1", "payment-chain-1")
    before_history = registry.record_history(
        "tenant-1", "payment-chain-1", "1"
    )

    with pytest.raises(ContextStateRegistryError, match="missing"):
        registry.supersede(
            "tenant-1",
            "payment-chain-1",
            "1",
            superseded_by_version="missing",
            actor_ref="workflow-orchestrator",
            authority_ref="authority:workflow-context",
            reason="invalid transition",
            evidence_refs=("evidence:invalid",),
            occurred_at=NOW - timedelta(seconds=1),
        )

    reopened = SQLiteActionChainContextRegistry(path)
    assert reopened.events("tenant-1", "payment-chain-1") == before_events
    assert reopened.record_history(
        "tenant-1", "payment-chain-1", "1"
    ) == before_history


def test_event_payload_and_hash_column_tampering_are_detected(tmp_path):
    path = tmp_path / "context.sqlite3"
    registry = SQLiteActionChainContextRegistry(path)
    register(registry)

    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            UPDATE action_chain_context_events
            SET event_hash = 'sha256:tampered'
            WHERE tenant_id = 'tenant-1' AND context_id = 'payment-chain-1'
            """
        )

    reopened = SQLiteActionChainContextRegistry(path)
    with pytest.raises(ContextStateRegistryError, match="hash column mismatch"):
        reopened.verify_chain("tenant-1", "payment-chain-1")


def test_current_record_and_snapshot_tampering_are_detected(tmp_path):
    current_path = tmp_path / "current.sqlite3"
    current = SQLiteActionChainContextRegistry(current_path)
    register(current)
    with sqlite3.connect(current_path) as connection:
        connection.execute(
            """
            UPDATE action_chain_context_records
            SET context_digest = 'sha256:tampered'
            WHERE tenant_id = 'tenant-1' AND context_id = 'payment-chain-1'
            """
        )
    with pytest.raises(ContextStateRegistryError, match="columns do not match"):
        SQLiteActionChainContextRegistry(current_path).get_exact(
            "tenant-1", "payment-chain-1", "1"
        )

    snapshot_path = tmp_path / "snapshot.sqlite3"
    snapshots = SQLiteActionChainContextRegistry(snapshot_path)
    register(snapshots)
    with sqlite3.connect(snapshot_path) as connection:
        connection.execute(
            """
            UPDATE action_chain_context_record_snapshots
            SET record_digest = 'sha256:tampered'
            WHERE tenant_id = 'tenant-1' AND context_id = 'payment-chain-1'
            """
        )
    with pytest.raises(ContextStateRegistryError, match="snapshot columns"):
        SQLiteActionChainContextRegistry(snapshot_path).verify_chain(
            "tenant-1", "payment-chain-1"
        )


def test_multiple_active_versions_remain_fail_closed_after_restart(tmp_path):
    path = tmp_path / "context.sqlite3"
    registry = SQLiteActionChainContextRegistry(path)
    register(registry)
    register(
        registry,
        version="2",
        value=context(amount=125.0),
        occurred_at=NOW - timedelta(minutes=5),
        effective_from=NOW - timedelta(minutes=5),
    )

    with pytest.raises(ContextStateRegistryError, match="multiple active"):
        SQLiteActionChainContextRegistry(path).resolve_active(
            "tenant-1", "payment-chain-1", at=NOW
        )


def test_strict_action_case_service_can_reopen_registry_before_submit(tmp_path):
    context_path = tmp_path / "context.sqlite3"
    registry = SQLiteActionChainContextRegistry(context_path)
    registered = register(registry)
    first_service = clearance_service(tmp_path, registry)
    created = first_service.create_case(
        action_case(),
        registered_context_ref=registered.source_ref,
    )

    reopened_registry = SQLiteActionChainContextRegistry(context_path)
    reopened_service = RegisteredContextActionClearanceService(
        tenant_id="tenant-1",
        environment="test",
        registry=first_service.registry,
        store=SQLiteDecisionGovernanceStore(tmp_path / "governance.sqlite3"),
        context_registry=reopened_registry,
    )
    submitted = reopened_service.submit(created.case_id)

    assert submitted.case_id == created.case_id
    assert submitted.context_fingerprint == registered.context_digest
    assert reopened_registry.verify_chain("tenant-1", "payment-chain-1")


def test_strict_service_detects_durable_revocation_after_restart(tmp_path):
    context_path = tmp_path / "context.sqlite3"
    registry = SQLiteActionChainContextRegistry(context_path)
    registered = register(registry)
    first_service = clearance_service(tmp_path, registry)
    created = first_service.create_case(
        action_case(),
        registered_context_ref=registered.source_ref,
    )
    registry.revoke(
        "tenant-1",
        "payment-chain-1",
        "1",
        actor_ref="risk-owner",
        authority_ref="authority:risk-owner",
        reason="invalidated after creation",
        evidence_refs=("evidence:revoke",),
        occurred_at=NOW - timedelta(seconds=1),
    )

    reopened = SQLiteActionChainContextRegistry(context_path)
    second_service = RegisteredContextActionClearanceService(
        tenant_id="tenant-1",
        environment="test",
        registry=first_service.registry,
        store=SQLiteDecisionGovernanceStore(tmp_path / "governance.sqlite3"),
        context_registry=reopened,
    )
    with pytest.raises(DecisionGovernanceError, match="no longer uniquely active"):
        second_service.submit(created.case_id)
