from __future__ import annotations

import pytest

from valo_function_fabric.contracts import (
    AutonomyLevel,
    AutonomyProfile,
    FunctionDefinition,
    TypeRef,
)


def _profile() -> AutonomyProfile:
    return AutonomyProfile(
        allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.STEP_UP],
        default_autonomy_level=AutonomyLevel.STEP_UP,
    )


def test_definition_contract_frozen() -> None:
    definition = FunctionDefinition(
        function_id="valo.finance.pay", name="PAY", version="1.0.0",
        input_type=TypeRef(name="payment", type="PaymentRequest"),
        output_type=TypeRef(name="payment_result", type="VerifiedEffect<Payment>"),
        workflow_ref="wf.pay",
        effects=["MOVE_MONEY"],
        risk_class="R3_FINANCIAL_LEGAL",
        autonomy_profile=_profile(),
        status="ACTIVE",
    )
    with pytest.raises(ValueError):
        definition.name = "renamed"  # type: ignore[misc]


def test_identity_is_machine_readable() -> None:
    definition = FunctionDefinition(
        function_id="valo.finance.pay", name="Display Pay", version="1.0.0",
        input_type=TypeRef(name="payment", type="PaymentRequest"),
        output_type=TypeRef(name="payment_result", type="VerifiedEffect<Payment>"),
        workflow_ref="wf.pay",
        effects=["MOVE_MONEY"],
        risk_class="R3_FINANCIAL_LEGAL",
        autonomy_profile=_profile(),
        status="ACTIVE",
    )
    assert definition.identity == "valo.finance.pay@1.0.0"
    assert "@" not in definition.function_id


def test_default_autonomy_must_be_allowed() -> None:
    with pytest.raises(ValueError):
        AutonomyProfile(
            allowed_autonomy_levels=[AutonomyLevel.HUMAN],
            default_autonomy_level=AutonomyLevel.AUTO_EXECUTE,
        )


def test_invalid_type_expression_rejected() -> None:
    with pytest.raises(ValueError):
        TypeRef(name="x", type="Verified<")
