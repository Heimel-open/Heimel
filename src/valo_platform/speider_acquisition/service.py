"""Speider-controlled execution of approved, pinned Apify Actors."""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from .models import (
    AcquisitionEvent,
    AcquisitionRequest,
    ProviderRunHandle,
    ProviderRunState,
    ProviderRunStatus,
    ProvenanceStep,
)
from .provider import (
    AcquisitionProvider,
    AcquisitionProviderError,
    ProviderAcquisitionRequest,
)
from .registry import ActorRegistry


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _mechanically_relevant(value: Any) -> bool:
    """Drop only empty mappings; preserve every other acquired value."""
    return bool(value) if isinstance(value, dict) else True


def _normalize(value: Any) -> Any:
    """Representation-only normalization; no inference, scoring, or conclusion."""
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        normalized = [_normalize(item) for item in value]
        return [item for item in normalized if _mechanically_relevant(item)]
    return value


class SpeiderAcquisitionService:
    """Collection control plane between an approved registry and BARO.

    Speider selects and validates collection, invokes only the pinned Actor, performs
    representation-only normalization, preserves provenance, and forwards candidate
    acquisition facts. It does not analyse or make governance decisions.
    """

    SCHEMA_VERSION = "speider.acquisition.v1"

    def __init__(
        self,
        registry: ActorRegistry,
        provider: AcquisitionProvider,
        *,
        baro_sink: Callable[[AcquisitionEvent], Any] | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self._registry = registry
        self._provider = provider
        self._baro_sink = baro_sink
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic or time.monotonic
        self._sleeper = sleeper or time.sleep
        if not math.isfinite(poll_interval_seconds) or poll_interval_seconds <= 0:
            raise ValueError("poll interval must be finite and positive")
        self._poll_interval_seconds = poll_interval_seconds

    def acquire(self, request: AcquisitionRequest) -> AcquisitionEvent:
        entry, grant = self._registry.authorize_run(request)
        request_input_hash = _hash(request.actor_input)
        provider_request = ProviderAcquisitionRequest(
            request_id=request.request_id,
            registry_entry_ref=entry.registry_entry_id,
            actor_id=entry.actor_id,
            actor_version=entry.pinned_version,
            actor_input=request.actor_input,
            requested_source=request.requested_source,
            source_platform=request.source_platform,
            tenant_id=request.tenant_id,
            correlation_id=request.correlation_id,
            timeout_seconds=request.timeout_seconds,
            max_cost_usd=request.cost_ceiling_usd,
            resource_limits=dict(entry.resource_limits),
            authorization_grant=grant,
        )
        handle = None
        try:
            self._provider.validate_request(provider_request)
            estimate = self._provider.estimate_cost(provider_request)
            if (
                isinstance(estimate.amount_usd, bool)
                or not isinstance(estimate.amount_usd, (int, float))
                or not math.isfinite(float(estimate.amount_usd))
                or estimate.amount_usd < 0
                or estimate.amount_usd > request.cost_ceiling_usd
                or estimate.amount_usd > entry.max_cost_usd
                or not estimate.is_hard_ceiling
            ):
                raise AcquisitionProviderError(
                    "provider cost estimate is not a verifiable hard ceiling"
                )
            handle = self._provider.start_run(provider_request)
            status = self._wait_for_terminal(handle, request.timeout_seconds)
            if status.state is not ProviderRunState.SUCCEEDED:
                raise AcquisitionProviderError(
                    f"provider run did not succeed: {status.state.value}"
                )
            status_cost = status.cost_metadata.get("total_usd")
            if (
                isinstance(status_cost, bool)
                or not isinstance(status_cost, (int, float))
                or not math.isfinite(float(status_cost))
                or status_cost > request.cost_ceiling_usd
                or status_cost > entry.max_cost_usd
            ):
                raise AcquisitionProviderError("provider run cost cannot be verified")
            result = self._provider.fetch_dataset(handle)
            if (
                result.provider_name != self._provider.provider_name
                or result.run_id != handle.run_id
                or result.actor_id != handle.actor_id
                or result.actor_version != handle.actor_version
                or (
                    status.dataset_ref is not None
                    and result.dataset_ref != status.dataset_ref
                )
            ):
                raise AcquisitionProviderError(
                    "provider raw record identity does not match run evidence"
                )
            self._registry.validate_result(entry, request, result)
        except Exception:
            if handle is not None:
                try:
                    self._provider.cancel_run(handle)
                except Exception:
                    pass
            raise

        raw_hash = _hash(result.raw_payload)
        normalized_payload = _normalize(result.raw_payload)
        normalized_hash = _hash(normalized_payload)
        changed = _canonical_json(result.raw_payload) != _canonical_json(
            normalized_payload
        )
        emitted_at = self._now().isoformat()

        request_evidence = {
            "request_id": request.request_id,
            "registry_entry_ref": request.registry_entry_ref,
            "actor_id": entry.actor_id,
            "actor_version": entry.pinned_version,
            "requester_id": request.requester_id,
            "authority_ref": request.authority_ref,
            "purpose": request.purpose,
            "tenant_id": request.tenant_id,
            "organizational_context": request.organizational_context,
            "source": request.requested_source,
            "source_platform": request.source_platform,
            "actor_input": request.actor_input,
            "input_hash": request_input_hash,
            "requested_at": request.requested_at,
            "deadline_at": request.deadline_at,
            "timeout_seconds": request.timeout_seconds,
            "cost_ceiling_usd": request.cost_ceiling_usd,
        }
        execution_evidence = {
            "actor_id": result.actor_id,
            "actor_version": result.actor_version,
            "provider": result.provider_name,
            "provider_run_id": result.run_id,
            "dataset_ref": result.dataset_ref,
            "source": result.source_identifier,
            "source_platform": result.source_platform,
            "requester_id": request.requester_id,
            "purpose": request.purpose,
            "executed_at": result.executed_at,
            "retrieved_at": result.retrieved_at,
            "cost_metadata": result.cost_metadata,
            "execution_metadata": result.execution_metadata,
            "collection_errors": list(result.collection_errors),
        }
        normalization_evidence = {
            "raw_payload_hash": raw_hash,
            "normalized_payload_hash": normalized_hash,
            "normalization_changed": changed,
            "schema_version": self.SCHEMA_VERSION,
        }
        provenance = (
            ProvenanceStep(
                stage="request",
                timestamp=request.requested_at,
                evidence=request_evidence,
                evidence_hash=_hash(request_evidence),
            ),
            ProvenanceStep(
                stage="actor_execution",
                timestamp=result.executed_at,
                evidence=execution_evidence,
                evidence_hash=_hash(execution_evidence),
            ),
            ProvenanceStep(
                stage="normalization",
                timestamp=emitted_at,
                evidence=normalization_evidence,
                evidence_hash=_hash(normalization_evidence),
            ),
        )

        raw_item_count = len(result.payload) if isinstance(result.payload, list) else 1
        item_count = (
            len(normalized_payload) if isinstance(normalized_payload, list) else 1
        )
        source_count = 0
        if isinstance(normalized_payload, list):
            source_count = sum(
                1
                for item in normalized_payload
                if isinstance(item, dict) and bool(item.get("source_url"))
            )
        collection_integrity_confidence = (
            1.0
            if not result.collection_errors
            else max(0.0, 1.0 - len(result.collection_errors) / max(raw_item_count, 1))
        )
        quality_indicators = {
            "schema_valid": True,
            "raw_item_count": raw_item_count,
            "retained_item_count": item_count,
            "items_with_source": source_count,
            "source_coverage": source_count / item_count if item_count else 0.0,
            "collection_integrity_confidence": collection_integrity_confidence,
        }
        event = AcquisitionEvent(
            acquisition_id=f"acq:{uuid4().hex}",
            request_id=request.request_id,
            registry_entry_ref=entry.registry_entry_id,
            actor_id=result.actor_id,
            actor_version=result.actor_version,
            provider_name=result.provider_name,
            provider_run_id=result.run_id,
            dataset_reference=result.dataset_ref,
            source_url_or_identifier=result.source_identifier,
            source_platform=result.source_platform,
            retrieval_timestamp=result.retrieved_at,
            actor_execution_timestamp=result.executed_at,
            normalized_payload=normalized_payload,
            payload_reference=result.dataset_ref,
            content_hash=normalized_hash,
            schema_version=self.SCHEMA_VERSION,
            provenance_chain=provenance,
            quality_indicators=quality_indicators,
            collection_errors=result.collection_errors,
            cost_metadata=result.cost_metadata,
            correlation_id=request.correlation_id,
            tenant_id=request.tenant_id,
            organizational_context=request.organizational_context,
            request_input_hash=request_input_hash,
            raw_payload_reference=result.dataset_ref,
            raw_payload_hash=raw_hash,
            normalized_payload_hash=normalized_hash,
            normalization_changed=changed,
            collection_integrity_confidence=collection_integrity_confidence,
            retention_rule=entry.retention_rule,
            emitted_at=emitted_at,
        )
        if self._baro_sink is not None:
            self._baro_sink(event)
        return event

    def _wait_for_terminal(
        self, handle: ProviderRunHandle, timeout_seconds: int
    ) -> ProviderRunStatus:
        started = self._monotonic()
        while True:
            status = self._provider.get_run_status(handle)
            if status.handle != handle:
                raise AcquisitionProviderError(
                    "provider status handle does not match run"
                )
            if status.state not in {ProviderRunState.PENDING, ProviderRunState.RUNNING}:
                return status
            elapsed = self._monotonic() - started
            if elapsed >= timeout_seconds:
                raise AcquisitionProviderError("provider run timed out")
            self._sleeper(
                min(self._poll_interval_seconds, max(0.0, timeout_seconds - elapsed))
            )

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("Speider acquisition clock must be timezone-aware")
        return value.astimezone(timezone.utc)
