from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

Decision = Literal["ALLOW", "STEP_UP", "DENY"]

_VALID_DECISIONS: frozenset[str] = frozenset({"ALLOW", "STEP_UP", "DENY"})


@dataclass(frozen=True)
class DecisionResult:
    """Deterministic REHT authorization result.

    This is an authorization-boundary contract owned by REHT. It creates no
    state and performs no external effect by itself.

    The decision plane is exactly ``ALLOW`` | ``STEP_UP`` | ``DENY``. Any other
    decision value is rejected at construction so no wider outcome plane can be
    minted into the authoritative runtime.
    """

    decision: Decision
    clearance_ref: str | None = None
    permit_ref: str | None = None
    execution_context_hash: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.decision not in _VALID_DECISIONS:
            raise ValueError(f"invalid REHT decision: {self.decision!r}")


class RehtPort(Protocol):
    """Minimal protocol for the sole runtime authorization boundary."""

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult: ...
