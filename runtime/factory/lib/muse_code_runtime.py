"""Provider-neutral runtime patterns inspired by Meta Muse Code.

This module adopts durable patterns, not Meta authority semantics:
- persistent specialist subagents for a run,
- append-only hash-chained runtime events,
- restart-safe replay from SQLite,
- immutable goal binding,
- provenance-preserving context compaction.

Runtime state never grants authority. Consequence-bearing execution still
requires the Factory's fresh VAIG -> REHT -> RACS authorization path and
Veritas-backed evidence at the external effect boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


RUNTIME_EVENT_TYPES = {
    "model.call",
    "tool.run",
    "approval",
    "edit",
    "goal.bound",
    "specialist.started",
    "specialist.heartbeat",
    "specialist.stopped",
    "context.compacted",
}
SPECIALIST_STATES = {"ACTIVE", "PAUSED", "STOPPED"}


class MuseRuntimeError(RuntimeError):
    """Base error for governed long-horizon runtime state."""


class GoalDriftError(MuseRuntimeError):
    """Raised when a run attempts to silently replace its bound goal."""


class SpecialistIdentityError(MuseRuntimeError):
    """Raised when a persistent specialist identity is reused inconsistently."""


class EventChainError(MuseRuntimeError):
    """Raised when append-only runtime history fails integrity validation."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _now_ns() -> int:
    return time.time_ns()


def _require_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MuseRuntimeError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class GoalBinding:
    run_id: str
    goal_id: str
    objective: str
    success_criteria: tuple[str, ...]
    objective_digest: str
    criteria_digest: str
    created_at_ns: int
    authority_effect: str = "none"


@dataclass(frozen=True)
class PersistentSpecialist:
    run_id: str
    specialist_id: str
    role: str
    provider_id: str
    workspace_ref: str
    state: str
    started_at_ns: int
    last_seen_seq: int
    authority_effect: str = "none"


@dataclass(frozen=True)
class RuntimeEvent:
    run_id: str
    seq: int
    event_id: str
    event_type: str
    actor_id: str
    payload: Mapping[str, Any]
    payload_digest: str
    prev_hash: str
    event_hash: str
    created_at_ns: int
    authority_effect: str = "none"


@dataclass(frozen=True)
class ContextCompaction:
    run_id: str
    compaction_id: str
    through_seq: int
    source_chain_hash: str
    summary: str
    compacted_digest: str
    created_at_ns: int
    authority_effect: str = "none"


class MuseRuntimeStore:
    """Durable non-authoritative state for long-running Factory work.

    SQLite is intentionally local and simple. The event table is the source of
    truth for replay; every append is hash-chained to the previous event in the
    same run. Reopening the database recovers the same event history and stable
    specialist identities.
    """

    DEFAULT_DB = os.path.expanduser("~/.valo/muse-runtime.db")

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = str(path or self.DEFAULT_DB)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self.conn:
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS goals (
                    run_id TEXT PRIMARY KEY,
                    goal_id TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    success_criteria_json TEXT NOT NULL,
                    objective_digest TEXT NOT NULL,
                    criteria_digest TEXT NOT NULL,
                    created_at_ns INTEGER NOT NULL
                )"""
            )
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS specialists (
                    run_id TEXT NOT NULL,
                    specialist_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    provider_id TEXT NOT NULL,
                    workspace_ref TEXT NOT NULL,
                    state TEXT NOT NULL,
                    started_at_ns INTEGER NOT NULL,
                    last_seen_seq INTEGER NOT NULL,
                    PRIMARY KEY (run_id, specialist_id),
                    UNIQUE (run_id, role)
                )"""
            )
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_digest TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at_ns INTEGER NOT NULL,
                    PRIMARY KEY (run_id, seq),
                    UNIQUE (run_id, event_id)
                )"""
            )
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS compactions (
                    run_id TEXT NOT NULL,
                    compaction_id TEXT NOT NULL,
                    through_seq INTEGER NOT NULL,
                    source_chain_hash TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    compacted_digest TEXT NOT NULL,
                    created_at_ns INTEGER NOT NULL,
                    PRIMARY KEY (run_id, compaction_id)
                )"""
            )

    def close(self) -> None:
        self.conn.close()

    @property
    def has_authority_surface(self) -> bool:
        return False

    def bind_goal(
        self,
        run_id: str,
        objective: str,
        success_criteria: Sequence[str],
        *,
        goal_id: str | None = None,
    ) -> GoalBinding:
        run = _require_nonempty(run_id, "run_id")
        obj = _require_nonempty(objective, "objective")
        criteria = tuple(
            _require_nonempty(item, "success_criterion") for item in success_criteria
        )
        if not criteria:
            raise MuseRuntimeError("success_criteria must not be empty")

        existing = self.conn.execute(
            "SELECT * FROM goals WHERE run_id=?", (run,)
        ).fetchone()
        obj_digest = digest(obj)
        criteria_digest = digest(criteria)
        if existing is not None:
            binding = self._goal_from_row(existing)
            if (
                binding.objective_digest != obj_digest
                or binding.criteria_digest != criteria_digest
            ):
                raise GoalDriftError(
                    "run goal is already bound; create an explicit new run to change it"
                )
            return binding

        created = _now_ns()
        binding = GoalBinding(
            run_id=run,
            goal_id=goal_id or f"goal-{uuid.uuid4().hex}",
            objective=obj,
            success_criteria=criteria,
            objective_digest=obj_digest,
            criteria_digest=criteria_digest,
            created_at_ns=created,
        )
        with self._lock, self.conn:
            self.conn.execute(
                """INSERT INTO goals (
                    run_id, goal_id, objective, success_criteria_json,
                    objective_digest, criteria_digest, created_at_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    binding.run_id,
                    binding.goal_id,
                    binding.objective,
                    json.dumps(binding.success_criteria, ensure_ascii=False),
                    binding.objective_digest,
                    binding.criteria_digest,
                    binding.created_at_ns,
                ),
            )
        self.append_event(
            run,
            "goal.bound",
            actor_id="factory",
            payload={
                "goal_id": binding.goal_id,
                "objective_digest": binding.objective_digest,
                "criteria_digest": binding.criteria_digest,
                "authority_effect": "none",
            },
        )
        return binding

    def goal(self, run_id: str) -> GoalBinding | None:
        row = self.conn.execute(
            "SELECT * FROM goals WHERE run_id=?", (run_id,)
        ).fetchone()
        return self._goal_from_row(row) if row else None

    def ensure_specialist(
        self,
        run_id: str,
        role: str,
        provider_id: str,
        workspace_ref: str,
        *,
        specialist_id: str | None = None,
    ) -> PersistentSpecialist:
        run = _require_nonempty(run_id, "run_id")
        specialist_role = _require_nonempty(role, "role")
        provider = _require_nonempty(provider_id, "provider_id")
        workspace = _require_nonempty(workspace_ref, "workspace_ref")
        existing = self.conn.execute(
            "SELECT * FROM specialists WHERE run_id=? AND role=?",
            (run, specialist_role),
        ).fetchone()
        if existing is not None:
            specialist = self._specialist_from_row(existing)
            if (
                specialist.provider_id != provider
                or specialist.workspace_ref != workspace
                or specialist.state == "STOPPED"
            ):
                raise SpecialistIdentityError(
                    "persistent specialist role is already bound to a different identity or stopped session"
                )
            return specialist

        started = _now_ns()
        sid = specialist_id or f"specialist-{uuid.uuid4().hex}"
        with self._lock, self.conn:
            self.conn.execute(
                """INSERT INTO specialists (
                    run_id, specialist_id, role, provider_id, workspace_ref,
                    state, started_at_ns, last_seen_seq
                ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, 0)""",
                (run, sid, specialist_role, provider, workspace, started),
            )
        event = self.append_event(
            run,
            "specialist.started",
            actor_id=sid,
            payload={
                "role": specialist_role,
                "provider_id": provider,
                "workspace_ref": workspace,
                "authority_effect": "none",
            },
        )
        self._set_specialist_last_seen(run, sid, event.seq)
        return self.specialist(run, sid)

    def specialist(self, run_id: str, specialist_id: str) -> PersistentSpecialist:
        row = self.conn.execute(
            "SELECT * FROM specialists WHERE run_id=? AND specialist_id=?",
            (run_id, specialist_id),
        ).fetchone()
        if row is None:
            raise MuseRuntimeError(f"unknown specialist_id: {specialist_id}")
        return self._specialist_from_row(row)

    def specialists(self, run_id: str) -> tuple[PersistentSpecialist, ...]:
        rows = self.conn.execute(
            "SELECT * FROM specialists WHERE run_id=? ORDER BY started_at_ns, specialist_id",
            (run_id,),
        ).fetchall()
        return tuple(self._specialist_from_row(row) for row in rows)

    def heartbeat_specialist(
        self, run_id: str, specialist_id: str, *, state: str = "ACTIVE"
    ) -> PersistentSpecialist:
        normalized = state.upper()
        if normalized not in SPECIALIST_STATES:
            raise MuseRuntimeError(f"invalid specialist state: {state}")
        current = self.specialist(run_id, specialist_id)
        if current.state == "STOPPED":
            raise SpecialistIdentityError("stopped specialist cannot be resumed implicitly")
        event_type = (
            "specialist.stopped" if normalized == "STOPPED" else "specialist.heartbeat"
        )
        event = self.append_event(
            run_id,
            event_type,
            actor_id=specialist_id,
            payload={"state": normalized, "authority_effect": "none"},
        )
        with self._lock, self.conn:
            self.conn.execute(
                """UPDATE specialists SET state=?, last_seen_seq=?
                   WHERE run_id=? AND specialist_id=?""",
                (normalized, event.seq, run_id, specialist_id),
            )
        return self.specialist(run_id, specialist_id)

    def append_event(
        self,
        run_id: str,
        event_type: str,
        *,
        actor_id: str,
        payload: Mapping[str, Any],
        event_id: str | None = None,
    ) -> RuntimeEvent:
        run = _require_nonempty(run_id, "run_id")
        kind = _require_nonempty(event_type, "event_type")
        actor = _require_nonempty(actor_id, "actor_id")
        if kind not in RUNTIME_EVENT_TYPES:
            raise MuseRuntimeError(f"unsupported runtime event type: {kind}")
        if not isinstance(payload, Mapping):
            raise MuseRuntimeError("payload must be an object")

        payload_dict = dict(payload)
        payload_bytes = canonical_json(payload_dict)
        payload_digest = "sha256:" + hashlib.sha256(payload_bytes).hexdigest()
        created = _now_ns()
        eid = event_id or f"evt-{uuid.uuid4().hex}"

        with self._lock, self.conn:
            previous = self.conn.execute(
                """SELECT seq, event_hash FROM events
                   WHERE run_id=? ORDER BY seq DESC LIMIT 1""",
                (run,),
            ).fetchone()
            seq = int(previous["seq"]) + 1 if previous else 1
            prev_hash = str(previous["event_hash"]) if previous else "GENESIS"
            event_hash = self._event_hash(
                run_id=run,
                seq=seq,
                event_id=eid,
                event_type=kind,
                actor_id=actor,
                payload_digest=payload_digest,
                prev_hash=prev_hash,
                created_at_ns=created,
            )
            self.conn.execute(
                """INSERT INTO events (
                    run_id, seq, event_id, event_type, actor_id, payload_json,
                    payload_digest, prev_hash, event_hash, created_at_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run,
                    seq,
                    eid,
                    kind,
                    actor,
                    payload_bytes.decode("utf-8"),
                    payload_digest,
                    prev_hash,
                    event_hash,
                    created,
                ),
            )

        return RuntimeEvent(
            run_id=run,
            seq=seq,
            event_id=eid,
            event_type=kind,
            actor_id=actor,
            payload=payload_dict,
            payload_digest=payload_digest,
            prev_hash=prev_hash,
            event_hash=event_hash,
            created_at_ns=created,
        )

    def events(self, run_id: str, *, after_seq: int = 0) -> tuple[RuntimeEvent, ...]:
        rows = self.conn.execute(
            """SELECT * FROM events WHERE run_id=? AND seq>?
               ORDER BY seq ASC""",
            (run_id, int(after_seq)),
        ).fetchall()
        return tuple(self._event_from_row(row) for row in rows)

    def verify_chain(self, run_id: str) -> bool:
        expected_prev = "GENESIS"
        expected_seq = 1
        for event in self.events(run_id):
            if event.seq != expected_seq or event.prev_hash != expected_prev:
                return False
            if digest(dict(event.payload)) != event.payload_digest:
                return False
            expected_hash = self._event_hash(
                run_id=event.run_id,
                seq=event.seq,
                event_id=event.event_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                payload_digest=event.payload_digest,
                prev_hash=event.prev_hash,
                created_at_ns=event.created_at_ns,
            )
            if expected_hash != event.event_hash:
                return False
            expected_prev = event.event_hash
            expected_seq += 1
        return True

    def compact_context(
        self, run_id: str, *, through_seq: int, summary: str
    ) -> ContextCompaction:
        compacted_summary = _require_nonempty(summary, "summary")
        if not self.verify_chain(run_id):
            raise EventChainError("cannot compact an invalid event chain")
        source = self.conn.execute(
            "SELECT event_hash FROM events WHERE run_id=? AND seq=?",
            (run_id, int(through_seq)),
        ).fetchone()
        if source is None:
            raise MuseRuntimeError("through_seq must identify an existing event")

        compaction = ContextCompaction(
            run_id=run_id,
            compaction_id=f"compact-{uuid.uuid4().hex}",
            through_seq=int(through_seq),
            source_chain_hash=str(source["event_hash"]),
            summary=compacted_summary,
            compacted_digest=digest(compacted_summary),
            created_at_ns=_now_ns(),
        )
        with self._lock, self.conn:
            self.conn.execute(
                """INSERT INTO compactions (
                    run_id, compaction_id, through_seq, source_chain_hash,
                    summary, compacted_digest, created_at_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    compaction.run_id,
                    compaction.compaction_id,
                    compaction.through_seq,
                    compaction.source_chain_hash,
                    compaction.summary,
                    compaction.compacted_digest,
                    compaction.created_at_ns,
                ),
            )
        self.append_event(
            run_id,
            "context.compacted",
            actor_id="factory",
            payload={
                "compaction_id": compaction.compaction_id,
                "through_seq": compaction.through_seq,
                "source_chain_hash": compaction.source_chain_hash,
                "compacted_digest": compaction.compacted_digest,
                "authority_effect": "none",
            },
        )
        return compaction

    def latest_compaction(self, run_id: str) -> ContextCompaction | None:
        row = self.conn.execute(
            """SELECT * FROM compactions WHERE run_id=?
               ORDER BY through_seq DESC, created_at_ns DESC LIMIT 1""",
            (run_id,),
        ).fetchone()
        return self._compaction_from_row(row) if row else None

    def recover(self, run_id: str) -> dict[str, Any]:
        """Recover exact persisted run state after process restart.

        The compacted summary is guidance only; its source event hash remains
        bound so callers can verify what history it summarizes. Events after the
        compaction point are replayed exactly from the append-only log.
        """
        if not self.verify_chain(run_id):
            raise EventChainError("runtime event chain failed integrity verification")
        goal = self.goal(run_id)
        compaction = self.latest_compaction(run_id)
        after_seq = compaction.through_seq if compaction else 0
        all_events = self.events(run_id)
        return {
            "schema": "valo.muse-runtime.recovery.v1",
            "run_id": run_id,
            "goal": goal,
            "specialists": self.specialists(run_id),
            "latest_compaction": compaction,
            "events_after_compaction": self.events(run_id, after_seq=after_seq),
            "last_seq": all_events[-1].seq if all_events else 0,
            "last_event_hash": all_events[-1].event_hash if all_events else "GENESIS",
            "chain_valid": True,
            "authority_effect": "none",
        }

    def _set_specialist_last_seen(
        self, run_id: str, specialist_id: str, last_seen_seq: int
    ) -> None:
        with self._lock, self.conn:
            self.conn.execute(
                """UPDATE specialists SET last_seen_seq=?
                   WHERE run_id=? AND specialist_id=?""",
                (int(last_seen_seq), run_id, specialist_id),
            )

    @staticmethod
    def _event_hash(
        *,
        run_id: str,
        seq: int,
        event_id: str,
        event_type: str,
        actor_id: str,
        payload_digest: str,
        prev_hash: str,
        created_at_ns: int,
    ) -> str:
        return digest(
            {
                "run_id": run_id,
                "seq": seq,
                "event_id": event_id,
                "event_type": event_type,
                "actor_id": actor_id,
                "payload_digest": payload_digest,
                "prev_hash": prev_hash,
                "created_at_ns": created_at_ns,
            }
        )

    @staticmethod
    def _goal_from_row(row: sqlite3.Row) -> GoalBinding:
        return GoalBinding(
            run_id=str(row["run_id"]),
            goal_id=str(row["goal_id"]),
            objective=str(row["objective"]),
            success_criteria=tuple(json.loads(row["success_criteria_json"])),
            objective_digest=str(row["objective_digest"]),
            criteria_digest=str(row["criteria_digest"]),
            created_at_ns=int(row["created_at_ns"]),
        )

    @staticmethod
    def _specialist_from_row(row: sqlite3.Row) -> PersistentSpecialist:
        return PersistentSpecialist(
            run_id=str(row["run_id"]),
            specialist_id=str(row["specialist_id"]),
            role=str(row["role"]),
            provider_id=str(row["provider_id"]),
            workspace_ref=str(row["workspace_ref"]),
            state=str(row["state"]),
            started_at_ns=int(row["started_at_ns"]),
            last_seen_seq=int(row["last_seen_seq"]),
        )

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> RuntimeEvent:
        return RuntimeEvent(
            run_id=str(row["run_id"]),
            seq=int(row["seq"]),
            event_id=str(row["event_id"]),
            event_type=str(row["event_type"]),
            actor_id=str(row["actor_id"]),
            payload=json.loads(row["payload_json"]),
            payload_digest=str(row["payload_digest"]),
            prev_hash=str(row["prev_hash"]),
            event_hash=str(row["event_hash"]),
            created_at_ns=int(row["created_at_ns"]),
        )

    @staticmethod
    def _compaction_from_row(row: sqlite3.Row) -> ContextCompaction:
        return ContextCompaction(
            run_id=str(row["run_id"]),
            compaction_id=str(row["compaction_id"]),
            through_seq=int(row["through_seq"]),
            source_chain_hash=str(row["source_chain_hash"]),
            summary=str(row["summary"]),
            compacted_digest=str(row["compacted_digest"]),
            created_at_ns=int(row["created_at_ns"]),
        )


__all__ = [
    "ContextCompaction",
    "EventChainError",
    "GoalBinding",
    "GoalDriftError",
    "MuseRuntimeError",
    "MuseRuntimeStore",
    "PersistentSpecialist",
    "RUNTIME_EVENT_TYPES",
    "RuntimeEvent",
    "SPECIALIST_STATES",
    "SpecialistIdentityError",
    "canonical_json",
    "digest",
]
