from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from src.valo_platform.action_envelope.bounded_connector import ConnectorBoundaryError
from src.valo_platform.connectors.content import (
    ContentMutationRequest,
    PersistedSanityExecutionContext,
    SanityCanaryActivation,
    SanityCanaryDeployment,
    SanityCanaryDeploymentError,
    SanityCanaryDeploymentProfile,
    SanityCanaryDurableMutationExecutor,
    SanityExecutionContextConflict,
    SanityExecutionContextCorrupt,
    SanityHttpConfigurationError,
    SanityPatchArtifact,
    SanitySchemaSnapshot,
    SanitySecretManagerCredentialProvider,
    SQLiteSanityExecutionContextStore,
)
from src.valo_platform.content_operations import ContentOperation
from tests.content_operations.test_cleared_content_mutation_connector import (
    make_case,
    make_policy,
    make_transport,
    sha,
)


NOW = datetime(2026, 8, 1, 5, 0, tzinfo=timezone.utc)
CONNECTOR_ID = "connector.content.sanity"
PROJECT_REF = "project:products"
DATASET_REF = "dataset:test"
SCHEMA_VERSION = "schema-v1"
DOCUMENT_ID = "product-1"
SOURCE_REVISION = "rev-source-1"
TOKEN = "sanity-live-token-value"


class SecretResolver:
    def __init__(self, token: str = TOKEN) -> None:
        self.token = token
        self.calls: list[str] = []

    def resolve_secret(self, secret_ref: str) -> SecretStr:
        self.calls.append(secret_ref)
        return SecretStr(self.token)


class FailingSecretResolver:
    def resolve_secret(self, secret_ref: str) -> SecretStr:
        del secret_ref
        raise RuntimeError("underlying-secret-manager-token-value")


class PatchResolver:
    def resolve(self, change_ref: str) -> SanityPatchArtifact:
        raise KeyError(change_ref)


class ValueResolver:
    def resolve(self, value_ref: str):
        raise KeyError(value_ref)


class ProviderClient:
    def mutate(self, transaction):
        raise AssertionError(transaction)

    def lookup_transaction(self, **kwargs):
        del kwargs
        return None


class FakeConnector:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def prepare(self, *, action_case, **kwargs):
        del kwargs
        self.calls += 1
        if self.fail:
            raise ConnectorBoundaryError("canonical prepare rejected action")
        return SimpleNamespace(
            connector_id=CONNECTOR_ID,
            capability=action_case.content.operation.value,
            target_digest=action_case.target_digest(),
            payload_digest=action_case.digest(),
            idempotency_key=action_case.content.idempotency_key,
            mutation=lambda execution_id: execution_id,
        )


class FakeDurableExecutor:
    def __init__(self, store: SQLiteSanityExecutionContextStore) -> None:
        self.store = store
        self.calls: list[dict] = []

    def execute(self, **kwargs):
        execution_id = kwargs["signed_commit_token"]["payload"]["execution_id"]
        assert self.store.resolve(execution_id) is not None
        self.calls.append(kwargs)
        return {"execution_id": execution_id, "replayed": False}


def profile(**updates) -> SanityCanaryDeploymentProfile:
    values = {
        "profile_id": "sanity-canary-profile-1",
        "environment": "canary",
        "tenant_id": "tenant-1",
        "connector_id": CONNECTOR_ID,
        "project_id": "abc123",
        "dataset": "test_dataset",
        "project_ref": PROJECT_REF,
        "dataset_ref": DATASET_REF,
        "schema_version": SCHEMA_VERSION,
        "allowed_document_ids": (DOCUMENT_ID,),
        "allowed_operations": (ContentOperation.UPDATE_FIELD,),
        "max_documents_per_transaction": 1,
        "secret_ref": "secret://sanity/canary/token",
        "expires_at": NOW + timedelta(hours=1),
    }
    values.update(updates)
    return SanityCanaryDeploymentProfile(**values)


def activation(
    deployment_profile: SanityCanaryDeploymentProfile,
    *,
    live: bool = False,
    writes: bool = False,
) -> SanityCanaryActivation:
    return SanityCanaryActivation(
        profile_digest=deployment_profile.digest(),
        live_enabled=live,
        writes_enabled=writes,
    )


def context(
    *,
    execution_id: str = "exec-sanity-context-1",
    project_ref: str = PROJECT_REF,
    change_digest: str = sha("a"),
    registered_at: datetime = NOW,
) -> PersistedSanityExecutionContext:
    return PersistedSanityExecutionContext.build(
        execution_id=execution_id,
        tenant_id="tenant-1",
        connector_id=CONNECTOR_ID,
        project_ref=project_ref,
        dataset_ref=DATASET_REF,
        operation=ContentOperation.UPDATE_FIELD,
        document_ids=(DOCUMENT_ID,),
        source_revisions=(SOURCE_REVISION,),
        proposed_change_digest=change_digest,
        payload_digest=sha("b"),
        target_digest=sha("c"),
        idempotency_key="sanity-product-1-v2",
        registered_at=registered_at,
    )


def deployment(
    tmp_path,
    *,
    live: bool = False,
    writes: bool = False,
    deployment_profile: SanityCanaryDeploymentProfile | None = None,
    resolver=None,
) -> SanityCanaryDeployment:
    selected_profile = deployment_profile or profile()
    return SanityCanaryDeployment(
        profile=selected_profile,
        activation=activation(selected_profile, live=live, writes=writes),
        secret_resolver=resolver or SecretResolver(),
        context_store=SQLiteSanityExecutionContextStore(tmp_path / "context.db"),
    )


def request(**updates) -> ContentMutationRequest:
    values = {
        "execution_id": "exec-sanity-context-1",
        "action_id": "case-sanity-context-1",
        "tenant_id": "tenant-1",
        "content_system": "sanity",
        "workspace_ref": "workspace:catalogue",
        "project_ref": PROJECT_REF,
        "dataset_ref": DATASET_REF,
        "operation": ContentOperation.UPDATE_FIELD,
        "record_ids": (DOCUMENT_ID,),
        "schema_version": SCHEMA_VERSION,
        "source_version_refs": (SOURCE_REVISION,),
        "target_version_refs": (),
        "content_snapshot_digest": sha("1"),
        "payload_digest": sha("2"),
        "target_digest": sha("3"),
        "state_binding_digest": sha("4"),
        "proposed_change_ref": "change:product-1:v2",
        "proposed_change_digest": sha("5"),
        "idempotency_key": "sanity-product-1-v2",
    }
    values.update(updates)
    return ContentMutationRequest(**values)


def sanity_case():
    transport = make_transport()
    policy = make_policy(NOW)
    action_case = make_case(policy=policy, transport=transport)
    content = action_case.content.model_copy(
        update={
            "content_system": "sanity",
            "project_ref": PROJECT_REF,
            "dataset_ref": DATASET_REF,
            "record_ids": (DOCUMENT_ID,),
            "schema_version": SCHEMA_VERSION,
            "source_version_refs": (SOURCE_REVISION,),
            "target_version_refs": (),
            "content_snapshot_digest": sha("1"),
        }
    )
    return action_case.model_copy(update={"content": content})


def schema() -> SanitySchemaSnapshot:
    return SanitySchemaSnapshot(
        project_ref=PROJECT_REF,
        dataset_ref=DATASET_REF,
        schema_version=SCHEMA_VERSION,
        schema_digest=sha("6"),
        document_types=("product",),
        schema_refs=("schema:product:v1",),
    )


def test_context_survives_restart_and_resolves_existing_http_contract(tmp_path) -> None:
    path = tmp_path / "nested" / "context.db"
    first = SQLiteSanityExecutionContextStore(path)
    first.register(context())

    restarted = SQLiteSanityExecutionContextStore(path)
    resolved = restarted.resolve("exec-sanity-context-1")

    assert resolved is not None
    assert resolved.operation is ContentOperation.UPDATE_FIELD
    assert resolved.document_ids == (DOCUMENT_ID,)
    assert resolved.source_revisions == (SOURCE_REVISION,)
    assert resolved.proposed_change_digest == sha("a")
    assert restarted.count() == 1


def test_exact_context_reregistration_is_idempotent(tmp_path) -> None:
    store = SQLiteSanityExecutionContextStore(tmp_path / "context.db")
    original = store.register(context())
    replay = store.register(
        context(registered_at=NOW + timedelta(minutes=5))
    )

    assert replay.context_digest == original.context_digest
    assert replay.registered_at == original.registered_at
    assert store.count() == 1


def test_conflicting_execution_identity_fails_closed(tmp_path) -> None:
    store = SQLiteSanityExecutionContextStore(tmp_path / "context.db")
    store.register(context())

    with pytest.raises(SanityExecutionContextConflict, match="execution ID"):
        store.register(context(project_ref="project:other"))

    assert store.count() == 1


def test_tampered_persisted_row_fails_closed(tmp_path) -> None:
    path = tmp_path / "context.db"
    store = SQLiteSanityExecutionContextStore(path)
    store.register(context())
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE sanity_execution_contexts SET document_ids_json=? WHERE execution_id=?",
            (json.dumps(["attacker-document"]), "exec-sanity-context-1"),
        )

    with pytest.raises(SanityExecutionContextCorrupt, match="tampered|digest"):
        store.get("exec-sanity-context-1")


def test_context_database_contains_no_content_token_or_secret_reference(tmp_path) -> None:
    path = tmp_path / "context.db"
    store = SQLiteSanityExecutionContextStore(path)
    store.register(context())

    raw = path.read_bytes()
    assert TOKEN.encode() not in raw
    assert b"secret://sanity" not in raw
    assert b"New title" not in raw
    assert b"commit_token" not in raw


def test_secret_manager_provider_resolves_fresh_secret_without_exposure() -> None:
    resolver = SecretResolver()
    provider = SanitySecretManagerCredentialProvider(
        secret_ref="secret://sanity/canary/token",
        resolver=resolver,
    )

    first = provider.get_token()
    second = provider.get_token()

    assert first.get_secret_value() == TOKEN
    assert second.get_secret_value() == TOKEN
    assert len(resolver.calls) == 2
    assert TOKEN not in repr(provider)
    assert "secret://sanity/canary/token" not in repr(provider)


def test_secret_manager_failure_suppresses_underlying_exception_chain() -> None:
    provider = SanitySecretManagerCredentialProvider(
        secret_ref="secret://sanity/canary/token",
        resolver=FailingSecretResolver(),
    )

    with pytest.raises(SanityHttpConfigurationError) as error:
        provider.get_token()

    assert error.value.__cause__ is None
    assert "underlying-secret-manager-token-value" not in str(error.value)


def test_default_activation_denies_live_and_writes(tmp_path) -> None:
    configured = deployment(tmp_path)

    with pytest.raises(SanityCanaryDeploymentError, match="live"):
        configured.build_http_client(now=NOW)
    with pytest.raises(SanityCanaryDeploymentError, match="live|writes"):
        configured.build_mutation_transport(
            client=ProviderClient(),
            patch_resolver=PatchResolver(),
            value_resolver=ValueResolver(),
            schema=schema(),
            now=NOW,
        )


def test_live_only_activation_can_build_client_but_cannot_write(tmp_path) -> None:
    resolver = SecretResolver()
    configured = deployment(tmp_path, live=True, resolver=resolver)
    http_client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(404)),
        trust_env=False,
    )
    client = configured.build_http_client(http_client=http_client, now=NOW)

    assert TOKEN not in repr(client)
    assert resolver.calls == []
    with pytest.raises(SanityCanaryDeploymentError, match="writes"):
        configured.build_mutation_transport(
            client=ProviderClient(),
            patch_resolver=PatchResolver(),
            value_resolver=ValueResolver(),
            schema=schema(),
            now=NOW,
        )


def test_writes_only_activation_cannot_construct_live_client(tmp_path) -> None:
    configured = deployment(tmp_path, writes=True)

    with pytest.raises(SanityCanaryDeploymentError, match="live"):
        configured.build_http_client(now=NOW)


def test_both_activation_switches_build_independently_gated_transport(tmp_path) -> None:
    configured = deployment(tmp_path, live=True, writes=True)

    transport = configured.build_mutation_transport(
        client=ProviderClient(),
        patch_resolver=PatchResolver(),
        value_resolver=ValueResolver(),
        schema=schema(),
        now=NOW,
    )

    assert transport.writes_enabled is True


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"tenant_id": "tenant-other"}, "scope"),
        ({"project_ref": "project:other"}, "scope"),
        ({"dataset_ref": "dataset:other"}, "scope"),
        ({"schema_version": "schema-v2"}, "scope"),
        ({"content_system": "other-cms"}, "Sanity"),
        ({"operation": ContentOperation.PUBLISH}, "operation"),
        ({"record_ids": ("outside-canary",)}, "allowlist"),
        (
            {
                "record_ids": (DOCUMENT_ID, "product-2"),
                "source_version_refs": (SOURCE_REVISION, "rev-source-2"),
            },
            "cardinality",
        ),
    ],
)
def test_canary_scope_mismatches_fail_before_provider_dispatch(
    tmp_path, updates, message
) -> None:
    configured = deployment(tmp_path, live=True, writes=True)

    with pytest.raises(SanityCanaryDeploymentError, match=message):
        configured.require_write_request(
            request(**updates),
            connector_id=CONNECTOR_ID,
            now=NOW,
        )


def test_expired_or_wrong_profile_activation_fails_closed(tmp_path) -> None:
    expired_profile = profile(expires_at=NOW)
    expired = SanityCanaryDeployment(
        profile=expired_profile,
        activation=activation(expired_profile, live=True, writes=True),
        secret_resolver=SecretResolver(),
        context_store=SQLiteSanityExecutionContextStore(tmp_path / "expired.db"),
    )
    wrong = SanityCanaryDeployment(
        profile=profile(),
        activation=SanityCanaryActivation(
            profile_digest=sha("f"),
            live_enabled=True,
            writes_enabled=True,
        ),
        secret_resolver=SecretResolver(),
        context_store=SQLiteSanityExecutionContextStore(tmp_path / "wrong.db"),
    )

    with pytest.raises(SanityCanaryDeploymentError, match="expired"):
        expired.require_write_request(request(), connector_id=CONNECTOR_ID, now=NOW)
    with pytest.raises(SanityCanaryDeploymentError, match="bind"):
        wrong.require_write_request(request(), connector_id=CONNECTOR_ID, now=NOW)


def test_failed_prepare_does_not_persist_execution_context(tmp_path) -> None:
    configured = deployment(tmp_path, live=True, writes=True)
    connector = FakeConnector(fail=True)
    durable = FakeDurableExecutor(configured.context_store)
    executor = SanityCanaryDurableMutationExecutor(
        connector=connector,  # type: ignore[arg-type]
        durable_executor=durable,  # type: ignore[arg-type]
        deployment=configured,
    )

    with pytest.raises(ConnectorBoundaryError, match="prepare"):
        executor.execute(
            action_case=sanity_case(),
            signed_commit_token={"payload": {"execution_id": "exec-prepare-fail"}},
            integrity_baseline=object(),
            integrity_checkpoint=object(),
            transport=object(),  # type: ignore[arg-type]
            receipt_id="receipt-prepare-fail",
            now=NOW,
        )

    assert configured.context_store.count() == 0
    assert durable.calls == []


def test_successful_prepare_persists_context_before_canonical_durable_call(tmp_path) -> None:
    configured = deployment(tmp_path, live=True, writes=True)
    connector = FakeConnector()
    durable = FakeDurableExecutor(configured.context_store)
    executor = SanityCanaryDurableMutationExecutor(
        connector=connector,  # type: ignore[arg-type]
        durable_executor=durable,  # type: ignore[arg-type]
        deployment=configured,
    )
    action_case = sanity_case()

    result = executor.execute(
        action_case=action_case,
        signed_commit_token={"payload": {"execution_id": "exec-context-before-journal"}},
        integrity_baseline=object(),
        integrity_checkpoint=object(),
        transport=object(),  # type: ignore[arg-type]
        receipt_id="receipt-context-before-journal",
        now=NOW,
    )

    stored = configured.context_store.get("exec-context-before-journal")
    assert connector.calls == 1
    assert len(durable.calls) == 1
    assert stored.tenant_id == "tenant-1"
    assert stored.connector_id == CONNECTOR_ID
    assert stored.document_ids == (DOCUMENT_ID,)
    assert stored.source_revisions == (SOURCE_REVISION,)
    assert stored.payload_digest == action_case.digest()
    assert result["execution_id"] == "exec-context-before-journal"


def test_persistent_context_supports_history_lookup_after_restart(tmp_path) -> None:
    path = tmp_path / "restart.db"
    first_store = SQLiteSanityExecutionContextStore(path)
    first_store.register(context(execution_id="exec-history-restart"))
    restarted_store = SQLiteSanityExecutionContextStore(path)
    selected_profile = profile()
    resolver = SecretResolver()
    configured = SanityCanaryDeployment(
        profile=selected_profile,
        activation=activation(selected_profile, live=True),
        secret_resolver=resolver,
        context_store=restarted_store,
    )
    history = {
        "id": "exec-history-restart",
        "timestamp": "2026-08-01T05:01:00Z",
        "mutations": [
            {
                "patch": {
                    "id": DOCUMENT_ID,
                    "ifRevisionID": SOURCE_REVISION,
                }
            }
        ],
        "documentIDs": [DOCUMENT_ID],
    }

    def handler(http_request: httpx.Request) -> httpx.Response:
        assert http_request.method == "GET"
        assert http_request.url.params["excludeContent"] == "true"
        return httpx.Response(
            200,
            content=(json.dumps(history) + "\n").encode(),
            headers={"content-type": "application/x-ndjson"},
        )

    client = configured.build_http_client(
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            trust_env=False,
        ),
        now=NOW,
    )
    evidence = client.lookup_transaction(
        project_ref=PROJECT_REF,
        dataset_ref=DATASET_REF,
        transaction_id="exec-history-restart",
    )

    assert evidence is not None
    assert evidence.document_ids == (DOCUMENT_ID,)
    assert evidence.previous_revisions == (SOURCE_REVISION,)
    assert evidence.proposed_change_digest == sha("a")
    assert resolver.calls == ["secret://sanity/canary/token"]
