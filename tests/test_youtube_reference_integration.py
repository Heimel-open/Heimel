from __future__ import annotations

import ast
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest

from src.valo_platform.action_envelope.models import (
    ActionType,
    ConsequenceClass,
    PurposeRecordRef,
)
from src.valo_platform.connectors.content import PublicationDryRun
from src.valo_platform.content_operations import PublicationPrivacy
from src.valo_platform.decision_governance.action_case import (
    ActionCaseLifecycleState,
    ActionCaseRecord,
)
from src.valo_platform.decision_governance.models import ActionCaseStatus


EXAMPLE_PATH = (
    Path(__file__).parents[2]
    / "examples"
    / "integrations"
    / "youtube_shorts_pipeline"
    / "governed_upload.py"
)


def sha(char: str) -> str:
    return "sha256:" + char * 64


def load_example() -> ModuleType:
    module_name = "valo_youtube_shorts_governed_upload_example"
    spec = importlib.util.spec_from_file_location(module_name, EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def action_case() -> ActionCaseRecord:
    now = datetime.now(timezone.utc)
    return ActionCaseRecord(
        case_id="case-short-1",
        tenant_id="tenant-1",
        environment="test",
        record_version=1,
        case_hash=sha("1"),
        decision_state=ActionCaseStatus.READY_FOR_REHT,
        lifecycle_state=ActionCaseLifecycleState.SUBMITTED,
        purpose_record_ref=PurposeRecordRef(
            purpose_id="purpose-channel",
            version="1",
            record_ref="purpose:tenant-1:channel:1",
            fingerprint=sha("2"),
            established_by="human:publisher",
            authority_ref="authority:board:1",
            evidence_refs=["evidence:source:1"],
        ),
        purpose_binding_ref="purpose-binding:channel:1",
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
        created_at=now,
        updated_at=now,
    )


def assembled(module: ModuleType, **updates: object):
    payload: dict[str, object] = {
        "video_ref": "media:short:1",
        "video_digest": sha("5"),
        "title": "Who gave the machine the right?",
        "description": "A governed publication example.",
        "tags": ("reht", "governance"),
        "language": "en",
        "audiences": ("general",),
        "jurisdictions": ("NO",),
        "made_for_kids": False,
        "source_refs": ("evidence:source:1",),
        "claim_evidence_refs": ("evidence:claim:1",),
        "rights_evidence_refs": ("evidence:rights:1",),
        "thumbnail_ref": "media:thumbnail:1",
        "thumbnail_digest": sha("6"),
    }
    payload.update(updates)
    return module.AssembledShort(**payload)


def build_case(module: ModuleType, **assembled_updates: object):
    return module.build_publication_case(
        action_case_record=action_case(),
        assembled=assembled(module, **assembled_updates),
        principal_id="human:publisher",
        delegated_mandate_ref="mandate:tenant-1:publisher:1",
        account_ref="youtube-account:1",
        channel_ref="youtube-channel:1",
        policy_ref="policy:channel:1",
        policy_snapshot_digest=sha("7"),
        idempotency_key="short-publication-1",
    )


class RecordingConnector:
    def __init__(self) -> None:
        self.previewed = []
        self.executed = []

    def dry_run(self, publication_case):
        self.previewed.append(publication_case)
        publication = publication_case.publication
        return PublicationDryRun(
            action_id=publication_case.action_case.case_id,
            tenant_id=publication.tenant_id,
            provider=publication.provider,
            account_ref=publication.account_ref,
            channel_ref=publication.channel_ref,
            privacy_status=publication.privacy_status,
            payload_digest=publication_case.digest(),
            target_digest=publication_case.target_digest(),
            idempotency_key=publication.idempotency_key,
        )

    def execute(self, **kwargs):
        self.executed.append(kwargs)
        return {"receipt": "receipt-publication-1"}


class RecordingTransport:
    pass


def test_example_builds_exact_governed_publication_case() -> None:
    module = load_example()

    publication_case = build_case(module)

    assert publication_case.publication.provider == "youtube"
    assert publication_case.publication.account_ref == "youtube-account:1"
    assert publication_case.publication.channel_ref == "youtube-channel:1"
    assert publication_case.publication.privacy_status is PublicationPrivacy.PRIVATE
    assert publication_case.publication.video.digest == sha("5")
    assert publication_case.publication.thumbnail is not None
    assert publication_case.publication.thumbnail.digest == sha("6")
    assert publication_case.digest().startswith("sha256:")


def test_material_assembled_change_creates_new_clearance_digest() -> None:
    module = load_example()

    original = build_case(module)
    changed = build_case(module, title="Changed after assembly")

    assert original.digest() != changed.digest()


def test_preview_uses_connector_dry_run_without_execution() -> None:
    module = load_example()
    connector = RecordingConnector()
    publication_case = build_case(module)

    preview = module.preview_governed_upload(
        connector=connector,
        publication_case=publication_case,
    )

    assert connector.previewed == [publication_case]
    assert connector.executed == []
    assert preview.payload_digest == publication_case.digest()


def test_execute_routes_only_through_clearance_bound_connector() -> None:
    module = load_example()
    connector = RecordingConnector()
    transport = RecordingTransport()
    publication_case = build_case(module)
    token = {"artifact_type": "COMMIT_TOKEN", "payload": {"action_id": "case-short-1"}}
    now = datetime.now(timezone.utc)

    result = module.execute_governed_upload(
        connector=connector,
        publication_case=publication_case,
        signed_commit_token=token,
        transport=transport,
        receipt_id="receipt-publication-1",
        now=now,
    )

    assert result == {"receipt": "receipt-publication-1"}
    assert connector.previewed == []
    assert len(connector.executed) == 1
    call = connector.executed[0]
    assert call["action_case"] is publication_case
    assert call["signed_commit_token"] is token
    assert call["transport"] is transport
    assert call["receipt_id"] == "receipt-publication-1"
    assert call["now"] is now


def test_partial_optional_artifact_fails_closed() -> None:
    module = load_example()

    with pytest.raises(ValueError, match="both reference and digest"):
        build_case(module, thumbnail_digest=None)


def test_example_does_not_import_or_vendor_external_pipeline() -> None:
    source = EXAMPLE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules: set[str] = set()
    defined_functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.FunctionDef):
            defined_functions.add(node.name)

    assert not any("rushindrasinha" in name for name in imported_modules)
    assert not any("youtube_shorts_pipeline" in name for name in imported_modules)
    assert "upload_to_youtube" not in defined_functions


def test_example_has_no_clearance_issuance_or_policy_authority() -> None:
    module = load_example()

    assert not hasattr(module, "issue_clearance")
    assert not hasattr(module, "create_commit_token")
    assert not hasattr(module, "evaluate_policy")
    assert not hasattr(module, "upload_to_youtube")
