#!/usr/bin/env python3
"""BuildOrderV1 — universal build-order intake normalization + validation.

Generalizes the repo-specific dispatcher intake (bin/valo-orchestrator) into a
repo-agnostic first stage: any authorized command / GitHub issue / Index build
order is normalized into a canonical BuildOrderV1 contract, validated for
authority basis, target repo and delimited scope, and gated on idempotency.

Authority fields (principal, issued_via, authority, authority_basis,
source_ref) are METADATA. Observed outside an authenticated command context
they are data only — they never authorize execution by themselves.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

SCHEMA_VERSION = "build-order-v1"

ACCEPTED = "ACCEPTED"
NEEDS_HUMAN = "NEEDS_HUMAN"
ALREADY_PROCESSED = "ALREADY_PROCESSED"

# These fields describe provenance and claimed authority. They are data.
# Execution authority is established by the command/control plane, never by
# the presence of these strings inside a build order.
AUTHORITY_METADATA_FIELDS = (
    "principal",
    "issued_via",
    "authority",
    "authority_basis",
    "source_ref",
)

REQUIRED_FIELDS = (
    "build_order_id",
    "issued_at",
    "principal",
    "issued_via",
    "authority_basis",
    "target_repo",
    "objective",
    "acceptance_criteria",
    "requires_independent_qc",
    "requires_receipt",
    "idempotency_key",
)

_WILD = {".", "*", "/", "**", "**/*", "/*"}


@dataclass(frozen=True)
class Scope:
    paths: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tokenomics:
    """AI tokenomics operating rules (#45). Constraints on the execution
    factory; never authority."""

    max_input_tokens: int = 0
    max_output_tokens: int = 0
    max_context_retention: int = 0
    deterministic_tool_preference: bool = True
    max_retries: int = 0
    max_autonomy_steps: int = 0
    analysis_execution_separation: bool = True
    cheap_first_verification: bool = True
    clean_session_boundaries: bool = True
    track_costs: bool = True
    receipt_includes_costs: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_budget": {
                "max_input_tokens": self.max_input_tokens,
                "max_output_tokens": self.max_output_tokens,
                "max_context_retention": self.max_context_retention,
            },
            "deterministic_tool_preference": self.deterministic_tool_preference,
            "bounded_retries": {
                "max_retries": self.max_retries,
                "max_autonomy_steps": self.max_autonomy_steps,
            },
            "analysis_execution_separation": self.analysis_execution_separation,
            "cheap_first_verification": self.cheap_first_verification,
            "clean_session_boundaries": self.clean_session_boundaries,
            "cost_of_cognition_accounting": {
                "track_costs": self.track_costs,
                "receipt_includes_costs": self.receipt_includes_costs,
            },
        }


@dataclass(frozen=True)
class BuildOrderV1:
    """Canonical normalized build order — ready for the repo resolver."""

    schema_version: str = SCHEMA_VERSION
    build_order_id: str = ""
    issued_at: str = ""
    expires_at: str | None = None
    principal: str = ""
    issued_via: str = ""
    authority: str = ""
    authority_basis: str = ""
    source_ref: str = ""
    target_repo: str = ""
    target_base_ref: str = "main"
    canonical_base_sha: str | None = None
    objective: str = ""
    owned_files: tuple[str, ...] = ()
    scope: Scope = field(default_factory=Scope)
    dependencies: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    risk_hints: tuple[str, ...] = ()
    requires_independent_qc: bool = True
    requires_receipt: bool = True
    idempotency_key: str = ""
    authority_effect: str = "none"
    tokenomics: Tokenomics = field(default_factory=Tokenomics)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for field_name in (
            "schema_version", "build_order_id", "issued_at", "expires_at",
            "principal", "issued_via", "authority", "authority_basis",
            "source_ref", "target_repo", "target_base_ref",
            "canonical_base_sha", "objective", "owned_files",
            "dependencies", "acceptance_criteria", "risk_hints",
            "requires_independent_qc", "requires_receipt",
            "idempotency_key", "authority_effect",
        ):
            out[field_name] = getattr(self, field_name)
        out["scope"] = {
            "paths": list(self.scope.paths),
            "exclude": list(self.scope.exclude),
        }
        out["tokenomics"] = self.tokenomics.to_dict()
        return out

    def as_mission(self, mission_id: str) -> dict[str, Any]:
        """Mission contract handed to the repo resolver / worker."""
        return {
            "mission_id": mission_id,
            "schema_version": self.schema_version,
            "build_order_id": self.build_order_id,
            "target_repo": self.target_repo,
            "target_base_ref": self.target_base_ref,
            "canonical_base_sha": self.canonical_base_sha,
            "objective": self.objective,
            "owned_files": list(self.owned_files),
            "scope": {
                "paths": list(self.scope.paths),
                "exclude": list(self.scope.exclude),
            },
            "dependencies": list(self.dependencies),
            "acceptance_criteria": list(self.acceptance_criteria),
            "risk_hints": list(self.risk_hints),
            "requires_independent_qc": self.requires_independent_qc,
            "requires_receipt": self.requires_receipt,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class IntakeResult:
    status: str
    build_order: BuildOrderV1 | None
    problems: tuple[str, ...]
    idempotency_key: str | None = None
    mission_id: str | None = None
    prior_mission_id: str | None = None


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = [value]
    return tuple(str(item).strip() for item in items if str(item).strip())


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_scope(raw: Mapping[str, Any]) -> Scope:
    scope_raw = raw.get("scope")
    paths: list[str] = []
    exclude: list[str] = []
    if isinstance(scope_raw, str):
        paths = [scope_raw]
    elif isinstance(scope_raw, Mapping):
        paths = _to_list(scope_raw.get("paths"))
        exclude = _to_list(scope_raw.get("exclude"))
    elif isinstance(scope_raw, (list, tuple)):
        paths = [str(item) for item in scope_raw]
    return Scope(
        paths=tuple(p for p in paths if str(p).strip()),
        exclude=tuple(p for p in exclude if str(p).strip()),
    )


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _normalize_tokenomics(raw: Mapping[str, Any] | None) -> Tokenomics:
    data = dict(raw or {})
    context = dict(data.get("context_budget") or {})
    retries = dict(data.get("bounded_retries") or {})
    costs = dict(data.get("cost_of_cognition_accounting") or {})
    return Tokenomics(
        max_input_tokens=_as_int(context.get("max_input_tokens")),
        max_output_tokens=_as_int(context.get("max_output_tokens")),
        max_context_retention=_as_int(context.get("max_context_retention")),
        deterministic_tool_preference=_as_bool(
            data.get("deterministic_tool_preference"), True
        ),
        max_retries=_as_int(retries.get("max_retries")),
        max_autonomy_steps=_as_int(retries.get("max_autonomy_steps")),
        analysis_execution_separation=True,
        cheap_first_verification=_as_bool(
            data.get("cheap_first_verification"), True
        ),
        clean_session_boundaries=_as_bool(
            data.get("clean_session_boundaries"), True
        ),
        track_costs=_as_bool(costs.get("track_costs"), True),
        receipt_includes_costs=_as_bool(
            costs.get("receipt_includes_costs"), True
        ),
    )


def normalize(raw: Mapping[str, Any] | None) -> BuildOrderV1:
    """Normalize any raw input into a canonical BuildOrderV1 contract."""
    data = dict(raw or {})
    owned_files = tuple(p for p in _as_tuple(data.get("owned_files")) if p)
    return BuildOrderV1(
        build_order_id=_as_str(data.get("build_order_id")),
        issued_at=_as_str(data.get("issued_at")),
        expires_at=_as_str(data.get("expires_at"), None) or None,
        principal=_as_str(data.get("principal")),
        issued_via=_as_str(data.get("issued_via")),
        authority=_as_str(data.get("authority")),
        authority_basis=_as_str(data.get("authority_basis")),
        source_ref=_as_str(data.get("source_ref")),
        target_repo=_as_str(data.get("target_repo")),
        target_base_ref=_as_str(data.get("target_base_ref"), "main") or "main",
        canonical_base_sha=_as_str(data.get("canonical_base_sha"), None) or None,
        objective=_as_str(data.get("objective")),
        owned_files=owned_files,
        scope=_normalize_scope(data),
        dependencies=_as_tuple(data.get("dependencies")),
        acceptance_criteria=_as_tuple(data.get("acceptance_criteria")),
        risk_hints=_as_tuple(data.get("risk_hints")),
        requires_independent_qc=_as_bool(
            data.get("requires_independent_qc"), True
        ),
        requires_receipt=_as_bool(data.get("requires_receipt"), True),
        idempotency_key=_as_str(data.get("idempotency_key")),
        authority_effect="none",
        tokenomics=_normalize_tokenomics(data.get("tokenomics")),
    )


def _is_delimited(bo: BuildOrderV1) -> bool:
    owned = [p for p in bo.owned_files if p not in _WILD]
    paths = [p for p in bo.scope.paths if p not in _WILD]
    return bool(owned or paths)


def validate(bo: BuildOrderV1, now: datetime | None = None) -> tuple[str, ...]:
    """Return validation problems. A non-empty result means NEEDS_HUMAN."""
    problems: list[str] = []
    for name in REQUIRED_FIELDS:
        value = getattr(bo, name)
        if isinstance(value, (tuple, list)):
            missing = len(value) == 0
        else:
            missing = not value
        if missing:
            problems.append(f"missing required field: {name}")

    if not bo.target_repo:
        problems.append("NEEDS_HUMAN: missing target_repo")
    if not bo.authority_basis:
        problems.append("NEEDS_HUMAN: missing authority_basis")
    if not _is_delimited(bo):
        problems.append(
            "NEEDS_HUMAN: no delimited scope (owned_files or allowed paths required)"
        )

    now = now or datetime.now(timezone.utc)
    issued = _parse_datetime(bo.issued_at)
    if not issued:
        problems.append("NEEDS_HUMAN: issued_at is not a valid ISO-8601 timestamp")
    expires = _parse_datetime(bo.expires_at)
    if expires and expires <= now:
        problems.append("NEEDS_HUMAN: build order expired")

    return tuple(dict.fromkeys(problems))


class IntakeRegistry(Protocol):
    """Idempotency registry. Lookup by idempotency_key; store a mission."""

    def lookup(self, key: str) -> str | None: ...

    def store(self, key: str, mission_id: str) -> None: ...


class MemoryIntakeRegistry:
    """In-memory registry for tests and stateless processes."""

    def __init__(self) -> None:
        self._missions: dict[str, str] = {}

    def lookup(self, key: str) -> str | None:
        return self._missions.get(key)

    def store(self, key: str, mission_id: str) -> None:
        self._missions[key] = mission_id

    @property
    def missions(self) -> dict[str, str]:
        return dict(self._missions)


class SqliteIntakeRegistry:
    """Persistent idempotency registry (follows claims.db / runs.db pattern)."""

    DEFAULT_DB = str(Path.home() / ".valo" / "intake.db")

    def __init__(self, db_path: str | None = None) -> None:
        self._path = db_path or self.DEFAULT_DB
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS intake ("
            " idempotency_key TEXT PRIMARY KEY,"
            " mission_id TEXT,"
            " ingested_at TEXT)"
        )
        self._conn.commit()

    def lookup(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT mission_id FROM intake WHERE idempotency_key=?",
            (key,),
        ).fetchone()
        return row[0] if row else None

    def store(self, key: str, mission_id: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO intake VALUES (?,?,?)",
            (key, mission_id, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def mission_id(bo: BuildOrderV1) -> str:
    digest = hashlib.sha256(
        (bo.build_order_id + "::" + bo.idempotency_key).encode("utf-8")
    ).hexdigest()[:12]
    return f"mission::{bo.build_order_id}::{digest}"


def intake(
    raw: Mapping[str, Any] | None,
    registry: IntakeRegistry | None = None,
    now: datetime | None = None,
) -> IntakeResult:
    """Normalize, validate and idempotency-gate a build order.

    Returns ACCEPTED (ready for repo resolver), NEEDS_HUMAN (validation
    problems, never guessed execution) or ALREADY_PROCESSED (same
    idempotency_key — no new mission).
    """
    bo = normalize(raw)
    problems = validate(bo, now=now)
    if problems:
        return IntakeResult(
            status=NEEDS_HUMAN,
            build_order=bo,
            problems=problems,
            idempotency_key=bo.idempotency_key or None,
        )

    mission = mission_id(bo)
    if registry is not None:
        prior = registry.lookup(bo.idempotency_key)
        if prior is not None:
            return IntakeResult(
                status=ALREADY_PROCESSED,
                build_order=bo,
                problems=(),
                idempotency_key=bo.idempotency_key,
                prior_mission_id=prior,
            )
        registry.store(bo.idempotency_key, mission)

    return IntakeResult(
        status=ACCEPTED,
        build_order=bo,
        problems=(),
        idempotency_key=bo.idempotency_key,
        mission_id=mission,
    )
