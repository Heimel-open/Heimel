"""Opt-in Sanity HTTP client behind the governed content provider protocol.

This module performs provider I/O only. It does not evaluate policy, issue
clearance, mint or consume CommitTokens, retry mutations, write execution state,
or issue receipts. Credentials are resolved per request through an injected
provider and are never stored in models or returned evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import quote

import httpx
import rfc8785
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from src.valo_platform.content_operations.actions import ContentOperation

from .sanity_mutation import (
    SanityDefiniteNoEffectError,
    SanityMutationResponse,
    SanityMutationTransaction,
    SanityTransactionEvidence,
    SanityTransactionStatus,
    SanityUnknownEffectError,
)


_PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_DATASET_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_API_VERSION_RE = re.compile(r"^v\d{4}-\d{2}-\d{2}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


class SanityHttpConfigurationError(SanityDefiniteNoEffectError):
    """Configuration or credentials failed before provider dispatch."""


class SanityHttpClientDisabled(SanityHttpConfigurationError):
    """Live provider construction was not explicitly enabled."""


class SanityHistoryLookupError(RuntimeError):
    """Read-only history lookup could not produce authoritative evidence."""


class SanityCredentialProvider(Protocol):
    """Resolve a current provider token without exposing it through configuration."""

    def get_token(self) -> SecretStr: ...


@dataclass(frozen=True)
class SanityExecutionContext:
    """Canonical local context required to interpret reference-only history."""

    operation: ContentOperation
    document_ids: tuple[str, ...]
    source_revisions: tuple[str, ...]
    proposed_change_digest: str

    def __post_init__(self) -> None:
        if not self.document_ids or len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("Sanity execution context requires unique document IDs")
        if len(self.document_ids) != len(self.source_revisions):
            raise ValueError("Sanity execution context revision cardinality mismatch")
        if not _SHA256_RE.fullmatch(self.proposed_change_digest):
            raise ValueError("proposed_change_digest must be lowercase sha256:<64 hex>")


class SanityExecutionContextResolver(Protocol):
    """Resolve canonical action context by execution ID for restart-safe lookup."""

    def resolve(self, execution_id: str) -> SanityExecutionContext | None: ...


class SanityHttpSettings(BaseModel):
    """Non-secret deployment settings for one fixed Sanity project and dataset."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    project_id: str
    dataset: str
    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)
    api_version: str = "v2025-02-19"
    connect_timeout_seconds: float = Field(default=3.0, gt=0.0, le=60.0)
    read_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    write_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    pool_timeout_seconds: float = Field(default=3.0, gt=0.0, le=60.0)
    max_response_bytes: int = Field(default=1_048_576, ge=1_024, le=8_388_608)
    live_enabled: bool = False

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str) -> str:
        if not _PROJECT_ID_RE.fullmatch(value):
            raise ValueError("invalid Sanity project ID")
        return value

    @field_validator("dataset")
    @classmethod
    def validate_dataset(cls, value: str) -> str:
        if not _DATASET_RE.fullmatch(value):
            raise ValueError("invalid Sanity dataset name")
        return value

    @field_validator("api_version")
    @classmethod
    def validate_api_version(cls, value: str) -> str:
        if not _API_VERSION_RE.fullmatch(value):
            raise ValueError("Sanity api_version must be vYYYY-MM-DD")
        return value

    @property
    def base_url(self) -> str:
        return f"https://{self.project_id}.api.sanity.io/{self.api_version}"

    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout_seconds,
            read=self.read_timeout_seconds,
            write=self.write_timeout_seconds,
            pool=self.pool_timeout_seconds,
        )


@dataclass(frozen=True)
class _HttpResult:
    status_code: int
    body: bytes
    headers: Mapping[str, str]


class SanityHttpClient:
    """No-retry HTTP implementation of ``SanityProviderClient``.

    Construction and mutation execution are independently gated. This client can
    only be constructed when ``settings.live_enabled`` is true; the surrounding
    ``SanityConditionalMutationTransport`` still defaults writes to false.
    """

    def __init__(
        self,
        *,
        settings: SanityHttpSettings,
        credential_provider: SanityCredentialProvider,
        context_resolver: SanityExecutionContextResolver,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not settings.live_enabled:
            raise SanityHttpClientDisabled(
                "Sanity HTTP client requires explicit live_enabled=True"
            )
        self.settings = settings
        self._credential_provider = credential_provider
        self._context_resolver = context_resolver
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.Client(
            timeout=settings.timeout(),
            transport=httpx.HTTPTransport(retries=0),
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "valo-governed-content/1"},
        )

    def __repr__(self) -> str:
        return (
            "SanityHttpClient("
            f"project_id={self.settings.project_id!r}, "
            f"dataset={self.settings.dataset!r}, "
            f"api_version={self.settings.api_version!r}, live_enabled=True)"
        )

    def close(self) -> None:
        if self._owns_http_client:
            self._http.close()

    def __enter__(self) -> "SanityHttpClient":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()

    def mutate(self, transaction: SanityMutationTransaction) -> SanityMutationResponse:
        """Submit exactly one transaction and return reference-only evidence."""

        self._require_transaction_scope(transaction)
        document_ids, source_revisions = self._extract_patch_bindings(
            transaction.mutations
        )
        params = {
            "returnIds": "true",
            "returnDocuments": "false",
            "transactionId": transaction.transaction_id,
            "visibility": "sync",
            "dryRun": "false",
        }
        body = {"mutations": [dict(value) for value in transaction.mutations]}
        result = self._request(
            method="POST",
            path=f"/data/mutate/{quote(self.settings.dataset, safe='_-')}",
            params=params,
            json_body=body,
            mutation_may_have_started=True,
        )
        if result.status_code == 409:
            raise SanityDefiniteNoEffectError(
                "Sanity revision precondition rejected the transaction; no effect occurred"
            )
        if 300 <= result.status_code < 500:
            raise SanityDefiniteNoEffectError(
                f"Sanity rejected the transaction before effect (HTTP {result.status_code})"
            )
        if result.status_code < 200 or result.status_code >= 300:
            raise SanityUnknownEffectError(
                f"Sanity mutation outcome is unknown (HTTP {result.status_code})"
            )

        payload = self._parse_json_object(result.body, mutation=True)
        response_transaction_id = payload.get("transactionId")
        results = payload.get("results")
        if response_transaction_id != transaction.transaction_id or not isinstance(
            results, list
        ):
            raise SanityUnknownEffectError(
                "Sanity mutation response does not bind the submitted transaction"
            )
        result_ids: list[str] = []
        for value in results:
            if not isinstance(value, Mapping):
                raise SanityUnknownEffectError(
                    "Sanity mutation response contains a malformed result"
                )
            document_id = value.get("documentId")
            operation = value.get("operation")
            if not isinstance(document_id, str) or not document_id:
                raise SanityUnknownEffectError(
                    "Sanity mutation response is missing a document ID"
                )
            if not isinstance(operation, str) or not operation:
                raise SanityUnknownEffectError(
                    "Sanity mutation response is missing an operation"
                )
            result_ids.append(document_id)
        if tuple(sorted(result_ids)) != document_ids:
            raise SanityUnknownEffectError(
                "Sanity mutation response document scope mismatch"
            )

        # Sanity defines _rev as the revision corresponding to the transaction ID.
        current_revisions = tuple(transaction.transaction_id for _ in document_ids)
        observed_snapshot_digest = _digest(
            {
                "provider": "sanity",
                "transaction_id": transaction.transaction_id,
                "document_ids": list(document_ids),
                "current_revisions": list(current_revisions),
            }
        )
        provider_reference = f"sanity:transaction:{transaction.transaction_id}"
        return SanityMutationResponse(
            transaction_id=transaction.transaction_id,
            provider_reference=provider_reference,
            status="committed",
            document_ids=document_ids,
            previous_revisions=source_revisions,
            current_revisions=current_revisions,
            snapshot_digest=observed_snapshot_digest,
            evidence_refs=(provider_reference,),
            response={
                "status": "committed",
                "transaction_id": transaction.transaction_id,
                "result_count": len(result_ids),
            },
        )

    def lookup_transaction(
        self,
        *,
        project_ref: str,
        dataset_ref: str,
        transaction_id: str,
    ) -> SanityTransactionEvidence | None:
        """Read exact transaction history with content excluded."""

        if project_ref != self.settings.project_ref or dataset_ref != self.settings.dataset_ref:
            raise SanityHistoryLookupError("Sanity history lookup scope mismatch")
        context = self._context_resolver.resolve(transaction_id)
        if context is None:
            return None
        document_path = ",".join(
            quote(document_id, safe="._-") for document_id in context.document_ids
        )
        params = {
            "excludeContent": "true",
            "fromTransaction": transaction_id,
            "toTransaction": transaction_id,
            "limit": "2",
            "includeIdentifiedDocumentsOnly": "true",
        }
        result = self._request(
            method="GET",
            path=(
                f"/data/history/{quote(self.settings.dataset, safe='_-')}"
                f"/transactions/{document_path}"
            ),
            params=params,
            json_body=None,
            mutation_may_have_started=False,
        )
        if result.status_code == 404:
            return None
        if result.status_code < 200 or result.status_code >= 300:
            raise SanityHistoryLookupError(
                f"Sanity history lookup failed (HTTP {result.status_code})"
            )
        transaction = self._find_transaction(result.body, transaction_id)
        if transaction is None:
            return None
        history_ids = transaction.get("documentIDs")
        mutations = transaction.get("mutations")
        timestamp = transaction.get("timestamp")
        if not isinstance(history_ids, list) or not isinstance(mutations, list):
            raise SanityHistoryLookupError("Sanity history transaction is malformed")
        if tuple(sorted(str(value) for value in history_ids)) != tuple(
            sorted(context.document_ids)
        ):
            raise SanityHistoryLookupError(
                "Sanity history document scope does not match canonical context"
            )
        observed_ids, observed_revisions = self._extract_history_patch_bindings(mutations)
        if observed_ids != tuple(sorted(context.document_ids)) or observed_revisions != tuple(
            sorted(context.source_revisions)
        ):
            raise SanityHistoryLookupError(
                "Sanity history patch bindings do not match canonical context"
            )
        observed_at = self._parse_timestamp(timestamp)
        current_revisions = tuple(transaction_id for _ in context.document_ids)
        snapshot_digest = _digest(
            {
                "provider": "sanity",
                "transaction_id": transaction_id,
                "document_ids": list(observed_ids),
                "current_revisions": list(current_revisions),
            }
        )
        provider_reference = f"sanity:transaction:{transaction_id}"
        return SanityTransactionEvidence(
            transaction_id=transaction_id,
            provider_reference=provider_reference,
            project_ref=project_ref,
            dataset_ref=dataset_ref,
            status=SanityTransactionStatus.COMMITTED,
            operation=context.operation,
            document_ids=observed_ids,
            previous_revisions=observed_revisions,
            current_revisions=current_revisions,
            proposed_change_digest=context.proposed_change_digest,
            snapshot_digest=snapshot_digest,
            evidence_refs=(f"sanity:history:{transaction_id}",),
            observed_at=observed_at,
            response={
                "status": "committed",
                "transaction_id": transaction_id,
                "content_excluded": True,
            },
        )

    def _request(
        self,
        *,
        method: str,
        path: str,
        params: Mapping[str, str],
        json_body: Mapping[str, Any] | None,
        mutation_may_have_started: bool,
    ) -> _HttpResult:
        token = self._resolve_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, application/x-ndjson",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            with self._http.stream(
                method,
                self.settings.base_url + path,
                params=dict(params),
                json=dict(json_body) if json_body is not None else None,
                headers=headers,
                timeout=self.settings.timeout(),
                follow_redirects=False,
            ) as response:
                body = self._read_bounded(
                    response,
                    mutation=mutation_may_have_started,
                )
                return _HttpResult(
                    status_code=response.status_code,
                    body=body,
                    headers={
                        key.lower(): value
                        for key, value in response.headers.items()
                        if key.lower() in {"content-type", "content-length"}
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            if mutation_may_have_started:
                raise SanityUnknownEffectError(
                    "Sanity provider connection failed after dispatch may have started"
                ) from exc
            raise SanityHistoryLookupError(
                "Sanity history provider connection failed"
            ) from exc
        except (httpx.InvalidURL, httpx.UnsupportedProtocol) as exc:
            if mutation_may_have_started:
                raise SanityDefiniteNoEffectError(
                    "Sanity provider URL was rejected before dispatch"
                ) from exc
            raise SanityHistoryLookupError(
                "Sanity history provider URL was rejected"
            ) from exc

    def _resolve_token(self) -> str:
        try:
            secret = self._credential_provider.get_token()
        except Exception:
            raise SanityHttpConfigurationError(
                "Sanity credential provider failed before dispatch"
            ) from None
        if not isinstance(secret, SecretStr):
            raise SanityHttpConfigurationError(
                "Sanity credential provider must return SecretStr"
            )
        value = secret.get_secret_value().strip()
        if not value:
            raise SanityHttpConfigurationError("Sanity credential is empty")
        if any(character in value for character in "\r\n"):
            raise SanityHttpConfigurationError("Sanity credential contains invalid characters")
        return value

    def _read_bounded(self, response: httpx.Response, *, mutation: bool) -> bytes:
        error_type = SanityUnknownEffectError if mutation else SanityHistoryLookupError
        declared = response.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.settings.max_response_bytes:
                    raise error_type(
                        "Sanity provider response exceeded the configured size limit"
                    )
            except ValueError:
                raise error_type(
                    "Sanity provider returned an invalid content length"
                ) from None
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > self.settings.max_response_bytes:
                raise error_type(
                    "Sanity provider response exceeded the configured size limit"
                )
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _parse_json_object(body: bytes, *, mutation: bool) -> Mapping[str, Any]:
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            if mutation:
                raise SanityUnknownEffectError(
                    "Sanity mutation response was not valid JSON"
                ) from exc
            raise SanityHistoryLookupError(
                "Sanity history response was not valid JSON"
            ) from exc
        if not isinstance(value, Mapping):
            if mutation:
                raise SanityUnknownEffectError(
                    "Sanity mutation response must be a JSON object"
                )
            raise SanityHistoryLookupError(
                "Sanity history response must be a JSON object"
            )
        return value

    @staticmethod
    def _find_transaction(body: bytes, transaction_id: str) -> Mapping[str, Any] | None:
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SanityHistoryLookupError(
                "Sanity history response was not valid UTF-8"
            ) from exc
        matches: list[Mapping[str, Any]] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SanityHistoryLookupError(
                    "Sanity history response contained invalid NDJSON"
                ) from exc
            if not isinstance(value, Mapping):
                raise SanityHistoryLookupError(
                    "Sanity history response contained a non-object record"
                )
            if value.get("id") == transaction_id:
                matches.append(value)
        if not matches:
            return None
        if len(matches) != 1:
            raise SanityHistoryLookupError(
                "Sanity history returned duplicate transaction identities"
            )
        return matches[0]

    @staticmethod
    def _extract_patch_bindings(
        mutations: Sequence[Mapping[str, Any]],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        pairs: list[tuple[str, str]] = []
        for mutation in mutations:
            patch = mutation.get("patch")
            if not isinstance(patch, Mapping):
                raise SanityHttpConfigurationError(
                    "Sanity HTTP client accepts patch mutations only"
                )
            document_id = patch.get("id")
            source_revision = patch.get("ifRevisionID")
            if not isinstance(document_id, str) or not document_id:
                raise SanityHttpConfigurationError(
                    "Sanity patch is missing a document ID"
                )
            if not isinstance(source_revision, str) or not source_revision:
                raise SanityHttpConfigurationError(
                    "Sanity patch is missing ifRevisionID"
                )
            pairs.append((document_id, source_revision))
        if not pairs or len({value[0] for value in pairs}) != len(pairs):
            raise SanityHttpConfigurationError(
                "Sanity transaction requires unique patch document IDs"
            )
        ordered = sorted(pairs)
        return (
            tuple(value[0] for value in ordered),
            tuple(value[1] for value in ordered),
        )

    @staticmethod
    def _extract_history_patch_bindings(
        mutations: Sequence[Any],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        pairs: list[tuple[str, str]] = []
        for mutation in mutations:
            if not isinstance(mutation, Mapping):
                raise SanityHistoryLookupError(
                    "Sanity history mutation record is malformed"
                )
            patch = mutation.get("patch")
            if not isinstance(patch, Mapping):
                raise SanityHistoryLookupError(
                    "Sanity history transaction contains a non-patch mutation"
                )
            document_id = patch.get("id")
            source_revision = patch.get("ifRevisionID")
            if not isinstance(document_id, str) or not isinstance(
                source_revision, str
            ):
                raise SanityHistoryLookupError(
                    "Sanity history patch binding is incomplete"
                )
            pairs.append((document_id, source_revision))
        ordered = sorted(pairs)
        return (
            tuple(value[0] for value in ordered),
            tuple(value[1] for value in ordered),
        )

    def _require_transaction_scope(self, transaction: SanityMutationTransaction) -> None:
        expected = (self.settings.project_ref, self.settings.dataset_ref, "sync", False)
        actual = (
            transaction.project_ref,
            transaction.dataset_ref,
            transaction.visibility,
            transaction.dry_run,
        )
        if actual != expected:
            raise SanityHttpConfigurationError(
                "Sanity transaction scope or execution mode mismatch"
            )

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if not isinstance(value, str) or not value:
            raise SanityHistoryLookupError(
                "Sanity history transaction timestamp is missing"
            )
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SanityHistoryLookupError(
                "Sanity history transaction timestamp is invalid"
            ) from exc
        if parsed.tzinfo is None:
            raise SanityHistoryLookupError(
                "Sanity history transaction timestamp lacks timezone"
            )
        return parsed.astimezone(timezone.utc)
