"""
VALO Spend Gate v0.1

Combines ROI Gate and Model Router.

Order:
    1. Is the work worth doing?
    2. If yes, which approved model should do it?

This keeps expensive remote tokens behind value, authority and routing checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from vacs.src.roi_gate import ROIEstimate, ROIPolicy, ROIResult, ROIDecision, VALOROIGate
from vacs.src.model_router import (
    ModelCard,
    RouteResult,
    RouteDecision,
    RoutePolicy,
    TaskProfile,
    VALOModelRouter,
)


@dataclass(frozen=True)
class SpendGateResult:
    roi_result: ROIResult
    route_result: Optional[RouteResult]
    final_decision: str
    reason: str


class VALOSpendGate:
    """
    Cost and routing orchestrator for agent work.

    It does not execute the model call. It decides whether the spend is
    admissible and which approved model should receive the job.
    """

    def __init__(self):
        self.roi_gate = VALOROIGate()
        self.model_router = VALOModelRouter()

    def evaluate(
        self,
        estimate: ROIEstimate,
        task: TaskProfile,
        models: Iterable[ModelCard],
        roi_policy: ROIPolicy | None = None,
        route_policy: RoutePolicy | None = None,
    ) -> SpendGateResult:
        roi_result = self.roi_gate.evaluate(estimate, roi_policy)

        if roi_result.decision in (ROIDecision.DENY, ROIDecision.DEFER, ROIDecision.HALT):
            return SpendGateResult(
                roi_result=roi_result,
                route_result=None,
                final_decision=roi_result.decision.value,
                reason=f"ROI Gate stopped routing: {roi_result.reason}",
            )

        route_result = self.model_router.route(task, models, route_policy)

        if roi_result.decision == ROIDecision.STEP_UP:
            return SpendGateResult(
                roi_result=roi_result,
                route_result=route_result,
                final_decision="STEP_UP",
                reason=f"ROI Gate requires approval before selected route: {roi_result.reason}",
            )

        if route_result.decision in (RouteDecision.DENY, RouteDecision.DEFER, RouteDecision.HALT, RouteDecision.HUMAN):
            return SpendGateResult(
                roi_result=roi_result,
                route_result=route_result,
                final_decision=route_result.decision.value,
                reason=f"Model Router stopped or escalated routing: {route_result.reason}",
            )

        return SpendGateResult(
            roi_result=roi_result,
            route_result=route_result,
            final_decision=route_result.decision.value,
            reason="ROI accepted and model route selected",
        )
