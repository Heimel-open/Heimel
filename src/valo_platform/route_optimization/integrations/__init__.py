"""Adapters from existing planning and governance contracts into route optimization."""

from src.valo_platform.route_optimization.integrations.execution_binding import (
    RouteBoundClearanceInput,
    RouteBoundClearanceReceipt,
    RouteBoundCommitEnvelope,
    assert_route_bound_commit,
    bind_route_to_clearance,
    clear_route_bound_input,
    create_route_bound_commit,
    verify_route_bound_commit,
)
from src.valo_platform.route_optimization.integrations.governance_inputs import (
    GovernanceInputPolicy,
    GovernanceInputSnapshot,
    apply_governance_inputs,
    build_governance_input_snapshot,
    governance_inputs_changed,
)
from src.valo_platform.route_optimization.integrations.workflow_contracts import (
    WorkflowRouteCompilationError,
    compile_workflow_graph,
    workflow_candidate,
)

__all__ = [
    "GovernanceInputPolicy",
    "GovernanceInputSnapshot",
    "RouteBoundClearanceInput",
    "RouteBoundClearanceReceipt",
    "RouteBoundCommitEnvelope",
    "WorkflowRouteCompilationError",
    "apply_governance_inputs",
    "assert_route_bound_commit",
    "bind_route_to_clearance",
    "build_governance_input_snapshot",
    "clear_route_bound_input",
    "compile_workflow_graph",
    "create_route_bound_commit",
    "governance_inputs_changed",
    "verify_route_bound_commit",
    "workflow_candidate",
]
