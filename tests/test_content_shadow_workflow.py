from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ActionDecision,
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
    ContentMateriality,
    ContentOperation,
    ContentPolicyProfile,
    ContentRiskDomain,
    ContentRiskEvidence,
    ContentShadowWorkflowRunner,
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
        dataset_ref="dataset:shadow",
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
                version_ref="version:record-2:v1",
                snapshot_digest=sha("b"),
                schema_version="schema-v1",
                field_names=("title", "description"),
                locales=("en",),
                metadata_refs=("metadata:record-2:v1",),
            ),
        ),
    )


def policy(now: datetime, **updates: object) -> ContentPolicyProfile:
    payload: dict[str, object] = {
        "policy_id": "policy-content-shadow-1",
        "version": "1",
        "tenant_id": "tenant-1",
        "established_by": "human:content-owner",
        "authority_ref": "authority:content-board:1",
        "authority_fingerprint": sha("c"),
        "mandate_ref": "mandate:tenant-1:content:1",
        "mandate_fingerprint": sha("3"),
        "allowed_principal_ids": (
            "agent:content-editor",
            "agent:untrusted",
        ),
        "allowed_content_systems": ("synthetic-cms",),
        "allowed_workspace_refs": ("workspace:catalogue",),
        "allowed_project_refs": ("project:products",),
        "allowed_dataset_refs": ("dataset:shadow",),
        "allowed_operations": tuple(ContentOperation),
        "allowed_markets": ("NO",),
        "allowed_languages": ("en",),
        "allowed_jurisdictions": ("NO",),
        "allowed_channels": ("web",),
        "auto_clear_operations": (
            ContentOperation.CREATE_DRAFT,
            ContentOperation.UPDATE_FIELD,
        ),
        "step_up_operations": (
            ContentOperation.PUBLISH,
            ContentOperation.DELETE,
            ContentOperation.UPDATE_SCHEMA,
            ContentOperation.MIGRATE,
            ContentOperation.BULK_UPDATE,
        ),
        "max_auto_materiality": ContentMateriality.MEDIUM,
        "max_uncertainty": 0.20,
        "max_batch_size": 10,
        "max_audience_count": 3,
        "max_unique_markets": 1,
        "max_unique_locales": 1,
        "max_cumulative_materiality_score": 10,
        "required_approver_roles": ("content_owner",),
        "effective_from": now - timedelta(hours=1),
        "effective_until": now + timedelta(days=30),
    }
    payload.update(updates)
    return ContentPolicyProfile.model_validate(payload)


def content_case(
    profile: ContentPolicyProfile,
    ws: SyntheticContentWorkspace,
    *,
    operation: ContentOperation = ContentOperation.UPDATE_FIELD,
    case_id: str = "case-1",
    record_id: str = "record-1",
    content_updates: dict[str, object] | None = None,
) -> ContentActionCase:
    mutation = operation is not ContentOperation.QUERY
    snapshot_digest = ws.snapshot_digest((record_id,))
    content_payload: dict[str, object] = {
        "tenant_id": "tenant-1",
        "principal_id": "agent:content-editor",
        "delegated_mandate_ref": profile.mandate_ref,
        "purpose_ref": "purpose:tenant-1:content:1",
        "operation": operation,
        "content_system": ws.content_system,
        "workspace_ref": ws.workspace_ref,
        "project_ref": ws.project_ref,
        "dataset_ref": ws.dataset_ref,
        "record_ids": (record_id,),
        "content_type": "product",
        "schema_version": ws.schema_version,
        "affected_fields": ("title",) if mutation else (),
        "locales": ("en",),
        "source_version_refs": (f"version:{record_id}:v1",),
        "target_version_refs": (f"version:{record_id}:v2",) if mutation else (),
        "proposed_change": (
            ContentChangeReference(
                change_ref=f"change:{record_id}:v2",
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
        "reversibility": (
            Reversibility.REVERSIBLE if mutation else Reversibility.UNKNOWN
        ),
        "rollback_ref": f"rollback:{record_id}:v1" if mutation else None,
        "approval_requirement": ContentApprovalRequirement.POLICY,
        "approver_roles": ("content_owner",),
        "confidence": 0.95,
        "uncertainty": 0.05,
        "expected_effect": "Observe and simulate a catalogue metadata change.",
        "idempotency_key": f"change-{record_id}-v2" if mutation else None,
        "content_snapshot_digest": snapshot_digest,
        "policy_snapshot_digest": profile.digest(),
    }
    content_payload.update(content_updates or {})
    content = ContentAction.model_validate(content_payload)

    now = datetime.now(timezone.utc)
    record = ActionCaseRecord(
        case_id=case_id,
        tenant_id=content.tenant_id,
        environment="test",
        record_version=1,
        case_hash=sha("1"),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.READY,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-content",
            version="1",
            record_ref=content.purpose_ref,
            fingerprint=sha("2"),
            established_by="human:content-owner",
            authority_ref=profile.authority_ref,
            evidence_refs=["evidence:source:1"],
        ),
        purpose_binding_ref="purpose-binding:content:1",
        mandate_ref=content.delegated_mandate_ref,
        mandate_fingerprint=profile.mandate_fingerprint,
        delegation_ref="delegation:tenant-1:content:1",
        delegation_fingerprint=sha("4"),
        policy_refs=content.policy_refs,
        policy_fingerprint=content.policy_snapshot_digest,
        evidence_refs=(
            "evidence:source:1",
            "evidence:semantic:1",
            "evidence:rights:1",
        ),
        evidence_fingerprint=sha("5"),
        context_refs=("context:market:NO",),
        context_fingerprint=sha("7"),
        state_refs=(f"state:{record_id}:v1",),
        state_fingerprint=content.content_snapshot_digest,
        action_class=operation.action_type,
        consequence_class=ConsequenceClass.C2_MEDIUM,
        created_at=now,
        updated_at=now,
    )
    return ContentActionCase(action_case=record, content=content)


def runner(ws: SyntheticContentWorkspace):
    transport = SyntheticContentWorkspaceTransport(ws)
    connector = SyntheticContentShadowConnector(transport)
    return ContentShadowWorkflowRunner(connector=connector), transport


def run_workflow(
    ws: SyntheticContentWorkspace,
    profile: ContentPolicyProfile,
    cases: tuple[ContentActionCase, ...],
    risks: tuple[ContentRiskEvidence, ...],
    now: datetime,
):
    workflow_runner, transport = runner(ws)
    result = workflow_runner.run(
        workflow_ref="workflow:catalogue:1",
        action_cases=cases,
        policy=profile,
        risk_evidence=risks,
        now=now,
    )
    return result, transport


def test_complete_shadow_workflow_produces_verified_chain() -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    profile = policy(now)
    cases = (
        content_case(profile, ws, case_id="case-1", record_id="record-1"),
        content_case(
            profile,
            ws,
            operation=ContentOperation.PUBLISH,
            case_id="case-2",
            record_id="record-2",
        ),
    )
    risks = (ContentRiskEvidence(), ContentRiskEvidence())

    result, transport = run_workflow(ws, profile, cases, risks, now)

    assert result.verify_chain()
    assert len(result.item_results) == 2
    assert len(result.evidence_links) == 13
    assert result.item_results[0].policy_decision is ActionDecision.ALLOW
    assert result.item_results[1].policy_decision is ActionDecision.STEP_UP
    assert result.batch_decision is ActionDecision.STEP_UP
    assert result.production_writes == 0
    assert not result.execution_authorized
    assert all(not item.execution_authorized for item in result.item_results)
    assert transport.calls == [
        "observe_current_state",
        "simulate",
        "observe_current_state",
        "simulate",
    ]


def test_identical_inputs_produce_identical_chain() -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    profile = policy(now)
    cases = (content_case(profile, ws),)
    risks = (ContentRiskEvidence(),)

    first, _ = run_workflow(ws, profile, cases, risks, now)
    second, _ = run_workflow(ws, profile, cases, risks, now + timedelta(hours=1))

    assert first.final_chain_digest == second.final_chain_digest
    assert tuple(link.chain_digest for link in first.evidence_links) == tuple(
        link.chain_digest for link in second.evidence_links
    )


def test_reordering_actions_changes_chain() -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    profile = policy(now)
    first = content_case(profile, ws, case_id="case-1", record_id="record-1")
    second = content_case(profile, ws, case_id="case-2", record_id="record-2")
    risks = (ContentRiskEvidence(), ContentRiskEvidence())

    forward, _ = run_workflow(ws, profile, (first, second), risks, now)
    reverse, _ = run_workflow(ws, profile, (second, first), risks, now)

    assert forward.final_chain_digest != reverse.final_chain_digest


def test_material_action_change_changes_chain() -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    profile = policy(now)
    original = content_case(profile, ws)
    changed = content_case(
        profile,
        ws,
        content_updates={
            "proposed_change": ContentChangeReference(
                change_ref="change:record-1:v3",
                digest=sha("d"),
                media_type="application/json-patch+json",
            ),
            "target_version_refs": ("version:record-1:v3",),
        },
    )

    first, _ = run_workflow(
        ws, profile, (original,), (ContentRiskEvidence(),), now
    )
    second, _ = run_workflow(
        ws, profile, (changed,), (ContentRiskEvidence(),), now
    )

    assert first.final_chain_digest != second.final_chain_digest


def test_every_evidence_link_verifies_against_prior_link() -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    profile = policy(now)
    result, _ = run_workflow(
        ws,
        profile,
        (content_case(profile, ws),),
        (ContentRiskEvidence(),),
        now,
    )
    assert result.verify_chain()
    assert all(link.verify() for link in result.evidence_links)
    assert all(
        current.previous_chain_digest == previous.chain_digest
        for previous, current in zip(
            result.evidence_links, result.evidence_links[1:]
        )
    )


@pytest.mark.parametrize(
    ("content_updates", "risk", "expected"),
    [
        (
            {"principal_id": "agent:outside-policy"},
            ContentRiskEvidence(),
            ActionDecision.DENY,
        ),
        ({}, ContentRiskEvidence(unsupported_claims=True), ActionDecision.DEFER),
        (
            {},
            ContentRiskEvidence(risk_domains=(ContentRiskDomain.SAFETY,)),
            ActionDecision.STEP_UP,
        ),
        ({}, ContentRiskEvidence(halt_required=True), ActionDecision.HALT),
    ],
)
def test_restrictive_decisions_remain_visible_without_permission(
    content_updates: dict[str, object],
    risk: ContentRiskEvidence,
    expected: ActionDecision,
) -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    profile = policy(now)
    case = content_case(profile, ws, content_updates=content_updates)

    result, transport = run_workflow(ws, profile, (case,), (risk,), now)

    assert result.item_results[0].policy_decision is expected
    assert result.batch_decision is expected
    assert not result.item_results[0].execution_authorized
    assert result.production_writes == 0
    assert transport.calls == ["observe_current_state", "simulate"]


@pytest.mark.parametrize(
    "updates",
    [
        {"content_snapshot_digest": sha("e")},
        {"source_version_refs": ("version:record-1:v0",)},
        {"schema_version": "schema-v0"},
    ],
)
def test_stale_state_version_or_schema_fails_closed(
    updates: dict[str, object],
) -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    profile = policy(now)
    case = content_case(profile, ws, content_updates=updates)
    workflow_runner, _ = runner(ws)

    with pytest.raises(ContentShadowConflict):
        workflow_runner.run(
            workflow_ref="workflow:stale:1",
            action_cases=(case,),
            policy=profile,
            risk_evidence=(ContentRiskEvidence(),),
            now=now,
        )


def test_result_is_reference_only_and_workspace_is_unchanged() -> None:
    now = datetime.now(timezone.utc)
    ws = workspace()
    before = ws.model_dump(mode="json")
    profile = policy(now)
    result, _ = run_workflow(
        ws,
        profile,
        (content_case(profile, ws),),
        (ContentRiskEvidence(),),
        now,
    )
    payload = result.model_dump_json()

    assert ws.model_dump(mode="json") == before
    assert "raw_content" not in payload
    assert "secret" not in payload
    assert "credential" not in payload
    assert "ExecutionReceipt" not in payload
    assert "commit_envelope" not in payload


def test_runner_exposes_no_execution_or_clearance_authority() -> None:
    workflow_runner, _ = runner(workspace())
    for name in (
        "clear",
        "issue_clearance",
        "create_commit_token",
        "execute",
        "publish",
        "mutate",
        "record_execution",
    ):
        assert not hasattr(workflow_runner, name)
