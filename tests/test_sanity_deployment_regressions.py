from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.connectors.content import (
    ContentMutationRequest,
    SanityCanaryActivation,
    SanityCanaryDeployment,
    SanityCanaryDeploymentError,
    SanityCanaryDeploymentProfile,
    SQLiteSanityExecutionContextStore,
)
from src.valo_platform.content_operations import ContentOperation


NOW = datetime(2026, 8, 1, 5, 0, tzinfo=timezone.utc)


class SecretResolver:
    def resolve_secret(self, secret_ref):
        raise AssertionError(secret_ref)


def sha(char: str) -> str:
    return "sha256:" + char * 64


def test_every_context_connection_reapplies_durable_pragmas(tmp_path) -> None:
    store = SQLiteSanityExecutionContextStore(tmp_path / "context.db")

    with store._connect() as connection:
        synchronous = connection.execute("PRAGMA synchronous").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        busy_timeout = connection.execute("PRAGMA busy_timeout").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert synchronous == 2
    assert foreign_keys == 1
    assert busy_timeout == 5000
    assert str(journal_mode).lower() == "wal"


def test_allowlist_size_is_independent_of_per_transaction_limit(tmp_path) -> None:
    profile = SanityCanaryDeploymentProfile(
        profile_id="sanity-canary-many-allowed",
        tenant_id="tenant-1",
        connector_id="connector.content.sanity",
        project_id="abc123",
        dataset="test_dataset",
        project_ref="project:products",
        dataset_ref="dataset:test",
        schema_version="schema-v1",
        allowed_document_ids=("product-1", "product-2", "product-3"),
        allowed_operations=(ContentOperation.UPDATE_FIELD,),
        max_documents_per_transaction=1,
        secret_ref="secret://sanity/canary/token",
        expires_at=NOW + timedelta(hours=1),
    )
    deployment = SanityCanaryDeployment(
        profile=profile,
        activation=SanityCanaryActivation(
            profile_digest=profile.digest(),
            live_enabled=True,
            writes_enabled=True,
        ),
        secret_resolver=SecretResolver(),
        context_store=SQLiteSanityExecutionContextStore(tmp_path / "context.db"),
    )
    request = ContentMutationRequest(
        execution_id="exec-cardinality-regression",
        action_id="case-cardinality-regression",
        tenant_id="tenant-1",
        content_system="sanity",
        workspace_ref="workspace:catalogue",
        project_ref="project:products",
        dataset_ref="dataset:test",
        operation=ContentOperation.UPDATE_FIELD,
        record_ids=("product-1", "product-2"),
        schema_version="schema-v1",
        source_version_refs=("rev-1", "rev-2"),
        target_version_refs=(),
        content_snapshot_digest=sha("1"),
        payload_digest=sha("2"),
        target_digest=sha("3"),
        state_binding_digest=sha("4"),
        proposed_change_ref="change:products:v2",
        proposed_change_digest=sha("5"),
        idempotency_key="products-v2",
    )

    with pytest.raises(SanityCanaryDeploymentError, match="cardinality"):
        deployment.require_write_request(
            request,
            connector_id="connector.content.sanity",
            now=NOW,
        )
