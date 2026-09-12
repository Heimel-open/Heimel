"""Deterministic Function Fabric lowering into Kernel workspace contracts.

Function Fabric describes the program and its governance requirements. Kernel
still owns state projection and purpose enforcement; REHT still owns final
authorization. This module creates no authority and performs no execution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator
from valo_kernel import (
    CandidateKind,
    ProjectionSelector,
    Purpose,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
)

from .contracts.common import AutonomyLevel, FunctionStatus, canonical_digest
from .contracts.function import FunctionDefinition
from .contracts.registry import RegistrySnapshot

WORKSPACE_COMPILER_REF = "valo-function-fabric.workspace-plan@1"


class WorkspacePlanError(ValueError):
    """Function governance cannot be lowered into a bounded workspace."""


class FunctionWorkspacePlan(BaseModel):
    schema_version: Literal["function_workspace_plan.v1"] = "function_workspace_plan.v1"
    compiler_ref: Literal["valo-function-fabric.workspace-plan@1"] = (
        WORKSPACE_COMPILER_REF
    )
    function_identity: str
    function_hash: str
    workflow_ref: str
    compiled_graph_hash: str
    registry_snapshot_hash: str
    program_digest: str
    workspace_spec: WorkspaceSpec
    plan_digest: str = ""
    authority_effect: Literal["none"] = "none"
    can_issue_clearance: Literal[False] = False
    direct_execution: Literal[False] = False
    final_authorization_boundary: Literal["REHT"] = "REHT"

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"plan_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_plan(self) -> FunctionWorkspacePlan:
        if self.workspace_spec.program_ref != self.function_identity:
            raise ValueError("workspace program reference differs from function")
        if self.workspace_spec.program_digest != self.program_digest:
            raise ValueError("workspace program digest differs from function plan")
        if self.plan_digest and self.plan_digest != self.computed_digest:
            raise ValueError("function workspace plan digest mismatch")
        return self


def _snapshot_payload(snapshot: RegistrySnapshot) -> dict[str, Any]:
    return {
        "functions": {
            identity: {
                "def": entry.definition.model_dump(mode="json"),
                "hash": entry.function_hash,
            }
            for identity, entry in sorted(snapshot.functions.items())
        },
        "graphs": {
            identity: (
                graph.model_dump(mode="json") if hasattr(graph, "model_dump") else graph
            )
            for identity, graph in sorted(snapshot.graphs.items())
        },
    }


def _validate_snapshot(
    definition: FunctionDefinition,
    snapshot: RegistrySnapshot,
) -> tuple[str, str]:
    if canonical_digest(_snapshot_payload(snapshot)) != snapshot.hash:
        raise WorkspacePlanError("registry snapshot seal is invalid")
    entry = snapshot.functions.get(definition.identity)
    if entry is None or entry.definition != definition:
        raise WorkspacePlanError("function is absent from the pinned registry snapshot")
    function_hash = canonical_digest(definition.model_dump(mode="json"))
    if entry.function_hash != function_hash:
        raise WorkspacePlanError("function definition hash is invalid")
    graph = snapshot.graphs.get(definition.workflow_ref)
    if graph is None:
        raise WorkspacePlanError("function workflow is absent from registry snapshot")
    if hasattr(graph, "nodes"):
        node_effects = {
            node.effect_type.value if hasattr(node.effect_type, "value") else str(node.effect_type)
            for node in graph.nodes
            if (node.effect_type.value if hasattr(node.effect_type, "value") else str(node.effect_type)) != "PURE"
        }
        declared = set(definition.effects)
        undeclared = node_effects - declared
        if undeclared:
            raise WorkspacePlanError(f"function workflow carries undeclared effect(s) {sorted(undeclared)}")
    graph_payload = (
        graph.model_dump(mode="json") if hasattr(graph, "model_dump") else graph
    )
    return function_hash, canonical_digest(graph_payload)


def _validate_purpose_type(
    definition: FunctionDefinition,
    purpose: Purpose,
) -> None:
    for requirement in definition.purpose_requirements:
        if (
            requirement.purpose_types
            and purpose.purpose_type not in requirement.purpose_types
        ):
            raise WorkspacePlanError(
                f"purpose type {purpose.purpose_type} is outside function requirement"
            )


def _declared_capability_scopes(
    definition: FunctionDefinition,
) -> dict[str, set[str]]:
    scopes: dict[str, set[str]] = {}
    for requirement in definition.authority_requirements:
        scopes.setdefault(requirement.capability, set()).update(requirement.scope)
    return scopes


def _bind_targets(
    declared_scopes: dict[str, set[str]],
    targets_by_capability: dict[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    if set(targets_by_capability) != set(declared_scopes):
        raise WorkspacePlanError(
            "invocation targets must exactly cover declared capabilities"
        )
    bound: dict[str, tuple[str, ...]] = {}
    for capability, scope in sorted(declared_scopes.items()):
        targets = targets_by_capability[capability]
        if not targets or "*" in targets or len(set(targets)) != len(targets):
            raise WorkspacePlanError(
                f"capability {capability} requires unique explicit targets"
            )
        if scope and "*" not in scope and not set(targets).issubset(scope):
            raise WorkspacePlanError(
                f"capability {capability} target is outside function scope"
            )
        bound[capability] = tuple(sorted(targets))
    return bound


def _bind_effects(
    definition: FunctionDefinition,
    capabilities: set[str],
    effects_by_capability: dict[str, tuple[str, ...]] | None,
) -> dict[str, tuple[str, ...]]:
    declared_effects = {item for item in definition.effects if item != "PURE"}
    if not capabilities:
        if effects_by_capability:
            raise WorkspacePlanError("effects cannot be leased without a capability")
        return {}
    if effects_by_capability is None:
        if len(capabilities) != 1:
            raise WorkspacePlanError(
                "multi-capability functions require explicit effect bindings"
            )
        capability = next(iter(capabilities))
        return {capability: tuple(sorted(declared_effects))}
    if set(effects_by_capability) != capabilities:
        raise WorkspacePlanError(
            "effect bindings must exactly cover declared capabilities"
        )
    bound = {
        capability: tuple(sorted(set(effects)))
        for capability, effects in effects_by_capability.items()
    }
    union = {effect for effects in bound.values() for effect in effects}
    if union != declared_effects:
        raise WorkspacePlanError(
            "capability effects must exactly preserve the function effect set"
        )
    return bound


def compile_function_workspace_plan(
    definition: FunctionDefinition,
    snapshot: RegistrySnapshot,
    *,
    workspace_id: str,
    work_unit_id: str,
    tenant_id: str,
    purpose: Purpose,
    selectors: tuple[ProjectionSelector, ...],
    targets_by_capability: dict[str, tuple[str, ...]],
    expires_at: datetime,
    effects_by_capability: dict[str, tuple[str, ...]] | None = None,
    parameter_constraints_by_capability: dict[str, dict[str, Any]] | None = None,
    max_actions: int = 1,
) -> FunctionWorkspacePlan:
    """Lower one pinned Function invocation into a Kernel WorkspaceSpec.

    This is a deterministic plan only. Kernel compiles the actual projection
    from current WorldState and REHT evaluates fresh execution authority.
    """
    if definition.status != FunctionStatus.ACTIVE or definition.deprecated:
        raise WorkspacePlanError("only an active function may request a workspace")
    function_hash, compiled_graph_hash = _validate_snapshot(definition, snapshot)
    _validate_purpose_type(definition, purpose)

    declared_scopes = _declared_capability_scopes(definition)
    targets = _bind_targets(declared_scopes, targets_by_capability)
    effects = _bind_effects(
        definition,
        set(declared_scopes),
        effects_by_capability,
    )
    parameter_constraints_by_capability = parameter_constraints_by_capability or {}
    if not set(parameter_constraints_by_capability).issubset(declared_scopes):
        raise WorkspacePlanError(
            "parameter constraints reference an undeclared capability"
        )

    program_payload = {
        "compiler_ref": WORKSPACE_COMPILER_REF,
        "function_identity": definition.identity,
        "function_hash": function_hash,
        "workflow_ref": definition.workflow_ref,
        "compiled_graph_hash": compiled_graph_hash,
        "registry_snapshot_hash": snapshot.hash,
    }
    program_digest = canonical_digest(program_payload)
    consequence_bearing = bool(declared_scopes)
    workspace_spec = WorkspaceSpec(
        workspace_id=workspace_id,
        work_unit_id=work_unit_id,
        tenant_id=tenant_id,
        purpose_id=purpose.purpose_id,
        program_ref=definition.identity,
        program_digest=program_digest,
        selectors=selectors,
        capabilities=tuple(
            WorkspaceCapabilitySpec(
                capability=capability,
                target_refs=targets[capability],
                allowed_effects=effects[capability],
                parameter_constraints=parameter_constraints_by_capability.get(
                    capability,
                    {},
                ),
            )
            for capability in sorted(declared_scopes)
        ),
        allowed_output_kinds=(
            (CandidateKind.EXTERNAL_ACTION,)
            if consequence_bearing
            else (CandidateKind.ARTIFACT,)
        ),
        expires_at=expires_at,
        max_actions=max_actions if consequence_bearing else 0,
        step_up_required=(
            consequence_bearing
            and definition.autonomy_profile.default_autonomy_level
            != AutonomyLevel.AUTO_EXECUTE
        ),
    )
    provisional = FunctionWorkspacePlan(
        function_identity=definition.identity,
        function_hash=function_hash,
        workflow_ref=definition.workflow_ref,
        compiled_graph_hash=compiled_graph_hash,
        registry_snapshot_hash=snapshot.hash,
        program_digest=program_digest,
        workspace_spec=workspace_spec,
    )
    return provisional.model_copy(update={"plan_digest": provisional.computed_digest})

