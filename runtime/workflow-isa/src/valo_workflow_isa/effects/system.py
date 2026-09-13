from __future__ import annotations

from ..contracts.common import EffectType, NodeClass

# Effects that change authoritative reality irreversibly. A WRITE node carrying
# one of these must be idempotent (require an idempotency key) or the compiler
# rejects it.
IRREVERSIBLE_EFFECTS = frozenset(
    {
        EffectType.MOVE_MONEY,
        EffectType.CHANGE_RIGHT,
        EffectType.ALLOCATE_RESOURCE,
        EffectType.CREATE_OBLIGATION,
        EffectType.EXERCISE_AUTHORITY,
        EffectType.SAFETY_CRITICAL,
    }
)

# Effects that touch the external reality boundary and must be revalidated
# against a fresh execution context before execution.
EXTERNAL_EFFECTS = frozenset(
    {
        EffectType.READ_EXTERNAL,
        EffectType.COMMUNICATE,
        EffectType.ALLOCATE_RESOURCE,
        EffectType.CREATE_OBLIGATION,
        EffectType.CHANGE_RIGHT,
        EffectType.MOVE_MONEY,
        EffectType.EXERCISE_AUTHORITY,
        EffectType.SAFETY_CRITICAL,
    }
)


def allowed_effects(node_class: NodeClass) -> set[EffectType]:
    """The only effects each node class may declare. WRITE must be non-PURE;
    DECIDE can never have an effect at all."""
    if node_class == NodeClass.READ:
        return {EffectType.PURE, EffectType.READ_EXTERNAL}
    if node_class == NodeClass.COMPUTE:
        return {EffectType.PURE, EffectType.WRITE_INTERNAL}
    if node_class == NodeClass.DECIDE:
        return {EffectType.PURE}
    if node_class == NodeClass.WAIT:
        return {EffectType.PURE}
    if node_class == NodeClass.WRITE:
        return set(EffectType) - {EffectType.PURE}
    raise ValueError(f"unknown node class: {node_class}")


def validate_effect(node_class: NodeClass, effect: EffectType) -> None:
    allowed = allowed_effects(node_class)
    if effect not in allowed:
        raise ValueError(
            f"effect {effect.value} not allowed for node class {node_class.value}; "
            f"allowed: {sorted(e.value for e in allowed)}"
        )
