from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.valo_platform.connectors.content import (
    ContentShadowConflict,
    SanityShadowConnector,
)
from src.valo_platform.content_operations import (
    ContentActionCase,
    ContentOperation,
    ContentRiskEvidence,
    ContentShadowWorkflowRunner,
)
from src.valo_platform.content_operations.demo import (
    _content_case,
    _policy,
    _sanity_fixture,
)


def test_sanity_adapter_binds_schema_ids_revisions_and_snapshot() -> None:
    at = datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    schema, transport = _sanity_fixture()
    profile = _policy(at)
    case = _content_case(
        policy=profile,
        transport=transport,
        operation=ContentOperation.UPDATE_FIELD,
        case_id="case-sanity-bindings",
        document_id="product-1",
        affected_fields=("seo.title",),
    )
    connector = SanityShadowConnector(transport)

    schema_evidence = connector.inspect_schema(case)
    metadata_evidence = connector.fetch_metadata(case)
    state_evidence = connector.observe_current_state(case)
    preview_evidence = connector.preview(case)
    simulation_evidence = connector.dry_run(case)

    assert schema_evidence.schema_digest == schema.schema_digest
    assert metadata_evidence.result_refs == ("sanity:product-1:metadata",)
    assert state_evidence.record_version_refs == ("rev-product-1-v1",)
    assert state_evidence.observed_snapshot_digest == transport.snapshot_digest(
        ("product-1",)
    )
    assert preview_evidence.dry_run
    assert not preview_evidence.would_mutate
    assert simulation_evidence.dry_run
    assert simulation_evidence.would_mutate
    assert simulation_evidence.payload_digest == case.digest()
    assert simulation_evidence.target_digest == case.target_digest()
    assert simulation_evidence.state_binding_digest == case.state_binding_digest()
    assert transport.calls == [
        "inspect_schema",
        "fetch_metadata",
        "observe_current_state",
        "preview_patch",
        "simulate_patch",
    ]


def test_stale_sanity_revision_fails_closed() -> None:
    at = datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    _, transport = _sanity_fixture()
    profile = _policy(at)
    case = _content_case(
        policy=profile,
        transport=transport,
        operation=ContentOperation.UPDATE_FIELD,
        case_id="case-sanity-stale-rev",
        document_id="product-1",
        affected_fields=("description",),
        source_revision="rev-product-1-old",
    )

    with pytest.raises(ContentShadowConflict, match="_rev"):
        SanityShadowConnector(transport).observe_current_state(case)


def test_stale_schema_and_wrong_scope_fail_closed() -> None:
    at = datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    _, transport = _sanity_fixture()
    profile = _policy(at)
    original = _content_case(
        policy=profile,
        transport=transport,
        operation=ContentOperation.UPDATE_FIELD,
        case_id="case-sanity-scope",
        document_id="product-1",
        affected_fields=("description",),
    )
    connector = SanityShadowConnector(transport)

    stale_content = original.content.model_copy(update={"schema_version": "schema-old"})
    stale_schema = ContentActionCase(
        action_case=original.action_case,
        content=stale_content,
    )
    with pytest.raises(ContentShadowConflict, match="schema"):
        connector.observe_current_state(stale_schema)

    wrong_project_content = original.content.model_copy(
        update={"project_ref": "sanity-project:other"}
    )
    wrong_project = ContentActionCase(
        action_case=original.action_case,
        content=wrong_project_content,
    )
    with pytest.raises(ContentShadowConflict, match="project"):
        connector.observe_current_state(wrong_project)

    wrong_dataset_content = original.content.model_copy(
        update={"dataset_ref": "sanity-dataset:other"}
    )
    wrong_dataset = ContentActionCase(
        action_case=original.action_case,
        content=wrong_dataset_content,
    )
    with pytest.raises(ContentShadowConflict, match="dataset"):
        connector.observe_current_state(wrong_dataset)


def test_sanity_fixture_and_connector_have_no_mutation_or_credential_surface() -> None:
    _, transport = _sanity_fixture()
    connector = SanityShadowConnector(transport)

    for obj in (transport, connector):
        for name in (
            "execute",
            "mutate",
            "commit",
            "patch",
            "publish",
            "delete",
            "rollback",
            "token",
            "credentials",
            "api_key",
        ):
            assert not hasattr(obj, name)


def test_sanity_adapter_runs_through_existing_shadow_workflow() -> None:
    at = datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    _, transport = _sanity_fixture()
    profile = _policy(at)
    case = _content_case(
        policy=profile,
        transport=transport,
        operation=ContentOperation.UPDATE_FIELD,
        case_id="case-sanity-workflow",
        document_id="product-1",
        affected_fields=("seo.title",),
    )
    result = ContentShadowWorkflowRunner(
        connector=SanityShadowConnector(transport)
    ).run(
        workflow_ref="workflow:sanity-adapter:test",
        action_cases=(case,),
        policy=profile,
        risk_evidence=(ContentRiskEvidence(),),
        now=at,
    )

    assert result.verify_chain()
    assert result.production_writes == 0
    assert not result.execution_authorized
    assert result.item_results[0].action_payload_digest == case.digest()
    assert transport.calls == ["observe_current_state", "simulate_patch"]
