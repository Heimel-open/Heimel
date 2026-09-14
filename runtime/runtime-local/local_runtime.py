"""Local Heimel runtime with an executable governed consequence path.

Submission never executes. A successful consequence requires fresh authority,
exact effect binding, a positively issued one-shot permit, execution, and
attributable evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import threading
import time
import uuid
from typing import Any, Dict, Optional

from core.interfaces import RuntimeInterface, Event, Checkpoint, Result, Decision


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class LocalPermit:
    permit_id: str
    action_id: str
    effect_digest: str
    authority_revision: int
    reht_ref: str
    racs_ref: str
    expires_at: datetime


@dataclass(frozen=True)
class LocalReceipt:
    receipt_id: str
    action_id: str
    permit_id: str
    effect_digest: str
    authority_revision: int
    reht_ref: str
    racs_ref: str
    outcome: str
    outcome_digest: str
    recorded_at: datetime


class ConsequenceDenied(RuntimeError):
    pass


class ConsequenceRejected(RuntimeError):
    pass


class EvidenceRecordingFailed(RuntimeError):
    pass


class LocalRuntime(RuntimeInterface):
    def __init__(self):
        self._actions: Dict[str, Dict[str, Any]] = {}
        self._events: Dict[str, list[Event]] = {}
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._authority_revision = 1
        self._authorized_effects: set[str] = set()
        self._issued_permits: Dict[str, LocalPermit] = {}
        self._consumed_permits: set[str] = set()
        self._permit_lock = threading.Lock()
        self._receipts: Dict[str, LocalReceipt] = {}

    def submit(self, action):
        aid = "act-" + uuid.uuid4().hex[:12]
        normalized = dict(action)
        effect_digest = _digest(normalized)
        self._actions[aid] = {
            "action": normalized,
            "effect_digest": effect_digest,
            "state": "PENDING",
            "result": None,
            "receipt_ref": None,
        }
        self._events[aid] = []
        self._emit(aid, "ACTION_REQUESTED", {"type": action.get("type"), "effect_digest": effect_digest})
        return aid

    def _emit(self, aid, kind, payload=None):
        ev = Event(
            id="ev-" + uuid.uuid4().hex[:8],
            kind=kind,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            payload=payload or {},
            source="local-runtime",
        )
        self._events.setdefault(aid, []).append(ev)
        return ev

    def stream(self, action_id):
        return list(self._events.get(action_id, []))

    def checkpoint(self, action_id):
        if action_id not in self._actions:
            raise KeyError(action_id)
        state = json.dumps(self._actions[action_id], sort_keys=True, default=str).encode()
        digest = "sha256:" + hashlib.sha256(state).hexdigest()
        cp = Checkpoint(
            id="cp-" + uuid.uuid4().hex[:12],
            step=len(self._events.get(action_id, [])),
            state_ref=digest,
            digest=digest,
        )
        self._checkpoints[cp.id] = cp
        self._emit(action_id, "CHECKPOINT", {"checkpoint": cp.id, "digest": digest})
        return cp

    def restart(self, checkpoint_id):
        if checkpoint_id not in self._checkpoints:
            raise KeyError(checkpoint_id)
        aid = "act-" + uuid.uuid4().hex[:12]
        self._actions[aid] = {"state": "RESTARTED", "from": checkpoint_id, "result": None, "receipt_ref": None}
        self._events[aid] = []
        self._emit(aid, "RESTARTED", {"from": checkpoint_id})
        return aid

    def grant(self, action_id: str) -> None:
        record = self._require_action(action_id)
        self._authorized_effects.add(record["effect_digest"])
        self._authority_revision += 1
        self._emit(action_id, "AUTHORITY_CHANGED", {"revision": self._authority_revision, "status": "GRANTED"})

    def revoke(self, action_id: str) -> None:
        record = self._require_action(action_id)
        self._authorized_effects.discard(record["effect_digest"])
        self._authority_revision += 1
        self._emit(action_id, "AUTHORITY_CHANGED", {"revision": self._authority_revision, "status": "REVOKED"})

    def authorize(self, action_id: str, *, now: Optional[datetime] = None, ttl_seconds: int = 30) -> LocalPermit:
        record = self._require_action(action_id)
        now = now or _utc_now()
        if now.tzinfo is None:
            raise ValueError("authorization time must be timezone-aware")
        effect_digest = record["effect_digest"]
        reht_ref = _digest({
            "action_id": action_id,
            "effect_digest": effect_digest,
            "authority_revision": self._authority_revision,
            "evaluated_at": now.isoformat(),
        })
        if effect_digest not in self._authorized_effects:
            record["state"] = "DENIED"
            self._emit(action_id, "DECISION", {"decision": Decision.DENY.value, "reht_ref": reht_ref})
            raise ConsequenceDenied("authority denied for exact effect")

        racs_ref = _digest({
            "decision": Decision.ALLOW.value,
            "reht_ref": reht_ref,
            "effect_digest": effect_digest,
            "authority_revision": self._authority_revision,
        })
        expires_at = now + timedelta(seconds=ttl_seconds)
        permit_id = _digest({"racs_ref": racs_ref, "action_id": action_id, "expires_at": expires_at.isoformat()})
        permit = LocalPermit(
            permit_id=permit_id,
            action_id=action_id,
            effect_digest=effect_digest,
            authority_revision=self._authority_revision,
            reht_ref=reht_ref,
            racs_ref=racs_ref,
            expires_at=expires_at,
        )
        self._issued_permits[permit_id] = permit
        record["state"] = "AUTHORIZED"
        self._emit(action_id, "DECISION", {
            "decision": Decision.ALLOW.value,
            "reht_ref": reht_ref,
            "racs_ref": racs_ref,
            "permit_id": permit_id,
            "authority_revision": self._authority_revision,
        })
        return permit

    def execute(
        self,
        action_id: str,
        permit: LocalPermit,
        *,
        now: Optional[datetime] = None,
        effect: Optional[Dict[str, Any]] = None,
    ) -> Result:
        record = self._require_action(action_id)
        now = now or _utc_now()
        if now.tzinfo is None:
            raise ValueError("execution time must be timezone-aware")

        proposed_effect = dict(record["action"] if effect is None else effect)
        effect_digest = _digest(proposed_effect)

        with self._permit_lock:
            if not isinstance(permit, LocalPermit):
                raise ConsequenceRejected("execution permit binding is missing")
            issued = self._issued_permits.get(permit.permit_id)
            if issued is None:
                raise ConsequenceRejected("permit was not issued by this runtime")
            if issued != permit:
                raise ConsequenceRejected("permit does not match issued authorization")
            if permit.permit_id in self._consumed_permits:
                raise ConsequenceRejected("one-shot permit already consumed")
            if permit.action_id != action_id:
                raise ConsequenceRejected("permit action mismatch")
            if permit.effect_digest != effect_digest or effect_digest != record["effect_digest"]:
                raise ConsequenceRejected("permit is not bound to exact effect")
            if permit.authority_revision != self._authority_revision:
                raise ConsequenceRejected("authority state changed after authorization")
            if now >= permit.expires_at:
                raise ConsequenceRejected("permit expired")
            if effect_digest not in self._authorized_effects:
                raise ConsequenceRejected("authority no longer current")
            self._consumed_permits.add(permit.permit_id)

        self._emit(action_id, "PERMIT_CONSUMED", {"permit_id": permit.permit_id, "racs_ref": permit.racs_ref})
        outcome_payload = {"executed_by": "local-runtime", "effect": proposed_effect}
        outcome_digest = _digest(outcome_payload)
        record["state"] = "EFFECT_OCCURRED_UNATTESTED"
        self._emit(action_id, "EFFECT_EXECUTED", {"effect_digest": effect_digest, "outcome_digest": outcome_digest})

        receipt_body = {
            "action_id": action_id,
            "permit_id": permit.permit_id,
            "effect_digest": effect_digest,
            "authority_revision": permit.authority_revision,
            "reht_ref": permit.reht_ref,
            "racs_ref": permit.racs_ref,
            "outcome": "SUCCESS",
            "outcome_digest": outcome_digest,
            "recorded_at": now.isoformat(),
        }
        receipt_ref = _digest(receipt_body)
        receipt = LocalReceipt(
            receipt_id=receipt_ref,
            action_id=action_id,
            permit_id=permit.permit_id,
            effect_digest=effect_digest,
            authority_revision=permit.authority_revision,
            reht_ref=permit.reht_ref,
            racs_ref=permit.racs_ref,
            outcome="SUCCESS",
            outcome_digest=outcome_digest,
            recorded_at=now,
        )
        try:
            self._record_receipt(action_id, receipt)
        except Exception as exc:
            self._emit(action_id, "EVIDENCE_FAILED", {"error": type(exc).__name__})
            raise EvidenceRecordingFailed("effect occurred but evidence was not admitted") from exc

        self._emit(action_id, "EVIDENCE_RECORDED", {"veritas_ref": receipt_ref, "outcome_digest": outcome_digest})
        result = Result(action_id=action_id, status="SUCCESS", outputs=outcome_payload, receipt_ref=receipt_ref)
        record["state"] = "EXECUTED"
        record["result"] = result
        record["receipt_ref"] = receipt_ref
        return result

    def _record_receipt(self, action_id: str, receipt: LocalReceipt) -> None:
        self._receipts[action_id] = receipt

    def result(self, action_id):
        record = self._require_action(action_id)
        result = record.get("result")
        if isinstance(result, Result):
            return result
        return Result(
            action_id=action_id,
            status="FAILURE",
            outputs={},
            error=f"NOT_EXECUTED:{record.get('state', 'UNKNOWN')}",
            receipt_ref=None,
        )

    def receipt(self, action_id: str) -> Optional[LocalReceipt]:
        return self._receipts.get(action_id)

    def replay(self, action_id: str) -> Dict[str, Any]:
        record = self._require_action(action_id)
        return {
            "action_id": action_id,
            "effect_digest": record.get("effect_digest"),
            "state": record.get("state"),
            "events": self.stream(action_id),
            "receipt": self._receipts.get(action_id),
        }

    def _require_action(self, action_id: str) -> Dict[str, Any]:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            raise KeyError(action_id) from exc


def build():
    return LocalRuntime()
