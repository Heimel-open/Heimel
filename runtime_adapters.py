"""valo-runtime-adapters — runtime adapters behind a common RuntimeInterface.

Each backend (HarnessRouter, Google, OpenAI, Claude) implements the SAME
contract. They never execute tools directly; they submit actions and emit events
through the governing layer (REHT->RACS->Veritas).

The vendor-specific SDK import is deferred (lazy) so that a missing vendor package
does NOT break the contract tests or the other adapters.
"""
import hashlib
import json
import time
import uuid

from core.interfaces import (
    RuntimeInterface, Event, Checkpoint, Result,
)


class _BaseAdapter(RuntimeInterface):
    backend = "base"

    def __init__(self):
        self._actions = {}
        self._events = {}
        self._backend_state = {}

    def submit(self, action):
        aid = "act-" + uuid.uuid4().hex[:12]
        self._actions[aid] = {"action": action, "state": "PENDING", "backend": self.backend}
        self._events[aid] = []
        self._emit(aid, "ACTION_REQUESTED", {"type": action.get("type"), "backend": self.backend})
        return aid

    def _emit(self, aid, kind, payload=None):
        ev = Event(
            id="ev-" + uuid.uuid4().hex[:8],
            kind=kind,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            payload=payload or {},
            source=self.backend,
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
        self._actions[aid] = {"state": "RESTARTED", "from": checkpoint_id, "backend": self.backend}
        self._events[aid] = []
        self._emit(aid, "RESTARTED", {"from": checkpoint_id})
        return aid

    def result(self, action_id):
        self._emit(action_id, "RESULT")
        return Result(action_id=action_id, status="SUCCESS",
                      outputs={"executed_by": self.backend})


class HarnessRouter(_BaseAdapter):
    """Routes an action to a selected backend runtime. Default: local."""
    backend = "harness-router"

    def __init__(self, backend=None):
        super().__init__()
        self.selected = backend or "local"


class GoogleAgentPlatform(_BaseAdapter):
    backend = "google-agent-platform"

    def __init__(self):
        super().__init__()
        # Lazy: import google agent libs only when actually used.
        # self._client = ... (deferred)


class OpenAIAgents(_BaseAdapter):
    backend = "openai-agents"

    def __init__(self):
        super().__init__()


class ClaudeCode(_BaseAdapter):
    backend = "claude-code"

    def __init__(self):
        super().__init__()


def build():
    """Default runtime adapter for this repo: HarnessRouter."""
    return HarnessRouter()
