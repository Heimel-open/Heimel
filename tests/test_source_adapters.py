from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from services.evidence_store.store import EvidenceItem, EvidenceStore
from src.valo_platform.action_envelope.models import ActionType, ConsequenceClass
from src.valo_platform.action_envelope.transition_models import (
    RevisionType,
    TargetStateBinding,
)
from src.valo_platform.content_operations.policy_profile import PublicationPolicyProfile
from src.valo_platform.decision_governance.continuity import ContinuityTriggerKind
from src.valo_platform.decision_governance.models import MandateRecord, RegistryStatus
from src.valo_platform.decision_governance.registries import DecisionGovernanceRegistry
from src.valo_platform.operational_continuity.observers import ObservationBinding
from src.valo_platform.operational_continuity.source_adapters import (
    EvidenceStoreSourceAdapter,
    MandateRegistrySourceAdapter,
    PublicationPolicySourceAdapter,
    SourceObservationError,
    TargetStateSourceAdapter,
    build_source_bundle,
)


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
SHA = "sha256:" + "1" * 64


def binding(**updates) -> ObservationBinding:
    data = dict(
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash="sha256:case-1",
        clearance_ref="clearance-1",
        observer_ref="observer:source-bridge",
    )
    data.update(updates)
    return ObservationBinding(**data)


def policy(**updates) -> PublicationPolicyProfile:
    data = dict(
        policy_id="publication-default",
        version="1",
        tenant_id="tenant-1",
        established_by="board",
        authority_ref="board-resolution:1",
        mandate_ref="mandate:tenant-1:publish:1",
        mandate_fingerprint=SHA,
        allowed_principal_ids=("publisher-1",),
        allowed_providers=("provider-1",),
        allowed_account_refs=("account-1",),
        allowed_channel_refs=("channel-1",),
        allowed_languages=("en",),
        allowed_jurisdictions=("NO",),
        effective_from=NOW - timedelta(days=1),
        effective_until=NOW + timedelta(hours=1),
    )
    data.update(updates)
    return PublicationPolicyProfile(**data)


def mandate(**updates) -> MandateRecord:
    data = dict(
        mandate_id="pay",
        version="1",
        tenant_id="tenant-1",
        purpose_id="finance",
        purpose_version="1",
        holder_id="finance-team",
        action_types=[ActionType.PROCESS_PAYMENT],
        max_consequence_class=ConsequenceClass.HIGH,
        established_by="board",
        authority_ref="board-resolution:pay",
        evidence_refs=["evidence:mandate"],
        effective_from=NOW - timedelta(days=1),
        effective_until=NOW + timedelta(days=1),
    )
    data.update(updates)
    return MandateRecord(**data).finalized()


def target_state(**updates) -> TargetStateBinding:
    data = dict(
        system_id="erp",
        object_id="invoice-1",
        revision_type=RevisionType.VERSION,
        revision_value="7",
        observed_at=NOW,
        current_state_hash="sha256:invoice-v7",
        state_witness_ref="erp-witness:7",
    )
    data.update(updates)
    return TargetStateBinding(**data)


def test_policy_source_detects_effective_window_change_without_authority():
    adapter = PublicationPolicySourceAdapter(binding=binding(), policy=policy())
    expected = adapter.fingerprint(observed_at=NOW)

    stable = adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW + timedelta(minutes=30),
    )
    assert stable.trigger is None

    expired = adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW + timedelta(hours=2),
    )
    assert expired.trigger is not None
    assert expired.trigger.trigger_kind == ContinuityTriggerKind.POLICY_CHANGED
    assert "policy_effective_window" in expired.changed_fields


def test_mandate_registry_source_detects_revocation_and_missing_record():
    registry = DecisionGovernanceRegistry()
    active = mandate()
    registry.mandate_registry.seed(active)
    adapter = MandateRegistrySourceAdapter(
        binding=binding(),
        registry=registry,
        mandate_id="pay",
    )
    expected = adapter.fingerprint(observed_at=NOW)
    assert adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW,
    ).trigger is None

    registry.mandate_registry.records[("tenant-1", "pay")] = active.model_copy(
        update={"status": RegistryStatus.REVOKED}
    )
    revoked = adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW + timedelta(minutes=1),
    )
    assert revoked.trigger is not None
    assert revoked.trigger.trigger_kind == ContinuityTriggerKind.MANDATE_CHANGED
    assert "mandate_active_state" in revoked.changed_fields

    del registry.mandate_registry.records[("tenant-1", "pay")]
    missing = adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW + timedelta(minutes=2),
    )
    assert missing.trigger is not None
    assert "mandate_missing" in missing.changed_fields


def test_evidence_store_source_detects_expiry_and_required_item_loss(tmp_path):
    store = EvidenceStore(str(tmp_path / "evidence"))
    store.append(
        EvidenceItem(
            evidence_id="ev-1",
            receipt_id="receipt-1",
            tenant_id="tenant-1",
            evidence_type="verification",
            payload={"result": "pass"},
            created_at=NOW.isoformat(),
        )
    )
    store.append(
        EvidenceItem(
            evidence_id="ev-2",
            receipt_id="receipt-1",
            tenant_id="tenant-1",
            evidence_type="authority",
            payload={"result": "valid"},
            created_at=NOW.isoformat(),
        )
    )
    adapter = EvidenceStoreSourceAdapter(
        binding=binding(),
        store=store,
        receipt_id="receipt-1",
        required_evidence_ids=("ev-1", "ev-2"),
        max_age=timedelta(hours=1),
    )
    expected = adapter.fingerprint(observed_at=NOW)

    stable = adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW + timedelta(minutes=30),
    )
    assert stable.trigger is None

    expired = adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW + timedelta(hours=2),
    )
    assert expired.trigger is not None
    assert expired.trigger.trigger_kind == ContinuityTriggerKind.EVIDENCE_EXPIRED
    assert expired.trigger.freshness == 0.0

    first_row = store.find_by_receipt("tenant-1", "receipt-1")[0]
    store._path("tenant-1").write_text(
        json.dumps(first_row) + "\n",
        encoding="utf-8",
    )
    missing = adapter.observe(
        expected_fingerprint=expected,
        observed_at=NOW + timedelta(minutes=31),
    )
    assert missing.trigger is not None
    assert missing.trigger.trigger_kind == ContinuityTriggerKind.EVIDENCE_CHANGED
    assert "missing:ev-2" in missing.changed_fields


def test_target_state_ignores_read_time_but_detects_revision_drift():
    expected_state = target_state()
    adapter = TargetStateSourceAdapter(
        binding=binding(),
        expected_state=expected_state,
    )

    reread = target_state(observed_at=NOW + timedelta(minutes=5))
    assert adapter.observe(
        current_state=reread,
        observed_at=NOW + timedelta(minutes=5),
    ).trigger is None

    changed = target_state(
        revision_value="8",
        observed_at=NOW + timedelta(minutes=6),
        current_state_hash="sha256:invoice-v8",
        state_witness_ref="erp-witness:8",
    )
    observed = adapter.observe(
        current_state=changed,
        observed_at=NOW + timedelta(minutes=6),
    )
    assert observed.trigger is not None
    assert observed.trigger.trigger_kind == ContinuityTriggerKind.ASSET_STATE_CHANGED
    assert set(observed.changed_fields) == {
        "revision_value",
        "current_state_hash",
        "state_witness_ref",
    }


def test_source_bundle_is_deterministic_and_rejects_cross_case_trigger():
    policy_adapter = PublicationPolicySourceAdapter(binding=binding(), policy=policy())
    policy_expected = policy_adapter.fingerprint(observed_at=NOW)
    policy_observation = policy_adapter.observe(
        expected_fingerprint=policy_expected,
        observed_at=NOW,
    )
    state_observation = TargetStateSourceAdapter(
        binding=binding(),
        expected_state=target_state(),
    ).observe(
        current_state=target_state(
            revision_value="8",
            current_state_hash="sha256:invoice-v8",
            state_witness_ref="erp-witness:8",
        ),
        observed_at=NOW,
    )

    first = build_source_bundle(
        binding=binding(),
        observed_at=NOW,
        observations=(policy_observation, state_observation),
    )
    second = build_source_bundle(
        binding=binding(),
        observed_at=NOW,
        observations=(state_observation, policy_observation),
    )
    assert first.bundle_digest == second.bundle_digest
    assert len(first.triggers) == 1
    assert first.triggers[0].trigger_kind == ContinuityTriggerKind.ASSET_STATE_CHANGED

    foreign = TargetStateSourceAdapter(
        binding=binding(action_case_id="other-case"),
        expected_state=target_state(),
    ).observe(
        current_state=target_state(revision_value="9"),
        observed_at=NOW,
    )
    with pytest.raises((SourceObservationError, ValidationError), match="bundle binding"):
        build_source_bundle(
            binding=binding(),
            observed_at=NOW,
            observations=(foreign,),
        )
