"""Provider-neutral long-horizon harness primitives for VALO Factory.

The harness owns durable execution state, isolated child contexts, bounded
context, sandbox lifecycle and duty-separated judge evidence. It never grants
authority. Every consequence-bearing action is fail-closed unless a fresh
VAIG -> REHT -> RACS authorization envelope is bound to the exact action
immediately before execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


RACS_DECISIONS = {"ALLOW", "MODIFY", "DEFER", "DENY", "STEP_UP", "HALT"}
SANDBOX_STATES = {"CREATED", "ACTIVE", "SEALED", "RELEASED"}
RUN_STATES = {"ACTIVE", "PAUSED", "COMPLETED", "BLOCKED"}


class HarnessError(RuntimeError):
    """Base error for long-horizon harness failures."""


class AuthorizationDenied(HarnessError):
    """Raised when a side effect lacks valid fresh authorization."""


class AmbiguousSideEffect(HarnessError):
    """Raised when a prior side effect may have crossed the external boundary."""


class InvalidTransition(HarnessError):
    """Raised for an invalid durable lifecycle transition."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _now_ns() -> int:
    return time.time_ns()


def _require_nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HarnessError(f"{field} must be a non-empty string")
    return value.strip()


def _safe_owned_path(path: str) -> str:
    candidate = _require_nonempty(path, "owned_file")
    pure = Path(candidate)
    if pure.is_absolute() or ".." in pure.parts:
        raise HarnessError("owned files must be relative and may not traverse parents")
    return pure.as_posix()


@dataclass(frozen=True)
class AuthorizationEnvelope:
    """Evidence proving that one exact action passed VAIG -> REHT -> RACS."""

    action_digest: str
    vaig_evaluation_id: str
    reht_clearance_id: str
    racs_decision_id: str
    racs_decision: str
    issued_at_ns: int
    expires_at_ns: int
    authority_effect: str = "execution_clearance"

    @classmethod
    def from_mapping(
        cls, raw: Mapping[str, Any], expected_action_digest: str
    ) -> "AuthorizationEnvelope":
        if not isinstance(raw, Mapping):
            raise AuthorizationDenied("authorization callback must return an object")
        action_digest = _require_nonempty(raw.get("action_digest"), "action_digest")
        if action_digest != expected_action_digest:
            raise AuthorizationDenied("authorization is not bound to this action")

        vaig = raw.get("vaig")
        reht = raw.get("reht")
        racs = raw.get("racs")
        if not all(isinstance(item, Mapping) for item in (vaig, reht, racs)):
            raise AuthorizationDenied("VAIG, REHT and RACS artifacts are required")

        assert isinstance(vaig, Mapping)
        assert isinstance(reht, Mapping)
        assert isinstance(racs, Mapping)
        for name, artifact in (("vaig", vaig), ("reht", reht), ("racs", racs)):
            bound = _require_nonempty(
                artifact.get("action_digest"), f"{name}.action_digest"
            )
            if bound != expected_action_digest:
                raise AuthorizationDenied(f"{name} artifact is not bound to this action")

        decision = _require_nonempty(racs.get("decision"), "racs.decision").upper()
        if decision not in RACS_DECISIONS:
            raise AuthorizationDenied("unknown RACS decision")

        envelope = cls(
            action_digest=action_digest,
            vaig_evaluation_id=_require_nonempty(
                vaig.get("evaluation_id"), "vaig.evaluation_id"
            ),
            reht_clearance_id=_require_nonempty(
                reht.get("clearance_id"), "reht.clearance_id"
            ),
            racs_decision_id=_require_nonempty(
                racs.get("decision_id"), "racs.decision_id"
            ),
            racs_decision=decision,
            issued_at_ns=int(raw.get("issued_at_ns", 0)),
            expires_at_ns=int(raw.get("expires_at_ns", 0)),
            authority_effect=str(raw.get("authority_effect", "execution_clearance")),
        )
        now = _now_ns()
        if envelope.issued_at_ns <= 0 or envelope.expires_at_ns <= envelope.issued_at_ns:
            raise AuthorizationDenied("authorization validity window is invalid")
        if now < envelope.issued_at_ns or now > envelope.expires_at_ns:
            raise AuthorizationDenied("authorization is not currently valid")
        if envelope.authority_effect != "execution_clearance":
            raise AuthorizationDenied("authorization envelope has wrong authority effect")
        if envelope.racs_decision != "ALLOW":
            raise AuthorizationDenied(
                f"RACS decision {envelope.racs_decision} does not permit execution"
            )
        return envelope


class SqliteHarnessStore:
    """Durable run/checkpoint state and side-effect replay journal."""

    DEFAULT_DB = os.path.expanduser("~/.valo/long_horizon.db")

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
                """CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    worker_provider_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    cursor TEXT NOT NULL,
                    sandbox_id TEXT NOT NULL,
                    checkpoint_json TEXT NOT NULL,
                    created_at_ns INTEGER NOT NULL,
                    updated_at_ns INTEGER NOT NULL
                )"""
            )
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS actions (
                    run_id TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    action_digest TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_digest TEXT,
                    authorization_json TEXT,
                    prepared_at_ns INTEGER NOT NULL,
                    completed_at_ns INTEGER,
                    PRIMARY KEY (run_id, action_id)
                )"""
            )

    def close(self) -> None:
        self.conn.close()

    def create_run(
        self,
        *,
        run_id: str,
        mission_id: str,
        owner_id: str,
        worker_id: str,
        worker_provider_id: str,
        sandbox_id: str,
    ) -> dict[str, Any]:
        now = _now_ns()
        checkpoint = {
            "schema": "valo.long-horizon.checkpoint.v1",
            "run_id": run_id,
            "mission_id": mission_id,
            "state": "ACTIVE",
            "stage": "START",
            "cursor": "0",
            "sandbox_id": sandbox_id,
            "sandbox_state": "ACTIVE",
            "completed_action_ids": [],
            "evidence_refs": [],
            "active_context": [],
            "authority_effect": "none",
            "updated_at_ns": now,
        }
        with self._lock, self.conn:
            self.conn.execute(
                """INSERT INTO runs (
                    run_id, mission_id, owner_id, worker_id, worker_provider_id,
                    state, stage, cursor, sandbox_id, checkpoint_json,
                    created_at_ns, updated_at_ns
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    mission_id,
                    owner_id,
                    worker_id,
                    worker_provider_id,
                    "ACTIVE",
                    "START",
                    "0",
                    sandbox_id,
                    json.dumps(checkpoint, sort_keys=True),
                    now,
                    now,
                ),
            )
        return checkpoint

    def load_run(self, run_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            raise HarnessError(f"unknown run_id: {run_id}")
        result = dict(row)
        result["checkpoint"] = json.loads(result.pop("checkpoint_json"))
        return result

    def save_checkpoint(
        self,
        run_id: str,
        *,
        state: str,
        stage: str,
        cursor: str,
        sandbox_id: str,
        sandbox_state: str,
        completed_action_ids: Sequence[str],
        evidence_refs: Sequence[str],
        active_context: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if state not in RUN_STATES:
            raise HarnessError(f"invalid run state: {state}")
        if sandbox_state not in SANDBOX_STATES:
            raise HarnessError(f"invalid sandbox state: {sandbox_state}")
        checkpoint = {
            "schema": "valo.long-horizon.checkpoint.v1",
            "run_id": run_id,
            "mission_id": self.load_run(run_id)["mission_id"],
            "state": state,
            "stage": _require_nonempty(stage, "stage"),
            "cursor": str(cursor),
            "sandbox_id": _require_nonempty(sandbox_id, "sandbox_id"),
            "sandbox_state": sandbox_state,
            "completed_action_ids": sorted(set(completed_action_ids)),
            "evidence_refs": list(dict.fromkeys(evidence_refs)),
            "active_context": list(active_context),
            "authority_effect": "none",
            "updated_at_ns": _now_ns(),
        }
        with self._lock, self.conn:
            changed = self.conn.execute(
                """UPDATE runs SET state=?, stage=?, cursor=?, sandbox_id=?,
                   checkpoint_json=?, updated_at_ns=? WHERE run_id=?""",
                (
                    state,
                    checkpoint["stage"],
                    checkpoint["cursor"],
                    checkpoint["sandbox_id"],
                    json.dumps(checkpoint, sort_keys=True),
                    checkpoint["updated_at_ns"],
                    run_id,
                ),
            ).rowcount
        if changed != 1:
            raise HarnessError(f"unknown run_id: {run_id}")
        return checkpoint

    def action_state(self, run_id: str, action_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM actions WHERE run_id=? AND action_id=?",
            (run_id, action_id),
        ).fetchone()
        return dict(row) if row else None

    def prepare_action(self, run_id: str, action_id: str, action_digest: str) -> None:
        with self._lock, self.conn:
            existing = self.action_state(run_id, action_id)
            if existing is not None:
                if existing["action_digest"] != action_digest:
                    raise HarnessError("action_id reused with different payload")
                if existing["state"] == "PREPARED":
                    raise AmbiguousSideEffect(
                        "action was PREPARED previously; reconcile before retry"
                    )
                return
            self.conn.execute(
                """INSERT INTO actions (
                    run_id, action_id, action_digest, state, prepared_at_ns
                ) VALUES (?, ?, ?, 'PREPARED', ?)""",
                (run_id, action_id, action_digest, _now_ns()),
            )

    def complete_action(
        self,
        run_id: str,
        action_id: str,
        *,
        result_digest: str,
        authorization: Mapping[str, Any],
    ) -> None:
        with self._lock, self.conn:
            changed = self.conn.execute(
                """UPDATE actions
                   SET state='COMPLETED', result_digest=?, authorization_json=?,
                       completed_at_ns=?
                   WHERE run_id=? AND action_id=? AND state='PREPARED'""",
                (
                    result_digest,
                    json.dumps(dict(authorization), sort_keys=True),
                    _now_ns(),
                    run_id,
                    action_id,
                ),
            ).rowcount
        if changed != 1:
            raise HarnessError("action completion requires PREPARED state")


class SandboxLifecycle:
    """Durable filesystem sandbox lifecycle; never an authority source."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lifecycle_root = self.root / ".lifecycle"
        self.lifecycle_root.mkdir(mode=0o700, exist_ok=True)
        self._lock = threading.RLock()

    def _safe_id(self, sandbox_id: str) -> str:
        sid = _require_nonempty(sandbox_id, "sandbox_id")
        if "/" in sid or "\\" in sid or sid in {".", ".."}:
            raise HarnessError("sandbox_id must be a simple identifier")
        return sid

    def _metadata_path(self, sandbox_id: str) -> Path:
        return self.lifecycle_root / f"{self._safe_id(sandbox_id)}.json"

    def _read_metadata(self, sandbox_id: str) -> dict[str, Any]:
        path = self._metadata_path(sandbox_id)
        if not path.exists():
            raise HarnessError(f"unknown sandbox: {sandbox_id}")
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HarnessError(f"invalid sandbox lifecycle state: {sandbox_id}") from exc
        state = metadata.get("state")
        if state not in SANDBOX_STATES:
            raise HarnessError(f"invalid sandbox state: {state}")
        return metadata

    def _write_metadata(self, sandbox_id: str, metadata: Mapping[str, Any]) -> None:
        target = self._metadata_path(sandbox_id)
        tmp = target.with_suffix(f".{uuid.uuid4().hex}.tmp")
        tmp.write_text(
            json.dumps(dict(metadata), sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)

    def create(self, sandbox_id: str) -> Path:
        sid = self._safe_id(sandbox_id)
        path = self.root / sid
        metadata_path = self._metadata_path(sid)
        with self._lock:
            if metadata_path.exists() or path.exists():
                raise HarnessError(f"sandbox already exists: {sid}")
            path.mkdir(mode=0o700)
            self._write_metadata(
                sid,
                {
                    "schema": "valo.long-horizon.sandbox-state.v1",
                    "sandbox_id": sid,
                    "state": "CREATED",
                    "sealed_digest": None,
                    "updated_at_ns": _now_ns(),
                    "authority_effect": "none",
                },
            )
        return path

    def activate(self, sandbox_id: str) -> Path:
        self._transition(sandbox_id, "CREATED", "ACTIVE")
        return self.root / self._safe_id(sandbox_id)

    def seal(self, sandbox_id: str) -> str:
        sid = self._safe_id(sandbox_id)
        with self._lock:
            metadata = self._read_metadata(sid)
            if metadata["state"] != "ACTIVE":
                raise InvalidTransition("sandbox must be ACTIVE before seal")
            path = self.root / sid
            if not path.is_dir():
                raise HarnessError("active sandbox directory is missing")
            manifest: list[dict[str, Any]] = []
            for item in sorted(path.rglob("*")):
                if item.is_file():
                    manifest.append(
                        {
                            "path": item.relative_to(path).as_posix(),
                            "sha256": hashlib.sha256(item.read_bytes()).hexdigest(),
                            "size": item.stat().st_size,
                        }
                    )
            sealed = digest(manifest)
            metadata.update(
                state="SEALED", sealed_digest=sealed, updated_at_ns=_now_ns()
            )
            self._write_metadata(sid, metadata)
            return sealed

    def release(self, sandbox_id: str) -> str:
        sid = self._safe_id(sandbox_id)
        with self._lock:
            metadata = self._read_metadata(sid)
            if metadata["state"] != "SEALED":
                raise InvalidTransition("sandbox must be SEALED before release")
            sealed = _require_nonempty(metadata.get("sealed_digest"), "sealed_digest")
            path = self.root / sid
            if path.exists():
                shutil.rmtree(path, ignore_errors=False)
            metadata.update(state="RELEASED", updated_at_ns=_now_ns())
            self._write_metadata(sid, metadata)
            return sealed

    def state(self, sandbox_id: str) -> str:
        return str(self._read_metadata(sandbox_id)["state"])

    def _transition(self, sandbox_id: str, expected: str, target: str) -> None:
        sid = self._safe_id(sandbox_id)
        with self._lock:
            metadata = self._read_metadata(sid)
            if metadata["state"] != expected:
                raise InvalidTransition(
                    f"sandbox transition requires {expected}, got {metadata['state']}"
                )
            metadata.update(state=target, updated_at_ns=_now_ns())
            self._write_metadata(sid, metadata)


def make_child_context(
    *,
    parent_run_id: str,
    child_id: str,
    role: str,
    mission: str,
    owned_files: Iterable[str],
    worker_id: str,
    provider_id: str,
    sandbox_id: str,
) -> dict[str, Any]:
    files = sorted({_safe_owned_path(path) for path in owned_files})
    if not files:
        raise HarnessError("child context requires at least one owned file")
    return {
        "schema": "valo.long-horizon.child-context.v1",
        "parent_run_id": _require_nonempty(parent_run_id, "parent_run_id"),
        "child_id": _require_nonempty(child_id, "child_id"),
        "role": _require_nonempty(role, "role"),
        "mission": _require_nonempty(mission, "mission"),
        "owned_files": files,
        "worker_id": _require_nonempty(worker_id, "worker_id"),
        "provider_id": _require_nonempty(provider_id, "provider_id"),
        "sandbox_id": _require_nonempty(sandbox_id, "sandbox_id"),
        "authority_effect": "none",
    }


def compact_context(
    events: Sequence[Mapping[str, Any]],
    *,
    max_items: int,
    summarizer: Callable[[Sequence[Mapping[str, Any]]], str] | None = None,
) -> list[dict[str, Any]]:
    """Bound active context while preserving hashes and immutable evidence refs."""
    if max_items < 2:
        raise HarnessError("max_items must be >= 2")
    normalized = [dict(event) for event in events]
    if len(normalized) <= max_items:
        return normalized
    prefix_count = len(normalized) - (max_items - 1)
    prefix = normalized[:prefix_count]
    tail = normalized[prefix_count:]
    evidence_refs: list[str] = []
    for event in prefix:
        refs = event.get("evidence_refs", [])
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, str) and ref and ref not in evidence_refs:
                    evidence_refs.append(ref)
    summary = (
        summarizer(prefix)
        if summarizer is not None
        else f"Compacted {len(prefix)} prior context events."
    )
    return [
        {
            "kind": "context_compaction",
            "summary": str(summary),
            "compacted_count": len(prefix),
            "source_digests": [digest(event) for event in prefix],
            "evidence_refs": evidence_refs,
            "authority_effect": "none",
        },
        *tail,
    ]


def judge_evidence(
    *,
    run_id: str,
    worker_id: str,
    worker_provider_id: str,
    judge_id: str,
    judge_provider_id: str,
    findings: Sequence[Mapping[str, Any]],
    evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Create duty-separated judge evidence; never an authorization decision."""
    if _require_nonempty(judge_id, "judge_id") == _require_nonempty(
        worker_id, "worker_id"
    ):
        raise HarnessError("worker cannot judge or attest its own run")
    normalized_findings = [dict(item) for item in findings]
    unique_refs = list(dict.fromkeys(evidence_refs))
    return {
        "schema": "valo.long-horizon.judge-evidence.v1",
        "run_id": _require_nonempty(run_id, "run_id"),
        "subject_worker_id": worker_id,
        "subject_provider_id": _require_nonempty(
            worker_provider_id, "worker_provider_id"
        ),
        "judge_id": judge_id,
        "judge_provider_id": _require_nonempty(
            judge_provider_id, "judge_provider_id"
        ),
        "provider_independent": judge_provider_id != worker_provider_id,
        "findings": normalized_findings,
        "evidence_refs": unique_refs,
        "evidence_digest": digest(
            {"findings": normalized_findings, "evidence_refs": unique_refs}
        ),
        "authority_effect": "none",
        "created_at_ns": _now_ns(),
    }


class JudgeFork:
    """Non-blocking, duty-separated judge fork."""

    def __init__(
        self,
        judge_callback: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]],
        *,
        max_workers: int = 1,
    ):
        self.judge_callback = judge_callback
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="valo-judge-fork"
        )

    def submit(
        self,
        *,
        run_id: str,
        worker_id: str,
        worker_provider_id: str,
        judge_id: str,
        judge_provider_id: str,
        subject: Mapping[str, Any],
        evidence_refs: Sequence[str],
    ) -> Future[dict[str, Any]]:
        if judge_id == worker_id:
            raise HarnessError("worker cannot fork itself as judge")
        return self._pool.submit(
            self._review,
            run_id=run_id,
            worker_id=worker_id,
            worker_provider_id=worker_provider_id,
            judge_id=judge_id,
            judge_provider_id=judge_provider_id,
            subject=dict(subject),
            evidence_refs=tuple(evidence_refs),
        )

    def _review(self, **kwargs: Any) -> dict[str, Any]:
        subject = kwargs.pop("subject")
        findings = self.judge_callback(subject)
        return judge_evidence(findings=findings, **kwargs)

    def close(self) -> None:
        self._pool.shutdown(wait=True)


class SideEffectGate:
    """Fail-closed right-before-action wrapper with durable replay protection."""

    def __init__(
        self,
        store: SqliteHarnessStore,
        authorization_callback: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    ):
        self.store = store
        self.authorization_callback = authorization_callback

    def execute(
        self,
        *,
        run_id: str,
        action_id: str,
        action_type: str,
        payload: Mapping[str, Any],
        executor: Callable[[Mapping[str, Any]], Any],
    ) -> dict[str, Any]:
        run_id = _require_nonempty(run_id, "run_id")
        self.store.load_run(run_id)
        action = {
            "run_id": run_id,
            "action_id": _require_nonempty(action_id, "action_id"),
            "action_type": _require_nonempty(action_type, "action_type"),
            "payload": dict(payload),
        }
        action_digest = digest(action)

        existing = self.store.action_state(run_id, action_id)
        if existing is not None:
            if existing["action_digest"] != action_digest:
                raise HarnessError("action_id reused with different payload")
            if existing["state"] == "COMPLETED":
                return {
                    "status": "ALREADY_COMPLETED",
                    "action_digest": action_digest,
                    "result_digest": existing["result_digest"],
                    "executed": False,
                }
            if existing["state"] == "PREPARED":
                raise AmbiguousSideEffect(
                    "action may already have executed; automatic replay denied"
                )

        if self.authorization_callback is None:
            raise AuthorizationDenied("no authorization callback configured")
        raw_authorization = self.authorization_callback(
            {
                "schema": "valo.long-horizon.action-request.v1",
                "action": action,
                "action_digest": action_digest,
                "authority_effect": "none",
            }
        )
        authorization = AuthorizationEnvelope.from_mapping(
            raw_authorization, expected_action_digest=action_digest
        )

        self.store.prepare_action(run_id, action_id, action_digest)
        result = executor(dict(payload))
        result_digest = digest({"result": result})
        self.store.complete_action(
            run_id,
            action_id,
            result_digest=result_digest,
            authorization={
                "action_digest": authorization.action_digest,
                "vaig": {
                    "evaluation_id": authorization.vaig_evaluation_id,
                    "action_digest": authorization.action_digest,
                },
                "reht": {
                    "clearance_id": authorization.reht_clearance_id,
                    "action_digest": authorization.action_digest,
                },
                "racs": {
                    "decision_id": authorization.racs_decision_id,
                    "decision": authorization.racs_decision,
                    "action_digest": authorization.action_digest,
                },
                "issued_at_ns": authorization.issued_at_ns,
                "expires_at_ns": authorization.expires_at_ns,
                "authority_effect": authorization.authority_effect,
            },
        )
        return {
            "status": "COMPLETED",
            "action_digest": action_digest,
            "result_digest": result_digest,
            "executed": True,
        }


class LongHorizonHarness:
    """Facade combining durable checkpoints and isolated execution contexts."""

    def __init__(self, store: SqliteHarnessStore, sandboxes: SandboxLifecycle):
        self.store = store
        self.sandboxes = sandboxes

    def start(
        self,
        *,
        mission_id: str,
        owner_id: str,
        worker_id: str,
        worker_provider_id: str,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        rid = run_id or f"lha-{uuid.uuid4().hex}"
        sandbox_id = f"run-{rid}"
        self.sandboxes.create(sandbox_id)
        self.sandboxes.activate(sandbox_id)
        return self.store.create_run(
            run_id=rid,
            mission_id=_require_nonempty(mission_id, "mission_id"),
            owner_id=_require_nonempty(owner_id, "owner_id"),
            worker_id=_require_nonempty(worker_id, "worker_id"),
            worker_provider_id=_require_nonempty(
                worker_provider_id, "worker_provider_id"
            ),
            sandbox_id=sandbox_id,
        )

    def spawn_child(
        self,
        *,
        parent_run_id: str,
        child_id: str,
        role: str,
        mission: str,
        owned_files: Iterable[str],
        worker_id: str,
        provider_id: str,
    ) -> dict[str, Any]:
        self.store.load_run(parent_run_id)
        sandbox_id = f"child-{parent_run_id}-{child_id}"
        self.sandboxes.create(sandbox_id)
        self.sandboxes.activate(sandbox_id)
        return make_child_context(
            parent_run_id=parent_run_id,
            child_id=child_id,
            role=role,
            mission=mission,
            owned_files=owned_files,
            worker_id=worker_id,
            provider_id=provider_id,
            sandbox_id=sandbox_id,
        )

    def resume(self, run_id: str) -> dict[str, Any]:
        run = self.store.load_run(run_id)
        checkpoint = run["checkpoint"]
        if checkpoint["state"] == "COMPLETED":
            raise InvalidTransition("completed run cannot resume")
        actual_state = self.sandboxes.state(run["sandbox_id"])
        if actual_state != checkpoint["sandbox_state"]:
            raise HarnessError(
                "checkpoint sandbox state does not match durable lifecycle state"
            )
        return checkpoint

    def checkpoint(
        self,
        run_id: str,
        *,
        state: str,
        stage: str,
        cursor: str,
        active_context: Sequence[Mapping[str, Any]],
        evidence_refs: Sequence[str] = (),
    ) -> dict[str, Any]:
        run = self.store.load_run(run_id)
        completed = [
            row["action_id"]
            for row in self.store.conn.execute(
                "SELECT action_id FROM actions WHERE run_id=? AND state='COMPLETED'",
                (run_id,),
            ).fetchall()
        ]
        return self.store.save_checkpoint(
            run_id,
            state=state,
            stage=stage,
            cursor=cursor,
            sandbox_id=run["sandbox_id"],
            sandbox_state=self.sandboxes.state(run["sandbox_id"]),
            completed_action_ids=completed,
            evidence_refs=evidence_refs,
            active_context=active_context,
        )
