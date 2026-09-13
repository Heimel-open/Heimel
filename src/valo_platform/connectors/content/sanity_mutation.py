"""Sanity conditional mutation transport for governed content operations.

The transport is provider-specific but authority-neutral. It accepts only an
already-cleared canonical ``ContentMutationRequest`` and performs one
revision-conditional Sanity transaction through an injected client. Network
configuration, credentials, retries, clearance, receipts and journaling remain
outside this module.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.action_envelope.bounded_connector import (
    DefiniteProviderFailure,
    IndeterminateProviderFailure,
)
from src.valo_platform.action_envelope.reconciliation import (
    ProviderObservation,
    ProviderResolution,
)
from src.valo_platform.content_operations.actions import ContentOperation

from .protocol import ContentMutationRequest, ContentMutationResult
from .sanity import SanitySchemaSnapshot


_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PROTECTED_ROOTS = frozenset({"_id", "_rev", "_type", "_createdAt", "_updatedAt"})
_SUPPORTED_OPERATIONS = frozenset(
    {ContentOperation.UPDATE_FIELD, ContentOperation.BULK_UPDATE}
)


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _validate_digest(value: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("digest must be lowercase sha256:<64 hex>")
    return value


class SanityPatchVerb(str, Enum):
    SET = "set"
    SET_IF_MISSING = "setIfMissing"
    UNSET = "unset"
    INC = "inc"
    DEC = "dec"


class SanityPatchInstruction(BaseModel):
    """Reference-only patch instruction; values are resolved only in memory."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    verb: SanityPatchVerb
    path: str = Field(min_length=1)
    value_ref: str | None = None
    value_digest: str | None = None

    @field_validator("value_digest")
    @classmethod
    def validate_value_digest(cls, value: str | None) -> str | None:
        return None if value is None else _validate_digest(value)

    @model_validator(mode="after")
    def validate_shape(self) -> "SanityPatchInstruction":
        root = re.split(r"[.\[]", self.path, maxsplit=1)[0]
        if root in _PROTECTED_ROOTS:
            raise ValueError(f"Sanity system field {root} cannot be mutated")
        if self.verb is SanityPatchVerb.UNSET:
            if self.value_ref is not None or self.value_digest is not None:
                raise ValueError("unset instructions cannot carry a value")
        elif not self.value_ref or not self.value_digest:
            raise ValueError(f"{self.verb.value} requires value_ref and value_digest")
        return self


class SanityDocumentPatch(BaseModel):
    """One document patch bound to its exact pre-mutation revision."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    document_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    instructions: tuple[SanityPatchInstruction, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_ambiguous_paths(self) -> "SanityDocumentPatch":
        paths = [instruction.path for instruction in self.instructions]
        if len(set(paths)) != len(paths):
            raise ValueError("a Sanity document patch may mutate each path only once")
        return self


class SanityPatchArtifact(BaseModel):
    """Immutable, digest-bound patch description with no raw values or credentials."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    artifact_version: str = "1"
    change_ref: str = Field(min_length=1)
    content_snapshot_digest: str
    documents: tuple[SanityDocumentPatch, ...] = Field(min_length=1)

    @field_validator("content_snapshot_digest")
    @classmethod
    def validate_snapshot_digest(cls, value: str) -> str:
        return _validate_digest(value)

    @model_validator(mode="after")
    def reject_duplicate_documents(self) -> "SanityPatchArtifact":
        identifiers = [document.document_id for document in self.documents]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Sanity patch document IDs must be unique")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return _digest(self.canonical_payload())


class SanityPatchArtifactResolver(Protocol):
    def resolve(self, change_ref: str) -> SanityPatchArtifact: ...


class SanityPatchValueResolver(Protocol):
    def resolve(self, value_ref: str) -> Any: ...


class SanityMutationTransaction(BaseModel):
    """Transient provider request. It is not a governance artifact or receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    mutations: tuple[Mapping[str, Any], ...] = Field(min_length=1)
    visibility: str = "sync"
    return_ids: bool = True
    dry_run: bool = False

    @model_validator(mode="after")
    def require_safe_execution_shape(self) -> "SanityMutationTransaction":
        if self.visibility != "sync":
            raise ValueError("Sanity mutation visibility must be sync")
        if not self.return_ids:
            raise ValueError("Sanity mutation must return affected document IDs")
        if self.dry_run:
            raise ValueError("cleared mutation transport cannot submit dry-run transactions")
        return self


class SanityMutationResponse(BaseModel):
    """Reference-only response from one submitted Sanity transaction."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    transaction_id: str = Field(min_length=1)
    provider_reference: str = Field(min_length=1)
    status: str = Field(min_length=1)
    document_ids: tuple[str, ...] = Field(min_length=1)
    previous_revisions: tuple[str, ...] = Field(min_length=1)
    current_revisions: tuple[str, ...] = Field(min_length=1)
    snapshot_digest: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    response: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("snapshot_digest")
    @classmethod
    def validate_snapshot_digest(cls, value: str) -> str:
        return _validate_digest(value)


class SanityTransactionStatus(str, Enum):
    COMMITTED = "committed"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class SanityTransactionEvidence(BaseModel):
    """Authoritative read-only provider history used for reconciliation."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    transaction_id: str = Field(min_length=1)
    provider_reference: str | None = None
    project_ref: str = Field(min_length=1)
    dataset_ref: str = Field(min_length=1)
    status: SanityTransactionStatus
    operation: ContentOperation
    document_ids: tuple[str, ...] = Field(min_length=1)
    previous_revisions: tuple[str, ...] = Field(min_length=1)
    current_revisions: tuple[str, ...] = ()
    proposed_change_digest: str
    snapshot_digest: str | None = None
    evidence_refs: tuple[str, ...] = ()
    observed_at: datetime
    response: Mapping[str, Any] = Field(default_factory=dict)

    @field_validator("proposed_change_digest", "snapshot_digest")
    @classmethod
    def validate_digests(cls, value: str | None) -> str | None:
        return None if value is None else _validate_digest(value)

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Sanity transaction evidence timestamp must be timezone-aware")
        return value


class SanityProviderClient(Protocol):
    """Injected Sanity API surface. Implementations own HTTP and credentials."""

    def mutate(self, transaction: SanityMutationTransaction) -> SanityMutationResponse: ...

    def lookup_transaction(
        self,
        *,
        project_ref: str,
        dataset_ref: str,
        transaction_id: str,
    ) -> SanityTransactionEvidence | None: ...


class SanityDefiniteNoEffectError(RuntimeError):
    """Provider proved the transaction had no effect."""


class SanityUnknownEffectError(RuntimeError):
    """Provider call may have had an effect and must be reconciled."""


class SanityConditionalMutationTransport:
    """One-shot Sanity compare-and-set transport with read-only reconciliation."""

    def __init__(
        self,
        *,
        client: SanityProviderClient,
        patch_resolver: SanityPatchArtifactResolver,
        value_resolver: SanityPatchValueResolver,
        project_ref: str,
        dataset_ref: str,
        schema: SanitySchemaSnapshot,
        writes_enabled: bool = False,
    ) -> None:
        if schema.project_ref != project_ref or schema.dataset_ref != dataset_ref:
            raise ValueError("Sanity schema scope does not match mutation transport scope")
        self._client = client
        self._patch_resolver = patch_resolver
        self._value_resolver = value_resolver
        self.project_ref = project_ref
        self.dataset_ref = dataset_ref
        self.schema = schema
        self._writes_enabled = bool(writes_enabled)

    @property
    def writes_enabled(self) -> bool:
        return self._writes_enabled

    def mutate_if_current(
        self, request: ContentMutationRequest
    ) -> ContentMutationResult:
        self._require_scope(request)
        if request.operation not in _SUPPORTED_OPERATIONS:
            raise DefiniteProviderFailure(
                "Sanity first-slice transport supports update_field and bulk_update only"
            )
        if not self._writes_enabled:
            raise DefiniteProviderFailure("Sanity writes are disabled by default")

        artifact = self._resolve_artifact(request)
        transaction = self._build_transaction(request, artifact)
        try:
            response = self._client.mutate(transaction)
        except SanityDefiniteNoEffectError as exc:
            raise DefiniteProviderFailure(str(exc)) from exc
        except SanityUnknownEffectError as exc:
            raise IndeterminateProviderFailure(str(exc)) from exc
        except Exception as exc:
            raise IndeterminateProviderFailure(
                "Sanity mutation call failed after submission may have started"
            ) from exc

        self._require_success_response(request, response)
        return ContentMutationResult(
            provider_reference=response.provider_reference,
            content_system="sanity",
            project_ref=self.project_ref,
            dataset_ref=self.dataset_ref,
            operation=request.operation,
            record_ids=tuple(sorted(response.document_ids)),
            schema_version=self.schema.schema_version,
            previous_version_refs=tuple(sorted(response.previous_revisions)),
            current_version_refs=tuple(sorted(response.current_revisions)),
            observed_snapshot_digest=response.snapshot_digest,
            applied_payload_digest=request.payload_digest,
            applied_target_digest=request.target_digest,
            applied_state_binding_digest=request.state_binding_digest,
            response={
                "status": response.status,
                "transaction_id": response.transaction_id,
                "evidence_refs": list(response.evidence_refs),
                "document_ids": list(sorted(response.document_ids)),
                "current_revisions": list(sorted(response.current_revisions)),
            },
        )

    def lookup(
        self,
        *,
        execution_id: str,
        provider_reference: str | None,
        idempotency_key: str,
    ) -> ProviderObservation:
        """Read provider history only; never retry or submit a mutation."""

        del idempotency_key
        try:
            evidence = self._client.lookup_transaction(
                project_ref=self.project_ref,
                dataset_ref=self.dataset_ref,
                transaction_id=execution_id,
            )
        except Exception as exc:
            return self._unknown(
                {"status": "lookup_error", "error_class": type(exc).__name__}
            )
        if evidence is None or evidence.status is SanityTransactionStatus.UNKNOWN:
            return self._unknown({"status": "unknown"})
        if (
            evidence.transaction_id != execution_id
            or evidence.project_ref != self.project_ref
            or evidence.dataset_ref != self.dataset_ref
        ):
            return self._unknown({"status": "scope_mismatch"})
        if (
            provider_reference not in {None, "unavailable", evidence.provider_reference}
            or not evidence.provider_reference
            or not evidence.evidence_refs
        ):
            return self._unknown({"status": "reference_or_evidence_mismatch"})

        common_effect = {
            "content_system": "sanity",
            "project_ref": evidence.project_ref,
            "dataset_ref": evidence.dataset_ref,
            "operation": evidence.operation.value,
            "record_ids": list(sorted(evidence.document_ids)),
            "source_version_refs": list(sorted(evidence.previous_revisions)),
            "proposed_change_digest": evidence.proposed_change_digest,
        }
        if evidence.status is SanityTransactionStatus.COMMITTED:
            if (
                not evidence.current_revisions
                or len(evidence.current_revisions) != len(evidence.document_ids)
                or evidence.snapshot_digest is None
            ):
                return self._unknown({"status": "incomplete_committed_evidence"})
            resolution = ProviderResolution.CONFIRMED_SUCCEEDED
            observed_effect = {
                "effect": "mutation_applied",
                **common_effect,
                "current_version_refs": list(sorted(evidence.current_revisions)),
                "observed_snapshot_digest": evidence.snapshot_digest,
            }
        else:
            if evidence.current_revisions:
                return self._unknown({"status": "rejected_with_current_revisions"})
            resolution = ProviderResolution.CONFIRMED_NO_EFFECT
            observed_effect = {
                "effect": "confirmed_absent",
                **common_effect,
            }

        return ProviderObservation(
            resolution=resolution,
            provider_reference=evidence.provider_reference,
            observed_effect=observed_effect,
            evidence_refs=tuple(evidence.evidence_refs),
            measurement_method="sanity-transaction-history",
            observed_at=evidence.observed_at,
            response={
                "status": evidence.status.value,
                "transaction_id": evidence.transaction_id,
            },
        )

    def _resolve_artifact(self, request: ContentMutationRequest) -> SanityPatchArtifact:
        try:
            artifact = self._patch_resolver.resolve(request.proposed_change_ref)
        except Exception as exc:
            raise DefiniteProviderFailure(
                "Sanity patch artifact could not be resolved before mutation"
            ) from exc
        if artifact.change_ref != request.proposed_change_ref:
            raise DefiniteProviderFailure("Sanity patch artifact reference mismatch")
        if artifact.digest() != request.proposed_change_digest:
            raise DefiniteProviderFailure("Sanity patch artifact digest mismatch")
        if artifact.content_snapshot_digest != request.content_snapshot_digest:
            raise DefiniteProviderFailure("Sanity patch snapshot binding mismatch")

        documents = tuple(sorted(artifact.documents, key=lambda item: item.document_id))
        if tuple(item.document_id for item in documents) != tuple(sorted(request.record_ids)):
            raise DefiniteProviderFailure("Sanity patch document scope mismatch")
        if tuple(sorted(item.source_revision for item in documents)) != tuple(
            sorted(request.source_version_refs)
        ):
            raise DefiniteProviderFailure("Sanity patch source revision mismatch")
        return artifact

    def _build_transaction(
        self,
        request: ContentMutationRequest,
        artifact: SanityPatchArtifact,
    ) -> SanityMutationTransaction:
        mutations: list[Mapping[str, Any]] = []
        for document in sorted(artifact.documents, key=lambda item: item.document_id):
            patch: dict[str, Any] = {
                "id": document.document_id,
                "ifRevisionID": document.source_revision,
            }
            grouped: dict[str, Any] = {
                "set": {},
                "setIfMissing": {},
                "unset": [],
                "inc": {},
                "dec": {},
            }
            for instruction in document.instructions:
                if instruction.verb is SanityPatchVerb.UNSET:
                    grouped["unset"].append(instruction.path)
                    continue
                assert instruction.value_ref is not None
                assert instruction.value_digest is not None
                try:
                    value = self._value_resolver.resolve(instruction.value_ref)
                except Exception as exc:
                    raise DefiniteProviderFailure(
                        f"Sanity patch value could not be resolved for {instruction.path}"
                    ) from exc
                if _digest(value) != instruction.value_digest:
                    raise DefiniteProviderFailure(
                        f"Sanity patch value digest mismatch for {instruction.path}"
                    )
                if instruction.verb in {SanityPatchVerb.INC, SanityPatchVerb.DEC} and (
                    isinstance(value, bool) or not isinstance(value, (int, float))
                ):
                    raise DefiniteProviderFailure(
                        f"Sanity {instruction.verb.value} requires a numeric value"
                    )
                grouped[instruction.verb.value][instruction.path] = value
            for key, value in grouped.items():
                if value:
                    patch[key] = value
            mutations.append({"patch": patch})
        return SanityMutationTransaction(
            project_ref=self.project_ref,
            dataset_ref=self.dataset_ref,
            transaction_id=request.execution_id,
            mutations=tuple(mutations),
        )

    def _require_scope(self, request: ContentMutationRequest) -> None:
        expected = (
            "sanity",
            self.project_ref,
            self.dataset_ref,
            self.schema.schema_version,
        )
        actual = (
            request.content_system,
            request.project_ref,
            request.dataset_ref,
            request.schema_version,
        )
        if actual != expected:
            raise DefiniteProviderFailure(
                "Sanity project, dataset or schema scope mismatch; no effect occurred"
            )

    @staticmethod
    def _require_success_response(
        request: ContentMutationRequest,
        response: SanityMutationResponse,
    ) -> None:
        if response.status != "committed":
            raise IndeterminateProviderFailure(
                "Sanity response did not prove a committed transaction"
            )
        expected = (
            request.execution_id,
            tuple(sorted(request.record_ids)),
            tuple(sorted(request.source_version_refs)),
        )
        actual = (
            response.transaction_id,
            tuple(sorted(response.document_ids)),
            tuple(sorted(response.previous_revisions)),
        )
        if actual != expected:
            raise IndeterminateProviderFailure(
                "Sanity response does not bind the cleared transaction"
            )
        if (
            len(response.current_revisions) != len(request.record_ids)
            or any(not revision for revision in response.current_revisions)
        ):
            raise IndeterminateProviderFailure(
                "Sanity response is missing provider-generated revisions"
            )
        if not response.provider_reference or not response.evidence_refs:
            raise IndeterminateProviderFailure(
                "Sanity response is missing transaction evidence"
            )

    @staticmethod
    def _unknown(response: Mapping[str, Any]) -> ProviderObservation:
        return ProviderObservation(
            resolution=ProviderResolution.UNKNOWN,
            provider_reference=None,
            observed_effect={},
            evidence_refs=(),
            measurement_method="sanity-transaction-history",
            observed_at=datetime.now(timezone.utc),
            response=dict(response),
        )
