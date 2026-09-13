from __future__ import annotations

import pytest

from valo_workflow_isa.contracts import (
    ControlOpcode,
    EffectType,
    NodeClass,
    NodePolicies,
    PrimitiveOpcode,
    RetryPolicy,
    WorkflowNode,
)
from valo_workflow_isa.effects import allowed_effects, validate_effect


def test_node_classes_are_fixed() -> None:
    assert set(NodeClass) == {
        NodeClass.READ,
        NodeClass.COMPUTE,
        NodeClass.DECIDE,
        NodeClass.WAIT,
        NodeClass.WRITE,
    }


def test_control_isa_fixed() -> None:
    assert set(ControlOpcode) == {
        ControlOpcode.SEQ,
        ControlOpcode.PARALLEL,
        ControlOpcode.BRANCH,
        ControlOpcode.JOIN,
        ControlOpcode.LOOP,
        ControlOpcode.WAIT,
        ControlOpcode.TIMEOUT,
        ControlOpcode.RETRY,
        ControlOpcode.COMPENSATE,
        ControlOpcode.CALL,
        ControlOpcode.RETURN,
        ControlOpcode.HALT,
    }


def test_primitive_opcodes_fixed() -> None:
    assert len(set(PrimitiveOpcode)) == 18


def test_write_node_requires_non_pure_effect() -> None:
    with pytest.raises(ValueError):
        WorkflowNode(id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.PURE)


def test_probabilistic_write_rejected() -> None:
    from valo_workflow_isa.contracts import Determinism

    with pytest.raises(ValueError):
        WorkflowNode(
            id="w",
            opcode="EXECUTE_ACTION",
            node_class=NodeClass.WRITE,
            effect_type=EffectType.MOVE_MONEY,
            determinism=Determinism.PROBABILISTIC,
            policies=NodePolicies(authority=None),
        )


def test_effect_allowed_per_node_class() -> None:
    assert EffectType.PURE in allowed_effects(NodeClass.READ)
    assert EffectType.READ_EXTERNAL in allowed_effects(NodeClass.READ)
    with pytest.raises(ValueError):
        validate_effect(NodeClass.DECIDE, EffectType.MOVE_MONEY)
    with pytest.raises(ValueError):
        validate_effect(NodeClass.WRITE, EffectType.PURE)


def test_retry_policy_validation() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
