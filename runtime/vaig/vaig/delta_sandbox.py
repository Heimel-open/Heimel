"""
DeltaBoxSandbox — L8, checkpoint + rollback for agentic execution.

Security note (VAIG#157): checkpoints previously used `pickle` for both
serialization and deserialization. `pickle.loads` on attacker-influenced bytes
is RCE-prone. We now serialize with JSON by default (safe, language-neutral).
Only states that are not JSON-serializable fall back to pickle, and that path
uses a `RestrictedUnpickler` that refuses to instantiate arbitrary classes —
so even a malicious checkpoint blob cannot execute code on rollback.
"""

import base64
import io
import json
import pickle
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional


class CheckpointNotFoundError(KeyError):
    pass


class _RestrictedUnpickler(pickle.Unpickler):
    """Pickle loader that refuses to import or instantiate arbitrary globals.

    Blocks the classic pickle RCE vector: ``__reduce__`` returning
    ``(os.system, (cmd,))`` etc. Only a small allow-list of safe builtins is
    permitted. Anything else raises ``pickle.UnpicklingError``.
    """

    SAFE_BUILTINS = frozenset({
        "builtins.str", "builtins.bytes", "builtins.bytearray",
        "builtins.int", "builtins.float", "builtins.bool",
        "builtins.complex", "builtins.list", "builtins.tuple",
        "builtins.dict", "builtins.set", "builtins.frozenset",
        "builtins.NoneType", "builtins.float", "builtins.range",
    })

    def find_class(self, module: str, name: str) -> Any:
        qual = f"{module}.{name}"
        if qual in self.SAFE_BUILTINS:
            return super().find_class(module, name)
        # Refuse everything else (os.system, subprocess.Popen, eval, ...).
        raise pickle.UnpicklingError(
            f"Blocked unsafe pickle global: {qual!r}"
        )


def _safe_pickle_loads(data: bytes) -> Any:
    return _RestrictedUnpickler(io.BytesIO(data)).load()


_ENVELOPE_MAGIC = "v1:"


def _serialize(state: Any) -> bytes:
    """Return a base64 envelope: 'v1:<base64(json|pickle-blob)>'.

    JSON is preferred for primitive data (dict/list/str/int/float/bool/None).
    Anything not JSON-serializable (set, tuple, bytes, custom objects, ...)
    falls back to a restricted pickle blob (safe to load back via
    _safe_pickle_loads — never raw pickle.loads).
    """
    try:
        payload = json.dumps(state).encode("utf-8")
        kind = "j"
    except (TypeError, ValueError):
        # Fallback: restricted pickle (only loaded by _safe_pickle_loads).
        payload = pickle.dumps(state)
        kind = "p"
    return (_ENVELOPE_MAGIC + kind + ":").encode("ascii") + base64.b64encode(payload)


def _deserialize(data: bytes) -> Any:
    text = data.decode("ascii")
    if not text.startswith(_ENVELOPE_MAGIC):
        # Legacy format (old pickle-only checkpoints): treat as raw pickle.
        return _safe_pickle_loads(base64.b64decode(data))
    _, kind, blob_b64 = text.split(":", 2)
    blob = base64.b64decode(blob_b64)
    if kind == "j":
        return json.loads(blob)
    # kind == "p": restricted pickle fallback.
    return _safe_pickle_loads(blob)


class DeltaBoxSandbox:
    """
    L8 — Checkpoint + rollback for agentic execution.

    When L4 HALT fires mid-execution, rollback to the last known-good state.

    Usage:
        box = DeltaBoxSandbox()
        ckpt = box.checkpoint({"messages": history})
        try:
            response = call_model(prompt)
            result = orchestrator.evaluate(prompt, response)
            if result.should_halt:
                state = box.rollback(ckpt)
                return halt_response(state)
            box.commit(ckpt)
            return response
        except Exception:
            box.rollback(ckpt)
            raise
    """

    def __init__(self):
        self._checkpoints: Dict[str, bytes] = {}
        self._lock = threading.Lock()

    def checkpoint(self, state: Any) -> str:
        """Serialize and store state. Returns checkpoint_id."""
        ckpt_id = str(uuid.uuid4())[:8]
        serialized = _serialize(state)
        with self._lock:
            self._checkpoints[ckpt_id] = serialized
        return ckpt_id

    def rollback(self, checkpoint_id: str) -> Any:
        """Deserialize and return stored state. Does NOT delete the checkpoint.

        Deserialization is safe: JSON by default, restricted-pickle fallback
        only (see _safe_pickle_loads). Malicious checkpoint bytes cannot
        execute code.
        """
        with self._lock:
            data = self._checkpoints.get(checkpoint_id)
        if data is None:
            raise CheckpointNotFoundError(f"No checkpoint: {checkpoint_id!r}")
        return _deserialize(data)

    def commit(self, checkpoint_id: str) -> None:
        """Delete checkpoint after successful execution."""
        with self._lock:
            self._checkpoints.pop(checkpoint_id, None)

    def execute(
        self,
        fn: Callable,
        *args,
        checkpoint_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Execute fn(*args, **kwargs).
        If checkpoint_id given, rolls back automatically on exception before re-raising.
        """
        try:
            return fn(*args, **kwargs)
        except Exception:
            if checkpoint_id is not None:
                try:
                    self.rollback(checkpoint_id)
                except CheckpointNotFoundError:
                    pass
            raise

    def active(self) -> List[str]:
        """Return list of active checkpoint IDs."""
        with self._lock:
            return list(self._checkpoints.keys())

    def clear(self) -> None:
        """Remove all checkpoints."""
        with self._lock:
            self._checkpoints.clear()
