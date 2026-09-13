"""Operator-safe Sanity canary workflow over canonical execution components.

This module packages deployment verification, preflight, kill-switch state, status,
single-pass reconciliation and rollback proposals. It does not issue authority,
clearance, CommitTokens, execution receipts or outcome receipts. It cannot perform a
provider mutation except by delegating to ``SanityCanaryDurableMutationExecutor``.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.valo_platform.action_envelope.execution_journal import (
    ExecutionJournalError,
    ExecutionRecord,
    ExecutionState,
    SQLiteExecutionJournal,
)
from src.valo_platform.content_operations.actions import ContentActionCase

from .durable_mutation import ContentMutationReconciliationAdapter
from .protocol import ContentMutationRequest, ContentMutationTransport
from .sanity_deployment import (
    SanityCanaryActivation,
    SanityCanaryDeployment,
    SanityCanaryDeploymentError,
    SanityCanaryDeploymentProfile,
    SanityCanaryDurableMutationExecutor,
    SanityExecutionContextStoreError,
    SanitySecretManagerCredentialProvider,
    SanitySecretResolver,
    SQLiteSanityExecutionContextStore,
)


_MAX_BUNDLE_BYTES = 1_048_576
_SHA256_PREFIX = "sha256:"


def _digest(value: Any) -> str:
    return _SHA256_PREFIX + hashlib.sha256(rfc8785.dumps(value)).hexdigest()


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_sha256(value: str) -> str:
    if not value.startswith(_SHA256_PREFIX) or len(value) != 71:
        raise ValueError("digest must be lowercase sha256:<64 hex>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError("digest must be lowercase sha256:<64 hex>") from exc
    if value != value.lower():
        raise ValueError("digest must be lowercase sha256:<64 hex>")
    return value


class SanityCanaryOperationsError(RuntimeError):
    """Fail-closed operations-pack error before provider dispatch."""


class SanityCanaryBundleVerificationError(SanityCanaryOperationsError):
    """Signed deployment bundle failed structural, time or signature verification."""


class SanityCanaryOperationsStateError(SanityCanaryOperationsError):
    """Deployment control state is missing, conflicting or corrupted."""


class SanityCanarySignatureVerifier(Protocol):
    """Verify detached signatures using an externally managed trust store."""

    def verify(
        self,
        *,
        key_id: str,
        payload: bytes,
        signature: str,
    ) -> bool: ...


class SanityCanarySignedBundle(BaseModel):
    """Signed, non-secret deployment profile and activation epoch."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    bundle_version: str = "1"
    profile: SanityCanaryDeploymentProfile
    activation: SanityCanaryActivation
    activation_epoch: int = Field(ge=1)
    issued_at: datetime
    expires_at: datetime
    signer_id: str = Field(min_length=1)
    key_id: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    bundle_digest: str

    @field_validator("issued_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("signed bundle timestamps must be timezone-aware")
        return value

    @field_validator("bundle_digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _require_sha256(value)

    @model_validator(mode="after")
    def validate_bundle(self) -> "SanityCanarySignedBundle":
        if self.expires_at <= self.issued_at:
            raise ValueError("signed bundle expiry must follow issuance")
        if self.expires_at > self.profile.expires_at:
            raise ValueError("signed bundle cannot outlive deployment profile")
        if self.activation.profile_digest != self.profile.digest():
            raise ValueError("activation does not bind signed deployment profile")
        if self.bundle_digest != _digest(self.canonical_payload()):
            raise ValueError("signed bundle digest mismatch")
        return self

    @staticmethod
    def payload_for(
        *,
        profile: SanityCanaryDeploymentProfile,
        activation: SanityCanaryActivation,
        activation_epoch: int,
        issued_at: datetime,
        expires_at: datetime,
        signer_id: str,
        key_id: str,
        bundle_version: str = "1",
    ) -> dict[str, Any]:
        return {
            "bundle_version": bundle_version,
            "profile": profile.model_dump(mode="json"),
            "activation": activation.model_dump(mode="json"),
            "activation_epoch": activation_epoch,
            "issued_at": _timestamp(issued_at),
            "expires_at": _timestamp(expires_at),
            "signer_id": signer_id,
            "key_id": key_id,
        }

    def canonical_payload(self) -> dict[str, Any]:
        return self.payload_for(
            profile=self.profile,
            activation=self.activation,
            activation_epoch=self.activation_epoch,
            issued_at=self.issued_at,
            expires_at=self.expires_at,
            signer_id=self.signer_id,
            key_id=self.key_id,
            bundle_version=self.bundle_version,
        )

    def canonical_bytes(self) -> bytes:
        return rfc8785.dumps(self.canonical_payload())


@dataclass(frozen=True)
class VerifiedSanityCanaryBundle:
    """Bundle that passed an injected signature verifier at a specific time."""

    bundle: SanityCanarySignedBundle
    verification_ref: str
    verified_at: datetime


class SanityCanaryBundleLoader:
    """Load and verify signed canary bundles without accessing provider secrets."""

    def __init__(self, verifier: SanityCanarySignatureVerifier) -> None:
        self._verifier = verifier

    def load_bytes(
        self,
        raw: bytes,
        *,
        now: datetime | None = None,
    ) -> VerifiedSanityCanaryBundle:
        if not raw or len(raw) > _MAX_BUNDLE_BYTES:
            raise SanityCanaryBundleVerificationError(
                "signed canary bundle is empty or exceeds size limit"
            )
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise SanityCanaryBundleVerificationError(
                "bundle verification time must be timezone-aware"
            )
        try:
            bundle = SanityCanarySignedBundle.model_validate_json(raw)
        except Exception:
            raise SanityCanaryBundleVerificationError(
                "signed canary bundle is malformed or digest-invalid"
            ) from None
        if current < bundle.issued_at or current >= bundle.expires_at:
            raise SanityCanaryBundleVerificationError(
                "signed canary bundle is not currently valid"
            )
        try:
            verified = self._verifier.verify(
                key_id=bundle.key_id,
                payload=bundle.canonical_bytes(),
                signature=bundle.signature,
            )
        except Exception:
            raise SanityCanaryBundleVerificationError(
                "signed canary bundle verification failed"
            ) from None
        if verified is not True:
            raise SanityCanaryBundleVerificationError(
                "signed canary bundle verification failed"
            )
        return VerifiedSanityCanaryBundle(
            bundle=bundle,
            verification_ref=(
                "sanity-canary-signature:"
                + bundle.bundle_digest.removeprefix(_SHA256_PREFIX)[:24]
            ),
            verified_at=current,
        )

    def load_file(
        self,
        path: str | Path,
        *,
        now: datetime | None = None,
    ) -> VerifiedSanityCanaryBundle:
        try:
            raw = Path(path).read_bytes()
        except OSError:
            raise SanityCanaryBundleVerificationError(
                "signed canary bundle could not be read"
            ) from None
        return self.load_bytes(raw, now=now)


class SanityCanaryOperationsState(BaseModel):
    """Deployment-local availability state; never execution authority or state."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    profile_id: str = Field(min_length=1)
    profile_digest: str
    activation_epoch: int = Field(ge=1)
    halted: bool = False
    halt_reason: str | None = None
    actor_ref: str = Field(min_length=1)
    changed_at: datetime
    last_preflight_ref: str | None = None
    state_digest: str

    @field_validator("profile_digest", "state_digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("changed_at")
    @classmethod
    def require_changed_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("operations state timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_state(self) -> "SanityCanaryOperationsState":
        if self.halted and not self.halt_reason:
            raise ValueError("halted operations state requires a reason")
        if not self.halted and self.halt_reason is not None:
            raise ValueError("active operations state cannot retain a halt reason")
        if self.state_digest != _digest(self.canonical_payload()):
            raise ValueError("operations state digest mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "profile_digest": self.profile_digest,
            "activation_epoch": self.activation_epoch,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "actor_ref": self.actor_ref,
            "changed_at": _timestamp(self.changed_at),
            "last_preflight_ref": self.last_preflight_ref,
        }

    @classmethod
    def build(
        cls,
        *,
        profile_id: str,
        profile_digest: str,
        activation_epoch: int,
        halted: bool,
        halt_reason: str | None,
        actor_ref: str,
        changed_at: datetime,
        last_preflight_ref: str | None,
    ) -> "SanityCanaryOperationsState":
        payload = {
            "profile_id": profile_id,
            "profile_digest": profile_digest,
            "activation_epoch": activation_epoch,
            "halted": halted,
            "halt_reason": halt_reason,
            "actor_ref": actor_ref,
            "changed_at": _timestamp(changed_at),
            "last_preflight_ref": last_preflight_ref,
        }
        return cls(**payload, state_digest=_digest(payload))


class SQLiteSanityCanaryOperationsStateStore:
    """Mutable availability sidecar with an append-only event trail."""

    def __init__(self, path: str | Path) -> None:
        database_path = Path(path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(database_path)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sanity_canary_operations_state (
                    profile_id TEXT PRIMARY KEY,
                    profile_digest TEXT NOT NULL,
                    activation_epoch INTEGER NOT NULL,
                    halted INTEGER NOT NULL,
                    halt_reason TEXT,
                    actor_ref TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    last_preflight_ref TEXT,
                    state_digest TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sanity_canary_operations_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    state_digest TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )
                """
            )
        try:
            database_path.chmod(0o600)
        except OSError:
            pass

    def activate(
        self,
        verified: VerifiedSanityCanaryBundle,
        *,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        bundle = verified.bundle
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None or not actor_ref.strip():
            raise SanityCanaryOperationsStateError(
                "activation requires timezone-aware time and actor reference"
            )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM sanity_canary_operations_state WHERE profile_id=?",
                (bundle.profile.profile_id,),
            ).fetchone()
            previous = self._decode(row) if row is not None else None
            if previous is not None:
                if bundle.activation_epoch < previous.activation_epoch:
                    connection.rollback()
                    raise SanityCanaryOperationsStateError(
                        "activation epoch is older than persisted operations state"
                    )
                if bundle.activation_epoch == previous.activation_epoch:
                    if bundle.profile.digest() != previous.profile_digest:
                        connection.rollback()
                        raise SanityCanaryOperationsStateError(
                            "activation epoch is already bound to another profile"
                        )
                    if previous.halted:
                        connection.rollback()
                        raise SanityCanaryOperationsStateError(
                            "halted deployment requires a newer signed activation epoch"
                        )
                    connection.commit()
                    return previous
            state = SanityCanaryOperationsState.build(
                profile_id=bundle.profile.profile_id,
                profile_digest=bundle.profile.digest(),
                activation_epoch=bundle.activation_epoch,
                halted=False,
                halt_reason=None,
                actor_ref=actor_ref,
                changed_at=current_time,
                last_preflight_ref=(
                    previous.last_preflight_ref if previous is not None else None
                ),
            )
            self._write_state(connection, state)
            self._append_event(
                connection,
                state,
                "ACTIVATED" if previous is None else "RESUMED",
                {"verification_ref": verified.verification_ref},
            )
            connection.commit()
        return self.get(state.profile_id)

    def halt(
        self,
        *,
        profile_id: str,
        expected_profile_digest: str,
        actor_ref: str,
        reason: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None or not actor_ref.strip() or not reason.strip():
            raise SanityCanaryOperationsStateError(
                "halt requires timezone-aware time, actor and reason"
            )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM sanity_canary_operations_state WHERE profile_id=?",
                (profile_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise SanityCanaryOperationsStateError("operations state not found")
            previous = self._decode(row)
            if previous.profile_digest != expected_profile_digest:
                connection.rollback()
                raise SanityCanaryOperationsStateError(
                    "halt profile digest does not match active deployment"
                )
            if previous.halted:
                connection.commit()
                return previous
            state = SanityCanaryOperationsState.build(
                profile_id=previous.profile_id,
                profile_digest=previous.profile_digest,
                activation_epoch=previous.activation_epoch,
                halted=True,
                halt_reason=reason,
                actor_ref=actor_ref,
                changed_at=current_time,
                last_preflight_ref=previous.last_preflight_ref,
            )
            self._write_state(connection, state)
            self._append_event(connection, state, "HALTED", {"reason": reason})
            connection.commit()
        return self.get(profile_id)

    def require_operational(
        self,
        verified: VerifiedSanityCanaryBundle,
    ) -> SanityCanaryOperationsState:
        state = self.get(verified.bundle.profile.profile_id)
        expected = (
            verified.bundle.profile.digest(),
            verified.bundle.activation_epoch,
        )
        actual = (state.profile_digest, state.activation_epoch)
        if actual != expected:
            raise SanityCanaryOperationsStateError(
                "runner bundle is not the active operations epoch"
            )
        if state.halted:
            raise SanityCanaryOperationsStateError(
                "Sanity canary deployment is halted"
            )
        return state

    def record_preflight(
        self,
        *,
        profile_id: str,
        profile_digest: str,
        activation_epoch: int,
        preflight_ref: str,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        current_time = now or datetime.now(timezone.utc)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM sanity_canary_operations_state WHERE profile_id=?",
                (profile_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise SanityCanaryOperationsStateError("operations state not found")
            previous = self._decode(row)
            if (
                previous.profile_digest != profile_digest
                or previous.activation_epoch != activation_epoch
            ):
                connection.rollback()
                raise SanityCanaryOperationsStateError(
                    "preflight does not bind active profile and epoch"
                )
            state = SanityCanaryOperationsState.build(
                profile_id=previous.profile_id,
                profile_digest=previous.profile_digest,
                activation_epoch=previous.activation_epoch,
                halted=previous.halted,
                halt_reason=previous.halt_reason,
                actor_ref=actor_ref,
                changed_at=current_time,
                last_preflight_ref=preflight_ref,
            )
            self._write_state(connection, state)
            self._append_event(connection, state, "PREFLIGHT", {})
            connection.commit()
        return self.get(profile_id)

    def get(self, profile_id: str) -> SanityCanaryOperationsState:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM sanity_canary_operations_state WHERE profile_id=?",
                (profile_id,),
            ).fetchone()
        if row is None:
            raise SanityCanaryOperationsStateError("operations state not found")
        return self._decode(row)

    def events(self, profile_id: str) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_type, occurred_at, state_digest, details_json
                FROM sanity_canary_operations_events
                WHERE profile_id=? ORDER BY event_id
                """,
                (profile_id,),
            ).fetchall()
        return tuple(
            {
                "event_type": row[0],
                "occurred_at": row[1],
                "state_digest": row[2],
                "details": json.loads(row[3]),
            }
            for row in rows
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _write_state(
        connection: sqlite3.Connection,
        state: SanityCanaryOperationsState,
    ) -> None:
        connection.execute(
            """
            INSERT INTO sanity_canary_operations_state (
                profile_id, profile_digest, activation_epoch, halted,
                halt_reason, actor_ref, changed_at, last_preflight_ref,
                state_digest
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(profile_id) DO UPDATE SET
                profile_digest=excluded.profile_digest,
                activation_epoch=excluded.activation_epoch,
                halted=excluded.halted,
                halt_reason=excluded.halt_reason,
                actor_ref=excluded.actor_ref,
                changed_at=excluded.changed_at,
                last_preflight_ref=excluded.last_preflight_ref,
                state_digest=excluded.state_digest
            """,
            (
                state.profile_id,
                state.profile_digest,
                state.activation_epoch,
                int(state.halted),
                state.halt_reason,
                state.actor_ref,
                _timestamp(state.changed_at),
                state.last_preflight_ref,
                state.state_digest,
            ),
        )

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        state: SanityCanaryOperationsState,
        event_type: str,
        details: Mapping[str, Any],
    ) -> None:
        connection.execute(
            """
            INSERT INTO sanity_canary_operations_events (
                profile_id, event_type, occurred_at, state_digest, details_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                state.profile_id,
                event_type,
                _timestamp(state.changed_at),
                state.state_digest,
                json.dumps(dict(details), sort_keys=True, separators=(",", ":")),
            ),
        )

    @staticmethod
    def _decode(row: sqlite3.Row) -> SanityCanaryOperationsState:
        try:
            changed_at = datetime.fromisoformat(row["changed_at"].replace("Z", "+00:00"))
            return SanityCanaryOperationsState(
                profile_id=row["profile_id"],
                profile_digest=row["profile_digest"],
                activation_epoch=int(row["activation_epoch"]),
                halted=bool(row["halted"]),
                halt_reason=row["halt_reason"],
                actor_ref=row["actor_ref"],
                changed_at=changed_at,
                last_preflight_ref=row["last_preflight_ref"],
                state_digest=row["state_digest"],
            )
        except Exception:
            raise SanityCanaryOperationsStateError(
                "persisted operations state is malformed or tampered"
            ) from None


class SanityCanarySecretProbe(Protocol):
    def probe(self) -> str: ...


class SanitySecretAvailabilityProbe:
    """Check secret-manager availability without returning or retaining the token."""

    def __init__(
        self,
        *,
        secret_ref: str,
        resolver: SanitySecretResolver,
    ) -> None:
        self._provider = SanitySecretManagerCredentialProvider(
            secret_ref=secret_ref,
            resolver=resolver,
        )
        self._probe_ref = (
            "sanity-secret-ref:"
            + hashlib.sha256(secret_ref.encode("utf-8")).hexdigest()[:24]
        )

    def probe(self) -> str:
        token = self._provider.get_token()
        token.get_secret_value()
        del token
        return self._probe_ref


class SanityCanaryPreflightResult(BaseModel):
    """Reference-only result; it grants no permission and consumes no token."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    permitted: bool
    reason_code: str = Field(min_length=1)
    profile_digest: str
    activation_epoch: int = Field(ge=1)
    execution_id: str = Field(min_length=1)
    action_digest: str
    target_digest: str
    secret_available: bool
    context_store_ready: bool
    created_at: datetime
    result_digest: str

    @field_validator("profile_digest", "action_digest", "target_digest", "result_digest")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _require_sha256(value)

    @field_validator("created_at")
    @classmethod
    def require_created_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("preflight timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_result(self) -> "SanityCanaryPreflightResult":
        if self.result_digest != _digest(self.canonical_payload()):
            raise ValueError("preflight result digest mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "permitted": self.permitted,
            "reason_code": self.reason_code,
            "profile_digest": self.profile_digest,
            "activation_epoch": self.activation_epoch,
            "execution_id": self.execution_id,
            "action_digest": self.action_digest,
            "target_digest": self.target_digest,
            "secret_available": self.secret_available,
            "context_store_ready": self.context_store_ready,
            "created_at": _timestamp(self.created_at),
        }

    @classmethod
    def build(cls, **values: Any) -> "SanityCanaryPreflightResult":
        payload = {
            **values,
            "created_at": _timestamp(values["created_at"]),
        }
        return cls(**payload, result_digest=_digest(payload))

    @property
    def reference(self) -> str:
        return "sanity-preflight:" + self.result_digest[7:31]


class SanityCanaryExecutionStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    execution_state: ExecutionState
    attempt: int
    provider_reference: str | None
    execution_receipt_id: str | None
    execution_receipt_digest: str | None
    context_digest: str | None
    operation: str | None
    document_ids: tuple[str, ...]
    observed_at: datetime


class SanityRollbackPlan(BaseModel):
    """Reference-only proposal requiring a new canonical action and clearance."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    plan_id: str = Field(min_length=1)
    original_execution_id: str = Field(min_length=1)
    original_execution_receipt_id: str = Field(min_length=1)
    original_execution_receipt_digest: str
    source_context_digest: str
    document_ids: tuple[str, ...] = Field(min_length=1)
    expected_current_revisions: tuple[str, ...] = Field(min_length=1)
    rollback_change_ref: str = Field(min_length=1)
    rollback_change_digest: str
    requested_by: str = Field(min_length=1)
    created_at: datetime
    requires_new_action_case: bool = True
    requires_new_clearance: bool = True
    automatic_execution: bool = False
    plan_digest: str

    @field_validator(
        "original_execution_receipt_digest",
        "source_context_digest",
        "rollback_change_digest",
        "plan_digest",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        return _require_sha256(value)

    @model_validator(mode="after")
    def validate_plan(self) -> "SanityRollbackPlan":
        if len(self.document_ids) != len(self.expected_current_revisions):
            raise ValueError("rollback revision cardinality mismatch")
        if not self.requires_new_action_case or not self.requires_new_clearance:
            raise ValueError("rollback plan must require new action and clearance")
        if self.automatic_execution:
            raise ValueError("rollback plan cannot authorize automatic execution")
        if self.plan_digest != _digest(self.canonical_payload()):
            raise ValueError("rollback plan digest mismatch")
        return self

    def canonical_payload(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.model_dump(mode="json").items()
            if key != "plan_digest"
        }


class SanityCanaryOperationsRunner:
    """Command surface over existing deployment, journal and durable executor."""

    def __init__(
        self,
        *,
        verified_bundle: VerifiedSanityCanaryBundle,
        deployment: SanityCanaryDeployment,
        operations_store: SQLiteSanityCanaryOperationsStateStore,
        connector: Any,
        durable_executor: SanityCanaryDurableMutationExecutor,
        journal: SQLiteExecutionJournal,
        context_store: SQLiteSanityExecutionContextStore,
        secret_probe: SanityCanarySecretProbe,
    ) -> None:
        bundle = verified_bundle.bundle
        if deployment.profile.digest() != bundle.profile.digest():
            raise SanityCanaryOperationsError(
                "runner deployment does not match verified profile"
            )
        if deployment.activation != bundle.activation:
            raise SanityCanaryOperationsError(
                "runner deployment does not match verified activation"
            )
        self.verified_bundle = verified_bundle
        self.deployment = deployment
        self.operations_store = operations_store
        self.connector = connector
        self.durable_executor = durable_executor
        self.journal = journal
        self.context_store = context_store
        self.secret_probe = secret_probe

    def register_activation(
        self,
        *,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return self.operations_store.activate(
            self.verified_bundle,
            actor_ref=actor_ref,
            now=now,
        )

    def preflight(
        self,
        *,
        action_case: ContentActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        integrity_baseline: Any,
        integrity_checkpoint: Any,
        transport: ContentMutationTransport,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryPreflightResult:
        current = now or datetime.now(timezone.utc)
        execution_id = self._execution_id(signed_commit_token)
        secret_available = False
        context_ready = False
        permitted = False
        reason = "DENIED"
        try:
            self.operations_store.require_operational(self.verified_bundle)
            plan = self.connector.prepare(
                action_case=action_case,
                signed_commit_token=signed_commit_token,
                integrity_baseline=integrity_baseline,
                integrity_checkpoint=integrity_checkpoint,
                transport=transport,
            )
            request = ContentMutationRequest.from_action_case(
                execution_id=execution_id,
                action_case=action_case,
            )
            self.deployment.require_write_request(
                request,
                connector_id=plan.connector_id,
                now=current,
            )
            self.secret_probe.probe()
            secret_available = True
            self.context_store.count()
            context_ready = True
            permitted = True
            reason = "READY"
        except Exception as exc:
            reason = type(exc).__name__
        result = SanityCanaryPreflightResult.build(
            permitted=permitted,
            reason_code=reason,
            profile_digest=self.verified_bundle.bundle.profile.digest(),
            activation_epoch=self.verified_bundle.bundle.activation_epoch,
            execution_id=execution_id,
            action_digest=action_case.digest(),
            target_digest=action_case.target_digest(),
            secret_available=secret_available,
            context_store_ready=context_ready,
            created_at=current,
        )
        try:
            self.operations_store.record_preflight(
                profile_id=self.verified_bundle.bundle.profile.profile_id,
                profile_digest=result.profile_digest,
                activation_epoch=result.activation_epoch,
                preflight_ref=result.reference,
                actor_ref=actor_ref,
                now=current,
            )
        except SanityCanaryOperationsStateError:
            if permitted:
                raise
        return result

    def execute(
        self,
        *,
        preflight: SanityCanaryPreflightResult,
        action_case: ContentActionCase,
        signed_commit_token: Mapping[str, Any] | None,
        integrity_baseline: Any,
        integrity_checkpoint: Any,
        transport: ContentMutationTransport,
        receipt_id: str,
        now: datetime | None = None,
    ) -> Any:
        self.operations_store.require_operational(self.verified_bundle)
        if not preflight.permitted:
            raise SanityCanaryOperationsError("canary execution requires ready preflight")
        expected = (
            self.verified_bundle.bundle.profile.digest(),
            self.verified_bundle.bundle.activation_epoch,
            self._execution_id(signed_commit_token),
            action_case.digest(),
            action_case.target_digest(),
        )
        actual = (
            preflight.profile_digest,
            preflight.activation_epoch,
            preflight.execution_id,
            preflight.action_digest,
            preflight.target_digest,
        )
        if actual != expected:
            raise SanityCanaryOperationsError(
                "preflight does not bind exact execution and action"
            )
        return self.durable_executor.execute(
            action_case=action_case,
            signed_commit_token=signed_commit_token,
            integrity_baseline=integrity_baseline,
            integrity_checkpoint=integrity_checkpoint,
            transport=transport,
            receipt_id=receipt_id,
            now=now,
        )

    def status(
        self,
        execution_id: str,
        *,
        now: datetime | None = None,
    ) -> SanityCanaryExecutionStatus:
        record = self.journal.get(execution_id)
        try:
            context = self.context_store.get(execution_id)
        except SanityExecutionContextStoreError:
            context = None
        return SanityCanaryExecutionStatus(
            execution_id=record.execution_id,
            execution_state=record.state,
            attempt=record.attempt,
            provider_reference=record.provider_reference,
            execution_receipt_id=record.execution_receipt_id,
            execution_receipt_digest=record.execution_receipt_digest,
            context_digest=context.context_digest if context else None,
            operation=context.operation.value if context else None,
            document_ids=context.document_ids if context else (),
            observed_at=now or datetime.now(timezone.utc),
        )

    def halt(
        self,
        *,
        actor_ref: str,
        reason: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        return self.operations_store.halt(
            profile_id=self.verified_bundle.bundle.profile.profile_id,
            expected_profile_digest=self.verified_bundle.bundle.profile.digest(),
            actor_ref=actor_ref,
            reason=reason,
            now=now,
        )

    def resume(
        self,
        verified_new_bundle: VerifiedSanityCanaryBundle,
        *,
        actor_ref: str,
        now: datetime | None = None,
    ) -> SanityCanaryOperationsState:
        current = self.operations_store.get(
            self.verified_bundle.bundle.profile.profile_id
        )
        if verified_new_bundle.bundle.profile.profile_id != current.profile_id:
            raise SanityCanaryOperationsStateError(
                "resume bundle targets another canary profile"
            )
        if verified_new_bundle.bundle.activation_epoch <= current.activation_epoch:
            raise SanityCanaryOperationsStateError(
                "resume requires a newer signed activation epoch"
            )
        return self.operations_store.activate(
            verified_new_bundle,
            actor_ref=actor_ref,
            now=now,
        )

    def rollback_plan(
        self,
        *,
        execution_id: str,
        expected_current_revisions: Sequence[str],
        rollback_change_ref: str,
        rollback_change_digest: str,
        requested_by: str,
        now: datetime | None = None,
    ) -> SanityRollbackPlan:
        record = self.journal.get(execution_id)
        if record.state is not ExecutionState.SUCCEEDED:
            raise SanityCanaryOperationsError(
                "rollback proposal requires a succeeded execution"
            )
        if not record.execution_receipt_id or not record.execution_receipt_digest:
            raise SanityCanaryOperationsError(
                "rollback proposal requires canonical execution receipt"
            )
        context = self.context_store.get(execution_id)
        _require_sha256(rollback_change_digest)
        created = now or datetime.now(timezone.utc)
        payload = {
            "plan_id": "sanity-rollback:" + execution_id,
            "original_execution_id": execution_id,
            "original_execution_receipt_id": record.execution_receipt_id,
            "original_execution_receipt_digest": record.execution_receipt_digest,
            "source_context_digest": context.context_digest,
            "document_ids": list(context.document_ids),
            "expected_current_revisions": list(expected_current_revisions),
            "rollback_change_ref": rollback_change_ref,
            "rollback_change_digest": rollback_change_digest,
            "requested_by": requested_by,
            "created_at": _timestamp(created),
            "requires_new_action_case": True,
            "requires_new_clearance": True,
            "automatic_execution": False,
        }
        return SanityRollbackPlan(**payload, plan_digest=_digest(payload))

    @staticmethod
    def _execution_id(
        signed_commit_token: Mapping[str, Any] | None,
    ) -> str:
        if not isinstance(signed_commit_token, Mapping):
            raise SanityCanaryOperationsError("signed CommitToken is required")
        payload = signed_commit_token.get("payload")
        if not isinstance(payload, Mapping):
            raise SanityCanaryOperationsError("CommitToken payload is missing")
        execution_id = payload.get("execution_id")
        if not isinstance(execution_id, str) or not execution_id:
            raise SanityCanaryOperationsError("CommitToken execution_id is missing")
        return execution_id


@dataclass(frozen=True)
class SanityCanaryReconciliationWorkItem:
    execution_id: str
    action_case: ContentActionCase
    integrity_baseline: Any
    outcome_receipt_id: str
    observation_window: Mapping[str, Any]
    attribution_score: float
    confidence: float
    counterfactual_ref: str | None = None


class ReconciliationWorkStatus(str, Enum):
    RECONCILED = "RECONCILED"
    STILL_UNKNOWN = "STILL_UNKNOWN"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class SanityCanaryReconciliationWorkResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    status: ReconciliationWorkStatus
    before_state: ExecutionState
    after_state: ExecutionState
    provider_resolution: str | None = None
    outcome_receipt_id: str | None = None
    error_class: str | None = None


class SanityCanaryReconciliationWorker:
    """Process an explicit finite work list exactly once with no provider mutation."""

    def __init__(
        self,
        *,
        journal: SQLiteExecutionJournal,
        adapter: ContentMutationReconciliationAdapter,
    ) -> None:
        self._journal = journal
        self._adapter = adapter

    def run_once(
        self,
        items: Sequence[SanityCanaryReconciliationWorkItem],
    ) -> tuple[SanityCanaryReconciliationWorkResult, ...]:
        results: list[SanityCanaryReconciliationWorkResult] = []
        for item in items:
            try:
                before = self._journal.get(item.execution_id)
            except ExecutionJournalError as exc:
                results.append(
                    SanityCanaryReconciliationWorkResult(
                        execution_id=item.execution_id,
                        status=ReconciliationWorkStatus.ERROR,
                        before_state=ExecutionState.CANCELLED,
                        after_state=ExecutionState.CANCELLED,
                        error_class=type(exc).__name__,
                    )
                )
                continue
            if before.state not in {
                ExecutionState.INDETERMINATE,
                ExecutionState.RECONCILIATION_REQUIRED,
            }:
                results.append(
                    SanityCanaryReconciliationWorkResult(
                        execution_id=item.execution_id,
                        status=ReconciliationWorkStatus.SKIPPED,
                        before_state=before.state,
                        after_state=before.state,
                    )
                )
                continue
            try:
                reconciled = self._adapter.reconcile(
                    execution_id=item.execution_id,
                    action_case=item.action_case,
                    integrity_baseline=item.integrity_baseline,
                    outcome_receipt_id=item.outcome_receipt_id,
                    observation_window=item.observation_window,
                    attribution_score=item.attribution_score,
                    confidence=item.confidence,
                    counterfactual_ref=item.counterfactual_ref,
                )
                after = reconciled.record
                unknown = reconciled.outcome_receipt is None
                results.append(
                    SanityCanaryReconciliationWorkResult(
                        execution_id=item.execution_id,
                        status=(
                            ReconciliationWorkStatus.STILL_UNKNOWN
                            if unknown
                            else ReconciliationWorkStatus.RECONCILED
                        ),
                        before_state=before.state,
                        after_state=after.state,
                        provider_resolution=reconciled.observation.resolution.value,
                        outcome_receipt_id=(
                            None if unknown else item.outcome_receipt_id
                        ),
                    )
                )
            except Exception as exc:
                current = self._journal.get(item.execution_id)
                results.append(
                    SanityCanaryReconciliationWorkResult(
                        execution_id=item.execution_id,
                        status=ReconciliationWorkStatus.ERROR,
                        before_state=before.state,
                        after_state=current.state,
                        error_class=type(exc).__name__,
                    )
                )
        return tuple(results)
