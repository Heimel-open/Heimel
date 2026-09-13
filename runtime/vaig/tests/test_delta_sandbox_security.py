"""
Tests for vaig.delta_sandbox — VAIG#157 pickle hardening.

Covers:
- JSON-default serialization round-trips safely
- non-JSON types (set/tuple/bytes) round-trip via restricted pickle fallback
- a malicious pickle checkpoint blob is REFUSED (no RCE) on rollback
"""
import base64
import io
import pickle

import pytest

from vaig.delta_sandbox import (
    CheckpointNotFoundError,
    DeltaBoxSandbox,
    _RestrictedUnpickler,
    _serialize,
    _deserialize,
)


def test_json_roundtrip_basic():
    box = DeltaBoxSandbox()
    state = {"messages": ["a", "b"], "score": 0.5, "flag": True, "none": None}
    cid = box.checkpoint(state)
    assert box.rollback(cid) == state


def test_json_roundtrip_nested_and_list():
    box = DeltaBoxSandbox()
    state = {"items": [1, 2, {"x": [3, 4]}], "meta": {"k": "v"}}
    cid = box.checkpoint(state)
    assert box.rollback(cid) == state


def test_pickle_fallback_for_set_tuple_bytes():
    box = DeltaBoxSandbox()
    state = {"s": {1, 2, 3}, "t": (4, 5), "b": b"\x00\x01binary"}
    cid = box.checkpoint(state)
    out = box.rollback(cid)
    assert out["s"] == {1, 2, 3}
    assert out["t"] == (4, 5)
    assert out["b"] == b"\x00\x01binary"


def test_commit_removes_checkpoint():
    box = DeltaBoxSandbox()
    cid = box.checkpoint({"x": 1})
    box.commit(cid)
    assert cid not in box.active()


def test_rollback_unknown_id_raises():
    box = DeltaBoxSandbox()
    with pytest.raises(CheckpointNotFoundError):
        box.rollback("nope")


def test_execute_auto_rollback_then_reraise():
    box = DeltaBoxSandbox()
    cid = box.checkpoint({"before": True})

    class Boom(Exception):
        pass

    with pytest.raises(Boom):
        box.execute(lambda: (_ for _ in ()).throw(Boom()), checkpoint_id=cid)
    # checkpoint still present (rollback does not delete)
    assert cid in box.active()


def test_malicious_pickle_blob_is_refused():
    """A checkpoint crafted with os.system-style pickle must NOT execute."""
    # Build a classic RCE payload (does not actually run; just proves refusal).
    class Evil:
        def __reduce__(self):
            return (eval, ("1+1",))

    evil_blob = pickle.dumps(Evil())
    envelope = b"v1:p:" + base64.b64encode(evil_blob)
    assert envelope.startswith(b"v1:p:")
    with pytest.raises(pickle.UnpicklingError):
        _deserialize(envelope)


def test_restricted_unpickler_blocks_dangerous_globals():
    class Evil:
        def __reduce__(self):
            import os

            return (os.system, ("echo pwned",))

    data = pickle.dumps(Evil())
    with pytest.raises(pickle.UnpicklingError):
        _RestrictedUnpickler(io.BytesIO(data)).load()


def test_legacy_pickle_checkpoint_refused_if_malicious():
    class Evil:
        def __reduce__(self):
            return (eval, ("1+1",))

    legacy = base64.b64encode(pickle.dumps(Evil()))
    with pytest.raises(pickle.UnpicklingError):
        _deserialize(legacy)


def test_serialize_is_base64_ascii_envelope():
    blob = _serialize({"a": 1})
    assert blob.startswith(b"v1:")
    decoded = blob.decode("ascii")  # must be ascii-enveloped
    assert decoded.startswith("v1:j:") or decoded.startswith("v1:p:")
