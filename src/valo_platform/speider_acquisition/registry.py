"""Governed Actor registry and collection-constraint validation for Speider."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from math import isfinite
import secrets
from threading import RLock
from typing import Any, Callable, TypeGuard
from urllib.parse import urlparse

from .models import (
    AcquisitionRequest,
    ActorLifecycleState,
    ActorLifecycleTransition,
    ActorRegistryEntry,
    RawAcquisitionRecord,
    RegistryExecutionGrant,
)


class AcquisitionConstraintError(ValueError):
    """Fail-closed rejection of unverifiable or out-of-policy collection."""


_ALLOWED_TRANSITIONS = {
    ActorLifecycleState.PROPOSED: {ActorLifecycleState.REVIEW},
    ActorLifecycleState.REVIEW: {ActorLifecycleState.APPROVED},
    ActorLifecycleState.APPROVED: {
        ActorLifecycleState.SUSPENDED,
        ActorLifecycleState.REVOKED,
    },
    ActorLifecycleState.SUSPENDED: {
        ActorLifecycleState.APPROVED,
        ActorLifecycleState.REVOKED,
    },
    ActorLifecycleState.REVOKED: set(),
}

_REQUIRED_PROVENANCE = {
    "actor_id",
    "actor_version",
    "requester_id",
    "purpose",
    "source",
    "input_hash",
    "dataset_ref",
}

_SCHEMA_TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}
_SCHEMA_KEYWORDS = {
    "object": {"type", "enum", "properties", "required", "additionalProperties"},
    "array": {"type", "enum", "items"},
    "string": {"type", "enum"},
    "integer": {"type", "enum"},
    "number": {"type", "enum"},
    "boolean": {"type", "enum"},
    "null": {"type", "enum"},
}


def _finite_number(value: object) -> TypeGuard[int | float]:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def _schema_definition_errors(schema: Any, path: str = "$schema") -> list[str]:
    if not isinstance(schema, dict) or schema.get("type") not in _SCHEMA_TYPES:
        return [f"{path}: unsupported or missing type"]
    schema_type = schema["type"]
    unsupported = set(schema) - _SCHEMA_KEYWORDS[schema_type]
    if unsupported:
        names = ", ".join(sorted(str(item) for item in unsupported))
        return [f"{path}: unsupported schema keyword(s): {names}"]
    errors: list[str] = []
    if schema_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            return [f"{path}: invalid object definition"]
        if any(not isinstance(key, str) for key in properties):
            errors.append(f"{path}: property names must be strings")
        if any(not isinstance(key, str) for key in required):
            errors.append(f"{path}: required fields must be strings")
        if "additionalProperties" in schema and not isinstance(
            schema["additionalProperties"], bool
        ):
            errors.append(f"{path}: additionalProperties must be boolean")
        if any(isinstance(key, str) and key not in properties for key in required):
            errors.append(f"{path}: required field has no property schema")
        for key, child in properties.items():
            errors.extend(_schema_definition_errors(child, f"{path}.properties.{key}"))
    if schema["type"] == "array" and "items" in schema:
        errors.extend(_schema_definition_errors(schema["items"], f"{path}.items"))
    if "enum" in schema and not isinstance(schema["enum"], list):
        errors.append(f"{path}: enum must be a list")
    return errors


def _parse_timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise AcquisitionConstraintError(f"{label} cannot be verified") from exc
    if parsed.tzinfo is None:
        raise AcquisitionConstraintError(f"{label} must include timezone")
    return parsed.astimezone(timezone.utc)


def _embedded_http_sources(value: Any) -> tuple[str, ...]:
    """Return every HTTP(S) source reference nested in provider input."""
    found: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for nested in item.values():
                visit(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                visit(nested)
        elif isinstance(item, str):
            parsed = urlparse(item)
            if parsed.scheme.lower() in {"http", "https"} and parsed.hostname:
                found.append(item)

    visit(value)
    return tuple(found)


def _schema_errors(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    if not isinstance(schema, dict) or "type" not in schema:
        return [f"{path}: schema type is not verifiable"]

    expected = schema["type"]
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "null": type(None),
    }
    expected_type = type_map.get(expected)
    if expected_type is None:
        return [f"{path}: unsupported schema type {expected!r}"]
    if expected == "integer" and isinstance(value, bool):
        return [f"{path}: expected integer"]
    if expected == "number" and isinstance(value, bool):
        return [f"{path}: expected number"]
    if not isinstance(value, expected_type):
        return [f"{path}: expected {expected}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: value is outside enum"]

    errors: list[str] = []
    if expected == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list):
            return [f"{path}: object schema cannot be verified"]
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: required property missing")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}.{key}: additional property not allowed")
        for key, child in properties.items():
            if key in value:
                errors.extend(_schema_errors(value[key], child, f"{path}.{key}"))
    elif expected == "array":
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, item_schema, f"{path}[{index}]"))
    return errors


class ActorRegistry:
    """In-memory Speider control plane for approved, pinned Actor execution."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._entries: dict[str, ActorRegistryEntry] = {}
        self._history: dict[str, list[ActorLifecycleTransition]] = {}
        self._run_history: dict[tuple[str, str], list[datetime]] = {}
        self._execution_grants: dict[str, RegistryExecutionGrant] = {}
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = RLock()

    def register(self, entry: ActorRegistryEntry) -> ActorRegistryEntry:
        if entry.registry_entry_id in self._entries:
            raise AcquisitionConstraintError("registry entry already exists")
        if entry.lifecycle_state is not ActorLifecycleState.PROPOSED:
            raise AcquisitionConstraintError("new registry entry must be PROPOSED")
        self._entries[entry.registry_entry_id] = entry
        self._history[entry.registry_entry_id] = []
        return entry

    def get(self, registry_entry_id: str) -> ActorRegistryEntry:
        try:
            return self._entries[registry_entry_id]
        except KeyError as exc:
            raise AcquisitionConstraintError(
                "registry entry cannot be verified"
            ) from exc

    def history(self, registry_entry_id: str) -> tuple[ActorLifecycleTransition, ...]:
        self.get(registry_entry_id)
        return tuple(self._history[registry_entry_id])

    def transition(
        self,
        registry_entry_id: str,
        target: ActorLifecycleState,
        *,
        changed_by: str,
        authority_ref: str,
        reason: str,
    ) -> ActorRegistryEntry:
        with self._lock:
            return self._transition_unlocked(
                registry_entry_id,
                target,
                changed_by=changed_by,
                authority_ref=authority_ref,
                reason=reason,
            )

    def _transition_unlocked(
        self,
        registry_entry_id: str,
        target: ActorLifecycleState,
        *,
        changed_by: str,
        authority_ref: str,
        reason: str,
    ) -> ActorRegistryEntry:
        entry = self.get(registry_entry_id)
        if target not in _ALLOWED_TRANSITIONS[entry.lifecycle_state]:
            raise AcquisitionConstraintError(
                f"invalid lifecycle transition {entry.lifecycle_state.value} -> {target.value}"
            )
        if not changed_by or not reason or authority_ref != entry.approval_authority:
            raise AcquisitionConstraintError("approval authority cannot be verified")
        if target is ActorLifecycleState.APPROVED:
            self._validate_approvable(entry)

        changed_at = self._now().isoformat()
        revoked_at = (
            changed_at if target is ActorLifecycleState.REVOKED else entry.revoked_at
        )
        revocation_authority = (
            authority_ref
            if target is ActorLifecycleState.REVOKED
            else entry.revocation_authority_ref
        )
        updated = replace(
            entry,
            lifecycle_state=target,
            updated_at=changed_at,
            revoked_at=revoked_at,
            revocation_authority_ref=revocation_authority,
        )
        self._entries[registry_entry_id] = updated
        self._history[registry_entry_id].append(
            ActorLifecycleTransition(
                registry_entry_id=registry_entry_id,
                from_state=entry.lifecycle_state,
                to_state=target,
                changed_by=changed_by,
                authority_ref=authority_ref,
                reason=reason,
                changed_at=changed_at,
            )
        )
        stale_tokens = [
            token
            for token, grant in self._execution_grants.items()
            if grant.registry_entry_ref == registry_entry_id
        ]
        for token in stale_tokens:
            self._execution_grants.pop(token, None)
        return updated

    def validate_request(self, request: AcquisitionRequest) -> ActorRegistryEntry:
        entry = self.get(request.registry_entry_ref)
        now = self._now()
        if (
            entry.lifecycle_state is not ActorLifecycleState.APPROVED
            or entry.is_revoked
        ):
            raise AcquisitionConstraintError(
                "Actor does not have active approved status"
            )
        self._validate_approvable(entry)
        if _parse_timestamp(entry.review_date, "review date") < now:
            raise AcquisitionConstraintError("Actor review date has expired")
        if request.actor_id != entry.actor_id:
            raise AcquisitionConstraintError("actor identifier does not match registry")
        if request.actor_version != entry.pinned_version:
            raise AcquisitionConstraintError("pinned version does not match registry")
        if not request.requester_id or not request.purpose:
            raise AcquisitionConstraintError(
                "request authority and purpose are required"
            )
        if request.authority_ref != entry.approval_authority:
            raise AcquisitionConstraintError("request authority is not approved")
        if request.tenant_id not in entry.permitted_tenant_ids:
            raise AcquisitionConstraintError("tenant scope is not permitted")
        if not self.source_permitted(
            entry, request.requested_source, request.source_platform
        ):
            raise AcquisitionConstraintError("permitted source constraint failed")
        errors = _schema_errors(request.actor_input, entry.allowed_input_schema)
        if errors:
            raise AcquisitionConstraintError(
                f"input schema validation failed: {errors[0]}"
            )
        for embedded_source in _embedded_http_sources(request.actor_input):
            if not self.source_permitted(
                entry, embedded_source, request.source_platform
            ):
                raise AcquisitionConstraintError(
                    "Actor input source is outside registry scope"
                )
        if (
            not _finite_number(request.cost_ceiling_usd)
            or request.cost_ceiling_usd <= 0
            or request.cost_ceiling_usd > entry.max_cost_usd
        ):
            raise AcquisitionConstraintError("cost ceiling exceeds registry limit")
        max_timeout = entry.resource_limits.get("max_timeout_seconds")
        if not isinstance(max_timeout, int) or request.timeout_seconds <= 0:
            raise AcquisitionConstraintError("timeout limit cannot be verified")
        if request.timeout_seconds > max_timeout:
            raise AcquisitionConstraintError("timeout exceeds registry limit")
        deadline = _parse_timestamp(request.deadline_at, "deadline")
        if (
            deadline <= now
            or now + timedelta(seconds=request.timeout_seconds) > deadline
        ):
            raise AcquisitionConstraintError("deadline or timeout window is invalid")
        self._validate_frequency(entry, request.tenant_id, now)
        return entry

    def authorize_run(
        self, request: AcquisitionRequest
    ) -> tuple[ActorRegistryEntry, RegistryExecutionGrant]:
        """Atomically validate, reserve frequency capacity, and mint one run grant."""
        with self._lock:
            entry = self.validate_request(request)
            self.record_run(entry, request.tenant_id)
            deadline = min(
                _parse_timestamp(request.deadline_at, "deadline"),
                self._now() + timedelta(seconds=request.timeout_seconds),
            )
            grant = RegistryExecutionGrant(
                token=secrets.token_urlsafe(32),
                request_id=request.request_id,
                registry_entry_ref=entry.registry_entry_id,
                actor_id=entry.actor_id,
                actor_version=entry.pinned_version,
                source_identifier=request.requested_source,
                tenant_id=request.tenant_id,
                expires_at=deadline.isoformat(),
            )
            self._execution_grants[grant.token] = grant
            return entry, grant

    def verify_execution_grant(self, provider_request: Any, consume: bool) -> bool:
        """Verify a one-time capability; Apify consumes it immediately before start."""
        with self._lock:
            supplied = getattr(provider_request, "authorization_grant", None)
            token = getattr(supplied, "token", None)
            stored = (
                self._execution_grants.get(token) if isinstance(token, str) else None
            )
            if stored is None or stored != supplied:
                return False
            try:
                entry = self.get(stored.registry_entry_ref)
                valid = (
                    entry.lifecycle_state is ActorLifecycleState.APPROVED
                    and not entry.is_revoked
                    and _parse_timestamp(stored.expires_at, "execution grant expiry")
                    >= self._now()
                    and stored.request_id == provider_request.request_id
                    and stored.registry_entry_ref == provider_request.registry_entry_ref
                    and stored.actor_id == provider_request.actor_id == entry.actor_id
                    and stored.actor_version
                    == provider_request.actor_version
                    == entry.pinned_version
                    and stored.source_identifier == provider_request.requested_source
                    and stored.tenant_id == provider_request.tenant_id
                )
            except (AcquisitionConstraintError, AttributeError):
                return False
            if not valid:
                return False
            if consume:
                del self._execution_grants[stored.token]
            return True

    def record_run(self, entry: ActorRegistryEntry, tenant_id: str) -> None:
        self._run_history.setdefault((entry.registry_entry_id, tenant_id), []).append(
            self._now()
        )

    def validate_result(
        self,
        entry: ActorRegistryEntry,
        request: AcquisitionRequest,
        result: RawAcquisitionRecord,
    ) -> None:
        current = self.get(entry.registry_entry_id)
        if (
            current.lifecycle_state is not ActorLifecycleState.APPROVED
            or current.is_revoked
            or current.pinned_version != entry.pinned_version
        ):
            raise AcquisitionConstraintError(
                "Actor approval changed before result validation"
            )
        if (
            result.actor_id != entry.actor_id
            or result.actor_version != entry.pinned_version
        ):
            raise AcquisitionConstraintError(
                "Actor execution did not use pinned version"
            )
        if not result.run_id or not result.dataset_ref:
            raise AcquisitionConstraintError(
                "Actor run or dataset reference cannot be verified"
            )
        if not self.source_permitted(
            entry, result.source_identifier, result.source_platform
        ):
            raise AcquisitionConstraintError("Actor result source is not permitted")
        errors = _schema_errors(result.payload, entry.expected_output_schema)
        if errors:
            raise AcquisitionConstraintError(
                f"output schema validation failed: {errors[0]}"
            )
        for embedded_source in _embedded_http_sources(result.payload):
            if not self.source_permitted(
                entry, embedded_source, result.source_platform
            ):
                raise AcquisitionConstraintError(
                    "Actor output source is outside registry scope"
                )
        if isinstance(result.payload, list):
            max_items = entry.resource_limits.get("max_dataset_items")
            if not isinstance(max_items, int) or len(result.payload) > max_items:
                raise AcquisitionConstraintError("dataset resource limit exceeded")
            minimum_coverage = entry.quality_metrics.get("minimum_source_coverage")
            source_count = sum(
                1
                for item in result.payload
                if isinstance(item, dict) and bool(item.get("source_url"))
            )
            coverage = source_count / len(result.payload) if result.payload else 0.0
            if (
                not isinstance(minimum_coverage, (int, float))
                or not 0 <= minimum_coverage <= 1
            ):
                raise AcquisitionConstraintError("quality metric cannot be verified")
            if coverage < minimum_coverage:
                raise AcquisitionConstraintError("source quality threshold failed")
        total_cost = result.cost_metadata.get("total_usd")
        if not _finite_number(total_cost):
            raise AcquisitionConstraintError("cost metadata cannot be verified")
        verified_cost = float(total_cost)
        if (
            verified_cost > request.cost_ceiling_usd
            or verified_cost > entry.max_cost_usd
        ):
            raise AcquisitionConstraintError("Actor run exceeded cost ceiling")
        max_errors = entry.failure_metrics.get("max_collection_errors")
        if (
            not isinstance(max_errors, int)
            or len(result.collection_errors) > max_errors
        ):
            raise AcquisitionConstraintError("collection failure threshold exceeded")
        _parse_timestamp(result.executed_at, "Actor execution timestamp")
        _parse_timestamp(result.retrieved_at, "retrieval timestamp")

    @staticmethod
    def source_permitted(
        entry: ActorRegistryEntry, source: str, source_platform: str
    ) -> bool:
        if not source or not source_platform:
            return False
        hostname = (urlparse(source).hostname or "").lower().rstrip(".")
        platform = source_platform.lower()
        for allowed in entry.permitted_sources:
            candidate = allowed.lower().strip().rstrip(".")
            if candidate == f"platform:{platform}":
                return True
            if hostname and (
                hostname == candidate or hostname.endswith(f".{candidate}")
            ):
                return True
        return False

    def _validate_approvable(self, entry: ActorRegistryEntry) -> None:
        required_strings = (
            entry.actor_id,
            entry.human_readable_name,
            entry.pinned_version,
            entry.owner,
            entry.approval_authority,
            entry.review_date,
        )
        if not all(required_strings):
            raise AcquisitionConstraintError("registry approval metadata is incomplete")
        if not entry.permitted_sources or not entry.permitted_tenant_ids:
            raise AcquisitionConstraintError(
                "registry source or tenant scope is incomplete"
            )
        if not entry.legal_constraints or not entry.contractual_constraints:
            raise AcquisitionConstraintError(
                "legal or contractual constraints are incomplete"
            )
        if not _finite_number(entry.max_cost_usd) or entry.max_cost_usd <= 0:
            raise AcquisitionConstraintError("registry cost limit is invalid")
        frequency = entry.run_frequency_limit
        if frequency.max_runs <= 0 or frequency.window_seconds <= 0:
            raise AcquisitionConstraintError("run frequency limit is invalid")
        if entry.retention_rule.max_days <= 0:
            raise AcquisitionConstraintError("retention policy is invalid")
        if not _REQUIRED_PROVENANCE.issubset(set(entry.provenance_requirements)):
            raise AcquisitionConstraintError("provenance requirements are incomplete")
        if _schema_definition_errors(entry.allowed_input_schema):
            raise AcquisitionConstraintError("input schema cannot be verified")
        if _schema_definition_errors(entry.expected_output_schema):
            raise AcquisitionConstraintError("output schema cannot be verified")
        max_timeout = entry.resource_limits.get("max_timeout_seconds")
        max_items = entry.resource_limits.get("max_dataset_items")
        if not isinstance(max_timeout, int) or max_timeout <= 0:
            raise AcquisitionConstraintError("timeout resource limit is invalid")
        if not isinstance(max_items, int) or max_items <= 0:
            raise AcquisitionConstraintError("dataset resource limit is invalid")
        max_errors = entry.failure_metrics.get("max_collection_errors")
        if not isinstance(max_errors, int) or max_errors < 0:
            raise AcquisitionConstraintError("failure metric is invalid")
        minimum_coverage = entry.quality_metrics.get("minimum_source_coverage")
        if (
            not isinstance(minimum_coverage, (int, float))
            or not 0 <= minimum_coverage <= 1
        ):
            raise AcquisitionConstraintError("quality metric is invalid")
        if entry.revoked_at is not None or entry.revocation_authority_ref is not None:
            raise AcquisitionConstraintError("revocation state is inconsistent")
        _parse_timestamp(entry.review_date, "review date")

    def _validate_frequency(
        self, entry: ActorRegistryEntry, tenant_id: str, now: datetime
    ) -> None:
        limit = entry.run_frequency_limit
        cutoff = now - timedelta(seconds=limit.window_seconds)
        recent = [
            stamp
            for stamp in self._run_history.get((entry.registry_entry_id, tenant_id), [])
            if stamp >= cutoff
        ]
        self._run_history[(entry.registry_entry_id, tenant_id)] = recent
        if len(recent) >= limit.max_runs:
            raise AcquisitionConstraintError("run frequency limit exceeded")

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise AcquisitionConstraintError("registry clock cannot be verified")
        return now.astimezone(timezone.utc)
