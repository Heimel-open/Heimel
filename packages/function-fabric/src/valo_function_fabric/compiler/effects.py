from __future__ import annotations

from ..contracts.function import FunctionDefinition
from .errors import EffectsError
from .resolver import ResolvedCall


def leaf_effects_within_declared(definition: FunctionDefinition, workflow_graph) -> None:
    """Golden invariant (leaf): the compiled workflow may never carry an effect
    the Function does not declare. PURE nodes contribute no effect and are
    exempt."""
    node_effects = {node.effect_type.value for node in workflow_graph.nodes if node.effect_type.value != "PURE"}
    declared = set(definition.effects)
    undeclared = node_effects - declared
    if undeclared:
        raise EffectsError(
            f"{definition.identity}: workflow carries undeclared effect(s) {sorted(undeclared)}; "
            f"declared {sorted(declared)}"
        )


def parent_effects_cover_children(
    parent: FunctionDefinition, children: list[ResolvedCall]
) -> None:
    """Golden invariant (composition): a parent Function's declared effects must
    be a superset of the union of its children's compiled effects. PURE is the
    absence of an effect and is exempt."""
    declared = set(parent.effects)
    union: set[str] = set()
    for child in children:
        union |= {node.effect_type.value for node in child.workflow_graph.nodes if node.effect_type.value != "PURE"}
        union |= {effect for effect in child.definition.effects if effect != "PURE"}
    missing = union - declared
    if missing:
        raise EffectsError(
            f"{parent.identity}: effects {sorted(missing)} from children are not declared "
            f"by the parent (declared {sorted(declared)})"
        )


def compiled_effect_set(nodes) -> set[str]:
    return {node.effect_type.value for node in nodes}

