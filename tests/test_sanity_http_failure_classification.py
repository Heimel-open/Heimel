from __future__ import annotations

import httpx
import pytest

from src.valo_platform.connectors.content import (
    SanityDefiniteNoEffectError,
    SanityExecutionContext,
    SanityHttpClient,
    SanityHttpClientDisabled,
    SanityHttpConfigurationError,
    SanityHttpSettings,
    SanityMutationTransaction,
)
from src.valo_platform.content_operations import ContentOperation


class LeakingProvider:
    def get_token(self):
        raise RuntimeError("provider accidentally included secret-token-value")


class Resolver:
    def resolve(self, execution_id: str) -> SanityExecutionContext | None:
        del execution_id
        return None


def test_pre_dispatch_configuration_errors_are_definite_no_effect() -> None:
    assert issubclass(SanityHttpConfigurationError, SanityDefiniteNoEffectError)
    assert issubclass(SanityHttpClientDisabled, SanityDefiniteNoEffectError)


def test_credential_provider_exception_is_suppressed_and_no_request_occurs() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        del request
        calls += 1
        return httpx.Response(200)

    client = SanityHttpClient(
        settings=SanityHttpSettings(
            project_id="abc123",
            dataset="test_dataset",
            project_ref="project:products",
            dataset_ref="dataset:test",
            live_enabled=True,
        ),
        credential_provider=LeakingProvider(),
        context_resolver=Resolver(),
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    transaction = SanityMutationTransaction(
        project_ref="project:products",
        dataset_ref="dataset:test",
        transaction_id="exec-credential-failure",
        mutations=(
            {
                "patch": {
                    "id": "product-1",
                    "ifRevisionID": "rev-1",
                    "set": {"title": "changed"},
                }
            },
        ),
    )

    with pytest.raises(SanityHttpConfigurationError) as error:
        client.mutate(transaction)

    assert calls == 0
    assert error.value.__cause__ is None
    assert "secret-token-value" not in str(error.value)
    assert "secret-token-value" not in repr(error.value)
    assert isinstance(error.value, SanityDefiniteNoEffectError)
    assert transaction.mutations[0]["patch"]["set"]["title"] == "changed"
    assert ContentOperation.UPDATE_FIELD.value == "content.update_field"
