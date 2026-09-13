"""Deployment consistency contracts for consequence-boundary state.

These contracts are subordinate mechanical deployment constraints. They do not
grant execution authority, mint permits, or change REHT decisions. Their sole
purpose is to prevent process-local or same-host state from being misrepresented
as a multi-host consistency mechanism.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ConsistencyScope(str, Enum):
    """Strongest deployment scope a state mechanism explicitly supports."""

    PROCESS_LOCAL = "PROCESS_LOCAL"
    SAME_HOST_SHARED = "SAME_HOST_SHARED"
    DISTRIBUTED_CONSENSUS = "DISTRIBUTED_CONSENSUS"


class DeploymentTopology(str, Enum):
    """Consequence-boundary deployment topology."""

    SINGLE_HOST = "SINGLE_HOST"
    MULTI_HOST = "MULTI_HOST"


def _scope(value: Any) -> ConsistencyScope | None:
    raw = getattr(value, "consistency_scope", None)
    if isinstance(raw, ConsistencyScope):
        return raw
    try:
        return ConsistencyScope(str(raw))
    except (TypeError, ValueError):
        return None


def _require_distributed(component: str, value: Any) -> None:
    observed_scope = _scope(value)
    if observed_scope is ConsistencyScope.DISTRIBUTED_CONSENSUS:
        return
    observed = observed_scope.value if observed_scope is not None else "UNDECLARED"
    raise ValueError(
        f"MULTI_HOST EffectBoundary requires distributed-consensus {component}; "
        f"observed {observed}"
    )


def require_deployment_consistency(
    *,
    topology: DeploymentTopology | str,
    permit_store: Any,
    execution_journal: Any,
    runtime_control: Any,
    resource_ledger: Any,
) -> DeploymentTopology:
    """Fail closed when mutable consequence state is weaker than topology.

    ``SINGLE_HOST`` preserves the existing production-safe contract. For
    ``MULTI_HOST`` all mutable state capable of changing whether/how an effect
    may proceed must explicitly declare distributed-consensus semantics:

    - single-use permit truth;
    - execution-journal truth;
    - HALT/revocation runtime-control truth;
    - hierarchical resource-budget truth.

    A declaration is a deployment contract, not proof that a backend is correct;
    each distributed implementation still requires partition/failover/
    concurrency verification.
    """

    try:
        normalized = (
            topology
            if isinstance(topology, DeploymentTopology)
            else DeploymentTopology(str(topology))
        )
    except ValueError as exc:
        raise ValueError("unknown deployment topology") from exc

    if normalized is DeploymentTopology.MULTI_HOST:
        _require_distributed("permit store", permit_store)
        _require_distributed("execution journal", execution_journal)
        _require_distributed("runtime control", runtime_control)
        _require_distributed("resource ledger", resource_ledger)
    return normalized


__all__ = [
    "ConsistencyScope",
    "DeploymentTopology",
    "require_deployment_consistency",
]
