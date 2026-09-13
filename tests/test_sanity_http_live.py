from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from src.valo_platform.connectors.content import (
    SanityExecutionContext,
    SanityHttpClient,
    SanityHttpSettings,
)
from src.valo_platform.content_operations import ContentOperation


class EnvironmentCredentialProvider:
    """Test-only adapter; production clients receive a deployment secret provider."""

    def get_token(self) -> SecretStr:
        return SecretStr(os.environ["VALO_SANITY_TOKEN"])


class EnvironmentContextResolver:
    def resolve(self, execution_id: str) -> SanityExecutionContext | None:
        if execution_id != os.environ["VALO_SANITY_TRANSACTION_ID"]:
            return None
        return SanityExecutionContext(
            operation=ContentOperation(os.environ["VALO_SANITY_OPERATION"]),
            document_ids=(os.environ["VALO_SANITY_DOCUMENT_ID"],),
            source_revisions=(os.environ["VALO_SANITY_SOURCE_REVISION"],),
            proposed_change_digest=os.environ["VALO_SANITY_CHANGE_DIGEST"],
        )


_REQUIRED = (
    "VALO_SANITY_PROJECT_ID",
    "VALO_SANITY_DATASET",
    "VALO_SANITY_PROJECT_REF",
    "VALO_SANITY_DATASET_REF",
    "VALO_SANITY_TOKEN",
    "VALO_SANITY_TRANSACTION_ID",
    "VALO_SANITY_DOCUMENT_ID",
    "VALO_SANITY_SOURCE_REVISION",
    "VALO_SANITY_CHANGE_DIGEST",
    "VALO_SANITY_OPERATION",
)


@pytest.mark.live_sanity
def test_opt_in_history_smoke_is_read_only_and_explicitly_gated() -> None:
    if os.environ.get("VALO_SANITY_LIVE_TESTS") != "1":
        pytest.skip("Sanity live smoke is disabled")
    missing = [name for name in _REQUIRED if not os.environ.get(name)]
    if missing:
        pytest.skip("Sanity live smoke missing explicit inputs: " + ", ".join(missing))

    settings = SanityHttpSettings(
        project_id=os.environ["VALO_SANITY_PROJECT_ID"],
        dataset=os.environ["VALO_SANITY_DATASET"],
        project_ref=os.environ["VALO_SANITY_PROJECT_REF"],
        dataset_ref=os.environ["VALO_SANITY_DATASET_REF"],
        api_version=os.environ.get("VALO_SANITY_API_VERSION", "v2025-02-19"),
        live_enabled=True,
    )
    with SanityHttpClient(
        settings=settings,
        credential_provider=EnvironmentCredentialProvider(),
        context_resolver=EnvironmentContextResolver(),
    ) as client:
        evidence = client.lookup_transaction(
            project_ref=settings.project_ref,
            dataset_ref=settings.dataset_ref,
            transaction_id=os.environ["VALO_SANITY_TRANSACTION_ID"],
        )

    assert evidence is not None
    assert evidence.transaction_id == os.environ["VALO_SANITY_TRANSACTION_ID"]
    assert evidence.response["content_excluded"] is True
