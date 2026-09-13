from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ActionType,
    ActorRole,
    ConsequenceClass,
    Reversibility,
)
from src.valo_platform.decision_governance.context_registry import (
    ActionChainContextRegistry,
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
from src.valo_platform.decision_governance.action_case import (
    DefaultActionClearanceService,
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


def governance_registry() -> DecisionGovernanceRegistry:
    registry = DecisionGovernanceRegistry()
    registry.register_purpose(
        PurposeRecord(
            purpose_id="purpose-1",
            version="1",
            tenant_id="tenant-1",
            statement="Create a verified supplier report",
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


def chain_context(*, supplier="supplier-1", amount=100.0) -> ActionChainContext:
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


def register_context(
    registry: ActionChainContextRegistry,
    *,
    version="1",
    value=None,
    effective_from=None,
    occurred_at=None,
):
    return registry.register(
        tenant_id="tenant-1",
        context_id="supplier-report-1",
        version=version,
        context=value or chain_context(),
        established_by="workflow-orchestrator",
        authority_ref="authority:workflow-context",
        reason=f"register context version {version}",
        evidence_refs=(f"evidence:context:{version}",),
        effective_from=effective_from or NOW - timedelta(minutes=10),
        effective_until=NOW + timedelta(hours=1),
        occurred_at=occurred_at or NOW - timedelta(minutes=10),
    )


def action_case(*, case_id="case-1", context=None, **updates) -> ActionCase:
    values = dict(
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
        strongest_counterargument="A manual review may find more context.",
        falsification_conditions=["source records are stale"],
        consequence_class=ConsequenceClass.MEDIUM,
        reversibility=Reversibility.REVERSIBLE,
        status=ActionCaseStatus.DRAFT,
        chain_context=context,
    )
    values.update(updates)
    return ActionCase(**values)


def service(tmp_path, context_registry):
    return RegisteredContextActionClearanceService(
        tenant_id="tenant-1",
        environment="test",
        registry=governance_registry(),
        store=SQLiteDecisionGovernanceStore(tmp_path / "governance.sqlite3"),
        context_registry=context_registry,
    )


def test_create_case_binds_exact_context_ref_digest_and_registry_snapshot(tmp_path):
    contexts = ActionChainContextRegistry()
    registered = register_context(contexts)
    svc = service(tmp_path, contexts)
    draft = action_case(context=chain_context())

    record = svc.create_case(
        draft,
        registered_context_ref=registered.source_ref,
    )

    assert registered.source_ref in record.context_refs
    assert f"action-chain-context-record:{registered.record_digest}" in record.context_refs
    assert record.context_fingerprint == registered.context_digest
    assert record.case_hash.startswith("sha256:")
    assert svc.create_case(
        draft,
        registered_context_ref=registered.source_ref,
    ) == record


def test_context_ref_is_required_and_cannot_be_supplied_without_context(tmp_path):
    contexts = ActionChainContextRegistry()
    registered = register_context(contexts)
    svc = service(tmp_path, contexts)

    with pytest.raises(DecisionGovernanceError, match="requires an exact"):
        svc.create_case(action_case(context=chain_context()))

    with pytest.raises(DecisionGovernanceError, match="without chain_context"):
        svc.create_case(
            action_case(case_id="case-no-context", context=None),
            registered_context_ref=registered.source_ref,
        )


def test_legacy_clearance_service_rejects_context_bearing_action_case(tmp_path):
    legacy = DefaultActionClearanceService(
        tenant_id="tenant-1",
        environment="test",
        registry=governance_registry(),
        store=SQLiteDecisionGovernanceStore(tmp_path / "governance.sqlite3"),
    )

    with pytest.raises(
        DecisionGovernanceError,
        match="requires RegisteredContextActionClearanceService",
    ):
        legacy.create_case(action_case(context=chain_context()))


def test_context_ref_must_be_exact_and_tenant_scoped(tmp_path):
    contexts = ActionChainContextRegistry()
    register_context(contexts)
    svc = service(tmp_path, contexts)
    draft = action_case(context=chain_context())

    with pytest.raises(DecisionGovernanceError, match="must be"):
        svc.create_case(draft, registered_context_ref="context:latest")

    with pytest.raises(DecisionGovernanceError, match="crosses tenant"):
        svc.create_case(
            draft,
            registered_context_ref=(
                "action-chain-context:other:supplier-report-1:1"
            ),
        )


def test_chain_context_payload_must_match_registered_digest(tmp_path):
    contexts = ActionChainContextRegistry()
    registered = register_context(contexts)
    svc = service(tmp_path, contexts)

    with pytest.raises(DecisionGovernanceError, match="does not match"):
        svc.create_case(
            action_case(context=chain_context(amount=125.0)),
            registered_context_ref=registered.source_ref,
        )


def test_multiple_active_versions_fail_closed_without_latest_wins(tmp_path):
    contexts = ActionChainContextRegistry()
    first = register_context(contexts)
    register_context(
        contexts,
        version="2",
        value=chain_context(amount=125.0),
        effective_from=NOW - timedelta(minutes=5),
        occurred_at=NOW - timedelta(minutes=5),
    )
    svc = service(tmp_path, contexts)

    with pytest.raises(DecisionGovernanceError, match="active resolution"):
        svc.create_case(
            action_case(context=chain_context()),
            registered_context_ref=first.source_ref,
        )


def test_context_revocation_after_create_blocks_submit(tmp_path):
    contexts = ActionChainContextRegistry()
    registered = register_context(contexts)
    svc = service(tmp_path, contexts)
    record = svc.create_case(
        action_case(context=chain_context()),
        registered_context_ref=registered.source_ref,
    )
    contexts.revoke(
        "tenant-1",
        "supplier-report-1",
        "1",
        actor_ref="risk-owner",
        authority_ref="authority:risk-owner",
        reason="supplier evidence invalidated",
        evidence_refs=("evidence:context:revoke",),
        occurred_at=NOW - timedelta(seconds=1),
    )

    with pytest.raises(DecisionGovernanceError, match="no longer uniquely active"):
        svc.submit(record.case_id)


def test_context_supersession_after_create_blocks_old_case_submit(tmp_path):
    contexts = ActionChainContextRegistry()
    first = register_context(contexts)
    svc = service(tmp_path, contexts)
    record = svc.create_case(
        action_case(context=chain_context()),
        registered_context_ref=first.source_ref,
    )
    second = register_context(
        contexts,
        version="2",
        value=chain_context(amount=125.0),
        effective_from=NOW - timedelta(minutes=5),
        occurred_at=NOW - timedelta(minutes=5),
    )
    contexts.supersede(
        "tenant-1",
        "supplier-report-1",
        "1",
        superseded_by_version=second.version,
        actor_ref="workflow-orchestrator",
        authority_ref="authority:workflow-context",
        reason="supplier amount changed",
        evidence_refs=("evidence:context:supersede",),
        occurred_at=NOW - timedelta(seconds=1),
    )

    with pytest.raises(DecisionGovernanceError, match="no longer the unique active"):
        svc.submit(record.case_id)


def test_new_case_can_bind_successor_only_after_explicit_supersession(tmp_path):
    contexts = ActionChainContextRegistry()
    first = register_context(contexts)
    second = register_context(
        contexts,
        version="2",
        value=chain_context(amount=125.0),
        effective_from=NOW - timedelta(minutes=5),
        occurred_at=NOW - timedelta(minutes=5),
    )
    contexts.supersede(
        "tenant-1",
        "supplier-report-1",
        first.version,
        superseded_by_version=second.version,
        actor_ref="workflow-orchestrator",
        authority_ref="authority:workflow-context",
        reason="supplier amount changed",
        evidence_refs=("evidence:context:supersede",),
        occurred_at=NOW - timedelta(seconds=1),
    )
    svc = service(tmp_path, contexts)
    record = svc.create_case(
        action_case(
            case_id="case-2",
            context=chain_context(amount=125.0),
        ),
        registered_context_ref=second.source_ref,
    )

    submitted = svc.submit(record.case_id)
    assert submitted.case_id == "case-2"
    assert submitted.context_fingerprint == second.context_digest
    assert second.source_ref in submitted.context_refs


def test_case_hash_changes_when_registered_context_version_changes(tmp_path):
    contexts = ActionChainContextRegistry()
    first = register_context(contexts)
    svc = service(tmp_path, contexts)
    first_record = svc.create_case(
        action_case(case_id="case-1", context=chain_context()),
        registered_context_ref=first.source_ref,
    )

    second = register_context(
        contexts,
        version="2",
        value=chain_context(amount=125.0),
        effective_from=NOW - timedelta(minutes=5),
        occurred_at=NOW - timedelta(minutes=5),
    )
    contexts.supersede(
        "tenant-1",
        "supplier-report-1",
        first.version,
        superseded_by_version=second.version,
        actor_ref="workflow-orchestrator",
        authority_ref="authority:workflow-context",
        reason="new amount",
        evidence_refs=("evidence:context:supersede",),
        occurred_at=NOW - timedelta(seconds=1),
    )
    second_record = svc.create_case(
        action_case(
            case_id="case-2",
            context=chain_context(amount=125.0),
        ),
        registered_context_ref=second.source_ref,
    )

    assert first_record.case_hash != second_record.case_hash
    assert first_record.context_fingerprint != second_record.context_fingerprint


def test_submit_rejects_tampered_context_record_binding(tmp_path):
    contexts = ActionChainContextRegistry()
    registered = register_context(contexts)
    svc = service(tmp_path, contexts)
    record = svc.create_case(
        action_case(context=chain_context()),
        registered_context_ref=registered.source_ref,
    )
    tampered = record.model_copy(
        update={
            "record_version": 2,
            "context_refs": (
                registered.source_ref,
                "action-chain-context-record:sha256:tampered",
            ),
            "updated_at": datetime.now(timezone.utc),
        }
    )
    svc._insert_record(tampered)

    with pytest.raises(DecisionGovernanceError, match="registry record changed"):
        svc.submit(record.case_id)
