from __future__ import annotations

from valo_function_fabric import (
    AutonomyLevel,
    AutonomyProfile,
    GovernanceChange,
    RiskClass,
    TypeRef,
    UpgradeComparison,
)
from valo_function_fabric.contracts import (
    AuthorityRequirement,
    EvidenceRequirement,
    FunctionDefinition,
)


def _base(risk=RiskClass.R2_OPERATIONAL, effects=("PURE",), authority=None, evidence=None, autonomy=None) -> FunctionDefinition:
    return FunctionDefinition(
        function_id="valo.finance.pay", name="PAY", version="1.0.0",
        input_type=TypeRef(name="payment", type="PaymentRequest"),
        output_type=TypeRef(name="payment_result", type="VerifiedEffect<Payment>"),
        workflow_ref="wf.pay",
        effects=list(effects),
        risk_class=risk,
        autonomy_profile=autonomy or AutonomyProfile(
            allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.STEP_UP],
            default_autonomy_level=AutonomyLevel.STEP_UP,
        ),
        authority_requirements=authority or [],
        evidence_requirements=evidence or [],
        status="ACTIVE",
    )


def test_effects_increase_is_breaking() -> None:
    old = _base(effects=["PURE"])
    new = _base(effects=["PURE", "MOVE_MONEY"])
    comparison = UpgradeComparison(old, new)
    assert GovernanceChange.EFFECTS_INCREASED in comparison.changes()
    assert comparison.is_breaking_governance()


def test_risk_change_is_breaking() -> None:
    old = _base(risk=RiskClass.R2_OPERATIONAL)
    new = _base(risk=RiskClass.R4_RIGHTS_IMPACTING)
    assert GovernanceChange.RISK_CHANGED in UpgradeComparison(old, new).changes()
    assert UpgradeComparison(old, new).is_breaking_governance()


def test_authority_weakened_is_breaking() -> None:
    old = _base(authority=[AuthorityRequirement(capability="PAY", scope=["*"])])
    new = _base(authority=[])
    assert GovernanceChange.AUTHORITY_WEAKENED in UpgradeComparison(old, new).changes()
    assert UpgradeComparison(old, new).is_breaking_governance()


def test_evidence_weakened_is_breaking() -> None:
    old = _base(evidence=[EvidenceRequirement(required_types=["Verified<Recipient>", "Verified<Account>"], minimum_status="ADMITTED")])
    new = _base(evidence=[EvidenceRequirement(required_types=["Verified<Recipient>"], minimum_status="ADMITTED")])
    assert GovernanceChange.EVIDENCE_WEAKENED in UpgradeComparison(old, new).changes()


def test_autonomy_expansion_is_breaking() -> None:
    old = _base(autonomy=AutonomyProfile(allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.STEP_UP], default_autonomy_level=AutonomyLevel.STEP_UP))
    new = _base(autonomy=AutonomyProfile(allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.STEP_UP, AutonomyLevel.AUTO_EXECUTE], default_autonomy_level=AutonomyLevel.STEP_UP))
    assert GovernanceChange.AUTONOMY_EXPANDED in UpgradeComparison(old, new).changes()
    assert UpgradeComparison(old, new).is_breaking_governance()


def test_no_change_is_not_breaking() -> None:
    old = _base()
    new = _base()
    assert not UpgradeComparison(old, new).is_breaking_governance()
    assert UpgradeComparison(old, new).breaking_change_label() == GovernanceChange.NONE
