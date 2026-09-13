"""Deterministic product-content shadow demo for Governed Content Operations.

The demo uses the Sanity-compatible fixture transport and the canonical shadow
workflow. It contains no credentials, network client, clearance issuer, or
production mutation path.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import rfc8785
from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ConsequenceClass,
    PurposeRecordRef,
    Reversibility,
)
from src.valo_platform.connectors.content.sanity import (
    SanityDocumentMetadata,
    SanityFixtureTransport,
    SanitySchemaSnapshot,
    SanityShadowConnector,
)
from src.valo_platform.connectors.content.synthetic import ContentShadowConflict
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus

from .actions import (
    ContentAction,
    ContentActionCase,
    ContentApprovalRequirement,
    ContentChangeReference,
    ContentMateriality,
    ContentOperation,
)
from .content_policy import (
    ContentPolicyEvaluator,
    ContentPolicyProfile,
    ContentRiskDomain,
    ContentRiskEvidence,
)
from .invalidation import (
    ContentBindingObservation,
    ContentBindingSnapshot,
    ContentBindingValidator,
)
from .shadow_workflow import ContentShadowWorkflowRunner


class DemoScenarioResult(BaseModel):
    """Reference-only outcome for one deterministic demo scenario."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    scenario_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    action_ids: tuple[str, ...] = Field(min_length=1)
    item_decisions: tuple[ActionDecision, ...] = Field(min_length=1)
    batch_decision: ActionDecision
    reasons: tuple[str, ...]
    connector_outcomes: tuple[str, ...]
    evidence_chain_digest: str | None = None
    connector_blocked: bool = False
    binding_valid: bool = True
    invalidated_fields: tuple[str, ...] = ()
    production_writes: Literal[0] = 0
    execution_authorized: Literal[False] = False


class GovernedContentDemoReport(BaseModel):
    """Complete eight-scenario shadow-mode report."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    report_id: str
    generated_at: datetime
    content_system: Literal["sanity"] = "sanity"
    mode: Literal["shadow"] = "shadow"
    scenarios: tuple[DemoScenarioResult, ...] = Field(min_length=8, max_length=8)
    production_writes: Literal[0] = 0
    live_credentials_used: Literal[False] = False
    network_calls: Literal[0] = 0

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"generated_at"})

    def digest(self) -> str:
        return _digest(self.canonical_payload())


def build_governed_content_demo(
    at: datetime | None = None,
) -> GovernedContentDemoReport:
    """Run all acceptance scenarios against deterministic Sanity fixture data."""

    evaluated_at = _as_utc(
        at or datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    )
    schema, transport = _sanity_fixture()
    base_policy = _policy(evaluated_at)

    low_risk = _run_workflow_scenario(
        scenario_id="low-risk-seo-metadata",
        title="Low-risk SEO metadata update",
        cases=(
            _content_case(
                policy=base_policy,
                transport=transport,
                operation=ContentOperation.UPDATE_FIELD,
                case_id="case-demo-seo",
                document_id="product-1",
                affected_fields=("seo.title", "seo.description"),
                materiality=ContentMateriality.LOW,
            ),
        ),
        risks=(ContentRiskEvidence(),),
        policy=base_policy,
        transport=transport,
        at=evaluated_at,
    )

    safety = _run_workflow_scenario(
        scenario_id="high-risk-safety-claim",
        title="High-risk safety and regulated claim",
        cases=(
            _content_case(
                policy=base_policy,
                transport=transport,
                operation=ContentOperation.UPDATE_FIELD,
                case_id="case-demo-safety",
                document_id="product-2",
                affected_fields=("safety.instructions",),
                materiality=ContentMateriality.HIGH,
            ),
        ),
        risks=(
            ContentRiskEvidence(
                risk_domains=(
                    ContentRiskDomain.SAFETY,
                    ContentRiskDomain.REGULATED_PRODUCT,
                )
            ),
        ),
        policy=base_policy,
        transport=transport,
        at=evaluated_at,
    )

    stale_case = _content_case(
        policy=base_policy,
        transport=transport,
        operation=ContentOperation.UPDATE_FIELD,
        case_id="case-demo-stale-rev",
        document_id="product-1",
        affected_fields=("description",),
        source_revision="rev-product-1-stale",
    )
    stale_risk = ContentRiskEvidence(stale_content_state=True)
    stale_evaluation = ContentPolicyEvaluator().evaluate(
        action_case=stale_case,
        policy=base_policy,
        risk=stale_risk,
        now=evaluated_at,
    )
    stale_connector = SanityShadowConnector(transport)
    stale_blocked = False
    stale_reason = ""
    try:
        stale_connector.observe_current_state(stale_case)
    except ContentShadowConflict as exc:
        stale_blocked = True
        stale_reason = str(exc)
    stale = DemoScenarioResult(
        scenario_id="stale-sanity-revision",
        title="Stale Sanity _rev conflict",
        action_ids=(stale_case.action_case.case_id,),
        item_decisions=(stale_evaluation.decision,),
        batch_decision=stale_evaluation.decision,
        reasons=stale_evaluation.reasons + ((stale_reason,) if stale_reason else ()),
        connector_outcomes=("blocked_before_dry_run",),
        connector_blocked=stale_blocked,
    )

    missing_provenance = _run_workflow_scenario(
        scenario_id="missing-provenance",
        title="Missing source provenance",
        cases=(
            _content_case(
                policy=base_policy,
                transport=transport,
                operation=ContentOperation.UPDATE_FIELD,
                case_id="case-demo-provenance",
                document_id="product-1",
                affected_fields=("description",),
            ),
        ),
        risks=(ContentRiskEvidence(missing_provenance=True),),
        policy=base_policy,
        transport=transport,
        at=evaluated_at,
    )

    unauthorized = _run_workflow_scenario(
        scenario_id="unauthorized-publisher",
        title="Publisher outside the established mandate",
        cases=(
            _content_case(
                policy=base_policy,
                transport=transport,
                operation=ContentOperation.PUBLISH,
                case_id="case-demo-unauthorized",
                document_id="product-2",
                affected_fields=(),
                principal_id="agent:unauthorized-publisher",
                materiality=ContentMateriality.HIGH,
            ),
        ),
        risks=(ContentRiskEvidence(),),
        policy=base_policy,
        transport=transport,
        at=evaluated_at,
    )

    semantic_drift = _run_workflow_scenario(
        scenario_id="cross-language-semantic-drift",
        title="Cross-language localization with semantic drift",
        cases=(
            _content_case(
                policy=base_policy,
                transport=transport,
                operation=ContentOperation.LOCALIZE,
                case_id="case-demo-localize",
                document_id="product-3",
                affected_fields=("title", "description"),
                language="fr",
                locales=("fr",),
                jurisdictions=("FR",),
                materiality=ContentMateriality.MEDIUM,
            ),
        ),
        risks=(
            ContentRiskEvidence(
                cross_language=True,
                cross_market=True,
                semantic_uncertainty=True,
            ),
        ),
        policy=base_policy,
        transport=transport,
        at=evaluated_at,
    )

    batch_policy = _policy(
        evaluated_at,
        policy_id="policy-content-demo-batch",
        max_batch_size=1,
        max_cumulative_materiality_score=1,
    )
    oversized_batch = _run_workflow_scenario(
        scenario_id="aggregate-batch-escalation",
        title="Aggregate effect exceeds delegated batch threshold",
        cases=(
            _content_case(
                policy=batch_policy,
                transport=transport,
                operation=ContentOperation.UPDATE_FIELD,
                case_id="case-demo-batch-1",
                document_id="product-1",
                affected_fields=("seo.title",),
            ),
            _content_case(
                policy=batch_policy,
                transport=transport,
                operation=ContentOperation.UPDATE_FIELD,
                case_id="case-demo-batch-2",
                document_id="product-2",
                affected_fields=("seo.title",),
            ),
        ),
        risks=(ContentRiskEvidence(), ContentRiskEvidence()),
        policy=batch_policy,
        transport=transport,
        at=evaluated_at,
    )

    original_case = _content_case(
        policy=base_policy,
        transport=transport,
        operation=ContentOperation.UPDATE_FIELD,
        case_id="case-demo-policy-change",
        document_id="product-1",
        affected_fields=("seo.title",),
    )
    original_result = _run_workflow_scenario(
        scenario_id="policy-change-baseline",
        title="Baseline before policy change",
        cases=(original_case,),
        risks=(ContentRiskEvidence(),),
        policy=base_policy,
        transport=transport,
        at=evaluated_at,
    )
    changed_policy = _policy(
        evaluated_at,
        policy_id=base_policy.policy_id,
        version="2",
        max_uncertainty=0.05,
    )
    changed_evaluation = ContentPolicyEvaluator().evaluate(
        action_case=original_case,
        policy=changed_policy,
        risk=ContentRiskEvidence(),
        now=evaluated_at,
    )
    snapshot = ContentBindingSnapshot.capture(
        action_case=original_case,
        policy=base_policy,
        captured_at=evaluated_at,
    )
    observation = ContentBindingObservation.observe(
        action_case=original_case,
        policy=changed_policy,
        observed_at=evaluated_at + timedelta(minutes=1),
    )
    invalidation = ContentBindingValidator().evaluate(
        snapshot=snapshot,
        observation=observation,
        now=evaluated_at + timedelta(minutes=1),
    )
    policy_change = DemoScenarioResult(
        scenario_id="policy-change-invalidation",
        title="Prior binding invalidated after policy change",
        action_ids=(original_case.action_case.case_id,),
        item_decisions=(changed_evaluation.decision,),
        batch_decision=changed_evaluation.decision,
        reasons=changed_evaluation.reasons + invalidation.reasons,
        connector_outcomes=original_result.connector_outcomes,
        evidence_chain_digest=original_result.evidence_chain_digest,
        binding_valid=invalidation.valid,
        invalidated_fields=invalidation.invalidated_fields,
    )

    return GovernedContentDemoReport(
        report_id="governed-content-operations-shadow-demo-v0",
        generated_at=evaluated_at,
        scenarios=(
            low_risk,
            safety,
            stale,
            missing_provenance,
            unauthorized,
            semantic_drift,
            oversized_batch,
            policy_change,
        ),
    )


def _run_workflow_scenario(
    *,
    scenario_id: str,
    title: str,
    cases: tuple[ContentActionCase, ...],
    risks: tuple[ContentRiskEvidence, ...],
    policy: ContentPolicyProfile,
    transport: SanityFixtureTransport,
    at: datetime,
) -> DemoScenarioResult:
    connector = SanityShadowConnector(transport)
    result = ContentShadowWorkflowRunner(connector=connector).run(
        workflow_ref=f"workflow:content-demo:{scenario_id}",
        action_cases=cases,
        policy=policy,
        risk_evidence=risks,
        now=at,
    )
    return DemoScenarioResult(
        scenario_id=scenario_id,
        title=title,
        action_ids=tuple(item.action_id for item in result.item_results),
        item_decisions=tuple(item.policy_decision for item in result.item_results),
        batch_decision=result.batch_decision,
        reasons=result.batch_reasons,
        connector_outcomes=tuple(
            link.stage.value
            for link in result.evidence_links
            if link.stage.value in {"observation", "dry_run_simulation"}
        ),
        evidence_chain_digest=result.final_chain_digest,
        production_writes=result.production_writes,
        execution_authorized=result.execution_authorized,
    )


def _sanity_fixture() -> tuple[SanitySchemaSnapshot, SanityFixtureTransport]:
    schema = SanitySchemaSnapshot(
        project_ref="sanity-project:catalogue",
        dataset_ref="sanity-dataset:production-shadow",
        schema_version="catalogue-schema-v1",
        schema_digest=_digest(
            {
                "schema": "catalogue-schema-v1",
                "types": ["product"],
            }
        ),
        document_types=("product",),
        schema_refs=("sanity-schema:catalogue:v1",),
    )
    documents = tuple(
        SanityDocumentMetadata.model_validate(
            {
                "_id": f"product-{index}",
                "_rev": f"rev-product-{index}-v1",
                "_type": "product",
                "snapshot_digest": _digest(
                    {
                        "document_ref": f"product-{index}",
                        "revision": f"rev-product-{index}-v1",
                    }
                ),
                "locales": ("en", "fr") if index == 3 else ("en",),
                "metadata_refs": (f"sanity:product-{index}:metadata",),
            }
        )
        for index in range(1, 4)
    )
    return schema, SanityFixtureTransport(
        project_ref=schema.project_ref,
        dataset_ref=schema.dataset_ref,
        schema=schema,
        documents=documents,
    )


def _policy(
    at: datetime,
    **updates: object,
) -> ContentPolicyProfile:
    payload: dict[str, object] = {
        "policy_id": "policy-content-demo-v0",
        "version": "1",
        "tenant_id": "tenant-demo",
        "established_by": "human:content-owner",
        "authority_ref": "authority:content-board:demo",
        "authority_fingerprint": _ref_digest("authority:content-board:demo"),
        "mandate_ref": "mandate:tenant-demo:content:1",
        "mandate_fingerprint": _ref_digest("mandate:tenant-demo:content:1"),
        "allowed_principal_ids": ("agent:content-editor",),
        "allowed_content_systems": ("sanity",),
        "allowed_workspace_refs": ("workspace:product-content",),
        "allowed_project_refs": ("sanity-project:catalogue",),
        "allowed_dataset_refs": ("sanity-dataset:production-shadow",),
        "allowed_operations": tuple(ContentOperation),
        "allowed_markets": ("NO", "FR"),
        "allowed_languages": ("en", "fr"),
        "allowed_jurisdictions": ("NO", "FR"),
        "allowed_channels": ("web",),
        "auto_clear_operations": (
            ContentOperation.CREATE_DRAFT,
            ContentOperation.UPDATE_FIELD,
            ContentOperation.LOCALIZE,
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
        "max_batch_size": 4,
        "max_audience_count": 3,
        "max_unique_markets": 1,
        "max_unique_locales": 1,
        "max_cumulative_materiality_score": 8,
        "required_approver_roles": ("content_owner", "legal_reviewer"),
        "effective_from": at - timedelta(days=1),
        "effective_until": at + timedelta(days=30),
    }
    payload.update(updates)
    return ContentPolicyProfile.model_validate(payload)


def _content_case(
    *,
    policy: ContentPolicyProfile,
    transport: SanityFixtureTransport,
    operation: ContentOperation,
    case_id: str,
    document_id: str,
    affected_fields: tuple[str, ...],
    materiality: ContentMateriality = ContentMateriality.LOW,
    principal_id: str = "agent:content-editor",
    language: str = "en",
    locales: tuple[str, ...] = ("en",),
    jurisdictions: tuple[str, ...] = ("NO",),
    source_revision: str | None = None,
) -> ContentActionCase:
    revision = source_revision or transport.selected_documents((document_id,))[0].revision
    content = ContentAction(
        tenant_id=policy.tenant_id,
        principal_id=principal_id,
        delegated_mandate_ref=policy.mandate_ref,
        purpose_ref="purpose:tenant-demo:product-content:1",
        operation=operation,
        content_system="sanity",
        workspace_ref="workspace:product-content",
        project_ref=transport.project_ref,
        dataset_ref=transport.dataset_ref,
        record_ids=(document_id,),
        content_type="product",
        schema_version=transport.schema.schema_version,
        affected_fields=affected_fields,
        locales=locales,
        source_version_refs=(revision,),
        target_version_refs=(f"proposed:{document_id}:next",),
        proposed_change=ContentChangeReference(
            change_ref=f"sanity-patch:{case_id}",
            digest=_ref_digest(f"sanity-patch:{case_id}"),
            media_type="application/json-patch+json",
        ),
        batch_size=1,
        market=jurisdictions[0],
        language=language,
        jurisdictions=jurisdictions,
        channels=("web",),
        provenance_refs=(f"source:{document_id}:catalogue",),
        policy_refs=("policy:content-demo",),
        semantic_evidence_refs=(f"semantic:{document_id}:{language}",),
        rights_evidence_refs=(f"rights:{document_id}:brand",),
        materiality=materiality,
        affected_audiences=("customers",),
        reversibility=Reversibility.REVERSIBLE,
        rollback_ref=f"sanity:{document_id}:{revision}",
        approval_requirement=ContentApprovalRequirement.POLICY,
        approver_roles=("content_owner",),
        confidence=0.94,
        uncertainty=0.06,
        expected_effect=f"Shadow-evaluate {operation.value} for {document_id}.",
        idempotency_key=f"demo:{case_id}",
        content_snapshot_digest=transport.snapshot_digest((document_id,)),
        policy_snapshot_digest=policy.digest(),
    )
    evaluated_at = datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    evidence_refs = (
        content.provenance_refs
        + content.semantic_evidence_refs
        + content.rights_evidence_refs
    )
    record = ActionCaseRecord(
        case_id=case_id,
        tenant_id=content.tenant_id,
        environment="demo-shadow",
        record_version=1,
        case_hash=_ref_digest(case_id),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.READY,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-product-content",
            version="1",
            record_ref=content.purpose_ref,
            fingerprint=_ref_digest(content.purpose_ref),
            established_by="human:content-owner",
            authority_ref=policy.authority_ref,
            evidence_refs=list(content.provenance_refs),
        ),
        purpose_binding_ref="purpose-binding:product-content:1",
        mandate_ref=content.delegated_mandate_ref,
        mandate_fingerprint=policy.mandate_fingerprint,
        delegation_ref="delegation:content-demo:1",
        delegation_fingerprint=_ref_digest("delegation:content-demo:1"),
        policy_refs=content.policy_refs,
        policy_fingerprint=content.policy_snapshot_digest,
        evidence_refs=evidence_refs,
        evidence_fingerprint=_ref_digest("|".join(evidence_refs)),
        context_refs=(f"context:market:{content.market}",),
        context_fingerprint=_ref_digest(f"context:market:{content.market}"),
        state_refs=(f"sanity:{document_id}:{revision}",),
        state_fingerprint=content.content_snapshot_digest,
        action_class=operation.action_type,
        consequence_class=(
            ConsequenceClass.C3_HIGH
            if materiality in {ContentMateriality.HIGH, ContentMateriality.CRITICAL}
            else ConsequenceClass.C2_MEDIUM
        ),
        created_at=evaluated_at,
        updated_at=evaluated_at,
    )
    return ContentActionCase(action_case=record, content=content)


def _ref_digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
