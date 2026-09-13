"""Measured route-planning and execution efficiency metrics.

No performance claim is inferred without an explicit measured baseline.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import RouteSelection


class RoutePlanningMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_candidate_count: int = Field(ge=0)
    active_candidate_count: int = Field(ge=0)
    pruned_candidate_count: int = Field(ge=0)
    active_frontier_width: int = Field(ge=0)
    critical_path_node_count: int = Field(ge=0)
    parallel_group_count: int = Field(ge=0)
    estimated_completion_ms: int | None = Field(default=None, ge=0)
    estimated_total_cost_microunits: int | None = Field(default=None, ge=0)

    @property
    def digest(self) -> str:
        return canonical_digest(self)


class RouteWorkMeasurement(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evaluated_nodes: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    context_units: int = Field(ge=0)
    governance_evaluations: int = Field(ge=0)
    completion_ms: int = Field(ge=0)
    total_cost_microunits: int = Field(ge=0)
    human_wait_ms: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    rollback_count: int = Field(default=0, ge=0)
    source_ref: str

    @property
    def digest(self) -> str:
        return canonical_digest(self)


class RouteEfficiencyDelta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_digest: str
    observed_digest: str
    evaluated_nodes_delta: int
    model_calls_delta: int
    tool_calls_delta: int
    context_units_delta: int
    governance_evaluations_delta: int
    completion_ms_delta: int
    total_cost_microunits_delta: int
    work_reduced: bool
    measured_faster: bool
    measured_lower_cost: bool
    delta_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"delta_digest": ""}))


def planning_metrics_from_selection(
    selection: RouteSelection,
    *,
    input_candidate_count: int,
) -> RoutePlanningMetrics:
    if input_candidate_count < len(selection.pruned_candidates):
        raise ValueError("input candidate count is below pruned candidate count")
    active_count = input_candidate_count - len(selection.pruned_candidates)
    if selection.selected_candidate_id is None and active_count:
        raise ValueError("no-route selection cannot report active candidates")
    return RoutePlanningMetrics(
        input_candidate_count=input_candidate_count,
        active_candidate_count=active_count,
        pruned_candidate_count=len(selection.pruned_candidates),
        active_frontier_width=len(selection.active_frontier),
        critical_path_node_count=len(selection.critical_path),
        parallel_group_count=len(selection.parallel_groups),
        estimated_completion_ms=selection.estimated_completion_ms,
        estimated_total_cost_microunits=(
            selection.estimated_total_cost_microunits
        ),
    )


def compare_route_work(
    baseline: RouteWorkMeasurement,
    observed: RouteWorkMeasurement,
) -> RouteEfficiencyDelta:
    """Compare two measured runs; positive deltas mean work/time/cost avoided."""
    values = {
        "evaluated_nodes_delta": baseline.evaluated_nodes - observed.evaluated_nodes,
        "model_calls_delta": baseline.model_calls - observed.model_calls,
        "tool_calls_delta": baseline.tool_calls - observed.tool_calls,
        "context_units_delta": baseline.context_units - observed.context_units,
        "governance_evaluations_delta": (
            baseline.governance_evaluations - observed.governance_evaluations
        ),
        "completion_ms_delta": baseline.completion_ms - observed.completion_ms,
        "total_cost_microunits_delta": (
            baseline.total_cost_microunits - observed.total_cost_microunits
        ),
    }
    work_reduced = any(
        values[key] > 0
        for key in (
            "evaluated_nodes_delta",
            "model_calls_delta",
            "tool_calls_delta",
            "context_units_delta",
            "governance_evaluations_delta",
        )
    )
    provisional = RouteEfficiencyDelta(
        baseline_digest=baseline.digest,
        observed_digest=observed.digest,
        **values,
        work_reduced=work_reduced,
        measured_faster=values["completion_ms_delta"] > 0,
        measured_lower_cost=values["total_cost_microunits_delta"] > 0,
        delta_digest="",
    )
    return provisional.model_copy(
        update={"delta_digest": provisional.computed_digest}
    )


__all__ = [
    "RouteEfficiencyDelta",
    "RoutePlanningMetrics",
    "RouteWorkMeasurement",
    "compare_route_work",
    "planning_metrics_from_selection",
]
