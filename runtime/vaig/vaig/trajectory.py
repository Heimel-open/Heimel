"""Trajectory intake for P0.7 (#133 / #141).

A *trajectory* is the ordered record of an agent's reasoning/action steps that
led to a response, with provenance for each step. P0.7 requires that the
orchestrator accepts a trajectory and makes it available to instruments so they
can score drift / inconsistency *across* steps, not only on the final
(prompt, response) pair.

The trajectory is a plain data container. Production code populates it from the
governed agent loop (see ``vaig/agent_loop``); tests build it directly. The
``TrajectorySummary`` is what the orchestrator records on the result so REHT can
see that a trajectory was supplied and how many steps it carried.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class TrajectoryStep:
    """One step in an agent trajectory.

    ``provenance`` records where the step came from (e.g. ``"model"``,
    ``"tool:search"``, ``"external-unverified"``). Instruments use it to flag
    steps whose origin is not governed.
    """

    step_id: str
    prompt: str = ""
    response: str = ""
    role: str = "model"
    tool: str = ""
    timestamp: Optional[datetime] = None
    provenance: str = "model"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Trajectory:
    """Ordered set of steps that produced a response, with provenance."""

    steps: tuple[TrajectoryStep, ...]
    trajectory_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))


@dataclass(frozen=True)
class TrajectorySummary:
    """Bounded record of a supplied trajectory, attached to OrchestratorResult."""

    step_count: int
    roles: tuple[str, ...]
    has_provenance: bool
    span_seconds: Optional[float] = None
    trajectory_id: str = ""

    @classmethod
    def from_trajectory(cls, traj: Trajectory) -> "TrajectorySummary":
        steps = traj.steps
        roles: tuple[str, ...] = tuple(sorted({s.role for s in steps})) if steps else ()
        has_prov = any(s.provenance for s in steps)
        span: Optional[float] = None
        stamps = [s.timestamp for s in steps if s.timestamp is not None]
        if len(stamps) >= 2:
            span = (max(stamps) - min(stamps)).total_seconds()
        return cls(
            step_count=len(steps),
            roles=roles,
            has_provenance=has_prov,
            span_seconds=span,
            trajectory_id=traj.trajectory_id,
        )
