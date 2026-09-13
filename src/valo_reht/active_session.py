"""Active execution continuity for long-running consequence-bearing actions.

REHT remains the sole authorization owner. This module cannot grant authority or
execute rollback/handover. It keeps an already-authorized session current,
accepts non-authoritative runtime observations, narrows dynamic bounds, pauses or
halts when state changes materially, and requires a fresh REHT ALLOW before a
changed session may continue.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .contracts import DecisionResult, RehtPort
from .runtime_interlocks import RuntimeControlPlane


class SessionState(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    HALTED = "HALTED"
    COMPLETED = "COMPLETED"


class ObservationSource(str, Enum):
    SENSOR = "SENSOR"
    WATCHER = "WATCHER"
    EXECUTOR = "EXECUTOR"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


class SessionDisposition(str, Enum):
    CONTINUE = "CONTINUE"
    PAUSE = "PAUSE"
    STOP = "STOP"
    REAUTHORIZE = "REAUTHORIZE"
    ROLLBACK = "ROLLBACK"
    HANDOVER = "HANDOVER"
    HALT = "HALT"


@dataclass(frozen=True)
class SessionObservation:
    source: ObservationSource
    disposition: SessionDisposition
    reason: str = ""
    evidence_refs: tuple[str, ...] = ()
    bound_updates: Mapping[str, Any] = field(default_factory=dict)
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority_granted:
            raise ValueError("runtime observations cannot grant execution authority")


@dataclass(frozen=True)
class SessionCheckpoint:
    sequence: int
    state: SessionState
    disposition: SessionDisposition
    reason: str
    execution_context_hash: str
    clearance_ref: str | None
    permit_ref: str | None
    requires_reauthorization: bool
    valid_for_continuation: bool
    evidence_refs: tuple[str, ...] = ()
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority_granted:
            raise ValueError("session checkpoints cannot grant authority")


class ActiveExecutionSession:
    """Continuity state for one exact long-running authorized action.

    Construction requires an actual REHT ALLOW decision with clearance, permit,
    and execution-context binding. The session never derives authority from an
    observation. Any material context change or explicit REAUTHORIZE observation
    pauses continuation until :meth:`reauthorize` obtains a fresh REHT ALLOW.
    """

    def __init__(
        self,
        *,
        action_contract: Mapping[str, Any],
        execution_context: Mapping[str, Any],
        decision: DecisionResult,
        runtime_control: RuntimeControlPlane | None = None,
        dynamic_bounds: Mapping[str, Any] | None = None,
    ) -> None:
        if decision.decision != "ALLOW":
            raise ValueError("active session requires REHT ALLOW")
        if not decision.clearance_ref or not decision.permit_ref:
            raise ValueError("active session requires clearance and permit")
        context_hash = _digest(execution_context)
        if not decision.execution_context_hash or decision.execution_context_hash != context_hash:
            raise ValueError("active session context does not match REHT binding")

        self._action = copy.deepcopy(dict(action_contract))
        self._authorized_context_hash = context_hash
        self._clearance_ref = decision.clearance_ref
        self._permit_ref = decision.permit_ref
        self._runtime_control = runtime_control or RuntimeControlPlane()
        self._bounds: dict[str, Any] = copy.deepcopy(dict(dynamic_bounds or {}))
        self._state = SessionState.RUNNING
        self._sequence = 0
        self._requires_reauthorization = False
        self._history: list[SessionCheckpoint] = []

    @property
    def state(self) -> SessionState:
        return self._state

    @property
    def dynamic_bounds(self) -> dict[str, Any]:
        return copy.deepcopy(self._bounds)

    @property
    def history(self) -> tuple[SessionCheckpoint, ...]:
        return tuple(self._history)

    @property
    def requires_reauthorization(self) -> bool:
        return self._requires_reauthorization

    def _checkpoint(
        self,
        *,
        disposition: SessionDisposition,
        reason: str,
        execution_context_hash: str,
        evidence_refs: tuple[str, ...] = (),
    ) -> SessionCheckpoint:
        self._sequence += 1
        valid = (
            self._state is SessionState.RUNNING
            and not self._requires_reauthorization
            and disposition is SessionDisposition.CONTINUE
        )
        checkpoint = SessionCheckpoint(
            sequence=self._sequence,
            state=self._state,
            disposition=disposition,
            reason=reason,
            execution_context_hash=execution_context_hash,
            clearance_ref=self._clearance_ref,
            permit_ref=self._permit_ref,
            requires_reauthorization=self._requires_reauthorization,
            valid_for_continuation=valid,
            evidence_refs=evidence_refs,
        )
        self._history.append(checkpoint)
        return checkpoint

    def observe(
        self,
        *,
        execution_context: Mapping[str, Any],
        observation: SessionObservation,
    ) -> SessionCheckpoint:
        """Apply one non-authoritative runtime observation.

        Fresh context is mandatory. A changed context automatically requires
        reauthorization even when the observation itself says CONTINUE.
        """
        if self._state in {SessionState.HALTED, SessionState.COMPLETED}:
            return self._checkpoint(
                disposition=SessionDisposition.HALT,
                reason=f"session already {self._state.value}",
                execution_context_hash=_digest(execution_context),
                evidence_refs=observation.evidence_refs,
            )

        current_hash = _digest(execution_context)
        runtime_block = self._runtime_control.check(self._action, execution_context)
        if runtime_block is not None:
            self._state = SessionState.HALTED
            self._requires_reauthorization = False
            return self._checkpoint(
                disposition=SessionDisposition.HALT,
                reason=runtime_block,
                execution_context_hash=current_hash,
                evidence_refs=observation.evidence_refs,
            )

        if observation.bound_updates:
            self._bounds = _attenuate(self._bounds, observation.bound_updates)

        if current_hash != self._authorized_context_hash:
            self._state = SessionState.PAUSED
            self._requires_reauthorization = True
            return self._checkpoint(
                disposition=SessionDisposition.REAUTHORIZE,
                reason="EXECUTION_CONTEXT_CHANGED",
                execution_context_hash=current_hash,
                evidence_refs=observation.evidence_refs,
            )

        disposition = observation.disposition
        reason = observation.reason or disposition.value

        if disposition is SessionDisposition.CONTINUE:
            if self._state is SessionState.PAUSED or self._requires_reauthorization:
                return self._checkpoint(
                    disposition=SessionDisposition.REAUTHORIZE,
                    reason="SESSION_REAUTHORIZATION_REQUIRED",
                    execution_context_hash=current_hash,
                    evidence_refs=observation.evidence_refs,
                )
            self._state = SessionState.RUNNING
        elif disposition is SessionDisposition.PAUSE:
            self._state = SessionState.PAUSED
        elif disposition in {SessionDisposition.STOP, SessionDisposition.HALT}:
            self._state = SessionState.HALTED
            self._requires_reauthorization = False
        elif disposition is SessionDisposition.REAUTHORIZE:
            self._state = SessionState.PAUSED
            self._requires_reauthorization = True
        elif disposition in {SessionDisposition.ROLLBACK, SessionDisposition.HANDOVER}:
            # These are consequence-bearing follow-on actions. This session only
            # requests them; a separate REHT-authorized action must execute them.
            self._state = SessionState.PAUSED
            self._requires_reauthorization = True

        return self._checkpoint(
            disposition=disposition,
            reason=reason,
            execution_context_hash=current_hash,
            evidence_refs=observation.evidence_refs,
        )

    def reauthorize(
        self,
        *,
        reht: RehtPort,
        execution_context: Mapping[str, Any],
    ) -> SessionCheckpoint:
        """Request fresh REHT authorization for the exact current action/bounds.

        Any non-ALLOW leaves the session HALTED. A failed recovery therefore
        never silently returns to RUNNING.
        """
        if self._state is SessionState.COMPLETED:
            raise ValueError("completed session cannot be reauthorized")
        context = copy.deepcopy(dict(execution_context))
        action = copy.deepcopy(self._action)
        if self._bounds:
            action["runtime_bounds"] = copy.deepcopy(self._bounds)

        runtime_block = self._runtime_control.check(action, context)
        if runtime_block is not None:
            self._state = SessionState.HALTED
            self._requires_reauthorization = False
            return self._checkpoint(
                disposition=SessionDisposition.HALT,
                reason=runtime_block,
                execution_context_hash=_digest(context),
            )

        decision = reht.authorize(context, action)
        current_hash = _digest(context)
        if decision.decision != "ALLOW":
            self._state = SessionState.HALTED
            self._requires_reauthorization = False
            return self._checkpoint(
                disposition=SessionDisposition.HALT,
                reason=decision.reason or f"REAUTHORIZATION_{decision.decision}",
                execution_context_hash=current_hash,
            )
        if not decision.clearance_ref or not decision.permit_ref:
            self._state = SessionState.HALTED
            self._requires_reauthorization = False
            return self._checkpoint(
                disposition=SessionDisposition.HALT,
                reason="REAUTHORIZATION_ALLOW_MISSING_CAPABILITY",
                execution_context_hash=current_hash,
            )
        if decision.execution_context_hash != current_hash:
            self._state = SessionState.HALTED
            self._requires_reauthorization = False
            return self._checkpoint(
                disposition=SessionDisposition.HALT,
                reason="REAUTHORIZATION_CONTEXT_BINDING_MISMATCH",
                execution_context_hash=current_hash,
            )

        self._authorized_context_hash = current_hash
        self._clearance_ref = decision.clearance_ref
        self._permit_ref = decision.permit_ref
        self._state = SessionState.RUNNING
        self._requires_reauthorization = False
        return self._checkpoint(
            disposition=SessionDisposition.CONTINUE,
            reason="REAUTHORIZED_BY_REHT",
            execution_context_hash=current_hash,
        )

    def complete(self, *, execution_context: Mapping[str, Any]) -> SessionCheckpoint:
        if self._state is not SessionState.RUNNING or self._requires_reauthorization:
            raise ValueError("only a current running session can complete")
        current_hash = _digest(execution_context)
        if current_hash != self._authorized_context_hash:
            self._state = SessionState.PAUSED
            self._requires_reauthorization = True
            return self._checkpoint(
                disposition=SessionDisposition.REAUTHORIZE,
                reason="EXECUTION_CONTEXT_CHANGED_BEFORE_COMPLETION",
                execution_context_hash=current_hash,
            )
        self._state = SessionState.COMPLETED
        return self._checkpoint(
            disposition=SessionDisposition.CONTINUE,
            reason="SESSION_COMPLETED",
            execution_context_hash=current_hash,
        )


def _attenuate(current: Mapping[str, Any], updates: Mapping[str, Any]) -> dict[str, Any]:
    """Apply dynamic-bound updates without widening the existing envelope."""
    result = copy.deepcopy(dict(current))
    for key, new_value in updates.items():
        if key not in result:
            raise ValueError(f"runtime bound cannot be introduced during session: {key}")
        old_value = result[key]
        if isinstance(old_value, bool):
            if old_value is False and new_value is True:
                raise ValueError(f"runtime bound cannot widen: {key}")
            if not isinstance(new_value, bool):
                raise ValueError(f"runtime bound type mismatch: {key}")
        elif isinstance(old_value, (int, float)) and not isinstance(old_value, bool):
            if not isinstance(new_value, (int, float)) or isinstance(new_value, bool):
                raise ValueError(f"runtime bound type mismatch: {key}")
            if float(new_value) > float(old_value):
                raise ValueError(f"runtime bound cannot widen: {key}")
        elif isinstance(old_value, (set, frozenset, list, tuple)):
            old_set = set(old_value)
            new_set = set(new_value) if isinstance(new_value, (set, frozenset, list, tuple)) else None
            if new_set is None or not new_set.issubset(old_set):
                raise ValueError(f"runtime bound cannot widen: {key}")
            if isinstance(old_value, tuple):
                new_value = tuple(item for item in old_value if item in new_set)
            elif isinstance(old_value, list):
                new_value = [item for item in old_value if item in new_set]
            else:
                new_value = type(old_value)(new_set)
        elif new_value != old_value:
            raise ValueError(f"runtime bound cannot change non-orderable value: {key}")
        result[key] = copy.deepcopy(new_value)
    return result


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ActiveExecutionSession",
    "ObservationSource",
    "SessionCheckpoint",
    "SessionDisposition",
    "SessionObservation",
    "SessionState",
]
