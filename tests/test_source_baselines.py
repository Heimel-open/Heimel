from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.evidence_store.store import EvidenceItem, EvidenceStore
from src.valo_platform.action_envelope.models import ActionType, ConsequenceClass
from src.valo_platform.action_envelope.transition_models import RevisionType, TargetStateBinding
from src.valo_platform.content_operations.policy_profile import PublicationPolicyProfile
from src.valo_platform.decision_governance.models import MandateRecord, RegistryStatus
from src.valo_platform.decision_governance.registries import DecisionGovernanceRegistry
from src.valo_platform.operational_continuity.observers import ObservationBinding
from src.valo_platform.operational_continuity.source_adapters import (
    ContinuitySourceDomain,
    EvidenceStoreSourceAdapter,
    MandateRegistrySourceAdapter,
    PublicationPolicySourceAdapter,
    SourceObservationError,
    TargetStateSourceAdapter,
)
from src.valo_platform.operational_continuity.source_baselines import (
    build_source_baseline,
    capture_evidence_baseline,
    capture_mandate_baseline,
    capture_policy_baseline,
    capture_target_state_baseline,
)


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
SHA = "sha256:" + "2" * 64


def binding() -> ObservationBinding:
    return ObservationBinding(
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash="sha256:case-1",
        clearance_ref="clearance-1",
        observer_ref="observer:source-baseline",
    )


def policy(*, effective_until=NOW + timedelta(hours=1)) -> PublicationPolicyProfile:
    return PublicationPolicyProfile(
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
        effective_until=effective_until,
    )


def mandate(*, status=RegistryStatus.ACTIVE) -> MandateRecord:
    return MandateRecord(
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
        status=status,
        effective_from=NOW - timedelta(days=1),
        effective_until=NOW + timedelta(days=1),
    ).finalized()


def target(*, observed_at=NOW) -> TargetStateBinding:
    return TargetStateBinding(
        system_id="erp",
        object_id="invoice-1",
        revision_type=RevisionType.VERSION,
        revision_value="7",
        observed_at=observed_at,
        current_state_hash="sha256:invoice-v7",
        state_witness_ref="erp-witness:7",
    )


def evidence_adapter(tmp_path, *, created_at=NOW, required=("ev-1",)):
    store = EvidenceStore(str(tmp_path / "evidence"))
    store.append(
        EvidenceItem(
            evidence_id="ev-1",
            receipt_id="receipt-1",
            tenant_id="tenant-1",
            evidence_type="verification",
            payload={"result": "pass"},
            created_at=created_at.isoformat(),
        )
    )
    return EvidenceStoreSourceAdapter(
        binding=binding(),
        store=store,
        receipt_id="receipt-1",
        required_evidence_ids=required,
        max_age=timedelta(hours=1),
    )


def test_valid_source_baseline_is_deterministic_and_queryable(tmp_path):
    registry = DecisionGovernanceRegistry()
    registry.mandate_registry.seed(mandate())
    policy_adapter = PublicationPolicySourceAdapter(binding=binding(), policy=policy())
    mandate_adapter = MandateRegistrySourceAdapter(
        binding=binding(), registry=registry, mandate_id="pay"
    )
    evidence = evidence_adapter(tmp_path)
    target_adapter = TargetStateSourceAdapter(
        binding=binding(), expected_state=target()
    )
    entries = (
        capture_policy_baseline(policy_adapter, captured_at=NOW),
        capture_mandate_baseline(mandate_adapter, captured_at=NOW),
        capture_evidence_baseline(evidence, captured_at=NOW),
        capture_target_state_baseline(target_adapter, captured_at=NOW),
    )
    first = build_source_baseline(
        binding=binding(), captured_at=NOW, entries=entries
    )
    second = build_source_baseline(
        binding=binding(), captured_at=NOW, entries=tuple(reversed(entries))
    )
    assert first.baseline_digest == second.baseline_digest
    assert first.fingerprint_for(
        ContinuitySourceDomain.POLICY, policy_adapter.source_ref
    ) == policy_adapter.fingerprint(observed_at=NOW)


def test_inactive_policy_and_mandate_cannot_be_frozen():
    with pytest.raises(SourceObservationError, match="inactive policy"):
        capture_policy_baseline(
            PublicationPolicySourceAdapter(
                binding=binding(),
                policy=policy(effective_until=NOW),
            ),
            captured_at=NOW,
        )

    registry = DecisionGovernanceRegistry()
    registry.mandate_registry.seed(mandate(status=RegistryStatus.REVOKED))
    with pytest.raises(SourceObservationError, match="inactive mandate"):
        capture_mandate_baseline(
            MandateRegistrySourceAdapter(
                binding=binding(), registry=registry, mandate_id="pay"
            ),
            captured_at=NOW,
        )


def test_missing_or_expired_evidence_cannot_be_frozen(tmp_path):
    missing = evidence_adapter(tmp_path / "missing", required=("ev-1", "ev-2"))
    with pytest.raises(SourceObservationError, match="missing required evidence"):
        capture_evidence_baseline(missing, captured_at=NOW)

    expired = evidence_adapter(
        tmp_path / "expired",
        created_at=NOW - timedelta(hours=2),
    )
    with pytest.raises(SourceObservationError, match="expired evidence"):
        capture_evidence_baseline(expired, captured_at=NOW)


def test_future_target_observation_cannot_be_frozen():
    adapter = TargetStateSourceAdapter(
        binding=binding(),
        expected_state=target(observed_at=NOW + timedelta(seconds=1)),
    )
    with pytest.raises(SourceObservationError, match="future"):
        capture_target_state_baseline(adapter, captured_at=NOW)
