from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.action_envelope.models import (
    ActionType,
    ConsequenceClass,
    PurposeRecordRef,
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


def action_case(
    *,
    tenant_id: str = "tenant-1",
    action_class: ActionType = ActionType.EXTERNAL_PUBLICATION,
) -> ActionCaseRecord:
    now = datetime.now(timezone.utc)
    purpose = PurposeRecordRef(
        purpose_id="purpose-content",
        version="1",
        record_ref="purpose:tenant-1:content:1",
        fingerprint=sha("1"),
        established_by="human:publisher",
        authority_ref="authority:board:1",
        evidence_refs=["evidence:source:1"],
    )
    evidence_refs = (
        "evidence:source:1",
        "evidence:claim:1",
        "evidence:rights:1",
    )
    return ActionCaseRecord(
        case_id="case-publication-1",
        tenant_id=tenant_id,
        environment="test",
        record_version=1,
        case_hash=sha("2"),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.SUBMITTED,
        purpose_record_ref=purpose,
        purpose_binding_ref="purpose-binding:content:1",
        mandate_ref="mandate:tenant-1:publisher:1",
        mandate_fingerprint=sha("3"),
        evidence_refs=evidence_refs,
        evidence_fingerprint=sha("4"),
        action_class=action_class,
        consequence_class=ConsequenceClass.C2_MEDIUM,
        created_at=now,
        updated_at=now,
    )


def publication(**updates: object) -> PublicationAction:
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
        "tags": ("reht", "governance"),
        "language": "en",
        "audiences": ("general",),
        "jurisdictions": ("NO",),
        "privacy_status": PublicationPrivacy.PRIVATE,
        "made_for_kids": False,
        "captions": (
            PublicationArtifact(
                artifact_ref="media:captions:1",
                digest=sha("6"),
                media_type="text/srt",
            ),
        ),
        "thumbnail": PublicationArtifact(
            artifact_ref="media:thumbnail:1",
            digest=sha("7"),
            media_type="image/png",
        ),
        "source_refs": ("evidence:source:1",),
        "claim_evidence_refs": ("evidence:claim:1",),
        "rights_evidence_refs": ("evidence:rights:1",),
        "policy_refs": ("policy:channel:1",),
        "policy_snapshot_digest": sha("8"),
        "rollback_capability": PublicationRollback.UNPUBLISH,
        "idempotency_key": "publication-1",
    }
    payload.update(updates)
    return PublicationAction.model_validate(payload)


def test_digest_is_deterministic_and_normalizes_unordered_refs() -> None:
    first = publication(tags=("reht", "governance"), jurisdictions=("NO", "EU"))
    second = publication(tags=("governance", "reht"), jurisdictions=("EU", "NO"))

    assert first.digest() == second.digest()
    assert first.tags == ("governance", "reht")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "Changed title"),
        ("privacy_status", PublicationPrivacy.PUBLIC),
        (
            "video",
            PublicationArtifact(
                artifact_ref="media:video:2",
                digest=sha("9"),
                media_type="video/mp4",
            ),
        ),
        ("policy_snapshot_digest", sha("a")),
    ],
)
def test_material_change_invalidates_payload_digest(field: str, value: object) -> None:
    original = publication()
    changed = original.model_copy(update={field: value})

    assert original.digest() != changed.digest()


def test_target_digest_binds_destination_not_metadata() -> None:
    original = publication()
    changed_title = original.model_copy(update={"title": "Another title"})
    changed_channel = original.model_copy(update={"channel_ref": "youtube-channel:2"})

    assert original.target_digest() == changed_title.target_digest()
    assert original.target_digest() != changed_channel.target_digest()


def test_publication_composes_with_canonical_action_case() -> None:
    bound = PublicationActionCase(
        action_case=action_case(),
        publication=publication(),
    )

    assert bound.digest().startswith("sha256:")
    assert bound.canonical_payload()["action_case_ref"]["case_hash"] == sha("2")


def test_non_publication_action_case_fails_closed() -> None:
    with pytest.raises(ValidationError, match="EXTERNAL_PUBLICATION"):
        PublicationActionCase(
            action_case=action_case(action_class=ActionType.SEND_EMAIL),
            publication=publication(),
        )


def test_cross_tenant_binding_fails_closed() -> None:
    with pytest.raises(ValidationError, match="tenant"):
        PublicationActionCase(
            action_case=action_case(tenant_id="tenant-2"),
            publication=publication(),
        )


def test_missing_action_case_evidence_fails_closed() -> None:
    with pytest.raises(ValidationError, match="does not bind canonical"):
        PublicationActionCase(
            action_case=action_case(),
            publication=publication(rights_evidence_refs=("evidence:rights:other",)),
        )


def test_unknown_fields_are_rejected() -> None:
    payload = publication().model_dump(mode="python")
    payload["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PublicationAction.model_validate(payload)


def test_invalid_digest_is_rejected() -> None:
    with pytest.raises(ValidationError, match="digest must be lowercase"):
        publication(policy_snapshot_digest="sha256:not-valid")


def test_naive_schedule_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        publication(scheduled_for=datetime(2026, 8, 1, 10, 0, 0))
