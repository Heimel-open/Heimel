"""Persistent Sanity execution context and fail-closed canary deployment binding.

This module contains deployment and reconciliation support only. It does not
issue policy decisions, clearance, CommitTokens, execution receipts or outcome
receipts, and it does not create a parallel execution state machine.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

import httpx
import rfc8785
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from src.valo_platform.action_envelope.bounded_connector import ConnectorBoundaryError
from src.valo_platform.action_envelope.durable_execution import (
    DurableConnectorExecutor,
    DurableExecutionResult,
)
from src.valo_platform.content_operations.actions import (
    ContentActionCase,
    ContentOperation,
)

from .mutation import ClearedContentMutationConnector
from .protocol import ContentMutationRequest, ContentMutationTransport
from .sanity import SanitySchemaSnapshot
from .sanity_http import (
    SanityCredentialProvider,
    SanityExecutionContext,
    SanityHttpClient,
    SanityHttpConfigurationError,
    SanityHttpSettings,
)
from .sanity_mutation import (
    SanityConditionalMutationTransport,
    SanityPatchArtifactResolver,
    SanityPatchValueResolver,
    SanityProviderClient,
)


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}$")
_SUPPORTED_CANARY_OPERATIONS = frozenset(
    {ContentOperation.UPDATE_FIELD, ContentOperation.BULK_UPDATE}
)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SanityExecutionContextCorrupt("invalid stored timestamp") from exc
    if parsed.tzinfo is None:
        raise SanityExecutionContextCorrupt("stored timestamp is not timezone-aware")
    return parsed


def _normalize_strings(value: Any) -> tuple[str, ...]:
    values = [value] if isinstance(value, str) else list(value or ())
    normalized: set[str] = set()
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("string collections require non-empty strings")
        normalized.add(item.strip())
    return tuple(sorted(normalized))


class SanityExecutionContextStoreError(RuntimeError):
    """Base error for immutable Sanity execution-context persistence."""


class SanityExecutionContextConflict(SanityExecutionContextStoreError):
    """An execution or idempotency identity is already bound differently."""


class SanityExecutionContextCorrupt(SanityExecutionContextStoreError):
    """Persisted execution context failed structural or digest validation."""


class PersistedSanityExecutionContext(BaseModel):
    """Reference-only immutable context required for restart-safe history lookup."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )

    execution_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    connector_id: str = Field(min_length=1)
    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)
    operation: ContentOperation
    document_ids: tuple[str, ...] = Field(min_length=1)
    source_revisions: tuple[str, ...] = Field(min_length=1)
    proposed_change_digest: str
    payload_digest: str
    target_digest: str
    idempotency_key: str = Field(min_length=1)
    registered_at: datetime
    context_digest: str

    @field_validator("document_ids", "source_revisions", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any) -> tuple[str, ...]:
        return _normalize_strings(value)

    @field_validator(
        "proposed_change_digest",
        "payload_digest",
        "target_digest",
        "context_digest",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("digest must be lowercase sha256:<64 hex>")
        return value

    @field_validator("registered_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("registered_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_binding(self) -> "PersistedSanityExecutionContext":
        if self.operation not in _SUPPORTED_CANARY_OPERATIONS:
            raise ValueError("unsupported Sanity persisted operation")
        if len(self.document_ids) != len(self.source_revisions):
            raise ValueError("document and source-revision cardinality mismatch")
        if self.context_digest != _digest(self.canonical_payload()):
            raise ValueError("Sanity execution context digest mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "tenant_id": self.tenant_id,
            "connector_id": self.connector_id,
            "project_ref": self.project_ref,
            "dataset_ref": self.dataset_ref,
            "operation": self.operation.value,
            "document_ids": list(self.document_ids),
            "source_revisions": list(self.source_revisions),
            "proposed_change_digest": self.proposed_change_digest,
            "payload_digest": self.payload_digest,
            "target_digest": self.target_digest,
            "idempotency_key": self.idempotency_key,
        }

    def to_http_context(self) -> SanityExecutionContext:
        return SanityExecutionContext(
            operation=self.operation,
            document_ids=self.document_ids,
            source_revisions=self.source_revisions,
            proposed_change_digest=self.proposed_change_digest,
        )

    @classmethod
    def build(
        cls,
        *,
        execution_id: str,
        tenant_id: str,
        connector_id: str,
        project_ref: str,
        dataset_ref: str,
        operation: ContentOperation,
        document_ids: tuple[str, ...],
        source_revisions: tuple[str, ...],
        proposed_change_digest: str,
        payload_digest: str,
        target_digest: str,
        idempotency_key: str,
        registered_at: datetime,
    ) -> "PersistedSanityExecutionContext":
        payload = {
            "execution_id": execution_id,
            "tenant_id": tenant_id,
            "connector_id": connector_id,
            "project_ref": project_ref,
            "dataset_ref": dataset_ref,
            "operation": operation.value,
            "document_ids": list(_normalize_strings(document_ids)),
            "source_revisions": list(_normalize_strings(source_revisions)),
            "proposed_change_digest": proposed_change_digest,
            "payload_digest": payload_digest,
            "target_digest": target_digest,
            "idempotency_key": idempotency_key,
        }
        return cls(
            **payload,
            registered_at=registered_at,
            context_digest=_digest(payload),
        )


class SQLiteSanityExecutionContextStore:
    """Immutable SQLite sidecar for history interpretation, not execution state."""

    def __init__(self, path: str | Path) -> None:
        database_path = Path(path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(database_path)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sanity_execution_contexts (
                    execution_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    connector_id TEXT NOT NULL,
                    project_ref TEXT NOT NULL,
                    dataset_ref TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    document_ids_json TEXT NOT NULL,
                    source_revisions_json TEXT NOT NULL,
                    proposed_change_digest TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    target_digest TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    context_digest TEXT NOT NULL,
                    UNIQUE (tenant_id, idempotency_key)
                )
                """
            )
        try:
            database_path.chmod(0o600)
        except OSError:
            pass

    def register(
        self, context: PersistedSanityExecutionContext
    ) -> PersistedSanityExecutionContext:
        """Register once; exact replay is idempotent and conflicting reuse fails."""

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_row = connection.execute(
                "SELECT * FROM sanity_execution_contexts WHERE execution_id=?",
                (context.execution_id,),
            ).fetchone()
            if existing_row is not None:
                existing = self._decode(existing_row)
                if existing.context_digest != context.context_digest:
                    connection.rollback()
                    raise SanityExecutionContextConflict(
                        "execution ID is already bound to different Sanity context"
                    )
                connection.commit()
                return existing

            idempotency_row = connection.execute(
                """
                SELECT * FROM sanity_execution_contexts
                WHERE tenant_id=? AND idempotency_key=?
                """,
                (context.tenant_id, context.idempotency_key),
            ).fetchone()
            if idempotency_row is not None:
                existing = self._decode(idempotency_row)
                connection.rollback()
                if existing.context_digest == context.context_digest:
                    return existing
                raise SanityExecutionContextConflict(
                    "content idempotency key is already bound to different Sanity context"
                )

            try:
                connection.execute(
                    """
                    INSERT INTO sanity_execution_contexts (
                        execution_id, tenant_id, connector_id, project_ref,
                        dataset_ref, operation, document_ids_json,
                        source_revisions_json, proposed_change_digest,
                        payload_digest, target_digest, idempotency_key,
                        registered_at, context_digest
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        context.execution_id,
                        context.tenant_id,
                        context.connector_id,
                        context.project_ref,
                        context.dataset_ref,
                        context.operation.value,
                        json.dumps(list(context.document_ids), separators=(",", ":")),
                        json.dumps(
                            list(context.source_revisions), separators=(",", ":")
                        ),
                        context.proposed_change_digest,
                        context.payload_digest,
                        context.target_digest,
                        context.idempotency_key,
                        _timestamp(context.registered_at),
                        context.context_digest,
                    ),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise SanityExecutionContextConflict(
                    "Sanity execution or idempotency identity already exists"
                ) from exc
        return self.get(context.execution_id)

    def get(self, execution_id: str) -> PersistedSanityExecutionContext:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sanity_execution_contexts WHERE execution_id=?",
                (execution_id,),
            ).fetchone()
        if row is None:
            raise SanityExecutionContextStoreError("Sanity execution context not found")
        return self._decode(row)

    def resolve(self, execution_id: str) -> SanityExecutionContext | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sanity_execution_contexts WHERE execution_id=?",
                (execution_id,),
            ).fetchone()
        if row is None:
            return None
        return self._decode(row).to_http_context()

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM sanity_execution_contexts"
            ).fetchone()
        return int(row[0])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _decode(row: sqlite3.Row) -> PersistedSanityExecutionContext:
        try:
            document_ids = json.loads(row["document_ids_json"])
            source_revisions = json.loads(row["source_revisions_json"])
            if not isinstance(document_ids, list) or not isinstance(
                source_revisions, list
            ):
                raise TypeError("stored collections are not lists")
            return PersistedSanityExecutionContext(
                execution_id=row["execution_id"],
                tenant_id=row["tenant_id"],
                connector_id=row["connector_id"],
                project_ref=row["project_ref"],
                dataset_ref=row["dataset_ref"],
                operation=ContentOperation(row["operation"]),
                document_ids=tuple(document_ids),
                source_revisions=tuple(source_revisions),
                proposed_change_digest=row["proposed_change_digest"],
                payload_digest=row["payload_digest"],
                target_digest=row["target_digest"],
                idempotency_key=row["idempotency_key"],
                registered_at=_parse_timestamp(row["registered_at"]),
                context_digest=row["context_digest"],
            )
        except SanityExecutionContextCorrupt:
            raise
        except Exception as exc:
            raise SanityExecutionContextCorrupt(
                "persisted Sanity execution context is malformed or tampered"
            ) from exc


class SanityCanaryDeploymentError(SanityHttpConfigurationError):
    """Canary deployment binding failed before provider dispatch."""


class SanitySecretResolver(Protocol):
    """Resolve a current secret by opaque reference from an external manager."""

    def resolve_secret(self, secret_ref: str) -> SecretStr: ...


class SanitySecretManagerCredentialProvider(SanityCredentialProvider):
    """Resolve a fresh token per request without caching or exposing it."""

    def __init__(self, *, secret_ref: str, resolver: SanitySecretResolver) -> None:
        if not _SECRET_REF_RE.fullmatch(secret_ref):
            raise SanityCanaryDeploymentError("invalid Sanity secret reference")
        self._secret_ref = secret_ref
        self._resolver = resolver

    def __repr__(self) -> str:
        return "SanitySecretManagerCredentialProvider(secret_ref=<configured>)"

    def get_token(self) -> SecretStr:
        try:
            secret = self._resolver.resolve_secret(self._secret_ref)
        except Exception:
            raise SanityHttpConfigurationError(
                "Sanity secret manager resolution failed before dispatch"
            ) from None
        if not isinstance(secret, SecretStr):
            raise SanityHttpConfigurationError(
                "Sanity secret manager must return SecretStr"
            )
        value = secret.get_secret_value().strip()
        if not value:
            raise SanityHttpConfigurationError("Sanity secret manager returned empty token")
        if len(value) > 8192 or "\r" in value or "\n" in value:
            raise SanityHttpConfigurationError(
                "Sanity secret manager returned malformed token"
            )
        return SecretStr(value)


class SanityCanaryDeploymentProfile(BaseModel):
    """Frozen non-secret allowlist for one Sanity canary deployment."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )

    profile_id: str = Field(min_length=1)
    environment: str = "canary"
    tenant_id: str = Field(min_length=1)
    connector_id: str = Field(min_length=1)
    project_id: str = Field(min_length=2)
    dataset: str = Field(min_length=1)
    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    allowed_document_ids: tuple[str, ...] = Field(min_length=1)
    allowed_operations: tuple[ContentOperation, ...] = (
        ContentOperation.UPDATE_FIELD,
    )
    max_documents_per_transaction: int = Field(default=1, ge=1, le=100)
    secret_ref: str = Field(min_length=3)
    api_version: str = "v2025-02-19"
    connect_timeout_seconds: float = Field(default=3.0, gt=0.0, le=60.0)
    read_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    write_timeout_seconds: float = Field(default=10.0, gt=0.0, le=120.0)
    pool_timeout_seconds: float = Field(default=3.0, gt=0.0, le=60.0)
    max_response_bytes: int = Field(default=1_048_576, ge=1_024, le=8_388_608)
    expires_at: datetime

    @field_validator("allowed_document_ids", mode="before")
    @classmethod
    def normalize_document_ids(cls, value: Any) -> tuple[str, ...]:
        return _normalize_strings(value)

    @field_validator("allowed_operations", mode="before")
    @classmethod
    def normalize_operations(cls, value: Any) -> tuple[ContentOperation, ...]:
        values = [value] if isinstance(value, (str, ContentOperation)) else list(value)
        normalized = tuple(
            sorted(
                {ContentOperation(item) for item in values},
                key=lambda item: item.value,
            )
        )
        if not normalized:
            raise ValueError("at least one canary operation is required")
        if any(item not in _SUPPORTED_CANARY_OPERATIONS for item in normalized):
            raise ValueError("canary profile contains unsupported Sanity operation")
        return normalized

    @field_validator("secret_ref")
    @classmethod
    def validate_secret_ref(cls, value: str) -> str:
        if not _SECRET_REF_RE.fullmatch(value):
            raise ValueError("invalid secret reference")
        return value

    @field_validator("expires_at")
    @classmethod
    def require_expiry_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("canary profile expiry must be timezone-aware")
        return value

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return _digest(self.canonical_payload())


class SanityCanaryActivation(BaseModel):
    """Independent deployment switches bound to one exact profile digest."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    profile_digest: str
    live_enabled: bool = False
    writes_enabled: bool = False

    @field_validator("profile_digest")
    @classmethod
    def validate_profile_digest(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("profile_digest must be lowercase sha256:<64 hex>")
        return value


class SanityCanaryDeployment:
    """Bind HTTP, secrets, scope and write activation beneath governance."""

    def __init__(
        self,
        *,
        profile: SanityCanaryDeploymentProfile,
        activation: SanityCanaryActivation,
        secret_resolver: SanitySecretResolver,
        context_store: SQLiteSanityExecutionContextStore,
    ) -> None:
        self.profile = profile
        self.activation = activation
        self._secret_resolver = secret_resolver
        self.context_store = context_store

    def build_http_client(
        self,
        *,
        http_client: httpx.Client | None = None,
        now: datetime | None = None,
    ) -> SanityHttpClient:
        self._require_activation(now=now, require_live=True, require_writes=False)
        settings = SanityHttpSettings(
            project_id=self.profile.project_id,
            dataset=self.profile.dataset,
            project_ref=self.profile.project_ref,
            dataset_ref=self.profile.dataset_ref,
            api_version=self.profile.api_version,
            connect_timeout_seconds=self.profile.connect_timeout_seconds,
            read_timeout_seconds=self.profile.read_timeout_seconds,
            write_timeout_seconds=self.profile.write_timeout_seconds,
            pool_timeout_seconds=self.profile.pool_timeout_seconds,
            max_response_bytes=self.profile.max_response_bytes,
            live_enabled=True,
        )
        credentials = SanitySecretManagerCredentialProvider(
            secret_ref=self.profile.secret_ref,
            resolver=self._secret_resolver,
        )
        return SanityHttpClient(
            settings=settings,
            credential_provider=credentials,
            context_resolver=self.context_store,
            http_client=http_client,
        )

    def build_mutation_transport(
        self,
        *,
        client: SanityProviderClient,
        patch_resolver: SanityPatchArtifactResolver,
        value_resolver: SanityPatchValueResolver,
        schema: SanitySchemaSnapshot,
        now: datetime | None = None,
    ) -> SanityConditionalMutationTransport:
        self._require_activation(now=now, require_live=True, require_writes=True)
        expected = (
            self.profile.project_ref,
            self.profile.dataset_ref,
            self.profile.schema_version,
        )
        actual = (schema.project_ref, schema.dataset_ref, schema.schema_version)
        if actual != expected:
            raise SanityCanaryDeploymentError(
                "Sanity schema does not match canary deployment profile"
            )
        return SanityConditionalMutationTransport(
            client=client,
            patch_resolver=patch_resolver,
            value_resolver=value_resolver,
            project_ref=self.profile.project_ref,
            dataset_ref=self.profile.dataset_ref,
            schema=schema,
            writes_enabled=True,
        )

    def require_write_request(
        self,
        request: ContentMutationRequest,
        *,
        connector_id: str,
        now: datetime | None = None,
    ) -> None:
        self._require_activation(now=now, require_live=True, require_writes=True)
        expected = (
            self.profile.tenant_id,
            self.profile.connector_id,
            self.profile.project_ref,
            self.profile.dataset_ref,
            self.profile.schema_version,
        )
        actual = (
            request.tenant_id,
            connector_id,
            request.project_ref,
            request.dataset_ref,
            request.schema_version,
        )
        if actual != expected:
            raise SanityCanaryDeploymentError(
                "content mutation is outside the canary deployment scope"
            )
        if request.content_system != "sanity":
            raise SanityCanaryDeploymentError(
                "canary deployment accepts Sanity content actions only"
            )
        if request.operation not in self.profile.allowed_operations:
            raise SanityCanaryDeploymentError(
                "content operation is not allowed by canary deployment"
            )
        if len(request.record_ids) > self.profile.max_documents_per_transaction:
            raise SanityCanaryDeploymentError(
                "content mutation exceeds canary transaction cardinality"
            )
        if not set(request.record_ids).issubset(
            set(self.profile.allowed_document_ids)
        ):
            raise SanityCanaryDeploymentError(
                "content mutation targets a document outside canary allowlist"
            )

    def _require_activation(
        self,
        *,
        now: datetime | None,
        require_live: bool,
        require_writes: bool,
    ) -> None:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise SanityCanaryDeploymentError("activation time must be timezone-aware")
        if self.activation.profile_digest != self.profile.digest():
            raise SanityCanaryDeploymentError(
                "canary activation does not bind deployment profile"
            )
        if current >= self.profile.expires_at:
            raise SanityCanaryDeploymentError("canary deployment profile has expired")
        if require_live and not self.activation.live_enabled:
            raise SanityCanaryDeploymentError("Sanity live deployment is disabled")
        if require_writes and not self.activation.writes_enabled:
            raise SanityCanaryDeploymentError("Sanity canary writes are disabled")


class SanityCanaryDurableMutationExecutor:
    """Persist exact context before delegating to canonical durable execution."""

    def __init__(
        self,
        *,
        connector: ClearedContentMutationConnector,
        durable_executor: DurableConnectorExecutor,
        deployment: SanityCanaryDeployment,
    ) -> None:
        self._connector = connector
        self._durable = durable_executor
        self._deployment = deployment

    def execute(
        self,
        *,
        action_case: ContentActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        integrity_baseline: Any,
        integrity_checkpoint: Any,
        transport: ContentMutationTransport,
        receipt_id: str,
        now: datetime | None = None,
    ) -> DurableExecutionResult:
        plan = self._connector.prepare(
            action_case=action_case,
            signed_commit_token=signed_commit_token,
            integrity_baseline=integrity_baseline,
            integrity_checkpoint=integrity_checkpoint,
            transport=transport,
        )
        if signed_commit_token is None:
            raise ConnectorBoundaryError("signed CommitToken is required")
        payload = signed_commit_token.get("payload")
        if not isinstance(payload, Mapping):
            raise ConnectorBoundaryError("CommitToken payload is missing")
        execution_id = payload.get("execution_id")
        if not isinstance(execution_id, str) or not execution_id:
            raise ConnectorBoundaryError("CommitToken execution_id is missing")

        request = ContentMutationRequest.from_action_case(
            execution_id=execution_id,
            action_case=action_case,
        )
        self._deployment.require_write_request(
            request,
            connector_id=plan.connector_id,
            now=now,
        )
        registered_at = now or datetime.now(timezone.utc)
        context = PersistedSanityExecutionContext.build(
            execution_id=execution_id,
            tenant_id=request.tenant_id,
            connector_id=plan.connector_id,
            project_ref=request.project_ref,
            dataset_ref=request.dataset_ref,
            operation=request.operation,
            document_ids=request.record_ids,
            source_revisions=request.source_version_refs,
            proposed_change_digest=request.proposed_change_digest,
            payload_digest=plan.payload_digest,
            target_digest=plan.target_digest,
            idempotency_key=plan.idempotency_key,
            registered_at=registered_at,
        )
        self._deployment.context_store.register(context)
        return self._durable.execute(
            signed_commit_token=signed_commit_token,
            connector_id=plan.connector_id,
            capability=plan.capability,
            target_digest=plan.target_digest,
            payload_digest=plan.payload_digest,
            mutation=plan.mutation,
            receipt_id=receipt_id,
            idempotency_key=plan.idempotency_key,
            now=now,
        )
