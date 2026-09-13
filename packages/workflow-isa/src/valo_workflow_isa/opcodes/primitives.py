from __future__ import annotations

from dataclasses import dataclass

from ..contracts.common import EffectType, NodeClass, PrimitiveOpcode


@dataclass(frozen=True)
class OpcodeSpec:
    opcode: PrimitiveOpcode
    node_class: NodeClass
    default_effect: EffectType
    description: str


OPCODES: dict[PrimitiveOpcode, OpcodeSpec] = {
    PrimitiveOpcode.READ_STATE: OpcodeSpec(
        PrimitiveOpcode.READ_STATE, NodeClass.READ, EffectType.PURE,
        "Typed kernel query over current state; returns an immutable snapshot value.",
    ),
    PrimitiveOpcode.ASSERT_STATE: OpcodeSpec(
        PrimitiveOpcode.ASSERT_STATE, NodeClass.READ, EffectType.PURE,
        "Reads state and asserts a predicate; produces a boolean/Verified result.",
    ),
    PrimitiveOpcode.FETCH: OpcodeSpec(
        PrimitiveOpcode.FETCH, NodeClass.READ, EffectType.READ_EXTERNAL,
        "Fetches a value from an external source through the READ boundary.",
    ),
    PrimitiveOpcode.VALIDATE_SCHEMA: OpcodeSpec(
        PrimitiveOpcode.VALIDATE_SCHEMA, NodeClass.COMPUTE, EffectType.PURE,
        "Validates a value against a schema; produces Verified<T>.",
    ),
    PrimitiveOpcode.COMPARE: OpcodeSpec(
        PrimitiveOpcode.COMPARE, NodeClass.COMPUTE, EffectType.PURE,
        "Deterministic comparison of two values.",
    ),
    PrimitiveOpcode.RECONCILE: OpcodeSpec(
        PrimitiveOpcode.RECONCILE, NodeClass.COMPUTE, EffectType.PURE,
        "Reconciles a proposed value with authoritative state.",
    ),
    PrimitiveOpcode.EVALUATE_RULE: OpcodeSpec(
        PrimitiveOpcode.EVALUATE_RULE, NodeClass.DECIDE, EffectType.PURE,
        "Evaluates a rule against typed inputs; produces a decision result.",
    ),
    PrimitiveOpcode.CALCULATE: OpcodeSpec(
        PrimitiveOpcode.CALCULATE, NodeClass.COMPUTE, EffectType.PURE,
        "Pure deterministic calculation.",
    ),
    PrimitiveOpcode.REQUEST_INPUT: OpcodeSpec(
        PrimitiveOpcode.REQUEST_INPUT, NodeClass.DECIDE, EffectType.PURE,
        "Requests typed input; the node defers until input arrives.",
    ),
    PrimitiveOpcode.REQUEST_REVIEW: OpcodeSpec(
        PrimitiveOpcode.REQUEST_REVIEW, NodeClass.DECIDE, EffectType.PURE,
        "Requests a review; produces an Admitted<T> decision result.",
    ),
    PrimitiveOpcode.REQUEST_APPROVAL: OpcodeSpec(
        PrimitiveOpcode.REQUEST_APPROVAL, NodeClass.DECIDE, EffectType.PURE,
        "Requests approval; produces an Admitted/Authorized decision result.",
    ),
    PrimitiveOpcode.PREPARE_ACTION: OpcodeSpec(
        PrimitiveOpcode.PREPARE_ACTION, NodeClass.COMPUTE, EffectType.PURE,
        "Builds the Action Contract payload from typed inputs.",
    ),
    PrimitiveOpcode.AUTHORIZE_ACTION: OpcodeSpec(
        PrimitiveOpcode.AUTHORIZE_ACTION, NodeClass.WRITE, EffectType.EXERCISE_AUTHORITY,
        "Requests authorization through the REHT port; executes against a binding derived deterministically from the REHT decision.",
    ),
    PrimitiveOpcode.EXECUTE_ACTION: OpcodeSpec(
        PrimitiveOpcode.EXECUTE_ACTION, NodeClass.WRITE, EffectType.WRITE_INTERNAL,
        "Executes an already-authorized action through the Gateway port.",
    ),
    PrimitiveOpcode.VERIFY_EXECUTION: OpcodeSpec(
        PrimitiveOpcode.VERIFY_EXECUTION, NodeClass.READ, EffectType.READ_EXTERNAL,
        "Observes execution outcome via Veritas and checks postconditions via BARO.",
    ),
    PrimitiveOpcode.CREATE_DEADLINE: OpcodeSpec(
        PrimitiveOpcode.CREATE_DEADLINE, NodeClass.WRITE, EffectType.CREATE_OBLIGATION,
        "Creates a deadline obligation in authoritative state.",
    ),
    PrimitiveOpcode.RESERVE_RESOURCE: OpcodeSpec(
        PrimitiveOpcode.RESERVE_RESOURCE, NodeClass.WRITE, EffectType.ALLOCATE_RESOURCE,
        "Atomically reserves a resource through the full authorization pipeline.",
    ),
    PrimitiveOpcode.RELEASE_RESOURCE: OpcodeSpec(
        PrimitiveOpcode.RELEASE_RESOURCE, NodeClass.WRITE, EffectType.ALLOCATE_RESOURCE,
        "Releases a previously reserved resource.",
    ),
}


def opcode_node_class(opcode: str) -> NodeClass | None:
    try:
        return OPCODES[PrimitiveOpcode(opcode)].node_class
    except (KeyError, ValueError):
        return None


def opcode_spec(opcode: str) -> OpcodeSpec | None:
    try:
        return OPCODES[PrimitiveOpcode(opcode)]
    except (KeyError, ValueError):
        return None
