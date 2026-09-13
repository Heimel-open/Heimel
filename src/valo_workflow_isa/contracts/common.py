from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any

SCHEMA_VERSION = "v1"


def utcnow() -> datetime:
    return datetime.now(UTC)


def canonical_digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode()
    return sha256(raw).hexdigest()


class NodeClass(str, Enum):
    """The only five runtime node classes. Anything else is a compile error."""

    READ = "READ"
    COMPUTE = "COMPUTE"
    DECIDE = "DECIDE"
    WAIT = "WAIT"
    WRITE = "WRITE"


class ControlOpcode(str, Enum):
    """Canonical control-flow ISA. No implicit control flow."""

    SEQ = "SEQ"
    PARALLEL = "PARALLEL"
    BRANCH = "BRANCH"
    JOIN = "JOIN"
    LOOP = "LOOP"
    WAIT = "WAIT"
    TIMEOUT = "TIMEOUT"
    RETRY = "RETRY"
    COMPENSATE = "COMPENSATE"
    CALL = "CALL"
    RETURN = "RETURN"
    HALT = "HALT"


class PrimitiveOpcode(str, Enum):
    """The 18 primitive workflow opcodes. No new primitives without a concrete
    demonstrator need."""

    READ_STATE = "READ_STATE"
    ASSERT_STATE = "ASSERT_STATE"
    FETCH = "FETCH"
    VALIDATE_SCHEMA = "VALIDATE_SCHEMA"
    COMPARE = "COMPARE"
    RECONCILE = "RECONCILE"
    EVALUATE_RULE = "EVALUATE_RULE"
    CALCULATE = "CALCULATE"
    REQUEST_INPUT = "REQUEST_INPUT"
    REQUEST_REVIEW = "REQUEST_REVIEW"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    PREPARE_ACTION = "PREPARE_ACTION"
    AUTHORIZE_ACTION = "AUTHORIZE_ACTION"
    EXECUTE_ACTION = "EXECUTE_ACTION"
    VERIFY_EXECUTION = "VERIFY_EXECUTION"
    CREATE_DEADLINE = "CREATE_DEADLINE"
    RESERVE_RESOURCE = "RESERVE_RESOURCE"
    RELEASE_RESOURCE = "RELEASE_RESOURCE"


class EdgeType(str, Enum):
    """Explicit edge types. All edges are explicit; there is no implicit flow."""

    NEXT = "NEXT"
    TRUE = "TRUE"
    FALSE = "FALSE"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    COMPENSATE = "COMPENSATE"


class EffectType(str, Enum):
    """Effect type system. WRITE nodes must declare an effect."""

    PURE = "PURE"
    READ_EXTERNAL = "READ_EXTERNAL"
    WRITE_INTERNAL = "WRITE_INTERNAL"
    COMMUNICATE = "COMMUNICATE"
    ALLOCATE_RESOURCE = "ALLOCATE_RESOURCE"
    CREATE_OBLIGATION = "CREATE_OBLIGATION"
    CHANGE_RIGHT = "CHANGE_RIGHT"
    MOVE_MONEY = "MOVE_MONEY"
    EXERCISE_AUTHORITY = "EXERCISE_AUTHORITY"
    SAFETY_CRITICAL = "SAFETY_CRITICAL"


class Determinism(str, Enum):
    DETERMINISTIC = "DETERMINISTIC"
    PROBABILISTIC = "PROBABILISTIC"


class WorkflowStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HALTED = "HALTED"
    DEFERRED = "DEFERRED"
    COMPENSATING = "COMPENSATING"


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    COMPENSATED = "COMPENSATED"
    WAITING = "WAITING"


class FailurePolicy(str, Enum):
    FAIL = "FAIL"
    DEFER = "DEFER"
    COMPENSATE = "COMPENSATE"
    RETRY = "RETRY"
    CONTINUE = "CONTINUE"
