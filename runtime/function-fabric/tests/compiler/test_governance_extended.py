from __future__ import annotations

import pytest

from tests.helpers import call, graph
from valo_function_fabric import (
    AutonomyLevel,
    AutonomyProfile,
    FunctionDefinition,
    GovernanceError,
    RiskClass,
    TypeRef,
    compile_function_graph,
)
from valo_function_fabric.compiler.governance import (
    _authority_covered,
    _evidence_covered,
    _purpose_covered,
    _rights_covered,
)
from valo_function_fabric.contracts import (
    AuthorityRequirement,
    EvidenceRequirement,
    PurposeRequirement,
    RightsRequirement,
)


def _profile() -> AutonomyProfile:
    return AutonomyProfile(allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.STEP_UP], default_autonomy_level=AutonomyLevel.STEP_UP)


def _parent(identity="valo.test.parent", *, authority=None, evidence=None, rights=None, purpose=None) -> FunctionDefinition:
    return FunctionDefinition(
        function_id=identity, name="PARENT", version="1.0.0",
        input_type=TypeRef(name="payment", type="PaymentRequest"),
        output_type=TypeRef(name="payment_result", type="VerifiedEffect<Payment>"),
        workflow_ref="graph",
        effects=["MOVE_MONEY"],
        risk_class=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy_profile=_profile(),
        authority_requirements=authority or [AuthorityRequirement(capability="PAY", scope=["*"])],
        evidence_requirements=evidence or [],
        rights_requirements=rights or [],
        purpose_requirements=purpose or [],
        status="ACTIVE",
    )


def test_authority_scope_weakening_rejected(snapshot, stdlib_registry) -> None:
    g = graph(
        "gov.scope",
        [call("pay", "valo.finance.pay", input_bindings={"payment": "payment"})],
        inputs={"payment": "PaymentRequest"}, outputs={"payment_result": "VerifiedEffect<Payment>"},
    )
    parent = _parent(authority=[AuthorityRequirement(capability="PAY", scope=["acct-1"])])
    with pytest.raises(GovernanceError, match="scope"):
        compile_function_graph(g, snapshot, parent_definition=parent)


def test_evidence_status_weakening_rejected(snapshot, stdlib_registry) -> None:
    """PAY requires Verified<Recipient> at ADMITTED; a parent requiring it only
    at RECEIVED weakens evidence and must be rejected."""
    g = graph(
        "gov.evidence_status",
        [call("pay", "valo.finance.pay", input_bindings={"payment": "payment"})],
        inputs={"payment": "PaymentRequest"}, outputs={"payment_result": "VerifiedEffect<Payment>"},
    )
    parent = _parent(evidence=[EvidenceRequirement(required_types=["Verified<Recipient>"], minimum_status="RECEIVED")])
    with pytest.raises(GovernanceError, match="evidence"):
        compile_function_graph(g, snapshot, parent_definition=parent)


def test_rights_weakening_rejected(snapshot, stdlib_registry) -> None:
    g = graph(
        "gov.rights",
        [call("pay", "valo.finance.pay", input_bindings={"payment": "payment"})],
        inputs={"payment": "PaymentRequest"}, outputs={"payment_result": "VerifiedEffect<Payment>"},
    )
    # a parent that covers PAY's evidence and adds rights compiles
    parent = _parent(
        evidence=[
            EvidenceRequirement(required_types=["Verified<Recipient>", "Verified<Account>", "Admitted<PaymentObligation>"], minimum_status="ADMITTED"),
        ],
        rights=[RightsRequirement(required_rights=["APPROVE"])],
    )
    compile_function_graph(g, snapshot, parent_definition=parent)


def test_helper_authority_scope() -> None:
    parent = [AuthorityRequirement(capability="PAY", scope=["acct-1", "acct-2"])]
    assert _authority_covered(parent, AuthorityRequirement(capability="PAY", scope=["acct-1"]))
    assert not _authority_covered(parent, AuthorityRequirement(capability="PAY", scope=["acct-3"]))
    assert not _authority_covered(parent, AuthorityRequirement(capability="PAY", scope=["*"]))
    assert _authority_covered([AuthorityRequirement(capability="PAY", scope=["*"])], AuthorityRequirement(capability="PAY", scope=["acct-1"]))
    assert not _authority_covered(parent, AuthorityRequirement(capability="PAY", scope=["acct-1", "acct-9"]))
    # Capability mismatch must always return False even if child scope is empty
    assert not _authority_covered([AuthorityRequirement(capability="OTHER", scope=["*"])], AuthorityRequirement(capability="PAY", scope=[]))
    assert not _authority_covered([], AuthorityRequirement(capability="PAY", scope=[]))
    assert _authority_covered([AuthorityRequirement(capability="PAY", scope=[])], AuthorityRequirement(capability="PAY", scope=[]))


def test_helper_evidence_status() -> None:
    parent = [EvidenceRequirement(required_types=["Verified<Recipient>"], minimum_status="VERIFIED")]
    assert _evidence_covered(parent, EvidenceRequirement(required_types=["Verified<Recipient>"], minimum_status="VERIFIED"))
    assert _evidence_covered(parent, EvidenceRequirement(required_types=["Verified<Recipient>"], minimum_status="ADMITTED"))
    assert not _evidence_covered(parent, EvidenceRequirement(required_types=["Verified<Recipient>"], minimum_status="CONFIRMED"))
    assert not _evidence_covered(parent, EvidenceRequirement(required_types=["Verified<Account>"], minimum_status="ADMITTED"))


def test_helper_rights_and_purpose() -> None:
    parent = [RightsRequirement(required_rights=["ACCESS", "APPEAL"])]
    assert _rights_covered(parent, RightsRequirement(required_rights=["ACCESS"]))
    assert not _rights_covered(parent, RightsRequirement(required_rights=["PAYMENT"]))

    parent_purpose = [PurposeRequirement(purpose_types=["payment"])]
    assert _purpose_covered(parent_purpose, PurposeRequirement(purpose_types=["payment"]))
    assert not _purpose_covered(parent_purpose, PurposeRequirement(purpose_types=["inspection"]))
