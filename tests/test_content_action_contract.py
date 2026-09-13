from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.action_envelope.models import (
    ActionType,
    ConsequenceClass,
    PurposeRecordRef,
    Reversibility,
)
from src.valo_platform.content_operations import (
    ContentAction,
    ContentActionCase,
    ContentApprovalRequirement,
    ContentChangeReference,
    ContentEffect,
    ContentMateriality,
    ContentOperation,
    PublicationActionCase,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus


def sha(char: str) -> str:
    return "sha256:" + char * 64


def action_record(
    operation: ContentOperation = ContentOperation.UPDATE_FIELD,
    **updates: object,
) -> ActionCaseRecord:
    now = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "case_id": "case-content-1",
        "tenant_id": "tenant-1",
        "environment": "test",
        "record_version": 1,
        "case_hash": sha("1"),
        "decision_state": ActionCaseStatus.READY_FOR_REHT,
        "lifecycle_state": ActionCaseLifecycleState.READY,
        "purpose_record_ref": PurposeRecordRef(
            purpose_id="purpose-content",
            version="1",
            record_ref="purpose:tenant-1:content:1",
            fingerprint=sha("2"),
            established_by="human:editor",
            authority_ref="authority:board:1",
            evidence_refs=["evidence:source:1"],
        ),
        "purpose_binding_ref": "purpose-binding:content:1",
        "mandate_ref": "mandate:tenant-1:editor:1",
        "mandate_fingerprint": sha("3"),
        "policy_refs": ("policy:brand:1",),
        "policy_fingerprint": sha("9"),
        "evidence_refs": (
            "evidence:source:1",
            "evidence:semantic:1",
        ),
        "evidence_fingerprint": sha("4"),
        "state_refs": ("state:content:record-1:v1",),
        "state_fingerprint": sha("8"),
        "action_class": operation.action_type,
        "consequence_class": ConsequenceClass.C2_MEDIUM,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(updates)
    return ActionCaseRecord.model_validate(payload)


def content_action(
    operation: ContentOperation = ContentOperation.UPDATE_FIELD,
    **updates: object,
) -> ContentAction:
    mutation = operation.effect is ContentEffect.MUTATION
    payload: dict[str, object] = {
        "tenant_id": "tenant-1",
        "principal_id": "human:editor",
        "delegated_mandate_ref": "mandate:tenant-1:editor:1",
        "purpose_ref": "purpose:tenant-1:content:1",
        "operation": operation,
        "content_system": "synthetic-cms",
        "workspace_ref": "workspace:catalogue",
        "project_ref": "project:products",
        "dataset_ref": "dataset:production-shadow",
        "record_ids": ("record-1",),
        "content_type": "product",
        "schema_version": "schema-v1",
        "affected_fields": ("title",) if mutation else (),
        "locales": ("en",),
        "source_version_refs": ("version:record-1:v1",),
        "target_version_refs": ("version:record-1:v2",) if mutation else (),
        "proposed_change": (
            ContentChangeReference(
                change_ref="change:record-1:title:v2",
                digest=sha("5"),
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
        "policy_refs": ("policy:brand:1",),
        "semantic_evidence_refs": ("evidence:semantic:1",),
        "rights_evidence_refs": (),
        "materiality": ContentMateriality.MEDIUM,
        "affected_audiences": ("customers",),
        "reversibility": (
            Reversibility.REVERSIBLE if mutation else Reversibility.UNKNOWN
        ),
        "rollback_ref": "rollback:record-1:v1" if mutation else None,
        "approval_requirement": ContentApprovalRequirement.POLICY,
        "approver_roles": ("editor",),
        "confidence": 0.94,
        "uncertainty": 0.06,
        "expected_effect": "Update the product title in the shadow catalogue.",
        "idempotency_key": "content-change-1" if mutation else None,
        "content_snapshot_digest": sha("8"),
        "policy_snapshot_digest": sha("9"),
    }
    payload.update(updates)
    return ContentAction.model_validate(payload)


def content_case(
    operation: ContentOperation = ContentOperation.UPDATE_FIELD,
    *,
    content_updates: dict[str, object] | None = None,
    record_updates: dict[str, object] | None = None,
) -> ContentActionCase:
    return ContentActionCase(
        action_case=action_record(operation, **(record_updates or {})),
        content=content_action(operation, **(content_updates or {})),
    )


def test_taxonomy_is_complete_and_effect_separated() -> None:
    assert {operation.value for operation in ContentOperation} == {
        "content.query",
        "content.create_draft",
        "content.update_field",
        "content.bulk_update",
        "content.publish",
        "content.unpublish",
        "content.archive",
        "content.delete",
        "content.migrate",
        "content.localize",
        "content.attach_asset",
        "content.update_taxonomy",
        "content.update_schema",
    }
    assert ContentOperation.QUERY.effect is ContentEffect.OBSERVATION
    assert not ContentOperation.QUERY.requires_mutation_clearance
    assert all(
        operation.requires_mutation_clearance
        for operation in ContentOperation
        if operation is not ContentOperation.QUERY
    )


def test_taxonomy_reuses_canonical_action_types() -> None:
    assert ContentOperation.QUERY.action_type is ActionType.GENERATE_REPORT
    assert ContentOperation.PUBLISH.action_type is ActionType.EXTERNAL_PUBLICATION
    assert ContentOperation.DELETE.action_type is ActionType.DELETE_RESOURCE
    assert (
        ContentOperation.UPDATE_SCHEMA.action_type
        is ActionType.CONFIGURATION_CHANGE
    )
    assert ContentOperation.UPDATE_FIELD.action_type is ActionType.STATE_TRANSITION


def test_unknown_content_fields_fail_closed() -> None:
    payload = content_action().model_dump(mode="python")
    payload["raw_content"] = "must never be accepted"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ContentAction.model_validate(payload)


def test_mutation_requires_reference_idempotency_and_rollback() -> None:
    with pytest.raises(ValidationError, match="proposed change"):
        content_action(proposed_change=None)
    with pytest.raises(ValidationError, match="idempotency"):
        content_action(idempotency_key=None)
    with pytest.raises(ValidationError, match="rollback"):
        content_action(rollback_ref=None)


def test_observation_cannot_smuggle_mutation_fields() -> None:
    with pytest.raises(ValidationError, match="observation actions"):
        content_action(
            ContentOperation.QUERY,
            proposed_change=ContentChangeReference(
                change_ref="change:forbidden",
                digest=sha("5"),
            ),
        )
    with pytest.raises(ValidationError, match="idempotency"):
        content_action(ContentOperation.QUERY, idempotency_key="forbidden")


def test_batch_requires_identifier_and_consistent_size() -> None:
    with pytest.raises(ValidationError, match="batch_id"):
        content_action(batch_size=2)
    with pytest.raises(ValidationError, match="batch_size"):
        content_action(record_ids=("record-1", "record-2"), batch_size=1)


def test_content_case_binds_canonical_tenant_action_and_mandate() -> None:
    with pytest.raises(ValidationError, match="tenant"):
        content_case(content_updates={"tenant_id": "tenant-2"})
    with pytest.raises(ValidationError, match="ActionType"):
        content_case(record_updates={"action_class": ActionType.DELETE_RESOURCE})
    with pytest.raises(ValidationError, match="mandate"):
        content_case(
            content_updates={
                "delegated_mandate_ref": "mandate:tenant-1:other:1"
            }
        )


def test_content_case_binds_evidence_policy_and_state() -> None:
    with pytest.raises(ValidationError, match="evidence"):
        content_case(content_updates={"semantic_evidence_refs": ()})
    with pytest.raises(ValidationError, match="policy"):
        content_case(content_updates={"policy_refs": ("policy:other:1",)})
    with pytest.raises(ValidationError, match="policy snapshot"):
        content_case(content_updates={"policy_snapshot_digest": sha("7")})
    with pytest.raises(ValidationError, match="content snapshot"):
        content_case(content_updates={"content_snapshot_digest": sha("7")})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        (
            "proposed_change",
            ContentChangeReference(
                change_ref="change:record-1:title:v3",
                digest=sha("6"),
            ),
        ),
        ("locales", ("fr",)),
        ("target_version_refs", ("version:record-1:v3",)),
        ("policy_snapshot_digest", sha("7")),
        ("channels", ("mobile",)),
    ],
)
def test_material_changes_alter_deterministic_digest(
    field: str, value: object
) -> None:
    original = content_action()
    changed = original.model_copy(update={field: value})
    assert changed.digest() != original.digest()


def test_content_action_case_exposes_exact_bindings() -> None:
    case = content_case()
    assert not case.is_observation
    assert case.requires_mutation_clearance
    assert case.digest().startswith("sha256:")
    assert case.target_digest() == case.content.target_digest()
    assert case.state_binding_digest() == case.content.state_binding_digest()


def test_contract_contains_references_and_hashes_not_raw_content() -> None:
    payload = content_case().canonical_payload()
    content = payload["content"]
    assert "raw_content" not in content
    assert "secret" not in content
    assert set(content["proposed_change"]) == {
        "change_ref",
        "digest",
        "media_type",
    }


def test_publication_contract_remains_available() -> None:
    assert PublicationActionCase.__name__ == "PublicationActionCase"
