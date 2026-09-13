from __future__ import annotations

import base64
import copy
import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.valo_platform.action_envelope.bounded_connector import (
    BoundedConnectorBoundary,
    ConnectorBoundaryError,
    SQLiteTokenConsumptionStore,
    TrustedCoreKey,
)
from src.valo_platform.action_envelope.models import (
    ConsequenceClass,
    PurposeRecordRef,
    Reversibility,
)
from src.valo_platform.connectors.content import (
    ClearedContentMutationConnector,
    ConditionalContentFixtureTransport,
    ConditionalContentRecord,
    ContentMutationRequest,
    ContentMutationResult,
    SanityShadowConnector,
)
from src.valo_platform.continuous_integrity import (
    IntegrityDecision,
    IntegrityTrigger,
)
from src.valo_platform.content_operations import (
    ContentAction,
    ContentActionCase,
    ContentApprovalRequirement,
    ContentChangeReference,
    ContentContinuousIntegrityAdapter,
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


CONNECTOR_ID = "connector.content.fixture"
CONTENT_SYSTEM = "fixture-cms"
CLEARANCE_DIGEST = "sha256:" + "9" * 64


def sha(char: str) -> str:
    return "sha256:" + char * 64


def digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


class ReceiptSigner:
    issuer_id = "connector:content-fixture:test"
    issuer_role = "EXECUTION_RECEIPT_ISSUER"
    key_id = "key:connector:content-fixture:1"
    algorithm = "Ed25519"

    def __init__(self) -> None:
        self._key = Ed25519PrivateKey.generate()

    def sign(self, data: bytes) -> str:
        return base64.b64encode(self._key.sign(data)).decode("ascii")


def make_transport(
    *,
    schema_version: str = "schema-v1",
    version_ref: str = "version:record-1:v1",
    record_snapshot_digest: str = sha("8"),
) -> ConditionalContentFixtureTransport:
    return ConditionalContentFixtureTransport(
        content_system=CONTENT_SYSTEM,
        workspace_ref="workspace:catalogue",
        project_ref="project:products",
        dataset_ref="dataset:test",
        schema_version=schema_version,
        records=(
            ConditionalContentRecord(
                record_id="record-1",
                version_ref=version_ref,
                snapshot_digest=record_snapshot_digest,
            ),
        ),
    )


def make_policy(now: datetime, **updates: object) -> ContentPolicyProfile:
    payload: dict[str, object] = {
        "policy_id": "policy-cleared-content-mutation",
        "version": "1",
        "tenant_id": "tenant-1",
        "established_by": "human:content-owner",
        "authority_ref": "authority:content-board:1",
        "authority_fingerprint": sha("a"),
        "mandate_ref": "mandate:tenant-1:content:1",
        "mandate_fingerprint": sha("3"),
        "allowed_principal_ids": ("agent:content-editor",),
        "allowed_content_systems": (CONTENT_SYSTEM,),
        "allowed_workspace_refs": ("workspace:catalogue",),
        "allowed_project_refs": ("project:products",),
        "allowed_dataset_refs": ("dataset:test",),
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
    *,
    policy: ContentPolicyProfile,
    transport: ConditionalContentFixtureTransport,
    operation: ContentOperation = ContentOperation.UPDATE_FIELD,
    case_id: str = "case-content-mutation-1",
    target_version_refs: tuple[str, ...] = ("version:record-1:v2",),
    change_digest: str = sha("6"),
) -> ContentActionCase:
    now = datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc)
    snapshot = transport.snapshot_digest(("record-1",))
    content = ContentAction(
        tenant_id="tenant-1",
        principal_id="agent:content-editor",
        delegated_mandate_ref="mandate:tenant-1:content:1",
        purpose_ref="purpose:tenant-1:content:1",
        operation=operation,
        content_system=CONTENT_SYSTEM,
        workspace_ref="workspace:catalogue",
        project_ref="project:products",
        dataset_ref="dataset:test",
        record_ids=("record-1",),
        content_type="product",
        schema_version="schema-v1",
        affected_fields=("title",),
        locales=("en",),
        source_version_refs=("version:record-1:v1",),
        target_version_refs=target_version_refs,
        proposed_change=ContentChangeReference(
            change_ref="change:record-1:title:v2",
            digest=change_digest,
            media_type="application/json-patch+json",
        ),
        batch_size=1,
        market="NO",
        language="en",
        jurisdictions=("NO",),
        channels=("web",),
        provenance_refs=("evidence:source:1",),
        policy_refs=("policy:content:1",),
        semantic_evidence_refs=("evidence:semantic:1",),
        rights_evidence_refs=("evidence:rights:1",),
        materiality=ContentMateriality.LOW,
        affected_audiences=("customers",),
        reversibility=Reversibility.REVERSIBLE,
        rollback_ref="rollback:record-1:v1",
        approval_requirement=ContentApprovalRequirement.POLICY,
        approver_roles=("content_owner",),
        confidence=0.95,
        uncertainty=0.05,
        expected_effect="Update one synthetic title reference.",
        idempotency_key="mutation-record-1-title-v2",
        content_snapshot_digest=snapshot,
        policy_snapshot_digest=policy.digest(),
    )
    record = ActionCaseRecord(
        case_id=case_id,
        tenant_id="tenant-1",
        environment="test",
        record_version=1,
        case_hash=sha("1"),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.CLEARED,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-content",
            version="1",
            record_ref=content.purpose_ref,
            fingerprint=sha("2"),
            established_by="human:content-owner",
            authority_ref=policy.authority_ref,
            evidence_refs=["evidence:source:1"],
        ),
        purpose_binding_ref="purpose-binding:content:1",
        mandate_ref=content.delegated_mandate_ref,
        mandate_fingerprint=sha("3"),
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
        state_refs=("state:record-1:v1",),
        state_fingerprint=snapshot,
        action_class=operation.action_type,
        consequence_class=ConsequenceClass.C2_MEDIUM,
        clearance_ref="clearance-content-mutation-1",
        created_at=now,
        updated_at=now,
        evaluated_at=now,
        cleared_at=now,
    )
    return ContentActionCase(action_case=record, content=content)


def integrity_evidence(
    *,
    action_case: ContentActionCase,
    policy: ContentPolicyProfile,
    now: datetime,
    critical_validity: dict[str, bool] | None = None,
):
    adapter = ContentContinuousIntegrityAdapter()
    integrity_profile = default_content_integrity_profile()
    baseline = adapter.capture_baseline(
        baseline_id="baseline-content-mutation-1",
        action_case=action_case,
        policy=policy,
        clearance_digest=CLEARANCE_DIGEST,
        profile=integrity_profile,
        captured_at=now,
    )
    checkpoint = adapter.checkpoint(
        receipt_id="checkpoint-content-mutation-1",
        baseline=baseline,
        action_case=action_case,
        policy=policy,
        profile=integrity_profile,
        trigger=IntegrityTrigger.CHECKPOINT,
        observed_at=now + timedelta(seconds=1),
        critical_validity=critical_validity,
    )
    return adapter, integrity_profile, baseline, checkpoint


def signed_token(
    action_case: ContentActionCase,
    now: datetime,
    *,
    clearance_digest: str = CLEARANCE_DIGEST,
    connector_id: str = CONNECTOR_ID,
    capability: str | None = None,
) -> tuple[dict, Ed25519PrivateKey]:
    key = Ed25519PrivateKey.generate()
    expiry_time = now + timedelta(minutes=5)
    issued = now.isoformat().replace("+00:00", "Z")
    expiry = expiry_time.isoformat().replace("+00:00", "Z")
    payload = {
        "commit_token_id": "token-content-mutation-1",
        "execution_id": "execution-content-mutation-1",
        "tenant_id": action_case.action_case.tenant_id,
        "action_id": action_case.action_case.case_id,
        "case_hash": action_case.action_case.case_hash,
        "action_envelope_digest": sha("b"),
        "clearance_id": "clearance-content-mutation-1",
        "clearance_digest": clearance_digest,
        "racs_decision_id": "racs-decision-content-mutation-1",
        "racs_decision_digest": sha("d"),
        "decision": "ALLOW",
        "evidence_refs": list(action_case.action_case.evidence_refs),
        "execution_permit_id": "permit-content-mutation-1",
        "execution_permit_digest": sha("c"),
        "connector_id": connector_id,
        "capability": capability or action_case.content.operation.value,
        "target_digest": action_case.target_digest(),
        "payload_digest": action_case.digest(),
        "reservation_id": "reservation-content-mutation-1",
        "issued_at": issued,
        "valid_until": expiry,
        "single_use": True,
        "consumption_registry_ref": "consumption:content-mutation:test",
    }
    artifact = {
        "artifact_type": "COMMIT_TOKEN",
        "schema_version": "0.2.0",
        "profile_id": "racs-core-0.2",
        "artifact_id": "token-content-mutation-1",
        "tenant_id": "tenant-1",
        "trust_domain": "tenant-1:test",
        "issuer_id": "core:test",
        "issuer_role": "CORE_COMMIT_TOKEN_ISSUER",
        "issued_at": issued,
        "expires_at": expiry,
        "payload": payload,
        "payload_digest": digest(payload),
        "canonicalization": "RACS-JCS-1",
        "signature": {
            "algorithm": "Ed25519",
            "key_id": "key:core:1",
            "value": "",
        },
    }
    artifact["signature"]["value"] = base64.b64encode(
        key.sign(rfc8785.dumps(artifact))
    ).decode("ascii")
    return artifact, key


def make_connector(tmp_path, key: Ed25519PrivateKey) -> ClearedContentMutationConnector:
    boundary = BoundedConnectorBoundary(
        trusted_core_key=TrustedCoreKey(
            issuer_id="core:test",
            issuer_role="CORE_COMMIT_TOKEN_ISSUER",
            key_id="key:core:1",
            tenant_id="tenant-1",
            trust_domain="tenant-1:test",
            public_key=key.public_key(),
        ),
        consumption_store=SQLiteTokenConsumptionStore(tmp_path / "tokens.db"),
        receipt_signer=ReceiptSigner(),
        receipt_trust_domain="tenant-1:test",
    )
    return ClearedContentMutationConnector(
        boundary=boundary,
        connector_id=CONNECTOR_ID,
        content_system=CONTENT_SYSTEM,
    )


def test_valid_token_and_fresh_checkpoint_execute_once(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=action_case, policy=policy, now=now
    )
    token, key = signed_token(action_case, now)

    result = make_connector(tmp_path, key).execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=transport,
        receipt_id="receipt-content-mutation-1",
        now=now + timedelta(seconds=2),
    )

    assert transport.successful_mutations == 1
    assert len(transport.attempts) == 1
    assert transport.records()[0].version_ref == "version:record-1:v2"
    receipt = result.receipt["payload"]
    assert receipt["technical_outcome"] == "SUCCEEDED"
    assert receipt["payload_digest"] == action_case.digest()
    assert receipt["target_digest"] == action_case.target_digest()
    assert receipt["clearance_digest"] == CLEARANCE_DIGEST


@pytest.mark.parametrize("missing", ["token", "baseline", "checkpoint"])
def test_missing_governance_input_blocks_before_transport(tmp_path, missing: str) -> None:
    now = datetime.now(timezone.utc)
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=action_case, policy=policy, now=now
    )
    token, key = signed_token(action_case, now)

    with pytest.raises(ConnectorBoundaryError, match="required"):
        make_connector(tmp_path, key).execute(
            action_case=action_case,
            signed_commit_token=None if missing == "token" else token,
            integrity_baseline=None if missing == "baseline" else baseline,
            integrity_checkpoint=None if missing == "checkpoint" else checkpoint,
            transport=transport,
            receipt_id="receipt-missing",
            now=now + timedelta(seconds=2),
        )

    assert transport.attempts == []
    assert transport.successful_mutations == 0


def test_reevaluate_and_halt_checkpoints_block_before_token_consumption(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    adapter, profile, baseline, _ = integrity_evidence(
        action_case=action_case, policy=policy, now=now
    )
    token, key = signed_token(action_case, now)
    connector = make_connector(tmp_path, key)

    changed_policy = make_policy(now, version="2", max_uncertainty=0.08)
    reevaluate = adapter.checkpoint(
        receipt_id="checkpoint-reevaluate",
        baseline=baseline,
        action_case=action_case,
        policy=changed_policy,
        profile=profile,
        trigger=IntegrityTrigger.POLICY_CHANGE,
        observed_at=now + timedelta(seconds=1),
    )
    assert reevaluate.checkpoint_receipt.decision is IntegrityDecision.REEVALUATE
    with pytest.raises(ConnectorBoundaryError, match="invalidated"):
        connector.execute(
            action_case=action_case,
            signed_commit_token=token,
            integrity_baseline=baseline,
            integrity_checkpoint=reevaluate,
            transport=transport,
            receipt_id="receipt-reevaluate",
            now=now + timedelta(seconds=2),
        )

    halt = adapter.checkpoint(
        receipt_id="checkpoint-halt",
        baseline=baseline,
        action_case=action_case,
        policy=policy,
        profile=profile,
        trigger=IntegrityTrigger.AUTHORITY_CHANGE,
        observed_at=now + timedelta(seconds=1),
        critical_validity={"authority": False},
    )
    assert halt.checkpoint_receipt.decision is IntegrityDecision.HALT
    with pytest.raises(ConnectorBoundaryError, match="requires halt"):
        connector.execute(
            action_case=action_case,
            signed_commit_token=token,
            integrity_baseline=baseline,
            integrity_checkpoint=halt,
            transport=transport,
            receipt_id="receipt-halt",
            now=now + timedelta(seconds=2),
        )

    assert transport.attempts == []


def test_clearance_and_case_mismatches_block_before_transport(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=action_case, policy=policy, now=now
    )

    wrong_clearance, key = signed_token(
        action_case, now, clearance_digest=sha("d")
    )
    with pytest.raises(ConnectorBoundaryError, match="clearance_digest"):
        make_connector(tmp_path, key).execute(
            action_case=action_case,
            signed_commit_token=wrong_clearance,
            integrity_baseline=baseline,
            integrity_checkpoint=checkpoint,
            transport=transport,
            receipt_id="receipt-wrong-clearance",
            now=now + timedelta(seconds=2),
        )

    token, key = signed_token(action_case, now)
    cross_case = copy.deepcopy(token)
    cross_case["payload"]["action_id"] = "case-other"
    with pytest.raises(ConnectorBoundaryError, match="action_id"):
        make_connector(tmp_path / "cross", key).execute(
            action_case=action_case,
            signed_commit_token=cross_case,
            integrity_baseline=baseline,
            integrity_checkpoint=checkpoint,
            transport=transport,
            receipt_id="receipt-cross-case",
            now=now + timedelta(seconds=2),
        )

    assert transport.attempts == []


@pytest.mark.parametrize("change", ["payload", "target", "operation"])
def test_exact_token_binding_blocks_changed_action(tmp_path, change: str) -> None:
    now = datetime.now(timezone.utc)
    original_transport = make_transport()
    policy = make_policy(now)
    original = make_case(policy=policy, transport=original_transport)
    token, key = signed_token(original, now)

    changed_transport = make_transport()
    if change == "payload":
        changed = make_case(
            policy=policy,
            transport=changed_transport,
            change_digest=sha("e"),
        )
    elif change == "target":
        changed = make_case(
            policy=policy,
            transport=changed_transport,
            target_version_refs=("version:record-1:v3",),
        )
    else:
        changed = make_case(
            policy=policy,
            transport=changed_transport,
            operation=ContentOperation.LOCALIZE,
        )
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=changed, policy=policy, now=now
    )

    with pytest.raises(ConnectorBoundaryError, match="binding mismatch"):
        make_connector(tmp_path, key).execute(
            action_case=changed,
            signed_commit_token=token,
            integrity_baseline=baseline,
            integrity_checkpoint=checkpoint,
            transport=changed_transport,
            receipt_id=f"receipt-changed-{change}",
            now=now + timedelta(seconds=2),
        )

    assert changed_transport.attempts == []


@pytest.mark.parametrize(
    "stale_transport",
    [
        make_transport(schema_version="schema-v2"),
        make_transport(version_ref="version:record-1:other"),
        make_transport(record_snapshot_digest=sha("f")),
    ],
    ids=["schema", "source-version", "snapshot"],
)
def test_stale_provider_precondition_fails_without_state_change(
    tmp_path, stale_transport: ConditionalContentFixtureTransport
) -> None:
    now = datetime.now(timezone.utc)
    original_transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=original_transport)
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=action_case, policy=policy, now=now
    )
    token, key = signed_token(action_case, now)
    before = stale_transport.records()

    result = make_connector(tmp_path, key).execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=stale_transport,
        receipt_id="receipt-stale-provider",
        now=now + timedelta(seconds=2),
    )

    assert result.receipt["payload"]["technical_outcome"] == "FAILED"
    assert result.receipt["payload"]["error_class"] == "DefiniteProviderFailure"
    assert stale_transport.records() == before
    assert stale_transport.successful_mutations == 0


class PostconditionMismatchTransport:
    def __init__(self, delegate: ConditionalContentFixtureTransport) -> None:
        self.delegate = delegate

    def mutate_if_current(self, request: ContentMutationRequest) -> ContentMutationResult:
        result = self.delegate.mutate_if_current(request)
        return replace(result, project_ref="project:wrong")


def test_postcondition_mismatch_is_indeterminate(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    fixture = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=fixture)
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=action_case, policy=policy, now=now
    )
    token, key = signed_token(action_case, now)

    result = make_connector(tmp_path, key).execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=PostconditionMismatchTransport(fixture),
        receipt_id="receipt-indeterminate",
        now=now + timedelta(seconds=2),
    )

    assert fixture.successful_mutations == 1
    assert result.provider_result is None
    assert result.receipt["payload"]["technical_outcome"] == "INDETERMINATE"
    assert result.receipt["payload"]["error_class"] == "IndeterminateProviderFailure"


def test_commit_token_is_single_use(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    _, _, baseline, checkpoint = integrity_evidence(
        action_case=action_case, policy=policy, now=now
    )
    token, key = signed_token(action_case, now)
    connector = make_connector(tmp_path, key)

    connector.execute(
        action_case=action_case,
        signed_commit_token=token,
        integrity_baseline=baseline,
        integrity_checkpoint=checkpoint,
        transport=transport,
        receipt_id="receipt-once",
        now=now + timedelta(seconds=2),
    )
    with pytest.raises(ConnectorBoundaryError, match="already consumed"):
        connector.execute(
            action_case=action_case,
            signed_commit_token=token,
            integrity_baseline=baseline,
            integrity_checkpoint=checkpoint,
            transport=transport,
            receipt_id="receipt-twice",
            now=now + timedelta(seconds=3),
        )

    assert len(transport.attempts) == 1
    assert transport.successful_mutations == 1


def test_fixture_and_connector_expose_no_live_or_authority_surface(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    transport = make_transport()
    policy = make_policy(now)
    action_case = make_case(policy=policy, transport=transport)
    token, key = signed_token(action_case, now)
    connector = make_connector(tmp_path, key)

    forbidden_connector = {
        "evaluate",
        "issue_clearance",
        "grant_clearance",
        "mint_commit_token",
    }
    assert forbidden_connector.isdisjoint(set(dir(connector)))
    assert not hasattr(transport, "credentials")
    assert not hasattr(transport, "network_client")
    assert not hasattr(SanityShadowConnector, "execute")
    assert not hasattr(SanityShadowConnector, "mutate")
    assert token["payload"]["payload_digest"] == action_case.digest()
