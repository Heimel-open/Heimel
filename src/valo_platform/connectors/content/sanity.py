"""Sanity-compatible, injected shadow adapter for Governed Content Operations.

The adapter binds Sanity project, dataset, document IDs, ``_rev`` values and
schema metadata to the existing provider-neutral shadow evidence contract. It
has no production mutation method and assumes no undocumented API endpoint.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Protocol

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.content_operations.actions import ContentActionCase

from .protocol import ContentShadowRequest
from .synthetic import ContentShadowConflict, ContentShadowEvidence


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _validate_sha256(value: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("digest must be lowercase sha256:<64 hex>")
    return value


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


class SanitySchemaSnapshot(BaseModel):
    """Reference-only Sanity schema observation."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    schema_digest: str
    document_types: tuple[str, ...] = Field(min_length=1)
    schema_refs: tuple[str, ...] = ()

    @field_validator("schema_digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("document_types", "schema_refs", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        normalized: set[str] = set()
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Sanity schema collections require non-empty strings")
            normalized.add(item.strip())
        return tuple(sorted(normalized))


class SanityDocumentMetadata(BaseModel):
    """Sanity document metadata without raw document content."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    document_id: str = Field(min_length=1, alias="_id")
    revision: str = Field(min_length=1, alias="_rev")
    document_type: str = Field(min_length=1, alias="_type")
    snapshot_digest: str
    locales: tuple[str, ...] = ()
    metadata_refs: tuple[str, ...] = ()

    @field_validator("snapshot_digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("locales", "metadata_refs", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        normalized: set[str] = set()
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("Sanity metadata collections require non-empty strings")
            normalized.add(item.strip())
        return tuple(sorted(normalized))


class SanityShadowResult(BaseModel):
    """Observed or simulated Sanity state returned by an injected transport."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: str = Field(min_length=1)
    schema_digest: str
    document_ids: tuple[str, ...] = Field(min_length=1)
    revisions: tuple[str, ...] = Field(min_length=1)
    snapshot_digest: str
    result_refs: tuple[str, ...] = ()
    would_mutate: bool = False

    @field_validator("schema_digest", "snapshot_digest")
    @classmethod
    def validate_digests(cls, value: str) -> str:
        return _validate_sha256(value)


class SanityShadowTransport(Protocol):
    """Injected read and dry-run surface; deliberately no write operation."""

    def inspect_schema(self, request: ContentShadowRequest) -> SanityShadowResult:
        """Observe the schema bound to the requested project and dataset."""

    def fetch_metadata(self, request: ContentShadowRequest) -> SanityShadowResult:
        """Observe document IDs, revisions and reference metadata."""

    def observe_current_state(self, request: ContentShadowRequest) -> SanityShadowResult:
        """Observe the current reference-only document snapshot."""

    def preview_patch(self, request: ContentShadowRequest) -> SanityShadowResult:
        """Preview the exact patch without applying it."""

    def simulate_patch(self, request: ContentShadowRequest) -> SanityShadowResult:
        """Simulate the patch without changing Sanity state."""


class SanityFixtureTransport:
    """Deterministic local Sanity fixture with zero credentials and network calls."""

    def __init__(
        self,
        *,
        project_ref: str,
        dataset_ref: str,
        schema: SanitySchemaSnapshot,
        documents: tuple[SanityDocumentMetadata, ...],
    ) -> None:
        if schema.project_ref != project_ref or schema.dataset_ref != dataset_ref:
            raise ValueError("Sanity schema scope does not match fixture scope")
        by_id = {document.document_id: document for document in documents}
        if len(by_id) != len(documents):
            raise ValueError("Sanity fixture document IDs must be unique")
        if not documents:
            raise ValueError("Sanity fixture requires at least one document")
        self.project_ref = project_ref
        self.dataset_ref = dataset_ref
        self.schema = schema
        self.documents = documents
        self.calls: list[str] = []

    def inspect_schema(self, request: ContentShadowRequest) -> SanityShadowResult:
        self.calls.append("inspect_schema")
        self._require_scope(request)
        return self._result(request, "sanity_schema_observed", would_mutate=False)

    def fetch_metadata(self, request: ContentShadowRequest) -> SanityShadowResult:
        self.calls.append("fetch_metadata")
        documents = self._require_current(request)
        refs = tuple(sorted(ref for item in documents for ref in item.metadata_refs))
        return self._result(
            request,
            "sanity_metadata_observed",
            would_mutate=False,
            result_refs=refs,
        )

    def observe_current_state(self, request: ContentShadowRequest) -> SanityShadowResult:
        self.calls.append("observe_current_state")
        self._require_current(request)
        return self._result(request, "sanity_state_observed", would_mutate=False)

    def preview_patch(self, request: ContentShadowRequest) -> SanityShadowResult:
        self.calls.append("preview_patch")
        self._require_current(request)
        return self._result(request, "sanity_patch_previewed", would_mutate=False)

    def simulate_patch(self, request: ContentShadowRequest) -> SanityShadowResult:
        self.calls.append("simulate_patch")
        self._require_current(request)
        return self._result(
            request,
            "sanity_patch_would_apply",
            would_mutate=request.operation.requires_mutation_clearance,
        )

    def selected_documents(
        self, document_ids: tuple[str, ...]
    ) -> tuple[SanityDocumentMetadata, ...]:
        by_id = {document.document_id: document for document in self.documents}
        missing = set(document_ids) - set(by_id)
        if missing:
            raise ContentShadowConflict(
                "Sanity documents are missing: " + ", ".join(sorted(missing))
            )
        return tuple(by_id[document_id] for document_id in sorted(document_ids))

    def snapshot_digest(self, document_ids: tuple[str, ...]) -> str:
        documents = self.selected_documents(document_ids)
        return _digest(
            {
                "content_system": "sanity",
                "project_ref": self.project_ref,
                "dataset_ref": self.dataset_ref,
                "schema_version": self.schema.schema_version,
                "documents": [
                    {
                        "_id": document.document_id,
                        "_rev": document.revision,
                        "_type": document.document_type,
                        "snapshot_digest": document.snapshot_digest,
                    }
                    for document in documents
                ],
            }
        )

    def _require_scope(self, request: ContentShadowRequest) -> None:
        if request.content_system != "sanity":
            raise ContentShadowConflict("Sanity adapter requires content_system=sanity")
        if request.project_ref != self.project_ref:
            raise ContentShadowConflict("Sanity project is outside fixture scope")
        if request.dataset_ref != self.dataset_ref:
            raise ContentShadowConflict("Sanity dataset is outside fixture scope")
        if request.schema_version != self.schema.schema_version:
            raise ContentShadowConflict("Sanity schema version is stale or mismatched")

    def _require_current(
        self, request: ContentShadowRequest
    ) -> tuple[SanityDocumentMetadata, ...]:
        self._require_scope(request)
        documents = self.selected_documents(request.record_ids)
        revisions = tuple(sorted(document.revision for document in documents))
        if revisions != tuple(sorted(request.source_version_refs)):
            raise ContentShadowConflict("Sanity _rev binding is stale or mismatched")
        return documents

    def _result(
        self,
        request: ContentShadowRequest,
        status: str,
        *,
        would_mutate: bool,
        result_refs: tuple[str, ...] = (),
    ) -> SanityShadowResult:
        documents = self.selected_documents(request.record_ids)
        return SanityShadowResult(
            status=status,
            schema_digest=self.schema.schema_digest,
            document_ids=tuple(document.document_id for document in documents),
            revisions=tuple(sorted(document.revision for document in documents)),
            snapshot_digest=self.snapshot_digest(request.record_ids),
            result_refs=tuple(sorted(set(result_refs))),
            would_mutate=would_mutate,
        )


class SanityShadowConnector:
    """Adapter from Sanity-compatible reads to canonical shadow evidence."""

    def __init__(self, transport: SanityShadowTransport) -> None:
        self._transport = transport

    def inspect_schema(self, action_case: ContentActionCase) -> ContentShadowEvidence:
        return self._observe(action_case, "inspect_schema", dry_run=False)

    def fetch_metadata(self, action_case: ContentActionCase) -> ContentShadowEvidence:
        return self._observe(action_case, "fetch_metadata", dry_run=False)

    def observe_current_state(
        self, action_case: ContentActionCase
    ) -> ContentShadowEvidence:
        return self._observe(action_case, "observe_current_state", dry_run=False)

    def preview(self, action_case: ContentActionCase) -> ContentShadowEvidence:
        return self._observe(action_case, "preview_patch", dry_run=True)

    def dry_run(self, action_case: ContentActionCase) -> ContentShadowEvidence:
        return self._observe(action_case, "simulate_patch", dry_run=True)

    def _observe(
        self,
        action_case: ContentActionCase,
        method_name: str,
        *,
        dry_run: bool,
    ) -> ContentShadowEvidence:
        request = ContentShadowRequest.from_action_case(action_case)
        method = getattr(self._transport, method_name)
        result: SanityShadowResult = method(request)
        expected_ids = tuple(sorted(action_case.content.record_ids))
        if tuple(sorted(result.document_ids)) != expected_ids:
            raise ContentShadowConflict("Sanity result does not bind exact document IDs")
        if tuple(sorted(result.revisions)) != tuple(
            sorted(action_case.content.source_version_refs)
        ):
            raise ContentShadowConflict("Sanity result does not bind exact _rev values")
        if result.snapshot_digest != action_case.content.content_snapshot_digest:
            raise ContentShadowConflict(
                "Sanity snapshot does not match the Content Action Case"
            )

        return ContentShadowEvidence(
            action_id=request.action_id,
            operation=request.operation.value,
            payload_digest=request.payload_digest,
            target_digest=request.target_digest,
            state_binding_digest=request.state_binding_digest,
            observed_snapshot_digest=result.snapshot_digest,
            schema_digest=result.schema_digest,
            record_version_refs=result.revisions,
            outcome=result.status,
            result_refs=result.result_refs,
            would_mutate=result.would_mutate,
            dry_run=dry_run,
        )
