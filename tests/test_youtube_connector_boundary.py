from __future__ import annotations

import base64
import copy
import hashlib
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
    ActionType,
    ConsequenceClass,
    PurposeRecordRef,
)
from src.valo_platform.connectors.content import (
    PublicationMutationRequest,
    PublicationMutationResult,
    YouTubePublicationConnector,
)
from src.valo_platform.content_operations.publication import (
    PublicationAction,
    PublicationActionCase,
    PublicationArtifact,
    PublicationPrivacy,
    PublicationRollback,
)
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus


def sha(char: str) -> str:
    return "sha256:" + char * 64


def digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


class ReceiptSigner:
    issuer_id = "connector:youtube:test"
    issuer_role = "EXECUTION_RECEIPT_ISSUER"
    key_id = "key:connector:youtube:1"
    algorithm = "Ed25519"

    def __init__(self) -> None:
        self._key = Ed25519PrivateKey.generate()

    def sign(self, data: bytes) -> str:
        return base64.b64encode(self._key.sign(data)).decode("ascii")


class FakeTransport:
    def __init__(self, result: PublicationMutationResult) -> None:
        self.result = result
        self.calls: list[PublicationMutationRequest] = []

    def publish(self, request: PublicationMutationRequest) -> PublicationMutationResult:
        self.calls.append(request)
        return self.result


def action_case() -> ActionCaseRecord:
    now = datetime.now(timezone.utc)
    return ActionCaseRecord(
        case_id="case-publication-1",
        tenant_id="tenant-1",
        environment="test",
        record_version=1,
        case_hash=sha("1"),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.CLEARED,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-content",
            version="1",
            record_ref="purpose:tenant-1:content:1",
            fingerprint=sha("2"),
            established_by="human:publisher",
            authority_ref="authority:board:1",
            evidence_refs=["evidence:source:1"],
        ),
        purpose_binding_ref="purpose-binding:content:1",
        mandate_ref="mandate:tenant-1:publisher:1",
        mandate_fingerprint=sha("3"),
        evidence_refs=(
            "evidence:source:1",
            "evidence:claim:1",
            "evidence:rights:1",
        ),
        evidence_fingerprint=sha("4"),
        action_class=ActionType.EXTERNAL_PUBLICATION,
        consequence_class=ConsequenceClass.C2_MEDIUM,
        clearance_ref="clearance-publication-1",
        created_at=now,
        updated_at=now,
        evaluated_at=now,
        cleared_at=now,
    )


def publication_case(**updates: object) -> PublicationActionCase:
    payload: dict[str, object] = {
        "tenant_id": "tenant-1",
        "principal_id": "human:publisher",
        "delegated_mandate_ref": "mandate:tenant-1:publisher:1",
        "provider": "youtube",
        "account_ref": "youtube-account:1",
        "channel_ref": "youtube-channel:1",
        "video": PublicationArtifact(
            artifact_ref="media:video:1",
            digest=sha("5"),
            media_type="video/mp4",
        ),
        "title": "Governed publication",
        "description": "Exact metadata bound before upload.",
        "tags": ("governance", "reht"),
        "language": "en",
        "audiences": ("general",),
        "jurisdictions": ("NO",),
        "privacy_status": PublicationPrivacy.PRIVATE,
        "made_for_kids": False,
        "captions": (),
        "thumbnail": PublicationArtifact(
            artifact_ref="media:thumbnail:1",
            digest=sha("6"),
            media_type="image/png",
        ),
        "source_refs": ("evidence:source:1",),
        "claim_evidence_refs": ("evidence:claim:1",),
        "rights_evidence_refs": ("evidence:rights:1",),
        "policy_refs": ("policy:channel:1",),
        "policy_snapshot_digest": sha("7"),
        "rollback_capability": PublicationRollback.UNPUBLISH,
        "idempotency_key": "publication-1",
    }
    payload.update(updates)
    return PublicationActionCase(
        action_case=action_case(),
        publication=PublicationAction.model_validate(payload),
    )


def signed_token(
    case: PublicationActionCase,
    now: datetime,
    *,
    valid_until: datetime | None = None,
) -> tuple[dict, Ed25519PrivateKey]:
    key = Ed25519PrivateKey.generate()
    valid_until = valid_until or now + timedelta(minutes=5)
    timestamp = now.isoformat().replace("+00:00", "Z")
    expiry = valid_until.isoformat().replace("+00:00", "Z")
    payload = {
        "commit_token_id": "token-publication-1",
        "execution_id": "execution-publication-1",
        "tenant_id": case.action_case.tenant_id,
        "action_id": case.action_case.case_id,
        "case_hash": case.action_case.case_hash,
        "action_envelope_digest": sha("8"),
        "clearance_id": "clearance-publication-1",
        "clearance_digest": sha("9"),
        "racs_decision_id": "racs-decision-publication-1",
        "racs_decision_digest": sha("d"),
        "decision": "ALLOW",
        "evidence_refs": list(case.action_case.evidence_refs),
        "execution_permit_id": "permit-publication-1",
        "execution_permit_digest": sha("a"),
        "connector_id": YouTubePublicationConnector.CONNECTOR_ID,
        "capability": YouTubePublicationConnector.CAPABILITY,
        "target_digest": case.target_digest(),
        "payload_digest": case.digest(),
        "reservation_id": "reservation-publication-1",
        "issued_at": timestamp,
        "valid_until": expiry,
        "single_use": True,
        "consumption_registry_ref": "consumption:publication:test",
    }
    artifact = {
        "artifact_type": "COMMIT_TOKEN",
        "schema_version": "0.2.0",
        "profile_id": "racs-core-0.2",
        "artifact_id": "token-publication-1",
        "tenant_id": "tenant-1",
        "trust_domain": "tenant-1:test",
        "issuer_id": "core:test",
        "issuer_role": "CORE_COMMIT_TOKEN_ISSUER",
        "issued_at": timestamp,
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


def connector(
    tmp_path: object,
    key: Ed25519PrivateKey,
) -> YouTubePublicationConnector:
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
    return YouTubePublicationConnector(boundary)


def successful_transport(
    *,
    account_ref: str = "youtube-account:1",
    channel_ref: str = "youtube-channel:1",
    privacy_status: PublicationPrivacy = PublicationPrivacy.PRIVATE,
) -> FakeTransport:
    return FakeTransport(
        PublicationMutationResult(
            provider_reference="youtube:video:abc123",
            provider="youtube",
            account_ref=account_ref,
            channel_ref=channel_ref,
            privacy_status=privacy_status,
            response={"video_id": "abc123"},
        )
    )


def test_valid_commit_token_executes_once_and_emits_receipt(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    case = publication_case()
    token, key = signed_token(case, now)
    transport = successful_transport()

    result = connector(tmp_path, key).execute(
        action_case=case,
        signed_commit_token=token,
        transport=transport,
        receipt_id="receipt-publication-1",
        now=now,
    )

    assert len(transport.calls) == 1
    request = transport.calls[0]
    assert request.payload_digest == case.digest()
    assert request.target_digest == case.target_digest()
    assert request.idempotency_key == "publication-1"
    assert result.receipt["payload"]["technical_outcome"] == "SUCCEEDED"
    assert result.receipt["payload"]["provider_reference"] == "youtube:video:abc123"
    assert result.receipt["payload"]["payload_digest"] == case.digest()
    assert result.receipt["payload"]["target_digest"] == case.target_digest()


def test_missing_commit_token_blocks_before_transport(tmp_path) -> None:
    _, key = signed_token(publication_case(), datetime.now(timezone.utc))
    transport = successful_transport()

    with pytest.raises(ConnectorBoundaryError, match="required"):
        connector(tmp_path, key).execute(
            action_case=publication_case(),
            signed_commit_token=None,
            transport=transport,
            receipt_id="receipt-publication-1",
        )

    assert transport.calls == []


def test_private_clearance_cannot_authorize_public_visibility(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    private_case = publication_case()
    public_case = publication_case(privacy_status=PublicationPrivacy.PUBLIC)
    token, key = signed_token(private_case, now)
    transport = successful_transport(privacy_status=PublicationPrivacy.PUBLIC)

    with pytest.raises(ConnectorBoundaryError, match="payload_digest binding mismatch"):
        connector(tmp_path, key).execute(
            action_case=public_case,
            signed_commit_token=token,
            transport=transport,
            receipt_id="receipt-publication-1",
            now=now,
        )

    assert transport.calls == []


def test_clearance_for_another_account_blocks_before_transport(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    original = publication_case()
    changed_account = publication_case(account_ref="youtube-account:2")
    token, key = signed_token(original, now)
    transport = successful_transport(account_ref="youtube-account:2")

    with pytest.raises(ConnectorBoundaryError, match="target_digest binding mismatch"):
        connector(tmp_path, key).execute(
            action_case=changed_account,
            signed_commit_token=token,
            transport=transport,
            receipt_id="receipt-publication-1",
            now=now,
        )

    assert transport.calls == []


def test_expired_token_blocks_before_transport(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    case = publication_case()
    token, key = signed_token(case, now - timedelta(minutes=10), valid_until=now - timedelta(minutes=5))
    transport = successful_transport()

    with pytest.raises(ConnectorBoundaryError, match="validity window"):
        connector(tmp_path, key).execute(
            action_case=case,
            signed_commit_token=token,
            transport=transport,
            receipt_id="receipt-publication-1",
            now=now,
        )

    assert transport.calls == []


def test_cross_case_token_blocks_before_signature_or_transport(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    case = publication_case()
    token, key = signed_token(case, now)
    token = copy.deepcopy(token)
    token["payload"]["action_id"] = "another-case"
    transport = successful_transport()

    with pytest.raises(ConnectorBoundaryError, match="action_id"):
        connector(tmp_path, key).execute(
            action_case=case,
            signed_commit_token=token,
            transport=transport,
            receipt_id="receipt-publication-1",
            now=now,
        )

    assert transport.calls == []


def test_provider_postcondition_mismatch_is_indeterminate(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    case = publication_case()
    token, key = signed_token(case, now)
    transport = successful_transport(channel_ref="youtube-channel:wrong")

    result = connector(tmp_path, key).execute(
        action_case=case,
        signed_commit_token=token,
        transport=transport,
        receipt_id="receipt-publication-1",
        now=now,
    )

    assert len(transport.calls) == 1
    assert result.provider_result is None
    assert result.receipt["payload"]["technical_outcome"] == "INDETERMINATE"
    assert result.receipt["payload"]["error_class"] == "IndeterminateProviderFailure"


def test_commit_token_is_single_use_and_cannot_duplicate_publication(tmp_path) -> None:
    now = datetime.now(timezone.utc)
    case = publication_case()
    token, key = signed_token(case, now)
    gate = connector(tmp_path, key)
    transport = successful_transport()

    gate.execute(
        action_case=case,
        signed_commit_token=token,
        transport=transport,
        receipt_id="receipt-publication-1",
        now=now,
    )
    with pytest.raises(ConnectorBoundaryError, match="already consumed"):
        gate.execute(
            action_case=case,
            signed_commit_token=token,
            transport=transport,
            receipt_id="receipt-publication-2",
            now=now,
        )

    assert len(transport.calls) == 1


def test_dry_run_is_network_free_and_does_not_require_clearance(tmp_path) -> None:
    _, key = signed_token(publication_case(), datetime.now(timezone.utc))
    case = publication_case()

    preview = connector(tmp_path, key).dry_run(case)

    assert preview.payload_digest == case.digest()
    assert preview.target_digest == case.target_digest()
    assert preview.privacy_status == PublicationPrivacy.PRIVATE


def test_wrong_provider_is_rejected_by_youtube_adapter(tmp_path) -> None:
    case = publication_case(provider="vimeo")
    _, key = signed_token(case, datetime.now(timezone.utc))

    with pytest.raises(ConnectorBoundaryError, match="cannot execute provider"):
        connector(tmp_path, key).dry_run(case)


def test_connector_has_no_evaluation_or_clearance_authority(tmp_path) -> None:
    _, key = signed_token(publication_case(), datetime.now(timezone.utc))
    adapter = connector(tmp_path, key)

    assert not hasattr(adapter, "evaluate")
    assert not hasattr(adapter, "issue_clearance")
    assert not hasattr(adapter, "grant_clearance")
