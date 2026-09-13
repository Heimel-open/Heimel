"""VAIG execution boundary v0.1.

Separate L3 boundary module for agent-loop execution governance.
This package does not replace the existing vaig.agent_loop MVP harness.
"""

from .boundary import BoundaryDecision, BoundaryResult, ExecutionBoundary

__all__ = ["BoundaryDecision", "BoundaryResult", "ExecutionBoundary"]
