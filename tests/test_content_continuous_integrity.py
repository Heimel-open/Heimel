from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ConsequenceClass,
    PurposeRecordRef,
    Reversibility,
)
from src.valo_platform.continuous_integrity import (
    IntegrityDecision,
    IntegrityProfile,
    IntegrityTrigger,
    verify_checkpoint_chain,
)
from src.valo_platform.content_operations import (
    ContentAction,
    ContentActionCase,
    ContentApprovalRequirement,
    ContentChangeReference,
    ContentContinuousIntegrityAdapter,
    ContentIntegrityError,
    ContentMateriality,
    ContentOperation,
    ContentPolicyProfile,
    default_content_integrity_profile,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus


def sha(char: str) -> str:
    return "sha256:" + char * 64


def make_policy(now: datetime, **updates: object) -> ContentPolicyProfile:
    payload: dict[str, object] = {
        "policy_id": "policy-content-integrity-1",
        "version": "1",
        "tenant_id": "tenant-1",
        "established_by": "human:content-owner",
        "authority_ref": "authority:content-board:1",
        "authority_fingerprint": sha("a"),
        "mandate_ref": "mandate:tenant-1:content:1",
        "mandate_fingerprint": sha("3"),
        "allowed_principal_ids": ("agent:content-editor",),
        "allowed_content_systems": ("synthetic-cms",),
        "allowed_workspace_refs": ("workspace:catalogue", "workspace:other"),
        "allowed_project_refs": ("project:products",),
        "allowed_dataset_refs": ("dataset:shadow",),
        "allowed_operations": tuple(ContentOperation),
        "allowed_markets": ("NO",),
        "allowed_languages": ("en",),
        "allowed_jurisdictions": ("NO",),
        "allowed_channels": ("web",),
        "auto_clear_operations": (ContentOperation.UPDATE_FIELD,),
        "step_up_operations": tuple(
            operation
            for operation in ContentOperation
            if operation not in {ContentOperation.QUERY, ContentOperation.UPDATE_FIELD}
        ),
        "max_auto_materiality": ContentMateriality.LOW,
        "max_uncertainty": 0.10,
        "max_batch_size": 1,
        "max_audience_count": 1,
        "max_unique_markets": 1,
        "max_unique_locales": 1,
        "max_cumulative_materiality_score": 2,
        "required_approver_roles": ("content_owner",),
        "effective_from": now - timedelta(hours=1),
        "effective_until": now + timedelta(days=1),
    }
    payload.update(updates)
    return ContentPolicyProfile.model_validate(payload)


def make_case(
    profile: ContentPolicyProfile,
    operation: ContentOperation = ContentOperation.UPDATE_FIELD,
    *,
    case_id: str = "case-content-integrity-1",
    content_updates: dict[str, object] | None = None,
    record_updates: dict[str, object] | None = None,
) -> ContentActionCase:
    mutation = operation is not ContentOperation.QUERY
    content_payload: dict[str, object] = {
        "tenant_id": "tenant-1",
        "principal_id": "agent:content-editor",
        "delegated_mandate_ref": "mandate:tenant-1:content:1",
        "purpose_ref": "purpose:tenant-1:content:1",
        "operation": operation,
        "content_system": "synthetic-cms",
        "workspace_ref": "workspace:catalogue",
        "project_ref": "project:products",
        "dataset_ref": "dataset:shadow",
        "record_ids": ("record-1",),
        "content_type": "product",
        "schema_version": "schema-v1",
        "affected_fields": ("title",) if mutation else (),
        "locales": ("en",),
        "source_version_refs": ("version:record-1:v1",),
        "target_version_refs": ("version:record-1:v2",) if mutation else (),
        "proposed_change": (
            ContentChangeReference(
                change_ref="change:record-1:v2",
                digest=sha("6"),
                media_type="application/json-patch+json",
            )
            if mutation
            else None
        ),
        "batch_size": 1,
        "market": "NO",
        "language": "en",
        "jurisdictions": ("NO",),
        "channels": ("web",),
        "provenance_refs": ("evidence:source:1",),
        "policy_refs": ("policy:content:1",),
        "semantic_evidence_refs": ("evidence:semantic:1",),
        "rights_evidence_refs": ("evidence:rights:1",),
        "materiality": ContentMateriality.LOW,
        "affected_audiences": ("customers",),
        "reversibility": Reversibility.REVERSIBLE if mutation else Reversibility.UNKNOWN,
        "rollback_ref": "rollback:record-1:v1" if mutation else None,
        "approval_requirement": ContentApprovalRequirement.POLICY,
        "approver_roles": ("content_owner",),
        "confidence": 0.95,
        "uncertainty": 0.05,
        "expected_effect": "Update synthetic catalogue metadata.",
        "idempotency_key": "change-record-1-v2" if mutation else None,
        "content_snapshot_digest": sha("8"),
        "policy_snapshot_digest": profile.digest(),
    }
    content_payload.update(content_updates or {})
    content = ContentAction.model_validate(content_payload)

    created_at = datetime(2026, 7, 31, 18, 0, tzinfo=timezone.utc)
    record_payload: dict[str, object] = {
        "case_id": case_id,
        "tenant_id": content.tenant_id,
        "environment": "test",
        "record_version": 1,
        "case_hash": sha("1"),
        "decision_state": ActionCaseStatus.READY_FOR_REHT,
        "lifecycle_state": ActionCaseLifecycleState.READY,
        "purpose_record_ref": PurposeRecordRef(
            purpose_id="purpose-content",
            version="1",
            record_ref=content.purpose_ref,
            fingerprint=sha("2"),
            established_by="human:content-owner",
            authority_ref=profile.authority_ref,
            evidence_refs=["evidence:source:1"],
        ),
        "purpose_binding_ref": "purpose-binding:content:1",
        "mandate_ref": content.delegated_mandate_ref,
        "mandate_fingerprint": sha("3"),
        "delegation_ref": "delegation:tenant-1:content:1",
        "delegation_fingerprint": sha("4"),
        "policy_refs": content.policy_refs,
        "policy_fingerprint": content.policy_snapshot_digest,
        "evidence_refs": (
            "evidence:source:1",
            "evidence:semantic:1",
            "evidence:rights:1",
        ),
        "evidence_fingerprint": sha("5"),
        "context_refs": ("context:market:NO",),
        "context_fingerprint": sha("7"),
        "state_refs": ("state:record-1:v1",),
        "state_fingerprint": content.content_snapshot_digest,
        "action_class": operation.action_type,
        "consequence_class": ConsequenceClass.C2_MEDIUM,
        "created_at": created_at,
        "updated_at": created_at,
    }
    record_payload.update(record_updates or {})
    record = ActionCaseRecord.model_validate(record_payload)
    return ContentActionCase(action_case=record, content=content)


def capture(
    adapter: ContentContinuousIntegrityAdapter,
    case: ContentActionCase,
    profile: ContentPolicyProfile,
    integrity: IntegrityProfile,
    now: datetime,
):
    return adapter.capture_baseline(
        baseline_id="baseline-content-1",
        action_case=case,
        policy=profile,
        clearance_digest=sha("c"),
        profile=integrity,
        captured_at=now,
    )


def test_capture_requires_mutation_and_external_clearance_digest() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile()
    mutation = make_case(policy)

    baseline = capture(adapter, mutation, policy, integrity, now)

    assert baseline.integrity_baseline.clearance_digest == sha("c")
    assert baseline.integrity_baseline.action_ref == mutation.digest()
    assert baseline.binding_snapshot.action_payload_digest == mutation.digest()
    assert baseline.grants_authority is False
    assert baseline.grants_clearance is False
    assert baseline.production_writes == 0

    with pytest.raises(ContentIntegrityError, match="observation action"):
        adapter.capture_baseline(
            baseline_id="baseline-query",
            action_case=make_case(policy, ContentOperation.QUERY),
            policy=policy,
            clearance_digest=sha("c"),
            profile=integrity,
            captured_at=now,
        )

    with pytest.raises(ContentIntegrityError, match="clearance_digest"):
        adapter.capture_baseline(
            baseline_id="baseline-bad-clearance",
            action_case=mutation,
            policy=policy,
            clearance_digest="clearance:raw-token",
            profile=integrity,
            captured_at=now,
        )


def test_unchanged_content_state_continues() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    case = make_case(policy)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile()
    baseline = capture(adapter, case, policy, integrity, now)

    result = adapter.checkpoint(
        receipt_id="checkpoint-1",
        baseline=baseline,
        action_case=case,
        policy=policy,
        profile=integrity,
        trigger=IntegrityTrigger.CHECKPOINT,
        observed_at=now + timedelta(seconds=1),
    )

    assert result.invalidation_evidence.valid is True
    assert result.checkpoint_receipt.decision is IntegrityDecision.CONTINUE
    assert result.checkpoint_receipt.revalidation_required is False
    assert result.production_writes == 0


@pytest.mark.parametrize(
    "change",
    [
        "policy",
        "authority",
        "mandate",
        "delegation",
        "context",
        "target",
        "snapshot",
        "schema",
        "source_version",
    ],
)
def test_authoritative_binding_changes_require_reevaluation(change: str) -> None:
    now = datetime.now(timezone.utc)
    original_policy = make_policy(now)
    original_case = make_case(original_policy)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile()
    baseline = capture(adapter, original_case, original_policy, integrity, now)

    current_policy = original_policy
    current_case = original_case
    if change == "policy":
        current_policy = make_policy(now, version="2", max_uncertainty=0.08)
    elif change == "authority":
        current_policy = make_policy(now, authority_fingerprint=sha("b"))
    elif change == "mandate":
        current_case = make_case(
            original_policy,
            record_updates={"mandate_fingerprint": sha("b")},
        )
    elif change == "delegation":
        current_case = make_case(
            original_policy,
            record_updates={"delegation_fingerprint": sha("b")},
        )
    elif change == "context":
        current_case = make_case(
            original_policy,
            record_updates={"context_fingerprint": sha("b")},
        )
    elif change == "target":
        current_case = make_case(
            original_policy,
            content_updates={"workspace_ref": "workspace:other"},
        )
    elif change == "snapshot":
        current_case = make_case(
            original_policy,
            content_updates={"content_snapshot_digest": sha("9")},
            record_updates={"state_fingerprint": sha("9")},
        )
    elif change == "schema":
        current_case = make_case(
            original_policy,
            content_updates={"schema_version": "schema-v2"},
        )
    elif change == "source_version":
        current_case = make_case(
            original_policy,
            content_updates={"source_version_refs": ("version:record-1:v2",)},
        )

    result = adapter.checkpoint(
        receipt_id=f"checkpoint-{change}",
        baseline=baseline,
        action_case=current_case,
        policy=current_policy,
        profile=integrity,
        trigger=IntegrityTrigger.EXTERNAL_CHANGE,
        observed_at=now + timedelta(seconds=1),
    )

    assert result.invalidation_evidence.valid is False
    assert result.checkpoint_receipt.decision is IntegrityDecision.REEVALUATE
    assert result.checkpoint_receipt.revalidation_required is True


def test_expired_baseline_requires_reevaluation() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    case = make_case(policy)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile(baseline_validity_seconds=1)
    baseline = capture(adapter, case, policy, integrity, now)

    result = adapter.checkpoint(
        receipt_id="checkpoint-expired",
        baseline=baseline,
        action_case=case,
        policy=policy,
        profile=integrity,
        trigger=IntegrityTrigger.TIMEOUT,
        observed_at=now + timedelta(seconds=2),
    )

    assert result.invalidation_evidence.valid is True
    assert result.checkpoint_receipt.decision is IntegrityDecision.REEVALUATE


def test_critical_validity_failure_halts() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    case = make_case(policy)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile()
    baseline = capture(adapter, case, policy, integrity, now)

    result = adapter.checkpoint(
        receipt_id="checkpoint-halt",
        baseline=baseline,
        action_case=case,
        policy=policy,
        profile=integrity,
        trigger=IntegrityTrigger.AUTHORITY_CHANGE,
        observed_at=now + timedelta(seconds=1),
        critical_validity={"authority": False},
    )

    assert result.checkpoint_receipt.decision is IntegrityDecision.HALT
    assert result.checkpoint_receipt.failed_invariants == ("authority",)


def test_checkpoint_chain_uses_canonical_integrity_receipts() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    case = make_case(policy)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile()
    baseline = capture(adapter, case, policy, integrity, now)

    first = adapter.checkpoint(
        receipt_id="checkpoint-chain-1",
        baseline=baseline,
        action_case=case,
        policy=policy,
        profile=integrity,
        trigger=IntegrityTrigger.CHECKPOINT,
        observed_at=now + timedelta(seconds=1),
    )
    second = adapter.checkpoint(
        receipt_id="checkpoint-chain-2",
        baseline=baseline,
        action_case=case,
        policy=policy,
        profile=integrity,
        trigger=IntegrityTrigger.CHECKPOINT,
        previous_checkpoint_digest=first.checkpoint_receipt.digest(),
        observed_at=now + timedelta(seconds=2),
    )

    assert verify_checkpoint_chain(
        (first.checkpoint_receipt, second.checkpoint_receipt)
    )


def test_cross_case_cross_tenant_and_profile_reuse_fail_closed() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    case = make_case(policy)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile()
    baseline = capture(adapter, case, policy, integrity, now)

    other_case = case.model_copy(
        update={
            "action_case": case.action_case.model_copy(update={"case_id": "case-other"})
        }
    )
    with pytest.raises(ContentIntegrityError, match="cross-case"):
        adapter.checkpoint(
            receipt_id="checkpoint-cross-case",
            baseline=baseline,
            action_case=other_case,
            policy=policy,
            profile=integrity,
            trigger=IntegrityTrigger.CHECKPOINT,
            observed_at=now + timedelta(seconds=1),
        )

    other_tenant = case.model_copy(
        update={
            "action_case": case.action_case.model_copy(update={"tenant_id": "tenant-2"}),
            "content": case.content.model_copy(update={"tenant_id": "tenant-2"}),
        }
    )
    other_tenant_policy = policy.model_copy(update={"tenant_id": "tenant-2"})
    with pytest.raises(ContentIntegrityError, match="cross-tenant"):
        adapter.checkpoint(
            receipt_id="checkpoint-cross-tenant",
            baseline=baseline,
            action_case=other_tenant,
            policy=other_tenant_policy,
            profile=integrity,
            trigger=IntegrityTrigger.CHECKPOINT,
            observed_at=now + timedelta(seconds=1),
        )

    with pytest.raises(ContentIntegrityError, match="profile"):
        adapter.checkpoint(
            receipt_id="checkpoint-profile",
            baseline=baseline,
            action_case=case,
            policy=policy,
            profile=default_content_integrity_profile(profile_id="other-profile"),
            trigger=IntegrityTrigger.CHECKPOINT,
            observed_at=now + timedelta(seconds=1),
        )


def test_profile_that_allows_invalid_binding_to_continue_is_rejected() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    case = make_case(policy)
    adapter = ContentContinuousIntegrityAdapter()
    permissive = IntegrityProfile(
        profile_id="permissive-content-profile",
        weights={
            "authority": 1.0,
            "policy": 1.0,
            "objective": 1.0,
            "context": 1.0,
            "evidence": 1.0,
            "tools": 1.0,
            "model_harness": 1.0,
            "environment": 1.0,
            "risk": 1.0,
        },
        material_drift_threshold=1.0,
        baseline_validity_seconds=300,
    )
    baseline = capture(adapter, case, policy, permissive, now)
    changed_policy = make_policy(now, version="2")

    with pytest.raises(ContentIntegrityError, match="invalid content binding"):
        adapter.checkpoint(
            receipt_id="checkpoint-permissive",
            baseline=baseline,
            action_case=case,
            policy=changed_policy,
            profile=permissive,
            trigger=IntegrityTrigger.EXTERNAL_CHANGE,
            observed_at=now + timedelta(seconds=1),
        )


def test_adapter_and_results_expose_no_execution_or_authority_surface() -> None:
    now = datetime.now(timezone.utc)
    policy = make_policy(now)
    case = make_case(policy)
    adapter = ContentContinuousIntegrityAdapter()
    integrity = default_content_integrity_profile()
    baseline = capture(adapter, case, policy, integrity, now)
    result = adapter.checkpoint(
        receipt_id="checkpoint-surface",
        baseline=baseline,
        action_case=case,
        policy=policy,
        profile=integrity,
        trigger=IntegrityTrigger.CHECKPOINT,
        observed_at=now + timedelta(seconds=1),
    )

    forbidden = {
        "execute",
        "mutate",
        "publish",
        "issue_clearance",
        "create_commit_token",
        "authorize",
    }
    assert forbidden.isdisjoint(set(dir(adapter)))
    serialized = result.model_dump_json()
    assert "proposed_change" not in serialized
    assert "credential" not in serialized
    assert result.grants_authority is False
    assert result.grants_clearance is False
    assert result.checkpoint_receipt.grants_authority is False
    assert result.checkpoint_receipt.grants_clearance is False
