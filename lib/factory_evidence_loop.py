#!/usr/bin/env python3
"""Governed self-improving factory evidence loop (Fluent-derived Factory OS).

Event-sourced core implementing the adopted loop:

    Observation
      -> shaping (Brief, BehaviorSpec, TechnicalApproach, ImplementationPlan,
                  separate Authority Envelope)
      -> immutable authorized Work Item
      -> isolated Attempt on an exact base SHA
      -> Writer candidate
      -> deterministic Tester evidence bound to candidate SHA
      -> independent read-only parallel Reviewers (PASS/FAIL/UNCERTAIN)
      -> Learner handoff (proposals only, never authority)
      -> immutable Merge Candidate binding every evidence digest
      -> governed landing (mode, claims, drift, CI, REHT, RACS, current head)
      -> post-merge Observation

Design rules enforced in this module:

  * Events are append-only; identical event history rebuilds identical
    projections (see Projection.rebuild / EventStore).
  * Every consequential artifact binds repository, run ID, base/candidate SHA,
    actor identity, timestamp, schema version and content digest.
  * No actor may self-attest: a Work Item's Writer cannot act as Tester,
    Reviewer or Learner for its own candidate, and cannot approve, QC, merge
    or attest completion.
  * Observations are evidence only: they never authorize, dispatch or queue
    themselves.
  * The Learner emits provenance-bound expertise proposals; it never changes
    policy, authority, credentials or canonical expertise directly.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass, field, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "factory-loop-v1"

# Actor roles.
WRITER = "writer"
TESTER = "tester"
REVIEWER = "reviewer"
LEARNER = "learner"
OBSERVER = "observer"

# Review results.
PASS = "PASS"
FAIL = "FAIL"
UNCERTAIN = "UNCERTAIN"
REVIEW_RESULTS = (PASS, FAIL, UNCERTAIN)

# Queues.
HUMAN_QUEUE = "human"
EXECUTION_QUEUE = "execution"

# Work Item statuses.
SHAPED = "SHAPED"
AUTHORIZED = "AUTHORIZED"
ATTEMPTING = "ATTEMPTING"
CANDIDATE = "CANDIDATE"
TESTED = "TESTED"
REVIEWING = "REVIEWING"
CORRECTING = "CORRECTING"
LEARNER_READY = "LEARNER_READY"
MERGE_READY = "MERGE_READY"
MERGE_CANDIDATE = "MERGE_CANDIDATE"
LANDED = "LANDED"
NEEDS_HUMAN = "NEEDS_HUMAN"
SUPERSEDED = "SUPERSEDED"
CANCELLED = "CANCELLED"

TERMINAL_WORK_STATUSES = {LANDED, NEEDS_HUMAN, SUPERSEDED, CANCELLED}
EXECUTABLE_STATUSES = {
    AUTHORIZED, ATTEMPTING, CANDIDATE, TESTED, CORRECTING, REVIEWING,
}

# Attempt statuses.
STARTED = "STARTED"
REVIEWED = "REVIEWED"
LEARNED = "LEARNED"
BLOCKED = "BLOCKED"

# Landing modes.
NORMAL = "NORMAL"

REQUIRED_REVIEW_TYPES = (
    "behavior",
    "architecture",
    "tests",
    "documentation",
    "security",
)

ALLOWED_PROPOSAL_KINDS = ("expertise", "observation")
FORBIDDEN_PROPOSAL_KINDS = ("policy", "authority", "credential", "activation",
                            "behavior")

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Review finding severities.
SEVERITY_BLOCKING = "blocking"
SEVERITY_MINOR = "minor"
SEVERITY_OUT_OF_SCOPE = "out-of-scope"
FINDING_SEVERITIES = (SEVERITY_BLOCKING, SEVERITY_MINOR, SEVERITY_OUT_OF_SCOPE)
BLOCKING_SEVERITIES = {SEVERITY_BLOCKING}


class FactoryLoopError(Exception):
    """Base error for the factory evidence loop."""


class AuthorityError(FactoryLoopError):
    """Expired, mismatched or missing authority binding."""


class ImmutabilityError(FactoryLoopError):
    """Attempt to mutate an immutable artifact."""


class GateError(FactoryLoopError):
    """A required gate has not passed."""


class SeparationOfDutiesError(FactoryLoopError):
    """An actor crossed a separation-of-duties boundary."""


class NotFoundError(FactoryLoopError):
    """Referenced entity does not exist."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _digest(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Artifact):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, set):
        return sorted(_jsonable(v) for v in value)
    return value


def _artifact_dict(obj: Artifact) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in fields(obj):
        value = getattr(obj, f.name)
        if isinstance(value, tuple):
            value = list(value)
        out[f.name] = value
    return out


def artifact_digest(obj: Artifact) -> str:
    data = {k: v for k, v in _artifact_dict(obj).items()
            if k != "content_digest"}
    return _digest(data)


def _rebuild(cls: type, data: Mapping[str, Any]):
    """Reconstruct a frozen artifact from a projection dict, ignoring any
    derived/annotation keys that are not part of the contract."""
    valid = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in valid})


def _validate_sha(value: str | None, field_name: str, required: bool = True) -> str:
    if value is None or value == "":
        if required:
            raise ValueError(f"{field_name}: SHA-1 (40 hex) required")
        return ""
    if not _SHA_RE.match(str(value)):
        raise ValueError(f"{field_name}: must be a 40-hex SHA-1")
    return str(value)


@dataclass(frozen=True)
class Artifact:
    """Base for every consequential, digest-bound contract."""

    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _artifact_dict(self)

    def digest(self) -> str:
        return artifact_digest(self)

    def bind(self):
        return replace(self, content_digest=self.digest())


# ---------------------------------------------------------------------------
# Contracts (ObservationV1 ... PostMergeObservationV1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObservationV1(Artifact):
    observation_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    candidate_sha: str = ""
    actor: str = ""
    observed_at: str = ""
    severity: str = "info"
    classification: str = "observation"
    summary: str = ""
    evidence: str = ""
    content_digest: str = ""


@dataclass(frozen=True)
class BriefV1(Artifact):
    brief_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    actor: str = ""
    created_at: str = ""
    objective: str = ""
    acceptance_criteria: tuple[str, ...] = ()
    content_digest: str = ""


@dataclass(frozen=True)
class BehaviorSpecV1(Artifact):
    spec_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    actor: str = ""
    created_at: str = ""
    behavior_rules: tuple[str, ...] = ()
    content_digest: str = ""


@dataclass(frozen=True)
class TechnicalApproachV1(Artifact):
    approach_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    actor: str = ""
    created_at: str = ""
    approach: str = ""
    content_digest: str = ""


@dataclass(frozen=True)
class ImplementationPlanV1(Artifact):
    plan_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    actor: str = ""
    created_at: str = ""
    steps: tuple[str, ...] = ()
    content_digest: str = ""


@dataclass(frozen=True)
class AuthorityEnvelopeV1(Artifact):
    envelope_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    actor: str = ""
    issued_at: str = ""
    expires_at: str = ""
    authority_basis: str = ""
    scope: tuple[str, ...] = ()
    status: str = "valid"
    mode: str = NORMAL
    content_digest: str = ""


@dataclass(frozen=True)
class WorkItemV1(Artifact):
    work_item_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    actor: str = ""
    created_at: str = ""
    status: str = SHAPED
    version: int = 1
    supersedes: str = ""
    queue: str = EXECUTION_QUEUE
    objective: str = ""
    source_observation_id: str = ""
    brief_digest: str = ""
    behavior_digest: str = ""
    approach_digest: str = ""
    plan_digest: str = ""
    authority_digest: str = ""
    correction_round: int = 0
    content_digest: str = ""


@dataclass(frozen=True)
class AttemptV1(Artifact):
    attempt_id: str = ""
    work_item_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    candidate_sha: str = ""
    actor: str = ""
    worktree_id: str = ""
    started_at: str = ""
    status: str = STARTED
    correction_round: int = 0
    authority_digest: str = ""
    content_digest: str = ""


@dataclass(frozen=True)
class TesterEvidenceV1(Artifact):
    evidence_id: str = ""
    attempt_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    candidate_sha: str = ""
    actor: str = ""
    started_at: str = ""
    ended_at: str = ""
    duration: float = 0.0
    exit_code: int = 0
    command: str = ""
    working_directory: str = ""
    env_profile_digest: str = ""
    stdout_digest: str = ""
    stderr_digest: str = ""
    artifact_ref: str = ""
    test_counts: int = 0
    test_failures: int = 0
    status: str = "passed"
    content_digest: str = ""


@dataclass(frozen=True)
class ReviewFindingV1(Artifact):
    finding_id: str = ""
    report_id: str = ""
    run_id: str = ""
    repository: str = ""
    candidate_sha: str = ""
    actor: str = ""
    review_type: str = ""
    severity: str = SEVERITY_MINOR
    status: str = "open"
    evidence: str = ""
    file: str = ""
    line: str = ""
    requires_human: bool = False
    content_digest: str = ""


@dataclass(frozen=True)
class ReviewReportV1(Artifact):
    report_id: str = ""
    attempt_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    candidate_sha: str = ""
    actor: str = ""
    review_type: str = ""
    result: str = PASS
    started_at: str = ""
    ended_at: str = ""
    findings: tuple[dict[str, Any], ...] = ()
    evidence: str = ""
    content_digest: str = ""


@dataclass(frozen=True)
class LearnerHandoffV1(Artifact):
    handoff_id: str = ""
    attempt_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    candidate_sha: str = ""
    actor: str = ""
    created_at: str = ""
    proposals: tuple[dict[str, Any], ...] = ()
    observations: tuple[dict[str, Any], ...] = ()
    gates_passed: tuple[str, ...] = ()
    proposal_digest: str = ""
    content_digest: str = ""


@dataclass(frozen=True)
class MergeCandidateV1(Artifact):
    candidate_id: str = ""
    attempt_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    candidate_sha: str = ""
    actor: str = ""
    created_at: str = ""
    status: str = "PENDING"
    evidence_digests: tuple[str, ...] = ()
    review_digests: tuple[str, ...] = ()
    learner_digest: str = ""
    content_digest: str = ""


@dataclass(frozen=True)
class PostMergeObservationV1(Artifact):
    observation_id: str = ""
    run_id: str = ""
    repository: str = ""
    base_sha: str = ""
    candidate_sha: str = ""
    actor: str = ""
    observed_at: str = ""
    severity: str = "info"
    summary: str = ""
    evidence: str = ""
    content_digest: str = ""


# ---------------------------------------------------------------------------
# Event chain (append-only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Event:
    event_type: str
    entity_id: str
    payload: dict[str, Any]
    occurred_at: str
    previous_hash: str | None
    event_hash: str = ""

    @property
    def dedup_key(self) -> str:
        return _digest({
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "payload": _jsonable(self.payload),
        })

    def compute_hash(self) -> str:
        return _digest({
            "event_type": self.event_type,
            "entity_id": self.entity_id,
            "payload": _jsonable(self.payload),
            "occurred_at": self.occurred_at,
            "previous_hash": self.previous_hash,
        })


class EventStore:
    """Append-only, deduplicated event history."""

    def append(self, event: Event) -> bool:
        raise NotImplementedError

    def events(self) -> list[Event]:
        raise NotImplementedError

    def last_hash(self) -> str | None:
        raise NotImplementedError


class MemoryEventStore(EventStore):
    def __init__(self, events: Iterable[Event] | None = None) -> None:
        self._events: list[Event] = []
        self._keys: set[str] = set()
        for event in events or ():
            self._events.append(event)
            self._keys.add(event.dedup_key)

    def append(self, event: Event) -> bool:
        if event.dedup_key in self._keys:
            return False
        self._keys.add(event.dedup_key)
        self._events.append(event)
        return True

    def events(self) -> list[Event]:
        return list(self._events)

    def last_hash(self) -> str | None:
        return self._events[-1].event_hash if self._events else None


class SqliteEventStore(EventStore):
    """SQLite-backed append-only event history (extend existing .valo DBs)."""

    DEFAULT_DB = str(Path.home() / ".valo" / "factory_evidence_loop.db")

    def __init__(self, db_path: str | None = None) -> None:
        self._path = db_path or self.DEFAULT_DB
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS factory_loop_events ("
            " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            " dedup_key TEXT NOT NULL UNIQUE,"
            " event_type TEXT NOT NULL,"
            " entity_id TEXT NOT NULL,"
            " payload TEXT NOT NULL,"
            " occurred_at TEXT NOT NULL,"
            " previous_hash TEXT,"
            " event_hash TEXT NOT NULL)"
        )
        self._conn.commit()

    def append(self, event: Event) -> bool:
        try:
            self._conn.execute(
                "INSERT INTO factory_loop_events "
                "(dedup_key,event_type,entity_id,payload,occurred_at,"
                " previous_hash,event_hash) VALUES (?,?,?,?,?,?,?)",
                (event.dedup_key, event.event_type, event.entity_id,
                 json.dumps(_jsonable(event.payload), sort_keys=True),
                 event.occurred_at, event.previous_hash, event.event_hash),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def events(self) -> list[Event]:
        rows = self._conn.execute(
            "SELECT event_type,entity_id,payload,occurred_at,previous_hash,"
            " event_hash FROM factory_loop_events ORDER BY seq"
        ).fetchall()
        return [
            Event(
                event_type=row[0],
                entity_id=row[1],
                payload=json.loads(row[2]),
                occurred_at=row[3],
                previous_hash=row[4],
                event_hash=row[5],
            )
            for row in rows
        ]

    def last_hash(self) -> str | None:
        row = self._conn.execute(
            "SELECT event_hash FROM factory_loop_events ORDER BY seq DESC "
            "LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def close(self) -> None:
        self._conn.close()


# ---------------------------------------------------------------------------
# Projection (rebuilt from append-only history)
# ---------------------------------------------------------------------------

class Projection:
    """Replayable projections. Identical history -> identical projections."""

    def __init__(self) -> None:
        self.observations: dict[str, dict[str, Any]] = {}
        self.observation_order: list[str] = []
        self.shape_artifacts: dict[str, dict[str, Any]] = {}
        self.work_items: dict[str, dict[str, Any]] = {}
        self.work_item_order: list[str] = []
        self.attempts: dict[str, dict[str, Any]] = {}
        self.tester_evidence: dict[str, dict[str, Any]] = {}
        self.review_reports: dict[str, dict[str, Any]] = {}
        self.review_findings: dict[str, dict[str, Any]] = {}
        self.learner_handoffs: dict[str, dict[str, Any]] = {}
        self.merge_candidates: dict[str, dict[str, Any]] = {}
        self.post_merge_observations: dict[str, dict[str, Any]] = {}
        self.landings: list[dict[str, Any]] = []

    def rebuild(self, events: Iterable[Event]) -> None:
        self.__init__()
        for event in events:
            self.apply(event)

    def apply(self, event: Event) -> None:
        # Projections must never share or mutate event payload objects: the
        # event history is append-only and its payloads stay byte-stable so
        # identical history rebuilds identical state and digests.
        payload = copy.deepcopy(event.payload)

        if event.event_type == "observation.recorded":
            observation = payload["observation"]
            self.observations[observation["observation_id"]] = observation
            self.observation_order.append(observation["observation_id"])
        elif event.event_type == "shape.recorded":
            id_fields = {
                "brief": "brief_id",
                "behavior": "spec_id",
                "approach": "approach_id",
                "plan": "plan_id",
                "authority": "envelope_id",
            }
            for key, id_field in id_fields.items():
                artifact = payload[key]
                self.shape_artifacts[artifact[id_field]] = artifact
            work_item = payload["work_item"]
            self.work_items[work_item["work_item_id"]] = work_item
            self.work_item_order.append(work_item["work_item_id"])
        elif event.event_type == "work_item.authorized":
            work_item = payload["work_item"]
            self.work_items[work_item["work_item_id"]] = work_item
        elif event.event_type == "work_item.superseded":
            self.work_items[payload["superseded_id"]]["status"] = SUPERSEDED
            work_item = payload["work_item"]
            self.work_items[work_item["work_item_id"]] = work_item
            self.work_item_order.append(work_item["work_item_id"])
        elif event.event_type == "work_item.status_changed":
            work_item = payload["work_item"]
            self.work_items[work_item["work_item_id"]] = work_item
        elif event.event_type == "work_item.routed_human":
            work_item = payload["work_item"]
            work_item["human_attention_reason"] = payload.get("reason", "")
            self.work_items[work_item["work_item_id"]] = work_item
        elif event.event_type == "attempt.started":
            attempt = payload["attempt"]
            self.attempts[attempt["attempt_id"]] = attempt
            work_item = self.work_items[attempt["work_item_id"]]
            work_item["status"] = ATTEMPTING
        elif event.event_type == "attempt.candidate_submitted":
            attempt = payload["attempt"]
            self.attempts[attempt["attempt_id"]] = attempt
            work_item = self.work_items[attempt["work_item_id"]]
            work_item["status"] = CANDIDATE
        elif event.event_type == "attempt.status_changed":
            attempt = payload["attempt"]
            self.attempts[attempt["attempt_id"]] = attempt
            work_item = self.work_items[attempt["work_item_id"]]
            work_item["status"] = payload["work_item_status"]
            work_item["correction_round"] = attempt["correction_round"]
        elif event.event_type == "tester.evidence_recorded":
            evidence = payload["evidence"]
            self.tester_evidence[evidence["evidence_id"]] = evidence
            attempt = self.attempts[evidence["attempt_id"]]
            attempt["status"] = TESTED
            self.work_items[attempt["work_item_id"]]["status"] = TESTED
        elif event.event_type == "review.reported":
            report = payload["report"]
            self.review_reports[report["report_id"]] = report
            for finding in payload["findings"]:
                self.review_findings[finding["finding_id"]] = finding
            attempt = self.attempts[report["attempt_id"]]
            attempt["status"] = REVIEWED
            work_item = self.work_items[attempt["work_item_id"]]
            if work_item["status"] == TESTED:
                work_item["status"] = REVIEWING
        elif event.event_type == "review.decision":
            decision = payload["decision"]
            attempt = self.attempts[decision["attempt_id"]]
            attempt["status"] = decision["attempt_status"]
            attempt["last_decision"] = decision["result"]
            work_item = self.work_items[decision["work_item_id"]]
            work_item["status"] = decision["work_item_status"]
            work_item["correction_round"] = decision["correction_round"]
        elif event.event_type == "learner.handoff_recorded":
            handoff = payload["handoff"]
            self.learner_handoffs[handoff["handoff_id"]] = handoff
            attempt = self.attempts[handoff["attempt_id"]]
            attempt["status"] = LEARNED
            self.work_items[attempt["work_item_id"]]["status"] = MERGE_READY
        elif event.event_type == "merge_candidate.created":
            candidate = payload["candidate"]
            self.merge_candidates[candidate["candidate_id"]] = candidate
            attempt = self.attempts[candidate["attempt_id"]]
            self.work_items[attempt["work_item_id"]]["status"] = MERGE_CANDIDATE
        elif event.event_type == "merge_candidate.invalidated":
            candidate = payload["candidate"]
            candidate["invalidation_reason"] = payload.get("reason", "")
            self.merge_candidates[candidate["candidate_id"]] = candidate
        elif event.event_type == "landing.attempted":
            self.landings.append(payload)
        elif event.event_type == "merge_candidate.landed":
            candidate = payload["candidate"]
            self.merge_candidates[candidate["candidate_id"]] = candidate
            attempt = self.attempts[candidate["attempt_id"]]
            attempt["status"] = LANDED
            self.work_items[attempt["work_item_id"]]["status"] = LANDED
        elif event.event_type == "post_merge.observed":
            observation = payload["post_merge"]
            self.post_merge_observations[
                observation["observation_id"]
            ] = observation

    def execution_queue(self) -> list[str]:
        return [
            work_item_id for work_item_id in self.work_item_order
            if (self.work_items[work_item_id]["queue"] == EXECUTION_QUEUE
                and self.work_items[work_item_id]["status"]
                in EXECUTABLE_STATUSES)
        ]

    def human_queue(self) -> list[str]:
        return [
            work_item_id for work_item_id in self.work_item_order
            if (self.work_items[work_item_id]["queue"] == HUMAN_QUEUE
                and self.work_items[work_item_id]["status"]
                in EXECUTABLE_STATUSES | {NEEDS_HUMAN})
        ]


# ---------------------------------------------------------------------------
# Loop configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LoopConfig:
    max_correction_rounds: int = 3
    mode: str = NORMAL
    required_review_types: tuple[str, ...] = REQUIRED_REVIEW_TYPES
    now: Any = utc_now


@dataclass(frozen=True)
class ReviewResolution:
    result: str
    work_item_id: str
    attempt_id: str
    correction_round: int
    needs_human: bool = False
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class LandingResult:
    landed: bool
    candidate_id: str
    checks: dict[str, bool]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ShapingResult:
    work_item: WorkItemV1
    brief: BriefV1
    behavior: BehaviorSpecV1
    approach: TechnicalApproachV1
    plan: ImplementationPlanV1
    authority: AuthorityEnvelopeV1


# ---------------------------------------------------------------------------
# FactoryEvidenceLoop
# ---------------------------------------------------------------------------

class FactoryEvidenceLoop:
    """The governed self-improving evidence loop."""

    def __init__(self, store: EventStore | None = None,
                 config: LoopConfig | None = None) -> None:
        self._store = store or MemoryEventStore()
        self._config = config or LoopConfig()
        self._projection = Projection()
        self._projection.rebuild(self._store.events())

    # -- public accessors ---------------------------------------------------

    @property
    def store(self) -> EventStore:
        return self._store

    @property
    def config(self) -> LoopConfig:
        return self._config

    @property
    def projection(self) -> Projection:
        return self._projection

    def events(self) -> list[Event]:
        return self._store.events()

    def receipt_chain(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for event in self._store.events():
            assert event.event_hash == event.compute_hash(), "broken chain"
            out.append({
                "seq": len(out) + 1,
                "event_type": event.event_type,
                "entity_id": event.entity_id,
                "occurred_at": event.occurred_at,
                "previous_hash": event.previous_hash,
                "event_hash": event.event_hash,
            })
        return out

    def rebuild(self) -> None:
        self._projection.rebuild(self._store.events())

    # -- event plumbing -----------------------------------------------------

    def _record(self, event_type: str, entity_id: str,
                payload: Mapping[str, Any]) -> bool:
        event = Event(
            event_type=event_type,
            entity_id=entity_id,
            payload=_jsonable(dict(payload)),
            occurred_at=self._config.now(),
            previous_hash=self._store.last_hash(),
        )
        event = replace(event, event_hash=event.compute_hash())
        newly_applied = self._store.append(event)
        if newly_applied:
            self._projection.rebuild(self._store.events())
        return newly_applied

    # -- 1. Observations (append-only evidence) -----------------------------

    def observe(self, *, repository: str, run_id: str, base_sha: str = "",
                candidate_sha: str = "", actor: str = "", summary: str = "",
                evidence: str = "", severity: str = "info",
                classification: str = "observation",
                observation_id: str | None = None) -> ObservationV1:
        _validate_sha(base_sha, "base_sha", required=False)
        _validate_sha(candidate_sha, "candidate_sha", required=False)
        if not repository or not run_id or not actor:
            raise ValueError("repository, run_id and actor are required")
        observation = ObservationV1(
            observation_id=observation_id or new_id("obs"),
            run_id=run_id,
            repository=repository,
            base_sha=base_sha,
            candidate_sha=candidate_sha,
            actor=actor,
            observed_at=self._config.now(),
            severity=severity,
            classification=classification,
            summary=summary,
            evidence=evidence,
        ).bind()
        self._record(
            "observation.recorded",
            observation.observation_id,
            {"observation": observation.to_dict()},
        )
        return observation

    def _apply_observation(self, observation: ObservationV1) -> None:
        """Minor/out-of-scope review findings become Observations only."""
        self._record(
            "observation.recorded",
            observation.observation_id,
            {"observation": observation.to_dict()},
        )

    # -- 2. Shaping ---------------------------------------------------------

    def shape(self, *, repository: str, run_id: str, base_sha: str,
              actor: str, source_observation_id: str = "", objective: str = "",
              acceptance_criteria: Iterable[str] = (),
              behavior_rules: Iterable[str] = (),
              approach: str = "", steps: Iterable[str] = (),
              authority_basis: str = "", authority_scope: Iterable[str] = (),
              expires_at: str = "", mode: str = NORMAL,
              queue: str = EXECUTION_QUEUE,
              work_item_id: str | None = None) -> ShapingResult:
        _validate_sha(base_sha, "base_sha")
        if queue not in (HUMAN_QUEUE, EXECUTION_QUEUE):
            raise ValueError(f"invalid queue: {queue}")
        work_item_id = work_item_id or new_id("wi")
        now = self._config.now()
        brief = BriefV1(
            brief_id=f"{work_item_id}-brief", run_id=run_id,
            repository=repository, base_sha=base_sha, actor=actor,
            created_at=now, objective=objective,
            acceptance_criteria=tuple(acceptance_criteria),
        ).bind()
        behavior = BehaviorSpecV1(
            spec_id=f"{work_item_id}-spec", run_id=run_id,
            repository=repository, base_sha=base_sha, actor=actor,
            created_at=now, behavior_rules=tuple(behavior_rules),
        ).bind()
        approach_artifact = TechnicalApproachV1(
            approach_id=f"{work_item_id}-approach", run_id=run_id,
            repository=repository, base_sha=base_sha, actor=actor,
            created_at=now, approach=approach,
        ).bind()
        plan = ImplementationPlanV1(
            plan_id=f"{work_item_id}-plan", run_id=run_id,
            repository=repository, base_sha=base_sha, actor=actor,
            created_at=now, steps=tuple(steps),
        ).bind()
        authority = AuthorityEnvelopeV1(
            envelope_id=f"{work_item_id}-auth", run_id=run_id,
            repository=repository, base_sha=base_sha, actor=actor,
            issued_at=now, expires_at=expires_at,
            authority_basis=authority_basis, scope=tuple(authority_scope),
            mode=mode,
        ).bind()
        work_item = WorkItemV1(
            work_item_id=work_item_id,
            run_id=run_id, repository=repository, base_sha=base_sha,
            actor=actor, created_at=now, status=SHAPED, queue=queue,
            objective=objective, source_observation_id=source_observation_id,
            brief_digest=brief.digest(), behavior_digest=behavior.digest(),
            approach_digest=approach_artifact.digest(),
            plan_digest=plan.digest(), authority_digest=authority.digest(),
        ).bind()
        self._record(
            "shape.recorded",
            work_item.work_item_id,
            {
                "brief": brief.to_dict(),
                "behavior": behavior.to_dict(),
                "approach": approach_artifact.to_dict(),
                "plan": plan.to_dict(),
                "authority": authority.to_dict(),
                "work_item": work_item.to_dict(),
            },
        )
        return ShapingResult(
            work_item=work_item, brief=brief, behavior=behavior,
            approach=approach_artifact, plan=plan, authority=authority,
        )

    # -- 3. Authorization (immutable Work Item) -----------------------------

    def authorize_work_item(self, *, work_item_id: str,
                            actor: str) -> WorkItemV1:
        work_item = self._require_work_item(work_item_id)
        if work_item["status"] != SHAPED:
            raise ImmutabilityError(
                f"work item {work_item_id} already authorized/active "
                f"(status={work_item['status']})")
        updated = dict(work_item)
        updated["status"] = AUTHORIZED
        updated["actor"] = actor
        authorized = _rebuild(WorkItemV1, updated).bind()
        self._record(
            "work_item.authorized",
            authorized.work_item_id,
            {"work_item": authorized.to_dict()},
        )
        return authorized

    def supersede_work_item(self, *, work_item_id: str, actor: str,
                            **changes: Any) -> WorkItemV1:
        """Revision creates a superseding version; the old one stays immutable."""
        work_item = self._require_work_item(work_item_id)
        if work_item["status"] in TERMINAL_WORK_STATUSES:
            raise ImmutabilityError(
                f"terminal work item {work_item_id} cannot be superseded")
        base = dict(work_item)
        base.update(changes)
        base["work_item_id"] = new_id("wi")
        base["version"] = int(work_item["version"]) + 1
        base["supersedes"] = work_item_id
        base["status"] = AUTHORIZED
        base["actor"] = actor
        base["created_at"] = self._config.now()
        base.pop("content_digest", None)
        superseding = _rebuild(WorkItemV1, base).bind()
        self._record(
            "work_item.superseded",
            superseding.work_item_id,
            {"superseded_id": work_item_id,
             "work_item": superseding.to_dict()},
        )
        return superseding

    def route_to_human(self, *, work_item_id: str, reason: str,
                       actor: str) -> WorkItemV1:
        work_item = self._require_work_item(work_item_id)
        if work_item["status"] in TERMINAL_WORK_STATUSES:
            raise ImmutabilityError(
                f"terminal work item {work_item_id} cannot be routed")
        updated = dict(work_item)
        updated["status"] = NEEDS_HUMAN
        updated["queue"] = HUMAN_QUEUE
        updated["actor"] = actor
        routed = _rebuild(WorkItemV1, updated).bind()
        self._record(
            "work_item.routed_human",
            routed.work_item_id,
            {"work_item": routed.to_dict(), "reason": reason},
        )
        return routed

    # -- 4. Attempts (isolated worktree + exact base SHA) -------------------

    def start_attempt(self, *, work_item_id: str, actor: str,
                      worktree_id: str, base_sha: str,
                      authority_envelope_id: str, attempt_id: str | None = None,
                      ) -> AttemptV1:
        _validate_sha(base_sha, "base_sha")
        work_item = self._require_work_item(work_item_id)
        if work_item["status"] not in (AUTHORIZED, CORRECTING):
            raise GateError(
                f"work item {work_item_id} not executable "
                f"(status={work_item['status']})")
        if work_item["base_sha"] != base_sha:
            raise AuthorityError(
                f"attempt base SHA {base_sha} does not match work item base "
                f"SHA {work_item['base_sha']}")
        envelope = self._require_envelope(authority_envelope_id)
        self._check_envelope(envelope, work_item)
        attempt = AttemptV1(
            attempt_id=attempt_id or new_id("att"),
            work_item_id=work_item_id,
            run_id=work_item["run_id"],
            repository=work_item["repository"],
            base_sha=base_sha,
            actor=actor,
            worktree_id=worktree_id,
            started_at=self._config.now(),
            status=STARTED,
            correction_round=int(work_item["correction_round"]),
            authority_digest=envelope["content_digest"],
        ).bind()
        self._record(
            "attempt.started",
            attempt.attempt_id,
            {"attempt": attempt.to_dict()},
        )
        return attempt

    def _check_envelope(self, envelope: dict[str, Any],
                        work_item: dict[str, Any]) -> None:
        if envelope.get("status") != "valid":
            raise AuthorityError("authority envelope is not valid")
        if envelope.get("mode") not in (NORMAL, self._config.mode, ""):
            raise AuthorityError(
                f"envelope mode {envelope.get('mode')} disallows execution")
        if envelope.get("repository") != work_item.get("repository"):
            raise AuthorityError("authority envelope repository mismatch")
        if envelope.get("base_sha") != work_item.get("base_sha"):
            raise AuthorityError("authority envelope base SHA mismatch")
        expires_at = envelope.get("expires_at") or ""
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at)
            except ValueError:
                raise AuthorityError("authority envelope has invalid expiry")
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc):
                raise AuthorityError("authority envelope has expired")

    def submit_candidate(self, *, attempt_id: str, actor: str,
                         candidate_sha: str) -> AttemptV1:
        _validate_sha(candidate_sha, "candidate_sha")
        attempt = self._require_attempt(attempt_id)
        if attempt["actor"] != actor:
            raise SeparationOfDutiesError(
                f"attempt {attempt_id} is written by {attempt['actor']}, "
                f"not {actor}")
        if attempt["status"] not in (STARTED, CORRECTING, BLOCKED):
            raise GateError(
                f"attempt {attempt_id} cannot accept a candidate "
                f"(status={attempt['status']})")
        updated = dict(attempt)
        updated["candidate_sha"] = candidate_sha
        updated["status"] = CANDIDATE
        submitted = _rebuild(AttemptV1, updated).bind()
        self._record(
            "attempt.candidate_submitted",
            submitted.attempt_id,
            {"attempt": submitted.to_dict()},
        )
        return submitted

    # -- 5. Deterministic Tester evidence -----------------------------------

    def record_tester_evidence(self, *, attempt_id: str, actor: str,
                               candidate_sha: str, command: str,
                               working_directory: str, exit_code: int,
                               started_at: str, ended_at: str,
                               env_profile_digest: str = "",
                               stdout_digest: str = "",
                               stderr_digest: str = "",
                               artifact_ref: str = "",
                               test_counts: int = 0,
                               test_failures: int = 0,
                               status: str = "passed",
                               evidence_id: str | None = None,
                               ) -> TesterEvidenceV1:
        _validate_sha(candidate_sha, "candidate_sha")
        attempt = self._require_attempt(attempt_id)
        if attempt["actor"] == actor:
            raise SeparationOfDutiesError(
                "Writer cannot produce accepted Tester evidence (no "
                "self-attestation)")
        if not attempt.get("candidate_sha"):
            raise GateError(
                f"attempt {attempt_id} has no candidate yet")
        if attempt["candidate_sha"] != candidate_sha:
            raise GateError(
                f"Tester evidence bound to {candidate_sha} does not match "
                f"attempt candidate {attempt['candidate_sha']}")
        if not command or not working_directory:
            raise ValueError("command and working_directory required")
        evidence = TesterEvidenceV1(
            evidence_id=evidence_id or new_id("te"),
            attempt_id=attempt_id,
            run_id=attempt["run_id"],
            repository=attempt["repository"],
            base_sha=attempt["base_sha"],
            candidate_sha=candidate_sha,
            actor=actor,
            started_at=started_at,
            ended_at=ended_at,
            duration=_duration_seconds(started_at, ended_at),
            exit_code=int(exit_code),
            command=command,
            working_directory=working_directory,
            env_profile_digest=env_profile_digest,
            stdout_digest=stdout_digest,
            stderr_digest=stderr_digest,
            artifact_ref=artifact_ref,
            test_counts=int(test_counts),
            test_failures=int(test_failures),
            status=status,
        ).bind()
        self._record(
            "tester.evidence_recorded",
            evidence.evidence_id,
            {"evidence": evidence.to_dict()},
        )
        return evidence

    # -- 6. Independent read-only Reviewers ---------------------------------

    def review(self, *, attempt_id: str, actor: str, review_type: str,
               result: str, findings: Iterable[Mapping[str, Any]] = (),
               evidence: str = "", report_id: str | None = None,
               ) -> ReviewReportV1:
        if result not in REVIEW_RESULTS:
            raise ValueError(f"invalid review result: {result}")
        attempt = self._require_attempt(attempt_id)
        if attempt["actor"] == actor:
            raise SeparationOfDutiesError(
                "Writer cannot review its own candidate")
        evidence_rows = [
            ev for ev in self._projection.tester_evidence.values()
            if ev["attempt_id"] == attempt_id
            and ev["candidate_sha"] == attempt.get("candidate_sha")
        ]
        if not evidence_rows:
            raise GateError(
                f"review requires Tester evidence for attempt {attempt_id}")
        report_id = report_id or new_id("rr")
        report = ReviewReportV1(
            report_id=report_id,
            attempt_id=attempt_id,
            run_id=attempt["run_id"],
            repository=attempt["repository"],
            base_sha=attempt["base_sha"],
            candidate_sha=attempt.get("candidate_sha") or "",
            actor=actor,
            review_type=review_type,
            result=result,
            started_at=self._config.now(),
            ended_at=self._config.now(),
        )
        finding_artifacts: list[ReviewFindingV1] = []
        for index, raw in enumerate(findings):
            finding_artifact = ReviewFindingV1(
                finding_id=f"{report_id}-f{index}",
                report_id=report.report_id,
                run_id=attempt["run_id"],
                repository=attempt["repository"],
                candidate_sha=attempt.get("candidate_sha") or "",
                actor=actor,
                review_type=review_type,
                severity=str(raw.get("severity", SEVERITY_MINOR)),
                status=str(raw.get("status", "open")),
                evidence=str(raw.get("evidence", "")),
                file=str(raw.get("file", "")),
                line=str(raw.get("line", "")),
                requires_human=bool(raw.get("requires_human", False)),
            ).bind()
            finding_artifacts.append(finding_artifact)
        report = replace(
            report,
            findings=tuple(f.digest() for f in finding_artifacts),
            content_digest="",
        )
        report = report.bind()
        if evidence:
            report = replace(
                report,
                evidence=evidence,
                content_digest="",
            )
        self._record(
            "review.reported",
            report.report_id,
            {
                "report": report.to_dict(),
                "findings": [f.to_dict() for f in finding_artifacts],
            },
        )
        return report

    def resolve_review(self, *, attempt_id: str,
                       actor: str) -> ReviewResolution:
        attempt = self._require_attempt(attempt_id)
        if attempt["actor"] == actor:
            raise SeparationOfDutiesError(
                "Writer cannot adjudicate its own review (no self-attestation)")
        reports = [
            report for report in self._projection.review_reports.values()
            if report["attempt_id"] == attempt_id
        ]
        present_types = {report["review_type"] for report in reports}
        missing = [t for t in self._config.required_review_types
                   if t not in present_types]
        work_item = self._require_work_item(attempt["work_item_id"])

        blocking_findings: list[ReviewFindingV1] = []
        minor_observations: list[ObservationV1] = []
        for finding in self._projection.review_findings.values():
            if finding["report_id"] not in {r["report_id"]
                                            for r in reports}:
                continue
            if finding["severity"] in BLOCKING_SEVERITIES:
                blocking_findings.append(ReviewFindingV1(**finding))
            elif finding["severity"] in (SEVERITY_MINOR,
                                         SEVERITY_OUT_OF_SCOPE):
                minor_observations.append(ObservationV1(
                    observation_id=new_id("obs"),
                    run_id=attempt["run_id"],
                    repository=attempt["repository"],
                    base_sha=attempt["base_sha"],
                    candidate_sha=attempt.get("candidate_sha") or "",
                    actor=actor,
                    observed_at=self._config.now(),
                    severity="info",
                    classification="review-minor-finding",
                    summary=f"minor/out-of-scope review finding from "
                            f"{finding['review_type']} review",
                    evidence=finding["evidence"],
                ).bind())

        if any(r["result"] == FAIL for r in reports):
            round_number = int(work_item["correction_round"]) + 1
            needs_human = round_number >= self._config.max_correction_rounds
            reasons = (
                *[f.evidence for f in blocking_findings],
            ) if blocking_findings else ("review FAIL",)
            self._record(
                "review.decision",
                work_item["work_item_id"],
                {
                    "decision": {
                        "attempt_id": attempt_id,
                        "work_item_id": work_item["work_item_id"],
                        "result": "FAIL",
                        "attempt_status": NEEDS_HUMAN if needs_human
                        else CORRECTING,
                        "work_item_status": NEEDS_HUMAN if needs_human
                        else CORRECTING,
                        "correction_round": round_number,
                    }
                },
            )
            for observation in minor_observations:
                self._apply_observation(observation)
            return ReviewResolution(
                result=FAIL,
                work_item_id=work_item["work_item_id"],
                attempt_id=attempt_id,
                correction_round=round_number,
                needs_human=needs_human,
                reasons=reasons,
            )

        if any(r["result"] == UNCERTAIN for r in reports):
            self._record(
                "review.decision",
                work_item["work_item_id"],
                {
                    "decision": {
                        "attempt_id": attempt_id,
                        "work_item_id": work_item["work_item_id"],
                        "result": "UNCERTAIN",
                        "attempt_status": NEEDS_HUMAN,
                        "work_item_status": NEEDS_HUMAN,
                        "correction_round": int(work_item["correction_round"]),
                    }
                },
            )
            self._record(
                "work_item.routed_human",
                work_item["work_item_id"],
                {"work_item": dict(work_item, status=NEEDS_HUMAN,
                                   queue=HUMAN_QUEUE)},
            )
            return ReviewResolution(
                result=UNCERTAIN,
                work_item_id=work_item["work_item_id"],
                attempt_id=attempt_id,
                correction_round=int(work_item["correction_round"]),
                needs_human=True,
                reasons=("UNCERTAIN review routed to human attention",),
            )

        if missing:
            return ReviewResolution(
                result="PENDING_REVIEW",
                work_item_id=work_item["work_item_id"],
                attempt_id=attempt_id,
                correction_round=int(work_item["correction_round"]),
                reasons=(f"missing required reviews: {','.join(missing)}",),
            )

        self._record(
            "review.decision",
            work_item["work_item_id"],
            {
                "decision": {
                    "attempt_id": attempt_id,
                    "work_item_id": work_item["work_item_id"],
                    "result": "PASS",
                    "attempt_status": REVIEWED,
                    "work_item_status": LEARNER_READY,
                    "correction_round": int(work_item["correction_round"]),
                }
            },
        )
        for observation in minor_observations:
            self._apply_observation(observation)
        return ReviewResolution(
            result=PASS,
            work_item_id=work_item["work_item_id"],
            attempt_id=attempt_id,
            correction_round=int(work_item["correction_round"]),
        )

    # -- 7. Learner handoff (proposals only) --------------------------------

    def run_learner(self, *, attempt_id: str, actor: str,
                    proposals: Iterable[Mapping[str, Any]] = (),
                    observations: Iterable[Mapping[str, Any]] = (),
                    handoff_id: str | None = None) -> LearnerHandoffV1:
        attempt = self._require_attempt(attempt_id)
        if attempt["actor"] == actor:
            raise SeparationOfDutiesError(
                "Writer cannot act as Learner for its own candidate")
        if attempt["status"] not in (REVIEWED, LEARNED):
            raise GateError(
                f"Learner gate not passed for attempt {attempt_id} "
                f"(status={attempt['status']})")
        proposal_list = [_jsonable(dict(p)) for p in proposals]
        for proposal in proposal_list:
            kind = str(proposal.get("kind", "expertise"))
            if kind in FORBIDDEN_PROPOSAL_KINDS:
                raise GateError(
                    f"Learner cannot emit proposal kind {kind!r} "
                    f"(policy/authority/activation never generated here)")
            if kind not in ALLOWED_PROPOSAL_KINDS:
                raise ValueError(f"unknown proposal kind: {kind}")
        gates = [
            "tester_evidence",
            "review_pass",
            "learner_ready",
        ]
        handoff = LearnerHandoffV1(
            handoff_id=handoff_id or new_id("lh"),
            attempt_id=attempt_id,
            run_id=attempt["run_id"],
            repository=attempt["repository"],
            base_sha=attempt["base_sha"],
            candidate_sha=attempt.get("candidate_sha") or "",
            actor=actor,
            created_at=self._config.now(),
            proposals=tuple(proposal_list),
            observations=tuple(_jsonable(dict(o)) for o in observations),
            gates_passed=tuple(gates),
        )
        handoff = replace(
            handoff,
            proposal_digest=_digest({
                "proposals": proposal_list,
                "observations": [_jsonable(dict(o)) for o in observations],
            }),
            content_digest="",
        ).bind()
        self._record(
            "learner.handoff_recorded",
            handoff.handoff_id,
            {"handoff": handoff.to_dict()},
        )
        return handoff

    # -- 8. Immutable Merge Candidate ---------------------------------------

    def create_merge_candidate(self, *, attempt_id: str,
                               actor: str,
                               candidate_id: str | None = None,
                               ) -> MergeCandidateV1:
        attempt = self._require_attempt(attempt_id)
        if attempt["actor"] == actor:
            raise SeparationOfDutiesError(
                "Writer cannot create the Merge Candidate for its own work")
        if not attempt.get("candidate_sha"):
            raise GateError("no candidate SHA to merge")
        evidence = [
            ev for ev in self._projection.tester_evidence.values()
            if ev["attempt_id"] == attempt_id
            and ev["candidate_sha"] == attempt.get("candidate_sha")
        ]
        if not evidence:
            raise GateError("no Tester evidence for candidate")
        reports = [
            report for report in self._projection.review_reports.values()
            if report["attempt_id"] == attempt_id
        ]
        passes = [r for r in reports if r["result"] == PASS]
        if len({r["review_type"] for r in passes}) < len(
                self._config.required_review_types):
            raise GateError("not every required review passed")
        if any(r["result"] in (FAIL, UNCERTAIN) for r in reports):
            raise GateError("review did not pass cleanly")
        handoffs = [
            handoff for handoff in self._projection.learner_handoffs.values()
            if handoff["attempt_id"] == attempt_id
        ]
        if not handoffs:
            raise GateError("Learner gate not passed")
        candidate = MergeCandidateV1(
            candidate_id=candidate_id or new_id("mc"),
            attempt_id=attempt_id,
            run_id=attempt["run_id"],
            repository=attempt["repository"],
            base_sha=attempt["base_sha"],
            candidate_sha=attempt.get("candidate_sha") or "",
            actor=actor,
            created_at=self._config.now(),
            status="PENDING",
            evidence_digests=tuple(ev["content_digest"]
                                   for ev in evidence),
            review_digests=tuple(r["content_digest"] for r in reports),
            learner_digest=handoffs[-1]["content_digest"],
        ).bind()
        self._record(
            "merge_candidate.created",
            candidate.candidate_id,
            {"candidate": candidate.to_dict()},
        )
        return candidate

    # -- 9. Governed landing -------------------------------------------------

    def land(self, *, candidate_id: str, actor: str,
             current_head_sha: str, mode: str = NORMAL,
             claim_active: bool = True, ci_evidence: str = "",
             reht_clearance: str = "", racs_decision: str = "",
             ) -> LandingResult:
        _validate_sha(current_head_sha, "current_head_sha")
        candidate = self._require_candidate(candidate_id)
        if candidate["status"] == LANDED:
            raise ImmutabilityError(
                f"merge candidate {candidate_id} already landed")
        if candidate["status"] == "INVALID":
            raise GateError(
                f"merge candidate {candidate_id} invalidated (no landing)")
        attempt = self._require_attempt(candidate["attempt_id"])
        if attempt["actor"] == actor:
            raise SeparationOfDutiesError(
                "Writer cannot land its own candidate (no self-attestation)")
        checks: dict[str, bool] = {
            "mode_normal": mode == NORMAL,
            "claim_active": claim_active is True,
            "ci_evidence": bool(ci_evidence),
            "reht_clearance": bool(reht_clearance),
            "racs_decision": bool(racs_decision),
            "no_target_drift": current_head_sha == candidate["base_sha"],
            "current_head_matches": current_head_sha == candidate["base_sha"],
        }
        reasons: list[str] = [
            "landing requires NORMAL mode"
            for name, ok in checks.items()
            if not ok and name == "mode_normal"
        ]
        if not checks["claim_active"]:
            reasons.append("landing requires an active claim")
        if not checks["ci_evidence"]:
            reasons.append("landing requires CI evidence")
        if not checks["reht_clearance"]:
            reasons.append("landing requires current REHT clearance")
        if not checks["racs_decision"]:
            reasons.append("landing requires a RACS decision")
        if not checks["no_target_drift"]:
            reasons.append(
                f"target drifted: head {current_head_sha} != base "
                f"{candidate['base_sha']}")
        if not checks["current_head_matches"]:
            reasons.append("current head SHA does not match base")

        ok = all(checks.values())
        self._record(
            "landing.attempted",
            candidate_id,
            {
                "candidate_id": candidate_id,
                "actor": actor,
                "mode": mode,
                "checks": checks,
                "landed": ok,
                "reasons": tuple(reasons),
                "current_head_sha": current_head_sha,
            },
        )
        if not ok:
            if not checks["no_target_drift"]:
                self._invalidate_candidate(candidate_id,
                                           "target/head drift")
            return LandingResult(
                landed=False, candidate_id=candidate_id, checks=checks,
                reasons=tuple(reasons),
            )

        updated = dict(candidate)
        updated["status"] = LANDED
        landed = _rebuild(MergeCandidateV1, updated).bind()
        self._record(
            "merge_candidate.landed",
            landed.candidate_id,
            {"candidate": landed.to_dict()},
        )
        return LandingResult(
            landed=True, candidate_id=candidate_id, checks=checks,
            reasons=(),
        )

    def _invalidate_candidate(self, candidate_id: str, reason: str) -> None:
        candidate = self._require_candidate(candidate_id)
        if candidate["status"] in ("LANDED", "INVALID"):
            return
        updated = dict(candidate)
        updated["status"] = "INVALID"
        invalidated = _rebuild(MergeCandidateV1, updated).bind()
        self._record(
            "merge_candidate.invalidated",
            invalidated.candidate_id,
            {"candidate": invalidated.to_dict(), "reason": reason},
        )

    # -- 10. Post-merge Observations ----------------------------------------

    def post_merge_observe(self, *, repository: str, run_id: str,
                           base_sha: str, candidate_sha: str, actor: str,
                           summary: str = "", evidence: str = "",
                           severity: str = "info",
                           observation_id: str | None = None,
                           ) -> PostMergeObservationV1:
        _validate_sha(base_sha, "base_sha")
        _validate_sha(candidate_sha, "candidate_sha")
        observation = PostMergeObservationV1(
            observation_id=observation_id or new_id("pmo"),
            run_id=run_id,
            repository=repository,
            base_sha=base_sha,
            candidate_sha=candidate_sha,
            actor=actor,
            observed_at=self._config.now(),
            severity=severity,
            summary=summary,
            evidence=evidence,
        ).bind()
        self._record(
            "post_merge.observed",
            observation.observation_id,
            {"post_merge": observation.to_dict()},
        )
        return observation

    # -- helpers -------------------------------------------------------------

    def _require_work_item(self, work_item_id: str) -> dict[str, Any]:
        work_item = self._projection.work_items.get(work_item_id)
        if work_item is None:
            raise NotFoundError(f"work item {work_item_id} not found")
        return work_item

    def _require_attempt(self, attempt_id: str) -> dict[str, Any]:
        attempt = self._projection.attempts.get(attempt_id)
        if attempt is None:
            raise NotFoundError(f"attempt {attempt_id} not found")
        return attempt

    def _require_envelope(self, envelope_id: str) -> dict[str, Any]:
        envelope = self._projection.shape_artifacts.get(envelope_id)
        if envelope is None:
            raise NotFoundError(f"authority envelope {envelope_id} not found")
        return envelope

    def _require_candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate = self._projection.merge_candidates.get(candidate_id)
        if candidate is None:
            raise NotFoundError(f"merge candidate {candidate_id} not found")
        return candidate


def _duration_seconds(started_at: str, ended_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return max(0.0, (end - start).total_seconds())
    except (TypeError, ValueError):
        return 0.0
