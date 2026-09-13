from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from src.valo_platform.connectors.content import (
    SanityDefiniteNoEffectError,
    SanityExecutionContext,
    SanityHistoryLookupError,
    SanityHttpClient,
    SanityHttpClientDisabled,
    SanityHttpConfigurationError,
    SanityHttpSettings,
    SanityMutationTransaction,
    SanityTransactionStatus,
    SanityUnknownEffectError,
)
from src.valo_platform.content_operations import ContentOperation


TOKEN = "sanity-secret-token-value"
TRANSACTION_ID = "exec-sanity-http-1"
PROJECT_REF = "project:products"
DATASET_REF = "dataset:test"
DOCUMENT_ID = "product-1"
SOURCE_REVISION = "rev-source-1"
CHANGE_DIGEST = "sha256:" + "a" * 64


class CredentialProvider:
    def __init__(self, token: str = TOKEN) -> None:
        self._token = token
        self.calls = 0

    def get_token(self) -> SecretStr:
        self.calls += 1
        return SecretStr(self._token)

    def __repr__(self) -> str:
        return "CredentialProvider(***)"


class BadCredentialProvider:
    def get_token(self):
        return TOKEN


class ContextResolver:
    def __init__(self, context: SanityExecutionContext | None = None) -> None:
        self.context = context or SanityExecutionContext(
            operation=ContentOperation.UPDATE_FIELD,
            document_ids=(DOCUMENT_ID,),
            source_revisions=(SOURCE_REVISION,),
            proposed_change_digest=CHANGE_DIGEST,
        )
        self.calls: list[str] = []

    def resolve(self, execution_id: str) -> SanityExecutionContext | None:
        self.calls.append(execution_id)
        return self.context


class MissingContextResolver:
    def resolve(self, execution_id: str) -> None:
        del execution_id
        return None


def settings(**overrides) -> SanityHttpSettings:
    values = {
        "project_id": "abc123",
        "dataset": "test_dataset",
        "project_ref": PROJECT_REF,
        "dataset_ref": DATASET_REF,
        "live_enabled": True,
    }
    values.update(overrides)
    return SanityHttpSettings(**values)


def transaction() -> SanityMutationTransaction:
    return SanityMutationTransaction(
        project_ref=PROJECT_REF,
        dataset_ref=DATASET_REF,
        transaction_id=TRANSACTION_ID,
        mutations=(
            {
                "patch": {
                    "id": DOCUMENT_ID,
                    "ifRevisionID": SOURCE_REVISION,
                    "set": {"title": "New title"},
                }
            },
        ),
        visibility="sync",
        return_ids=True,
        dry_run=False,
    )


def success_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "transactionId": TRANSACTION_ID,
            "results": [{"operation": "update", "documentId": DOCUMENT_ID}],
        },
    )


def build_client(handler, **setting_overrides) -> tuple[SanityHttpClient, CredentialProvider]:
    credentials = CredentialProvider()
    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
        trust_env=False,
    )
    return (
        SanityHttpClient(
            settings=settings(**setting_overrides),
            credential_provider=credentials,
            context_resolver=ContextResolver(),
            http_client=http_client,
        ),
        credentials,
    )


def test_client_construction_requires_explicit_live_enablement() -> None:
    with pytest.raises(SanityHttpClientDisabled, match="live_enabled"):
        SanityHttpClient(
            settings=settings(live_enabled=False),
            credential_provider=CredentialProvider(),
            context_resolver=ContextResolver(),
        )


def test_settings_reject_invalid_provider_coordinates() -> None:
    with pytest.raises(ValidationError, match="project ID"):
        settings(project_id="https://attacker.example")
    with pytest.raises(ValidationError, match="dataset"):
        settings(dataset="../secret")
    with pytest.raises(ValidationError, match="api_version"):
        settings(api_version="latest")


def test_credential_must_be_secretstr_before_dispatch() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return success_response()

    client = SanityHttpClient(
        settings=settings(),
        credential_provider=BadCredentialProvider(),
        context_resolver=ContextResolver(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(SanityHttpConfigurationError, match="SecretStr") as error:
        client.mutate(transaction())

    assert calls == 0
    assert TOKEN not in str(error.value)
    assert TOKEN not in repr(error.value)


def test_mutation_wire_contract_is_exact_and_reference_only() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "POST"
        assert request.url.scheme == "https"
        assert request.url.host == "abc123.api.sanity.io"
        assert request.url.path == "/v2025-02-19/data/mutate/test_dataset"
        assert dict(request.url.params) == {
            "returnIds": "true",
            "returnDocuments": "false",
            "transactionId": TRANSACTION_ID,
            "visibility": "sync",
            "dryRun": "false",
        }
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        assert json.loads(request.content) == {
            "mutations": [
                {
                    "patch": {
                        "id": DOCUMENT_ID,
                        "ifRevisionID": SOURCE_REVISION,
                        "set": {"title": "New title"},
                    }
                }
            ]
        }
        return success_response()

    client, credentials = build_client(handler)
    result = client.mutate(transaction())

    assert len(requests) == 1
    assert credentials.calls == 1
    assert result.transaction_id == TRANSACTION_ID
    assert result.document_ids == (DOCUMENT_ID,)
    assert result.previous_revisions == (SOURCE_REVISION,)
    assert result.current_revisions == (TRANSACTION_ID,)
    assert result.provider_reference == f"sanity:transaction:{TRANSACTION_ID}"
    serialized = result.model_dump_json()
    assert TOKEN not in repr(client)
    assert TOKEN not in serialized
    assert "New title" not in serialized


def test_409_is_definite_no_effect_and_never_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        del request
        calls += 1
        return httpx.Response(409, json={"error": "conflict"})

    client, _ = build_client(handler)
    with pytest.raises(SanityDefiniteNoEffectError, match="no effect"):
        client.mutate(transaction())

    assert calls == 1


def test_timeout_is_unknown_effect_and_never_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout", request=request)

    client, _ = build_client(handler)
    with pytest.raises(SanityUnknownEffectError, match="unknown|dispatch"):
        client.mutate(transaction())

    assert calls == 1


def test_5xx_is_unknown_effect_and_never_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        del request
        calls += 1
        return httpx.Response(503, json={"error": "unavailable"})

    client, _ = build_client(handler)
    with pytest.raises(SanityUnknownEffectError, match="503"):
        client.mutate(transaction())

    assert calls == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"transactionId": "wrong", "results": []}),
        httpx.Response(
            200,
            json={
                "transactionId": TRANSACTION_ID,
                "results": [{"operation": "update", "documentId": "other"}],
            },
        ),
    ],
)
def test_malformed_success_is_unknown_effect(response: httpx.Response) -> None:
    client, _ = build_client(lambda request: response)

    with pytest.raises(SanityUnknownEffectError):
        client.mutate(transaction())


def test_oversized_success_is_unknown_effect() -> None:
    client, _ = build_client(
        lambda request: httpx.Response(200, content=b"x" * 2048),
        max_response_bytes=1024,
    )

    with pytest.raises(SanityUnknownEffectError, match="size limit"):
        client.mutate(transaction())


def test_history_lookup_excludes_content_and_returns_sanitized_evidence() -> None:
    requests: list[httpx.Request] = []
    raw_history = {
        "id": TRANSACTION_ID,
        "timestamp": "2026-08-01T04:30:00Z",
        "author": "provider-user",
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

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "GET"
        assert request.url.path == (
            "/v2025-02-19/data/history/test_dataset/transactions/product-1"
        )
        assert dict(request.url.params) == {
            "excludeContent": "true",
            "fromTransaction": TRANSACTION_ID,
            "toTransaction": TRANSACTION_ID,
            "limit": "2",
            "includeIdentifiedDocumentsOnly": "true",
        }
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        return httpx.Response(
            200,
            content=(json.dumps(raw_history) + "\n").encode("utf-8"),
            headers={"content-type": "application/x-ndjson"},
        )

    client, _ = build_client(handler)
    evidence = client.lookup_transaction(
        project_ref=PROJECT_REF,
        dataset_ref=DATASET_REF,
        transaction_id=TRANSACTION_ID,
    )

    assert len(requests) == 1
    assert evidence is not None
    assert evidence.status is SanityTransactionStatus.COMMITTED
    assert evidence.document_ids == (DOCUMENT_ID,)
    assert evidence.previous_revisions == (SOURCE_REVISION,)
    assert evidence.current_revisions == (TRANSACTION_ID,)
    assert evidence.proposed_change_digest == CHANGE_DIGEST
    assert evidence.observed_at == datetime(2026, 8, 1, 4, 30, tzinfo=timezone.utc)
    serialized = evidence.model_dump_json()
    assert TOKEN not in serialized
    assert "provider-user" not in serialized
    assert "New title" not in serialized
    assert evidence.response == {
        "status": "committed",
        "transaction_id": TRANSACTION_ID,
        "content_excluded": True,
    }


def test_unknown_history_transaction_returns_none() -> None:
    client, _ = build_client(
        lambda request: httpx.Response(
            200,
            content=b'{"id":"different","timestamp":"2026-08-01T04:30:00Z"}\n',
        )
    )

    assert (
        client.lookup_transaction(
            project_ref=PROJECT_REF,
            dataset_ref=DATASET_REF,
            transaction_id=TRANSACTION_ID,
        )
        is None
    )


def test_missing_canonical_context_returns_unknown_without_network() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        del request
        calls += 1
        return httpx.Response(500)

    client = SanityHttpClient(
        settings=settings(),
        credential_provider=CredentialProvider(),
        context_resolver=MissingContextResolver(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert (
        client.lookup_transaction(
            project_ref=PROJECT_REF,
            dataset_ref=DATASET_REF,
            transaction_id=TRANSACTION_ID,
        )
        is None
    )
    assert calls == 0


def test_history_scope_mismatch_fails_before_network() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        del request
        calls += 1
        return httpx.Response(200)

    client, _ = build_client(handler)
    with pytest.raises(SanityHistoryLookupError, match="scope"):
        client.lookup_transaction(
            project_ref="project:other",
            dataset_ref=DATASET_REF,
            transaction_id=TRANSACTION_ID,
        )

    assert calls == 0


def test_client_source_has_no_environment_read_or_retry_loop() -> None:
    source = Path(
        "src/valo_platform/connectors/content/sanity_http.py"
    ).read_text(encoding="utf-8")

    assert "os.getenv" not in source
    assert "os.environ" not in source
    assert "retries=0" in source
    assert "for attempt" not in source
    assert "while True" not in source
    assert "Authorization" in source
    assert "returnDocuments\": \"false" in source
