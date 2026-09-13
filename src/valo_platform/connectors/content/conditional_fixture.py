"""Deterministic provider-neutral compare-and-set mutation fixture.

The fixture exists only for boundary tests and reference demos. It stores no raw
content, requires no credentials, performs no network calls, and raises a
definite provider failure before mutation whenever exact preconditions fail.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable

import rfc8785

from src.valo_platform.action_envelope.bounded_connector import DefiniteProviderFailure
from src.valo_platform.action_envelope.reconciliation import (
    ProviderObservation,
    ProviderResolution,
)

from .protocol import ContentMutationRequest, ContentMutationResult


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


@dataclass(frozen=True)
class ConditionalContentRecord:
    """Reference-only provider record state."""

    record_id: str
    version_ref: str
    snapshot_digest: str

    def __post_init__(self) -> None:
        if not self.record_id or not self.version_ref:
            raise ValueError("record_id and version_ref are required")
        if not _SHA256.fullmatch(self.snapshot_digest):
            raise ValueError("snapshot_digest must be lowercase sha256:<64 hex>")


class ConditionalContentFixtureTransport:
    """In-memory conditional transport with exact precondition enforcement."""

    def __init__(
        self,
        *,
        content_system: str,
        workspace_ref: str,
        project_ref: str,
        dataset_ref: str,
        schema_version: str,
        records: Iterable[ConditionalContentRecord],
    ) -> None:
        values = tuple(records)
        by_id = {record.record_id: record for record in values}
        if not content_system or not workspace_ref or not project_ref or not dataset_ref:
            raise ValueError("fixture scope is incomplete")
        if not schema_version:
            raise ValueError("schema_version is required")
        if not values or len(by_id) != len(values):
            raise ValueError("fixture requires unique records")
        self.content_system = content_system
        self.workspace_ref = workspace_ref
        self.project_ref = project_ref
        self.dataset_ref = dataset_ref
        self.schema_version = schema_version
        self._records = by_id
        self._observations: dict[str, tuple[str, ProviderObservation]] = {}
        self.attempts: list[ContentMutationRequest] = []
        self.lookup_calls: list[tuple[str, str | None, str]] = []
        self.successful_mutations = 0

    def records(self) -> tuple[ConditionalContentRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def snapshot_digest(self, record_ids: tuple[str, ...]) -> str:
        selected = self._selected(record_ids)
        return _digest(
            {
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
                    for record in selected
                ],
            }
        )

    def mutate_if_current(
        self, request: ContentMutationRequest
    ) -> ContentMutationResult:
        self.attempts.append(request)
        try:
            self._require_scope(request)
            selected = self._selected(request.record_ids)
            current_versions = tuple(sorted(record.version_ref for record in selected))
            if current_versions != tuple(sorted(request.source_version_refs)):
                raise DefiniteProviderFailure(
                    "provider source-version precondition failed; no effect occurred"
                )
            if self.snapshot_digest(request.record_ids) != request.content_snapshot_digest:
                raise DefiniteProviderFailure(
                    "provider snapshot precondition failed; no effect occurred"
                )
            if len(request.target_version_refs) != len(request.record_ids):
                raise DefiniteProviderFailure(
                    "fixture requires one exact target version per record"
                )

            target_versions = tuple(sorted(request.target_version_refs))
            record_ids = tuple(sorted(request.record_ids))
            previous_versions = current_versions
            for record_id, target_version in zip(record_ids, target_versions, strict=True):
                current = self._records[record_id]
                transitioned_snapshot = _digest(
                    {
                        "previous_snapshot_digest": current.snapshot_digest,
                        "proposed_change_digest": request.proposed_change_digest,
                        "target_version_ref": target_version,
                        "operation": request.operation.value,
                    }
                )
                self._records[record_id] = replace(
                    current,
                    version_ref=target_version,
                    snapshot_digest=transitioned_snapshot,
                )

            self.successful_mutations += 1
            observed_snapshot = self.snapshot_digest(request.record_ids)
            provider_reference = "fixture:mutation:" + _digest(
                {
                    "execution_id": request.execution_id,
                    "idempotency_key": request.idempotency_key,
                    "observed_snapshot_digest": observed_snapshot,
                }
            )[7:23]
            response = {
                "status": "applied",
                "result_ref": provider_reference,
                "observed_snapshot_digest": observed_snapshot,
            }
            result = ContentMutationResult(
                provider_reference=provider_reference,
                content_system=self.content_system,
                project_ref=self.project_ref,
                dataset_ref=self.dataset_ref,
                operation=request.operation,
                record_ids=record_ids,
                schema_version=self.schema_version,
                previous_version_refs=previous_versions,
                current_version_refs=target_versions,
                observed_snapshot_digest=observed_snapshot,
                applied_payload_digest=request.payload_digest,
                applied_target_digest=request.target_digest,
                applied_state_binding_digest=request.state_binding_digest,
                response=response,
            )
            self._observations[request.execution_id] = (
                request.idempotency_key,
                ProviderObservation(
                    resolution=ProviderResolution.CONFIRMED_SUCCEEDED,
                    provider_reference=provider_reference,
                    observed_effect={
                        "effect": "mutation_applied",
                        "execution_id": request.execution_id,
                        "content_system": request.content_system,
                        "project_ref": request.project_ref,
                        "dataset_ref": request.dataset_ref,
                        "operation": request.operation.value,
                        "record_ids": list(record_ids),
                        "source_version_refs": list(previous_versions),
                        "current_version_refs": list(target_versions),
                        "proposed_change_digest": request.proposed_change_digest,
                        "observed_snapshot_digest": observed_snapshot,
                        "payload_digest": request.payload_digest,
                        "target_digest": request.target_digest,
                    },
                    evidence_refs=(
                        "fixture:mutation-evidence:" + request.execution_id,
                    ),
                    measurement_method="fixture-recorded-conditional-mutation",
                    observed_at=datetime.now(timezone.utc),
                    response=response,
                ),
            )
            return result
        except DefiniteProviderFailure as exc:
            provider_reference = "fixture:no-effect:" + _digest(
                {
                    "execution_id": request.execution_id,
                    "idempotency_key": request.idempotency_key,
                    "reason": str(exc),
                }
            )[7:23]
            self._observations[request.execution_id] = (
                request.idempotency_key,
                ProviderObservation(
                    resolution=ProviderResolution.CONFIRMED_NO_EFFECT,
                    provider_reference=provider_reference,
                    observed_effect={
                        "effect": "confirmed_absent",
                        "execution_id": request.execution_id,
                        "content_system": request.content_system,
                        "project_ref": request.project_ref,
                        "dataset_ref": request.dataset_ref,
                        "operation": request.operation.value,
                        "record_ids": list(sorted(request.record_ids)),
                        "source_version_refs": list(
                            sorted(request.source_version_refs)
                        ),
                        "proposed_change_digest": request.proposed_change_digest,
                        "reason": str(exc),
                    },
                    evidence_refs=(
                        "fixture:no-effect-evidence:" + request.execution_id,
                    ),
                    measurement_method="fixture-recorded-precondition-failure",
                    observed_at=datetime.now(timezone.utc),
                    response={"status": "no_effect", "error": str(exc)},
                ),
            )
            raise

    def lookup(
        self,
        *,
        execution_id: str,
        provider_reference: str | None,
        idempotency_key: str,
    ) -> ProviderObservation:
        """Return recorded evidence only; never execute or retry a mutation."""

        self.lookup_calls.append((execution_id, provider_reference, idempotency_key))
        recorded = self._observations.get(execution_id)
        if recorded is not None:
            recorded_key, observation = recorded
            reference_matches = provider_reference in {
                None,
                "unavailable",
                observation.provider_reference,
            }
            if recorded_key == idempotency_key and reference_matches:
                return observation
        return ProviderObservation(
            resolution=ProviderResolution.UNKNOWN,
            provider_reference=None,
            observed_effect={},
            evidence_refs=(),
            measurement_method="fixture-recorded-conditional-mutation",
            observed_at=datetime.now(timezone.utc),
            response={"status": "unknown"},
        )

    def _require_scope(self, request: ContentMutationRequest) -> None:
        expected = (
            self.content_system,
            self.workspace_ref,
            self.project_ref,
            self.dataset_ref,
            self.schema_version,
        )
        actual = (
            request.content_system,
            request.workspace_ref,
            request.project_ref,
            request.dataset_ref,
            request.schema_version,
        )
        if actual != expected:
            raise DefiniteProviderFailure(
                "provider scope or schema precondition failed; no effect occurred"
            )
        if not request.operation.requires_mutation_clearance:
            raise DefiniteProviderFailure("observation operation cannot mutate provider")

    def _selected(
        self, record_ids: tuple[str, ...]
    ) -> tuple[ConditionalContentRecord, ...]:
        missing = set(record_ids) - set(self._records)
        if missing:
            raise DefiniteProviderFailure(
                "provider records missing; no effect occurred: "
                + ", ".join(sorted(missing))
            )
        return tuple(self._records[record_id] for record_id in sorted(record_ids))
