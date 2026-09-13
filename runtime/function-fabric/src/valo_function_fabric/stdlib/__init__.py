from __future__ import annotations

from valo_workflow_isa.contracts import EffectType, NodeClass

from ..compiler import compile_function_graph
from ..contracts.common import (
    AutonomyLevel,
    IdempotencyRequirement,
    RiskClass,
)
from ..contracts.function import (
    AuthorityRequirement,
    AutonomyProfile,
    EvidenceRequirement,
    FunctionDefinition,
    TypeRef,
)
from ..contracts.graph import FunctionCall, FunctionEdge, FunctionGraph, FunctionRef
from ..registry.store import FunctionRegistry
from .helpers import leaf_definition, leaf_workflow, register_leaf

_DEFAULT_AUTONOMY = AutonomyProfile(
    allowed_autonomy_levels=[
        AutonomyLevel.HUMAN,
        AutonomyLevel.RECOMMEND,
        AutonomyLevel.STEP_UP,
    ],
    default_autonomy_level=AutonomyLevel.RECOMMEND,
)

AUTO_AUTONOMY = AutonomyProfile(
    allowed_autonomy_levels=[
        AutonomyLevel.HUMAN,
        AutonomyLevel.RECOMMEND,
        AutonomyLevel.STEP_UP,
        AutonomyLevel.AUTO_EXECUTE,
    ],
    default_autonomy_level=AutonomyLevel.STEP_UP,
)


def _t(name: str, type_expr: str) -> TypeRef:
    return TypeRef(name=name, type=type_expr)


def build_stdlib() -> FunctionRegistry:
    registry = FunctionRegistry()
    _register_identity(registry)
    _register_evidence(registry)
    _register_authority(registry)
    _register_qualification(registry)
    _register_resource(registry)
    _register_coordination(registry)
    _register_communication(registry)
    _register_finance(registry)
    _register_lifecycle(registry)
    _register_control(registry)
    _register_approve(registry)
    _register_composites(registry)
    return registry


def _register_identity(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.identity.verify_identity", "VERIFY_IDENTITY", "1.0.0",
        input_type=_t("candidate", "IdentityCandidate"),
        output_type=_t("identity", "Verified<Identity>"),
        workflow_graph=leaf_workflow(
            "wf.valo.identity.verify_identity", node_id="verify", opcode="RECONCILE",
            node_class=NodeClass.COMPUTE,
            input_refs=[_t("candidate", "IdentityCandidate")],
            output_refs=[_t("identity", "Verified<Identity>")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["READ_EXTERNAL", "WRITE_INTERNAL"],
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=AUTO_AUTONOMY,
        evidence=[EvidenceRequirement(required_types=["IdentityCandidate"], minimum_status="RECEIVED")],
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.identity.verify_identity", node_id="verify", opcode="RECONCILE",
        node_class=NodeClass.COMPUTE,
        input_refs=[_t("candidate", "IdentityCandidate")],
        output_refs=[_t("identity", "Verified<Identity>")],
        effect=EffectType.PURE, capability=None,
    ))


def _register_evidence(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.evidence.verify", "VERIFY_EVIDENCE", "1.0.0",
        input_type=_t("evidence_in", "Evidence"),
        output_type=_t("evidence", "Admitted<Evidence>"),
        workflow_graph=leaf_workflow(
            "wf.valo.evidence.verify", node_id="verify", opcode="RECONCILE",
            node_class=NodeClass.COMPUTE,
            input_refs=[_t("evidence_in", "Evidence")],
            output_refs=[_t("evidence", "Admitted<Evidence>")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["READ_EXTERNAL", "WRITE_INTERNAL"],
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=AUTO_AUTONOMY,
        evidence=[EvidenceRequirement(required_types=["Evidence"], minimum_status="RECEIVED")],
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.evidence.verify", node_id="verify", opcode="RECONCILE",
        node_class=NodeClass.COMPUTE,
        input_refs=[_t("evidence_in", "Evidence")],
        output_refs=[_t("evidence", "Admitted<Evidence>")],
        effect=EffectType.PURE, capability=None,
    ))

    definition = leaf_definition(
        "valo.evidence.request", "REQUEST_EVIDENCE", "1.0.0",
        input_type=_t("request", "EvidenceRequest"),
        output_type=_t("evidence", "Admitted<Evidence>"),
        workflow_graph=leaf_workflow(
            "wf.valo.evidence.request", node_id="request", opcode="REQUEST_INPUT",
            node_class=NodeClass.DECIDE,
            input_refs=[_t("request", "EvidenceRequest")],
            output_refs=[_t("evidence", "Admitted<Evidence>")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["PURE"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=_DEFAULT_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.evidence.request", node_id="request", opcode="REQUEST_INPUT",
        node_class=NodeClass.DECIDE,
        input_refs=[_t("request", "EvidenceRequest")],
        output_refs=[_t("evidence", "Admitted<Evidence>")],
        effect=EffectType.PURE, capability=None,
    ))


def _register_authority(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.authority.check", "CHECK_AUTHORITY", "1.0.0",
        input_type=_t("context", "AuthorityContext"),
        output_type=_t("evidence", "AuthorityEvidence"),
        workflow_graph=leaf_workflow(
            "wf.valo.authority.check", node_id="check", opcode="EVALUATE_RULE",
            node_class=NodeClass.DECIDE,
            input_refs=[_t("context", "AuthorityContext")],
            output_refs=[_t("evidence", "AuthorityEvidence")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["PURE"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=_DEFAULT_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.authority.check", node_id="check", opcode="EVALUATE_RULE",
        node_class=NodeClass.DECIDE,
        input_refs=[_t("context", "AuthorityContext")],
        output_refs=[_t("evidence", "AuthorityEvidence")],
        effect=EffectType.PURE, capability=None,
    ))


def _register_qualification(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.qualification.check_eligibility", "CHECK_ELIGIBILITY", "1.0.0",
        input_type=_t("criteria", "EligibilityCriteria"),
        output_type=_t("result", "EligibilityResult"),
        workflow_graph=leaf_workflow(
            "wf.valo.qualification.check_eligibility", node_id="check", opcode="EVALUATE_RULE",
            node_class=NodeClass.DECIDE,
            input_refs=[_t("criteria", "EligibilityCriteria")],
            output_refs=[_t("result", "EligibilityResult")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["PURE"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=_DEFAULT_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.qualification.check_eligibility", node_id="check", opcode="EVALUATE_RULE",
        node_class=NodeClass.DECIDE,
        input_refs=[_t("criteria", "EligibilityCriteria")],
        output_refs=[_t("result", "EligibilityResult")],
        effect=EffectType.PURE, capability=None,
    ))

    definition = leaf_definition(
        "valo.intake.classify", "CLASSIFY", "1.0.0",
        input_type=_t("request", "Request"),
        output_type=_t("classification", "Classification"),
        workflow_graph=leaf_workflow(
            "wf.valo.intake.classify", node_id="classify", opcode="EVALUATE_RULE",
            node_class=NodeClass.DECIDE,
            input_refs=[_t("request", "Request")],
            output_refs=[_t("classification", "Classification")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["PURE"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=AUTO_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.intake.classify", node_id="classify", opcode="EVALUATE_RULE",
        node_class=NodeClass.DECIDE,
        input_refs=[_t("request", "Request")],
        output_refs=[_t("classification", "Classification")],
        effect=EffectType.PURE, capability=None,
    ))


def _register_resource(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.resource.match", "MATCH_RESOURCE", "1.0.0",
        input_type=_t("requirement", "ResourceRequirement"),
        output_type=_t("candidates", "CandidateSet<Resource>"),
        workflow_graph=leaf_workflow(
            "wf.valo.resource.match", node_id="match", opcode="RECONCILE",
            node_class=NodeClass.COMPUTE,
            input_refs=[_t("requirement", "ResourceRequirement")],
            output_refs=[_t("candidates", "CandidateSet<Resource>")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["PURE"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=AUTO_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.resource.match", node_id="match", opcode="RECONCILE",
        node_class=NodeClass.COMPUTE,
        input_refs=[_t("requirement", "ResourceRequirement")],
        output_refs=[_t("candidates", "CandidateSet<Resource>")],
        effect=EffectType.PURE, capability=None,
    ))

    definition = leaf_definition(
        "valo.resource.reserve", "RESERVE_RESOURCE", "1.0.0",
        input_type=_t("resource", "Candidate<Resource>"),
        output_type=_t("reservation", "Reserved<Resource>"),
        workflow_graph=leaf_workflow(
            "wf.valo.resource.reserve", node_id="reserve", opcode="RESERVE_RESOURCE",
            node_class=NodeClass.WRITE,
            input_refs=[_t("resource", "Candidate<Resource>")],
            output_refs=[_t("reservation", "Reserved<Resource>")],
            effect=EffectType.ALLOCATE_RESOURCE, capability="ALLOCATE",
            idempotency=IdempotencyRequirement.REQUIRED,
            config={"action_type": "RESERVE_RESOURCE", "kernel_event_type": "RESOURCE_RESERVED"},
        ),
        effects=["ALLOCATE_RESOURCE"],
        risk=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy=AUTO_AUTONOMY,
        authority=[AuthorityRequirement(capability="ALLOCATE", scope=["*"])],
        idempotency=IdempotencyRequirement.REQUIRED,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.resource.reserve", node_id="reserve", opcode="RESERVE_RESOURCE",
        node_class=NodeClass.WRITE,
        input_refs=[_t("resource", "Candidate<Resource>")],
        output_refs=[_t("reservation", "Reserved<Resource>")],
        effect=EffectType.ALLOCATE_RESOURCE, capability="ALLOCATE",
        idempotency=IdempotencyRequirement.REQUIRED,
        config={"action_type": "RESERVE_RESOURCE", "kernel_event_type": "RESOURCE_RESERVED"},
    ))

    definition = leaf_definition(
        "valo.resource.allocate", "ALLOCATE_RESOURCE", "1.0.0",
        input_type=_t("demand", "AllocationDemand"),
        output_type=_t("allocation", "Executed<Allocation>"),
        workflow_graph=leaf_workflow(
            "wf.valo.resource.allocate", node_id="allocate", opcode="EXECUTE_ACTION",
            node_class=NodeClass.WRITE,
            input_refs=[_t("demand", "AllocationDemand")],
            output_refs=[_t("allocation", "Executed<Allocation>")],
            effect=EffectType.ALLOCATE_RESOURCE, capability="ALLOCATE",
            idempotency=IdempotencyRequirement.REQUIRED,
            config={"action_type": "ALLOCATE_RESOURCE", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
        ),
        effects=["ALLOCATE_RESOURCE"],
        risk=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy=AUTO_AUTONOMY,
        authority=[AuthorityRequirement(capability="ALLOCATE", scope=["*"])],
        idempotency=IdempotencyRequirement.REQUIRED,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.resource.allocate", node_id="allocate", opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        input_refs=[_t("demand", "AllocationDemand")],
        output_refs=[_t("allocation", "Executed<Allocation>")],
        effect=EffectType.ALLOCATE_RESOURCE, capability="ALLOCATE",
        idempotency=IdempotencyRequirement.REQUIRED,
        config={"action_type": "ALLOCATE_RESOURCE", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
    ))


def _register_coordination(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.coordination.schedule", "SCHEDULE", "1.0.0",
        input_type=_t("requirement", "ScheduleRequirement"),
        output_type=_t("booking", "Confirmed<Booking>"),
        workflow_graph=leaf_workflow(
            "wf.valo.coordination.schedule", node_id="book", opcode="RESERVE_RESOURCE",
            node_class=NodeClass.WRITE,
            input_refs=[_t("requirement", "ScheduleRequirement")],
            output_refs=[_t("booking", "Confirmed<Booking>")],
            effect=EffectType.ALLOCATE_RESOURCE, capability="SCHEDULE",
            idempotency=IdempotencyRequirement.REQUIRED,
            config={"action_type": "SCHEDULE", "kernel_event_type": "RESOURCE_RESERVED"},
        ),
        effects=["PURE", "ALLOCATE_RESOURCE"],
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=AUTO_AUTONOMY,
        authority=[AuthorityRequirement(capability="SCHEDULE", scope=["*"])],
        idempotency=IdempotencyRequirement.REQUIRED,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.coordination.schedule", node_id="book", opcode="RESERVE_RESOURCE",
        node_class=NodeClass.WRITE,
        input_refs=[_t("requirement", "ScheduleRequirement")],
        output_refs=[_t("booking", "Confirmed<Booking>")],
        effect=EffectType.ALLOCATE_RESOURCE, capability="SCHEDULE",
        idempotency=IdempotencyRequirement.REQUIRED,
        config={"action_type": "SCHEDULE", "kernel_event_type": "RESOURCE_RESERVED"},
    ))


def _register_communication(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.communication.notify", "NOTIFY", "1.0.0",
        input_type=_t("notification", "Notification"),
        output_type=_t("ack", "Acknowledged<Message>"),
        workflow_graph=leaf_workflow(
            "wf.valo.communication.notify", node_id="notify", opcode="EXECUTE_ACTION",
            node_class=NodeClass.WRITE,
            input_refs=[_t("notification", "Notification")],
            output_refs=[_t("ack", "Acknowledged<Message>")],
            effect=EffectType.COMMUNICATE, capability="NOTIFY",
            idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
            config={"action_type": "NOTIFY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
        ),
        effects=["COMMUNICATE"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=AUTO_AUTONOMY,
        authority=[AuthorityRequirement(capability="NOTIFY", scope=["*"])],
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.communication.notify", node_id="notify", opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        input_refs=[_t("notification", "Notification")],
        output_refs=[_t("ack", "Acknowledged<Message>")],
        effect=EffectType.COMMUNICATE, capability="NOTIFY",
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
        config={"action_type": "NOTIFY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
    ))


def _register_finance(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.finance.price", "PRICE", "1.0.0",
        input_type=_t("scope", "PriceScope"),
        output_type=_t("price", "Calculated<Price>"),
        workflow_graph=leaf_workflow(
            "wf.valo.finance.price", node_id="calc", opcode="CALCULATE",
            node_class=NodeClass.COMPUTE,
            input_refs=[_t("scope", "PriceScope")],
            output_refs=[_t("price", "Calculated<Price>")],
            effect=EffectType.PURE, capability=None,
            config={"expression": "scope"},
        ),
        effects=["PURE"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=AUTO_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.finance.price", node_id="calc", opcode="CALCULATE",
        node_class=NodeClass.COMPUTE,
        input_refs=[_t("scope", "PriceScope")],
        output_refs=[_t("price", "Calculated<Price>")],
        effect=EffectType.PURE, capability=None,
        config={"expression": "scope"},
    ))

    definition = leaf_definition(
        "valo.finance.invoice", "INVOICE", "1.0.0",
        input_type=_t("invoice", "InvoiceRequest"),
        output_type=_t("issued", "Issued<Invoice>"),
        workflow_graph=leaf_workflow(
            "wf.valo.finance.invoice", node_id="issue", opcode="CREATE_DEADLINE",
            node_class=NodeClass.WRITE,
            input_refs=[_t("invoice", "InvoiceRequest")],
            output_refs=[_t("issued", "Issued<Invoice>")],
            effect=EffectType.CREATE_OBLIGATION, capability="INVOICE",
            idempotency=IdempotencyRequirement.REQUIRED,
            config={"action_type": "ISSUE_INVOICE", "kernel_event_type": "OBLIGATION_CREATED"},
        ),
        effects=["CREATE_OBLIGATION"],
        risk=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy=AUTO_AUTONOMY,
        authority=[AuthorityRequirement(capability="INVOICE", scope=["*"])],
        idempotency=IdempotencyRequirement.REQUIRED,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.finance.invoice", node_id="issue", opcode="CREATE_DEADLINE",
        node_class=NodeClass.WRITE,
        input_refs=[_t("invoice", "InvoiceRequest")],
        output_refs=[_t("issued", "Issued<Invoice>")],
        effect=EffectType.CREATE_OBLIGATION, capability="INVOICE",
        idempotency=IdempotencyRequirement.REQUIRED,
        config={"action_type": "ISSUE_INVOICE", "kernel_event_type": "OBLIGATION_CREATED"},
    ))

    definition = leaf_definition(
        "valo.finance.pay", "PAY", "1.0.0",
        input_type=_t("payment", "PaymentRequest"),
        output_type=_t("payment_result", "VerifiedEffect<Payment>"),
        workflow_graph=leaf_workflow(
            "wf.valo.finance.pay", node_id="pay", opcode="EXECUTE_ACTION",
            node_class=NodeClass.WRITE,
            input_refs=[_t("payment", "PaymentRequest")],
            output_refs=[_t("payment_result", "VerifiedEffect<Payment>")],
            effect=EffectType.MOVE_MONEY, capability="PAY",
            idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
            config={"action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED", "postconditions": {"payment": "VERIFIED"}, "target": "payment", "actor": "agent-a", "identity_id": "id-agent"},
        ),
        effects=["MOVE_MONEY"],
        risk=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy=AutonomyProfile(
            allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP],
            default_autonomy_level=AutonomyLevel.STEP_UP,
        ),
        authority=[AuthorityRequirement(capability="PAY", scope=["*"])],
        evidence=[
            EvidenceRequirement(required_types=["Verified<Recipient>", "Verified<Account>", "Admitted<PaymentObligation>"], minimum_status="ADMITTED"),
        ],
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.finance.pay", node_id="pay", opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        input_refs=[_t("payment", "PaymentRequest")],
        output_refs=[_t("payment_result", "VerifiedEffect<Payment>")],
        effect=EffectType.MOVE_MONEY, capability="PAY",
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
        config={"action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED", "postconditions": {"payment": "VERIFIED"}, "target": "payment", "actor": "agent-a", "identity_id": "id-agent"},
    ))

    definition = leaf_definition(
        "valo.finance.refund", "REFUND", "1.0.0",
        input_type=_t("refund", "RefundRequest"),
        output_type=_t("refund_result", "VerifiedEffect<Refund>"),
        workflow_graph=leaf_workflow(
            "wf.valo.finance.refund", node_id="refund", opcode="EXECUTE_ACTION",
            node_class=NodeClass.WRITE,
            input_refs=[_t("refund", "RefundRequest")],
            output_refs=[_t("refund_result", "VerifiedEffect<Refund>")],
            effect=EffectType.MOVE_MONEY, capability="REFUND",
            idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
            config={"action_type": "REFUND", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
        ),
        effects=["MOVE_MONEY"],
        risk=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy=AutonomyProfile(
            allowed_autonomy_levels=[AutonomyLevel.HUMAN, AutonomyLevel.RECOMMEND, AutonomyLevel.STEP_UP],
            default_autonomy_level=AutonomyLevel.STEP_UP,
        ),
        authority=[AuthorityRequirement(capability="REFUND", scope=["*"])],
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.finance.refund", node_id="refund", opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        input_refs=[_t("refund", "RefundRequest")],
        output_refs=[_t("refund_result", "VerifiedEffect<Refund>")],
        effect=EffectType.MOVE_MONEY, capability="REFUND",
        idempotency=IdempotencyRequirement.VERIFY_BEFORE_REPLAY,
        config={"action_type": "REFUND", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
    ))


def _register_lifecycle(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.lifecycle.register", "REGISTER", "1.0.0",
        input_type=_t("registration", "Registration"),
        output_type=_t("registered", "Registered<Entity>"),
        workflow_graph=leaf_workflow(
            "wf.valo.lifecycle.register", node_id="register", opcode="EXECUTE_ACTION",
            node_class=NodeClass.WRITE,
            input_refs=[_t("registration", "Registration")],
            output_refs=[_t("registered", "Registered<Entity>")],
            effect=EffectType.WRITE_INTERNAL, capability="REGISTER",
            config={"action_type": "REGISTER", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
        ),
        effects=["WRITE_INTERNAL"],
        risk=RiskClass.R1_REVERSIBLE_ADMINISTRATIVE,
        autonomy=AUTO_AUTONOMY,
        authority=[AuthorityRequirement(capability="REGISTER", scope=["*"])],
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.lifecycle.register", node_id="register", opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        input_refs=[_t("registration", "Registration")],
        output_refs=[_t("registered", "Registered<Entity>")],
        effect=EffectType.WRITE_INTERNAL, capability="REGISTER",
        config={"action_type": "REGISTER", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
    ))


def _register_control(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.control.inspect", "INSPECT", "1.0.0",
        input_type=_t("requirement", "InspectionRequirement"),
        output_type=_t("finding", "Finding"),
        workflow_graph=leaf_workflow(
            "wf.valo.control.inspect", node_id="inspect", opcode="RECONCILE",
            node_class=NodeClass.COMPUTE,
            input_refs=[_t("requirement", "InspectionRequirement")],
            output_refs=[_t("finding", "Finding")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["READ_EXTERNAL"],
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=AUTO_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.control.inspect", node_id="inspect", opcode="RECONCILE",
        node_class=NodeClass.COMPUTE,
        input_refs=[_t("requirement", "InspectionRequirement")],
        output_refs=[_t("finding", "Finding")],
        effect=EffectType.PURE, capability=None,
    ))

    definition = leaf_definition(
        "valo.control.remediate", "REMEDIATE", "1.0.0",
        input_type=_t("finding", "Finding"),
        output_type=_t("result", "ResolvedFinding"),
        workflow_graph=leaf_workflow(
            "wf.valo.control.remediate", node_id="remediate", opcode="EXECUTE_ACTION",
            node_class=NodeClass.WRITE,
            input_refs=[_t("finding", "Finding")],
            output_refs=[_t("result", "ResolvedFinding")],
            effect=EffectType.WRITE_INTERNAL, capability="REMEDIATE",
            config={"action_type": "REMEDIATE", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
        ),
        effects=["WRITE_INTERNAL"],
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=AUTO_AUTONOMY,
        authority=[AuthorityRequirement(capability="REMEDIATE", scope=["*"])],
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.control.remediate", node_id="remediate", opcode="EXECUTE_ACTION",
        node_class=NodeClass.WRITE,
        input_refs=[_t("finding", "Finding")],
        output_refs=[_t("result", "ResolvedFinding")],
        effect=EffectType.WRITE_INTERNAL, capability="REMEDIATE",
        config={"action_type": "REMEDIATE", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
    ))


def _register_approve(registry: FunctionRegistry) -> None:
    definition = leaf_definition(
        "valo.decision.approve", "APPROVE", "1.0.0",
        input_type=_t("approval", "ApprovalRequest"),
        output_type=_t("attestation", "ApprovalAttestation"),
        workflow_graph=leaf_workflow(
            "wf.valo.decision.approve", node_id="approve", opcode="REQUEST_APPROVAL",
            node_class=NodeClass.DECIDE,
            input_refs=[_t("approval", "ApprovalRequest")],
            output_refs=[_t("attestation", "ApprovalAttestation")],
            effect=EffectType.PURE, capability=None,
        ),
        effects=["PURE"],
        risk=RiskClass.R2_OPERATIONAL,
        autonomy=_DEFAULT_AUTONOMY,
    )
    register_leaf(registry, definition, leaf_workflow(
        "wf.valo.decision.approve", node_id="approve", opcode="REQUEST_APPROVAL",
        node_class=NodeClass.DECIDE,
        input_refs=[_t("approval", "ApprovalRequest")],
        output_refs=[_t("attestation", "ApprovalAttestation")],
        effect=EffectType.PURE, capability=None,
    ))


def _register_composites(registry: FunctionRegistry) -> None:
    snapshot = registry.snapshot()

    onboard = FunctionGraph(
        graph_id="graph.valo.lifecycle.onboard", version="1",
        inputs={"identity": "IdentityCandidate", "criteria": "EligibilityCriteria", "evidence": "Evidence", "registration": "Registration", "demand": "AllocationDemand", "notification": "Notification"},
        outputs={"done": "Acknowledged<Message>"},
        nodes=[
            FunctionCall(id="verify_identity", function_ref=FunctionRef(function_id="valo.identity.verify_identity", version="1.0.0"), input_bindings={"candidate": "identity"}, output_bindings={"identity": "verified"}),
            FunctionCall(id="check_eligibility", function_ref=FunctionRef(function_id="valo.qualification.check_eligibility", version="1.0.0"), input_bindings={"criteria": "criteria"}, output_bindings={"result": "eligible"}),
            FunctionCall(id="verify_evidence", function_ref=FunctionRef(function_id="valo.evidence.verify", version="1.0.0"), input_bindings={"evidence_in": "evidence"}, output_bindings={"evidence": "admitted"}),
            FunctionCall(id="register", function_ref=FunctionRef(function_id="valo.lifecycle.register", version="1.0.0"), input_bindings={"registration": "registration"}, output_bindings={"registered": "registered"}),
            FunctionCall(id="allocate", function_ref=FunctionRef(function_id="valo.resource.allocate", version="1.0.0"), input_bindings={"demand": "demand"}, output_bindings={"allocation": "allocated"}),
            FunctionCall(id="notify", function_ref=FunctionRef(function_id="valo.communication.notify", version="1.0.0"), input_bindings={"notification": "notification"}, output_bindings={"ack": "done"}),
        ],
        edges=[
            FunctionEdge(source="verify_identity", target="check_eligibility"),
            FunctionEdge(source="check_eligibility", target="verify_evidence"),
            FunctionEdge(source="verify_evidence", target="register"),
            FunctionEdge(source="verify_evidence", target="allocate"),
            FunctionEdge(source="register", target="notify"),
            FunctionEdge(source="allocate", target="notify"),
        ],
        entry_nodes=["verify_identity"],
        terminal_nodes=["notify"],
    )

    onboard_def = FunctionDefinition(
        function_id="valo.lifecycle.onboard", name="ONBOARD", version="1.0.0",
        input_type=TypeRef(name="identity", type="IdentityCandidate"),
        output_type=TypeRef(name="done", type="Acknowledged<Message>"),
        workflow_ref="graph.valo.lifecycle.onboard",
        effects=["READ_EXTERNAL", "WRITE_INTERNAL", "ALLOCATE_RESOURCE", "COMMUNICATE"],
        risk_class=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy_profile=_DEFAULT_AUTONOMY,
        authority_requirements=[AuthorityRequirement(capability="REGISTER", scope=["*"]), AuthorityRequirement(capability="ALLOCATE", scope=["*"]), AuthorityRequirement(capability="NOTIFY", scope=["*"])],
        evidence_requirements=[EvidenceRequirement(required_types=["IdentityCandidate", "Evidence"], minimum_status="RECEIVED")],
        status="ACTIVE",
    )
    compiled = compile_function_graph(onboard, snapshot, parent_definition=onboard_def)
    registry.register(onboard_def, compiled.workflow_graph, source_graph=onboard)

    # OFFBOARD — composite over the v1 subset: the offboarding state change is
    # written through REGISTER (a WRITE); REVOKE/RESOURCE-release primitives
    # arrive with the authority packs (section 35 scope).
    offboard = FunctionGraph(
        graph_id="graph.valo.lifecycle.offboard", version="1",
        inputs={"registration": "Registration"},
        outputs={"done": "Registered<Entity>"},
        nodes=[
            FunctionCall(id="register_off", function_ref=FunctionRef(function_id="valo.lifecycle.register", version="1.0.0"), input_bindings={"registration": "registration"}, output_bindings={"registered": "done"}),
        ],
        edges=[],
        entry_nodes=["register_off"],
        terminal_nodes=["register_off"],
    )
    offboard_def = FunctionDefinition(
        function_id="valo.lifecycle.offboard", name="OFFBOARD", version="1.0.0",
        input_type=TypeRef(name="registration", type="Registration"),
        output_type=TypeRef(name="done", type="Registered<Entity>"),
        workflow_ref="graph.valo.lifecycle.offboard",
        effects=["WRITE_INTERNAL", "ALLOCATE_RESOURCE"],
        risk_class=RiskClass.R3_FINANCIAL_LEGAL,
        autonomy_profile=_DEFAULT_AUTONOMY,
        authority_requirements=[AuthorityRequirement(capability="REGISTER", scope=["*"]), AuthorityRequirement(capability="ALLOCATE", scope=["*"])],
        evidence_requirements=[EvidenceRequirement(required_types=["Registration"], minimum_status="RECEIVED")],
        status="ACTIVE",
    )
    compiled = compile_function_graph(offboard, snapshot, parent_definition=offboard_def)
    registry.register(offboard_def, compiled.workflow_graph, source_graph=offboard)
