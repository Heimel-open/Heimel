"""Trajectory consistency instrument (P0.7, #133 / #141).

Consumes a supplied :class:`Trajectory` (via ``kwargs["trajectory"]``) and scores
cross-step inconsistency: steps whose provenance is not governed, steps with an
empty response, and abrupt role changes are treated as integrity risk. This is
deliberately a simple, deterministic heuristic -- the point of P0.7 is that a
trajectory is *accepted by the orchestrator and available to instruments*, not
that this particular scorer is production-grade.

The instrument declares ``requires_trajectory = True`` so the ensemble fails it
closed (UNAVAILABLE) when no trajectory is supplied, exactly like judge/generate
requirements.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from vaig.instruments.base import InstrumentBase
from vaig.instruments.registry import register
from vaig.trajectory import Trajectory


@register("trajectory_consistency", name="cross_step_consistency", priority=2)
class TrajectoryConsistencyInstrument(InstrumentBase):
    requires_trajectory = True
    self_judging = False

    @classmethod
    def is_available(cls) -> bool:
        return True

    def score(
        self,
        prompt: str,
        response: str,
        generate_fn: Optional[Callable[[str], str]] = None,
        judge_fn: Optional[Callable[[str], str]] = None,
        **kwargs: Any,
    ) -> float:
        trajectory = kwargs.get("trajectory")
        if trajectory is None or not trajectory.steps:
            raise ValueError("trajectory_consistency requires a non-empty trajectory")
        steps = trajectory.steps
        n = len(steps)
        ungoverned = sum(1 for s in steps if s.provenance not in ("model", "tool", "self"))
        empty = sum(1 for s in steps if not s.response.strip())
        # abrupt role change: a step whose role differs from the previous step's
        role_changes = sum(
            1 for i in range(1, n) if steps[i].role != steps[i - 1].role
        )
        raw = ungoverned + empty + role_changes
        # normalize to [0, 1]; cap so a few anomalies do not saturate to risk 1.0
        return min(1.0, raw / max(1, n))
