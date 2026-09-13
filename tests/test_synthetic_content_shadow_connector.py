from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ConsequenceClass,
    PurposeRecordRef,
    Reversibility,
)
from src.valo_platform.connectors.content import (
    ContentShadowConflict,
    SyntheticContentRecord,
    SyntheticContentShadowConnector,
    SyntheticContentWorkspace,
    SyntheticContentWorkspaceTransport,
)
from src.valo_platform.content_operations import (
    ContentAction,
    ContentActionCase,
    ContentApprovalRequirement,
    ContentChangeReference,
    ContentEffect,
    ContentMateriality,
    ContentOperation,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus


def sha(char: str) -> str:
    return "sha256:" + char * 64


def workspace() -> SyntheticContentWorkspace:
    return SyntheticContentWorkspace(
        tenant_id="tenant-1",
        content_system="synthetic-cms",
        workspace_ref="workspace:catalogue",
        project_ref="project:products",
        dataset_ref="dataset:production-shadow",
        schema_version="schema-v1",
        schema_digest=sha("9"),
        records=(
            SyntheticContentRecord(
                record_id="record-1",
                version_ref="version:record-1:v1",
                snapshot_digest=sha("a"),
                schema_version="schema-v1",
                field_names=("title", "description"),
                locales=("en",),
                metadata_refs=("metadata:record-1:v1",),
            ),
            SyntheticContentRecord(
                record_id="record-2",
                version_ref="version:record-2:v4",
                snapshot_digest=sha("b"),
                schema_version="schema-v1",
                field_names=("title", "price"),
                locales=("en", "no"),
                metadata_refs=("metadata:record-2:v4",),
            ),
        ),
    )


def action_case(
    operation: ContentOperation,
    ws: SyntheticContentWorkspace,
    **updates: object,
) -> ContentActionCase:
    mutation = operation.effect is ContentEffect.MUTATION
    record_ids = tuple(updates.pop("record_ids", ("record-1",)))
    source_versions = tuple(
        updates.pop("source_version_refs", ("version:record-1:v1",))
    )
    snapshot_digest = str(
        updates.pop("content_snapshot_digest", ws.snapshot_digest(record_ids))
    )

    content_payload: dict[str, object] = {
        "tenant_id": "tenant-1",
        "principal_id": "agent:catalogue-editor",
        "delegated_mandate_ref": "mandate:tenant-1:catalogue:1",
        "purpose_ref": "purpose:tenant-1:catalogue:1",
        "operation": operation,
        "content_system": "synthetic-cms",
        "workspace_ref": "workspace:catalogue",
        "project_ref": "project:products",
        "dataset_ref": "dataset:production-shadow",
        "record_ids": record_ids,
        "content_type": "product",
        "schema_version": "schema-v1",
        "affected_fields": ("title",) if mutation else (),
        "locales": ("en",),
        "source_version_refs": source_versions,
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
        "batch_size": len(record_ids),
        "batch_id": "batch:catalogue:1" if len(record_ids) > 1 else None,
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
        "confidence": 0.92,
        "uncertainty": 0.08,
        "expected_effect": "Observe or simulate the proposed catalogue change.",
        "idempotency_key": "content-change-1" if mutation else None,
        "content_snapshot_digest": snapshot_digest,
        "policy_snapshot_digest": ws.schema_digest,
    }
    content_payload.update(updates)
    content = ContentAction.model_validate(content_payload)

    now = datetime.now(timezone.utc)
    record = ActionCaseRecord(
        case_id="case-shadow-1",
        tenant_id=content.tenant_id,
        environment="test",
        record_version=1,
        case_hash=sha("1"),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.READY,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-catalogue",
            version="1",
            record_ref=content.purpose_ref,
            fingerprint=sha("2"),
            established_by="human:content-owner",
            authority_ref="authority:content-board:1",
            evidence_refs=["evidence:source:1"],
        ),
        purpose_binding_ref="purpose-binding:catalogue:1",
        mandate_ref=content.delegated_mandate_ref,
        mandate_fingerprint=sha("3"),
        policy_refs=content.policy_refs,
        policy_fingerprint=content.policy_snapshot_digest,
        evidence_refs=("evidence:source:1", "evidence:semantic:1"),
        evidence_fingerprint=sha("4"),
        state_refs=("state:catalogue:current",),
        state_fingerprint=content.content_snapshot_digest,
        action_class=operation.action_type,
        consequence_class=ConsequenceClass.C2_MEDIUM,
        created_at=now,
        updated_at=now,
    )
    return ContentActionCase(action_case=record, content=content)


def connector(
    ws: SyntheticContentWorkspace,
) -> tuple[SyntheticContentShadowConnector, SyntheticContentWorkspaceTransport]:
    transport = SyntheticContentWorkspaceTransport(ws)
    return SyntheticContentShadowConnector(transport), transport


def test_observation_requires_no_clearance_or_token() -> None:
    ws = workspace()
    shadow, transport = connector(ws)
    case = action_case(ContentOperation.QUERY, ws)

    evidence = shadow.observe_current_state(case)

    assert case.is_observation
    assert not case.requires_mutation_clearance
    assert evidence.outcome == "state_observed"
    assert not evidence.would_mutate
    assert not evidence.dry_run
    assert transport.calls == ["observe_current_state"]


def test_dry_run_simulates_without_changing_workspace() -> None:
    ws = workspace()
    shadow, transport = connector(ws)
    case = action_case(ContentOperation.UPDATE_FIELD, ws)
    before = ws.model_dump(mode="json")

    evidence = shadow.dry_run(case)

    assert evidence.outcome == "mutation_would_apply"
    assert evidence.would_mutate
    assert evidence.dry_run
    assert transport.calls == ["simulate"]
    assert ws.model_dump(mode="json") == before


def test_shadow_connector_has_no_production_mutation_surface() -> None:
    shadow, transport = connector(workspace())
    for name in ("execute", "publish", "mutate", "update", "delete", "commit"):
        assert not hasattr(shadow, name)
        assert not hasattr(transport, name)


def test_schema_metadata_and_preview_are_reference_only() -> None:
    ws = workspace()
    shadow, transport = connector(ws)
    case = action_case(ContentOperation.UPDATE_FIELD, ws)

    schema = shadow.inspect_schema(case)
    metadata = shadow.fetch_metadata(case)
    preview = shadow.preview(case)

    assert schema.schema_digest == ws.schema_digest
    assert metadata.result_refs == ("metadata:record-1:v1",)
    assert preview.outcome == "proposal_previewed"
    assert not preview.would_mutate
    assert transport.calls == ["inspect_schema", "fetch_metadata", "preview"]


def test_stale_version_fails_closed() -> None:
    ws = workspace()
    shadow, transport = connector(ws)
    case = action_case(
        ContentOperation.UPDATE_FIELD,
        ws,
        source_version_refs=("version:record-1:v0",),
    )

    with pytest.raises(ContentShadowConflict, match="version"):
        shadow.dry_run(case)
    assert transport.calls == ["simulate"]


def test_stale_snapshot_fails_closed() -> None:
    ws = workspace()
    shadow, _ = connector(ws)
    case = action_case(
        ContentOperation.UPDATE_FIELD,
        ws,
        content_snapshot_digest=sha("8"),
    )

    with pytest.raises(ContentShadowConflict, match="snapshot"):
        shadow.dry_run(case)


def test_wrong_scope_fails_closed() -> None:
    ws = workspace()
    shadow, _ = connector(ws)
    case = action_case(
        ContentOperation.QUERY,
        ws,
        workspace_ref="workspace:other",
    )

    with pytest.raises(ContentShadowConflict, match="scope"):
        shadow.observe_current_state(case)


def test_evidence_binds_exact_action_target_state_and_observation() -> None:
    ws = workspace()
    shadow, _ = connector(ws)
    case = action_case(ContentOperation.UPDATE_FIELD, ws)

    first = shadow.dry_run(case)
    second = shadow.dry_run(case)

    assert first.payload_digest == case.digest()
    assert first.target_digest == case.target_digest()
    assert first.state_binding_digest == case.state_binding_digest()
    assert first.observed_snapshot_digest == ws.snapshot_digest(("record-1",))
    assert first.record_version_refs == ("version:record-1:v1",)
    assert first.digest() == second.digest()


def test_shadow_evidence_never_contains_raw_content_or_secrets() -> None:
    ws = workspace()
    shadow, _ = connector(ws)
    evidence = shadow.dry_run(action_case(ContentOperation.UPDATE_FIELD, ws))
    payload = evidence.model_dump(mode="json")

    assert "raw_content" not in payload
    assert "secret" not in payload
    assert "proposed_change" not in payload
    assert set(payload) == {
        "action_id",
        "operation",
        "payload_digest",
        "target_digest",
        "state_binding_digest",
        "observed_snapshot_digest",
        "schema_digest",
        "record_version_refs",
        "outcome",
        "result_refs",
        "would_mutate",
        "dry_run",
    }
