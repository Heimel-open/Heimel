"""Deterministic, network-free content connector for shadow-mode governance.

The synthetic transport stores reference metadata and snapshot hashes only. It
supports observation, preview, and simulation, but deliberately exposes no
production mutation method.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.content_operations.actions import ContentActionCase

from .protocol import ContentShadowRequest, ContentShadowResult


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _validate_sha256(value: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("digest must be lowercase sha256:<64 hex>")
    return value


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


class ContentShadowConflict(RuntimeError):
    """The proposed action no longer matches the observed synthetic state."""


class SyntheticContentRecord(BaseModel):
    """Reference-only synthetic CMS record metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    record_id: str = Field(min_length=1)
    version_ref: str = Field(min_length=1)
    snapshot_digest: str
    schema_version: str = Field(min_length=1)
    field_names: tuple[str, ...] = ()
    locales: tuple[str, ...] = ()
    metadata_refs: tuple[str, ...] = ()

    @field_validator("snapshot_digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _validate_sha256(value)

    @field_validator("field_names", "locales", "metadata_refs", mode="before")
    @classmethod
    def normalize_collections(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        normalized: set[str] = set()
        for item in values:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("record collections require non-empty strings")
            normalized.add(item.strip())
        return tuple(sorted(normalized))


class SyntheticContentWorkspace(BaseModel):
    """Immutable synthetic CMS state used by deterministic tests and demos."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    tenant_id: str = Field(min_length=1)
    content_system: str = Field(min_length=1)
    workspace_ref: str = Field(min_length=1)
    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    schema_digest: str
    records: tuple[SyntheticContentRecord, ...] = Field(min_length=1)

    @field_validator("schema_digest")
    @classmethod
    def validate_schema_digest(cls, value: str) -> str:
        return _validate_sha256(value)

    @model_validator(mode="after")
    def require_consistent_records(self) -> "SyntheticContentWorkspace":
        record_ids = [record.record_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("synthetic workspace record IDs must be unique")
        if any(
            record.schema_version != self.schema_version for record in self.records
        ):
            raise ValueError("record schema version must match workspace schema")
        return self

    def selected_records(
        self, record_ids: tuple[str, ...]
    ) -> tuple[SyntheticContentRecord, ...]:
        by_id = {record.record_id: record for record in self.records}
        missing = set(record_ids) - set(by_id)
        if missing:
            raise ContentShadowConflict(
                "synthetic records are missing: " + ", ".join(sorted(missing))
            )
        return tuple(by_id[record_id] for record_id in sorted(record_ids))

    def snapshot_digest(self, record_ids: tuple[str, ...]) -> str:
        records = self.selected_records(record_ids)
        return _digest(
            {
                "tenant_id": self.tenant_id,
                "content_system": self.content_system,
                "workspace_ref": self.workspace_ref,
                "project_ref": self.project_ref,
                "dataset_ref": self.dataset_ref,
                "schema_version": self.schema_version,
                "records": [
                    {
                        "record_id": record.record_id,
                        "version_ref": record.version_ref,
                        "snapshot_digest": record.snapshot_digest,
                    }
                    for record in records
                ],
            }
        )


class ContentShadowEvidence(BaseModel):
    """Reference-only evidence linking a proposal to a shadow observation."""

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    action_id: str
    operation: str
    payload_digest: str
    target_digest: str
    state_binding_digest: str
    observed_snapshot_digest: str
    schema_digest: str
    record_version_refs: tuple[str, ...]
    outcome: str
    result_refs: tuple[str, ...] = ()
    would_mutate: bool
    dry_run: bool

    @field_validator(
        "payload_digest",
        "target_digest",
        "state_binding_digest",
        "observed_snapshot_digest",
        "schema_digest",
    )
    @classmethod
    def validate_digests(cls, value: str) -> str:
        return _validate_sha256(value)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return _digest(self.canonical_payload())


class SyntheticContentWorkspaceTransport:
    """Provider-neutral shadow transport with no write operation."""

    def __init__(self, workspace: SyntheticContentWorkspace) -> None:
        self.workspace = workspace
        self.calls: list[str] = []

    def inspect_schema(self, request: ContentShadowRequest) -> ContentShadowResult:
        self.calls.append("inspect_schema")
        self._require_scope(request)
        return self._result(request, "schema_observed", would_mutate=False)

    def fetch_metadata(self, request: ContentShadowRequest) -> ContentShadowResult:
        self.calls.append("fetch_metadata")
        records = self._require_current(request)
        refs = tuple(sorted(ref for record in records for ref in record.metadata_refs))
        return self._result(
            request,
            "metadata_observed",
            would_mutate=False,
            result_refs=refs,
        )

    def observe_current_state(
        self, request: ContentShadowRequest
    ) -> ContentShadowResult:
        self.calls.append("observe_current_state")
        self._require_current(request)
        return self._result(request, "state_observed", would_mutate=False)

    def preview(self, request: ContentShadowRequest) -> ContentShadowResult:
        self.calls.append("preview")
        self._require_current(request)
        return self._result(request, "proposal_previewed", would_mutate=False)

    def simulate(self, request: ContentShadowRequest) -> ContentShadowResult:
        self.calls.append("simulate")
        self._require_current(request)
        return self._result(
            request,
            "mutation_would_apply",
            would_mutate=request.operation.requires_mutation_clearance,
        )

    def _require_scope(self, request: ContentShadowRequest) -> None:
        expected = (
            self.workspace.tenant_id,
            self.workspace.content_system,
            self.workspace.workspace_ref,
            self.workspace.project_ref,
            self.workspace.dataset_ref,
        )
        actual = (
            request.tenant_id,
            request.content_system,
            request.workspace_ref,
            request.project_ref,
            request.dataset_ref,
        )
        if actual != expected:
            raise ContentShadowConflict("content request is outside synthetic scope")
        if request.schema_version != self.workspace.schema_version:
            raise ContentShadowConflict("content schema version is stale or mismatched")

    def _require_current(
        self, request: ContentShadowRequest
    ) -> tuple[SyntheticContentRecord, ...]:
        self._require_scope(request)
        records = self.workspace.selected_records(request.record_ids)
        observed_versions = tuple(sorted(record.version_ref for record in records))
        if observed_versions != tuple(sorted(request.source_version_refs)):
            raise ContentShadowConflict("content source version is stale or mismatched")
        return records

    def _result(
        self,
        request: ContentShadowRequest,
        status: str,
        *,
        would_mutate: bool,
        result_refs: tuple[str, ...] = (),
    ) -> ContentShadowResult:
        records = self.workspace.selected_records(request.record_ids)
        return ContentShadowResult(
            operation=request.operation.value,
            status=status,
            schema_digest=self.workspace.schema_digest,
            record_version_refs=tuple(sorted(record.version_ref for record in records)),
            snapshot_digest=self.workspace.snapshot_digest(request.record_ids),
            result_refs=tuple(sorted(set(result_refs))),
            would_mutate=would_mutate,
        )


class SyntheticContentShadowConnector:
    """Governance-facing shadow connector with no execution authority."""

    def __init__(self, transport: SyntheticContentWorkspaceTransport) -> None:
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
        return self._observe(action_case, "preview", dry_run=True)

    def dry_run(self, action_case: ContentActionCase) -> ContentShadowEvidence:
        return self._observe(action_case, "simulate", dry_run=True)

    def _observe(
        self,
        action_case: ContentActionCase,
        method_name: str,
        *,
        dry_run: bool,
    ) -> ContentShadowEvidence:
        request = ContentShadowRequest.from_action_case(action_case)
        method = getattr(self._transport, method_name)
        result: ContentShadowResult = method(request)

        if result.snapshot_digest != action_case.content.content_snapshot_digest:
            raise ContentShadowConflict(
                "observed content snapshot does not match proposed Action Case"
            )

        return ContentShadowEvidence(
            action_id=request.action_id,
            operation=result.operation,
            payload_digest=request.payload_digest,
            target_digest=request.target_digest,
            state_binding_digest=request.state_binding_digest,
            observed_snapshot_digest=result.snapshot_digest,
            schema_digest=result.schema_digest,
            record_version_refs=result.record_version_refs,
            outcome=result.status,
            result_refs=result.result_refs,
            would_mutate=result.would_mutate,
            dry_run=dry_run,
        )
