from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ConsequenceClass,
    PurposeRecordRef,
    Reversibility,
)
from src.valo_platform.content_operations import (
    ContentAction,
    ContentActionCase,
    ContentApprovalRequirement,
    ContentBatchEvaluator,
    ContentBindingObservation,
    ContentBindingSnapshot,
    ContentBindingValidator,
    ContentChangeReference,
    ContentMateriality,
    ContentOperation,
    ContentPolicyEvaluator,
    ContentPolicyProfile,
    ContentRiskDomain,
    ContentRiskEvidence,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus


def sha(char: str) -> str:
    return "sha256:" + char * 64


def policy(now: datetime, **updates: object) -> ContentPolicyProfile:
    payload: dict[str, object] = {
        "policy_id": "policy-content-1",
        "version": "1",
        "tenant_id": "tenant-1",
        "established_by": "human:content-owner",
        "authority_ref": "authority:content-board:1",
        "authority_fingerprint": sha("a"),
        "mandate_ref": "mandate:tenant-1:content:1",
        "mandate_fingerprint": sha("3"),
        "allowed_principal_ids": ("agent:content-editor",),
        "allowed_content_systems": ("synthetic-cms",),
        "allowed_workspace_refs": ("workspace:catalogue",),
        "allowed_project_refs": ("project:products",),
        "allowed_dataset_refs": ("dataset:shadow",),
        "allowed_operations": tuple(ContentOperation),
        "allowed_markets": ("NO", "SE"),
        "allowed_languages": ("en", "no", "sv"),
        "allowed_jurisdictions": ("NO", "SE"),
        "allowed_channels": ("web", "mobile"),
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
        "max_batch_size": 5,
        "max_audience_count": 3,
        "max_unique_markets": 1,
        "max_unique_locales": 1,
        "max_cumulative_materiality_score": 4,
        "required_approver_roles": ("content_owner", "legal_reviewer"),
        "effective_from": now - timedelta(hours=1),
        "effective_until": now + timedelta(days=30),
    }
    payload.update(updates)
    return ContentPolicyProfile.model_validate(payload)


def content_case(
    profile: ContentPolicyProfile,
    operation: ContentOperation = ContentOperation.UPDATE_FIELD,
    *,
    case_id: str = "case-content-1",
    record_id: str = "record-1",
    content_updates: dict[str, object] | None = None,
    record_updates: dict[str, object] | None = None,
) -> ContentActionCase:
    mutation = operation is not ContentOperation.QUERY
    snapshot_digest = sha("8")
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
        "record_ids": (record_id,),
        "content_type": "product",
        "schema_version": "schema-v1",
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
        "expected_effect": "Observe or update synthetic catalogue metadata.",
        "idempotency_key": f"change-{record_id}-v2" if mutation else None,
        "content_snapshot_digest": snapshot_digest,
        "policy_snapshot_digest": profile.digest(),
    }
    content_payload.update(content_updates or {})
    content = ContentAction.model_validate(content_payload)

    now = datetime.now(timezone.utc)
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
        "state_refs": (f"state:{record_id}:v1",),
        "state_fingerprint": content.content_snapshot_digest,
        "action_class": operation.action_type,
        "consequence_class": ConsequenceClass.C2_MEDIUM,
        "created_at": now,
        "updated_at": now,
    }
    record_payload.update(record_updates or {})
    record = ActionCaseRecord.model_validate(record_payload)
    return ContentActionCase(action_case=record, content=content)


def evaluate(
    case: ContentActionCase,
    profile: ContentPolicyProfile,
    risk: ContentRiskEvidence | None = None,
):
    return ContentPolicyEvaluator().evaluate(
        action_case=case,
        policy=profile,
        risk=risk or ContentRiskEvidence(),
        now=datetime.now(timezone.utc),
    )


def test_in_scope_query_and_low_risk_update_can_allow() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)

    query_result = evaluate(content_case(profile, ContentOperation.QUERY), profile)
    update_result = evaluate(
        content_case(profile, ContentOperation.UPDATE_FIELD), profile
    )

    assert query_result.decision is ActionDecision.ALLOW
    assert update_result.decision is ActionDecision.ALLOW
    assert query_result.policy_digest == profile.digest()
    assert update_result.payload_digest.startswith("sha256:")


@pytest.mark.parametrize(
    "operation",
    [
        ContentOperation.PUBLISH,
        ContentOperation.DELETE,
        ContentOperation.UPDATE_SCHEMA,
        ContentOperation.MIGRATE,
        ContentOperation.BULK_UPDATE,
    ],
)
def test_high_consequence_operations_step_up_by_default(
    operation: ContentOperation,
) -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    result = evaluate(content_case(profile, operation), profile)
    assert result.decision is ActionDecision.STEP_UP
    assert operation.value in " ".join(result.reasons)


def test_sensitive_content_domains_step_up() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    domains = (
        ContentRiskDomain.PRICING,
        ContentRiskDomain.MEDICAL,
        ContentRiskDomain.LEGAL,
        ContentRiskDomain.SAFETY,
        ContentRiskDomain.REGULATED_PRODUCT,
        ContentRiskDomain.PUBLIC_POLICY,
    )
    result = evaluate(
        content_case(profile),
        profile,
        ContentRiskEvidence(risk_domains=domains),
    )
    assert result.decision is ActionDecision.STEP_UP
    assert set(result.risk_domains) == set(domains)


@pytest.mark.parametrize(
    "risk",
    [
        ContentRiskEvidence(missing_provenance=True),
        ContentRiskEvidence(unsupported_claims=True),
        ContentRiskEvidence(schema_mismatch=True),
        ContentRiskEvidence(stale_content_state=True),
    ],
)
def test_incomplete_or_stale_evidence_defers(risk: ContentRiskEvidence) -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    result = evaluate(content_case(profile), profile, risk)
    assert result.decision is ActionDecision.DEFER


def test_out_of_scope_principal_target_and_mandate_deny() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)

    principal = content_case(
        profile, content_updates={"principal_id": "agent:other"}
    )
    target = content_case(
        profile, content_updates={"workspace_ref": "workspace:other"}
    )
    other_policy = policy(
        now,
        policy_id="policy-content-2",
        mandate_ref="mandate:tenant-1:other:1",
    )
    mandate = content_case(profile)

    assert evaluate(principal, profile).decision is ActionDecision.DENY
    assert evaluate(target, profile).decision is ActionDecision.DENY
    assert evaluate(mandate, other_policy).decision is ActionDecision.DENY


def test_cross_language_semantic_uncertainty_escalates() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = content_case(
        profile,
        ContentOperation.LOCALIZE,
        content_updates={"language": "sv", "locales": ("sv",)},
    )
    result = evaluate(
        case,
        profile,
        ContentRiskEvidence(cross_language=True, semantic_uncertainty=True),
    )
    assert result.decision is ActionDecision.STEP_UP
    assert "semantics" in " ".join(result.reasons)


def test_cross_language_without_semantic_evidence_defers() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = content_case(
        profile,
        ContentOperation.LOCALIZE,
        content_updates={
            "language": "sv",
            "locales": ("sv",),
            "semantic_evidence_refs": (),
        },
        record_updates={
            "evidence_refs": ("evidence:source:1", "evidence:rights:1")
        },
    )
    result = evaluate(
        case,
        profile,
        ContentRiskEvidence(cross_language=True),
    )
    assert result.decision is ActionDecision.DEFER


def test_policy_snapshot_change_defers() -> None:
    now = datetime.now(timezone.utc)
    original = policy(now)
    changed = policy(now, version="2", max_uncertainty=0.15)
    case = content_case(original)
    assert evaluate(case, changed).decision is ActionDecision.DEFER


def test_aggregate_effect_escalates_individually_allowed_items() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(
        now,
        max_batch_size=1,
        max_cumulative_materiality_score=1,
    )
    cases = (
        content_case(profile, case_id="case-1", record_id="record-1"),
        content_case(profile, case_id="case-2", record_id="record-2"),
    )
    risks = (ContentRiskEvidence(), ContentRiskEvidence())
    items = tuple(evaluate(case, profile, risk) for case, risk in zip(cases, risks))
    assert all(item.decision is ActionDecision.ALLOW for item in items)

    batch = ContentBatchEvaluator().evaluate(
        action_cases=cases,
        item_evaluations=items,
        risk_evidence=risks,
        policy=profile,
        now=now,
    )
    assert batch.decision is ActionDecision.STEP_UP
    assert batch.total_batch_size == 2
    assert batch.unique_record_ids == ("record-1", "record-2")
    assert batch.member_payload_digests == tuple(case.digest() for case in cases)


@pytest.mark.parametrize(
    "restrictive",
    [
        ActionDecision.STEP_UP,
        ActionDecision.DEFER,
        ActionDecision.DENY,
        ActionDecision.HALT,
    ],
)
def test_batch_never_downgrades_member_outcome(
    restrictive: ActionDecision,
) -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now, max_batch_size=100, max_cumulative_materiality_score=100)
    cases = (
        content_case(profile, case_id="case-1", record_id="record-1"),
        content_case(profile, case_id="case-2", record_id="record-2"),
    )
    allowed = evaluate(cases[0], profile)
    restrictive_item = evaluate(cases[1], profile).model_copy(
        update={"decision": restrictive, "reasons": ("forced test outcome",)}
    )
    batch = ContentBatchEvaluator().evaluate(
        action_cases=cases,
        item_evaluations=(allowed, restrictive_item),
        risk_evidence=(ContentRiskEvidence(), ContentRiskEvidence()),
        policy=profile,
        now=now,
    )
    assert batch.decision is restrictive


def test_batch_order_is_digest_bound() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now, max_batch_size=100, max_cumulative_materiality_score=100)
    first = content_case(profile, case_id="case-1", record_id="record-1")
    second = content_case(profile, case_id="case-2", record_id="record-2")
    first_eval = evaluate(first, profile)
    second_eval = evaluate(second, profile)
    risks = (ContentRiskEvidence(), ContentRiskEvidence())
    evaluator = ContentBatchEvaluator()

    forward = evaluator.evaluate(
        action_cases=(first, second),
        item_evaluations=(first_eval, second_eval),
        risk_evidence=risks,
        policy=profile,
        now=now,
    )
    reverse = evaluator.evaluate(
        action_cases=(second, first),
        item_evaluations=(second_eval, first_eval),
        risk_evidence=risks,
        policy=profile,
        now=now,
    )
    assert forward.batch_digest != reverse.batch_digest


def test_unchanged_authoritative_bindings_remain_valid_deterministically() -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = content_case(profile)
    snapshot = ContentBindingSnapshot.capture(
        action_case=case, policy=profile, captured_at=now
    )
    observation = ContentBindingObservation.observe(
        action_case=case, policy=profile, observed_at=now + timedelta(minutes=1)
    )
    validator = ContentBindingValidator()

    first = validator.evaluate(snapshot=snapshot, observation=observation, now=now)
    second = validator.evaluate(snapshot=snapshot, observation=observation, now=now)

    assert first.valid
    assert first.invalidated_fields == ()
    assert snapshot.digest() == observation.digest()
    assert first == second


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("action_payload_digest", sha("b")),
        ("target_digest", sha("c")),
        ("state_binding_digest", sha("d")),
        ("content_snapshot_digest", sha("e")),
        ("policy_digest", sha("f")),
        ("mandate_fingerprint", sha("0")),
        ("authority_fingerprint", sha("1")),
        ("delegation_fingerprint", sha("2")),
        ("context_fingerprint", sha("3")),
        ("schema_version", "schema-v2"),
        ("source_version_refs", ("version:record-1:v2",)),
    ],
)
def test_each_authoritative_change_invalidates(
    field: str, value: object
) -> None:
    now = datetime.now(timezone.utc)
    profile = policy(now)
    case = content_case(profile)
    snapshot = ContentBindingSnapshot.capture(action_case=case, policy=profile)
    observation = ContentBindingObservation.observe(
        action_case=case, policy=profile
    ).model_copy(update={field: value})

    result = ContentBindingValidator().evaluate(
        snapshot=snapshot,
        observation=observation,
        now=now,
    )
    assert not result.valid
    assert result.invalidated_fields == (field,)
    assert "changed after evaluation" in result.reasons[0]


def test_layers_expose_no_clearance_or_execution_authority() -> None:
    objects = (
        ContentPolicyEvaluator(),
        ContentBatchEvaluator(),
        ContentBindingValidator(),
    )
    for obj in objects:
        for name in (
            "clear",
            "issue_clearance",
            "create_commit_token",
            "revoke_clearance",
            "execute",
            "publish",
            "mutate",
        ):
            assert not hasattr(obj, name)
