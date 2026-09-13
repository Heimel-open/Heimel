"""valo-runtime-local — reference runtime implementing RuntimeInterface.

Local process execution + checkpoint/restart + event stream. No vendor deps.
All actions flow through REHT (see core.interfaces); this runtime never executes
a tool directly — it returns an action_id and emits events; the governing layer
(VAIG -> REHT -> Veritas) drives authorization and evaluation.
"""
import hashlib
import json
import time
import uuid

from core.interfaces import (
    RuntimeInterface, Event, Checkpoint, Result,
)


class LocalRuntime(RuntimeInterface):
    def __init__(self):
        self._actions = {}
        self._events = {}

    def submit(self, action):
        aid = "act-" + uuid.uuid4().hex[:12]
        self._actions[aid] = {"action": action, "state": "PENDING"}
        self._events[aid] = []
        self._emit(aid, "ACTION_REQUESTED", {"type": action.get("type")})
        return aid

    def _emit(self, aid, kind, payload=None):
        ev = Event(
            id="ev-" + uuid.uuid4().hex[:8],
            kind=kind,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            payload=payload or {},
            source="local-runtime",
        )
        self._events[aid].append(ev)
        return ev

    def stream(self, action_id):
        return list(self._events.get(action_id, []))

    def checkpoint(self, action_id):
        state = json.dumps(self._actions.get(action_id, {}), sort_keys=True).encode()
        digest = "sha256:" + hashlib.sha256(state).hexdigest()
        cp = Checkpoint(
            id="cp-" + uuid.uuid4().hex[:12],
            step=len(self._events.get(action_id, [])),
            state_ref=digest,
            digest=digest,
        )
        self._emit(action_id, "CHECKPOINT", {"checkpoint": cp.id, "digest": digest})
        return cp

    def restart(self, checkpoint_id):
        aid = "act-" + uuid.uuid4().hex[:12]
        self._actions[aid] = {"state": "RESTARTED", "from": checkpoint_id}
        self._events[aid] = []
        self._emit(aid, "RESTARTED", {"from": checkpoint_id})
        return aid

    def result(self, action_id):
        self._emit(action_id, "RESULT")
        return Result(
            action_id=action_id,
            status="SUCCESS",
            outputs={"executed_by": "local-runtime"},
        )


def build():
    return LocalRuntime()
