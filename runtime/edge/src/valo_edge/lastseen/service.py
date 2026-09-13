"""Governed, provenance-preserving local memory for LastSeen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Sequence
from uuid import uuid4

from valo_edge.contracts import EdgeActionProposal, EdgeDecision, OfflineAuthorityEnvelope
from valo_edge.gateway import HardwareNeutralGateway
from valo_edge.runtime import MicroRehtEngine


_ALLOWED_ACTIONS = [
    "STORE_OBSERVATION",
    "READ_LAST_SEEN",
    "DELETE_OBJECT_HISTORY",
    "REBUILD_MEMORY_INDEX",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_iso(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("timestamp must not be empty")
    parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9æøå]+", " ", value)
    return " ".join(value.split())


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryScope:
    """Deterministic local retrieval boundary."""

    camera_ids: tuple[str, ...] = ()
    zone_ids: tuple[str, ...] = ()
    since_iso: str | None = None
    until_iso: str | None = None

    def canonical(self) -> "MemoryScope":
        since_iso = _canonical_iso(self.since_iso) if self.since_iso else None
        until_iso = _canonical_iso(self.until_iso) if self.until_iso else None
        if since_iso and until_iso and since_iso > until_iso:
            raise ValueError("scope since_iso must be before or equal to until_iso")
        return MemoryScope(
            camera_ids=tuple(sorted({value.strip() for value in self.camera_ids if value.strip()})),
            zone_ids=tuple(sorted({value.strip() for value in self.zone_ids if value.strip()})),
            since_iso=since_iso,
            until_iso=until_iso,
        )

    def as_parameters(self) -> dict[str, Any]:
        canonical = self.canonical()
        return {
            "camera_ids": list(canonical.camera_ids),
            "zone_ids": list(canonical.zone_ids),
            "since_iso": canonical.since_iso,
            "until_iso": canonical.until_iso,
        }


@dataclass(frozen=True)
class LastSeenResult:
    object_name: str
    location: str
    observed_at_iso: str
    image_ref: str | None
    confidence: float
    receipt_digest: str
    source_id: str = ""
    ingested_at_iso: str = ""
    source_type: str = "local-observation"
    source_device_id: str = ""
    camera_id: str | None = None
    zone_id: str | None = None
    policy_version: str = ""
    source_receipt_digest: str = ""
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class IndexRebuildResult:
    indexed_observations: int
    index_entries: int
    manifest_digest: str
    receipt_digest: str


@dataclass(frozen=True)
class LastSeenDeletionResult:
    deleted_observations: int
    object_name_hash: str
    receipt_digest: str
    deleted_at_iso: str
    policy_version: str


class LastSeenService:
    """Local object memory with micro-REHT at every consequence boundary."""

    def __init__(
        self,
        db_path: str | Path = "lastseen.db",
        *,
        device_id: str = "lastseen-local-01",
        policy_version: str = "lastseen-policy-v1",
    ) -> None:
        self.db_path = str(db_path)
        self.device_id = device_id
        self.policy_version = policy_version
        self._engine = MicroRehtEngine(state_path=f"{self.db_path}.replay-state.json")
        self._gateway = HardwareNeutralGateway()
        # Requests are serialized by the single-threaded local API server, so the
        # single SQLite connection may be shared across that serving thread.
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    @property
    def engine(self) -> MicroRehtEngine:
        return self._engine

    @property
    def gateway(self) -> HardwareNeutralGateway:
        return self._gateway

    def close(self) -> None:
        self._engine.flush()
        self._conn.close()

    def __enter__(self) -> "LastSeenService":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT,
                object_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                location TEXT NOT NULL,
                image_ref TEXT,
                confidence REAL NOT NULL,
                observed_at_iso TEXT NOT NULL,
                ingested_at_iso TEXT,
                source_type TEXT,
                source_device_id TEXT,
                camera_id TEXT,
                zone_id TEXT,
                policy_version TEXT,
                metadata_json TEXT NOT NULL,
                receipt_digest TEXT NOT NULL
            )
            """
        )
        existing_columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(observations)").fetchall()
        }
        migrations = {
            "source_id": "TEXT",
            "ingested_at_iso": "TEXT",
            "source_type": "TEXT",
            "source_device_id": "TEXT",
            "camera_id": "TEXT",
            "zone_id": "TEXT",
            "policy_version": "TEXT",
        }
        for column, declaration in migrations.items():
            if column not in existing_columns:
                self._conn.execute(f"ALTER TABLE observations ADD COLUMN {column} {declaration}")

        self._migrate_legacy_rows()

        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_lastseen_source_id "
            "ON observations(source_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lastseen_name_time "
            "ON observations(normalized_name, observed_at_iso DESC)"
        )
        memory_index_exists = self._conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'memory_index'"
        ).fetchone() is not None
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_index (
                source_id TEXT NOT NULL,
                lookup_term TEXT NOT NULL,
                observed_at_iso TEXT NOT NULL,
                day_key TEXT NOT NULL,
                hour_key TEXT NOT NULL,
                episode_key TEXT NOT NULL,
                camera_id TEXT,
                zone_id TEXT,
                PRIMARY KEY (source_id, lookup_term),
                FOREIGN KEY (source_id) REFERENCES observations(source_id)
                    ON DELETE CASCADE
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_lookup_time "
            "ON memory_index(lookup_term, observed_at_iso DESC)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_temporal_scope "
            "ON memory_index(day_key, hour_key, camera_id, zone_id)"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deletion_receipts (
                receipt_digest TEXT PRIMARY KEY,
                object_name_hash TEXT NOT NULL,
                deleted_count INTEGER NOT NULL,
                policy_version TEXT NOT NULL,
                deleted_at_iso TEXT NOT NULL
            )
            """
        )
        if not memory_index_exists:
            self._backfill_missing_indexes()
        self._conn.commit()

    def _migrate_legacy_rows(self) -> None:
        rows = self._conn.execute(
            """
            SELECT id, source_id, object_name, location, image_ref, confidence,
                   observed_at_iso, ingested_at_iso, source_type, source_device_id,
                   camera_id, zone_id, policy_version, metadata_json, receipt_digest
            FROM observations
            """
        ).fetchall()
        for row in rows:
            metadata = self._decode_metadata(row["metadata_json"])
            source_id = row["source_id"] or (
                "legacy-" + _stable_hash(
                    {
                        "id": row["id"],
                        "object_name": row["object_name"],
                        "location": row["location"],
                        "observed_at_iso": row["observed_at_iso"],
                        "receipt_digest": row["receipt_digest"],
                    }
                )[:24]
            )
            camera_id = row["camera_id"] or metadata.get("camera_id")
            zone_id = row["zone_id"] or metadata.get("zone_id")
            self._conn.execute(
                """
                UPDATE observations
                SET source_id = ?,
                    ingested_at_iso = ?,
                    source_type = ?,
                    source_device_id = ?,
                    camera_id = ?,
                    zone_id = ?,
                    policy_version = ?
                WHERE id = ?
                """,
                (
                    source_id,
                    row["ingested_at_iso"] or row["observed_at_iso"],
                    row["source_type"] or "legacy-observation",
                    row["source_device_id"] or self.device_id,
                    camera_id,
                    zone_id,
                    row["policy_version"] or self.policy_version,
                    row["id"],
                ),
            )

    @staticmethod
    def _decode_metadata(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("metadata_json must decode to an object")
        return decoded

    def _proposal(
        self,
        action_type: str,
        parameters: dict[str, Any],
        timestamp_iso: str,
    ) -> EdgeActionProposal:
        return EdgeActionProposal(
            proposal_id=f"lastseen-{uuid4().hex[:16]}",
            device_id=self.device_id,
            action_type=action_type,
            parameters=parameters,
            timestamp_iso=timestamp_iso,
            nonce=uuid4().hex,
        )

    def _authorize(self, proposal: EdgeActionProposal, timestamp_iso: str):
        envelope = OfflineAuthorityEnvelope(
            envelope_id=f"lastseen-envelope-{self.device_id}",
            device_id=self.device_id,
            allowed_action_types=list(_ALLOWED_ACTIONS),
            max_rate_per_sec=25.0,
            valid_until_iso="2099-12-31T23:59:59Z",
            is_revoked=False,
        )
        clearance = self._engine.evaluate_proposal(proposal, envelope, timestamp_iso)
        if clearance.decision is not EdgeDecision.ALLOW:
            receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
            raise PermissionError(f"{clearance.reason} receipt={receipt.receipt_digest}")
        return clearance

    @staticmethod
    def _temporal_keys(
        observed_at_iso: str,
        camera_id: str | None,
        zone_id: str | None,
    ) -> tuple[str, str, str]:
        parsed = datetime.fromisoformat(observed_at_iso.replace("Z", "+00:00"))
        day_key = parsed.strftime("%Y-%m-%d")
        hour_key = parsed.strftime("%Y-%m-%dT%H")
        episode_key = ":".join(
            (camera_id or "_camera", zone_id or "_zone", day_key, parsed.strftime("%H"))
        )
        return day_key, hour_key, episode_key

    @staticmethod
    def _index_terms(object_name: str, metadata: dict[str, Any]) -> tuple[str, ...]:
        aliases = metadata.get("aliases", ())
        if isinstance(aliases, str):
            aliases = [aliases]
        if not isinstance(aliases, Sequence):
            aliases = ()
        terms = {_normalize(object_name)}
        terms.update(_normalize(str(alias)) for alias in aliases)
        terms.discard("")
        return tuple(sorted(terms))

    def _write_index_rows(
        self,
        *,
        source_id: str,
        object_name: str,
        observed_at_iso: str,
        camera_id: str | None,
        zone_id: str | None,
        metadata: dict[str, Any],
    ) -> int:
        day_key, hour_key, episode_key = self._temporal_keys(
            observed_at_iso, camera_id, zone_id
        )
        rows = [
            (
                source_id,
                term,
                observed_at_iso,
                day_key,
                hour_key,
                episode_key,
                camera_id,
                zone_id,
            )
            for term in self._index_terms(object_name, metadata)
        ]
        self._conn.executemany(
            """
            INSERT OR REPLACE INTO memory_index (
                source_id, lookup_term, observed_at_iso, day_key, hour_key,
                episode_key, camera_id, zone_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    def _backfill_missing_indexes(self) -> int:
        """Backfill schema-migration gaps without rewriting existing derived indexes."""
        rows = self._conn.execute(
            """
            SELECT source_id, object_name, observed_at_iso, camera_id, zone_id,
                   metadata_json
            FROM observations AS o
            WHERE NOT EXISTS (
                SELECT 1 FROM memory_index AS mi WHERE mi.source_id = o.source_id
            )
            ORDER BY source_id
            """
        ).fetchall()
        entries = 0
        for row in rows:
            entries += self._write_index_rows(
                source_id=row["source_id"],
                object_name=row["object_name"],
                observed_at_iso=row["observed_at_iso"],
                camera_id=row["camera_id"],
                zone_id=row["zone_id"],
                metadata=self._decode_metadata(row["metadata_json"]),
            )
        return entries

    def _rebuild_indexes_internal(self) -> tuple[int, int]:
        self._conn.execute("DELETE FROM memory_index")
        rows = self._conn.execute(
            """
            SELECT source_id, object_name, observed_at_iso, camera_id, zone_id,
                   metadata_json
            FROM observations
            ORDER BY source_id
            """
        ).fetchall()
        entries = 0
        for row in rows:
            entries += self._write_index_rows(
                source_id=row["source_id"],
                object_name=row["object_name"],
                observed_at_iso=row["observed_at_iso"],
                camera_id=row["camera_id"],
                zone_id=row["zone_id"],
                metadata=self._decode_metadata(row["metadata_json"]),
            )
        return len(rows), entries

    def _index_manifest_digest(self) -> str:
        rows = self._conn.execute(
            """
            SELECT source_id, lookup_term, observed_at_iso, day_key, hour_key,
                   episode_key, camera_id, zone_id
            FROM memory_index
            ORDER BY source_id, lookup_term
            """
        ).fetchall()
        return _stable_hash([dict(row) for row in rows])

    def remember(
        self,
        object_name: str,
        location: str,
        *,
        image_ref: str | None = None,
        confidence: float = 1.0,
        observed_at_iso: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_id: str | None = None,
        source_type: str = "local-observation",
        source_device_id: str | None = None,
        camera_id: str | None = None,
        zone_id: str | None = None,
        policy_version: str | None = None,
        aliases: Iterable[str] = (),
    ) -> LastSeenResult:
        """Store one source observation and its rebuildable derived index."""
        if not object_name.strip():
            raise ValueError("object_name must not be empty")
        if not location.strip():
            raise ValueError("location must not be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        timestamp_iso = _canonical_iso(observed_at_iso or _utc_now_iso())
        ingested_at_iso = _utc_now_iso()
        metadata_payload = dict(metadata or {})
        metadata_aliases = metadata_payload.get("aliases", [])
        if isinstance(metadata_aliases, str):
            metadata_aliases = [metadata_aliases]
        elif not isinstance(metadata_aliases, Sequence):
            metadata_aliases = []
        metadata_payload["aliases"] = sorted(
            {
                str(alias).strip()
                for alias in [*metadata_aliases, *aliases]
                if str(alias).strip()
            }
        )
        resolved_camera_id = camera_id or metadata_payload.get("camera_id")
        resolved_zone_id = zone_id or metadata_payload.get("zone_id")
        if resolved_camera_id:
            metadata_payload["camera_id"] = resolved_camera_id
        if resolved_zone_id:
            metadata_payload["zone_id"] = resolved_zone_id

        resolved_source_id = (source_id or f"obs-{uuid4().hex}").strip()
        if not resolved_source_id:
            raise ValueError("source_id must not be empty")
        resolved_source_type = (source_type or "local-observation").strip() or "local-observation"
        resolved_source_device_id = source_device_id or self.device_id
        resolved_policy_version = policy_version or self.policy_version

        proposal = self._proposal(
            "STORE_OBSERVATION",
            {
                "source_id": resolved_source_id,
                "object_name": object_name,
                "location": location,
                "image_ref": image_ref,
                "confidence": confidence,
                "camera_id": resolved_camera_id,
                "zone_id": resolved_zone_id,
                "policy_version": resolved_policy_version,
            },
            timestamp_iso,
        )
        clearance = self._authorize(proposal, timestamp_iso)

        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO observations (
                        source_id, object_name, normalized_name, location, image_ref,
                        confidence, observed_at_iso, ingested_at_iso, source_type,
                        source_device_id, camera_id, zone_id, policy_version,
                        metadata_json, receipt_digest
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        resolved_source_id,
                        object_name.strip(),
                        _normalize(object_name),
                        location.strip(),
                        image_ref,
                        confidence,
                        timestamp_iso,
                        ingested_at_iso,
                        resolved_source_type,
                        resolved_source_device_id,
                        resolved_camera_id,
                        resolved_zone_id,
                        resolved_policy_version,
                        json.dumps(metadata_payload, sort_keys=True, ensure_ascii=False),
                        "pending",
                    ),
                )
                self._write_index_rows(
                    source_id=resolved_source_id,
                    object_name=object_name,
                    observed_at_iso=timestamp_iso,
                    camera_id=resolved_camera_id,
                    zone_id=resolved_zone_id,
                    metadata=metadata_payload,
                )
                receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
                self._conn.execute(
                    "UPDATE observations SET receipt_digest = ? WHERE source_id = ?",
                    (receipt.receipt_digest or "", resolved_source_id),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"source_id already exists: {resolved_source_id}") from exc

        return LastSeenResult(
            object_name=object_name.strip(),
            location=location.strip(),
            observed_at_iso=timestamp_iso,
            image_ref=image_ref,
            confidence=confidence,
            receipt_digest=receipt.receipt_digest or "",
            source_id=resolved_source_id,
            ingested_at_iso=ingested_at_iso,
            source_type=resolved_source_type,
            source_device_id=resolved_source_device_id,
            camera_id=resolved_camera_id,
            zone_id=resolved_zone_id,
            policy_version=resolved_policy_version,
            source_receipt_digest=receipt.receipt_digest or "",
            metadata=metadata_payload,
        )

    @staticmethod
    def _scope_sql(scope: MemoryScope) -> tuple[list[str], list[Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if scope.camera_ids:
            placeholders = ",".join("?" for _ in scope.camera_ids)
            clauses.append(f"o.camera_id IN ({placeholders})")
            parameters.extend(scope.camera_ids)
        if scope.zone_ids:
            placeholders = ",".join("?" for _ in scope.zone_ids)
            clauses.append(f"o.zone_id IN ({placeholders})")
            parameters.extend(scope.zone_ids)
        if scope.since_iso:
            clauses.append("o.observed_at_iso >= ?")
            parameters.append(scope.since_iso)
        if scope.until_iso:
            clauses.append("o.observed_at_iso <= ?")
            parameters.append(scope.until_iso)
        return clauses, parameters

    def _read_rows(
        self,
        object_name: str,
        *,
        aliases: Iterable[str],
        scope: MemoryScope,
        limit: int,
    ) -> tuple[list[sqlite3.Row], str]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        names = {_normalize(object_name), *(_normalize(alias) for alias in aliases)}
        names.discard("")
        if not names:
            raise ValueError("object_name must not be empty")

        timestamp_iso = _utc_now_iso()
        proposal = self._proposal(
            "READ_LAST_SEEN",
            {
                "query": object_name,
                "aliases": sorted(names),
                "scope": scope.as_parameters(),
                "limit": limit,
            },
            timestamp_iso,
        )
        clearance = self._authorize(proposal, timestamp_iso)

        placeholders = ",".join("?" for _ in names)
        clauses = [f"mi.lookup_term IN ({placeholders})"]
        parameters: list[Any] = list(sorted(names))
        scope_clauses, scope_parameters = self._scope_sql(scope)
        clauses.extend(scope_clauses)
        parameters.extend(scope_parameters)
        parameters.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT DISTINCT
                o.source_id, o.object_name, o.location, o.image_ref, o.confidence,
                o.observed_at_iso, o.ingested_at_iso, o.source_type,
                o.source_device_id, o.camera_id, o.zone_id, o.policy_version,
                o.metadata_json, o.receipt_digest
            FROM memory_index AS mi
            JOIN observations AS o ON o.source_id = mi.source_id
            WHERE {" AND ".join(clauses)}
            ORDER BY o.observed_at_iso DESC, o.id DESC
            LIMIT ?
            """,
            tuple(parameters),
        ).fetchall()

        receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
        return rows, receipt.receipt_digest or ""

    @staticmethod
    def _row_to_result(row: sqlite3.Row, read_receipt_digest: str) -> LastSeenResult:
        metadata = LastSeenService._decode_metadata(row["metadata_json"])
        return LastSeenResult(
            object_name=row["object_name"],
            location=row["location"],
            observed_at_iso=row["observed_at_iso"],
            image_ref=row["image_ref"],
            confidence=float(row["confidence"]),
            receipt_digest=read_receipt_digest,
            source_id=row["source_id"],
            ingested_at_iso=row["ingested_at_iso"],
            source_type=row["source_type"],
            source_device_id=row["source_device_id"],
            camera_id=row["camera_id"],
            zone_id=row["zone_id"],
            policy_version=row["policy_version"],
            source_receipt_digest=row["receipt_digest"],
            metadata=metadata,
        )

    def find(
        self,
        object_name: str,
        *,
        aliases: Iterable[str] = (),
        scope: MemoryScope | None = None,
    ) -> LastSeenResult | None:
        """Return the newest authorized matching observation."""
        canonical_scope = (scope or MemoryScope()).canonical()
        rows, receipt_digest = self._read_rows(
            object_name,
            aliases=aliases,
            scope=canonical_scope,
            limit=1,
        )
        if not rows:
            return None
        return self._row_to_result(rows[0], receipt_digest)

    def history(
        self,
        object_name: str,
        *,
        aliases: Iterable[str] = (),
        scope: MemoryScope | None = None,
        limit: int = 100,
    ) -> list[LastSeenResult]:
        """Return newest-first authorized source observations within a temporal scope."""
        canonical_scope = (scope or MemoryScope()).canonical()
        rows, receipt_digest = self._read_rows(
            object_name,
            aliases=aliases,
            scope=canonical_scope,
            limit=limit,
        )
        return [self._row_to_result(row, receipt_digest) for row in rows]

    def rebuild_indexes(self) -> IndexRebuildResult:
        """Rebuild derived indexes from retained source observations."""
        timestamp_iso = _utc_now_iso()
        proposal = self._proposal(
            "REBUILD_MEMORY_INDEX",
            {"policy_version": self.policy_version},
            timestamp_iso,
        )
        clearance = self._authorize(proposal, timestamp_iso)
        with self._conn:
            observations, entries = self._rebuild_indexes_internal()
        manifest_digest = self._index_manifest_digest()
        receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
        return IndexRebuildResult(
            indexed_observations=observations,
            index_entries=entries,
            manifest_digest=manifest_digest,
            receipt_digest=receipt.receipt_digest or "",
        )

    def forget_with_receipt(self, object_name: str) -> LastSeenDeletionResult:
        """Delete source content and all derived references, retaining only a digest receipt."""
        normalized_name = _normalize(object_name)
        if not normalized_name:
            raise ValueError("object_name must not be empty")

        timestamp_iso = _utc_now_iso()
        object_name_hash = _stable_hash(
            {"normalized_name": normalized_name, "salt": uuid4().hex}
        )
        proposal = self._proposal(
            "DELETE_OBJECT_HISTORY",
            {
                "object_name_hash": object_name_hash,
                "policy_version": self.policy_version,
            },
            timestamp_iso,
        )
        clearance = self._authorize(proposal, timestamp_iso)

        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM observations WHERE normalized_name = ?",
                (normalized_name,),
            )
            receipt = self._gateway.execute_action(proposal, clearance, timestamp_iso)
            self._conn.execute(
                """
                INSERT INTO deletion_receipts (
                    receipt_digest, object_name_hash, deleted_count,
                    policy_version, deleted_at_iso
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    receipt.receipt_digest or "",
                    object_name_hash,
                    int(cursor.rowcount),
                    self.policy_version,
                    timestamp_iso,
                ),
            )

        return LastSeenDeletionResult(
            deleted_observations=int(cursor.rowcount),
            object_name_hash=object_name_hash,
            receipt_digest=receipt.receipt_digest or "",
            deleted_at_iso=timestamp_iso,
            policy_version=self.policy_version,
        )

    def forget(self, object_name: str) -> int:
        """Compatibility wrapper returning the number of deleted source observations."""
        return self.forget_with_receipt(object_name).deleted_observations

    def get_deletion_receipt(self, receipt_digest: str) -> LastSeenDeletionResult | None:
        row = self._conn.execute(
            """
            SELECT receipt_digest, object_name_hash, deleted_count,
                   policy_version, deleted_at_iso
            FROM deletion_receipts
            WHERE receipt_digest = ?
            """,
            (receipt_digest,),
        ).fetchone()
        if row is None:
            return None
        return LastSeenDeletionResult(
            deleted_observations=int(row["deleted_count"]),
            object_name_hash=row["object_name_hash"],
            receipt_digest=row["receipt_digest"],
            deleted_at_iso=row["deleted_at_iso"],
            policy_version=row["policy_version"],
        )

    def get_receipt(self, receipt_digest: str) -> dict[str, Any] | None:
        """Look up a Veritas receipt: deletion receipts first, then observation source receipts."""
        deletion = self.get_deletion_receipt(receipt_digest)
        if deletion is not None:
            return {"kind": "deletion", **deletion.__dict__}
        row = self._conn.execute(
            """
            SELECT source_id, object_name, location, observed_at_iso,
                   source_type, policy_version
            FROM observations
            WHERE receipt_digest = ?
            """,
            (receipt_digest,),
        ).fetchone()
        if row is None:
            return None
        return {
            "kind": "observation",
            "receipt_digest": receipt_digest,
            **dict(row),
        }

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM observations").fetchone()
        return int(row["count"])

    def count_index_entries(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM memory_index").fetchone()
        return int(row["count"])

    def index_manifest_digest(self) -> str:
        return self._index_manifest_digest()
