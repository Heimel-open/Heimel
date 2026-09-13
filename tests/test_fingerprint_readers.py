from datetime import datetime, timedelta, timezone

import pytest

from services.evidence_store.store import EvidenceItem, EvidenceStore
from src.valo_platform.action_envelope.models import (
    ActionType,
    ConsequenceClass,
)
from src.valo_platform.content_operations.policy_profile import (
    PublicationPolicyProfile,
)
from src.valo_platform.content_operations.policy_registry import (
    PublicationPolicyRegistry,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.continuity import canonical_digest
from src.valo_platform.decision_governance.models import (
    ActionCaseStatus,
    DelegationGrant,
    MandateRecord,
    PurposeRecord,
)
from src.valo_platform.decision_governance.registries import (
    DecisionGovernanceRegistry,
)
from src.valo_platform.decision_governance.store import (
    SQLiteDecisionGovernanceStore,
)
from src.valo_platform.operational_continuity.fingerprint_readers import (
    AuthorityRegistryDecisionFingerprintReader,
    EvidenceStoreDecisionFingerprintReader,
    FingerprintOwnerReaderError,
    RegisteredPolicyDecisionFingerprintReader,
    SQLiteActionCaseStateDecisionFingerprintReader,
    build_canonical_owner_fingerprint_provider,
)
from src.valo_platform.operational_continuity.fingerprint_snapshot import (
    CallableDecisionFingerprintReader,
    DecisionFingerprintKind,
    DecisionFingerprintObservation,
)
from src.valo_platform.operational_continuity.observers import ObservationBinding
from src.valo_platform.operational_continuity.source_adapters import (
    EvidenceStoreSourceAdapter,
)


NOW = datetime(2026, 8, 1, 16, 30, tzinfo=timezone.utc)


def authority_registry():
    registry = DecisionGovernanceRegistry()
    purpose = registry.register_purpose(
        PurposeRecord(
            purpose_id="purpose-1",
            version="1",
            tenant_id="tenant-1",
            statement="Pay approved supplier invoices",
            established_by="board",
            authority_ref="board:1",
            evidence_refs=["evidence:purpose"],
            effective_from=NOW - timedelta(days=1),
            effective_until=NOW + timedelta(days=1),
        )
    )
    mandate = registry.register_mandate(
        MandateRecord(
            mandate_id="mandate-1",
            version="3",
            tenant_id="tenant-1",
            purpose_id=purpose.purpose_id,
            purpose_version=purpose.version,
            holder_id="finance-team",
            action_types=[ActionType.PROCESS_PAYMENT],
            max_consequence_class=ConsequenceClass.HIGH,
            established_by="cfo",
            authority_ref="cfo:1",
            evidence_refs=["evidence:mandate"],
            effective_from=NOW - timedelta(days=1),
            effective_until=NOW + timedelta(days=1),
        )
    )
    delegation = registry.register_delegation(
        DelegationGrant(
            delegation_id="delegation-1",
            tenant_id="tenant-1",
            mandate_id=mandate.mandate_id,
            grantor_id="cfo",
            grantee_id="agent-1",
            action_types=[ActionType.PROCESS_PAYMENT],
            max_consequence_class=ConsequenceClass.HIGH,
            evidence_refs=["evidence:delegation"],
            issued_at=NOW - timedelta(hours=1),
            effective_until=NOW + timedelta(hours=1),
        )
    )
    return registry, purpose, mandate, delegation


def publication_policy(mandate):
    return PublicationPolicyProfile(
        policy_id="policy-1",
        version="7",
        tenant_id="tenant-1",
        established_by="publisher",
        authority_ref="publisher:authority",
        mandate_ref=f"mandate:tenant-1:{mandate.mandate_id}:{mandate.version}",
        mandate_fingerprint=mandate.fingerprint,
        allowed_principal_ids=("agent-1",),
        allowed_providers=("sanity",),
        allowed_account_refs=("account-1",),
        allowed_channel_refs=("channel-1",),
        allowed_languages=("en",),
        allowed_jurisdictions=("NO",),
        effective_from=NOW - timedelta(hours=1),
        effective_until=NOW + timedelta(hours=1),
    )


def action_case(purpose, mandate, delegation, policy):
    evidence_refs = ("evidence:e1", "evidence:e2")
    case_hash = canonical_digest({"case": "case-1", "version": 1})
    return ActionCaseRecord(
        case_id="case-1",
        tenant_id="tenant-1",
        environment="test",
        record_version=3,
        case_hash=case_hash,
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.CLEARED,
        purpose_record_ref=purpose.to_ref(),
        purpose_binding_ref=(
            f"{purpose.to_ref().record_ref}#{purpose.to_ref().fingerprint}"
        ),
        mandate_ref=f"mandate:tenant-1:{mandate.mandate_id}:{mandate.version}",
        mandate_fingerprint=mandate.fingerprint,
        delegation_ref=f"delegation:tenant-1:{delegation.delegation_id}",
        delegation_fingerprint=delegation.fingerprint,
        policy_refs=(
            f"publication-policy-registry:tenant-1:{policy.policy_id}:{policy.version}",
        ),
        policy_fingerprint=policy.digest(),
        evidence_refs=evidence_refs,
        evidence_fingerprint=canonical_digest(list(evidence_refs)),
        context_refs=("context:1",),
        context_fingerprint=canonical_digest({"context": 1}),
        state_refs=("state:1",),
        state_fingerprint=case_hash,
        action_class=ActionType.PROCESS_PAYMENT,
        consequence_class=ConsequenceClass.HIGH,
        clearance_ref="clearance-1",
        created_at=NOW - timedelta(minutes=20),
        updated_at=NOW - timedelta(minutes=1),
        submitted_at=NOW - timedelta(minutes=15),
        evaluated_at=NOW - timedelta(minutes=10),
        cleared_at=NOW - timedelta(minutes=9),
    )


def binding(record):
    return ObservationBinding(
        tenant_id=record.tenant_id,
        action_case_id=record.case_id,
        action_case_hash=record.case_hash,
        clearance_ref=record.clearance_ref,
        observer_ref="runtime:commit-boundary",
    )


def policy_registry(policy):
    registry = PublicationPolicyRegistry()
    registry.register(
        policy,
        actor_ref="publisher",
        authority_ref=policy.authority_ref,
        reason="initial registration",
        occurred_at=NOW - timedelta(minutes=30),
        evidence_refs=("evidence:policy-registration",),
    )
    return registry


def evidence_adapter(tmp_path, record):
    store = EvidenceStore(str(tmp_path / "evidence"))
    for evidence_id in ("e1", "e2"):
        store.append(
            EvidenceItem(
                evidence_id=evidence_id,
                receipt_id="receipt-1",
                tenant_id="tenant-1",
                evidence_type="test",
                payload={"id": evidence_id},
                created_at=(NOW - timedelta(minutes=5)).isoformat(),
            )
        )
    adapter = EvidenceStoreSourceAdapter(
        binding=binding(record),
        store=store,
        receipt_id="receipt-1",
        required_evidence_ids=("e1", "e2"),
        max_age=timedelta(hours=1),
    )
    return store, adapter


def action_case_store(tmp_path, record):
    store = SQLiteDecisionGovernanceStore(tmp_path / "decision.db")
    store._insert(
        tenant_id=record.tenant_id,
        artifact_type="action_case_record",
        artifact_id=record.case_id,
        artifact_version=str(record.record_version),
        fingerprint=record.case_hash,
        model=record,
    )
    return store


def context_reader(record):
    def read(snapshot_binding, observed_at):
        return DecisionFingerprintObservation(
            binding=snapshot_binding,
            kind=DecisionFingerprintKind.CONTEXT,
            fingerprint=record.context_fingerprint,
            source_ref="context-owner:tenant-1:case-1",
            reader_ref="context-owner-reader:1",
            evidence_refs=("context:1",),
            observed_at=observed_at,
        )

    return CallableDecisionFingerprintReader(
        kind=DecisionFingerprintKind.CONTEXT,
        reader=read,
    )


def owner_readers(tmp_path):
    authority, purpose, mandate, delegation = authority_registry()
    policy = publication_policy(mandate)
    record = action_case(purpose, mandate, delegation, policy)
    policies = policy_registry(policy)
    _, evidence = evidence_adapter(tmp_path, record)
    action_cases = action_case_store(tmp_path, record)
    return {
        "record": record,
        "authority_registry": authority,
        "policy_registry": policies,
        "evidence_adapter": evidence,
        "action_case_store": action_cases,
        "authority": AuthorityRegistryDecisionFingerprintReader(
            action_case=record,
            registry=authority,
        ),
        "policy": RegisteredPolicyDecisionFingerprintReader(
            action_case=record,
            registry=policies,
            policy_id=policy.policy_id,
            version=policy.version,
        ),
        "evidence": EvidenceStoreDecisionFingerprintReader(
            action_case=record,
            adapter=evidence,
            expected_source_fingerprint=evidence.fingerprint(observed_at=NOW),
        ),
        "state": SQLiteActionCaseStateDecisionFingerprintReader(
            action_case=record,
            store=action_cases,
        ),
        "context": context_reader(record),
    }


def test_all_owner_readers_build_one_exact_current_snapshot(tmp_path):
    readers = owner_readers(tmp_path)
    provider = build_canonical_owner_fingerprint_provider(
        authority_reader=readers["authority"],
        policy_reader=readers["policy"],
        context_reader=readers["context"],
        state_reader=readers["state"],
        evidence_reader=readers["evidence"],
    )

    snapshot = provider.snapshot(
        binding=binding(readers["record"]),
        observed_at=NOW,
    )

    record = readers["record"]
    assert snapshot.as_mapping() == {
        "authority": record.delegation_fingerprint,
        "policy": record.policy_fingerprint,
        "context": record.context_fingerprint,
        "state": record.case_hash,
        "evidence": record.evidence_fingerprint,
    }
    assert snapshot.evidence_ref.startswith("current-decision-fingerprints:sha256:")
    assert any(ref.startswith("action-case-record:") for ref in snapshot.evidence_refs)
    assert any(ref.startswith("sha256:") for ref in snapshot.evidence_refs)


def test_authority_reader_fails_closed_on_revoked_pinned_delegation(tmp_path):
    readers = owner_readers(tmp_path)
    readers["authority_registry"].revoke_delegation(
        "tenant-1", "delegation-1"
    )

    with pytest.raises(FingerprintOwnerReaderError, match="not active"):
        readers["authority"].read(
            binding=binding(readers["record"]),
            observed_at=NOW,
        )


def test_authority_reader_fails_closed_on_cross_tenant_or_changed_fingerprint(tmp_path):
    readers = owner_readers(tmp_path)
    record = readers["record"]
    cross_tenant = record.model_copy(
        update={"mandate_ref": "mandate:other:mandate-1:3"}
    )
    reader = AuthorityRegistryDecisionFingerprintReader(
        action_case=cross_tenant,
        registry=readers["authority_registry"],
    )
    with pytest.raises(FingerprintOwnerReaderError, match="crosses tenant"):
        reader.read(binding=binding(cross_tenant), observed_at=NOW)

    changed = record.model_copy(update={"delegation_fingerprint": "sha256:changed"})
    reader = AuthorityRegistryDecisionFingerprintReader(
        action_case=changed,
        registry=readers["authority_registry"],
    )
    with pytest.raises(FingerprintOwnerReaderError, match="fingerprint changed"):
        reader.read(binding=binding(changed), observed_at=NOW)


def test_policy_reader_fails_closed_on_revocation_and_unbound_version(tmp_path):
    readers = owner_readers(tmp_path)
    policy_reader = readers["policy"]
    readers["policy_registry"].revoke(
        "tenant-1",
        "policy-1",
        "7",
        actor_ref="publisher",
        authority_ref="publisher:authority",
        reason="withdrawn",
        occurred_at=NOW - timedelta(seconds=1),
        evidence_refs=("evidence:policy-revocation",),
    )
    with pytest.raises(FingerprintOwnerReaderError, match="not active"):
        policy_reader.read(
            binding=binding(readers["record"]),
            observed_at=NOW,
        )

    record = readers["record"].model_copy(update={"policy_refs": ("policy:legacy",)})
    unbound = RegisteredPolicyDecisionFingerprintReader(
        action_case=record,
        registry=readers["policy_registry"],
        policy_id="policy-1",
        version="7",
    )
    with pytest.raises(FingerprintOwnerReaderError, match="does not bind"):
        unbound.read(binding=binding(record), observed_at=NOW)


def test_evidence_reader_requires_exact_store_ids_and_current_rows(tmp_path):
    readers = owner_readers(tmp_path)
    observation = readers["evidence"].read(
        binding=binding(readers["record"]),
        observed_at=NOW,
    )
    assert observation.fingerprint == readers["record"].evidence_fingerprint
    assert "evidence:e1" in observation.evidence_refs
    assert "evidence:e2" in observation.evidence_refs

    record = readers["record"].model_copy(
        update={
            "evidence_refs": ("evidence:e1", "evidence:unowned"),
            "evidence_fingerprint": canonical_digest(
                ["evidence:e1", "evidence:unowned"]
            ),
        }
    )
    mismatched = EvidenceStoreDecisionFingerprintReader(
        action_case=record,
        adapter=readers["evidence_adapter"],
        expected_source_fingerprint=readers["evidence"].expected_source_fingerprint,
    )
    with pytest.raises(FingerprintOwnerReaderError, match="exactly match"):
        mismatched.read(binding=binding(record), observed_at=NOW)


def test_evidence_reader_fails_closed_when_required_row_is_missing(tmp_path):
    authority, purpose, mandate, delegation = authority_registry()
    policy = publication_policy(mandate)
    record = action_case(purpose, mandate, delegation, policy)
    store = EvidenceStore(str(tmp_path / "missing-evidence"))
    store.append(
        EvidenceItem(
            evidence_id="e1",
            receipt_id="receipt-1",
            tenant_id="tenant-1",
            evidence_type="test",
            payload={"id": "e1"},
            created_at=(NOW - timedelta(minutes=5)).isoformat(),
        )
    )
    adapter = EvidenceStoreSourceAdapter(
        binding=binding(record),
        store=store,
        receipt_id="receipt-1",
        required_evidence_ids=("e1", "e2"),
    )
    reader = EvidenceStoreDecisionFingerprintReader(
        action_case=record,
        adapter=adapter,
        expected_source_fingerprint="sha256:baseline",
    )
    with pytest.raises(FingerprintOwnerReaderError, match="missing or expired"):
        reader.read(binding=binding(record), observed_at=NOW)


def test_state_reader_uses_latest_record_and_rejects_stale_clearance(tmp_path):
    readers = owner_readers(tmp_path)
    record = readers["record"]
    observation = readers["state"].read(
        binding=binding(record),
        observed_at=NOW,
    )
    assert observation.fingerprint == record.case_hash
    assert f"v{record.record_version}" in observation.source_ref

    newer = record.model_copy(
        update={
            "record_version": record.record_version + 1,
            "clearance_ref": "clearance-2",
            "updated_at": NOW - timedelta(seconds=1),
        }
    )
    readers["action_case_store"]._insert(
        tenant_id=newer.tenant_id,
        artifact_type="action_case_record",
        artifact_id=newer.case_id,
        artifact_version=str(newer.record_version),
        fingerprint=newer.case_hash,
        model=newer,
    )
    with pytest.raises(FingerprintOwnerReaderError, match="no longer binds"):
        readers["state"].read(binding=binding(record), observed_at=NOW)


def test_state_reader_rejects_revoked_or_future_record(tmp_path):
    readers = owner_readers(tmp_path)
    record = readers["record"]
    revoked = record.model_copy(
        update={
            "record_version": record.record_version + 1,
            "lifecycle_state": ActionCaseLifecycleState.REVOKED,
            "updated_at": NOW - timedelta(seconds=1),
            "revoked_at": NOW - timedelta(seconds=1),
        }
    )
    readers["action_case_store"]._insert(
        tenant_id=revoked.tenant_id,
        artifact_type="action_case_record",
        artifact_id=revoked.case_id,
        artifact_version=str(revoked.record_version),
        fingerprint=revoked.case_hash,
        model=revoked,
    )
    with pytest.raises(FingerprintOwnerReaderError, match="not executable"):
        readers["state"].read(binding=binding(record), observed_at=NOW)


def test_provider_requires_explicit_context_owner_reader(tmp_path):
    readers = owner_readers(tmp_path)
    wrong_context = CallableDecisionFingerprintReader(
        kind=DecisionFingerprintKind.POLICY,
        reader=lambda snapshot_binding, observed_at: readers["policy"].read(
            binding=snapshot_binding,
            observed_at=observed_at,
        ),
    )
    with pytest.raises(FingerprintOwnerReaderError, match="explicit context"):
        build_canonical_owner_fingerprint_provider(
            authority_reader=readers["authority"],
            policy_reader=readers["policy"],
            context_reader=wrong_context,
            state_reader=readers["state"],
            evidence_reader=readers["evidence"],
        )
